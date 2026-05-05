# Phase 1 — Foundation ✅

> **Goal:** Get local AI running on Mac Mini M4 · Weeks 1–2 · **COMPLETE**

## What We Built

A fully operational local AI workstation — running Gemma3:27b at zero cost with complete privacy.

## ✅ Completed Steps

| Step | Task | Command |
|------|------|---------|
| 1 | Install Homebrew | `/bin/bash -c "$(curl -fsSL https://brew.sh)"` |
| 2 | Install Ollama | `brew install ollama` |
| 3 | Pull Gemma3 models | `ollama pull gemma3:27b && ollama pull gemma3:4b` |
| 4 | Pull embedding model | `ollama pull nomic-embed-text` |
| 5 | Install Python 3.11 | `brew install python@3.11` |
| 6 | Install VS Code | `brew install --cask visual-studio-code` |
| 7 | Create virtual env | `python3.11 -m venv ai-env` |
| 8 | Install AI libraries | `pip install -r requirements.txt` |
| 9 | Verify full stack | `python Phase1_Foundation/test_gemma3.py` |

## 🧪 Test Your Setup

```bash
# Make sure ollama serve is running in another tab, then:
source ai-env/bin/activate
python Phase1_Foundation/test_gemma3.py
```

Expected output:
```
Connecting to Ollama at http://localhost:11434 ...
--------------------------------------------------
An AI agent is a software entity that perceives its environment...
SUCCESS: Gemma3 is working via Ollama API!
```

## 📦 Libraries Installed

| Library | Version | Purpose |
|---------|---------|---------|
| openai | 2.33.0 | Ollama-compatible API client |
| langchain | 1.2.17 | LLM orchestration |
| fastapi | 0.136.1 | Web API framework |
| uvicorn | 0.46.0 | ASGI server |

## 💡 Daily Startup

```bash
# Tab 1 — keep running
ollama serve

# Tab 2 — your work tab
source ai-env/bin/activate
cd path/to/Agentic-AI-Learning-Roadmap
```
