# Phase 8 — Integrations & Shipping
**Agentic AI Learning Roadmap | Weeks 37-44**

## What You Learn
Connect your AI to the real world — Slack, GitHub, email — and ship a production SaaS product with multi-tenancy, billing, and a launch checklist.

## Projects

| # | Project | What You Build | Key Tech |
|---|---------|----------------|----------|
| 01 | Slack AI Bot | /ask, /summarize, /brainstorm slash commands | slack-bolt, Socket Mode |
| 02 | GitHub Review Bot | Auto-reviews PRs via webhook + inline comments | FastAPI webhook, GitHub API |
| 03 | Email Intelligence Agent | Classify, draft replies, daily digest | SQLite email store, LLM classifier |
| 04 | Multi-tenant SaaS | Org isolation, per-tenant quotas, plans | Row-level security, JWT |
| 05 | Billing & Metering | Token-based pricing, invoices, Stripe sim | PricingEngine, StripeSimulator |
| 06 | AskMyDocs Pro (Capstone) | Full launch-ready AI SaaS product | Everything from Phases 1-8 + Hugging Face |

> **Planned for Project 06 — Hugging Face Cloud Integration:**
> Replace the `CLOUD_MODE` stub from Phase 6 Project 03 with the
> [Hugging Face Inference API](https://huggingface.co/inference-api).
> The deployed ECS app will call a hosted HF model instead of local Ollama,
> making AskMyDocs Pro fully cloud-native with no local GPU dependency.
> Pattern: swap `OLLAMA_URL` → `HF_ENDPOINT`, add `HF_API_KEY` as an ECS secret
> (same approach used for `SECRET_KEY` in Phase 6 Project 02).

## How to Run

```bash
source ~/Documents/my-ai-project/ai-env/bin/activate
ollama serve

# Project 01 — Slack Bot (needs Slack app credentials)
pip install slack-bolt openai python-dotenv
cp project_01_slack_bot/.env.example project_01_slack_bot/.env
# Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN
python project_01_slack_bot/bot.py

# Project 02 — GitHub Review Bot
pip install fastapi uvicorn requests openai python-dotenv
uvicorn project_02_github_review_bot.review_bot:app --port 8000
python project_02_github_review_bot/test_review.py  # test without webhook

# Project 03 — Email Agent (no credentials needed)
python project_03_email_agent/email_agent.py

# Project 04 — Multi-tenant SaaS
pip install -r project_04_multitenant_saas/requirements.txt
uvicorn project_04_multitenant_saas.main:app --reload
python project_04_multitenant_saas/test_multitenant.py

# Project 05 — Billing & Metering
python project_05_billing_metering/billing.py
python project_05_billing_metering/stripe_integration.py

# Project 06 — AskMyDocs Pro Capstone
cd project_06_capstone_launch
docker compose up --build
# Open http://localhost
```

## Accounts Needed for Phase 8

| Project | Account | Cost |
|---|---|---|
| 01 Slack Bot | Slack workspace (free) | Free |
| 02 GitHub Bot | GitHub account + PAT | Free |
| 03 Email Agent | None — uses simulated data | Free |
| 04-05 SaaS/Billing | None — local SQLite | Free |
| 06 Capstone | Docker (already installed) | Free |

## Progression

```
Project 01: Your AI inside Slack — where your team already works
    ↓
Project 02: AI in your dev workflow — automated PR reviews
    ↓
Project 03: AI in your inbox — triage and draft at scale
    ↓
Project 04: Package it for multiple customers (multi-tenancy)
    ↓
Project 05: Charge for it (billing and metering)
    ↓
Project 06: Launch it — AskMyDocs Pro, production-ready
```
