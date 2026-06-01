# Phase 7 — Advanced AI Patterns
**Agentic AI Learning Roadmap | Weeks 31-36**

## What You Learn
Go beyond basic agents into cutting-edge patterns used in production AI systems.

## Projects

| # | Project | Core Pattern | Key Tech |
|---|---------|--------------|----------|
| 01 | GraphRAG | Knowledge graph + relationship traversal | networkx, nomic-embed-text |
| 02 | Real-time Streaming | WebSocket token streaming | FastAPI WS, httpx async |
| 03 | Long-term Memory | Persistent vector memory across sessions | SQLite, numpy, nomic-embed-text |
| 04 | Mixture of Agents | Query routing to specialist agents | Router + 4 specialists |
| 05 | Self-Improving Agent | Reflexion: generate → critique → improve | LangGraph, LLM-as-judge |
| 06 | AI Safety & Red-teaming | Guardrails + adversarial testing | Input/output chains, SQLite audit log |

## How to Run

```bash
source ~/Documents/my-ai-project/ai-env/bin/activate
ollama serve   # required for all projects

# Project 01 — GraphRAG
pip install networkx
python Phase7_Advanced_AI_Patterns/project_01_graphrag/graph_rag.py

# Project 02 — Real-time Streaming
pip install fastapi uvicorn httpx websockets
uvicorn Phase7_Advanced_AI_Patterns.project_02_realtime_streaming.server:app --reload
# Open http://localhost:8000

# Project 03 — Long-term Memory
python Phase7_Advanced_AI_Patterns/project_03_longterm_memory/memory_agent.py

# Project 04 — Mixture of Agents
python Phase7_Advanced_AI_Patterns/project_04_mixture_of_agents/mixture_of_agents.py

# Project 05 — Self-Improving Agent (Reflexion)
python Phase7_Advanced_AI_Patterns/project_05_self_improving_agent/self_improving_agent.py

# Project 06 — AI Safety & Red-teaming
python Phase7_Advanced_AI_Patterns/project_06_ai_safety_redteam/safety_guardrails.py
python Phase7_Advanced_AI_Patterns/project_06_ai_safety_redteam/redteam_tests.py
```

## Key Concepts Progression

```
Project 01: RAG with relationships, not just similarity
    ↓
Project 02: Real-time UX — stream tokens as they generate
    ↓
Project 03: Agents that remember across sessions (not just context window)
    ↓
Project 04: Right model for right task — intelligent routing
    ↓
Project 05: Self-improvement without human feedback (Reflexion)
    ↓
Project 06: Test your system like an attacker would
```
