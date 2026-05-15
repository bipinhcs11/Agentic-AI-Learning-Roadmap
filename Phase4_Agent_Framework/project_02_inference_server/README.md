# Project 02 — Inference Server 🖥️

> **Week 13 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build your own **FastAPI inference server** that wraps Ollama and adds
streaming, logging, rate limiting, and request tracking.
This is exactly what commercial providers like OpenAI and Anthropic do at scale.

---

## Concept: What Is an Inference Server?

```
Your App → [Inference Server] → Ollama → gemma3:27b
                ↑
         - Request logging
         - Rate limiting (30 req/min)
         - Streaming support
         - Usage tracking
```

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:27b` is pulled
- [ ] Virtual environment is active
- [ ] `fastapi` and `uvicorn` installed (already in requirements.txt)

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
cd ~/Documents/"Agentic AI learning Roadmap"/Phase4_Agent_Framework/project_02_inference_server

# Start the inference server (port 8001)
python inference_server.py
```

**Then test in Terminal 3:**
```bash
# Non-streaming request
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Python?", "stream": false}'

# Chat endpoint
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'

# Check usage stats
curl http://localhost:8001/stats

# View request logs
curl http://localhost:8001/logs

# List available models
curl http://localhost:8001/models
```

---

## API Endpoints

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/generate` | Generate text (streaming or not) |
| `POST` | `/chat` | Multi-turn chat |
| `GET` | `/stats` | Request count, avg response time |
| `GET` | `/logs` | Last N request logs |
| `GET` | `/models` | Available Ollama models |
| `GET` | `/health` | Server health check |

---

## Expected Terminal Output

```
============================================================
🖥️  Inference Server — Phase 4, Project 2
============================================================
Model:  gemma3:27b
Port:   8001
Rate limit: 30 requests/minute
Logging to: inference_log.jsonl

INFO:     Started server process [23456]
INFO:     Uvicorn running on http://0.0.0.0:8001

POST /generate → 200 OK (4.1s)
POST /chat     → 200 OK (3.8s)
```

**Response from `/generate`:**
```json
{
  "response": "Python is a high-level programming language...",
  "model": "gemma3:27b",
  "duration_seconds": 4.1,
  "prompt_tokens": 8
}
```

---

## Verification Checklist

- [ ] Server starts and shows `Uvicorn running on http://0.0.0.0:8001`
- [ ] `POST /generate` returns JSON with `response` field
- [ ] `GET /stats` shows request count increasing with each call
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `inference_log.jsonl` file is created in the project folder
- [ ] `Ctrl+C` stops the server cleanly

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Port 8001 already in use` | Change `PORT = 8001` to `PORT = 8005` in the script |
| `500 Internal Server Error` | Ollama is not running — start `ollama serve` |
| `429 Too Many Requests` | Rate limit hit — wait 60 seconds and retry |
| `ModuleNotFoundError: fastapi` | Run: `pip install fastapi uvicorn --break-system-packages` |

---

## Status

⏳ Ready to run — port 8001
