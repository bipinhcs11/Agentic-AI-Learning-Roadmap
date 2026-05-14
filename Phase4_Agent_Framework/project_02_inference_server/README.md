# Project 02 — Inference Server 🖥️

> **Week 13 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build your own **FastAPI inference server** that wraps Ollama and adds
streaming, logging, rate limiting, and request tracking.

## Concept: What Is an Inference Server?

An inference server is what sits between your app and the AI model:

```
Your App → [Inference Server] → Ollama → gemma3:4b
                ↑
         - Request logging
         - Rate limiting
         - Streaming support
         - Usage tracking
```

This is exactly what commercial AI providers (OpenAI, Anthropic) do —
but now you're building your own!

## Features

- Streaming and non-streaming responses
- Request/response logging to file
- Basic rate limiting (max N requests per minute)
- Usage stats (tokens, response times)
- Health check endpoint

## Stack

- **FastAPI + Uvicorn** (already installed)
- **requests** for Ollama communication
- **No extra libraries needed**

## How to Run

```bash
ollama serve
source ~/Documents/my-ai-project/ai-env/bin/activate
python inference_server.py
# Opens on port 8001 (different from project 6's 8000)
```

## Test It

```bash
# Non-streaming
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Python?", "stream": false}'

# Check stats
curl http://localhost:8001/stats
```

## Status

⏳ Ready to run — port 8001
