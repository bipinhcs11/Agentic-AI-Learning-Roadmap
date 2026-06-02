# AskMyDocs Pro

**AI-powered document Q&A SaaS — Ask anything about your documents in natural language.**

Upload PDFs and text files, then ask questions. AskMyDocs Pro finds the relevant sections and generates accurate, cited answers using local AI (Ollama). Multi-tenant, metered, and Slack-integrated.

---

## Features

- Upload documents (PDF, TXT) and index them for AI search
- Ask questions in natural language — get answers with source citations
- Real-time streaming responses (WebSocket-powered)
- Multi-tenant architecture — data isolation between organizations
- Usage metering with monthly quotas per plan
- Slack `/ask` integration — query your docs from Slack
- Admin dashboard — manage all tenants and view platform metrics
- Full REST API with auto-generated Swagger docs
- Docker Compose deployment — runs in 3 containers (backend, frontend, nginx)

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally
- Required Ollama models:

```bash
ollama pull gemma3:4b          # Chat model
ollama pull nomic-embed-text   # Embedding model for document search
```

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend API available at: http://localhost:8000
Swagger UI at: http://localhost:8000/docs

### 2. Start the Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Frontend available at: http://localhost:8501

### 3. Login with demo accounts

| Email | Password | Plan | Quota |
|-------|----------|------|-------|
| admin@acme.example | acme-pass-123 | Pro | 500/month |
| admin@startup.example | startup-pass-123 | Free | 50/month |
| admin@bigcorp.example | bigcorp-pass-123 | Enterprise | Unlimited |

### 4. Try it out

1. Sign in as Acme Corp admin
2. Go to **Upload Documents** → upload any PDF or TXT file
3. Go to **Chat** → ask a question about the uploaded document
4. View the answer with source citations and relevance scores

---

## Docker Deployment

Run the full production stack (backend + frontend + nginx):

```bash
# Copy and edit environment variables
cp .env.example .env
# Edit .env with your secrets

# Build and start all services
docker compose up --build

# App is available at:
# http://localhost        (nginx → routes to frontend)
# http://localhost/docs   (nginx → FastAPI Swagger UI)
# http://localhost:8000   (direct backend access)
# http://localhost:8501   (direct Streamlit access)
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-strong-random-secret-here
SUPER_ADMIN_TOKEN=your-admin-token-here
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
AI_MODEL=gemma3:4b
SLACK_SIGNING_SECRET=your-slack-signing-secret
```

Generate secure secrets:
```bash
openssl rand -hex 32  # Run twice for SECRET_KEY and SUPER_ADMIN_TOKEN
```

---

## Deployment Guide (Cloud)

For AWS deployment, the architecture is:
- **EC2** (t3.medium or better, ~$30/month) for backend + Ollama
- **EC2** or **App Runner** for frontend
- **RDS PostgreSQL** (recommended over SQLite for production)
- **ALB** (Application Load Balancer) for HTTPS + WebSocket support
- **S3** for document storage (replace local filesystem)

See Phase 6 Project 03 for the full AWS deployment walkthrough with Terraform scripts.

### Quick EC2 Deploy

```bash
# SSH to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone and run
git clone https://github.com/yourusername/askmydocs-pro.git
cd askmydocs-pro
# Edit .env with production secrets
docker compose up -d

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:4b
ollama pull nomic-embed-text

# Enable HTTPS with Certbot
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

---

## Pricing Tiers

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Monthly requests | 50 | 500 | Unlimited |
| Documents | 10 | 100 | Unlimited |
| File size limit | 5MB | 25MB | 100MB |
| Slack integration | No | Yes | Yes |
| Priority support | No | Email | Dedicated |
| Price | $0/month | $49/month | $499/month |

---

## API Reference

The full API is documented at `/docs` when running locally.

### Key Endpoints

```bash
# Auth
POST /auth/login     # Get JWT token
POST /auth/register  # Register new user (requires existing auth)

# Documents
POST /documents      # Upload and index a document
GET  /documents      # List all documents for your tenant
DELETE /documents/{id}  # Delete a document

# AI Chat
POST /chat           # RAG-powered Q&A (HTTP)
WS   /ws/chat        # Streaming RAG chat (WebSocket)

# Slack
POST /slack/ask      # Slack slash command receiver

# Tenant & Usage
GET  /tenants/me     # Your tenant info + usage stats
GET  /usage          # Detailed usage breakdown

# Admin (super-admin token required)
POST /tenants        # Create new tenant
GET  /admin/tenants  # List all tenants with usage
GET  /metrics        # Platform-wide metrics
```

---

## How to Customize for Your Domain

### Change the AI model

Edit `AI_MODEL` environment variable. Any Ollama model works:
```bash
ollama pull llama3.2:8b
AI_MODEL=llama3.2:8b
```

### Change chunk size for better retrieval

In `backend/main.py`:
```python
CHUNK_SIZE = 800    # Larger chunks = more context per retrieval
CHUNK_OVERLAP = 100 # More overlap = fewer missed boundary sentences
```

### Add a new plan tier

In `backend/main.py`:
```python
PLAN_QUOTAS = {
    "free": 50,
    "starter": 200,   # New tier
    "pro": 500,
    "enterprise": -1,
}
```

### Brand the UI

In `frontend/app.py`, change:
```python
st.title("AskMyDocs Pro")  # → Your product name
```

In the `st.set_page_config()` call:
```python
page_title="Your Product Name",
page_icon="🔍",  # Your icon
```

### Connect to real Gmail (for email integration)

See Phase 8 Project 03 README for the Gmail API integration guide.

### Connect to real Stripe (for billing)

See Phase 8 Project 05 `stripe_integration.py` — each method has a docstring showing the exact real Stripe equivalent.

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │           Nginx (Port 80)         │
                    │   Reverse Proxy + SSL Termination │
                    └──────────┬──────────┬────────────┘
                               │          │
                    ┌──────────▼───┐  ┌───▼────────────┐
                    │   Streamlit  │  │  FastAPI Backend │
                    │  Frontend    │  │   Port 8000      │
                    │  Port 8501   │  │                  │
                    └─────────────┘  │  ┌─────────────┐ │
                                     │  │ RAG Engine  │ │
                                     │  │ (Retrieval) │ │
                                     │  └─────────────┘ │
                                     │  ┌─────────────┐ │
                                     │  │  SQLite DB  │ │
                                     │  └─────────────┘ │
                                     └────────┬─────────┘
                                              │
                                    ┌─────────▼────────┐
                                    │  Ollama (Local)   │
                                    │  gemma3:4b (chat) │
                                    │  nomic-embed-text │
                                    └──────────────────┘
```

---

## What You Built (Phase 8 Summary)

This capstone combines every major skill from the Agentic AI Learning Roadmap:

| Phase | Skill | Where Used |
|-------|-------|-----------|
| Phase 1 | Python + LLM basics | Email agent, all LLM calls |
| Phase 2 | API design | FastAPI backend |
| Phase 3 | Agentic patterns | RAG pipeline, email classifier |
| Phase 4 | Agent frameworks | Orchestration patterns |
| Phase 5 | Memory + context | Document chunking + retrieval |
| Phase 6 | Auth + RAG | Multi-tenant auth, RAG engine |
| Phase 7 | Streaming + WebSockets | /ws/chat endpoint |
| Phase 8 | Integrations + Shipping | Slack, billing, Docker, launch |

*Congratulations on completing Phase 8 of the Agentic AI Learning Roadmap!*
