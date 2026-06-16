# Module 02 — MCP + RAG Enterprise Integration (401k + HSA)

The second step of the Phase 9 track: combine **MCP tools** with **RAG** so a `qwen2.5:3b`
agent dynamically chooses the right context path per question. Builds directly on
`../module_01_mcp_benefits_assistant/` (pure MCP).

## The core idea: two context sources, one server

| Context | Served as | Data | Example question |
|---|---|---|---|
| **Your account** | MCP **tools** | **mock** (fictional employee) | "Am I getting my full 401(k) match?" |
| **The rules** | MCP **RAG tools** | public IRS/Fidelity reference summaries (2026) | "What's the 2026 HSA family limit?" |

That split is deliberate: personal/account data should never be a real document you embed —
it lives in tools (mocked). Public rules and limits are exactly what RAG is for. The agent
decides which to call, and uses **both** when a question mixes them.

> The corpus is our own **reference summaries** compiled from public IRS/Fidelity sources
> (with citations) — not verbatim copies of any document.

## Dynamic flow — four routes

```
  question ─▶ qwen2.5:3b router (explicit LangGraph)
                 │
                 ├─ direct     — no tools needed
                 ├─ mcp_only   — ACCOUNT tool(s)              "am I getting my full match?"
                 ├─ rag_only   — search_benefits_docs + cite  "what's the 2026 HSA limit?"
                 └─ mcp+rag    — both, then combine           "do dental expenses qualify, and
                                                               how much have I contributed?"
                 ▼
              grounded answer  (figures + source URL + educational disclaimer)
```

`agent.py` prints the tools the model chose and appends an **audit line** (route + tools +
documents used) to `audit_log.jsonl` — a small preview of the capstone's audit requirement.

## Files

| File | Role |
|---|---|
| `docs/401k_reference.md`, `docs/hsa_reference.md` | public-source reference summaries (compiled from IRS + Fidelity, 2026) |
| `ingest.py` | chunk + embed the real docs → `index.npz` (Ollama `nomic-embed-text`) |
| `benefits_mcp_server.py` | one MCP server: **mock** account tools + **RAG** tools (`search_benefits_docs`, `list_sources`) |
| `demo_client.py` | raw MCP client (no LLM) — shows the mechanics |
| `agent.py` | `qwen2.5:3b` explicit LangGraph router + audit log — the dynamic MCP+RAG flow |
| `demo_api.py` | browser-friendly recording API for the shared Agent Playground UI |
| `demo_agent_core.py` | deterministic demo router used by the recording API |

## Prerequisites

```bash
ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
source ~/Documents/my-ai-project/ai-env/bin/activate
pip install -r requirements.txt
```

## Run it

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/module_02_mcp_rag_enterprise_integration

python ingest.py            # build index.npz from the reference docs (one-time)
python demo_client.py       # see the raw MCP tools/calls (no LLM)

# the dynamic agent — try questions that take different routes:
python agent.py "Am I getting the full employer match on my 401(k)?"      # mcp_only
python agent.py "What is the 2026 HSA family contribution limit?"         # rag_only
python agent.py "I contribute 6%. Am I maxing the match, and what's the 2026 401k limit?"  # mcp+rag
```

## Record With The Shared Agent Playground

For LinkedIn/video recording, use the shared browser UI instead of relying only
on terminal output:

```bash
python demo_api.py
```

Then open:

```text
http://localhost:8090/
```

The Python demo API returns the same response shape as the Spring Boot Module 05
API: route, tool calls, retrieved documents, citations, and final answer. It is
deterministic so the recording does not require a live LLM call, while the main
`agent.py` file remains the real dynamic LangGraph/Ollama flow.

## Citations & safety

- Figures pulled from `search_benefits_docs` are cited to their source document; `list_sources`
  returns the IRS/Fidelity URLs.
- All employee/account data is **fictional**. This module is educational only — **not financial,
  tax, legal, or investment advice.**

## Connect to Claude Desktop (optional)

```json
{
  "mcpServers": {
    "benefits-mcp-rag": {
      "command": "/Users/bipinpradhan/Documents/my-ai-project/ai-env/bin/python",
      "args": ["/Users/bipinpradhan/Documents/Agentic AI learning Roadmap/Phase9_Dynamic_Agentic_RAG_MCP/module_02_mcp_rag_enterprise_integration/benefits_mcp_server.py"]
    }
  }
}
```

Run `python ingest.py` first so the RAG tool has an index.

## Not yet (these belong in the capstone)

- No AWS / Bedrock / SageMaker yet — local Ollama only.
- No real employee data, payroll, bank, retirement, or HSA integrations.
- No multi-tenant isolation or production financial guidance.

## Next step

The **capstone** reuses this exact pattern (MCP tools + RAG routing + audit) and adds the
enterprise layer — MCP gateway, tool permissions, audit logs, and a cloud LLM provider
abstraction — on top of the existing Phase 8 app rather than rebuilding it. See
`../capstone_enterprise_assistant_hub/` and
`../../Phase8_Integrations_Shipping/project_06_capstone_launch/UPGRADE_SPEC_dynamic_providers_mcp.md`.

## Sources (RAG corpus)
- IRS — 401(k) limit increases to $24,500 for 2026: https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500
- Fidelity — 401(k) contribution limits 2025 and 2026: https://www.fidelity.com/learning-center/smart-money/401k-contribution-limits
- Fidelity — HSA contribution limits and eligibility 2026: https://www.fidelity.com/learning-center/smart-money/hsa-contribution-limits
- IRS Revenue Procedure 2025-19 — 2026 HSA/HDHP limits (official PDF): https://www.irs.gov/pub/irs-drop/rp-25-19.pdf
