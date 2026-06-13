# AskMyDocs Pro — Capstone v2 Upgrade Spec
## Dynamic LLM Providers + Optional MCP/RAG Orchestration

> **Build-ready spec.** Hand this whole file to a coding agent (e.g. `/ultracode`). It is grounded in the *actual* `backend/main.py` as of 2026-06-12.
> **Scope:** `Phase8_Integrations_Shipping/project_06_capstone_launch/` + three README updates. Nothing else.
> **Prime directive:** Ollama stays the default; the local app must keep working with **no AWS credentials**; **no real AWS calls** in tests; do it on a feature branch.

---

## 0. How to use this doc

1. Read `CLAUDE.md` (repo root) and this file fully before editing.
2. Work on branch `phase8-dynamic-providers-mcp`.
3. Implement Part A (providers) first — it is independent and low-risk. Then Part B (MCP, off by default). Then docs + tests.
4. Run the smoke checks in Part D. Do **not** call real AWS or require live credentials.
5. A copy-paste prompt is in Appendix A if you want the short form.

---

## 1. Goal & non-goals

**Goal:** Let the deployed app generate text through a swappable provider — **Ollama (default) / Bedrock / SageMaker / Hugging Face** — selected by one env var, and add an *optional* MCP+RAG orchestration layer that can dynamically choose how to answer. Preserve every existing behavior when the new features are off.

**Non-goals (v2):**
- No change to embeddings — they stay local on Ollama `nomic-embed-text`.
- No real AWS deployment, no Terraform, no live endpoints in this task.
- No change to auth, billing, tenancy, DB schema, or the WebSocket wire protocol.
- No new vector DB — keep the NumPy/SQLite RAG store.

---

## 2. Current state (ground truth — do not re-discover)

Single-file backend: `backend/main.py` (~1400 lines). Relevant anchors:

| What | Where | Detail |
|---|---|---|
| Global LLM client | line ~126 | `ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")` |
| Config | lines ~106-126 | `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`), `AI_MODEL` (default `gemma3:4b`) |
| Embeddings | `RAGEngine.embed_text` ~419 | `ollama.embeddings.create(model="nomic-embed-text", ...)` + hash fallback — **leave as-is** |
| Retrieval | `RAGEngine.find_relevant_chunks` ~455 | tenant-scoped (`DocumentChunkModel.tenant_id`), NumPy cosine |
| Prompt builder | `RAGEngine.build_rag_prompt` ~511 | returns a single string |
| **Call site 1** | `/chat` ~990 | `ollama.chat.completions.create(...)` non-streaming |
| **Call site 2** | `/ws/chat` ~1132 | `ollama.chat.completions.create(..., stream=True)` token loop |
| **Call site 3** | `/slack/ask` ~1296 | `ollama.chat.completions.create(...)` non-streaming |
| Usage logging | after each call site | `UsageLogModel(... model=AI_MODEL, input_tokens, output_tokens, cost_usd ...)` |
| Tenancy | JWT carries `tenant_id`; `get_current_user`, `get_tenant_and_enforce_quota` | every query filters by `tenant_id` |

All three call sites build `messages=[{"role":"user","content": prompt}]` with `temperature=0.2`. Token counts are heuristics: `len(text.split()) * 4 // 3`.

---

## 3. Target architecture

```
  /chat   /slack/ask        /ws/chat (stream)
     │         │                  │
     ▼         ▼                  ▼
  ┌────────────────────────────────────────────┐
  │  answer_question()  /  provider.stream()    │   ← shared generation path
  │  (Part B orchestrator sits here, gated by   │
  │   ENABLE_MCP; default = today's RAG path)   │
  └───────────────────┬────────────────────────┘
                      │ get_provider()  (AI_PROVIDER)
        ┌─────────────┼───────────────┬───────────────┐
        ▼             ▼               ▼               ▼
   OllamaProvider  BedrockProvider  SageMaker...   HFProvider
   (default)       Converse API     invoke_endpoint  InferenceClient
        │
   embeddings stay here → ollama.embeddings.create(nomic-embed-text)   (unchanged)
```

Two new modules in `backend/`: `providers.py` (Part A) and `orchestrator.py` + `mcp_server.py` (Part B). `main.py` is refactored to route the 3 call sites through them.

---

## 4. Part A — Provider abstraction  *(do this first)*

### 4.1 New file: `backend/providers.py`

Define a normalized interface plus a factory. Keep boto3 imports **lazy** (inside the AWS providers) so the app imports fine without boto3/creds.

```python
# ═══════════════════════════════════════════════════════════════════════════════
#  providers.py — one LLM interface, swappable backends
#  WHY: the deployed app cannot reach the Mac's Ollama. Abstract generation so
#  local vs cloud is ONE env var (AI_PROVIDER), not a code rewrite. Ollama stays
#  the default; AWS SDKs are imported lazily so no creds are needed locally.
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator
import os

@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    model: str

def _estimate_tokens(text: str) -> int:          # preserve current heuristic
    return max(1, len(text.split()) * 4 // 3)

class LLMProvider(ABC):
    name: str
    model: str
    @abstractmethod
    def complete(self, messages: list[dict], *, temperature: float = 0.2,
                 max_tokens: int = 800) -> Completion: ...
    @abstractmethod
    def stream(self, messages: list[dict], *, temperature: float = 0.2,
               max_tokens: int = 800) -> Iterator[str]: ...

# ─── default: Ollama via the existing OpenAI-compatible client ──────────────────
class OllamaProvider(LLMProvider):
    name = "ollama"
    def __init__(self):
        from openai import OpenAI
        self.model = os.getenv("AI_MODEL", "gemma3:4b")
        self._c = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL",
                         "http://localhost:11434/v1"), api_key="ollama")
    def complete(self, messages, *, temperature=0.2, max_tokens=800):
        r = self._c.chat.completions.create(model=self.model, messages=messages,
                                            temperature=temperature, max_tokens=max_tokens)
        text = (r.choices[0].message.content or "").strip()
        u = getattr(r, "usage", None)
        return Completion(text,
                          getattr(u, "prompt_tokens", None) or _estimate_tokens(messages[-1]["content"]),
                          getattr(u, "completion_tokens", None) or _estimate_tokens(text),
                          self.model)
    def stream(self, messages, *, temperature=0.2, max_tokens=800):
        s = self._c.chat.completions.create(model=self.model, messages=messages,
                                            temperature=temperature, max_tokens=max_tokens, stream=True)
        for chunk in s:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

# ─── AWS Bedrock — Converse / ConverseStream ────────────────────────────────────
class BedrockProvider(LLMProvider):
    name = "bedrock"
    def __init__(self):
        import boto3                                   # lazy: only when selected
        self.model = os.environ["BEDROCK_MODEL_ID"]
        self._c = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    @staticmethod
    def _to_bedrock(messages):
        # split optional system; convert {"role","content"} → Bedrock content blocks
        system = [{"text": m["content"]} for m in messages if m["role"] == "system"]
        msgs = [{"role": m["role"], "content": [{"text": m["content"]}]}
                for m in messages if m["role"] != "system"]
        return system, msgs
    def complete(self, messages, *, temperature=0.2, max_tokens=800):
        system, msgs = self._to_bedrock(messages)
        kw = {"modelId": self.model, "messages": msgs,
              "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature}}
        if system: kw["system"] = system
        r = self._c.converse(**kw)
        text = r["output"]["message"]["content"][0]["text"].strip()
        u = r.get("usage", {})
        return Completion(text, u.get("inputTokens", _estimate_tokens(messages[-1]["content"])),
                          u.get("outputTokens", _estimate_tokens(text)), self.model)
    def stream(self, messages, *, temperature=0.2, max_tokens=800):
        system, msgs = self._to_bedrock(messages)
        kw = {"modelId": self.model, "messages": msgs,
              "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature}}
        if system: kw["system"] = system
        r = self._c.converse_stream(**kw)
        for event in r["stream"]:
            if "contentBlockDelta" in event:
                yield event["contentBlockDelta"]["delta"]["text"]

# ─── AWS SageMaker — invoke_endpoint (HF TGI container) ──────────────────────────
class SageMakerProvider(LLMProvider):
    name = "sagemaker"
    def __init__(self):
        import boto3
        self.model = os.environ["SAGEMAKER_ENDPOINT_NAME"]
        self._c = boto3.client("sagemaker-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    @staticmethod
    def _flatten(messages):                            # TGI generate wants a single prompt
        return "\n\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\n\nassistant:"
    def complete(self, messages, *, temperature=0.2, max_tokens=800):
        import json
        prompt = self._flatten(messages)
        payload = {"inputs": prompt,
                   "parameters": {"max_new_tokens": max_tokens, "temperature": max(temperature, 0.01),
                                  "return_full_text": False}}
        r = self._c.invoke_endpoint(EndpointName=self.model, ContentType="application/json",
                                    Body=json.dumps(payload))
        body = json.loads(r["Body"].read())
        text = (body[0]["generated_text"] if isinstance(body, list) else body["generated_text"]).strip()
        return Completion(text, _estimate_tokens(prompt), _estimate_tokens(text), self.model)
    def stream(self, messages, *, temperature=0.2, max_tokens=800):
        # invoke_endpoint_with_response_stream where the container supports it (TGI SSE).
        # Parsing depends on container; fall back to non-streaming if unavailable.
        import json
        prompt = self._flatten(messages)
        payload = {"inputs": prompt,
                   "parameters": {"max_new_tokens": max_tokens, "temperature": max(temperature, 0.01),
                                  "return_full_text": False}}
        try:
            r = self._c.invoke_endpoint_with_response_stream(
                EndpointName=self.model, ContentType="application/json", Body=json.dumps(payload))
            for event in r["Body"]:
                part = event.get("PayloadPart", {}).get("Bytes", b"").decode("utf-8", "ignore")
                for line in part.splitlines():
                    line = line.removeprefix("data:").strip()
                    if not line or line == "[DONE]":
                        continue
                    try:
                        tok = json.loads(line)
                        yield tok.get("token", {}).get("text") or \
                              tok.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    except Exception:
                        continue
        except Exception:                              # endpoint can't stream → one-shot
            yield self.complete(messages, temperature=temperature, max_tokens=max_tokens).text

# ─── optional / dev: Hugging Face Serverless Inference (free tier) ──────────────
class HFProvider(LLMProvider):
    name = "hf"
    def __init__(self):
        from huggingface_hub import InferenceClient
        self.model = os.getenv("HF_MODEL_ID", "meta-llama/Llama-3.2-3B-Instruct")
        self._c = InferenceClient(model=self.model, token=os.getenv("HF_TOKEN"))
    def complete(self, messages, *, temperature=0.2, max_tokens=800):
        r = self._c.chat_completion(messages=messages, max_tokens=max_tokens,
                                    temperature=temperature)
        text = r.choices[0].message.content.strip()
        return Completion(text, _estimate_tokens(messages[-1]["content"]),
                          _estimate_tokens(text), self.model)
    def stream(self, messages, *, temperature=0.2, max_tokens=800):
        for chunk in self._c.chat_completion(messages=messages, max_tokens=max_tokens,
                                             temperature=temperature, stream=True):
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

# ─── factory: env var picks the backend; default keeps local app unchanged ──────
_PROVIDERS = {"ollama": OllamaProvider, "bedrock": BedrockProvider,
              "sagemaker": SageMakerProvider, "hf": HFProvider}
_cache: dict[str, LLMProvider] = {}

def get_provider() -> LLMProvider:
    key = os.getenv("AI_PROVIDER", "ollama").lower()
    if key not in _PROVIDERS:
        raise ValueError(f"Unknown AI_PROVIDER={key!r}. Choose: {list(_PROVIDERS)}")
    if key not in _cache:
        _cache[key] = _PROVIDERS[key]()
    return _cache[key]
```

### 4.2 Env vars (add to `.env.example` + document in README)

```dotenv
# ─── LLM provider selection ───────────────────────────────────────────────────
AI_PROVIDER=ollama                 # ollama (default) | bedrock | sagemaker | hf
# AWS — only read when AI_PROVIDER=bedrock or sagemaker
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
SAGEMAKER_ENDPOINT_NAME=askmydocs-llm
# Hugging Face — only read when AI_PROVIDER=hf
HF_TOKEN=
HF_MODEL_ID=meta-llama/Llama-3.2-3B-Instruct
# Embeddings stay local (unchanged)
# ─── MCP orchestration (optional, OFF by default) ─────────────────────────────
ENABLE_MCP=false
MCP_ROUTER_MODEL=qwen2.5:3b
```

> Credentials use the standard AWS chain (env / `~/.aws` / instance role) — never hard-code keys. If `AI_PROVIDER` is `bedrock`/`sagemaker` but creds are missing, the provider should raise a clear error **only when selected**; `ollama` default must never touch boto3.

### 4.3 Refactor the 3 call sites in `main.py`

Replace each `ollama.chat.completions.create(...)` block with the provider interface. Keep usage logging, cost math, citations, and the WS protocol **byte-for-byte identical** apart from the swapped call.

**`/chat` (~990) and `/slack/ask` (~1296)** — non-streaming:
```python
provider = get_provider()
result = provider.complete([{"role": "user", "content": prompt}],
                           temperature=0.2, max_tokens=800)   # 400 for slack
answer        = result.text
input_tokens  = result.input_tokens
output_tokens = result.output_tokens
model_name    = result.model        # use in UsageLogModel(model=...) and ChatResponse(model=...)
```

**`/ws/chat` (~1132)** — streaming:
```python
provider = get_provider()
full_response = ""
for delta in provider.stream([{"role": "user", "content": prompt}],
                             temperature=0.2, max_tokens=800):
    full_response += delta
    await websocket.send_json({"type": "token", "content": delta})
    await asyncio.sleep(0)
```

Leave the global `ollama` client in place **only** for `RAGEngine.embed_text` (embeddings unchanged). Optionally rename it to `embed_client` for clarity. Replace `AI_MODEL` in the `UsageLogModel`/`ChatResponse` for the three chat paths with `model_name` from the provider.

### 4.4 `backend/requirements.txt`

Add (keep MCP deps in a separate optional file so the default install stays lean/RAM-safe):
```
boto3>=1.34.0
huggingface_hub>=0.24.0
```

---

## 5. Part B — Optional MCP + RAG orchestration  *(gated by `ENABLE_MCP`, default false)*

When `ENABLE_MCP=false`, the answer path is **exactly today's**: retrieve chunks → `build_rag_prompt` → `provider.complete`. The MCP layer must be additive and fully bypassed when off.

### 5.1 Shared answer path

Extract the current `/chat` body into one reusable function so both the legacy and MCP paths live in one place:

```python
def answer_question(*, question, tenant, tenant_id, document_id, top_k, db) -> dict:
    """Returns {answer, sources, input_tokens, output_tokens, model}."""
    if not _env_bool("ENABLE_MCP"):
        return _rag_answer(question, tenant, tenant_id, document_id, top_k, db)  # today's logic
    try:
        from orchestrator import run_orchestrated
        return run_orchestrated(question=question, tenant=tenant, tenant_id=tenant_id,
                                document_id=document_id, top_k=top_k, db=db)
    except Exception as e:                              # any MCP failure → safe fallback
        logger.warning(f"MCP orchestration failed, falling back to RAG: {e}")
        return _rag_answer(question, tenant, tenant_id, document_id, top_k, db)
```
`/chat` calls `answer_question(...)`. `/ws/chat` keeps streaming via `provider.stream` on the RAG prompt (MCP streaming is out of scope for v2 — note it).

### 5.2 New file: `backend/mcp_server.py` — tenant-scoped tools

A local FastMCP (stdio) server exposing a **fixed allowlist** of read-only tools. **Tenant id is bound by the orchestrator, never chosen by the model** (see 5.4):

| Tool | Args (model-visible) | Returns |
|---|---|---|
| `search_tenant_docs` | `query`, `k` | top-k chunks for the tenant (reuses `RAGEngine`) |
| `list_documents` | — | tenant's documents (id, filename, status) |
| `get_document_excerpt` | `document_id`, `max_chars` | excerpt **only if the doc belongs to the tenant** |
| `usage_summary` | — | tenant's month-to-date usage |

Every tool runs its DB query filtered by the injected `tenant_id`. `get_document_excerpt` must 404/empty if the doc's `tenant_id` ≠ caller's. No write tools. No tool that can read across tenants.

### 5.3 New file: `backend/orchestrator.py` — dynamic flow (explicit LangGraph)

- Router model: `MCP_ROUTER_MODEL` (`qwen2.5:3b`) via `ChatOpenAI(base_url=OLLAMA_BASE_URL, ...)` — **not gemma3** (weak at tool-calling).
- Load MCP tools with `langchain-mcp-adapters` (`MultiServerMCPClient` → `get_tools()`), then **wrap each tool to inject the authenticated `tenant_id`** before exposing to the model.
- Explicit `StateGraph`: `router` (bind_tools, decide) → `tools` (`ToolNode`) → loop → `generate`.
- **Flow modes** the router may pick: `direct` (no retrieval), `rag_only` (one retrieval), `mcp_only` (tools, no vector RAG), `rag+mcp` (both). Record the chosen mode in the response metadata for debugging.
- Final generation goes through `get_provider().complete(...)` so the provider matrix still applies.
- Hard cap tool-call iterations (e.g. ≤4) to bound latency/cost.

### 5.4 Tenant isolation & allowlist (security — required)

1. `tenant_id` comes from the JWT (`get_current_user`) and is injected server-side into every tool call via a closure/partial. The model can request `search_tenant_docs(query=...)` but **cannot** set or change `tenant_id`.
2. Only the four tools above are registered; reject any other tool name.
3. `get_document_excerpt` re-checks `DocumentModel.tenant_id == tenant_id`.
4. Add a test that a tenant-A token can never retrieve tenant-B content through any tool.

### 5.5 Optional MCP deps — `backend/requirements-mcp.txt`

```
mcp>=1.0.0
langchain-mcp-adapters>=0.1.0
langgraph>=0.2.0
langchain-openai>=0.1.0
```
Only needed when `ENABLE_MCP=true`. Document `ollama pull qwen2.5:3b` as a prerequisite for the MCP path.

---

## 6. Part C — Docs to update

1. **`Phase8_Integrations_Shipping/README.md`** — replace any Hugging Face-only note with the **provider matrix** (Section 9 below): Ollama local default · Bedrock recommended AWS · SageMaker custom-model · Hugging Face optional/dev.
2. **`Phase8_Integrations_Shipping/project_06_capstone_launch/README.md`** — add a "Cloud providers & MCP" section: every `AI_PROVIDER` value with required env vars, the MCP flow + `ENABLE_MCP`, the minimum AWS IAM permissions (`bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`; or `sagemaker:InvokeEndpoint`, `sagemaker:InvokeEndpointWithResponseStream`), and how to test locally with **no real AWS creds** (mocked).
3. **`Phase6_Production_Enterprise/project_03_aws_deployment/README.md`** — explain that `CLOUD_MODE` can now point the app at **Bedrock or SageMaker** via `AI_PROVIDER` instead of the current hosted-LLM stub.

---

## 7. Part D — Tests / smoke checks (no real AWS)

Add `backend/tests/` with pytest. Mock all cloud SDKs — **never hit AWS**.

| Test | Asserts |
|---|---|
| `test_provider_selection` | `AI_PROVIDER` unset → `OllamaProvider`; `bedrock`→`BedrockProvider`; `sagemaker`→`SageMakerProvider`; `hf`→`HFProvider`; bad value → `ValueError` |
| `test_ollama_default` | with no AWS env and no boto3 creds, `get_provider()` works and importing `providers` never imports boto3 |
| `test_bedrock_mocked` | patch `boto3.client` so `.converse()` returns a canned payload; `complete()` parses text + `inputTokens/outputTokens`; `converse_stream` yields deltas |
| `test_sagemaker_mocked` | patch `boto3.client` so `.invoke_endpoint()` returns `[{"generated_text": ...}]`; `complete()` parses it |
| `test_mcp_disabled_equals_rag` | `ENABLE_MCP=false`: `answer_question` calls `rag.find_relevant_chunks` + `provider.complete` and does **not** import/launch the orchestrator |
| `test_tenant_isolation` | a tool call bound to tenant A cannot return tenant B's document excerpt |

Mocking pattern (no creds):
```python
import providers
def test_bedrock_mocked(monkeypatch):
    fake = MagicMock()
    fake.converse.return_value = {"output": {"message": {"content": [{"text": "hi"}]}},
                                  "usage": {"inputTokens": 5, "outputTokens": 2}}
    monkeypatch.setattr("boto3.client", lambda *a, **k: fake)
    monkeypatch.setenv("AI_PROVIDER", "bedrock"); monkeypatch.setenv("BEDROCK_MODEL_ID", "x")
    providers._cache.clear()
    out = providers.get_provider().complete([{"role": "user", "content": "q"}])
    assert out.text == "hi" and out.input_tokens == 5
```
Run: `cd backend && pip install -r requirements.txt pytest && pytest -q`. (Install `requirements-mcp.txt` only for the MCP/isolation tests.)

---

## 8. File change list

**New**
- `backend/providers.py`
- `backend/orchestrator.py`
- `backend/mcp_server.py`
- `backend/requirements-mcp.txt`
- `backend/tests/test_providers.py`, `backend/tests/test_orchestrator.py`

**Modified**
- `backend/main.py` — 3 call sites → provider; extract `_rag_answer` + `answer_question`; keep embeddings on Ollama; report `provider.model`
- `backend/requirements.txt` — add `boto3`, `huggingface_hub`
- `.env.example` — new provider + MCP vars
- `README.md` (capstone), `Phase8_Integrations_Shipping/README.md`, `Phase6_Production_Enterprise/project_03_aws_deployment/README.md`

---

## 9. Provider matrix (for the docs)

| Provider | `AI_PROVIDER` | Role | Streaming | Creds | Cost shape |
|---|---|---|---|---|---|
| Ollama | `ollama` | **Local default** | yes | none | free (local) |
| Bedrock | `bedrock` | **Recommended AWS** — serverless, managed | yes (ConverseStream) | AWS chain | per-token, no infra |
| SageMaker | `sagemaker` | Your own/HF model on an endpoint | best-effort | AWS chain | **Serverless = scale-to-zero**; real-time = always-on GPU |
| Hugging Face | `hf` | Optional dev/free | yes | `HF_TOKEN` | free tier / PRO $9-mo |

**Cost guardrails:** prefer Bedrock or **SageMaker Serverless Inference** (scale-to-zero) over an always-on real-time endpoint — a forgotten GPU endpoint is the classic surprise bill. Add an endpoint-teardown note + AWS budget alarm to the capstone README.

---

## 10. Acceptance criteria

- [ ] App boots and all existing endpoints work with **no env changes** (Ollama default) and **no boto3 creds**.
- [ ] `importlib.import_module("providers")` does not import boto3 unless an AWS provider is selected.
- [ ] `AI_PROVIDER=bedrock|sagemaker|hf` route `/chat`, `/ws/chat`, `/slack/ask` through the provider; usage logging + citations + WS protocol unchanged; `model` reflects the active backend.
- [ ] `ENABLE_MCP=false` ⇒ identical behavior to current `main.py` (verified by `test_mcp_disabled_equals_rag`).
- [ ] `ENABLE_MCP=true` ⇒ orchestrator chooses among direct/rag_only/mcp_only/rag+mcp, tools are tenant-bound, ≤4 tool iterations, falls back to RAG on error.
- [ ] Cross-tenant access is impossible through any MCP tool (`test_tenant_isolation` passes).
- [ ] All tests pass with **zero** real AWS calls.
- [ ] Three READMEs updated; `.env.example` documents every new var.

---

## 11. Guardrails & constraints (from `CLAUDE.md`)

- Ollama default; embeddings stay local `nomic-embed-text`; NumPy cosine (no new vector DB).
- **No PyTorch / sentence-transformers locally** — boto3 + huggingface_hub are thin API clients; MCP deps are optional and only pulled for `ENABLE_MCP=true`.
- Router model is `qwen2.5:3b` (RAM-safe, strong tool-calling), not gemma3.
- House style: `═══` header blocks, WHY comments, section dividers, no docstrings on obvious functions.
- Feature branch `phase8-dynamic-providers-mcp`; do not run real AWS deployment.

---

## Appendix A — paste-ready `/ultracode` prompt

> Implement the upgrade described in `Phase8_Integrations_Shipping/project_06_capstone_launch/UPGRADE_SPEC_dynamic_providers_mcp.md`. Read `CLAUDE.md` and that spec first. Work on branch `phase8-dynamic-providers-mcp`. Scope strictly to the capstone project + the three READMEs named in the spec.
>
> Part A (do first): create `backend/providers.py` with an `LLMProvider` interface (`complete` + `stream`, normalized `Completion`) and a `get_provider()` factory keyed on `AI_PROVIDER` = ollama|bedrock|sagemaker|hf. Ollama default wraps the existing OpenAI client; Bedrock uses boto3 `converse`/`converse_stream`; SageMaker uses boto3 `invoke_endpoint`/`invoke_endpoint_with_response_stream`; HF uses `huggingface_hub.InferenceClient`. Import boto3 lazily. Refactor the three call sites in `backend/main.py` (`/chat` ~990, `/ws/chat` ~1132, `/slack/ask` ~1296) to use the provider; keep usage logging, citations, and the WS protocol identical; keep embeddings on Ollama. Add `boto3` + `huggingface_hub` to `requirements.txt` and the new env vars to `.env.example`.
>
> Part B (gated by `ENABLE_MCP`, default false → behavior must equal today's RAG): add `backend/mcp_server.py` (FastMCP stdio, tenant-scoped tools `search_tenant_docs`, `list_documents`, `get_document_excerpt`, `usage_summary`) and `backend/orchestrator.py` (explicit LangGraph router on `qwen2.5:3b` via `langchain-mcp-adapters`, modes direct/rag_only/mcp_only/rag+mcp, ≤4 tool iterations, final generation through `get_provider()`). Bind `tenant_id` server-side from the JWT — the model must never set it. Allowlist only those four tools. Put MCP deps in `backend/requirements-mcp.txt`. Extract `_rag_answer` + `answer_question` in `main.py` with a safe fallback to RAG on any MCP error.
>
> Part C: update the capstone README, `Phase8_Integrations_Shipping/README.md` (provider matrix), and `Phase6_Production_Enterprise/project_03_aws_deployment/README.md` (CLOUD_MODE → Bedrock/SageMaker).
>
> Part D: add `backend/tests/` proving provider selection, Ollama-default-without-boto3, mocked Bedrock + SageMaker (no real AWS), `ENABLE_MCP=false` == current RAG, and tenant isolation. Run the tests and summarize changed files. Do not call real AWS or require live credentials.

---

## Sources (provider APIs & costs)

- [Deploy Hugging Face models to Amazon SageMaker](https://huggingface.co/docs/sagemaker/inference)
- [Host HF models with SageMaker Serverless Inference (AWS)](https://aws.amazon.com/blogs/machine-learning/host-hugging-face-transformer-models-using-amazon-sagemaker-serverless-inference/)
- [Amazon Bedrock Converse API (boto3)](https://docs.aws.amazon.com/bedrock/latest/userguide/converse-api.html)
- [Hugging Face Inference pricing 2026](https://klymentiev.com/blog/huggingface-inference-api)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) · [MCP in LangChain docs](https://docs.langchain.com/oss/python/langchain/mcp)
- [Ollama tool calling guide](https://localaimaster.com/blog/ollama-tool-calling-guide)
