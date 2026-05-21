# Agentic AI Learning Roadmap — Project Context

## What This Is
A 6-phase, 30-week hands-on AI learning roadmap built on Mac Mini M4. All models run locally via Ollama. No cloud GPU required.

## Environment
- **Python venv:** `~/Documents/my-ai-project/ai-env`
- **Activate:** `source ~/Documents/my-ai-project/ai-env/bin/activate`
- **Ollama:** `http://localhost:11434` — run `ollama serve` before any project
- **Default model:** `gemma3:4b` (RAM-safe for M4)
- **Embeddings:** `nomic-embed-text` via Ollama

## Key Constraints
- Never install PyTorch or sentence-transformers — causes OOM with gemma3:27b
- Use numpy for cosine similarity (not chromadb vector ops)
- Use `from openai import OpenAI` with `base_url="http://localhost:11434/v1"` for Ollama
- For LangGraph: use `from langchain_openai import ChatOpenAI` pointing at Ollama

## Code Style
- Header block at top of every .py file using ═══ borders
- Rich inline comments explaining WHY (not what)
- Section dividers using ─────── or ═══════
- No docstrings on obvious functions

## Phase Status
- Phase 1 Foundation: ✅ Complete
- Phase 2 RAG Projects: ✅ Complete (10 projects)
- Phase 3 Agentic Stack: ✅ Complete (6 projects)
- Phase 4 Agent Framework: ✅ Complete (6 projects)
- Phase 5 Multi-Agent Systems: ✅ Complete (6 projects)
- Phase 6 Production & Enterprise: ✅ Complete (6 projects)

## Installed Packages (Phase 5+)
- langchain-openai, langgraph, crewai, redis
- prometheus-client, prometheus-fastapi-instrumentator
- python-jose[cryptography], passlib[bcrypt]

## Git Branches
- main: all phases merged
- phase5-multi-agent-systems: Phase 5 feature branch
- phase6-production-enterprise: Phase 6 feature branch
