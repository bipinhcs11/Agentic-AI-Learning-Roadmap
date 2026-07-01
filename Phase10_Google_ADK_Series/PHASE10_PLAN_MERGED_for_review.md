# Phase 10 — Merged Plan: Java ADK + A2UI/AG-UI + UCP (for review)

Status: Merge candidate — 2026-06-30
Owner: Bipin Pradhan

> This file merges the two converged drafts (`PHASE10_JAVA_ADK_A2UI_UCP_PLAN.md`
> by codex, `PLAN_Java_ADK_A2UI_UCP_Benefits.md` by Claude). Both originals are
> left untouched. Intended as the single canonical plan **after codex review**.

---

## Direction Lock

Phase 10 teaches **Google ADK** — it does not re-teach Phase 9.

- **Java ADK** is the main orchestrator.
- **A2UI + AG-UI** are target capabilities for the first module, but only
  **Rung 01A** is the immediate commitment.
- **UCP** is the transaction layer (narrow action lane only).
- **A2A** is important but comes **after** the core app works (Module 03).
- **Retrieval is infrastructure**, not the lesson — use managed Google retrieval.
- No standalone "RAG/MCP basics" module.

The existing contract-compliance project stays as a Phase 10 reference project.
This plan is for the **next** major Phase 10 build.

Cloud-native is intentional: this is a **Google ADK series** (later: Azure
OpenAI, then AWS), so using managed cloud services is the point, not scope creep.

---

## Goal

Build a **Java-first Google ADK benefits concierge** on the familiar fictional
**401(k)/HSA** domain from Phase 9, where:

- the agent reasons and orchestrates in **Java ADK** (Vertex Gemini)
- the frontend is driven by **A2UI**
- the browser receives live updates through **AG-UI** (or web streaming)
- knowledge comes from **managed Google retrieval**
- actions run through a **bounded UCP transaction lane**

Working title: `project_02_java_adk_benefits_concierge`

One-line pitch: a Java Google ADK benefits concierge that explains fictional
401(k)/HSA choices, renders guided React screens through A2UI, streams live state
through AG-UI, and executes a narrow benefits action through UCP.

## Immediate Focus

To reduce overload, do **not** solve all of Phase 10 now.

Keep the merged plan as the strategy document, but make only one near-term build
commitment:

- **Build Rung 01A first**

That means:

- Java ADK
- fictional 401(k)/HSA domain
- text responses first
- managed retrieval only if needed

And for now, explicitly **do not** block on:

- React
- AG-UI
- UCP
- A2A

Those stay in the plan, but they are **next decisions**, not **today’s
decisions**.

---

## Why This Direction

Clean learning progression, no repetition:

- **Phase 9** = MCP, RAG, Java, Spring Boot, enterprise benefits examples.
- **Phase 10** = ADK orchestration, UI-native agent experience, transactions, optional multi-agent expansion.

We reuse the Phase 9 benefits domain because it's familiar and audience-friendly,
but Phase 10 must not feel like "Phase 9 again in a new wrapper."

---

## Core Protocol Roles

The boundary to teach clearly (the guide's rule: **add protocols as you need them**):

| Layer | Protocol | Role here | Where |
|---|---|---|---|
| Data / read | **MCP** | optional read access to tools/systems | optional infra |
| Managed retrieval | **Agent Search / RAG Engine** | benefits knowledge and retrieval infrastructure | M01 infra |
| Presentation | **A2UI** | what the UI should be (declarative) | M01 |
| Delivery | **AG-UI** / web streaming | browser delivery + live agent events | M01 |
| Transaction | **UCP** | bounded checkout/order action lane | M02 |
| Multi-agent | **A2A** | service-to-service agents | M03 |

Note: the **browser is not an A2A client** — A2A is service-to-service; the
browser talks to the orchestrator via A2UI/AG-UI.

---

## Managed Retrieval Positioning

Don't rebuild chunking/embeddings. Use **ADK + managed Google retrieval**:

- **Agent Search** — start here (simplest managed retrieval over the benefits KB).
- **RAG Engine** — move to it only if finer control (chunking/ingestion) is needed.

Teaching message: Phase 9 taught *how retrieval works*; Phase 10 teaches *how an
ADK agent uses retrieval as infrastructure*.

---

## Skills First (kept lightweight)

Sketch the agent's skills before coding — but keep it light so Rung 01A ships
fast. A short list + rough input/output + which UI state each can trigger is
enough; flesh out contracts as you build, not as an upfront gate.

Initial skills:

1. **Benefits education** — match, HSA rules, limits, tradeoffs.
2. **Retrieval + citation** — managed retrieval for plan guidance/policy.
3. **Projection** — deterministic contribution / match / tax-savings math.
4. **Election drafting** — turn intent into a proposed 401(k)/HSA change.
5. **Approval gating** — explicit human confirmation before any commit.
6. **Transaction execution** — call the UCP lane (checkout/order).
7. **Optional specialist** — reserved for A2A (Module 03).

---

## Module Structure (3 modules)

### Module 01 — Java ADK + A2UI/AG-UI Benefits Concierge

Scope (eventually): Java ADK orchestration, managed retrieval, A2UI-driven UI,
React rendering, AG-UI streaming, deterministic calculations. **Do not build it
all at once.** Ship in four rungs; each rung runs locally and is **one LinkedIn
post**. Climb the next rung only after the current one runs and the post is out.

- **Rung 01A — Java ADK text agent (first runnable win).** Answers 401(k)/HSA in
  text on Vertex Gemini, backed by deterministic calculators + managed retrieval.
  → *Post: "Rebuilt my Phase 9 benefits assistant in Java ADK — Gemini + managed retrieval under the hood."*
- **Rung 01B — Verify A2UI path, then render it in the built-in ADK web UI.**
  Same agent returns a card/table; confirm the Java path cleanly supports the
  A2UI payload shape and validation model we need before treating this as the
  default path. If verified, the ADK web UI becomes the lowest-friction A2UI proof.
  → *Post: "Agents don't have to reply in text — here's mine returning a UI, no frontend code."*
- **Rung 01C — React renders the A2UI.** Minimal React app renders the agent's
  A2UI payloads from a **trusted component catalog**. One screen, a few components.
  → *Post: "Agent-driven React UI with A2UI."*
- **Rung 01D — AG-UI streaming.** Live agent events / state instead of
  request-response.
  → *Post: "Live, streaming agent UI with AG-UI."*

Teaches: how ADK drives a real user experience; how to structure agent skills;
how retrieval supports the agent without becoming the lesson.

### Module 02 — UCP Benefits Transactions

Narrow transaction flow only: proposed election → human approval → checkout →
order/receipt. Teaches how an ADK app moves from advice to action, and how to use
UCP without forcing it into every interaction.
→ *Post: "The agent doesn't just advise — it transacts, via UCP."*

### Module 03 — A2A Multi-Agent Expansion

Service-to-service boundaries; remote specialist agent(s) only when justified
(e.g. eligibility validation, policy/compliance, provider execution). Teaches
when A2A is useful and how to split responsibilities.

**Why A2A is Module 03, not Module 01:** it adds service-boundary complexity,
isn't required for the first strong ADK app, and works best once there's a real
second-agent boundary. Not out — just not first.

---

## Runtime Architecture

```text
React Frontend
  -> receives AG-UI / web-streamed events
  -> renders A2UI payloads from a trusted component catalog
     (browser is NOT an A2A client)

Java ADK Orchestrator (Vertex Gemini)
  -> runs benefits skills
  -> calls managed retrieval
  -> performs deterministic calculations
  -> triggers the UCP transaction flow when the user confirms an action

Managed Retrieval
  -> Agent Search (or RAG Engine) over fictional benefits knowledge

UCP Service
  -> catalog / draft / checkout / order / receipt style flow
  -> exposes OpenAPI 3.1 -> UcpClientTool can be generated as an ADK OpenAPI tool

Optional A2A Specialists
  -> added only in Module 03
```

---

## Best User Journey

1. User asks a benefits question in the React app.
2. Java ADK selects the right skill.
3. Agent retrieves context from managed retrieval if needed.
4. Agent responds with **A2UI**, not plain text.
5. Browser updates through **AG-UI / streaming**.
6. If the user chooses an action, the agent enters the **UCP lane** (with approval gate).
7. If later justified, a specialist agent is introduced through **A2A**.

---

## Build Order

- **Phase A — Light skill design:** sketch skills, rough contracts, UI states, confirmation boundaries, informational-vs-transactional split. Keep it short; don't gate Rung 01A behind a full design doc.
- **Phase B — Rung 01A only:** Java ADK text agent first. Do not start React, AG-UI, UCP, or A2A work until this runs.
- **Phase C — Module 01 continuation:** Rungs 01B → 01D (verify A2UI path → A2UI in dev UI → React → AG-UI).
- **Phase D — Module 02:** minimal UCP service/adapter, confirmation flow, receipt/transaction state.
- **Phase E — Module 03:** remote specialist agent, A2A boundary, failure/retry story.

---

## Reuse From Phase 9

Reuse: fictional 401(k)/HSA domain, contribution/tax examples, plan references +
educational disclaimers, Java/Spring familiarity.

Don't re-teach: raw chunking, embeddings from scratch, basic MCP concepts,
"benefits Q&A only" as the main story.

---

## Open Decisions

1. **Managed retrieval choice** — start with **Agent Search**; move to RAG Engine only if finer control is needed.
2. **Transaction shape** — use **benefits election confirmation** as the UCP flow, not a broad commerce simulation.
3. **UCP service placement** — keep minimal first; split into its own service only if it grows.
4. **A2A specialist** — add only in Module 03 after the core path is solid.

---

## Practical Definition of Done

Done = **it runs locally and a post is out**, rung by rung — not "a good plan
exists." The 3-module structure is the *shape*; completion is measured by
shipped, runnable milestones:

1. **Rung 01A runs** — Java ADK text agent answers the core benefits questions — posted.
2. **Rung 01B is verified and runs** — Java path for A2UI is confirmed and the agent returns A2UI in the ADK web UI — posted.
3. **Rung 01C runs** — React renders the A2UI payloads — posted.
4. **Rung 01D runs** — AG-UI / streaming updates the browser live — posted.
5. **Module 02 runs** — a narrow UCP transaction flow — posted.
6. **Module 03 runs** — only when a real A2A specialist boundary is justified.

---

## Build Notes / Caveats (verified June 2026)

- **A2UI** is in ADK since v1.23; the **ADK web UI renders A2UI out of the box since v1.24** — that's why Rung 01B needs no React.
- On the **Java** track, still treat Rung 01B as a **verification step first**:
  confirm the Java path for emitting and validating the A2UI payload shape you
  need before promising it as turnkey.
- **AG-UI** is supported in ADK Python/TS/Go/**Java**, but its quickstart/examples are **React/TS + CopilotKit-flavored** — on the Java track you'll wire the bridge from the generic docs, not copy a Java sample.
- **A2UI server-side validation is mandatory:** validate the model's A2UI JSON against the trusted catalog before sending (Gemini handles strict A2UI JSON reliably).
- **UCP** ships an **OpenAPI 3.1** transport, so the UCP client can be generated as an **ADK OpenAPI tool** rather than hand-written.

---

## Sources

- [Developer's Guide to AI Agent Protocols](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/)
- [ADK Integrations](https://adk.dev/integrations/)
- [A2UI for ADK](https://adk.dev/integrations/a2ui/)
- [AG-UI for ADK](https://adk.dev/integrations/ag-ui/)
- [ADK for Java 1.0](https://developers.googleblog.com/announcing-adk-for-java-100-building-the-future-of-ai-agents-in-java/)
- [adk-java repo](https://github.com/google/adk-java) · [adk-samples](https://github.com/google/adk-samples)
- [RAG Engine overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-overview)
- [Agent Search overview](https://docs.cloud.google.com/generative-ai-app-builder/docs)
- [UCP core concepts](https://ucp.dev/documentation/core-concepts/) · [UCP repo](https://github.com/universal-commerce-protocol/ucp)
- Reference sample (new-hire onboarding, Python) — https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/adk/new-hire-onboarding/README.md
