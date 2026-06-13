# Capstone — Enterprise Assistant Hub

The Phase 9 capstone ties together the MCP learning modules into a small
enterprise assistant hub. It reuses the Phase 8 patterns that matter here
without rebuilding the full SaaS app: tenant context, RAG isolation, metering
metadata, provider abstraction, and audit logs.

All account data is fictional. Outputs are educational only and are not
financial, tax, legal, or investment advice.

## What Is Built

- `providers.py` — `AI_PROVIDER=ollama|bedrock|sagemaker|hf` with lazy cloud clients.
- `mcp_gateway.py` — tenant tool allowlists, tenant-bound local tools, and an external
  `langchain-mcp-adapters` hook for the Module 02 benefits MCP server.
- `retrieval.py` — tenant-scoped heading chunks, local Ollama embeddings, NumPy cosine,
  keyword/topic rerank, and the Module 02 employee-vs-combined 401(k) intent boost.
- `orchestrator.py` — route selection for `direct`, `mcp_only`, `rag_only`, and `mcp+rag`,
  bounded to four planned tool calls with RAG fallback on MCP errors.
- `hub.py` — CLI plus a thin FastAPI `/chat` endpoint using mock API-key tenant auth.
- `audit.py` — one JSONL record per request.

## Run Locally

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub
source ~/Documents/my-ai-project/ai-env/bin/activate
pip install -r requirements.txt

ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

AI_PROVIDER=ollama python hub.py --tenant acme \
  "I contribute 6%. Am I getting the full match, and what is the 2026 employee 401k limit?"
```

To run only tenant RAG:

```bash
ENABLE_MCP=false AI_PROVIDER=ollama python hub.py --tenant acme \
  "What is the 2026 HSA family contribution limit?"
```

## Optional FastAPI

```bash
uvicorn hub:app --reload --port 8080
```

```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-acme-key" \
  -d '{"question":"What is the 2026 employee 401k contribution limit?"}'
```

The API key map in `config/tenants.yaml` is a mock for learning. Production would
plug into the Phase 8 JWT and tenant model.

## Provider Matrix

| Provider | Env | Role | Notes |
|---|---|---|---|
| Ollama | `AI_PROVIDER=ollama` | Local default | Uses `AI_MODEL`, default `qwen2.5:3b`. |
| Bedrock | `AI_PROVIDER=bedrock` | Recommended AWS path | Requires `BEDROCK_MODEL_ID`; uses lazy `boto3` Converse APIs. |
| SageMaker | `AI_PROVIDER=sagemaker` | Custom endpoint path | Requires `SAGEMAKER_ENDPOINT_NAME`; mock-tested, no real calls in tests. |
| Hugging Face | `AI_PROVIDER=hf` | Optional dev path | Uses lightweight `httpx`, no PyTorch or Transformers. |

Embeddings stay local through Ollama `nomic-embed-text` whenever embeddings are
available. Tests and offline runs fall back to lexical retrieval.

## Tenancy And Tools

`config/tenants.yaml` defines each tenant's API keys, allowed tools, and corpus.
The gateway rejects disallowed or unknown tools before execution. Hub-owned tools
inject tenant context server-side. Existing Module 02 MCP tools do not accept
tenant IDs, so they are only exposed where the configured corpus and allowlist are
tenant-safe.

Built-in tenants:

- `acme` / `dev-acme-key` — benefits account tools plus tenant RAG.
- `globex` / `dev-globex-key` — tenant RAG only.

## Tests

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub
~/Documents/my-ai-project/ai-env/bin/python -m pytest -q tests
```

The tests mock cloud SDKs and do not require Ollama, AWS credentials, Hugging Face
credentials, or a running MCP server.
