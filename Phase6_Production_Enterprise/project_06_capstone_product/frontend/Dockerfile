# ╔══════════════════════════════════════════════════════════════════╗
# ║  DocuMind Frontend — Streamlit Dockerfile                        ║
# ║  Standard single-stage pattern; Streamlit has no build step.     ║
# ╚══════════════════════════════════════════════════════════════════╝

FROM python:3.11-slim

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

# Streamlit configuration — disable telemetry and set server options
RUN mkdir -p /home/appuser/.streamlit && \
    printf '[server]\nheadless = true\naddress = "0.0.0.0"\nport = 8501\nenableCORS = false\nenableXsrfProtection = false\n\n[browser]\ngatherUsageStats = false\n' \
    > /home/appuser/.streamlit/config.toml && \
    chown -R appuser:appuser /home/appuser/.streamlit

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py"]
