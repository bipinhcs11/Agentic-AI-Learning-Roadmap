# Phase 7 · Project 3 — Long-Term Memory Agent

## Why Agents Forget

LLMs are **stateless functions**: you pass in tokens, you get tokens back. Nothing is written between calls. Every conversation begins with a blank slate — the model has no idea who you are, what you discussed yesterday, or what facts you've shared before.

This is fine for one-off tasks but disastrous for personal assistants, tutors, or any agent that's supposed to grow with you over time. The fix is to build a **memory layer outside the model** that persists to disk and is injected back in at the start of every conversation.

---

## How This Memory System Works

```
User message
     │
     ▼
[ Embed query ]  ──────────────────────────────────────────────────────────┐
     │                                                                      │
     ▼                                                                      │
[ Cosine search SQLite ]                                                    │
     │  top-k relevant memories                                             │
     ▼                                                                      │
[ Inject into system prompt ]                                               │
     │  "You have a long-term memory. Relevant memories: …"                │
     ▼                                                                      │
[ LLM generates response ]                                                  │
     │                                                                      │
     ▼                                                                      │
[ Ask LLM: "Worth remembering? YES/NO" ]                                   │
     │                                                                      │
     ├── YES → [ Summarise exchange ] → [ Embed ] → [ Store in SQLite ] ──►┘
     │
     └── NO  → discard (ephemeral exchange)
```

### Key components

| Component | Purpose |
|-----------|---------|
| `nomic-embed-text` | Converts text to 768-dim vectors |
| `SQLite` (`memories.db`) | Persists vectors + metadata across restarts |
| Cosine similarity | Finds semantically similar memories at query time |
| `gemma3:4b` | Both the chat model and the memory filter |

---

## Importance Scoring

Each memory has a dynamic importance score that affects how likely it is to be retrieved:

```
score = access_count_norm × 0.3
      + recency_score     × 0.4
      + base_importance   × 0.3
```

- **Recency** (40 %) — exponential decay with a 30-day half-life. Fresh memories surface first.
- **Access count** (30 %) — memories retrieved often are probably useful; they float to the top.
- **Base importance** (30 %) — set to 1.0 at creation; can be boosted manually.

Retrieval score = cosine_similarity × importance_score so a well-worn, recent memory beats a brand-new but slightly more similar one.

---

## Memory Consolidation

Over time the store accumulates near-duplicate memories. Running `store.consolidate()` finds pairs with cosine similarity > 0.90, keeps the older entry (preserving the original context), absorbs the duplicate's access count and tags, then soft-deletes the newer one.

This keeps the store compact without losing information.

---

## Soft Delete

`forget()` sets `deleted = 1` rather than removing the row. This lets you:
- Audit what the agent used to know
- Recover mistakes
- Analyse which memories get deleted most often

---

## Setup & Run

```bash
# 1. Install Ollama models
ollama pull gemma3:4b
ollama pull nomic-embed-text

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the demo
python memory_agent.py
```

The demo:
1. Creates a fresh `memories.db` (or reuses an existing one)
2. Teaches the agent several facts
3. Simulates a restart with a new `MemoryAgent` instance
4. Shows the agent recalling facts it learned in the previous "session"
5. Demonstrates consolidation of a near-duplicate memory
6. Prints memory store statistics

### Testing persistence manually

```python
from memory_agent import MemoryAgent

agent = MemoryAgent()
agent.remember("My cat is named Luna and she loves tuna.")
# Kill Python. Restart. Start a new agent.

agent2 = MemoryAgent()
agent2.chat("Do you know anything about my pets?")
# Agent will recall Luna.
```

---

## Files

```
project_03_longterm_memory/
├── memory_agent.py   — complete implementation
├── memories.db       — auto-created SQLite file (gitignored)
├── requirements.txt
└── README.md
```

Add `memories.db` to `.gitignore` if you don't want your personal memories committed to version control.
