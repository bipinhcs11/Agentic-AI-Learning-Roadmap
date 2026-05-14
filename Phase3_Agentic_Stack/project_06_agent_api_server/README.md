# Project 06 — Agent API Server 🚀

> **Week 12 · Phase 3 · Agentic Stack**

## What You'll Learn

How to wrap your AI agent in a **FastAPI web server** — so any app,
browser, or service can talk to it over HTTP. This is how real AI products are built.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:4b` is pulled
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
cd ~/Documents/"Agentic AI learning Roadmap"/Phase3_Agentic_Stack/project_06_agent_api_server

# Start the API server
python agent_api_server.py
```

**Then open your browser:**
```
http://localhost:8000/docs
```
This opens the Swagger UI — an interactive page where you can test every endpoint.

---

## API Endpoints

| Method | Endpoint | What It Does |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message, get a reply |
| `GET` | `/history/{session_id}` | Get conversation history |
| `DELETE` | `/history/{session_id}` | Clear a session |
| `GET` | `/sessions` | List all active sessions |
| `GET` | `/health` | Check server status |
| `GET` | `/docs` | Interactive API documentation |

---

## Test It

**Option A — Browser (easiest):**
1. Go to `http://localhost:8000/docs`
2. Click on `POST /chat` → `Try it out`
3. Paste this in the body and click Execute:
```json
{"message": "What is 42 * 7?"}
```

**Option B — curl (new terminal):**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 42 * 7?"}'
```

**Option C — Test with session (keep conversation going):**
```bash
# First message
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "My name is Sunita", "session_id": "test1"}'

# Follow-up (same session_id)
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my name?", "session_id": "test1"}'
```

---

## Expected Terminal Output

```
============================================================
🚀 Agent API Server — Phase 3, Project 6
============================================================
Model:  gemma3:4b (local via Ollama)
Server: http://localhost:8000
Docs:   http://localhost:8000/docs  ← open this in browser!

INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     POST /chat → 200 OK
```

**JSON response from /chat:**
```json
{
  "reply": "42 × 7 = 294.",
  "session_id": "a3f8b2c1",
  "tool_used": "calculator",
  "timestamp": "2026-05-11T14:32:07"
}
```

---

## Verification Checklist

- [ ] Server starts and shows `Uvicorn running on http://0.0.0.0:8000`
- [ ] Browser at `http://localhost:8000/docs` shows Swagger UI with all endpoints
- [ ] `POST /chat` returns JSON with `reply`, `session_id`, `tool_used` fields
- [ ] Using the same `session_id` in two requests maintains conversation context
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /sessions` shows active sessions after chatting
- [ ] `Ctrl+C` stops the server cleanly

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Port 8000 already in use` | Change `PORT = 8000` to `PORT = 8005` in the script |
| `Connection refused` in browser | Server is not running — run `python agent_api_server.py` first |
| `500 Internal Server Error` | Ollama is not running — run `ollama serve` in Terminal 1 |
| `curl: command not found` | Use the browser at `http://localhost:8000/docs` instead |
| `ModuleNotFoundError: fastapi` | Run: `pip install fastapi uvicorn --break-system-packages` |

---

## Stop the Server

```bash
# In Terminal 2, press:
Ctrl + C
```

## Status

⏳ Ready to run — opens interactive API docs at http://localhost:8000/docs
