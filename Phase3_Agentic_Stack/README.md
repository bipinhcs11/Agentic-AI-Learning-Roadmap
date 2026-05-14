# Phase 3 — Full Agentic Stack 🔄

> **Goal:** Master the complete agentic AI tech stack · Weeks 7–12 · IN PROGRESS

## Projects

| # | Project | Concept | Week | Status |
|---|---------|---------|------|--------|
| 01 | [Tool-Calling Agent](project_01_tool_calling_agent/) | ReAct pattern, tool registry | 7 | ⏳ Ready |
| 02 | [Memory Agent](project_02_memory_agent/) | Short-term + long-term memory | 8 | ⏳ Ready |
| 03 | [Web Scraping Agent](project_03_web_scraping_agent/) | BeautifulSoup, real-world data | 9 | ⏳ Ready |
| 04 | [Multi-Tool Agent](project_04_multi_tool_agent/) | Tool chaining, complex tasks | 10 | ⏳ Ready |
| 05 | [RAG Evaluation](project_05_rag_evaluation/) | LLM-as-judge, quality metrics | 11 | ⏳ Ready |
| 06 | [Agent API Server](project_06_agent_api_server/) | FastAPI, REST endpoints | 12 | ⏳ Ready |

```bash
# Start each project:
ollama serve                         # Terminal 1
source ~/Documents/my-ai-project/ai-env/bin/activate  # Terminal 2
python project_01_.../tool_calling_agent.py
```

## Overview

Phase 3 moves from RAG projects into building full autonomous AI agents that can use tools, remember context, and be deployed to the cloud.

## Tech Stack to Learn

| Layer | Tools | Why |
|-------|-------|-----|
| Foundation Models | Ollama (local), Claude API, OpenAI API | Multiple model capabilities |
| Orchestration | LangChain, LlamaIndex, DSPy | Connect models, memory, tools |
| Vector Databases | ChromaDB → Qdrant → Pinecone | Scale from local to production |
| Embedding Models | nomic-embed-text, OpenAI, HuggingFace | Convert text to vectors |
| Memory & Context | mem0, zep, LangChain memory | Persistent agent memory |
| Data Ingestion | BeautifulSoup, Firecrawl | Feed agents real-world data |
| Evaluation | Ragas, LangSmith | Measure and improve quality |
| Deployment | Modal → AWS | Ship agents to production |

## Coming in Weeks 7–12

- Build agents that use tools (search, calculator, code execution)
- Add persistent memory across conversations
- Deploy to Modal cloud with one command
- Connect to real data sources (web, APIs, databases)

## Status

🔄 All 6 projects are set up — work through them in order, each builds on the previous!
