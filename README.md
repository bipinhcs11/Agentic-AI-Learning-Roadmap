# Agentic AI Learning Roadmap 🤖

Local-first hands-on roadmap for learning Agentic AI, RAG, multi-agent systems,
MCP, and production AI apps with Ollama, LangGraph, CrewAI, FastAPI, and AWS
deployment patterns.

**9 phases | 48+ projects | suggested 48+ week pace | 100% local-first**

> **Origin:** This roadmap started with a viral LinkedIn post — *"Build these 10 RAG projects if you want to be taken seriously as an AI engineer."* Those 10 projects became **Phase 2**, and the journey grew from there into a full 9-phase path: foundations → RAG → agents → frameworks → multi-agent → production → advanced patterns → shipping → dynamic MCP enterprise systems.

This repo is built for two audiences:

- **Self-paced builders** who want to learn by running real projects locally.
- **Community learners** who want a practical map from first local model to
  production-style agentic systems.

The week numbers are suggested pacing, not a rigid calendar. Move faster, slow
down, or jump to the phase that matches what you are trying to build.

---

## Start Here

| If you are... | Start with | Why |
|---|---|---|
| New to local AI | `Phase1_Foundations/` | Get Ollama, Python, and the local OpenAI-compatible client working. |
| Learning RAG | `Phase2_RAG_Systems/project_01_first_rag/` | Build the first retrieval pipeline from scratch before frameworks. |
| Learning agents | `Phase3_Agentic_Stack/` | Move from tool calling to memory, scraping, and API agents. |
| Learning production AI | `Phase6_Production_Enterprise/` | Docker, auth, observability, deployment, and capstone SaaS patterns. |
| Learning MCP | `Phase9_Dynamic_Agentic_RAG_MCP/` | MCP tools, MCP + RAG routing, and the enterprise assistant hub capstone. |

## Learning Paths

You do not have to complete everything in order.

- **Beginner path:** Phase 1 → Phase 2 Project 01 → Phase 3 Project 01
- **RAG engineer path:** Phase 2 → Phase 3 Project 05 → Phase 7 Project 01
- **Agent builder path:** Phase 3 → Phase 5 → Phase 7
- **Production path:** Phase 6 → Phase 8 → Phase 9 capstone
- **MCP path:** Phase 9 Module 01 → Module 02 → Enterprise Assistant Hub

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
| Integrations | Slack, GitHub, Stripe, Email |
| MCP | Model Context Protocol tools, resources, prompts |

---

## Phases

### Phase 1 — Foundation (Weeks 1-2) ✅
**Goal:** Get local AI running on Mac Mini M4

- Installed Ollama, Python 3.11, VS Code
- OpenAI-compatible local API client
- Verified full stack with gemma3:4b

📁 `Phase1_Foundations/`

---

### Phase 2 — RAG Projects (Weeks 3-6) ✅
**Goal:** Build the 10 hands-on Retrieval-Augmented Generation projects from the original LinkedIn post

| # | Project |
|---|---------|
| 01 | First RAG pipeline (build from scratch) |
| 02 | IBM-style RAG (production patterns) |
| 03 | GraphRAG (knowledge graph) |
| 04 | Multi-document RAG (vector database) |
| 05 | Agentic RAG (autonomous agents) |
| 06 | LangChain RAG (production ready) |
| 07 | Document analysis (LLM + PDF) |
| 08 | Multimodal RAG (text + images) |
| 09 | AI research agent (automated analysis) |
| 10 | Real-time assistant (live RAG pipeline) |

**Stack:** nomic-embed-text, ChromaDB, numpy cosine similarity

📁 `Phase2_RAG_Systems/`

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

### Phase 7 — Advanced AI Patterns (Weeks 31-36) ✅
**Goal:** Go beyond basic agents into cutting-edge production patterns

| # | Project |
|---|---------|
| 01 | GraphRAG (knowledge graph + relationship traversal) |
| 02 | Real-time streaming (WebSocket token streaming) |
| 03 | Long-term memory (persistent vector memory) |
| 04 | Mixture of Agents (query routing to specialists) |
| 05 | Self-improving agent (Reflexion loop) |
| 06 | AI safety & red-teaming (guardrails + adversarial tests) |

**Stack:** networkx, FastAPI WebSockets, SQLite, LangGraph

📁 `Phase7_Advanced_AI_Patterns/`

---

### Phase 8 — Integrations & Shipping (Weeks 37-44) ✅
**Goal:** Take local-AI into real-world integrations and ship a SaaS

| # | Project |
|---|---------|
| 01 | Slack bot (Socket Mode) |
| 02 | GitHub review bot (PR webhook → AI review) |
| 03 | Email agent (classify, prioritize, draft) |
| 04 | Multi-tenant SaaS (FastAPI + JWT + quotas) |
| 05 | Billing & metering (token usage + invoices + Stripe) |
| 06 | Capstone launch (dockerized RAG SaaS) |

**Stack:** slack-bolt, FastAPI, SQLAlchemy, Stripe, Docker

📁 `Phase8_Integrations_Shipping/`

---

### Phase 9 — Dynamic Agentic RAG + MCP (Weeks 45+) 🔄
**Goal:** Learn MCP as its own enterprise integration pattern, then combine it with RAG and dynamic LLM provider routing

| # | Module |
|---|--------|
| 01 | MCP Benefits Assistant — mock 401(k) + HSA tools/resources |
| 02 | MCP + RAG Enterprise Integration — structured tools + document retrieval |
| 03 | Enterprise Assistant Hub capstone — MCP gateway + RAG + AWS provider abstraction |
| 04 | Java MCP Benefits Assistant — plain Java companion to Module 01 |
| 05 | Spring Boot MCP + RAG Benefits Microservice — Streamable HTTP MCP + REST |

**Stack:** MCP Python SDK, FastMCP, Spring AI MCP, Java, Spring Boot, local mock data, Ollama, NumPy, Bedrock/SageMaker adapters

📁 `Phase9_Dynamic_Agentic_RAG_MCP/`

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
python Phase2_RAG_Systems/project_01_first_rag/rag_from_scratch.py
```

## Community

This started as a personal learning roadmap, but it is open for people who want
to follow along, reuse examples, or suggest improvements.

- Star the repo if you are following the roadmap.
- Open an [issue](https://github.com/bipinhcs11/Agentic-AI-Learning-Roadmap/issues)
  if a setup step is unclear or a project breaks.
- Use [GitHub Discussions](https://github.com/bipinhcs11/Agentic-AI-Learning-Roadmap/discussions)
  for roadmap questions, project ideas, and learning notes.
- See `CONTRIBUTING.md` for the contribution style.

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
├── Phase1_Foundations/             # setup + first model (docs/, test_gemma3.py)
├── Phase2_RAG_Systems/           # 10 RAG projects (+ guide)
├── Phase3_Agentic_Stack/          # 6 agent projects (+ guide)
├── Phase4_Agent_Framework/        # 6 framework projects (+ guide)
├── Phase5_Multi_Agent_Systems/    # 6 multi-agent projects
├── Phase6_Production_Enterprise/  # 6 production projects
├── Phase7_Advanced_AI_Patterns/   # 6 advanced-pattern projects
├── Phase8_Integrations_Shipping/  # 6 integration / shipping projects
├── Phase9_Dynamic_Agentic_RAG_MCP/ # MCP benefits, MCP+RAG, enterprise capstone
├── scripts/                       # setup & install helper scripts
├── requirements.txt               # shared dependencies
├── CLAUDE.md                      # project context
└── README.md
```
