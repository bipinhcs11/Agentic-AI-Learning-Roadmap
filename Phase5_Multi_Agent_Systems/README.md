# Phase 5 — Multi-Agent Systems
**Agentic AI Learning Roadmap | Weeks 17-22**

## What You Learn
How to build systems where multiple AI agents coordinate to solve complex tasks no single agent can handle alone.

## Projects

| # | Project | Core Pattern | Stack |
|---|---------|--------------|-------|
| 01 | Supervisor-Worker | Central supervisor routes to specialists | LangGraph, ChatOpenAI→Ollama |
| 02 | CrewAI Research Crew | Role-based agents with personas | CrewAI, Ollama LLM |
| 03 | Agent Communication Bus | Event-driven pub/sub decoupling | asyncio queues, Redis (optional) |
| 04 | Code Gen Pipeline | Review-revise loop, code execution | LangGraph, subprocess sandbox |
| 05 | Multi-Agent RAG | Domain routing + specialist retrievers | LangGraph, nomic-embed-text |
| 06 | Autonomous Research | Full pipeline + human-in-the-loop | LangGraph, all Phase 5 patterns |

## Setup

```bash
# Activate environment
source ~/Documents/my-ai-project/ai-env/bin/activate

# Install Phase 5 packages
pip install langchain-openai crewai redis

# Start Ollama (required for all projects)
ollama serve
```

## How to Run Each Project

```bash
cd Phase5_Multi_Agent_Systems

# Project 01 — Supervisor-Worker (LangGraph)
python project_01_supervisor_worker/supervisor_worker.py

# Project 02 — CrewAI Research Crew
python project_02_crewai_research_crew/research_crew.py

# Project 03 — Agent Communication Bus
python project_03_agent_bus/agent_bus.py

# Project 04 — Code Generation Pipeline
python project_04_code_gen_pipeline/code_gen_pipeline.py

# Project 05 — Multi-Agent RAG
python project_05_multi_agent_rag/multi_agent_rag.py

# Project 06 — Autonomous Research (Capstone)
python project_06_autonomous_research/autonomous_research.py
```

## Key Concepts Progression

```
Project 01: One supervisor coordinates all agents (centralized)
    ↓
Project 02: Agents have rich personas and tools (role-based)
    ↓
Project 03: Agents communicate via message bus (decentralized)
    ↓
Project 04: Agents loop and revise each other's work (iterative)
    ↓
Project 05: Router picks the right specialist dynamically (routing)
    ↓
Project 06: All patterns + human approval gates (full production)
```

## Technology Installed in Phase 5

```
langchain-openai    → ChatOpenAI client for LangGraph
crewai              → Role-based multi-agent framework
redis               → Python client for Redis Pub/Sub (Project 03)
```

## Optional: Enable Redis Backend (Project 03)
```bash
brew install redis
brew services start redis
# Then in agent_bus.py: swap InMemoryBus() → RedisBus()
```
