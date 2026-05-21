# ═══════════════════════════════════════════════════════════════
# Project 04 — Observability Dashboard
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Adds Prometheus metrics to the FastAPI AI platform.
#   Prometheus scrapes /metrics every 15s.
#   Grafana reads from Prometheus and displays dashboards.
#
# KEY METRICS TRACKED:
#   - ai_requests_total        → how many LLM calls made
#   - ai_request_duration_seconds → how long each call took
#   - ai_tokens_estimated_total   → token throughput
#   - ai_errors_total             → error rate by type
#   - ai_active_requests          → concurrent requests gauge
#   - ai_ollama_up                → is Ollama reachable? (0 or 1)
#
# HOW TO RUN:
#   docker compose up --build
#   API:        http://localhost:8000
#   Metrics:    http://localhost:8000/metrics
#   Prometheus: http://localhost:9090
#   Grafana:    http://localhost:3000  (admin / admin123)
# ═══════════════════════════════════════════════════════════════

import json
import os
import time
from typing import AsyncGenerator, Optional

import httpx
import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
OLLAMA_URL    = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma3:4b")
APP_ENV       = os.getenv("APP_ENV", "production")

app = FastAPI(title="AI Platform API — Monitored", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# PROMETHEUS METRICS
#
# Counter   = only goes up (requests, errors, tokens)
# Histogram = tracks distribution (latency buckets)
# Gauge     = can go up and down (active requests, health status)
#
# Labels allow slicing: e.g. errors by model, latency by endpoint
# ─────────────────────────────────────────────────────────────

# Total LLM calls — sliced by model name and success/error
ai_requests_total = Counter(
    "ai_requests_total",
    "Total number of AI inference requests",
    ["model", "status"]   # labels
)

# How long each LLM call took — buckets in seconds
# Buckets chosen for AI: 1s, 2s, 5s, 10s, 30s, 60s, 120s
ai_request_duration = Histogram(
    "ai_request_duration_seconds",
    "LLM request duration in seconds",
    ["model"],
    buckets=[1, 2, 5, 10, 30, 60, 120]
)

# Estimated tokens (word count proxy — real tokenizer not needed)
ai_tokens_total = Counter(
    "ai_tokens_estimated_total",
    "Estimated total tokens generated",
    ["model"]
)

# Error breakdown by type
ai_errors_total = Counter(
    "ai_errors_total",
    "Total errors by category",
    ["error_type"]   # "timeout", "ollama_unavailable", "rate_limit", "internal"
)

# How many requests are currently being processed
ai_active_requests = Gauge(
    "ai_active_requests",
    "Number of AI requests currently being processed"
)

# Ollama health: 1=up, 0=down — Grafana shows red/green panel
ai_ollama_up = Gauge(
    "ai_ollama_up",
    "Whether Ollama is reachable (1=up, 0=down)"
)

# ─────────────────────────────────────────────────────────────
# Auto-instrument all HTTP endpoints (request count, latency, status codes)
# This adds standard HTTP metrics on top of our custom AI metrics
# ─────────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app)


# ═══════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    model: str
    duration_ms: float
    tokens_estimated: int


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check — also updates the Ollama availability gauge."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False

    # Update the gauge so Grafana reflects real-time Ollama status
    ai_ollama_up.set(1 if ollama_ok else 0)

    return {
        "status": "healthy" if ollama_ok else "degraded",
        "ollama": "connected" if ollama_ok else "unreachable",
        "environment": APP_ENV,
    }


@app.get("/models")
async def list_models():
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"models": models, "default": DEFAULT_MODEL}
    except Exception as e:
        ai_errors_total.labels(error_type="ollama_unavailable").inc()
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint — records full metrics for every call."""
    model = request.model or DEFAULT_MODEL

    # Track that we started a request
    ai_active_requests.inc()
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
        duration = time.time() - start
        tokens = len(text.split())

        # Record success metrics
        ai_requests_total.labels(model=model, status="success").inc()
        ai_request_duration.labels(model=model).observe(duration)
        ai_tokens_total.labels(model=model).inc(tokens)

        return ChatResponse(
            response=text,
            model=model,
            duration_ms=round(duration * 1000, 1),
            tokens_estimated=tokens,
        )

    except requests.Timeout:
        ai_errors_total.labels(error_type="timeout").inc()
        ai_requests_total.labels(model=model, status="error").inc()
        raise HTTPException(status_code=504, detail="Ollama request timed out")
    except Exception as e:
        ai_errors_total.labels(error_type="internal").inc()
        ai_requests_total.labels(model=model, status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always decrement active requests — even on error
        ai_active_requests.dec()


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming endpoint — metrics recorded at stream completion."""
    model = request.model or DEFAULT_MODEL
    ai_active_requests.inc()
    start = time.time()
    total_tokens = 0

    messages = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.message})

    async def generate() -> AsyncGenerator[str, None]:
        nonlocal total_tokens
        try:
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
                                    total_tokens += 1
                                    yield f"data: {json.dumps({'token': token})}\n\n"
                                if chunk.get("done"):
                                    duration = time.time() - start
                                    ai_requests_total.labels(model=model, status="success").inc()
                                    ai_request_duration.labels(model=model).observe(duration)
                                    ai_tokens_total.labels(model=model).inc(total_tokens)
                                    ai_active_requests.dec()
                                    yield "data: [DONE]\n\n"
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            ai_errors_total.labels(error_type="stream_error").inc()
            ai_requests_total.labels(model=model, status="error").inc()
            ai_active_requests.dec()

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/stats")
async def stats():
    return {
        "message": "See Prometheus at :9090 and Grafana at :3000 for full metrics",
        "metrics_endpoint": "/metrics",
        "default_model": DEFAULT_MODEL,
        "ollama_url": OLLAMA_URL,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
