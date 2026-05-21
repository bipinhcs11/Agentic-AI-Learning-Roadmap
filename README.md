# Agentic AI Learning Roadmap 🤖

A complete hands-on journey from running your first local AI model to shipping a production AI SaaS product — built entirely on a Mac Mini M4.

**30 weeks | 6 phases | 40+ projects | 100% local-first**

---

## The Stack

| Layer | Technology |
|---|---|
| Local AI | Ollama + Gemma3:4b / 27b |
| Orchestration | LangGraph, CrewAI, LangChain |
| Vector DB | ChromaDB → Qdrant → Pinecone |
| APIs | FastAPI + Uvicorn |
| UI | Streamlit |
| Multi-Agent | LangGraph StateGraph, CrewAI Crews |
| Containers | Docker + Docker Compose |
| Cloud | AWS ECS Fargate + ECR + ALB |
| IaC | Terraform |
| Monitoring | Prometheus + Grafana |
| Fine-Tuning | LoRA + Unsloth + GGUF |

---

## Phases

### Phase 1 — Foundation (Weeks 1-2) ✅
**Goal:** Get local AI running on Mac Mini M4

- Installed Ollama, Python 3.11, VS Code
- OpenAI-compatible local API client
- Verified full stack with gemma3:4b

📁 `Phase1_Foundation/`

---

### Phase 2 — RAG Projects (Weeks 3-6) ✅
**Goal:** Build 10 hands-on Retrieval-Augmented Generation projects

| # | Project |
|---|---------|
| 01 | First RAG pipeline |
| 02 | IBM-style RAG |
| 03 | GraphRAG |
| 04 | Multi-document RAG |
| 05 | Agentic RAG |
| 06 | LangChain RAG |
| 07 | Document analysis |
| 08 | Multimodal RAG |
| 09 | Research agent |
| 10 | Real-time assistant |

**Stack:** nomic-embed-text, ChromaDB, numpy cosine similarity

📁 `Phase2_RAG_Projects/`

---

### Phase 3 — Full Agentic Stack (Weeks 7-12) ✅
**Goal:** Master the complete agentic AI tech stack

| # | Project |
|---|---------|
| 01 | Tool-calling agent (ReAct pattern) |
| 02 | Memory agent (short + long term) |
| 03 | Web scraping agent |
| 04 | Multi-tool agent |
| 05 | RAG evaluation (LLM-as-judge) |
| 06 | Agent API server |

**Stack:** FastAPI, mem0, BeautifulSoup, Ragas

📁 `Phase3_Agentic_Stack/`

---

### Phase 4 — Build Your Own Agent Framework (Weeks 13-16) ✅
**Goal:** Build something similar to LangChain from scratch

| # | Project |
|---|---------|
| 01 | Model manager |
| 02 | Inference server (streaming + logging) |
| 03 | OpenAI-compatible API |
| 04 | Streamlit web UI |
| 05 | Custom agent framework (mini LangChain) |
| 06 | Full platform capstone |

**Stack:** FastAPI, Streamlit, SQLite, Typer

📁 `Phase4_Agent_Framework/`

---

### Phase 5 — Multi-Agent Systems (Weeks 17-22) ✅
**Goal:** Multiple specialized agents coordinating to solve complex tasks

| # | Project |
|---|---------|
| 01 | Supervisor-Worker pattern (LangGraph) |
| 02 | CrewAI Research Crew (Researcher → Analyst → Writer) |
| 03 | Agent Communication Bus (asyncio pub/sub) |
| 04 | Code Generation Pipeline (review-revise loop) |
| 05 | Multi-Agent RAG with domain routing |
| 06 | Autonomous Research Pipeline with human-in-the-loop |

**Stack:** LangGraph, CrewAI, asyncio, Redis (optional)

📁 `Phase5_Multi_Agent_Systems/`

---

### Phase 6 — Production & Enterprise (Weeks 23-30) ✅
**Goal:** Take everything and make it production-ready, observable, secure, and deployable

| # | Project |
|---|---------|
| 01 | Dockerize Everything (API + UI + Nginx) |
| 02 | Auth & RBAC (JWT + roles + API keys) |
| 03 | AWS Deployment (ECS Fargate + Terraform) |
| 04 | Observability (Prometheus + Grafana dashboards) |
| 05 | Fine-Tuning Gemma3:4b on Apple Silicon M4 |
| 06 | DocuMind — AI document intelligence SaaS (capstone) |

**Stack:** Docker, Terraform, AWS ECS, Prometheus, Grafana, LoRA, Unsloth

📁 `Phase6_Production_Enterprise/`

---

## Quick Start

```bash
# Clone
git clone https://github.com/bipinhcs11/Agentic-AI-Learning-Roadmap.git
cd Agentic-AI-Learning-Roadmap

# Setup Python environment
python3 -m venv ai-env
source ai-env/bin/activate
pip install -r requirements.txt

# Start Ollama
ollama pull gemma3:4b
ollama serve

# Run any project
python Phase2_RAG_Projects/project_01_first_rag/rag_pipeline.py
```

## Run the Capstone Product (DocuMind)

```bash
cd Phase6_Production_Enterprise/project_06_capstone_product
docker compose up --build
python demo/seed_data.py
# Open http://localhost  →  login: admin / admin123
```

---

## Hardware

All projects run locally on:
- **Mac Mini M4** (16GB unified memory)
- No cloud GPU required for any phase including fine-tuning
- Ollama handles model serving natively on Apple Silicon

---

## Repository Structure

```
├── Phase1_Foundation/
├── Phase2_RAG_Projects/          # 10 RAG projects
├── Phase3_Agentic_Stack/         # 6 agent projects
├── Phase4_Agent_Framework/       # 6 framework projects
├── Phase5_Multi_Agent_Systems/   # 6 multi-agent projects
├── Phase6_Production_Enterprise/ # 6 production projects
├── requirements.txt              # all dependencies
└── README.md
```
