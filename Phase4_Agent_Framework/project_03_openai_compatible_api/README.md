# Project 03 — OpenAI-Compatible API 🔌

> **Week 14 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build an API that is **100% compatible with the OpenAI Python client** —
meaning any app built for OpenAI can use your local model instead.

## Why This Is Powerful

```python
# This code normally talks to OpenAI's servers...
from openai import OpenAI
client = OpenAI(api_key="sk-...")

# Change 2 lines → now it talks to YOUR server!
client = OpenAI(base_url="http://localhost:8002/v1", api_key="local")
# Everything else stays the same!
```

This is exactly how Ollama's own `/v1` endpoint works.

## Endpoints (OpenAI-compatible)

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/chat/completions` | Chat (same as ChatGPT) |
| `GET /v1/models` | List available models |
| `POST /v1/embeddings` | Get text embeddings |

## Stack

- **FastAPI + Uvicorn** (already installed)
- **OpenAI Python SDK** (already installed)
- **Port 8002**

## How to Run

```bash
ollama serve
source ~/Documents/my-ai-project/ai-env/bin/activate
python openai_compatible_api.py
```

## Test with OpenAI client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8002/v1",
    api_key="local-key"
)

response = client.chat.completions.create(
    model="gemma3:4b",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Status

⏳ Ready to run — port 8002
