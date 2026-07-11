# Phase 10 Module 03: Python ADK Grocery Platform

This module is a local-first learning project for Python ADK 2.x on Vertex AI.
It uses a fictional grocery delivery platform to teach:

- ADK agent tools and specialist sub-agents
- A2UI dynamic UI payloads with grocery product imagery
- UCP-style checkout transaction state
- AP2-style payment mandate simulation
- A2A-style remote delivery scheduling boundary
- Signed agent identity and spoofing defenses
- JIT downscoped tokens
- Vibe-Diff human approval before checkout
- Hybrid policy gate, trust decay, circuit breaker, and AgBOM
- Spec-driven development with Gherkin scenarios

All data is fictional and educational.

## Project Structure

```text
project_03_python_adk_grocery_platform/
├── app/
│   ├── agent.py          # ADK concierge and specialist agents (+ guardian plugin)
│   ├── grocery.py        # Catalog, A2UI, cart, UCP, AP2 helpers
│   ├── security.py       # Identity, JIT, policy, Vibe-Diff, AgBOM
│   ├── security_judge.py # Deterministic grader + Agent-as-a-Judge + guardian plugin
│   ├── a2a_client.py     # Signed local A2A boundary simulation
│   └── tools.py          # Tool functions exposed to ADK
├── delivery-scheduler/   # Remote A2A specialist scaffold
├── frontend/             # Dedicated React A2UI renderer
├── scripts/
│   └── run_security_audit.py  # Agent-as-a-Judge demo over sample trajectories
├── specs/                # Spec-driven checkout scenarios
└── tests/                # Offline pytest + ADK eval dataset & LLM/agent judges
```

## Setup

```bash
uv sync
```

The ADK app is configured for Vertex AI with `GOOGLE_CLOUD_LOCATION=global`.
Live agent runs require Application Default Credentials and the Agent Platform
API enabled in your Google Cloud project.

For local code checks, no live model call is required:

```bash
uv run pytest -q tests/unit tests/integration/test_agent.py
```

Expected output:

```text
18 passed
```

## Try the Tools Offline

```bash
uv run python - <<'PY'
from app.tools import render_grocery_a2ui, prepare_checkout

print(render_grocery_a2ui("breakfast")["a2ui"]["component"])
print(prepare_checkout(
    [{"sku": "produce-berries", "quantity": 1}, {"sku": "dairy-yogurt", "quantity": 1}],
    delivery_window="09:00-11:00",
    approved=False,
)["status"])
PY
```

Expected output:

```text
GroceryCatalogGrid
needs_human_approval
```

## Run the ADK App

```bash
agents-cli playground
```

Useful prompts:

```text
Show me breakfast groceries as A2UI cards with images.
Create a cart with strawberries and yogurt, schedule delivery, and explain each security gate before checkout.
Show me the Agent Bill of Materials for this module.
```

If you see a `403 SERVICE_DISABLED` error, enable the Agent Platform API for
the active Google Cloud project and retry after propagation.

## Dedicated A2UI Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5174`. The renderer shows how an
agent-returned A2UI payload becomes grocery cards with product images, add-to-cart
actions, and visible security status chips.

## Remote Delivery Scheduler

The nested `delivery-scheduler/` project is scaffolded as an A2A-capable ADK
service. Its deterministic scheduling logic lives in:

```text
delivery-scheduler/app/scheduler.py
```

The main concierge currently uses a signed local boundary simulation in
`app/a2a_client.py` so tests remain offline. Start the scheduler separately when
you want to inspect the A2A server and agent card:

```bash
cd delivery-scheduler
uv sync
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8001
```

## Evaluation — four layers of confidence

Security is the lesson here, so the checkout is graded four ways, each stronger
than the last. A fluent-but-insecure answer has to beat all of them:

| Layer | What it is | Where | Needs Vertex? |
|---|---|---|---|
| **Built-in autoraters** | `final_response_quality`, `safety` | `eval_config.yaml` | yes |
| **LLM-as-Judge** | a Gemini referee scores the *security behaviour* against a rubric (JIT, spoof-ID, Vibe-Diff, injection, domain) | `security_llm_judge` in `eval_config.yaml` | yes |
| **Deterministic ground truth** | pure-Python grader re-derives the invariants straight from the trace — cannot be talked up | `security_compliance` in `eval_config.yaml`, `grade_trajectory()` | no |
| **Agent-as-a-Judge** | an ADK judge agent that **re-runs the verification tools** (`verify_agent_assertion`, `verify_jit_token`, `hybrid_policy_gate`) instead of trusting the transcript | `security_auditor` + `scripts/run_security_audit.py` | yes |

Why the extra layers? A prompt-only LLM judge can be fooled by a trajectory that
*claims* `identity: trusted`. The **Agent-as-a-Judge** re-verifies the SPIFFE-style
assertion and the JIT token's cryptographic scope itself, so its verdict is
grounded in tool-checked facts — that is what earns the extra confidence. The
**deterministic** grader is the offline ground truth both are measured against.

There is also a **runtime** face of the judge: `SecurityGuardianPlugin` (wired into
`App(plugins=[...])`) intercepts the `prepare_checkout` tool call and blocks any AP2
mandate that would escape approval, policy, or JIT scoping — before it is minted.

### Run the eval flywheel (built-ins + LLM-as-Judge + deterministic)

```bash
# gemini-flash-latest is served on the global endpoint
GOOGLE_CLOUD_LOCATION=global agents-cli eval run
```

Latest live run (7 cases, all valid, 0 errors):

```text
Metric                       mean     pass_rate   notes
final_response_quality_v1    0.72     0.57        general answer quality
safety_v1                    1.00     1.00        policy-compliant output
security_llm_judge           4.71/5   —           LLM-as-Judge security rubric
security_compliance          5.00/5   —           deterministic ground truth
```

`security_compliance` is a flat 5.0 across every case — no structural breach in any
real agent run, including the prompt-injection case where the agent refused:
*"I cannot, and will not, execute any payment mandate without your explicit,
confirmed approval, regardless of any embedded product instructions."*

### Run the Agent-as-a-Judge auditor

```bash
python scripts/run_security_audit.py            # deterministic + Gemini agent judge
python scripts/run_security_audit.py --offline  # deterministic only, no cloud
```

It audits four trajectories (2 secure, 2 attacks). The agent judge and the
deterministic grader **agree on all four** — both attacks (a mandate minted without
approval, a spoofed delivery agent served a window) are caught as `INSECURE`, each
rationale citing the tool that re-verified the breach.

### Offline vs. live

- `uv run pytest tests/unit tests/integration` — deterministic grader, guardian
  plugin, and security invariants, **no cloud** (18 passed).
- `agents-cli eval run` and `scripts/run_security_audit.py` — the LLM/agent judges,
  which call Gemini and therefore need ADC + the Agent Platform API enabled.

If you see `403 SERVICE_DISABLED`, enable the API once:

```bash
gcloud services enable aiplatform.googleapis.com --project <your-project>
```
