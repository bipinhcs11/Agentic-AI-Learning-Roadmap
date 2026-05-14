# Project 06 — Full Platform (Capstone) 🏆

> **Week 16 · Phase 4 · Build Your Own Agent Framework**

## What You're Building

The **final project** — combine everything from all 4 phases into
a complete local AI platform:

```
┌─────────────────────────────────────────────────┐
│            Your Local AI Platform               │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Web UI  │  │  Agent   │  │  Memory  │      │
│  │Streamlit │→ │ (ReAct)  │→ │  (JSON)  │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                     ↓                           │
│              ┌──────────┐                       │
│              │  Ollama  │                       │
│              │gemma3:4b │                       │
│              └──────────┘                       │
└─────────────────────────────────────────────────┘
```

## What You've Built Across 16 Weeks

| Phase | What You Learned |
|-------|-----------------|
| Phase 1 — Foundation | Python, APIs, Ollama setup |
| Phase 2 — RAG | Embeddings, vector search, document Q&A |
| Phase 3 — Agentic Stack | Tools, memory, APIs, evaluation |
| Phase 4 — Framework | Build your own platform from scratch |

## How to Run the Full Platform

```bash
# 1. Start Ollama
ollama serve

# 2. Activate environment
source ~/Documents/my-ai-project/ai-env/bin/activate

# 3. Run the platform (Streamlit UI + Agent backend)
python full_platform.py

# OR run just the web UI:
streamlit run streamlit_ui.py  # from project_04
```

## Congratulations! 🎉

You've gone from "what is AI?" to building your own:
- RAG system
- Agent with tools
- REST API server
- Web UI
- Custom agent framework

That's a real portfolio of AI engineering skills!

## Status

✅ Full journey complete — Week 16!
