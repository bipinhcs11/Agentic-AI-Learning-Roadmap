# ═══════════════════════════════════════════════════════════════
# Project 02 — Auth & RBAC · main.py
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   FastAPI application that wraps the Phase 6 Project 01 API
#   with a full authentication + role-based access layer.
#
#   Auth flow:
#     1. POST /auth/register  → create account
#     2. POST /auth/login     → receive JWT token
#     3. Include header:  Authorization: Bearer <token>
#        OR:              X-API-Key: <key>
#     4. Role check happens inside Depends(require_role(...))
#
# HOW TO RUN (local, no Docker):
#   pip install -r requirements.txt
#   uvicorn main:app --reload --port 8000
#
# HOW TO RUN (Docker):
#   docker build -t auth-api .
#   docker run -p 8000:8000 auth-api
#
# ENDPOINTS SUMMARY:
#   Open:        GET /health, POST /auth/register, POST /auth/login
#   Any user:    POST /chat, POST /chat/stream, POST /auth/api-key
#   Developer+:  GET /models
#   Admin only:  GET /stats
# ═══════════════════════════════════════════════════════════════

import json
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import httpx
import requests
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import (
    User,
    create_access_token,
    create_api_key,
    create_user,
    authenticate_user,
    get_current_user,
    get_db,
    init_db,
    require_role,
)

# ─────────────────────────────────────────────────────────────
# Config — environment variables with safe defaults
# ─────────────────────────────────────────────────────────────

OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
DEFAULT_MODEL  = os.getenv("DEFAULT_MODEL", "gemma3:4b")
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "30"))
APP_ENV        = os.getenv("APP_ENV", "development")

# ─────────────────────────────────────────────────────────────
# Lifespan — runs startup/shutdown logic around the server loop.
# Using lifespan is the FastAPI 0.100+ recommended alternative
# to the deprecated @app.on_event("startup") pattern.
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────
    print("[startup] Initialising database …")
    init_db()
    print("[startup] Auth database ready.")
    yield
    # ── Shutdown ──────────────────────────────────────────────
    print("[shutdown] Goodbye.")


app = FastAPI(
    title="AI Platform API — Auth & RBAC",
    description=(
        "Phase 6 Project 02: Production AI API with JWT authentication "
        "and role-based access control (admin / developer / viewer)."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — in production, restrict allow_origins to your front-end domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory rate tracker keyed by username (falls back to IP for
# unauthenticated endpoints). For production, swap with Redis + sliding window.
rate_tracker: dict = defaultdict(deque)

# Global stats counter (not persisted — resets on restart)
stats: dict = {
    "total_requests": 0,
    "total_errors": 0,
    "start_time": datetime.now(timezone.utc).isoformat(),
    "environment": APP_ENV,
}


# ═══════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "viewer"    # clients can request a role; admins should lock this down


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_hours: int = 24


class ApiKeyResponse(BaseModel):
    api_key: str
    note: str = "Store this key safely — it is shown only once."


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
    requested_by: str   # username surfaced so callers know whose quota was used


class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str


# ─────────────────────────────────────────────────────────────
# Rate limiter — identical logic to Project 01 but keyed on
# username so auth'd users get their own bucket
# ─────────────────────────────────────────────────────────────

def check_rate_limit(key: str) -> bool:
    now    = time.time()
    window = rate_tracker[key]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_RPM:
        return False
    window.append(now)
    return True


# ═══════════════════════════════════════════════════════════════
# AUTH ENDPOINTS  (open — no token required)
# ═══════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account.

    Role is accepted from the request body so developers can
    self-register as "developer". In a stricter setup, restrict
    role selection to admins only by calling require_role("admin").
    """
    user = create_user(db, body.username, body.email, body.password, body.role)
    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Exchange credentials for a JWT access token.

    We embed role in the JWT payload so downstream services can
    authorise without querying the DB on every request.
    """
    user = authenticate_user(db, body.username, body.password)
    if not user:
        # Deliberately vague message — don't leak whether username exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub":     user.username,
        "role":    user.role,
        "user_id": user.id,
    })
    return TokenResponse(access_token=token, role=user.role)


# ═══════════════════════════════════════════════════════════════
# AUTH ENDPOINTS  (requires valid login)
# ═══════════════════════════════════════════════════════════════

@app.post("/auth/api-key", response_model=ApiKeyResponse)
async def generate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    """Generate (or regenerate) an API key for the current user.

    Calling this again invalidates the previous key because we
    overwrite api_key_hash — only one active key per user.
    """
    raw_key = create_api_key(db, current_user)
    return ApiKeyResponse(api_key=raw_key)


@app.get("/auth/me", response_model=UserInfo)
async def whoami(current_user: User = Depends(get_current_user)):
    """Return info about the currently authenticated user."""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
    )


# ═══════════════════════════════════════════════════════════════
# AI ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/models")
async def list_models(
    current_user: User = Depends(require_role("models")),   # developer or admin
):
    """List Ollama models. Requires developer or admin role."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return {
            "models":       models,
            "default":      DEFAULT_MODEL,
            "requested_by": current_user.username,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach Ollama: {e}")


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request:      ChatRequest,
    req:          Request,
    current_user: User    = Depends(require_role("chat")),  # any authenticated role
    db:           Session = Depends(get_db),
):
    """Standard (non-streaming) chat. Requires any authenticated role."""
    if not check_rate_limit(current_user.username):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

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
            requested_by=current_user.username,
        )
    except Exception as e:
        stats["total_errors"] += 1
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(
    request:      ChatRequest,
    req:          Request,
    current_user: User = Depends(require_role("chat")),  # any authenticated role
):
    """Streaming chat via Server-Sent Events. Requires any authenticated role."""
    if not check_rate_limit(current_user.username):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

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


# ═══════════════════════════════════════════════════════════════
# ADMIN / OPS ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/stats")
async def get_stats(
    current_user: User = Depends(require_role("stats")),    # admin only
):
    """Usage statistics. Requires admin role."""
    return {
        **stats,
        "rate_limit_rpm": RATE_LIMIT_RPM,
        "requested_by":   current_user.username,
    }


@app.get("/health")
async def health():
    """Health check — open endpoint for Docker / load-balancer probes.

    Deliberately has NO auth dependency so the health check works
    before a token is acquired (e.g., during rolling deploys).
    """
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = resp.status_code == 200
    except Exception:
        ollama_ok = False

    return {
        "status":      "healthy" if ollama_ok else "degraded",
        "ollama":      "connected" if ollama_ok else "unreachable",
        "ollama_url":  OLLAMA_URL,
        "environment": APP_ENV,
        "uptime_since": stats["start_time"],
    }


# ─────────────────────────────────────────────────────────────
# Entry point — only used when running directly (not via Docker CMD)
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=(APP_ENV == "development"),
    )
