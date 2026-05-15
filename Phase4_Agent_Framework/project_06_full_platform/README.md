# Project 06 — Full Platform (Capstone) 🏆

> **Week 16 · Phase 4 · Build Your Own Agent Framework**

## What You're Building

The **final capstone** — combine everything from all 4 phases into
a complete local AI platform running on your Mac Mini.

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
│              │gemma3:27b│                       │
│              └──────────┘                       │
└─────────────────────────────────────────────────┘
```

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:27b` is pulled
- [ ] Virtual environment is active
- [ ] `fastapi`, `uvicorn`, `streamlit` installed (already in requirements.txt)

---

## How to Run — Step by Step

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2 — CLI mode (default, interactive chat):**
```bash
# Activate venv
source ~/Documents/my-ai-project/ai-env/bin/activate

# Navigate to project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase4_Agent_Framework/project_06_full_platform

# Run in CLI mode
python full_platform.py
```

**Terminal 2 — API server mode:**
```bash
# Run as a REST API on port 8003
python full_platform.py --server
```

**Terminal 2 — Web UI (from project 04):**
```bash
streamlit run ../project_04_streamlit_web_ui/streamlit_ui.py
# Opens at http://localhost:8501
```

---

## Test Inputs (CLI mode) — Try These

```
What is 256 * 16?
My name is Sunita, remember that
What is my name?
What time is it?
Save a note: I completed the full 16-week AI learning journey!
What notes do I have?
```

Type `quit` to exit.

---

## Test It (API server mode)

```bash
# Start with --server flag, then in another terminal:
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, who are you?"}'

curl http://localhost:8003/health

curl http://localhost:8003/sessions
```

---

## Expected Terminal Output (CLI mode)

```
============================================================
🏆 Full Platform — Phase 4, Project 6 (Capstone)
============================================================
Model:   gemma3:27b
Memory:  platform_memory.json
Log:     platform_log.jsonl
Mode:    CLI

You: What is 256 * 16?
[tool: calculator] 256*16 = 4096
Agent: 256 multiplied by 16 equals 4,096.

You: My name is Sunita, remember that
[memory saved: user_name = Sunita]
Agent: Got it! I'll remember your name is Sunita.

You: What is my name?
Agent: Your name is Sunita — I have it saved in memory.
```

---

## Files Created by This Project

- `platform_memory.json` — persistent memory across sessions
- `platform_log.jsonl` — full interaction log with timestamps

---

## Verification Checklist

- [ ] CLI mode starts and shows the platform header
- [ ] Math questions use the calculator tool automatically
- [ ] Saying "My name is X" gets saved and recalled later
- [ ] `platform_memory.json` is created in the project folder
- [ ] `platform_log.jsonl` is created and grows with each interaction
- [ ] `--server` flag starts FastAPI on port 8003 with working `/chat` endpoint
- [ ] `quit` exits cleanly

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Connection refused` | Ollama is not running — run `ollama serve` |
| `Port 8003 already in use` | Change `PORT = 8003` to `PORT = 8007` in the script |
| Memory not persisting | Check write permission in project folder |
| `ModuleNotFoundError: streamlit` | Run: `pip install streamlit --break-system-packages` |

---

## What You've Built Across 16 Weeks

| Phase | What You Learned |
|-------|-----------------|
| Phase 1 — Foundation | Python, APIs, Ollama setup, first chat agent |
| Phase 2 — RAG | Embeddings, vector search, document Q&A |
| Phase 3 — Agentic Stack | Tools, memory, web scraping, APIs, evaluation |
| Phase 4 — Framework | Inference server, OpenAI-compatible API, web UI, custom framework |

---

## Congratulations! 🎉

You've gone from "what is AI?" to building your own:
- RAG system with semantic search
- Multi-tool agent with persistent memory
- REST API server and OpenAI-compatible layer
- Chat web UI running locally
- Custom agent framework from scratch

**That is a real portfolio of AI engineering skills.**

---

## Status

✅ Full journey complete — Week 16!
