# ─────────────────────────────────────────────────────────────────────────────
# AskMyDocs Pro — Frontend Dockerfile (Multi-Stage Build)
# ─────────────────────────────────────────────────────────────────────────────

# ─── Stage 1: Build ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

# Streamlit configuration — prevent it from asking for email on first run
# and configure for containerized deployment
RUN mkdir -p /home/appuser/.streamlit && \
    chown -R appuser:appuser /home/appuser/.streamlit

# Write Streamlit config
RUN echo '[general]\nemail = ""\n' > /home/appuser/.streamlit/credentials.toml && \
    echo '[server]\nport = 8501\nheadless = true\nenableCORS = false\naddress = "0.0.0.0"\n\n[browser]\ngatherUsageStats = false\n' > /home/appuser/.streamlit/config.toml

USER appuser

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# WHY HOME? Streamlit looks for config in ~/.streamlit — needs to know home dir
ENV HOME=/home/appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
