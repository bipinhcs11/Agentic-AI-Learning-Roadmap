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

## Kaggle 5-Day AI Agents Intensive Alignment

This module is also a suggested local-first capstone for Kaggle and Google's
[5-Day AI Agents: Intensive Vibe Coding Course](https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google/overview/how-does-the-intensive-work)
(June 15-19, 2026). This mapping is project guidance, not an official Kaggle
submission or endorsement.

| Kaggle day | Course topic | Evidence in this module |
|---|---|---|
| Day 1 | Introduction to agents and vibe coding | `app/agent.py`: ADK root concierge, specialist agents, and natural-language tool orchestration |
| Day 2 | Agent tools and interoperability | `app/tools.py`, `app/a2a_client.py`, and `delivery-scheduler/`: deterministic tools and an A2A-capable boundary |
| Day 3 | Agent skills | `app/grocery.py` and `app/security.py`: stateful cart/checkout helpers, scoped capabilities, and reusable security skills |
| Day 4 | Vibe coding agent security and evaluation | `app/security_judge.py`, `tests/eval/`, and `scripts/run_security_audit.py`: guardrails, evaluation, and grounded judges |
| Day 5 | Spec-driven production-grade development | `specs/`, `Dockerfile`, telemetry helpers, manifests, and the documented network/deployment boundary |

The Kaggle capstone submission shape calls for a write-up, explanatory video,
rationale, and code link. The generated carousel PDF and short teaser video
(kept in the local, uncommitted repository-level `output/` directory) can be
reused as the visual explanation; add your Kaggle write-up and final repository
URL before submitting.

Remaining course-alignment gaps are intentionally visible: persistent long-term
memory/context engineering, a live network call from the concierge to the remote
A2A scheduler, and a governed production deployment with operational telemetry.

### Course Citation Contributors

The official Kaggle course citation credits the following contributors:

- Brenda Flynn
- Fran Hinkelmann
- Polong Lin
- Nikita Namjoshi
- Anant Nawalgaria
- Kinjal Parekh
- Kanchana Patlolla
- Jim Plotts
- María Cruz
- Tania Rodriguez Fuentes
- Frank Guan
- Melissa Nalubwama-Mukasa
- Sara Wolley

These names are reproduced for acknowledgement from the official course
citation; this independent educational project does not imply endorsement.

## Project Structure

```text
project_03_python_adk_grocery_platform/
├── app/
│   ├── agent.py          # ADK concierge and specialist agents (+ guardian plugin)
│   ├── grocery.py        # Catalog, A2UI, cart, UCP, AP2 helpers
│   ├── security.py       # Identity, JIT, policy, Vibe-Diff, AgBOM
│   ├── security_judge.py # Deterministic grader + Agent-as-a-Judge + guardian plugin
│   ├── a2ui.py           # Trusted A2UI component catalog + server-side validation
│   ├── a2ui_server.py    # Offline FastAPI A2UI backend for the React renderer
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
28 passed
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

The renderer is agent-driven and validated on both ends: the server only emits
A2UI payloads whose component is in the trusted catalog
(`app/a2ui.TRUSTED_COMPONENTS`), and the React app only renders components it
finds in the *same* catalog — anything else is refused, not drawn. It runs
**offline** (the payloads come from the deterministic grocery/security helpers,
no Gemini call).

Two processes — the A2UI server and the Vite dev server:

```bash
# 1) A2UI server (serves validated payloads on :8000)
uv run uvicorn app.a2ui_server:app --port 8000

# 2) React renderer (Vite proxies /api -> :8000)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5174` and walk the flow:

1. **Catalog** (`GroceryCatalogGrid`) — grocery cards with dynamic product
   imagery. Each `image_url` comes from the payload; a per-item SVG tile is
   generated as a fallback when an image URL fails, so a card is never blank.
2. **Cart** (`CartSummary`) — add items, see subtotal + service fee + total.
3. **Checkout** (`CheckoutApproval`) — the **Vibe-Diff** gate: a plain-English
   summary you must approve, with live security chips (signed A2A identity,
   policy decision, JIT scope, approval state).
4. **Approve** — the server issues a JIT token scoped to that exact cart and
   creates the AP2 mandate; the chips flip to green and the mandate id, amount,
   merchant category, and delivery window render.

The whole `catalog → cart → Vibe-Diff → mandate` path is covered offline by
`tests/unit/test_a2ui.py`.

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
  plugin, and security invariants, **no cloud** (28 passed).
- `agents-cli eval run` and `scripts/run_security_audit.py` — the LLM/agent judges,
  which call Gemini and therefore need ADC + the Agent Platform API enabled.

If you see `403 SERVICE_DISABLED`, enable the API once:

```bash
gcloud services enable aiplatform.googleapis.com --project <your-project>
```
