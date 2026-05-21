# DocuMind — Internal Document Intelligence Platform

> Phase 6 / Project 06 Capstone · Agentic AI Learning Roadmap

DocuMind is a production-ready AI SaaS product that lets teams upload internal documents and ask natural-language questions about them. Answers are grounded in your documents, come with citations, and are quality-scored by a multi-agent pipeline.

---

## What DocuMind Does

| Capability | Detail |
|---|---|
| Document ingestion | Upload PDF, TXT, or Markdown files via drag-and-drop UI |
| Semantic search | nomic-embed-text embeddings + cosine similarity retrieval |
| Grounded Q&A | Multi-agent LangGraph pipeline: retrieve → answer → cite → quality |
| Citations | Every answer links to the exact document sections used |
| Role-based access | Admins manage all docs; users query their own |
| Usage dashboard | Token costs, query counts, quality scores (admin view) |
| Local-first | Runs entirely with Ollama — no OpenAI key required |
| Cloud-ready | Docker + nginx stack deploys to any VPS or AWS EC2 |

---

## Architecture

```
Browser
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  nginx :80                                           │
│  /api/ → backend:8000                               │
│  /     → frontend:8501                              │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
               ▼                      ▼
   ┌───────────────────┐   ┌──────────────────────┐
   │  FastAPI Backend   │   │  Streamlit Frontend  │
   │                   │   │                      │
   │  • JWT Auth       │   │  • Login / Register  │
   │  • SQLite (meta)  │   │  • Document Upload   │
   │  • VectorStore    │   │  • Chat Interface    │
   │    (numpy)        │   │  • Admin Dashboard   │
   │  • LangGraph RAG  │   └──────────────────────┘
   │    Pipeline       │
   └─────────┬─────────┘
             │  HTTP
             ▼
   ┌───────────────────┐
   │  Ollama :11434    │
   │  (host machine)   │
   │                   │
   │  gemma3:4b (LLM)  │
   │  nomic-embed-text │
   └───────────────────┘

RAG Multi-Agent Pipeline (LangGraph):
  Query → [RetrieveAgent] → [AnswerAgent] → [CitationAgent] → [QualityAgent] → Response
```

---

## Quick Start

### Prerequisites

1. Install [Ollama](https://ollama.ai) and pull the required models:

```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

2. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker + Docker Compose).

### Start the stack

```bash
cd Phase6_Production_Enterprise/project_06_capstone_product

docker compose up --build
```

Wait for all services to show `healthy`. This takes 2-3 minutes on first build.

### Seed demo data

In a separate terminal:

```bash
python demo/seed_data.py
```

This creates demo users, uploads 3 sample documents, and runs 5 test queries.

### Open the UI

- **Frontend:** http://localhost:8501
- **Backend API docs:** http://localhost:8000/docs
- **Via nginx:** http://localhost

Default credentials:

| Username | Password | Role |
|---|---|---|
| admin | admin123 | admin |
| user1 | user123 | user |

---

## User Guide

### Upload Documents

1. Log in with your credentials.
2. In the left sidebar, click the upload area and select a PDF, TXT, or MD file.
3. DocuMind chunks the file and indexes it — this takes a few seconds while Ollama generates embeddings.
4. Your document appears in the sidebar list.

### Ask Questions

1. Type your question in the chat input at the bottom.
2. DocuMind retrieves the most relevant passages from your documents.
3. The answer appears with a quality score (1-10) and citations.
4. Expand the citations section to see which document sections were used.

### Read Citations

Each citation shows:
- The source filename
- A text excerpt from the document
- A similarity score (0-1; higher is more relevant)

---

## Admin Guide

Log in as `admin` to access the **Admin Dashboard** tab.

### Stats Dashboard

| Metric | Description |
|---|---|
| Total Users | All registered accounts |
| Documents Indexed | Across all users |
| Queries Answered | Cumulative |
| Tokens Used (est.) | Approximate LLM token consumption |
| Avg Quality Score | Mean quality rating across all queries |

### User Management

The admin can create users with specific roles via the API:

```bash
curl -X POST http://localhost:8000/admin/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret", "role": "user"}'
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `documind-change-me-in-production` | JWT signing secret |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama API endpoint |
| `LLM_MODEL` | `gemma3:4b` | Ollama model for generation |
| `DB_PATH` | `/app/db/documind.db` | SQLite database path |
| `DOCUMENTS_DIR` | `/app/documents` | Uploaded file storage |
| `API_URL` | `http://backend:8000` | Backend URL (used by frontend) |

Set these in a `.env` file in the project root:

```bash
SECRET_KEY=my-super-secret-production-key
OLLAMA_URL=http://host.docker.internal:11434
LLM_MODEL=gemma3:4b
```

---

## Deploying to AWS

Refer to [Phase 6 / Project 03](../project_03_aws_deployment/) for the full AWS deployment guide.

Short version:

1. Launch an EC2 instance (t3.medium minimum; t3.large for comfortable performance).
2. Install Docker, Docker Compose, and Ollama on the instance.
3. Copy the project directory to the instance via `scp` or `git clone`.
4. Set `SECRET_KEY` and `OLLAMA_URL` in `.env`.
5. Open ports 80 (nginx) and 8000 (API direct access, optional) in the Security Group.
6. Run `docker compose up -d --build`.

For production hardening:
- Add HTTPS via Let's Encrypt + Certbot in the nginx container.
- Replace SQLite with PostgreSQL (add a `db` service to `docker-compose.yml`).
- Replace the in-memory VectorStore with Qdrant for persistence across restarts.
- Set `OLLAMA_URL` to the EC2 instance's private IP if running Ollama separately.

---

## Extension Ideas

| Idea | Effort | Value |
|---|---|---|
| Connect to S3 for document storage | Medium | High — survives container restarts |
| Add LangSmith tracing | Low | High — debug agent pipelines visually |
| Support DOCX files | Low | Medium — add `python-docx` parser |
| Persistent vector DB (Qdrant) | Medium | High — no re-indexing on restart |
| Per-query model selection | Low | Medium — let users pick fast vs. quality |
| Streaming answers | Medium | High — improves perceived latency |
| Document sharing between users | Medium | Medium — collaborative knowledge base |
| Slack/Teams bot integration | High | High — meet users where they work |
| Fine-tuned embedding model | High | High — domain-specific retrieval quality |

---

## Project Structure

```
project_06_capstone_product/
├── backend/
│   ├── main.py               # FastAPI app, auth, all endpoints
│   ├── rag_pipeline.py       # LangGraph multi-agent RAG pipeline
│   ├── document_processor.py # PDF/TXT/MD parsing, chunking, embedding
│   ├── requirements.txt
│   └── Dockerfile            # Multi-stage, non-root user
├── frontend/
│   ├── app.py                # Streamlit UI
│   ├── requirements.txt
│   └── Dockerfile
├── nginx/
│   └── nginx.conf            # Reverse proxy config
├── demo/
│   └── seed_data.py          # Demo data population script
├── data/                     # Created by docker compose (gitignored)
│   ├── documents/            # Uploaded files (bind mount)
│   └── db/                   # SQLite database (bind mount)
├── docker-compose.yml
└── README.md
```

---

## Technology Stack

| Layer | Technology | Phase Introduced |
|---|---|---|
| Local LLM | Ollama + gemma3:4b | Phase 1 |
| Embeddings | nomic-embed-text | Phase 1 |
| Vector search | numpy cosine similarity | Phase 2 |
| RAG pipeline | Custom + LangGraph | Phase 2 + Phase 5 |
| Agent framework | LangGraph StateGraph | Phase 5 |
| REST API | FastAPI | Phase 3 |
| UI | Streamlit | Phase 4 |
| Auth | JWT (python-jose) | Phase 6 |
| Containerisation | Docker + Docker Compose | Phase 6 |
| Reverse proxy | nginx | Phase 6 |
| Database | SQLite (SQLAlchemy) | Phase 6 |
