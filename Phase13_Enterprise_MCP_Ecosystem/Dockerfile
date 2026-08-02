FROM ghcr.io/astral-sh/uv:0.8.3 AS uv

FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY config ./config
COPY contracts ./contracts
COPY registry ./registry
COPY src ./src

RUN uv sync --locked --no-dev --no-editable

USER 65532:65532

CMD ["enterprise-mcp-gateway"]
