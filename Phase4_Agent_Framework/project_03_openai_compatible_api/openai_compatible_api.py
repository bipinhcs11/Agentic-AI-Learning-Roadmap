# ═══════════════════════════════════════════════════════════════
# Project 03 — OpenAI-Compatible REST API
# Phase 4 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Builds an API that mirrors OpenAI's exact format.
#   Any code written for OpenAI will work with this server!
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python openai_compatible_api.py
#
# TEST WITH OPENAI CLIENT:
#   from openai import OpenAI
#   client = OpenAI(base_url="http://localhost:8002/v1", api_key="local")
#   response = client.chat.completions.create(
#       model="gemma3:4b",
#       messages=[{"role": "user", "content": "Hello!"}]
#   )
#   print(response.choices[0].message.content)
# ═══════════════════════════════════════════════════════════════

import time
import uuid
import requests
import uvicorn
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:4b"
PORT = 8002

app = FastAPI(
    title="OpenAI-Compatible Local API",
    description="Drop-in replacement for OpenAI API — uses local Ollama models",
    version="1.0.0",
)

# Allow cross-origin requests (needed for browser-based frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# OPENAI-COMPATIBLE DATA MODELS
# These match OpenAI's exact API structure
# ═══════════════════════════════════════════════════════════════

class Message(BaseModel):
    role: str   # "system", "user", or "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gemma3:4b",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is the capital of France?"}
                ],
                "temperature": 0.7
            }
        }


class EmbeddingRequest(BaseModel):
    model: str = "nomic-embed-text"
    input: str | List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "model": "nomic-embed-text",
                "input": "Hello, world!"
            }
        }


# ═══════════════════════════════════════════════════════════════
# HELPER: Build OpenAI-format response
# ═══════════════════════════════════════════════════════════════

def make_chat_response(content: str, model: str, prompt_tokens: int = 10, completion_tokens: int = 50) -> dict:
    """Create an OpenAI-format chat completion response."""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/v1/models")
def list_models():
    """
    List available models.
    Compatible with: openai.models.list()
    """
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = resp.json().get("models", [])

        return {
            "object": "list",
            "data": [
                {
                    "id": m.get("name"),
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "local-ollama",
                    "permission": [],
                    "root": m.get("name"),
                    "parent": None,
                }
                for m in models
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not reachable: {e}")


@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    """
    Chat completions endpoint — mirrors OpenAI's /v1/chat/completions exactly.
    Compatible with: openai.chat.completions.create(...)
    """
    # Convert to Ollama format
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": request.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                    "top_p": request.top_p,
                }
            },
            timeout=120
        )
        data = resp.json()

    except requests.ConnectionError:
        raise HTTPException(status_code=503,
                            detail="Ollama not running. Start with: ollama serve")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Extract response
    message = data.get("message", {})
    content = message.get("content", "")

    # Token counts from Ollama
    prompt_tokens = data.get("prompt_eval_count", 10)
    completion_tokens = data.get("eval_count", 50)

    return make_chat_response(content, request.model, prompt_tokens, completion_tokens)


@app.post("/v1/embeddings")
def create_embeddings(request: EmbeddingRequest):
    """
    Embeddings endpoint.
    Compatible with: openai.embeddings.create(...)
    """
    # Handle both string and list input
    inputs = request.input if isinstance(request.input, list) else [request.input]

    embeddings = []
    for i, text in enumerate(inputs):
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": request.model, "prompt": text},
                timeout=30
            )
            data = resp.json()
            embedding = data.get("embedding", [])
            embeddings.append({
                "object": "embedding",
                "embedding": embedding,
                "index": i
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    return {
        "object": "list",
        "data": embeddings,
        "model": request.model,
        "usage": {"prompt_tokens": sum(len(t.split()) for t in inputs), "total_tokens": sum(len(t.split()) for t in inputs)}
    }


@app.get("/v1/health")
@app.get("/health")
def health():
    """Health check."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/version", timeout=3)
        ollama_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "not running"

    return {
        "status": "ok",
        "ollama": ollama_status,
        "compatible_with": "OpenAI API v1",
        "base_url": f"http://localhost:{PORT}/v1",
    }


@app.get("/")
def root():
    return {
        "name": "OpenAI-Compatible Local API",
        "base_url": f"http://localhost:{PORT}/v1",
        "docs": f"http://localhost:{PORT}/docs",
        "usage": {
            "python": f"from openai import OpenAI; client = OpenAI(base_url='http://localhost:{PORT}/v1', api_key='local')",
        }
    }


# ── Demo script (run separately) ──────────────────────────────
DEMO_SCRIPT = '''
# Run this AFTER starting the server to test it:
# python demo_client.py

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8002/v1",
    api_key="local-key"  # any string works
)

print("Testing OpenAI-compatible API...")
print()

# Chat
response = client.chat.completions.create(
    model="gemma3:4b",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "What is 5 + 3? Answer in one line."}
    ]
)
print("Chat response:", response.choices[0].message.content)
print("Tokens used:", response.usage.total_tokens)
print()

# Models
models = client.models.list()
print("Available models:")
for m in models.data[:5]:
    print(f"  - {m.id}")
'''


# ═══════════════════════════════════════════════════════════════
# START SERVER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Write demo client
    demo_file = os.path.join(os.path.dirname(__file__), "demo_client.py")
    with open(demo_file, "w") as f:
        f.write(DEMO_SCRIPT)

    print("=" * 60)
    print("🔌 OpenAI-Compatible API — Phase 4, Project 3")
    print("=" * 60)
    print(f"Base URL: http://localhost:{PORT}/v1")
    print(f"Docs:     http://localhost:{PORT}/docs")
    print()
    print("Connect with OpenAI client:")
    print(f"  from openai import OpenAI")
    print(f"  client = OpenAI(base_url='http://localhost:{PORT}/v1', api_key='local')")
    print()
    print(f"Demo script created: {demo_file}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    import os
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
