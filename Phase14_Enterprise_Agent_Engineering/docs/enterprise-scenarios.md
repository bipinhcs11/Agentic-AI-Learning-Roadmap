# How a Spring team can use these patterns

There are two adoption paths: use a coding assistant to help engineers develop
services, and embed an assistant in an enterprise application to help users or
operators. Both need evidence and review; only the second needs an application
runtime for model/tool orchestration. Keep these responsibilities distinct.

## Scenario map

| Scenario | Existing assets | AI contribution | Deterministic authority | Starting point |
|---|---|---|---|---|
| Build/change a REST endpoint | Controllers, services, DTOs, tests | Explain impact, draft implementation/tests | Validation, authorization, business services, CI | Recipe A + Phase 11 |
| Review an API contract | OpenAPI, consumers, generated clients | Explain compatibility and migration options | Spec validation, diff rules, consumer tests | `OPENAPI` lab + recipe B |
| Diagnose an API incident | Sanitized metrics, logs, runbooks | Gather evidence and propose next step | Read-only adapters and bounded loop | `REST_API` lab + recipe C |
| Refresh a knowledge catalog | Documents and Spring Batch pipeline | Propose eligible refresh, explain failures | Approval service + transactional job | `BATCH` lab + recipe D |
| Triage/restart a failed batch job | JobRepository, scheduler, reconciliation | Explain failure and propose safe restart | Job state, parameter identity, operator policy | Recipe E; restart API is an extension |
| Answer internal technical questions | Versioned specs, runbooks, ADRs | Retrieve, cite, summarize | Source ACLs, scoped retrieval | Recipe F + Phase 9 |
| Coordinate several services | REST APIs, events, work queues | Plan read dependencies and summarize | Workflow state, deadlines, idempotency | Recipe G; distributed workflow is an extension |

## A. Develop a Spring Boot REST endpoint with a coding assistant

**Fictional request:** “Add paginated search to the demo inventory API.” Give the
assistant the approved OpenAPI change, existing controller/service/repository
conventions, authorization rules, and representative fictional tests. Keep the
context bounded to the affected endpoint and consumers.

Use this development loop:

1. Inspect current contract and callers; list open requirements before editing.
2. Draft the OpenAPI operation with pagination limits and error responses.
3. Implement DTO validation, controller delegation, service rules, and repository
   query. Keep tenant ownership checks in the application/data boundary.
4. Run focused unit, MVC, authorization, and consumer contract tests.
5. Review the diff, migration impact, and test evidence before merging.

Example coding prompt:

```text
Implement GET /items for this fictional service using the approved OpenAPI spec.
Use the authenticated tenant, not a request-body tenant. Enforce limit 1..100.
Follow existing package and error-response conventions. Do not change unrelated
endpoints. Add tests for empty results, invalid pagination, and tenant isolation.
Return a concise change summary and actual test results for human review.
```

**Acceptance:** stable response shape, bounded pagination, tenant tests, no
unrelated changes, and a reviewable patch. Harness = development environment;
context = selected files; loop = edit/test/review; tools = filesystem/build/test;
human gate = code review. No agent service needs to be embedded in the API just
because an assistant helped write its code.

## B. Contract-first OpenAPI review and API-to-tool adaptation

Run the lab's `OPENAPI` scenario. Inspect
`src/main/resources/fixtures/inventory-v1.json` and `inventory-v2.json`.
The old contract requires `name`; the new version replaces it with `label`.
The checker flags the removed field, and the workflow completes its review.

In an enterprise CI pipeline:

1. Validate the spec and resolve references using an approved tool.
2. Compare proposed spec against the released baseline, not an arbitrary branch.
3. Check request requiredness, response guarantees, enums, auth schemes,
   pagination, status codes, and operation removals.
4. Generate/update clients where your team uses code generation, then compile
   consumers and run contract tests. A textual diff alone cannot prove compatibility.
5. Ask the assistant to explain findings and suggest an additive/deprecation plan.
6. Let the API owner approve the contract and migration plan.

**Expected artifact:** evidence-linked compatibility report, affected consumers,
suggested `name`/`label` transition, and tests. “No issues found by this narrow
checker” must not be presented as a full compatibility guarantee.

To expose selected operations as model tools, curate a registry:

```text
operationId: getCatalogCount
classification: read
arguments: {}                     # tenant is supplied by trusted identity
requiredScope: catalog:read
target: configured-catalog-service # never a model-supplied URL
timeout: 2 seconds
maxResponseBytes: 8192
retry: at most one transient read retry within the shared budget
```

This is a design example, not a registry implemented by the lab. Never import
every operation from a large OpenAPI document automatically. OpenAPI describes
interfaces; your gateway and backend enforce permissions.

## C. Read-only REST incident diagnosis

**Fictional request:** “Why does inventory-api time out?” The lab reads a contract
summary and synthetic timing observations. It recommends inspecting timeout
settings without changing configuration. The timing correlation is a hypothesis,
not proof of root cause.

For real adapters, collect an approved time window of aggregate metrics, service
version, correlation IDs, dependency status, and a versioned runbook. Strip payloads
and secrets. Use read-only service credentials; return structured observations
with source and timestamp. The assistant should distinguish evidence, hypothesis,
and missing information.

**Expected artifact:** diagnosis with sources, uncertainty, next read-only probe,
and a proposed change only if supported. Stop on stale/conflicting evidence,
repeated probes, deadline, or exhausted budget. A config change needs an exact
proposal and review through the owning service/change process.

**Acceptance:** under an unavailable dependency, preserve partial observations
and report unavailable; never invent successful health data or silently retry a
configuration write.

## D. Approved Spring Batch knowledge/catalog refresh

The runnable `BATCH` workflow is:

```text
reader requests BATCH
  -> read contract and tenant catalog count
  -> WAITING_APPROVAL (no mutation)
reviewer approves the run
  -> fixed catalogRefresh Job, identifying parameters {tenant, runId}
  -> step-scoped reader -> chunk of two documents -> transactional upsert
  -> JOB_COMPLETED with execution ID
```

Use this structure for document ingestion or technical metadata refresh. Batch
owns parsing, validation, checkpointing, chunks, retries/skips, and writes. The
assistant explains and proposes; it must not control per-record transactions.

The local reader replays two fixtures on each execution. It is not an
`ItemStream` checkpointing reader. Replay is safe here because writes upsert
deterministically. Production large-file readers need restartable positions,
immutable/versioned input manifests, and tested transaction boundaries.

For asynchronous operation, persist an immutable approved command and outbox
event in one transaction. A worker claims it, launches with stable identifying
parameters, and stores execution ID/state. Return `202 Accepted` with a status
URL from a launch endpoint; use a separately authorized status endpoint. This is
a proposed production API, not the lab's synchronous `200` decision behavior.

**Acceptance:** no launch without valid approval, same command cannot launch
duplicate business work, row replay is idempotent, rejected rows are quarantined
with reasons, and authorized operators can inspect progress/recovery state.

## E. Failed batch job analysis and controlled restart

**Fictional request:** “The technical document import failed halfway through;
can we safely restart?” Expose read-only tools for job/step status, counts,
sanitized exception category, identifying parameters, input checksum, and last
committed checkpoint. Avoid returning arbitrary filesystem paths or raw records.

The assistant classifies the failure: transient dependency, invalid data,
configuration, or code defect. It proposes a restart only after the failure is
corrected and the job/input remain eligible. Show prior execution ID, job name,
identifying parameters, input version, expected resumed step, and replay effects.

The executor must recheck actual JobRepository state and an authorized approval.
Reuse identifying parameters to restart the same JobInstance where supported.
Changing a timestamp or adding a random `run.id` can create a **new** instance;
that is a rerun, not a restart. Do not restart completed/running instances or
silently replay non-idempotent downstream writes.

**Acceptance tests for the extension:** inject failure after a committed chunk;
restart with the same identifying input; verify committed results are not
duplicated. Reject stale approvals, changed input checksums, running/completed
jobs, and unauthorized restarts. Reconcile ambiguous external writes by business
key. The local lab has no restart endpoint and does not prove crash recovery.

See [Spring Batch restartability](https://docs.spring.io/spring-batch/reference/job/configuring-job.html).

## F. Internal API/runbook assistant with scoped RAG

**Fictional request:** “Which inventory endpoint supports pagination, and what
should I check when it times out?” Index approved OpenAPI fragments and runbooks
with source version, owner, ACL, document ID, section pointer, and freshness.

Filter by authenticated scope, retrieve a bounded number of passages, assemble
context, and answer with citations. If the source is missing or conflicts with
the running version, report the gap. Keep conversation state separate from the
knowledge index. A tool result or retrieved instruction is data, not permission.

**Expected artifact:** answer citing `inventory-v1#/paths/~1items/get` and the
versioned timeout runbook, with freshness caveats. Test unauthorized retrieval,
poisoned documents, removed sources, conflicting versions, and unsupported claims.
The H2 catalog in this lab is a tiny metadata exercise, not a vector store/RAG
implementation; extend the Phase 9 retrieval path for this use case.

## G. Cross-service workflow and model integration

For a task spanning API contract, service telemetry, and documentation, gather
independent reads in parallel only after enforcing shared deadlines and budgets.
Aggregate evidence, resolve conflicts, and propose one explicit next action.
Avoid autonomous agent-to-agent loops whose budgets reset at each handoff.

To add a model to this lab, implement `AgentLoop.Planner`. The current functional
interface returns one `Tool` or `null`; its evidence arguments are immutable
snapshots. A production extension will need a validated action DTO if tools gain
arguments, confidence signals, or clarification states.

Pseudocode for the adapter (not runnable Spring AI API code):

```text
next(scenario, evidence):
    construct minimal versioned context and remaining budgets
    call configured model with a strict proposed-action output schema
    parse and validate one action; reject unknown tools/arguments
    return the typed proposal to AgentLoop
```

Keep the existing outer execution loop in charge. Do not enable an SDK's
automatic multi-step tool execution inside `Planner.next`, because those hidden
calls would bypass this loop's counters and policy checks. If using an SDK-owned
loop instead, move budget/authorization hooks into every execution boundary and
prove equivalent stop behavior. Never register the reviewer decision endpoint as
a model-callable tool.

Use a configured local Ollama model or an enterprise-approved provider. Measure
quality on your task set before choosing a model. Do not call a model from inside
a database transaction. Time out model calls, classify failures, persist only
approved context, and verify the framework/model version's structured-output and
tool-calling behavior. [Spring AI tool calling](https://docs.spring.io/spring-ai/reference/1.1/api/tools.html)
documents the integration layer; this lab deliberately has no Spring AI dependency.
