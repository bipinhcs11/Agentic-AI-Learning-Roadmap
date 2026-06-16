# Phase 9 · MCP + RAG Benefits Prototype (401k + HSA)

A small, standalone prototype that does **MCP + RAG together for LLM calling**.
Start with `../module_01_mcp_benefits_assistant/` first if you want the pure MCP
version with mock tools and resources before retrieval enters the picture.

A `qwen2.5:3b` agent answers questions about 401(k) and HSA plans by *deciding
at runtime* to call a retrieval tool exposed over the **Model Context Protocol
(MCP)**.

Reference content (contribution limits, HDHP rules, tax treatment) is sourced from the IRS
and Fidelity, verified for **2026**.

## How it works

```
  you ──▶ agent.py (qwen2.5:3b)
            │  "needs facts?" → yes
            ▼
        MCP tool call  ──stdio──▶  benefits_mcp_server.py
            ▲                         │  embed query (nomic-embed-text)
            │  retrieved excerpts     │  NumPy cosine over docs/*.md
            └─────────────────────────┘
            │  enough context → grounded answer
            ▼
         ANSWER (with figures + source doc)
```

- **Retrieval is a tool, not a hardcoded step.** The agent chooses when to search — that's
  the "dynamic flow."
- **Everything local + RAM-safe:** Ollama for the LLM and embeddings, NumPy for cosine. No
  PyTorch, no sentence-transformers, no external vector DB.
- **qwen2.5:3b, not gemma3** — it has the strong tool-calling MCP relies on.

## Prerequisites

```bash
# 1. Ollama running, with the two models pulled
ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

# 2. Python deps (use your project venv: source ~/Documents/my-ai-project/ai-env/bin/activate)
pip install -r requirements.txt
```

## Run it

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/mcp_benefits_example

python ingest.py                  # build index.npz from docs/*.md (one-time)

python agent.py "What is the 2026 HSA family contribution limit?"
python agent.py "If I'm 61, how much can I put in my 401(k) in 2026?"
python agent.py "What's the triple tax advantage of an HSA?"
python agent.py "How do the 2026 401(k) and HSA limits compare?"
```

You'll see the tool call the agent decided to make, then a grounded answer citing the figures
and source document.

## Files

| File | Role |
|---|---|
| `docs/401k_reference.md`, `docs/hsa_reference.md` | the knowledge base (verified 2026 facts) |
| `ingest.py` | chunk + embed docs → `index.npz` |
| `benefits_mcp_server.py` | **MCP server** exposing `search_benefits_docs` + `list_topics` |
| `agent.py` | **MCP client + LangGraph router** on qwen2.5:3b |
| `requirements.txt` | dependencies |

## How this maps to Module 02 and the capstone

Same three layers as the Module 02 plan and the capstone upgrade spec, just minimal:
`search_benefits_docs` (MCP tool) ≈ the capstone's tenant-scoped `search_tenant_docs`; the
LangGraph router here becomes the capstone's optional orchestrator behind `ENABLE_MCP`. Once
this clicks, continue with `../module_02_mcp_rag_enterprise_integration/` and the integration
spec in `../../Phase8_Integrations_Shipping/project_06_capstone_launch/UPGRADE_SPEC_dynamic_providers_mcp.md`.

## Sources
- IRS — 401(k) limit increases to $24,500 for 2026: https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500
- Fidelity — 401(k) contribution limits 2025 and 2026: https://www.fidelity.com/learning-center/smart-money/401k-contribution-limits
- Fidelity — HSA contribution limits and eligibility 2026: https://www.fidelity.com/learning-center/smart-money/hsa-contribution-limits
- IRS Revenue Procedure 2025-19 (2026 HSA/HDHP limits)
