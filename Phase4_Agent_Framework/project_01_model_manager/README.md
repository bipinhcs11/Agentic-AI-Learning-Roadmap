# Project 01 — Model Manager 📦

> **Week 13 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

How to programmatically manage your local AI models —
download, list, inspect, and delete them using the Ollama REST API.
This is exactly how tools like Open WebUI and LM Studio control models under the hood.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:27b` is pulled
- [ ] Virtual environment is active
- [ ] `requests` and `rich` installed (see Install step below)

---

## Install (one time only)

```bash
pip install requests rich --break-system-packages
```

---

## How to Run — Step by Step

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2:**
```bash
# Activate venv
source ~/Documents/my-ai-project/ai-env/bin/activate

# Navigate to project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase4_Agent_Framework/project_01_model_manager

# List all installed models
python model_manager.py list

# Show details about a model
python model_manager.py info gemma3:27b

# Quick test (sends a short prompt)
python model_manager.py test gemma3:27b

# Check Ollama server status
python model_manager.py status
```

---

## All Commands

| Command | What It Does |
|---------|-------------|
| `python model_manager.py list` | Show all installed models with size |
| `python model_manager.py info <model>` | Show full details (parameters, family, size) |
| `python model_manager.py pull <model>` | Download a model (streaming progress) |
| `python model_manager.py delete <model>` | Remove a model from disk |
| `python model_manager.py test <model>` | Send a quick test prompt |
| `python model_manager.py status` | Check if Ollama is running |

---

## Expected Terminal Output

```
============================================================
📦 Model Manager — Phase 4, Project 1
============================================================
Ollama API: http://localhost:11434

python model_manager.py list
┌─────────────────────┬──────────┬─────────────┐
│ Model               │ Size     │ Modified    │
├─────────────────────┼──────────┼─────────────┤
│ gemma3:27b          │ 17.2 GB  │ 2 days ago  │
│ nomic-embed-text    │ 274 MB   │ 5 days ago  │
└─────────────────────┴──────────┴─────────────┘

python model_manager.py test gemma3:27b
🤖 Test prompt: "Say hello in one sentence"
✅ Response: Hello! I'm Gemma, ready to assist you today.
⏱️  Response time: 3.2s
```

---

## Verification Checklist

- [ ] `python model_manager.py list` shows your installed models in a table
- [ ] `python model_manager.py info gemma3:27b` shows model parameters and family
- [ ] `python model_manager.py test gemma3:27b` gets a response back
- [ ] `python model_manager.py status` shows `✅ Ollama is running`
- [ ] Script exits cleanly with no Python errors

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Connection refused to localhost:11434` | Ollama is not running — run `ollama serve` first |
| `ModuleNotFoundError: rich` | Run: `pip install rich --break-system-packages` |
| `Model not found` on info/test | Use exact name from `list` output (e.g. `gemma3:27b`) |
| Table not showing colours | `rich` is optional — plain text output still works |

---

## Status

⏳ Ready to run — make sure `ollama serve` is running first
