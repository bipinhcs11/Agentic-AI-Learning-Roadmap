# ─────────────────────────────────────────────────────────────────────────────
# AskMyDocs Pro — Backend Dockerfile (Multi-Stage Build)
#
# WHY multi-stage? Two-stage builds create smaller final images:
# Stage 1 (builder): Install build dependencies (gcc, etc.) + compile packages
# Stage 2 (runtime): Copy only the compiled packages — no build tools
#
# Result: Runtime image is ~300MB instead of ~800MB with all build tools.
# Smaller images = faster deploys, less attack surface, cheaper storage.
# ─────────────────────────────────────────────────────────────────────────────

# ─── Stage 1: Build ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Set working directory for build stage
WORKDIR /build

# WHY copy requirements first, then source? Docker layer caching.
# If requirements.txt doesn't change, Docker reuses the pip install layer.
# This makes rebuilds after code changes much faster (~10s vs ~120s).
COPY requirements.txt .

# Install dependencies into a virtual environment
# WHY venv in Docker? Keeps site-packages isolated and easy to copy to next stage
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# WHY create a non-root user? Security principle of least privilege.
# If the app is compromised, the attacker has user-level access, not root.
# This is a CRITICAL security practice for production containers.
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser

WORKDIR /app

# Copy the virtual environment from build stage (no build tools included)
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY . .

# Create data directory for SQLite database (writable by appuser)
RUN mkdir -p /data && chown appuser:appuser /data

# Switch to non-root user
USER appuser

# Add venv to PATH so we can run python/uvicorn without full path
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app
# WHY PYTHONDONTWRITEBYTECODE? Prevents creating .pyc files — saves disk space
# WHY PYTHONUNBUFFERED? Ensures logs appear immediately (not buffered)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Document what port the app listens on (informational only — doesn't actually publish)
EXPOSE 8000

# Health check — Docker will mark container unhealthy if this fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# WHY uvicorn with --workers 1? For a single-machine deployment with SQLite,
# multiple workers would cause database lock contention. Use 1 worker + SQLite,
# or switch to PostgreSQL for multi-worker production deployments.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
