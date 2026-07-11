# Agentic AI Learning Roadmap — Project Context

## What This Is
A 9-phase, local-first hands-on AI learning roadmap built on Mac Mini M4. All models run locally via Ollama unless a later cloud module explicitly says otherwise. No cloud GPU required for the core path. The roadmap began with a viral "10 RAG Projects" LinkedIn post (now Phase 2) and grew into the full path: foundations, RAG, agents, frameworks, multi-agent systems, production, advanced patterns, shipping, and dynamic MCP enterprise systems.

## Environment
- **Python venv:** `~/Documents/my-ai-project/ai-env`
- **Activate:** `source ~/Documents/my-ai-project/ai-env/bin/activate`
- **Ollama:** `http://localhost:11434` — run `ollama serve` before any project
- **Default model:** `gemma3:4b` (RAM-safe for M4)
- **Embeddings:** `nomic-embed-text` via Ollama

## Key Constraints
- Never install PyTorch or sentence-transformers — causes OOM with gemma3:27b
- Use numpy for cosine similarity (not chromadb vector ops)
- Use `from openai import OpenAI` with `base_url="http://localhost:11434/v1"` for Ollama
- For LangGraph: use `from langchain_openai import ChatOpenAI` pointing at Ollama

## Code Style
- Header block at top of every .py file using ═══ borders
- Rich inline comments explaining WHY (not what)
- Section dividers using ─────── or ═══════
- No docstrings on obvious functions

## Phase Status
- Phase 1 Foundation: ✅ Complete
- Phase 2 RAG Projects: ✅ Complete (10 projects)
- Phase 3 Agentic Stack: ✅ Complete (6 projects)
- Phase 4 Agent Framework: ✅ Complete (6 projects)
- Phase 5 Multi-Agent Systems: ✅ Complete (6 projects)
- Phase 6 Production & Enterprise: ✅ Complete (6 projects)
- Phase 7 Advanced AI Patterns: ✅ Complete (6 projects)
- Phase 8 Integrations & Shipping: ✅ Complete (6 projects) — all fix+verified vs live Ollama 2026-06-08; needs-creds paths (Slack/GitHub/Stripe/Gmail) untested by design
- Phase 8 Capstone v2 — Dynamic Providers + MCP: 📋 Spec ready, not built (2026-06-12) — extends `project_06_capstone_launch` with an `AI_PROVIDER` abstraction (Ollama default / Bedrock / SageMaker / HF) wrapping the 3 LLM call sites, + optional MCP+RAG orchestration (`ENABLE_MCP=false`, tenant-scoped tools, qwen2.5:3b router). Embeddings stay local. Spec: `Phase8_Integrations_Shipping/project_06_capstone_launch/UPGRADE_SPEC_dynamic_providers_mcp.md`
- Phase 9 Dynamic Agentic RAG + MCP: 🔄 In Progress — new standalone MCP learning track before capstone integration.
  - Module 01 MCP Benefits Assistant: ✅ Built — mock primary contribution/savings account FastMCP server with tools/resources/prompts, no RAG, no AWS, no real professional data. Path: `Phase9_Dynamic_Agentic_RAG_MCP/module_01_mcp_benefits_assistant/`.
  - Module 02 MCP + RAG Enterprise Integration: ✅ Built — combined MCP server (mock account tools + RAG over public-source IRS/fixture provider 2026 reference summaries), qwen2.5:3b dynamic 4-way router (direct/mcp_only/rag_only/mcp+rag) + audit_log.jsonl. Retrieval = heading-anchored chunks + nomic search prefixes + cosine/topic/keyword rerank + an employee-vs-combined primary contribution intent boost so employee contribution-limit queries rank $24,500 above the $72,000 combined cap. Verified with capstone regression tests in the project venv; live qwen/Ollama checks still require Ollama running on Mac. Path: `Phase9_Dynamic_Agentic_RAG_MCP/module_02_mcp_rag_enterprise_integration/`.
  - Capstone Enterprise Assistant Hub: ✅ Built — standalone Phase 9 hub with lazy `AI_PROVIDER=ollama|bedrock|sagemaker|hf`, tenant API-key config, MCP gateway with tool allowlists, tenant-scoped RAG inheriting the corrected Module 02 reranker, direct/mcp_only/rag_only/mcp+rag orchestration, CLI + thin FastAPI `/chat`, and structured JSONL audit logs. Tests mock cloud providers and run with no Ollama/AWS/HF credentials. Path: `Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub/`.
  - Module 04 Java MCP Benefits Assistant: ✅ Built — plain Java companion to Module 01 using the official MCP Java SDK, with stdio server, demo client, mock tools/resources/prompts, and a captured terminal demo transcript. Path: `Phase9_Dynamic_Agentic_RAG_MCP/module_04_java_mcp_benefits_assistant/`.
  - Module 05 Spring Boot MCP + RAG Benefits Microservice: ✅ Built — Spring Boot WebMVC microservice using Spring AI MCP annotations, Streamable HTTP `/mcp`, REST inspection endpoints, mock primary contribution/savings account tools, bundled markdown RAG docs, and tests for Spring context + retrieval intent ranking. Path: `Phase9_Dynamic_Agentic_RAG_MCP/module_05_springboot_mcp_benefits_assistant/`.
  - Existing MCP+RAG prototype: ✅ Built — `qwen2.5:3b` agent answers primary contribution/savings account questions via a FastMCP retrieval server over local reference docs. Path: `Phase9_Dynamic_Agentic_RAG_MCP/mcp_benefits_example/`.
- Phase 10 Google ADK Series: 🔄 In Progress — cloud-native Google ADK phase (Vertex Gemini, NOT Ollama/local-first).
  - Module 03 Python ADK Grocery Platform: 🔄 In Progress — Python ADK 2.x (google-adk 2.4) grocery-delivery concierge on Vertex AI (`gemini-flash-latest`, `GOOGLE_CLOUD_LOCATION=global`). Multi-agent (concierge + catalog/checkout-security sub-agents + remote A2A delivery-scheduler), A2UI grocery cards, UCP checkout + AP2 mandate sim, and a full security stack from the Day 4/5 "Vibe Coding" papers: SPIFFE-style signed agent identity + spoof detection, JIT downscoped tokens, hybrid policy gate, Vibe-Diff HITL, AgBOM + trust decay + circuit breaker, runtime `SecurityGuardianPlugin`. **Eval is the centerpiece** — 4 confidence layers: built-in autoraters (`final_response_quality`, `safety`), **LLM-as-Judge** (`security_llm_judge`), **deterministic ground truth** (`security_compliance`, `app/security_judge.grade_trajectory`), and **Agent-as-a-Judge** (`security_auditor` that re-runs the verification tools; `scripts/run_security_audit.py`). Live scores: safety 1.0, security_llm_judge 4.71/5, security_compliance 5.0/5, agent-judge agrees with ground truth 4/4. Strictly grocery domain — NO benefits/HSA/401k/retirement terms (enforced by a domain-hygiene eval check). 18 offline pytest pass with no cloud. Path: `Phase10_Google_ADK_Series/project_03_python_adk_grocery_platform/`. Branch `phase10-module3-python-adk-grocery`.

## Installed Packages / Module Dependencies (Phase 5+)
- langchain-openai, langgraph, crewai, redis
- prometheus-client, prometheus-fastapi-instrumentator
- python-jose[cryptography], passlib[bcrypt]
- Phase 8: slack_bolt, PyGithub, fastapi, uvicorn, stripe (sim), pypdf (capstone PDF support)
- Phase 9 module deps: `mcp` (Module 01); Module 02 + prototype add `langchain-mcp-adapters`, `langgraph`, `langchain-openai`, `numpy`, `openai`

## Git Branches
- main: original 8 phases merged; Phase 9 is the new MCP expansion track
- Feature branches per phase (phase5… through phase8…) merged via PR
- Tag `v1.0`: pre-restructure snapshot of the full 8-phase roadmap
