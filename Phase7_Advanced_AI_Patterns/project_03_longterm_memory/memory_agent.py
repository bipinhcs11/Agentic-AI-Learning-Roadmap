"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           Phase 7 · Project 3 — Long-Term Memory Agent                     ║
║                                                                              ║
║  WHY THIS EXISTS                                                             ║
║  Every conversation with an LLM normally starts from scratch. The model     ║
║  has no idea who you are, what you talked about yesterday, or any facts      ║
║  you've shared before. This project fixes that by building a persistent     ║
║  memory layer that outlives individual conversations.                        ║
║                                                                              ║
║  ARCHITECTURE                                                                ║
║  User message                                                                ║
║    → embed the query (ask Ollama for embeddings)                            ║
║    → cosine-search SQLite for relevant past memories                        ║
║    → inject top-k memories into the system prompt                           ║
║    → LLM responds with context it wouldn't otherwise have                   ║
║    → ask LLM: "worth remembering?" → if YES, embed & store the exchange     ║
║                                                                              ║
║  PERSISTENCE                                                                 ║
║  Memories live in a SQLite file next to this script. Kill the process,      ║
║  reboot the machine — memories survive. New agent instance reads same DB.   ║
║                                                                              ║
║  Model   : gemma3:4b (Ollama)                                               ║
║  Embed   : nomic-embed-text (Ollama)                                        ║
║  Storage : SQLite + numpy JSON serialisation                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from openai import OpenAI  # We use the OpenAI-compatible client to talk to Ollama

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"          # Ollama ignores the key but the client needs one
CHAT_MODEL = "gemma3:4b"           # The "brain" that reads/writes memories
EMBED_MODEL = "nomic-embed-text"   # Dedicated embedding model (much smaller / faster)

# Where to persist memories — same directory as this script
DB_PATH = Path(__file__).parent / "memories.db"

# Cosine similarity threshold above which two memories are considered duplicates
CONSOLIDATION_THRESHOLD = 0.90

# How many memories to inject into each conversation turn
DEFAULT_TOP_K = 5


# ─────────────────────────────────────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Memory:
    """
    One unit of long-term memory.

    Fields
    ------
    id              : unique UUID so we can reference / delete individual memories
    content         : the raw text that was remembered
    embedding       : numpy float array produced by the embedding model
    timestamp       : epoch seconds when the memory was created
    importance_score: [0.0, ∞)  — higher = more important, boosted by access
    access_count    : how many times this memory was retrieved
    tags            : free-form labels added by the user (e.g. ["work", "hobby"])
    deleted         : soft-delete flag — we keep the row but stop surfacing it
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    embedding: np.ndarray = field(default_factory=lambda: np.array([]))
    timestamp: float = field(default_factory=time.time)
    importance_score: float = 1.0
    access_count: int = 0
    tags: list[str] = field(default_factory=list)
    deleted: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Embedding helper
# ─────────────────────────────────────────────────────────────────────────────

def _embed(client: OpenAI, text: str) -> np.ndarray:
    """
    Ask Ollama to produce a dense vector for `text`.

    WHY a separate embed model?
    Chat models are optimised for next-token prediction; embedding models are
    optimised to map semantically similar texts to nearby points in vector
    space.  nomic-embed-text is tiny (274 M params) and purpose-built for
    retrieval, so it's faster and more accurate for similarity search than
    asking the chat model.
    """
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    vec = np.array(response.data[0].embedding, dtype=np.float32)
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity in [-1, 1].

    WHY cosine and not Euclidean distance?
    Embedding vectors can have very different magnitudes depending on text
    length.  Cosine similarity normalises for magnitude and measures only
    the *direction* of the vectors — which correlates with semantic meaning.
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ─────────────────────────────────────────────────────────────────────────────
# Persistent Memory Store
# ─────────────────────────────────────────────────────────────────────────────

class LongTermMemoryStore:
    """
    SQLite-backed vector store that survives process restarts.

    We store embeddings as JSON arrays (one float per dimension) rather than
    using a dedicated vector database.  For a local learning project this is
    fine — SQLite is zero-dependency and the cosine search loop over a few
    hundred memories is sub-millisecond on any modern CPU.  In production
    you'd swap this for pgvector, Qdrant, Weaviate, etc.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self._init_db()

    # ── Database initialisation ──────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create the memories table if it doesn't already exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id             TEXT PRIMARY KEY,
                    content        TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    timestamp      REAL NOT NULL,
                    importance     REAL NOT NULL DEFAULT 1.0,
                    access_count   INTEGER NOT NULL DEFAULT 0,
                    tags_json      TEXT NOT NULL DEFAULT '[]',
                    deleted        INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()
        print(f"[MemoryStore] Connected to {self.db_path}")

    # ── Internal serialise / deserialise ────────────────────────────────────

    def _row_to_memory(self, row: tuple) -> Memory:
        """Convert a SQLite row back into a Memory dataclass."""
        id_, content, emb_json, ts, importance, access, tags_json, deleted = row
        return Memory(
            id=id_,
            content=content,
            embedding=np.array(json.loads(emb_json), dtype=np.float32),
            timestamp=ts,
            importance_score=importance,
            access_count=access,
            tags=json.loads(tags_json),
            deleted=bool(deleted),
        )

    def _load_all_active(self) -> list[Memory]:
        """Load every non-deleted memory from SQLite into RAM for searching."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, content, embedding_json, timestamp, importance, "
                "access_count, tags_json, deleted FROM memories WHERE deleted = 0"
            ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    # ── Importance Scoring ───────────────────────────────────────────────────

    def _importance_score(self, mem: Memory) -> float:
        """
        Compute a retrieval priority score for a memory.

        Formula (all components in [0, 1]):
            score = access_count_norm * 0.3
                  + recency_score     * 0.4
                  + base_importance   * 0.3

        WHY these weights?
        - Recency (0.4) gets the highest weight because recent information is
          most likely to still be relevant.
        - Access count (0.3) rewards memories that have been useful before —
          if you retrieved it last week, you'll probably need it again.
        - Base importance (0.3) preserves manually boosted memories.

        The recency score decays exponentially with a 30-day half-life.
        """
        now = time.time()
        age_days = (now - mem.timestamp) / 86_400
        half_life = 30.0
        recency = math.exp(-age_days * math.log(2) / half_life)

        # Normalise access count with a soft cap at 20 accesses
        access_norm = min(mem.access_count / 20.0, 1.0)

        return access_norm * 0.3 + recency * 0.4 + mem.importance_score * 0.3

    # ── Public API ───────────────────────────────────────────────────────────

    def add(self, content: str, tags: list[str] | None = None) -> Memory:
        """
        Embed `content` and write it to the database.

        Returns the Memory object so callers can inspect the assigned ID.
        """
        tags = tags or []
        embedding = _embed(self.client, content)
        mem = Memory(
            content=content,
            embedding=embedding,
            timestamp=time.time(),
            importance_score=1.0,
            tags=tags,
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?)",
                (
                    mem.id,
                    mem.content,
                    json.dumps(mem.embedding.tolist()),
                    mem.timestamp,
                    mem.importance_score,
                    mem.access_count,
                    json.dumps(mem.tags),
                    0,
                ),
            )
            conn.commit()
        print(f"  [+] Stored memory [{mem.id[:8]}...]: {content[:60]}")
        return mem

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Memory]:
        """
        Find the `top_k` memories most relevant to `query`.

        Relevance = cosine_similarity * importance_score
        This means a slightly less similar but heavily-accessed memory can
        outrank a more similar but brand-new one — which mirrors human memory.
        """
        all_mems = self._load_all_active()
        if not all_mems:
            return []

        query_vec = _embed(self.client, query)

        scored: list[tuple[float, Memory]] = []
        for mem in all_mems:
            sim = _cosine_similarity(query_vec, mem.embedding)
            # Blend semantic similarity with importance
            score = sim * self._importance_score(mem)
            scored.append((score, mem))

        # Sort descending, take top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [m for _, m in scored[:top_k]]

        # Increment access count for every retrieved memory
        with sqlite3.connect(self.db_path) as conn:
            for mem in top:
                conn.execute(
                    "UPDATE memories SET access_count = access_count + 1 WHERE id = ?",
                    (mem.id,),
                )
            conn.commit()

        return top

    def forget(self, memory_id: str) -> bool:
        """
        Soft-delete a memory by ID.

        WHY soft-delete?
        Hard deleting makes debugging harder — you lose the ability to
        inspect what the agent used to know.  Soft-delete preserves the row
        with deleted=1 so you can audit, recover, or analyse later.
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE memories SET deleted = 1 WHERE id = ? AND deleted = 0",
                (memory_id,),
            )
            conn.commit()
        removed = result.rowcount > 0
        if removed:
            print(f"  [-] Soft-deleted memory {memory_id[:8]}...")
        return removed

    def consolidate(self) -> int:
        """
        Merge near-duplicate memories to prevent the store from bloating.

        Algorithm:
          1. Load all active memories.
          2. For every pair (i, j) where i < j, compute cosine similarity.
          3. If similarity > CONSOLIDATION_THRESHOLD, keep the older memory
             (lower index after sorting by timestamp), soft-delete the newer
             duplicate, and merge their tags.

        WHY merge rather than just delete?
        We want to preserve important metadata (tags, access counts).
        The surviving memory gets the higher of the two importance scores and
        the combined access count.

        Returns the number of memories that were merged away.
        """
        mems = self._load_all_active()
        if len(mems) < 2:
            return 0

        # Sort by timestamp so we always keep the older version
        mems.sort(key=lambda m: m.timestamp)

        merged_count = 0
        deleted_ids: set[str] = set()

        for i in range(len(mems)):
            if mems[i].id in deleted_ids:
                continue
            for j in range(i + 1, len(mems)):
                if mems[j].id in deleted_ids:
                    continue
                sim = _cosine_similarity(mems[i].embedding, mems[j].embedding)
                if sim >= CONSOLIDATION_THRESHOLD:
                    # mems[i] is older → keep it, absorb mems[j]
                    merged_tags = list(set(mems[i].tags + mems[j].tags))
                    new_importance = max(mems[i].importance_score, mems[j].importance_score)
                    new_access = mems[i].access_count + mems[j].access_count
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute(
                            "UPDATE memories SET tags_json=?, importance=?, access_count=? WHERE id=?",
                            (json.dumps(merged_tags), new_importance, new_access, mems[i].id),
                        )
                        conn.execute(
                            "UPDATE memories SET deleted=1 WHERE id=?",
                            (mems[j].id,),
                        )
                        conn.commit()
                    print(
                        f"  [≈] Merged [{mems[j].id[:8]}] into [{mems[i].id[:8]}] "
                        f"(similarity={sim:.3f})"
                    )
                    deleted_ids.add(mems[j].id)
                    merged_count += 1

        return merged_count

    def get_stats(self) -> dict:
        """Return aggregate statistics about the memory store."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM memories WHERE deleted=0").fetchone()[0]
            deleted = conn.execute("SELECT COUNT(*) FROM memories WHERE deleted=1").fetchone()[0]
            if total > 0:
                oldest_ts = conn.execute(
                    "SELECT MIN(timestamp) FROM memories WHERE deleted=0"
                ).fetchone()[0]
                newest_ts = conn.execute(
                    "SELECT MAX(timestamp) FROM memories WHERE deleted=0"
                ).fetchone()[0]
                most_accessed = conn.execute(
                    "SELECT content, access_count FROM memories WHERE deleted=0 "
                    "ORDER BY access_count DESC LIMIT 1"
                ).fetchone()
            else:
                oldest_ts = newest_ts = None
                most_accessed = None

        return {
            "active_memories": total,
            "soft_deleted": deleted,
            "oldest": datetime.fromtimestamp(oldest_ts, tz=timezone.utc).isoformat() if oldest_ts else None,
            "newest": datetime.fromtimestamp(newest_ts, tz=timezone.utc).isoformat() if newest_ts else None,
            "most_accessed": most_accessed,
        }

    def show_all(self) -> None:
        """Pretty-print every active memory — useful for debugging."""
        mems = self._load_all_active()
        if not mems:
            print("  (no memories yet)")
            return
        mems.sort(key=lambda m: m.timestamp)
        for m in mems:
            ts = datetime.fromtimestamp(m.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            tags_str = f"  tags={m.tags}" if m.tags else ""
            print(
                f"  [{m.id[:8]}] {ts}  acc={m.access_count}  imp={m.importance_score:.2f}"
                f"{tags_str}\n    ↳ {m.content[:100]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Memory Agent
# ─────────────────────────────────────────────────────────────────────────────

class MemoryAgent:
    """
    A conversational agent with a persistent long-term memory.

    Every time you send a message:
      1. Relevant past memories are retrieved and injected into the system prompt.
      2. The LLM responds with those memories available as context.
      3. The agent asks the LLM whether the exchange is worth remembering.
      4. If YES, it embeds and stores a summary in SQLite.

    Because the database persists on disk, starting a new MemoryAgent instance
    (even after a full machine restart) will load all previous memories.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.store = LongTermMemoryStore(db_path=db_path)
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self.conversation_history: list[dict] = []
        print("[MemoryAgent] Ready.  Long-term memory loaded from disk.")

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _format_memories(self, memories: list[Memory]) -> str:
        """Turn a list of Memory objects into a readable block for the system prompt."""
        if not memories:
            return "No relevant memories found."
        lines = []
        for i, m in enumerate(memories, 1):
            age_days = (time.time() - m.timestamp) / 86_400
            lines.append(
                f"{i}. [{age_days:.0f}d ago, accessed {m.access_count}x] {m.content}"
            )
        return "\n".join(lines)

    def _should_remember(self, user_msg: str, assistant_msg: str) -> bool:
        """
        Ask the LLM whether this exchange contains something worth remembering.

        WHY delegate this to the LLM?
        Rule-based heuristics ("remember if message > 50 tokens") are brittle.
        The LLM can understand that "what time is it?" is ephemeral while
        "my daughter's name is Sofia" is worth keeping forever.
        """
        decision_prompt = (
            "You are a memory filter. Your only job is to decide whether the "
            "following conversation exchange contains information that would be "
            "useful to remember for future conversations (e.g., personal facts, "
            "preferences, goals, important events). "
            "Ignore small talk, greetings, or questions that need no context.\n\n"
            f"User said: {user_msg}\n"
            f"Assistant replied: {assistant_msg}\n\n"
            "Should this be stored in long-term memory? Reply with exactly YES or NO."
        )
        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": decision_prompt}],
            temperature=0.0,   # We want a deterministic YES/NO
            max_tokens=5,
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer.startswith("YES")

    def _summarise_for_memory(self, user_msg: str, assistant_msg: str) -> str:
        """
        Compress an exchange into a concise memory sentence.

        We don't store the raw conversation — we ask the LLM to distil the
        key fact so that stored memories are dense and retrieval-friendly.
        """
        prompt = (
            "Summarise the following exchange into one concise fact sentence "
            "suitable for long-term memory storage. Focus on facts, not the "
            "conversation structure.\n\n"
            f"User: {user_msg}\n"
            f"Assistant: {assistant_msg}\n\n"
            "One-sentence fact:"
        )
        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=80,
        )
        return response.choices[0].message.content.strip()

    # ── Public API ───────────────────────────────────────────────────────────

    def chat(self, message: str) -> str:
        """
        Send a message to the agent and receive a memory-augmented response.

        The flow:
          retrieve → inject into system prompt → call LLM → maybe store result
        """
        print(f"\n[You] {message}")

        # Step 1: Retrieve relevant memories
        relevant = self.store.retrieve(message, top_k=DEFAULT_TOP_K)
        memory_block = self._format_memories(relevant)

        # Step 2: Build system prompt with injected memories
        system_prompt = (
            "You are a helpful assistant with a long-term memory. "
            "Use the memories below to give personalised, context-aware responses. "
            "If a memory is relevant, reference it naturally — don't just recite it.\n\n"
            f"=== Long-Term Memories ===\n{memory_block}\n"
            "=========================\n\n"
            "Respond conversationally and helpfully."
        )

        # Step 3: Add user message to in-session history and call LLM
        self.conversation_history.append({"role": "user", "content": message})

        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *self.conversation_history,
            ],
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": reply})

        print(f"[Agent] {reply}")

        # Step 4: Decide whether to store this exchange as a long-term memory
        if self._should_remember(message, reply):
            summary = self._summarise_for_memory(message, reply)
            self.store.add(summary, tags=["auto"])
            print(f"  → Stored to long-term memory: \"{summary[:70]}...\"")
        else:
            print("  → Not stored (ephemeral exchange)")

        return reply

    def remember(self, fact: str, tags: list[str] | None = None) -> None:
        """Manually inject a fact into long-term memory, bypassing the LLM filter."""
        tags = (tags or []) + ["manual"]
        mem = self.store.add(fact, tags=tags)
        print(f"[MemoryAgent] Manually remembered: \"{fact[:70]}\" (id={mem.id[:8]})")

    def forget_about(self, topic: str) -> int:
        """
        Retrieve memories related to `topic` and soft-delete them all.

        Returns the number of memories erased.
        """
        candidates = self.store.retrieve(topic, top_k=10)
        count = 0
        for mem in candidates:
            if self.store.forget(mem.id):
                count += 1
        print(f"[MemoryAgent] Forgot {count} memories related to: \"{topic}\"")
        return count

    def show_memories(self) -> None:
        """Display all stored memories with metadata."""
        print("\n[MemoryAgent] ── Long-Term Memory Contents ──")
        self.store.show_all()
        stats = self.store.get_stats()
        print(f"\n  Stats: {stats}")


# ─────────────────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────────────────

def run_demo() -> None:
    """
    Demonstrate persistent memory across simulated conversation sessions.

    SESSION A  — tell the agent facts about yourself
    SESSION B  — simulate a restart (new MemoryAgent, same DB), ask what it knows
    CONSOLIDATION — add a near-duplicate, show the merger
    STATS      — print memory store statistics
    """
    print("=" * 70)
    print("  LONG-TERM MEMORY AGENT  —  Phase 7 / Project 3")
    print("=" * 70)

    # ── Session A: First conversation ────────────────────────────────────────
    print("\n" + "─" * 60)
    print("SESSION A: Teaching the agent about you")
    print("─" * 60)

    agent_a = MemoryAgent()

    agent_a.remember("The user's name is Bipin and he lives in Kathmandu, Nepal.", tags=["identity"])
    agent_a.remember("Bipin is a software engineer learning agentic AI systems.", tags=["career"])
    agent_a.remember("Bipin's favourite programming language is Python.", tags=["preference"])

    agent_a.chat("I'm thinking about building a RAG pipeline for my company. Any thoughts?")
    agent_a.chat("I really enjoy hiking in the Himalayas on weekends.")

    print("\n[Session A complete — memories saved to disk]\n")

    # ── Session B: Simulated restart ─────────────────────────────────────────
    print("\n" + "─" * 60)
    print("SESSION B: New agent instance — simulating a restart")
    print("─" * 60)

    # This is a BRAND NEW agent object — no shared state with agent_a
    # It only knows what's on disk
    agent_b = MemoryAgent()

    agent_b.chat("Hey! Do you know anything about me?")
    agent_b.chat("What kind of projects am I working on?")
    agent_b.chat("What outdoor activities do I enjoy?")

    # ── Consolidation demo ───────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("CONSOLIDATION: Adding a near-duplicate to show merge logic")
    print("─" * 60)

    # Manually add a fact that is semantically very close to one already stored
    agent_b.remember(
        "Bipin's preferred programming language is Python and he uses it daily.",
        tags=["preference"],
    )

    print("\n[Before consolidation]")
    agent_b.show_memories()

    merged = agent_b.store.consolidate()
    print(f"\n  consolidate() merged {merged} near-duplicate(s)")

    print("\n[After consolidation]")
    agent_b.show_memories()

    # ── Final stats ──────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("MEMORY STORE STATISTICS")
    print("─" * 60)
    stats = agent_b.store.get_stats()
    for k, v in stats.items():
        print(f"  {k:<20}: {v}")

    print("\n[Demo complete]")


if __name__ == "__main__":
    run_demo()
