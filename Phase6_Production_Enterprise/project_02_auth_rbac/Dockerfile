# ═══════════════════════════════════════════════════════════════
# Dockerfile — Auth & RBAC API
# Phase 6 · Production & Enterprise · Project 02
# ═══════════════════════════════════════════════════════════════
#
# MULTI-STAGE BUILD:
#   Stage 1 (builder): pip install into /install prefix
#   Stage 2 (runtime): copy only the installed packages + app code
#
# WHY TWO STAGES?
#   The builder stage pulls in gcc, pip wheel caches, and build
#   artefacts needed to compile bcrypt/cryptography extensions.
#   None of those end up in the final image, keeping it lean.
#
# BUILD:
#   docker build -t auth-api .
#
# RUN (standalone):
#   docker run -p 8000:8000 \
#     -e SECRET_KEY=change-me \
#     -e OLLAMA_URL=http://host.docker.internal:11434 \
#     auth-api
#
# RUN (with persistent DB volume):
#   docker run -p 8000:8000 \
#     -v $(pwd)/data:/data \
#     -e DB_PATH=/data/auth.db \
#     auth-api
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Copy and install dependencies first so Docker can cache this
# expensive layer independently of code changes
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Never run application containers as root — limits blast radius
# if a dependency has a RCE vulnerability
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy installed packages from builder (no pip, no gcc in runtime)
COPY --from=builder /install /usr/local

# Copy application source
COPY auth.py main.py ./

# Create data directory for SQLite with correct ownership
# The DB_PATH env var below points here; mount a volume over /data
# in production so the DB survives container restarts.
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

# ── Environment defaults ──────────────────────────────────────
# Override any of these in docker run -e or docker-compose.yml
# SECRET_KEY is intentionally omitted — pass it at runtime:
#   docker run -e SECRET_KEY=$(openssl rand -hex 32) ...
ENV OLLAMA_URL=http://host.docker.internal:11434
ENV DEFAULT_MODEL=gemma3:4b
ENV RATE_LIMIT_RPM=30
ENV APP_ENV=production
ENV DB_PATH=/data/auth.db

EXPOSE 8000

# Health check — Docker marks the container unhealthy (and
# docker-compose can restart it) if /health returns non-200
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
