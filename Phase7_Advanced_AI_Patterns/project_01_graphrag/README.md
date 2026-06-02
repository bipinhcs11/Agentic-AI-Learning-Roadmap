# Phase 7 — Project 1: GraphRAG (Graph-Augmented Retrieval)

## What is GraphRAG?

**Standard RAG** (Retrieval-Augmented Generation) splits your documents into chunks, embeds them as vectors, and at query time finds the chunks most similar to your question. It's powerful but flat — it only sees *local* text similarity.

**GraphRAG** adds a second layer: it extracts *entities* (companies, people, concepts) and *relationships* from those documents and stores them in a knowledge graph. At query time it finds matching entities *and then walks their graph connections* to pull in related facts — even from completely different documents.

```
STANDARD RAG
────────────
 Query → [embed] → similarity search → [chunk 1] [chunk 3] → LLM → Answer
                                           ↑           ↑
                                      (similar text, same document)


GRAPHRAG
────────
 Query → [embed] → similarity search → [OpenAI entity] ─────► LLM → Answer
                                              │ graph traversal        ↑
                                              ├─[COMPETES_WITH]──► [Anthropic entity]
                                              ├─[INVESTED_BY]───► [Microsoft entity]
                                              └─[CREATED]───────► [GPT-4 entity]
                                         (connected entities from multiple documents)
```

## Why Relationships Matter

Consider the question: **"Who competes with OpenAI?"**

- A standard RAG system returns chunks that *mention* OpenAI.  
  It may find "OpenAI is an AI safety company founded in 2015…" — but that chunk doesn't mention competitors.

- A GraphRAG system finds the OpenAI entity node, then **traverses `COMPETES_WITH` edges** to immediately surface Anthropic and Google DeepMind — even though those facts live in completely separate documents.

Another example: **"What have safety-focused AI companies built?"**

- Standard RAG needs a chunk that happens to contain both "safety" and "product names" in the same passage.
- GraphRAG finds `Anthropic --[CREATED]--> Claude` and `OpenAI --[CREATED]--> GPT-4` by combining the `SAFETY_FOCUS` attribute traversal with `CREATED` edges.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       graph_rag.py                              │
│                                                                 │
│  ┌──────────────────────┐     ┌───────────────────────────┐    │
│  │  DocumentGraphBuilder│     │    GraphRAGRetriever       │    │
│  │                      │     │                           │    │
│  │  add_document(text)  │     │  retrieve(query, top_k)   │    │
│  │    │                 │     │    │                      │    │
│  │    ├─ LLM extract    │     │    ├─ embed query         │    │
│  │    │   entities      │     │    ├─ cosine similarity   │    │
│  │    ├─ embed each     │────►│    ├─ top-k entities      │    │
│  │    │   entity        │     │    └─ 1-hop neighbors     │    │
│  │    └─ build DiGraph  │     │                           │    │
│  └──────────────────────┘     └─────────────┬─────────────┘    │
│                                             │                  │
│                              ┌──────────────▼──────────────┐   │
│                              │     GraphRAGPipeline         │   │
│                              │                              │   │
│                              │  query(question)             │   │
│                              │    │                         │   │
│                              │    ├─ retriever.retrieve()   │   │
│                              │    ├─ format context         │   │
│                              │    ├─ LLM generate answer    │   │
│                              │    └─ return {answer,        │   │
│                              │              entities_used,  │   │
│                              │              relationships}  │   │
│                              └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Concepts

| Concept | Description |
|---|---|
| **Entity extraction** | Using an LLM to identify named things (companies, people, products) in text and classify them |
| **Knowledge graph** | A directed graph where nodes are entities and edges are typed relationships (A COMPETES_WITH B) |
| **Graph traversal** | Walking edges from a matched node to find connected but not directly queried information |
| **Cosine similarity** | Measuring the angle between two embedding vectors — the smaller the angle, the more similar the meaning |
| **1-hop neighbor** | A node directly connected to a matched node by one edge (outgoing or incoming) |
| **Grounded generation** | Giving the LLM structured facts (entity + relationship triples) rather than raw text, reducing hallucination |

## Requirements

```bash
pip install networkx numpy openai
```

You also need [Ollama](https://ollama.com) running locally with:
```bash
ollama pull gemma3:4b          # reasoning model
ollama pull nomic-embed-text   # embedding model
```

## How to Run

```bash
cd "Phase7_Advanced_AI_Patterns/project_01_graphrag"
python graph_rag.py
```

The demo will:
1. Build a knowledge graph from 3 documents about OpenAI, Anthropic, and Google DeepMind
2. Display the graph structure (entities and relationships)
3. Answer 4 questions that require cross-document graph traversal
4. Show which entities and relationships were used to form each answer

## Expected Output

```
STEP 1: Building knowledge graph from documents …
  [Extract] Calling LLM to extract entities from doc 'doc_openai' …
  [Extract] Found 6 entities, 5 relationships
  [Embed]   Embedding entity: OpenAI
  ...

STEP 2: Knowledge Graph Structure
  [COMPANY] OpenAI
  [COMPANY] Anthropic
  [COMPANY] Google DeepMind
  ...
  OpenAI  --[COMPETES_WITH]-->  Anthropic
  Microsoft  --[INVESTED_IN]-->  OpenAI
  ...

STEP 3: Answering questions using GraphRAG
  Question 1: Who are the main competitors of OpenAI?
  [ANSWER] Based on the knowledge graph, OpenAI's main competitors are
  Anthropic (which competes directly via Claude) and Google DeepMind
  (which competes via Gemini) …
```

## What Makes This "Advanced"

- **Multi-document reasoning**: The graph connects facts across documents that vector search would treat as separate islands
- **Explicit relationship types**: The LLM knows *how* entities relate, not just that they're similar
- **Expandable context**: 1-hop traversal can become 2-hop, 3-hop, or community detection for richer context
- **Structured citations**: Every answer knows which entities and relationships it used — auditable reasoning
