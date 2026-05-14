# ═══════════════════════════════════════════════════════════════
# Project 02 — Inference Server
# Phase 4 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Your own FastAPI server wrapping Ollama with streaming,
#   logging, stats, and rate limiting.
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python inference_server.py
#   4. Visit: http://localhost:8001/docs
# ═══════════════════════════════════════════════════════════════

import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional, AsyncGenerator

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:4b"
LOG_FILE = os.path.join(os.path.dirname(__file__), "inference_log.jsonl")
RATE_LIMIT_RPM = 30       # requests per minute
PORT = 8001

app = FastAPI(
    title="🖥️ Local Inference Server",
    description="Your own AI inference server — wraps Ollama with logging, streaming, and stats",
    version="1.0.0",
)

# ── Usage Tracking ─────────────────────────────────────────────
stats = {
    "total_requests": 0,
    "total_tokens": 0,
    "total_errors": 0,
    "start_time": datetime.now().isoformat(),
    "response_times": [],
}
# Rate limiter: stores timestamps of recent requests per IP
rate_tracker: dict = defaultdict(deque)


# ═══════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = DEFAULT_MODEL
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 512
    system: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Explain machine learning in 2 sentences.",
                "model": "gemma3:4b",
                "stream": False,
                "temperature": 0.7
            }
        }


class ChatRequest(BaseModel):
    messages: list
    model: Optional[str] = DEFAULT_MODEL
    stream: bool = False
    temperature: float = 0.7

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "What is 2 + 2?"}
                ],
                "model": "gemma3:4b",
                "stream": False
            }
        }


# ═══════════════════════════════════════════════════════════════
# MIDDLEWARE — Rate Limiting + Logging
# ═══════════════════════════════════════════════════════════════

def check_rate_limit(ip: str) -> bool:
    """Return True if under rate limit, False if exceeded."""
    now = time.time()
    window = 60  # 1 minute window
    timestamps = rate_tracker[ip]

    # Remove old timestamps
    while timestamps and timestamps[0] < now - window:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_RPM:
        return False

    timestamps.append(now)
    return True


def log_request(request_data: dict, response_data: dict, duration: float):
    """Append request/response to log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "duration_s": round(duration, 3),
        "request": request_data,
        "response_summary": {
            "text_length": len(response_data.get("response", response_data.get("text", ""))),
            "model": response_data.get("model", DEFAULT_MODEL),
        }
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    """Check server and Ollama status."""
    ollama_ok = False
    ollama_version = "unknown"
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/version", timeout=3)
        ollama_ok = resp.status_code == 200
        ollama_version = resp.json().get("version", "?")
    except Exception:
        pass

    return {
        "server": "ok",
        "ollama": "ok" if ollama_ok else "not running",
        "ollama_version": ollama_version,
        "default_model": DEFAULT_MODEL,
        "port": PORT,
        "rate_limit": f"{RATE_LIMIT_RPM} req/min",
    }


@app.post("/generate")
async def generate(request: Request, body: GenerateRequest):
    """
    Generate text from a prompt.
    Supports both streaming and non-streaming responses.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting
    if not check_rate_limit(client_ip):
        stats["total_errors"] += 1
        raise HTTPException(status_code=429, detail=f"Rate limit: max {RATE_LIMIT_RPM} requests/minute")

    stats["total_requests"] += 1
    start = time.time()

    # Build Ollama request
    ollama_payload = {
        "model": body.model,
        "prompt": body.prompt,
        "stream": body.stream,
        "options": {"temperature": body.temperature, "num_predict": body.max_tokens},
    }
    if body.system:
        ollama_payload["system"] = body.system

    # ── Streaming response ────────────────────────────────────
    if body.stream:
        def stream_generator():
            try:
                resp = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=ollama_payload,
                    stream=True,
                    timeout=120
                )
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            stats["total_tokens"] += data.get("eval_count", 0)
                            break
            except Exception as e:
                yield f"\n[ERROR: {e}]"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    # ── Non-streaming response ────────────────────────────────
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=ollama_payload,
            timeout=120
        )
        data = resp.json()
        duration = time.time() - start
        stats["response_times"].append(round(duration, 2))
        if len(stats["response_times"]) > 100:
            stats["response_times"] = stats["response_times"][-100:]

        tokens_used = data.get("eval_count", 0)
        stats["total_tokens"] += tokens_used

        result = {
            "text": data.get("response", ""),
            "model": body.model,
            "duration_s": round(duration, 2),
            "tokens": tokens_used,
        }
        log_request({"prompt": body.prompt[:200], "model": body.model}, result, duration)
        return JSONResponse(result)

    except requests.ConnectionError:
        stats["total_errors"] += 1
        raise HTTPException(status_code=503, detail="Ollama is not running. Start with: ollama serve")
    except Exception as e:
        stats["total_errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: Request, body: ChatRequest):
    """
    Chat completion endpoint (messages array format).
    """
    client_ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {RATE_LIMIT_RPM} req/min")

    stats["total_requests"] += 1
    start = time.time()

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": body.model, "messages": body.messages, "stream": False,
                  "options": {"temperature": body.temperature}},
            timeout=120
        )
        data = resp.json()
        duration = time.time() - start

        message = data.get("message", {})
        return {
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
            "model": body.model,
            "duration_s": round(duration, 2),
        }

    except requests.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama not running. Run: ollama serve")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def get_stats():
    """Show server usage statistics."""
    avg_rt = (sum(stats["response_times"]) / len(stats["response_times"])
              if stats["response_times"] else 0)
    return {
        "total_requests": stats["total_requests"],
        "total_tokens": stats["total_tokens"],
        "total_errors": stats["total_errors"],
        "avg_response_time_s": round(avg_rt, 2),
        "server_started": stats["start_time"],
        "log_file": LOG_FILE,
    }


@app.get("/logs")
def get_logs(limit: int = 10):
    """Return last N log entries."""
    if not os.path.exists(LOG_FILE):
        return {"logs": [], "message": "No logs yet"}
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    recent = lines[-limit:]
    return {
        "logs": [json.loads(l) for l in recent],
        "total_entries": len(lines),
        "showing": len(recent)
    }


@app.get("/models")
def list_models():
    """List available Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        data = resp.json()
        return {
            "models": [m.get("name") for m in data.get("models", [])],
            "default": DEFAULT_MODEL
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Ollama: {e}")


@app.get("/")
def root():
    return {
        "name": "Local Inference Server",
        "version": "1.0.0",
        "docs": f"http://localhost:{PORT}/docs",
        "endpoints": ["/generate (POST)", "/chat (POST)", "/health (GET)", "/stats (GET)", "/logs (GET)", "/models (GET)"]
    }


# ═══════════════════════════════════════════════════════════════
# START SERVER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🖥️  Inference Server — Phase 4, Project 2")
    print("=" * 60)
    print(f"Wrapping Ollama at: {OLLAMA_URL}")
    print(f"Default model:      {DEFAULT_MODEL}")
    print(f"Server URL:         http://localhost:{PORT}")
    print(f"Docs:               http://localhost:{PORT}/docs")
    print(f"Rate limit:         {RATE_LIMIT_RPM} req/min")
    print(f"Log file:           {LOG_FILE}")
    print()
    print("Quick test (after starting):")
    print(f'  curl -X POST http://localhost:{PORT}/generate \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f"    -d '{{\"prompt\": \"Hello!\", \"stream\": false}}'")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
