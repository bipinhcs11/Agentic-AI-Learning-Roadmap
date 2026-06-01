"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                 PHASE 7 — PROJECT 1: GRAPH-AUGMENTED RETRIEVAL (GraphRAG)       ║
║                                                                                  ║
║  What this file does:                                                            ║
║    Standard RAG finds text chunks similar to your query. GraphRAG goes further   ║
║    — it first extracts *entities* (companies, people, concepts) and their        ║
║    *relationships* from your documents, stores them in a knowledge graph, and    ║
║    then at query-time traverses that graph to find not just what matches your     ║
║    question directly, but what is *connected* to those matches.                  ║
║                                                                                  ║
║    Example: "Who competes with OpenAI?" — a vector search returns chunks         ║
║    mentioning OpenAI. GraphRAG also walks to Anthropic, Google DeepMind,         ║
║    Mistral … because those nodes are linked by "COMPETES_WITH" edges.            ║
║                                                                                  ║
║  Architecture:                                                                   ║
║    DocumentGraphBuilder  → parse text → extract entities/rels → build DiGraph    ║
║    GraphRAGRetriever      → embed query → cosine-match entities → hop neighbors  ║
║    GraphRAGPipeline       → retriever + LLM → grounded, cited answer             ║
║                                                                                  ║
║  Dependencies: pip install networkx numpy openai                                 ║
║  Ollama models needed:                                                           ║
║    - gemma3:4b  (entity extraction + answer generation)                         ║
║    - nomic-embed-text  (embeddings)                                              ║
║                                                                                  ║
║  Author : Bipin Pradhan                                                          ║
║  Phase  : 7 — Advanced AI Patterns                                               ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────────────────────────────
# STDLIB IMPORTS
# ─────────────────────────────────────────────────────────────────────────────────
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────────
# THIRD-PARTY DEPENDENCY CHECK
# We do this early so users get a friendly message rather than a confusing
# ImportError deep in the program.
# ─────────────────────────────────────────────────────────────────────────────────
_missing: list[str] = []
try:
    import networkx as nx          # graph data structure and algorithms
except ImportError:
    _missing.append("networkx")

try:
    import numpy as np             # fast cosine-similarity math
except ImportError:
    _missing.append("numpy")

try:
    from openai import OpenAI      # Ollama exposes an OpenAI-compatible REST API
except ImportError:
    _missing.append("openai")

if _missing:
    print(f"\n[ERROR] Missing required packages: {', '.join(_missing)}")
    print(f"  Install with:  pip install {' '.join(_missing)}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────────
# OLLAMA CLIENT SETUP
# Ollama runs locally and exposes the same API surface as OpenAI. By pointing the
# OpenAI client at http://localhost:11434 we get the same SDK ergonomics without
# any cloud dependency. api_key is required by the SDK but ignored by Ollama.
# ─────────────────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# Model for text reasoning tasks (entity extraction, answer generation)
LLM_MODEL = "gemma3:4b"

# Dedicated embedding model — much smaller and faster than a chat model
EMBED_MODEL = "nomic-embed-text"

# The two clients are separate objects so it's always clear which is which.
llm_client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
embed_client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


# ─────────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# Python dataclasses give us clean, typed containers without boilerplate.
# ─────────────────────────────────────────────────────────────────────────────────

@dataclass
class Entity:
    """
    A node in the knowledge graph.

    name        — canonical label  (e.g., "OpenAI")
    entity_type — category          (e.g., "COMPANY", "PERSON", "CONCEPT")
    description — one-sentence fact about this entity from the source text
    doc_id      — which document this came from (for provenance)
    embedding   — vector representation of the description; used for similarity search
    """
    name: str
    entity_type: str
    description: str
    doc_id: str
    embedding: list[float] = field(default_factory=list)


@dataclass
class Relationship:
    """
    A directed edge in the knowledge graph.

    source   — entity name that is the *subject* of the relationship
    target   — entity name that is the *object*
    relation — label describing how source relates to target
                (e.g., "COMPETES_WITH", "FOUNDED_BY", "PARTNERED_WITH")
    doc_id   — provenance
    """
    source: str
    target: str
    relation: str
    doc_id: str


@dataclass
class RetrievalResult:
    """
    Everything the retriever hands back to the pipeline:
      matched_entities   — entities whose embeddings were closest to the query
      neighbor_entities  — 1-hop graph neighbors of the matched entities
      relationships      — all edges that touch the above entities
    """
    matched_entities: list[Entity]
    neighbor_entities: list[Entity]
    relationships: list[Relationship]


# ─────────────────────────────────────────────────────────────────────────────────
# SECTION 1 — DocumentGraphBuilder
# Responsible for:
#   1. Calling the LLM to extract structured entities/relationships from raw text
#   2. Storing those in a NetworkX directed graph
#   3. Embedding each entity's description for later similarity search
# ─────────────────────────────────────────────────────────────────────────────────

class DocumentGraphBuilder:
    """
    Converts raw text documents into a knowledge graph.

    Internally the graph is a NetworkX DiGraph where:
      - each node is keyed by entity name and stores an Entity object
      - each edge is keyed by (source, target) and stores a Relationship object

    A separate flat list (self.entities) is kept so we can iterate quickly over
    all entities during embedding and similarity search without graph traversal.
    """

    def __init__(self) -> None:
        # DiGraph = directed graph; edges have a direction (A → B ≠ B → A)
        self.graph: nx.DiGraph = nx.DiGraph()
        # Flat list for fast iteration during similarity search
        self.entities: list[Entity] = []

    # ── Private helpers ──────────────────────────────────────────────────────────

    def _extract_entities_and_relationships(
        self, text: str, doc_id: str
    ) -> tuple[list[Entity], list[Relationship]]:
        """
        Send the document text to the LLM and ask it to return structured JSON.

        Why JSON output? We need machine-readable data, not prose. Asking for a
        strict schema ("return ONLY valid JSON, no prose") makes parsing reliable.
        The schema we request:
          {
            "entities": [{"name": ..., "type": ..., "description": ...}, ...],
            "relationships": [{"source": ..., "target": ..., "relation": ...}, ...]
          }
        """
        prompt = f"""You are a knowledge extraction system. Read the text below and extract entities and their relationships.

Return ONLY valid JSON — no explanation, no markdown code fences — in exactly this structure:
{{
  "entities": [
    {{"name": "EntityName", "type": "COMPANY|PERSON|CONCEPT|PRODUCT|PLACE", "description": "one sentence fact"}}
  ],
  "relationships": [
    {{"source": "EntityA", "target": "EntityB", "relation": "RELATION_LABEL"}}
  ]
}}

Relationship labels should be short uppercase phrases like:
  FOUNDED_BY, COMPETES_WITH, PARTNERED_WITH, INVESTED_IN, CREATED, ACQUIRED, WORKS_AT, RESEARCHES

TEXT TO ANALYZE:
\"\"\"
{text}
\"\"\"

JSON output:"""

        print(f"  [Extract] Calling LLM to extract entities from doc '{doc_id}' …")
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,   # zero temperature = deterministic, factual extraction
        )

        raw = response.choices[0].message.content.strip()

        # ── Parse JSON defensively ────────────────────────────────────────────────
        # The LLM sometimes wraps its response in markdown ```json ... ``` fences.
        # Strip those if present before parsing.
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Drop first line (```json or ```) and last line (```)
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"  [WARN] JSON parse failed for doc '{doc_id}': {exc}")
            print(f"  [WARN] Raw output was: {raw[:300]}")
            # Gracefully degrade — return empty rather than crash the whole run
            return [], []

        # Convert raw dicts into typed dataclass instances
        entities: list[Entity] = []
        for e in data.get("entities", []):
            if "name" in e and "description" in e:
                entities.append(Entity(
                    name=e["name"],
                    entity_type=e.get("type", "UNKNOWN"),
                    description=e["description"],
                    doc_id=doc_id,
                ))

        relationships: list[Relationship] = []
        for r in data.get("relationships", []):
            if "source" in r and "target" in r and "relation" in r:
                relationships.append(Relationship(
                    source=r["source"],
                    target=r["target"],
                    relation=r["relation"],
                    doc_id=doc_id,
                ))

        print(f"  [Extract] Found {len(entities)} entities, {len(relationships)} relationships")
        return entities, relationships

    def _embed_entity(self, entity: Entity) -> list[float]:
        """
        Generate a vector embedding for an entity's description.

        We embed the *description* (not just the name) so that semantically
        similar entities cluster together even if their names are different.
        E.g., "large language model" and "LLM" would map to nearby vectors.
        """
        response = embed_client.embeddings.create(
            model=EMBED_MODEL,
            input=entity.description,
        )
        return response.data[0].embedding

    # ── Public API ───────────────────────────────────────────────────────────────

    def add_document(self, text: str, doc_id: str) -> None:
        """
        Full pipeline for one document:
          1. Extract entities + relationships via LLM
          2. Add entities as graph nodes (merging duplicates by name)
          3. Add relationships as directed edges
          4. Embed each new entity's description
        """
        print(f"\n[Builder] Processing document: {doc_id}")

        entities, relationships = self._extract_entities_and_relationships(text, doc_id)

        # ── Add nodes ─────────────────────────────────────────────────────────────
        # We use entity.name as the node key. If two documents mention "OpenAI",
        # we prefer the first description rather than overwriting (could be smarter,
        # but keeps the demo simple).
        for entity in entities:
            if entity.name not in self.graph:
                # Embed before adding to graph so we fail fast on embedding errors
                print(f"  [Embed]   Embedding entity: {entity.name}")
                entity.embedding = self._embed_entity(entity)

                # Store entity object as node attribute
                self.graph.add_node(entity.name, entity=entity)
                self.entities.append(entity)
            else:
                print(f"  [Skip]    Entity already in graph: {entity.name}")

        # ── Add edges ─────────────────────────────────────────────────────────────
        for rel in relationships:
            # Only add edge if both endpoints exist as nodes
            if rel.source in self.graph and rel.target in self.graph:
                self.graph.add_edge(
                    rel.source,
                    rel.target,
                    relationship=rel,
                )
                print(f"  [Edge]    {rel.source} --[{rel.relation}]--> {rel.target}")
            else:
                print(f"  [Skip]    Edge skipped (unknown node): {rel.source} → {rel.target}")

        print(f"[Builder] Graph now has {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")


# ─────────────────────────────────────────────────────────────────────────────────
# SECTION 2 — GraphRAGRetriever
# Responsible for:
#   1. Embedding the user's query
#   2. Finding the top-k most similar entities (via cosine similarity)
#   3. Expanding context by walking 1-hop neighbors in the graph
#   4. Collecting all relevant relationships
# ─────────────────────────────────────────────────────────────────────────────────

class GraphRAGRetriever:
    """
    Two-phase retrieval: vector similarity → graph traversal.

    Phase 1 (vector): Embed the query and compare against all entity embeddings.
                      This finds entities that are *semantically close* to the query.

    Phase 2 (graph):  Walk the edges of the matched entities to pull in neighbors.
                      This finds entities that are *structurally connected* to what
                      matched, even if they would not have ranked highly on their own.

    The combination gives richer, more connected context to the LLM.
    """

    def __init__(self, builder: DocumentGraphBuilder) -> None:
        self.builder = builder

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """
        Cosine similarity measures the *angle* between two vectors.
        Value of 1.0 = same direction (most similar)
        Value of 0.0 = perpendicular (unrelated)
        Value of -1.0 = opposite direction

        We use numpy for vectorized math — much faster than a pure-Python loop
        when you have many entities.
        """
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _embed_query(self, query: str) -> list[float]:
        """Embed the user's question using the same model used for entities."""
        response = embed_client.embeddings.create(
            model=EMBED_MODEL,
            input=query,
        )
        return response.data[0].embedding

    def retrieve(self, query: str, top_k: int = 3) -> RetrievalResult:
        """
        Main retrieval entry-point.

        Steps:
          1. Embed the query
          2. Score every entity by cosine similarity to the query embedding
          3. Take the top_k highest-scoring entities
          4. Collect their 1-hop successors (outgoing edges) and predecessors
             (incoming edges) — these are the "neighbors"
          5. Gather all relationship edges that touch our entity set
          6. Return a RetrievalResult with matched + neighbors + relationships
        """
        if not self.builder.entities:
            print("[Retriever] No entities in graph yet!")
            return RetrievalResult([], [], [])

        print(f"\n[Retriever] Embedding query: '{query}'")
        query_vec = self._embed_query(query)

        # ── Phase 1: cosine similarity ranking ───────────────────────────────────
        scored: list[tuple[float, Entity]] = []
        for entity in self.builder.entities:
            if entity.embedding:
                score = self._cosine_similarity(query_vec, entity.embedding)
                scored.append((score, entity))

        # Sort descending by score; take top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        matched = [entity for _, entity in scored[:top_k]]

        print(f"[Retriever] Top {top_k} matched entities:")
        for score, entity in scored[:top_k]:
            print(f"  {score:.3f}  {entity.name}  ({entity.entity_type})")

        # ── Phase 2: 1-hop graph traversal ───────────────────────────────────────
        # successors(n) = nodes that n points TO  (n → neighbor)
        # predecessors(n) = nodes that point to n (neighbor → n)
        matched_names = {e.name for e in matched}
        neighbor_names: set[str] = set()

        graph = self.builder.graph
        for entity in matched:
            if entity.name in graph:
                # Outgoing edges: who does this entity relate TO?
                for neighbor in graph.successors(entity.name):
                    if neighbor not in matched_names:
                        neighbor_names.add(neighbor)
                # Incoming edges: who relates TO this entity?
                for neighbor in graph.predecessors(entity.name):
                    if neighbor not in matched_names:
                        neighbor_names.add(neighbor)

        # Resolve neighbor names to Entity objects
        neighbor_entities: list[Entity] = [
            graph.nodes[name]["entity"]
            for name in neighbor_names
            if name in graph.nodes
        ]

        print(f"[Retriever] Expanded to {len(neighbor_entities)} neighbor entities: "
              f"{[e.name for e in neighbor_entities]}")

        # ── Collect relationships that touch any entity in our set ────────────────
        all_names = matched_names | neighbor_names
        relationships: list[Relationship] = []
        for src, tgt, data in graph.edges(data=True):
            if src in all_names or tgt in all_names:
                if "relationship" in data:
                    relationships.append(data["relationship"])

        return RetrievalResult(
            matched_entities=matched,
            neighbor_entities=neighbor_entities,
            relationships=relationships,
        )


# ─────────────────────────────────────────────────────────────────────────────────
# SECTION 3 — GraphRAGPipeline
# Responsible for:
#   1. Calling the retriever
#   2. Formatting the retrieved context into a grounded prompt
#   3. Calling the LLM for a final answer
#   4. Returning a structured result with citations
# ─────────────────────────────────────────────────────────────────────────────────

class GraphRAGPipeline:
    """
    End-to-end pipeline: question → retrieval → LLM → grounded answer.

    The key idea is that we *don't* just hand raw text chunks to the LLM.
    Instead we provide:
      - entity facts (name, type, description)
      - explicit relationship triples (A --[REL]--> B)

    This structured context is easier for the LLM to reason over than a
    wall of retrieved text paragraphs.
    """

    def __init__(self, builder: DocumentGraphBuilder) -> None:
        self.retriever = GraphRAGRetriever(builder)

    def _format_context(self, result: RetrievalResult) -> str:
        """
        Convert RetrievalResult into a readable context block for the LLM prompt.
        """
        lines: list[str] = []

        if result.matched_entities:
            lines.append("=== DIRECTLY MATCHED ENTITIES ===")
            for e in result.matched_entities:
                lines.append(f"• [{e.entity_type}] {e.name}: {e.description}")

        if result.neighbor_entities:
            lines.append("\n=== CONNECTED ENTITIES (graph neighbors) ===")
            for e in result.neighbor_entities:
                lines.append(f"• [{e.entity_type}] {e.name}: {e.description}")

        if result.relationships:
            lines.append("\n=== RELATIONSHIPS ===")
            seen: set[str] = set()
            for r in result.relationships:
                key = f"{r.source}|{r.relation}|{r.target}"
                if key not in seen:
                    lines.append(f"• {r.source}  --[{r.relation}]-->  {r.target}")
                    seen.add(key)

        return "\n".join(lines)

    def query(self, question: str, top_k: int = 3) -> dict[str, Any]:
        """
        Full GraphRAG query:
          1. Retrieve context from the knowledge graph
          2. Build a grounded prompt
          3. Generate an answer
          4. Return structured result

        Returns a dict with:
          answer            — the LLM's response
          entities_used     — names of entities that informed the answer
          relationships_found — list of (source, relation, target) triples
        """
        print(f"\n{'═'*70}")
        print(f"QUERY: {question}")
        print('═'*70)

        # ── Retrieval ─────────────────────────────────────────────────────────────
        retrieval = self.retriever.retrieve(question, top_k=top_k)
        context = self._format_context(retrieval)

        # ── Prompt construction ───────────────────────────────────────────────────
        # We explicitly instruct the LLM to:
        #   a) use only the provided context (prevents hallucination)
        #   b) cite which entities it used
        prompt = f"""You are a knowledge graph assistant. Answer the question using ONLY the facts provided in the context below.

CONTEXT FROM KNOWLEDGE GRAPH:
{context}

QUESTION: {question}

Instructions:
- Answer based only on the provided context
- Mention which entities you used (cite by name)
- If the context doesn't contain enough information, say so honestly
- Be concise but complete

ANSWER:"""

        print(f"\n[Pipeline] Generating answer with {LLM_MODEL} …")
        response = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,   # slight creativity for natural language, low for factuality
        )

        answer = response.choices[0].message.content.strip()

        # ── Build structured return value ─────────────────────────────────────────
        all_entities = retrieval.matched_entities + retrieval.neighbor_entities
        entities_used = [e.name for e in all_entities]
        relationships_found = [
            {"source": r.source, "relation": r.relation, "target": r.target}
            for r in retrieval.relationships
        ]

        return {
            "answer": answer,
            "entities_used": entities_used,
            "relationships_found": relationships_found,
        }


# ─────────────────────────────────────────────────────────────────────────────────
# SECTION 4 — SAMPLE DATA
# Three documents about AI companies. Notice that:
#   - Doc 1 establishes OpenAI and GPT-4
#   - Doc 2 establishes Anthropic and Claude, and links them to OpenAI
#   - Doc 3 establishes Google DeepMind and Gemini, and links to both others
#
# Questions that require multi-document graph traversal:
#   "Who competes with OpenAI?" — needs cross-doc edges
#   "What models have safety-focused companies built?" — needs COMPETES_WITH + CREATED
# ─────────────────────────────────────────────────────────────────────────────────

SAMPLE_DOCUMENTS = {
    "doc_openai": """
OpenAI is an American AI safety company and research laboratory founded in 2015 by
Sam Altman, Elon Musk, Greg Brockman, Ilya Sutskever, and others. The company is
headquartered in San Francisco. OpenAI created GPT-4, one of the most capable large
language models available. GPT-4 powers ChatGPT, OpenAI's widely used conversational AI
product. Microsoft has invested over $13 billion in OpenAI and deeply integrates OpenAI
models into its Azure cloud platform and Office products. OpenAI's mission is to ensure
that artificial general intelligence benefits all of humanity.
""",

    "doc_anthropic": """
Anthropic is an AI safety company founded in 2021 by Dario Amodei, Daniela Amodei, and
several colleagues who previously worked at OpenAI. Anthropic is headquartered in San
Francisco and competes directly with OpenAI in the large language model market. Anthropic
created Claude, a family of AI assistants designed with Constitutional AI techniques that
emphasize safety and harmlessness. Google has invested heavily in Anthropic, making it a
strategic partner. Amazon Web Services also invested in Anthropic and distributes Claude
models through its Bedrock platform. Anthropic's research focuses on AI interpretability
and alignment.
""",

    "doc_deepmind": """
Google DeepMind is an AI research laboratory owned by Alphabet, Google's parent company.
It was formed by the merger of Google Brain and DeepMind in 2023. Google DeepMind created
Gemini, a multimodal large language model that competes with GPT-4 and Claude. DeepMind
was originally a London-based AI startup acquired by Google in 2014. Demis Hassabis
co-founded DeepMind and now leads Google DeepMind as CEO. Google DeepMind is known for
AlphaFold, a groundbreaking system that predicted the 3D structure of nearly all known
proteins. Google DeepMind competes directly with both OpenAI and Anthropic in the
frontier AI model market. Microsoft, through its OpenAI partnership, is considered a key
competitor to Google in the AI platform space.
""",
}

DEMO_QUESTIONS = [
    "Who are the main competitors of OpenAI?",
    "Which companies have invested in AI research organizations?",
    "What AI models have been created by safety-focused companies?",
    "Who founded Anthropic and what is their background?",
]


# ─────────────────────────────────────────────────────────────────────────────────
# SECTION 5 — MAIN DEMO
# ─────────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║              Phase 7 — Project 1: GraphRAG Demo                     ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("GraphRAG combines vector similarity search with knowledge graph traversal.")
    print("Standard RAG finds similar text chunks. GraphRAG also finds *connected* facts.")
    print()

    # ── Step 1: Build the knowledge graph ─────────────────────────────────────────
    print("━"*70)
    print("STEP 1: Building knowledge graph from documents …")
    print("━"*70)
    builder = DocumentGraphBuilder()

    for doc_id, text in SAMPLE_DOCUMENTS.items():
        builder.add_document(text=text.strip(), doc_id=doc_id)
        time.sleep(0.5)   # slight pause to avoid hammering the local Ollama server

    print(f"\n[Summary] Final graph: {builder.graph.number_of_nodes()} entities, "
          f"{builder.graph.number_of_edges()} relationships")

    # ── Step 2: Show the graph structure ──────────────────────────────────────────
    print("\n" + "━"*70)
    print("STEP 2: Knowledge Graph Structure")
    print("━"*70)
    print("\nEntities in graph:")
    for name, data in builder.graph.nodes(data=True):
        entity = data.get("entity")
        if entity:
            print(f"  [{entity.entity_type}] {entity.name}")

    print("\nRelationships in graph:")
    for src, tgt, data in builder.graph.edges(data=True):
        rel = data.get("relationship")
        if rel:
            print(f"  {src}  --[{rel.relation}]-->  {tgt}")

    # ── Step 3: Run demo queries ───────────────────────────────────────────────────
    print("\n" + "━"*70)
    print("STEP 3: Answering questions using GraphRAG")
    print("━"*70)

    pipeline = GraphRAGPipeline(builder)

    for i, question in enumerate(DEMO_QUESTIONS, 1):
        print(f"\n{'─'*70}")
        print(f"Question {i}/{len(DEMO_QUESTIONS)}")
        result = pipeline.query(question)

        print(f"\n[ANSWER]")
        print(result["answer"])

        print(f"\n[Entities used in context]: {', '.join(result['entities_used'])}")
        print(f"[Relationships found]: {len(result['relationships_found'])} edges")
        for rel in result["relationships_found"][:5]:   # show up to 5
            print(f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}")

        if i < len(DEMO_QUESTIONS):
            print("\nPress Enter to continue to next question (or Ctrl+C to stop) …")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                break

    print(f"\n{'═'*70}")
    print("GraphRAG demo complete.")
    print("Key insight: by traversing graph relationships, the system found connections")
    print("across documents that pure vector similarity would have missed.")
    print("═"*70)


if __name__ == "__main__":
    main()
