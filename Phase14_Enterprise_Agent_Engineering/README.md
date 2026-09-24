# Phase 14 — Enterprise Agent Engineering for Spring Teams

Use agent engineering with an existing Java estate: Spring Boot REST services,
OpenAPI contracts, Spring Batch jobs, service catalogs, and operational runbooks.
Keep business rules and transactions in your services; let an AI assistant choose
bounded actions, gather evidence, and propose changes through those interfaces.

All identities, APIs, observations, and documents here are fictional educational
fixtures. No real financial, HR, billing, benefits, or customer data is used.

## Start here

**New to these concepts? Follow the [step-by-step developer walkthrough](docs/developer-walkthrough.md).**
It explains all ten practices through one hands-on workflow, with commands,
assistant prompts, expected results, and guidance for applying them to a work ticket.

1. Run the local lab below (about 15 minutes).
2. Read the [ten engineering practices](docs/engineering-practices.md).
3. Choose a [workplace scenario and implementation recipe](docs/enterprise-scenarios.md).
4. Use the [evaluation and production checklist](docs/evaluation-and-production.md)
   before replacing fixtures with a model or connecting enterprise systems.
5. Use the [enterprise skill pack](docs/skill-pack.md) for scenario-specific
   assistant workflows, instructions, example prompts, and optional installation.

The pack includes seven scenario skills, a cross-cutting evaluation skill, and
an attributed enterprise adaptation of Matt Pocock's `grill-me`/`grilling`.
Each has concrete scenario instructions. These guide coding/operations assistants;
the Java runtime continues to enforce its own controls.

Loop Engineering is **section 3**, as requested. The supplied images cover nine
topics; Context Engineering is added as section 2 to connect harness, loop,
tools, and memory. These are learning modules within Phase 14, not replacements
for existing roadmap phases.

| # | Practice | Spring/enterprise application | Coverage |
|---|---|---|---|
| 1 | Harness Engineering | Runtime, dependencies, credentials, tool boundary, budgets | Local Spring Boot harness; production isolation design |
| 2 | Context Engineering | Versioned contracts, runbooks, task and tenant context | Fixed scoped fixtures; retrieval/context assembly recipe |
| 3 | Loop Engineering | Observe → choose → validate → act → evaluate → stop | Runnable bounded Java loop with failure tests |
| 4 | Tool Design | Small operations over REST APIs and OpenAPI schemas | Typed tool enum, validated requests, actual contract comparison |
| 5 | Memory Architecture | Run state, durable records, semantic retrieval | Tenant-scoped expiring run memory and H2 catalog; durable/vector design |
| 6 | Orchestration Patterns | Sequential diagnostics, parallel reads, batch handoffs | Sequential loop + job handoff; parallel/multi-agent design |
| 7 | Guardrails & Permissions | Identity, roles, tenant access, operation allowlists | Spring Security, server-derived tenant, bounded tools |
| 8 | Evals for Agents | Outcome, trajectory, adversarial and regression cases | Deterministic JUnit tests; model-evaluation rubric |
| 9 | Human-in-the-Loop Design | Review exact changes, approve/reject, expiry | Authenticated reviewer decision, expiry, duplicate handling |
| 10 | Observability & Tracing | Run IDs, tools, latency, outcomes, job execution IDs | Logs and Micrometer metrics; distributed tracing recipe |

## Local lab

Prerequisites: JDK 21 and Maven 3.9+. The project uses the same Spring Boot
3.5.3 baseline as the existing Java modules and its managed Spring Batch 5.2.2.
These pins are for repository consistency, not a claim that they are the latest
or approved for production. Review supported versions and vulnerabilities before
enterprise adoption. The first Maven build downloads dependencies; tests then
run without external services. No Ollama, Docker, cloud account, or API key is
needed.

From the repository root:

```bash
cd Phase14_Enterprise_Agent_Engineering
mvn test
mvn spring-boot:run
```

The server binds only to `127.0.0.1:8094`. Stop with Ctrl-C. Restarting clears
all runs, approvals, catalog data, and Spring Batch metadata.

In a second terminal, create a diagnostic run:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"REST_API","maxSteps":4}'
```

Expected fields (UUID and timestamp vary):

```json
{
  "tenant": "demo-a",
  "scenario": "REST_API",
  "status": "COMPLETED",
  "evidence": [
    {"tool":"READ_CONTRACT","summary":"Fixture inventory-api v1: GET /items; operationId=listItems; limit=1..100; required id/name."},
    {"tool":"READ_HEALTH","summary":"Fixture inventory-api: available; upstream timeout=250ms, observed p95=400ms. These are synthetic observations."}
  ],
  "attempts": 2
}
```

The planner is **deterministic Java**, not an LLM. The application exposes the
control boundaries without nondeterministic model output. REST health readings
are fixture observations, not an actual network probe. `COMPLETED` means the
diagnostic workflow collected its evidence; it does not mean an incident was
repaired or a proposed contract is compatible.

### Review an OpenAPI change

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"OPENAPI","maxSteps":4}'
```

Expected: `COMPLETED`, with `CHECK_COMPATIBILITY` evidence containing
`removed required response field: name`. The fixture deliberately renames `name`
to `label`. The checker compares required inline response fields on `GET /items`;
it is not a complete OpenAPI compatibility validator. Real pipelines need a full
diff tool and consumer contract tests.

The lab's own [OpenAPI 3.1 contract](src/main/resources/static/openapi.json) is
also served at:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/openapi.json
```

### Propose and approve a Spring Batch refresh

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"BATCH","maxSteps":4}'
```

Expected: `WAITING_APPROVAL`. Copy the returned `id` into `RUN_ID` below. The
proposal always means: upsert exactly two bundled fictional documents into the
caller's tenant catalog. The caller cannot supply a job name, tenant, file path,
SQL statement, or replacement payload.

```bash
RUN_ID='paste-returned-id-here'
curl -sS -u reviewer:reviewer-demo \
  "http://127.0.0.1:8094/api/runs/$RUN_ID/decision" \
  -H 'Content-Type: application/json' -d '{"approved":true}'

curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/catalog
```

Expected: `JOB_COMPLETED` with a `jobExecutionId`, then
`{"tenant":"demo-a","documentCount":2}`. Repeating the successful approval
returns the same execution ID. A new approved run still leaves two catalog rows
because the writer upserts by tenant/document ID. Use `{"approved":false}` on a
new pending run to reject it; a rejected run cannot later be approved.

This tiny job runs synchronously in the HTTP request. It demonstrates real
Spring Batch chunk transactions and job metadata. Long-running enterprise jobs
need a queue, durable approval records, asynchronous launch/status APIs, and
worker ownership; see the scenario guide.

### Try the controls

| Action | Expected result |
|---|---|
| Create `REST_API` with `maxSteps:1` | `STEP_LIMIT`, one tool attempt |
| Use `maxSteps:9` or an unknown scenario | HTTP 400 |
| Add `tenant`, `approved`, or arbitrary fields to a run request | HTTP 400 |
| Call without credentials | HTTP 401 |
| Approve as `reader:reader-demo` | HTTP 403 |
| Read a demo-a run as `other:other-demo` | HTTP 404 |
| Read `/api/catalog` as `other:other-demo` | Tenant `demo-b`, zero documents |
| Approve an already rejected/completed diagnostic run | HTTP 409 |
| Read a run older than 30 minutes | HTTP 404 |

Public local credentials are in `SecurityConfig`; they are teaching fixtures.
Browser Origin requests are rejected. This CLI-only service has no UI, cookies,
or sessions. Do not expose it on a network or reuse this authentication setup
for enterprise deployments. Run capacity is capped at 100 with 30-minute expiry;
it is a memory bound, not a distributed request rate limiter.

### Inspect observability

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.runs
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.tool.calls
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.run.duration
```

Metrics appear after a run. Logs correlate `run_id`, status, and batch execution
ID. This is local correlation, not an exported distributed trace. The app's
custom audit events omit payloads; framework validation/batch logs can contain
rejected values/job parameters, so all inputs must remain fictional.

## Code map

| File | Responsibility |
|---|---|
| `AgentLoop.java` | Planner interface, typed tools, evidence validation, stop conditions, read retry |
| `RunService.java` | Scoped tools, run state, approval transition, fixed batch launch, metrics |
| `RunController.java` | REST requests, validation, status codes |
| `SecurityConfig.java` | Local users, reviewer role, identity-to-tenant mapping |
| `ContractReview.java` | Narrow fixture compatibility checker |
| `CatalogBatch.java` | Step-scoped reader/writer, transactional chunk, idempotent upsert |
| `src/main/resources/static/openapi.json` | API surface and explicit tool-exposure metadata |
| `src/test/java/...` | Loop, contract, access-control, approval, and batch checks |

## Connect to the rest of the roadmap

- [Phase 9 Spring Boot MCP](../Phase9_Dynamic_Agentic_RAG_MCP/module_05_springboot_mcp_benefits_assistant/README.md): expose selected tools to an assistant.
- [Phase 11 Java/Spring developer workflow](../Phase11_GitHub_Copilot_Best_Practices/stacks/java_springboot_microservices/README.md): use coding assistants while building these services.
- [Phase 12 identity and security](../Phase12_Enterprise_AI_Identity_Security/README.md): replace local users with governed identities and delegation.
- [Phase 13 MCP ecosystem](../Phase13_Enterprise_MCP_Ecosystem/README.md): publish approved tools through a registry and gateway.

The [production checklist](docs/evaluation-and-production.md) lists the deliberate
gaps. Do not interpret the passing deterministic tests as proof of LLM quality,
production isolation, durable exactly-once execution, or comprehensive security.
