# ═══════════════════════════════════════════════════════════════
# Dockerfile — Monitored FastAPI API
# Phase 6 · Project 04 Observability
# ═══════════════════════════════════════════════════════════════

FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
COPY --from=builder /install /usr/local
COPY main.py .
USER appuser
ENV OLLAMA_URL=http://host.docker.internal:11434
ENV DEFAULT_MODEL=gemma3:4b
ENV APP_ENV=production
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
