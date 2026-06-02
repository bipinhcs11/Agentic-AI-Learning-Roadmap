# Project 1 — First RAG System from Scratch ✅

> **Week 3 · Beginner · Status: Complete**

## What You'll Build

A complete RAG pipeline from scratch using pure Python — no LangChain abstractions — so you truly understand every step.

## Architecture

```
Documents → chunk_text() → embed via Ollama → numpy matrix
Query → embed via Ollama → cosine similarity → top-K chunks
Chunks + Query → Gemma3 via Ollama → Answer
```

## Key Design Decisions

| Choice | Why |
|--------|-----|
| Ollama for embeddings (not sentence-transformers) | No PyTorch = no OOM kill on 32GB M4 |
| numpy cosine similarity (not ChromaDB) | Lightweight, no background processes |
| gemma3:4b for this project | Saves RAM during learning; swap to 27b for production |
| in-memory store | Simple for learning; Project 2 adds persistence |

## Run It

```bash
# Prerequisites
ollama serve                    # Tab 1 — keep running
ollama pull nomic-embed-text    # one time

# Run
source ai-env/bin/activate
python project_01_first_rag/rag_from_scratch.py
```

## Files

```
project_01_first_rag/
├── README.md            ← this file
└── rag_from_scratch.py  ← complete RAG pipeline (~150 lines)
```

## What to Try

1. Run it with the sample documents — see how retrieval works
2. Replace `DOCUMENTS` with your own text
3. Try changing `TOP_K` from 3 to 1 or 5 — watch answer quality change
4. Change `LLM_MODEL` to `gemma3:27b` for higher quality answers (uses more RAM)

## What's Next → Project 2

Project 2 adds production patterns: persistent ChromaDB storage, error handling, evaluation metrics, and logging.
