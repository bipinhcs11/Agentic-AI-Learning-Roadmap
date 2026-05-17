# ═══════════════════════════════════════════════════════════════
# Dockerfile — Streamlit UI
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════

FROM python:3.11-slim

RUN useradd --create-home appuser
WORKDIR /home/appuser/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

USER appuser

# API URL — overridden by docker-compose to point to "api" container
ENV API_URL=http://api:8000

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
