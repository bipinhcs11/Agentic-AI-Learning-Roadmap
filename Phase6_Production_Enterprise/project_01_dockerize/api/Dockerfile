# ═══════════════════════════════════════════════════════════════
# Dockerfile — FastAPI Inference API
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# MULTI-STAGE BUILD:
#   Stage 1 (builder): install dependencies (heavy, cached layer)
#   Stage 2 (runtime): copy only what's needed (small final image)
#
# WHY MULTI-STAGE?
#   Build tools (gcc, pip cache) stay in stage 1.
#   Final image only has the app + runtime libs = smaller + safer.
#
# BUILD & RUN:
#   docker build -t ai-platform-api .
#   docker run -p 8000:8000 ai-platform-api
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install dependencies first (this layer is cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security (never run containers as root in production)
RUN useradd --create-home appuser
WORKDIR /home/appuser/app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy app code
COPY main.py .

# Switch to non-root user
USER appuser

# Environment defaults (overridden by docker-compose.yml)
ENV OLLAMA_URL=http://host.docker.internal:11434
ENV DEFAULT_MODEL=gemma3:4b
ENV RATE_LIMIT_RPM=30
ENV APP_ENV=production

# Expose port
EXPOSE 8000

# Health check — Docker restarts container if this fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
