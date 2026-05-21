# Phase 6 — Production & Enterprise
**Agentic AI Learning Roadmap | Weeks 23-30**

## What You Learn
Take everything built in Phases 1-5 and make it production-ready: containerized, secured, deployed to AWS, monitored, and fine-tuned.

## Projects

| # | Project | What You Build | Key Tech |
|---|---------|----------------|----------|
| 01 | Dockerize Everything | 3-container stack: API + UI + Nginx | Docker, Docker Compose |
| 02 | Auth & RBAC | JWT auth, role-based access, API keys | python-jose, passlib, FastAPI Security |
| 03 | AWS Deployment | ECS Fargate, ECR, ALB, Terraform IaC | AWS, Terraform |
| 04 | Observability | Prometheus metrics + Grafana dashboards | prometheus-client, Grafana |
| 05 | Fine-Tuning | LoRA fine-tune Gemma3:4b on Mac Mini M4 | Unsloth, PEFT, GGUF |
| 06 | Capstone: DocuMind | Full AI SaaS product — document Q&A platform | Everything from Phases 1-6 |

## How to Run Each Project

```bash
# Project 01 — Docker stack (requires Docker Desktop running)
cd project_01_dockerize
docker compose up --build
# → http://localhost (UI)  http://localhost:8000/docs (API)

# Project 02 — Auth & RBAC
cd project_02_auth_rbac
pip install -r requirements.txt
uvicorn main:app --reload
python test_auth.py   # runs 10 auth tests

# Project 03 — AWS Deployment
cd project_03_aws_deployment
./deploy.sh   # interactive — walks through ECR + Terraform + ECS
# Teardown: ./teardown.sh

# Project 04 — Observability
cd project_04_observability
docker compose up --build
# → Grafana: http://localhost:3000 (admin/admin123)
# → Prometheus: http://localhost:9090
python load_test.py   # generate traffic to see metrics

# Project 05 — Fine-Tuning
cd project_05_finetuning
bash install.sh
huggingface-cli login
python prepare_dataset.py
python finetune.py        # ~45-60 min on M4
python export_gguf.py
python ollama_deploy.py

# Project 06 — DocuMind Capstone
cd project_06_capstone_product
docker compose up --build
python demo/seed_data.py   # seed with demo data
# → http://localhost (login: admin/admin123 or user1/user123)
```

## Phase 6 Technology Stack

| Category | Technology |
|---|---|
| Containerization | Docker, Docker Compose |
| Reverse Proxy | Nginx |
| Authentication | JWT (python-jose), bcrypt (passlib) |
| Cloud | AWS ECS Fargate, ECR, ALB, VPC |
| Infrastructure as Code | Terraform |
| Metrics | Prometheus, prometheus-fastapi-instrumentator |
| Dashboards | Grafana |
| Fine-tuning | LoRA (PEFT), Unsloth, SFTTrainer (trl) |
| Model Export | GGUF via llama.cpp / Unsloth |
| Database | SQLite (local) → RDS PostgreSQL (cloud) |

## Progression Through Phase 6

```
Project 01: Package app into Docker containers
    ↓
Project 02: Add security — nobody gets in without auth
    ↓
Project 03: Deploy to AWS — anyone on internet can access it
    ↓
Project 04: Monitor it — know when things go wrong before users do
    ↓
Project 05: Improve the model — fine-tune for your specific use case
    ↓
Project 06: Ship it — a real product combining everything
```

## Prerequisites

```bash
# Required before any Project 01+ work
# (check with: docker --version)
brew install --cask docker

# Required for Project 03
brew install awscli terraform
aws configure   # enter your AWS access keys

# Required for Project 05
huggingface-cli login   # HuggingFace account + accepted Gemma3 license
```
