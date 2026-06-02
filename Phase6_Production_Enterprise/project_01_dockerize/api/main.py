# ═══════════════════════════════════════════════════════════════
# Phase 6 — Production API (Dockerized)
# Clean FastAPI app that connects to Ollama on the host machine
# ═══════════════════════════════════════════════════════════════
#
# KEY DOCKER CONCEPT:
#   Inside a container, "localhost" = the container itself.
#   To reach Ollama running on your Mac, use:
#     host.docker.internal   (Mac/Windows Docker Desktop)
#
#   Set via environment variable OLLAMA_URL so we can override
#   it per environment (local dev, staging, production).
# ═══════════════════════════════════════════════════════════════

import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import AsyncGenerator, Optional

import httpx
import requests
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────
# Config — pulled from environment variables
# Defaults work for local dev; override in docker-compose.yml
# ─────────────────────────────────────────────────────────────

OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL  = os.getenv("DEFAULT_MODEL", "gemma3:4b")
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "30"))
APP_ENV        = os.getenv("APP_ENV", "development")
CLOUD_MODE     = os.getenv("CLOUD_MODE", "false").lower() == "true"

app = FastAPI(
    title="AI Platform API",
    description="Production-ready AI inference API — Phase 6",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# All routes live on this router so they can be mounted at both
# / (for ALB internal health checks) and /api (public external access).
router = APIRouter()

# Allow the Streamlit UI container to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production (Phase 6 Project 2)
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory rate tracker (swap for Redis in production)
rate_tracker: dict = defaultdict(deque)

stats = {
    "total_requests": 0,
    "total_errors": 0,
    "start_time": datetime.now().isoformat(),
    "environment": APP_ENV,
}


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    stream: bool = False
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    duration_ms: float
    tokens_estimated: int


# ═══════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════

def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window = rate_tracker[client_ip]
    # Drop timestamps older than 60s
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_RPM:
        return False
    window.append(now)
    return True


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Health check — used by Docker and load balancers."""
    if CLOUD_MODE:
        return {
            "status": "healthy",
            "ollama": "n/a (cloud mode)",
            "ollama_url": OLLAMA_URL,
            "environment": APP_ENV,
            "uptime_since": stats["start_time"],
        }

    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False

    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama": "connected" if ollama_ok else "unreachable",
        "ollama_url": OLLAMA_URL,
        "environment": APP_ENV,
        "uptime_since": stats["start_time"],
    }


@router.get("/models")
async def list_models():
    """List all models available in Ollama."""
    if CLOUD_MODE:
        return {"models": [DEFAULT_MODEL], "default": DEFAULT_MODEL, "note": "Cloud mode — configure a hosted LLM for inference"}

    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"models": models, "default": DEFAULT_MODEL}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Ollama: {e}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Standard (non-streaming) chat endpoint."""
    client_ip = req.client.host

    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    if CLOUD_MODE:
        return ChatResponse(
            response="Cloud mode active — Ollama is not available in AWS. Configure a hosted LLM (OpenAI, Bedrock, Claude API) to enable inference.",
            model=DEFAULT_MODEL,
            duration_ms=0,
            tokens_estimated=0,
        )

    model = request.model or DEFAULT_MODEL
    stats["total_requests"] += 1
    start = time.time()

    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["message"]["content"]
        duration_ms = (time.time() - start) * 1000

        return ChatResponse(
            response=text,
            model=model,
            duration_ms=round(duration_ms, 1),
            tokens_estimated=len(text.split()),
        )
    except Exception as e:
        stats["total_errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """Streaming chat — returns Server-Sent Events."""
    client_ip = req.client.host

    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    if CLOUD_MODE:
        async def cloud_stub():
            yield 'data: {"token": "Cloud mode active — Ollama unavailable in AWS."}\n\n'
            yield "data: [DONE]\n\n"
        return StreamingResponse(cloud_stub(), media_type="text/event-stream")

    model = request.model or DEFAULT_MODEL
    stats["total_requests"] += 1

    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})

    async def generate() -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": True},
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if chunk.get("done"):
                                yield "data: [DONE]\n\n"
                        except json.JSONDecodeError:
                            continue

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/stats")
async def get_stats():
    """Usage statistics."""
    return {**stats, "rate_limit_rpm": RATE_LIMIT_RPM}


# Mount routes at both / (ALB health checks) and /api (public external access)
app.include_router(router)
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=APP_ENV == "development")
