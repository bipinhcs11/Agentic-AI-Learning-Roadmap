FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY config ./config
COPY contracts ./contracts
COPY registry ./registry
COPY src ./src

RUN pip install --no-cache-dir .

USER 65532:65532

CMD ["enterprise-mcp-gateway"]
