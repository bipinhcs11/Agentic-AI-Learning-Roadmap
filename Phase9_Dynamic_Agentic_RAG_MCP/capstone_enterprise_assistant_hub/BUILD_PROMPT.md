# Phase 9 Capstone — Enterprise Assistant Hub · Build Prompt

> Paste this whole file into Claude Code, or tell Claude Code:
> "Follow `Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub/BUILD_PROMPT.md`."

---

STEP 0 — FIX MODULE 02 FIRST (keep it small):
Before building the capstone, review `Phase9_Dynamic_Agentic_RAG_MCP/module_02_mcp_rag_enterprise_integration/`
and fix the remaining retrieval-quality issue where a 401(k) "employee contribution limit"
query can rank the combined employee+employer limit ($72,000) above the employee-only limit
($24,500). Add a small intent boost to the reranker (distinguish "employee/elective/salary
deferral" vs "combined/total/employer"). Keep the fix minimal. The capstone MUST inherit this
corrected reranker.

Then build the Phase 9 capstone: an Enterprise Assistant Hub that ties together the Phase 9
MCP work. It must REUSE Phase 8 patterns, not rebuild the Phase 8 SaaS app.

READ FIRST (do not skip):
1. CLAUDE.md (root) — environment + hard constraints.
2. Phase9_Dynamic_Agentic_RAG_MCP/module_01_mcp_benefits_assistant/ and
   module_02_mcp_rag_enterprise_integration/ — reuse the MCP server, the dynamic MCP+RAG
   router, the heading-anchored chunking + hybrid (cosine+topic+keyword) rerank, and the
   audit_log.jsonl pattern. DO NOT copy these files blindly — reuse the patterns, importing
   or adapting minimally.
3. Phase8_Integrations_Shipping/project_06_capstone_launch/backend/main.py — reuse its
   multi-tenant + RAG + metering PATTERNS only (do NOT copy the whole app).
4. Phase8_Integrations_Shipping/project_06_capstone_launch/UPGRADE_SPEC_dynamic_providers_mcp.md
   — the hub's provider layer must match this design.

SCOPE — build ONLY these five things (do NOT rebuild Phase 8 auth/billing/SaaS; skip
Slack/observability/real AWS deploy — those stay in Phase 8):
1. Cloud LLM provider abstraction: providers.py with get_provider() keyed on
   AI_PROVIDER = ollama (default) | bedrock | sagemaker | hf. Lazy-import boto3 and the
   Hugging Face client INSIDE the providers (only when selected) so nothing heavy or
   credentialed loads by default. For hf, use a lightweight client (httpx or huggingface_hub)
   — do NOT add heavy ML packages (no torch, no transformers). Same interface as the
   UPGRADE_SPEC (complete() + stream(), normalized Completion). Embeddings stay local Ollama
   nomic-embed-text.
2. MCP gateway: mcp_gateway.py that connects to one or more MCP servers (start with the
   Module 02 benefits server), loads tools via langchain-mcp-adapters, and for a given tenant
   returns ONLY that tenant's allowed tools. Each tool is wrapped so tenant permissions are
   enforced BEFORE tool execution. For hub-owned tools that accept tenant_id, inject tenant_id
   server-side (the model can never set it). For existing MCP tools that do NOT accept
   tenant_id, never expose cross-tenant data through their config/corpus/tool list.
3. Tool permissions / tenancy: config/tenants.yaml (tenant -> allowed tool names + its
   document corpus). Enforce the allowlist in the gateway; reject disallowed/unknown tools;
   guarantee no cross-tenant data access. Mock tenant auth via an API-key->tenant map; comment
   that production plugs into the Phase 8 JWT/tenant model.
4. Dynamic MCP+RAG router: orchestrator.py on qwen2.5:3b (Ollama) that picks
   direct | mcp_only | rag_only | mcp+rag per request, runs <=4 tool iterations, does final
   generation through the provider abstraction, and falls back to direct RAG on any MCP error.
5. Audit log: append one structured JSONL record per request — timestamp, tenant_id, question,
   route, tools_used, documents_used, provider, token counts if available.

ENTRYPOINT: a CLI (python hub.py --tenant acme "question") and an optional thin FastAPI /chat
(API key -> tenant). Keep it minimal.

HARD CONSTRAINTS (from CLAUDE.md):
- Ollama is the default; the app MUST run with no AWS credentials; NEVER make real AWS calls
  (mock boto3 in tests).
- RAM-safe: NO PyTorch, NO sentence-transformers; embeddings via Ollama nomic-embed-text;
  cosine via numpy.
- Mock account data + public-source reference summaries ONLY (no real financial accounts).
  Educational; include a "not financial, tax, legal, or investment advice" disclaimer.
- House style: ═══ header block per .py file, WHY comments, section dividers, no docstrings on
  obvious functions.
- Work on branch phase9-capstone-hub. Put everything under
  Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub/.

TESTS (pytest; no real AWS; no Ollama needed for these):
- All modules MUST be importable without Ollama, qwen2.5, boto3, AWS creds, or Hugging Face
  creds. Instantiate external clients lazily inside runtime functions only (not at import time).
- provider selection: unset -> Ollama; bedrock/sagemaker mocked; bad value errors; importing
  providers does NOT import boto3 unless selected.
- permissions: a tenant cannot call a tool outside its allowlist; tenant A cannot retrieve
  tenant B's documents.
- routing: mcp_only / rag_only / mcp+rag / direct classified correctly (unit-test the route
  logic with stub tool calls).
- audit: each request writes a well-formed JSONL record.

ACCEPTANCE:
- python hub.py --tenant <t> "..." runs end-to-end on local Ollama (qwen2.5:3b +
  nomic-embed-text) with AI_PROVIDER=ollama.
- Switching AI_PROVIDER=bedrock|sagemaker|hf routes generation through that provider
  (mock-tested; no real calls).
- Disallowed tools are blocked; audit log captures every request; all tests pass with zero real
  AWS calls.

WHEN DONE: update CLAUDE.md Phase 9 capstone status and the Phase9_.../DESIGN.md capstone
section, and summarize new files + how to run.
