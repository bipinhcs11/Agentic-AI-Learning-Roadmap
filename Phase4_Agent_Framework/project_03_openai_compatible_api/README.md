# Project 03 — OpenAI-Compatible API 🔌

> **Week 14 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build an API that is **100% compatible with the OpenAI Python client** —
meaning any app built for OpenAI can instantly use your local model instead,
with just a 2-line change.

---

## Why This Is Powerful

```python
# Normally talks to OpenAI's servers...
from openai import OpenAI
client = OpenAI(api_key="sk-...")

# Change 2 lines → talks to YOUR local server!
client = OpenAI(base_url="http://localhost:8002/v1", api_key="local")
# Everything else stays exactly the same!
```

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:27b` is pulled
- [ ] `nomic-embed-text` is pulled (for `/v1/embeddings`)
- [ ] Virtual environment is active
- [ ] `fastapi`, `uvicorn`, `openai` installed (already in requirements.txt)

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
cd ~/Documents/"Agentic AI learning Roadmap"/Phase4_Agent_Framework/project_03_openai_compatible_api

# Start the API server (port 8002)
python openai_compatible_api.py
```

**Then test in Terminal 3:**
```bash
# List available models
curl http://localhost:8002/v1/models

# Chat completion
curl -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma3:27b", "messages": [{"role": "user", "content": "Say hello!"}]}'

# Get embeddings
curl -X POST http://localhost:8002/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "input": "Hello world"}'
```

**Or test with the OpenAI Python SDK:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8002/v1",
    api_key="local-key"
)

response = client.chat.completions.create(
    model="gemma3:27b",
    messages=[{"role": "user", "content": "What is 7 * 8?"}]
)
print(response.choices[0].message.content)
```

A `demo_client.py` file is also auto-created in this folder when the server starts.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/v1/chat/completions` | Chat (OpenAI format) |
| `GET` | `/v1/models` | List available models |
| `POST` | `/v1/embeddings` | Get text embeddings |
| `GET` | `/health` | Server health check |

---

## Expected Terminal Output

```
============================================================
🔌 OpenAI-Compatible API — Phase 4, Project 3
============================================================
Port:    8002
Endpoints:
  POST /v1/chat/completions
  GET  /v1/models
  POST /v1/embeddings

INFO:     Uvicorn running on http://0.0.0.0:8002

POST /v1/chat/completions → 200 OK (3.9s)
```

**Response from `/v1/chat/completions`:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "choices": [{
    "message": {"role": "assistant", "content": "7 × 8 = 56."},
    "finish_reason": "stop"
  }],
  "model": "gemma3:27b"
}
```

---

## Verification Checklist

- [ ] Server starts and shows `Uvicorn running on http://0.0.0.0:8002`
- [ ] `GET /v1/models` returns a list of your installed models
- [ ] `POST /v1/chat/completions` returns OpenAI-format JSON
- [ ] OpenAI Python SDK test script works with `base_url="http://localhost:8002/v1"`
- [ ] `demo_client.py` is auto-created in this project folder
- [ ] `GET /health` returns `{"status": "ok"}`

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Port 8002 already in use` | Change `PORT = 8002` to `PORT = 8006` in the script |
| `500` on `/v1/embeddings` | Pull the embedding model: `ollama pull nomic-embed-text` |
| `openai.APIConnectionError` | Make sure server is running before running the test script |
| `ModuleNotFoundError: openai` | Run: `pip install openai --break-system-packages` |

---

## Status

⏳ Ready to run — port 8002
