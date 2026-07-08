# Phase 9 · MCP + RAG Benefits Prototype (primary_contribution + savings account)

A small, standalone prototype that does **MCP + RAG together for LLM calling**.
Start with `../module_01_mcp_benefits_assistant/` first if you want the pure MCP
version with mock tools and resources before retrieval enters the picture.

A `qwen2.5:3b` agent answers questions about primary contribution and savings account plans by *deciding
at runtime* to call a retrieval tool exposed over the **Model Context Protocol
(MCP)**.

Reference content (contribution limits, qualifying plan rules, adjustment treatment) is sourced from the fixture references, verified for **2026**.

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

python agent.py "What is the 2026 savings account family contribution limit?"
python agent.py "If I'm 61, how much can I put in my primary contribution in 2026?"
python agent.py "What's the triple adjustment advantage of an savings account?"
python agent.py "How do the 2026 primary contribution and savings account limits compare?"
```

You'll see the tool call the agent decided to make, then a grounded answer citing the figures
and source document.

## Files

| File | Role |
|---|---|
| `docs/primary_contribution_reference.md`, `docs/savings_account_reference.md` | the knowledge base (verified 2026 facts) |
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
- Fixture source summary
- Fixture source summary
- Fixture source summary
- fixture reference note (2026 savings account/qualifying plan limits)
