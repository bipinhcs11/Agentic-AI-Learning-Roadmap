# Phase 2 — RAG Projects 🔄

> **Goal:** Build 10 hands-on RAG projects · Weeks 3–6 · **In Progress**

## What is RAG?

**Retrieval-Augmented Generation** — Give your LLM access to your own documents without retraining.

```
User question → Embed question → Search vector DB → Retrieve chunks
→ Build prompt (context + question) → Gemma3 generates answer
```

## Setup

```bash
source ai-env/bin/activate
pip install chromadb openai numpy  # core RAG stack (no PyTorch needed)
ollama pull nomic-embed-text       # embedding model (~274MB)
```

## 📂 Projects

| # | Project | Concepts | Difficulty | Status |
|---|---------|----------|------------|--------|
| [01](./project_01_first_rag/) | First RAG from Scratch | Chunking, embeddings, cosine similarity, basic pipeline | ⭐ Beginner | ✅ Done |
| [02](./project_02_ibm_rag/) | IBM RAG — Production Patterns | Error handling, logging, evaluation | ⭐ Beginner+ | ⏳ Next |
| [03](./project_03_graphrag/) | GraphRAG Pipeline | Knowledge graphs, entity extraction | ⭐⭐ Intermediate | ⏳ |
| [04](./project_04_multi_doc_rag/) | Multi-Document RAG | Multiple sources, metadata filtering | ⭐⭐ Intermediate | ⏳ |
| [05](./project_05_agentic_rag/) | Agentic RAG | Autonomous agents, tool use | ⭐⭐ Intermediate+ | ⏳ |
| [06](./project_06_langchain_rag/) | LangChain RAG Agent | Production agent patterns | ⭐⭐ Intermediate+ | ⏳ |
| [07](./project_07_document_analysis/) | Document Analysis — LLM + PDF | PDF processing, document Q&A | ⭐ Beginner | ⏳ |
| [08](./project_08_multimodal_rag/) | Multimodal RAG | Text + image processing | ⭐⭐⭐ Advanced | ⏳ |
| [09](./project_09_research_agent/) | AI Research Agent | Web search, report generation | ⭐⭐⭐ Advanced | ⏳ |
| [10](./project_10_realtime_assistant/) | Real-Time Assistant | Streaming, FastAPI, live RAG | ⭐⭐⭐ Advanced | ⏳ |

## Key Concepts Learned

- **Chunking** — Splitting documents into retrieval-sized pieces with overlap
- **Embeddings** — Converting text to vectors that capture semantic meaning
- **Cosine Similarity** — Finding the most relevant chunks for a query
- **ChromaDB** — Persisting and querying a local vector database
- **Prompt Engineering** — Crafting prompts that use retrieved context effectively
