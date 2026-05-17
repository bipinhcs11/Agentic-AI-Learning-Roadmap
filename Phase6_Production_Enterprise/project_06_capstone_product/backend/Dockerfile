# ╔══════════════════════════════════════════════════════════════════╗
# ║  DocuMind Backend — Multi-stage Dockerfile                       ║
# ║  Stage 1: dependency builder (keeps layer cache stable)          ║
# ║  Stage 2: slim runtime image running as non-root user            ║
# ╚══════════════════════════════════════════════════════════════════╝

# ── Stage 1: build deps ───────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed for bcrypt, cryptography, numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security hardening
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appuser . .

# Directories that will be mounted as volumes; pre-create so ownership is correct
RUN mkdir -p /app/documents /app/db && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health-check so Docker Compose knows when the backend is ready
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
