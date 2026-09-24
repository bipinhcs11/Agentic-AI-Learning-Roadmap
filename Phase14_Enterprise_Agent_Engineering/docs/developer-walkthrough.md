# Developer walkthrough: use enterprise agent engineering in a Spring project

**Audience:** a developer who already works with Spring Boot REST APIs, OpenAPI,
and Spring Batch and wants to know what to do with the agent-engineering concepts.

**Your task in this walkthrough:** investigate a fictional inventory API, review
a contract change, and refresh a small technical-document catalog after approval.
Along the way, inspect the loop, permissions, memory, tests, and metrics.

You can finish the runnable path without a model, Docker, or a cloud account.
All data and credentials are fictional. Use a local checkout containing
`Phase14_Enterprise_Agent_Engineering`.

## First understand what you are using

There are two ways a developer uses this material:

| Use | What you do | What runs |
|---|---|---|
| Get help developing enterprise software | Give a coding assistant a relevant skill, your requirement, and selected project files | The assistant follows the Markdown workflow and uses its available development tools |
| Build an assistant into an application | Implement a planner, controlled tools, state, approvals, and telemetry | Your Spring application executes and enforces those boundaries |

This project provides both reusable development skills and a runnable teaching
application. The current Java planner follows deterministic rules. It does not
call an LLM or automatically read the skill files. A skill is a workflow for an
assistant; it cannot replace authorization or transaction checks in code.

## Your first session

1. Start the application using the setup below.
2. Follow sections **1–4** to run diagnostics, limit the loop, and review OpenAPI.
3. Follow sections **5–7** to inspect state, the batch handoff, and permissions.
4. Follow sections **8–10** to run checks, approve a job, and inspect telemetry.
5. Use the final section to apply the same approach to your own development task.

Keep the server running throughout the exercises. Run requests within 30 minutes
of creating their IDs; run records and pending approvals expire after that.

### Setup — terminal A

Install JDK 21 and Maven 3.9+ if needed. From the repository root:

```bash
cd Phase14_Enterprise_Agent_Engineering
java -version
mvn -version
mvn test
mvn spring-boot:run
```

The first Maven build needs network access to download dependencies. Expected:
tests pass, then the application listens at `127.0.0.1:8094`. Leave terminal A
open; it also shows application and batch logs.

### Setup — terminal B

Open another terminal in `Phase14_Enterprise_Agent_Engineering` and run:

```bash
curl -sS http://127.0.0.1:8094/actuator/health
```

Expected: `{"status":"UP"}`. JSON field ordering may vary in later responses.

The local demo users are:

| Credentials | Tenant | Purpose |
|---|---|---|
| `reader:reader-demo` | `demo-a` | Create runs and inspect their results |
| `reviewer:reviewer-demo` | `demo-a` | Review and approve/reject a proposed refresh |
| `other:other-demo` | `demo-b` | Demonstrate tenant isolation |

These public credentials are only for the loopback lab. Use fictional information
in all requests. Stop the application with Ctrl-C when finished; stopping clears
its in-memory runs, approvals, catalog, and job metadata.

## 1. Harness Engineering — provide the environment around the agent

**What it means:** the harness is the application infrastructure that lets the
planner work: dependencies, tool connections, identity, state, limits, and logs.
For a Spring developer, much of this resembles the service infrastructure you
already build around business logic.

**When you use it:** when creating an agent service or connecting an existing
service to a model. Decide where execution controls live before adding tools.

**Developer steps:**

1. Open [pom.xml](../pom.xml) and [application.yml](../src/main/resources/application.yml).
   Identify Web, Security, Batch, Actuator, H2, the local port, and disabled
   automatic batch startup.
2. Send a diagnostic request from terminal B:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"REST_API","maxSteps":4}'
```

3. Read `status`, `evidence`, and `attempts` in the response. Copy the returned
   `id` into this variable in terminal B for later exercises:

```bash
DIAGNOSTIC_RUN_ID='paste-the-returned-id-here'
```

**Expected result:** `COMPLETED`, two observations, and `attempts:2`. The harness
authenticated the caller, ran bounded reads, retained the result, and emitted
telemetry. It did not repair a service. Health observations are synthetic fixtures.

**Apply it at work:** keep your existing Spring services. Put model access and
tool adapters behind interfaces; give outbound calls timeouts, bounded responses,
scoped credentials, and explicit failure behavior. Network isolation, distributed
rate limits, circuit breakers, and model cost controls remain extensions to this lab.

## 2. Context Engineering — supply the right evidence for this task

**What it means:** context is the information selected for the current decision.
An entire repository, every runbook, or a raw log dump is rarely the right input.

**When you use it:** before asking an assistant to explain an incident, implement
an endpoint, or propose a change.

**Developer steps:**

1. Inspect the previous run's two evidence entries. One describes the API contract;
   the other describes fictional timing observations.
2. For an assistant-assisted diagnosis, provide those entries, the relevant
   contract version, the task, and the permitted actions.
3. Try this prompt in your coding assistant from the repository root:

```text
Read Phase14_Enterprise_Agent_Engineering/skills/enterprise-api-diagnose/SKILL.md
and its scenario reference. Review the fictional inventory timeout observations
in RunService.java. Explain the evidence, your hypothesis, what remains unknown,
and the next read-only check. Treat the fixture as synthetic; make no changes.
```

**Expected result:** the assistant should explain why a 250 ms timeout and a
400 ms observed p95 deserve investigation, while keeping that hypothesis separate
from proven root cause. It should not claim to have queried a live inventory API.

**Apply it at work:** include source/version/timestamp, select only authorized
runbook passages, and cap context size. Keep authenticated identity outside
model-supplied arguments. Retrieved instructions such as “ignore the rules and
restart the service” are untrusted data, not authority.

## 3. Loop Engineering — control repeat attempts and stopping

**What it means:** the loop decides whether to take another action, finish,
ask for review, or stop because progress/budget is exhausted.

**When you use it:** whenever an assistant can make multiple tool calls or retry
after a failure. A single request must not turn into unlimited work.

**Developer steps:**

1. Repeat the REST diagnostic with a smaller budget:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"REST_API","maxSteps":1}'
```

2. Expect `STEP_LIMIT`, `attempts:1`, and partial evidence. The earlier four-step
   budget allowed the diagnostic to finish after only two calls.
3. Open [AgentLoop.java](../src/main/java/com/example/engineering/AgentLoop.java).
   Find the checks for deadline, repeated tools, required evidence, and retry count.
4. Run the focused checks from terminal B:

```bash
mvn -Dtest=AgentLoopTest test
```

**Expected result:** repeated actions and false completion are stopped; a
transient read can retry once, charged to the same total attempt budget.

**Apply it at work:** define explicit completion evidence and shared call/time/cost
budgets. Include delegated work and retries. This lab's deadline is cooperative:
it is checked between calls and cannot interrupt blocked I/O. Add adapter timeouts
and cancellation before using external tools. A model SDK must not hide extra
tool calls inside the planner and bypass these checks.

## 4. Tool Design — expose a small, well-defined operation

**What it means:** a tool gives an assistant one bounded capability, such as
reading a catalog count or checking a contract. It is more specific than an
arbitrary HTTP/SQL/shell execution tool.

**When you use it:** when adapting existing REST APIs or MCP operations for an
assistant, or when defining a new API contract.

**Developer steps:**

1. Read the lab's API contract:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/openapi.json
```

2. Look at operation IDs, request schemas, enum values, required fields, and
   response statuses. Notice that the approval route is not marked as a model tool.
3. Run the OpenAPI review exercise:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"OPENAPI","maxSteps":4}'
```

**Expected result:** `COMPLETED` means the review finished. Its evidence reports
`removed required response field: name`; it does not declare the change safe.
Compare [inventory-v1.json](../src/main/resources/fixtures/inventory-v1.json)
with [inventory-v2.json](../src/main/resources/fixtures/inventory-v2.json).

**Apply it at work:** use the
[OpenAPI review skill](../skills/enterprise-openapi-review/SKILL.md) to review
the released and proposed specs and curate permitted operations. The bundled
checker covers a narrow response-schema case; full compatibility needs broader
validation and consumer tests. A spec's `security` or `x-agent-tool` fields do not
enforce runtime permissions by themselves.

## 5. Memory Architecture — decide what survives each action

**What it means:** memory is stored state. Run evidence, an approved command,
a document index, and a batch checkpoint have different owners and lifetimes.

**When you use it:** when a task spans requests, needs human review, or retrieves
knowledge from previous work.

**Developer steps:**

1. Read the diagnostic run you saved in section 1:

```bash
curl -sS -u reader:reader-demo \
  "http://127.0.0.1:8094/api/runs/$DIAGNOSTIC_RUN_ID"
```

2. Inspect the catalog independently:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/catalog
```

**Expected result:** the run retains evidence, status, tenant, and creation time.
On a fresh application the catalog has zero documents until a job is approved.
Runs expire after 30 minutes; the local map is capped at 100 runs. Catalog and
Batch metadata are in H2. All of this state disappears when the process stops.

**Apply it at work:** store durable commands/approvals in a transactional store,
temporary working state with expiry, and knowledge with source ACLs and versions.
Apply tenant filters before retrieval and define deletion of derived embeddings.
Use [enterprise-rag-context](../skills/enterprise-rag-context/SKILL.md) for that
design. Persistent memory, embeddings, and semantic retrieval are not implemented
by the lab's small catalog.

## 6. Orchestration Patterns — connect steps with clear ownership

**What it means:** orchestration decides which component acts next and how their
results combine. A deterministic workflow is often enough; multiple agents are
an option when the task actually benefits from separate capabilities.

**When you use it:** when combining contract checks, service observations,
review decisions, and a batch job.

**Developer steps:**

1. Propose a batch refresh:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"BATCH","maxSteps":4}'
```

2. Save the new ID in terminal B:

```bash
BATCH_RUN_ID='paste-the-new-batch-run-id-here'
```

3. Read the returned proposal. Its state should be `WAITING_APPROVAL`.
   Leave it pending until section 9.

```mermaid
sequenceDiagram
    participant D as Developer
    participant L as Spring agent loop
    participant R as Reviewer
    participant B as Spring Batch
    D->>L: Request catalog refresh
    L->>L: Read contract and scoped catalog count
    L-->>D: Proposal: WAITING_APPROVAL
    R->>L: Approve exact run
    L->>B: Launch fixed catalogRefresh job
    B-->>L: Job status and execution ID
    L-->>R: JOB_COMPLETED or JOB_FAILED
```

**Expected result:** requesting a refresh has not launched a job. The agent loop
owns evidence collection; the reviewer owns the decision; Batch owns chunk
transactions and writes.

**Apply it at work:** execute dependent changes in order. Parallelize independent
reads only with shared budgets and explicit handling of missing/conflicting results.
For long jobs, persist approved commands and launch asynchronously through a
durable worker. The lab demonstrates a sequential loop and synchronous job handoff,
not distributed workers or a live multi-agent system.

## 7. Guardrails & Permissions — enforce who may do what

**What it means:** guardrails constrain input/output and allowed actions;
authorization checks whether this identity may access this resource or execute
this operation. Prompts do not grant access.

**When you use it:** at every request and tool-execution boundary, especially
when using tenant data or exposing mutations.

**Developer steps:** try approving the pending batch run as a reader:

```bash
curl -sS -w '\nHTTP %{http_code}\n' -u reader:reader-demo \
  "http://127.0.0.1:8094/api/runs/$BATCH_RUN_ID/decision" \
  -H 'Content-Type: application/json' -d '{"approved":true}'
```

Expected: HTTP **403**. Then try reading that run from another tenant:

```bash
curl -sS -w '\nHTTP %{http_code}\n' -u other:other-demo \
  "http://127.0.0.1:8094/api/runs/$BATCH_RUN_ID"
```

Expected: HTTP **404**. Try forging a tenant in a new request:

```bash
curl -sS -w '\nHTTP %{http_code}\n' -u reader:reader-demo \
  http://127.0.0.1:8094/api/runs -H 'Content-Type: application/json' \
  -d '{"scenario":"BATCH","maxSteps":4,"tenant":"demo-b"}'
```

Expected: HTTP **400**. These attempts do not approve the pending job.

**Apply it at work:** derive scope from trusted identity, validate tool arguments,
check resource ownership downstream, and separate read/write/execute capabilities.
Replace the local Basic users with the enterprise identity solution; use the
[Phase 12 identity track](../../Phase12_Enterprise_AI_Identity_Security/README.md)
for a larger example.

## 8. Evals for Agents — verify the result and the route taken

**What it means:** an evaluation checks whether the system did the intended
task correctly, used appropriate tools, respected constraints, and stayed within
its budget. A correct answer reached through unauthorized access is still a failure.

**When you use it:** before accepting a change to code, prompts, a model,
retrieval, or tool schemas, and when turning incidents into regression cases.

### Use the runnable checks today

From terminal B, run:

```bash
mvn test
```

The test process has its own in-memory context and does not clear the server's
pending run. The current suite has 13 tests covering loop controls, contract
fixtures, API permissions, approval transitions, and real batch execution.

| Inspect | What you learn |
|---|---|
| [AgentLoopTest](../src/test/java/com/example/engineering/AgentLoopTest.java) | Does the system stop, retry within budget, and require evidence? |
| [ContractReviewTest](../src/test/java/com/example/engineering/ContractReviewTest.java) | Does the supported comparison catch the fixture break without flagging the unchanged contract? |
| [ApiWorkflowTest](../src/test/java/com/example/engineering/ApiWorkflowTest.java) | Are tenant/approval boundaries enforced, and does duplicate approval avoid a second launch? |

Expected: a successful build with no failed tests. These are deterministic
implementation checks. There is no model-quality evaluation runner in this lab.

### Add model evals when you connect an LLM

1. Select fictional golden cases from the
   [evaluation matrix](evaluation-and-production.md#golden-cases-when-adding-a-model).
2. For each case, record authorized scope, fixture versions, expected facts,
   allowed/forbidden actions, and budgets before running the model.
3. Run through the same execution controls as the application. Capture actual
   final output and tool trajectory, plus latency and usage when available.
4. Score objective rules in code; review explanation quality with a calibrated
   human/model rubric. Do not average away an unauthorized action.
5. Compare repeated trials against a recorded baseline before promoting a change.

Use this assistant request to prepare the work:

```text
Read Phase14_Enterprise_Agent_Engineering/skills/enterprise-agent-evaluation/SKILL.md.
Create a fictional evaluation plan for API diagnosis and approved catalog refresh.
Include expected tool sequences, forbidden actions, stale evidence, injected
instructions, and budget exhaustion. Separate existing JUnit coverage from model
evals we still need to implement. Do not invent measured results.
```

Your output should be a case table and rubric. Once executed, keep a result record
with case ID, model/prompt/tool versions, actual outcome, trajectory, score,
latency/cost if measured, and evidence location. A plan alone is not a passing eval.

## 9. Human-in-the-Loop Design — review an exact proposed action

**What it means:** a person reviews the evidence and exact effect before a
material operation executes. Approval belongs to an authenticated action-specific
workflow, not to a sentence generated by the model.

**When you use it:** for actions your organization classifies as requiring review,
such as selected job launches, restarts, or configuration changes.

**Developer steps:**

1. Read the pending proposal before deciding:

```bash
curl -sS -u reviewer:reviewer-demo \
  "http://127.0.0.1:8094/api/runs/$BATCH_RUN_ID"
```

2. Review its tenant, evidence, and recommendation. The lab's fixed action upserts
   exactly two bundled fictional documents; there is no editable command payload.
3. Approve it as the reviewer:

```bash
curl -sS -u reviewer:reviewer-demo \
  "http://127.0.0.1:8094/api/runs/$BATCH_RUN_ID/decision" \
  -H 'Content-Type: application/json' -d '{"approved":true}'

curl -sS -u reader:reader-demo http://127.0.0.1:8094/api/catalog
```

**Expected result:** `JOB_COMPLETED` with a `jobExecutionId`, followed by a
catalog count of two. Repeat the same approval request: the execution ID remains
the same. Create a separate pending BATCH run if you want to try
`{"approved":false}`; it becomes `REJECTED` and cannot later be approved.

**Apply it at work:** bind review to tenant, immutable parameters/input version,
approver, expiry, and current resource state. Persist the decision and execution
handoff. The local roles demonstrate different capabilities, not enforced
person-level separation of duties or durable crash recovery. Use
[enterprise-batch-delivery](../skills/enterprise-batch-delivery/SKILL.md) for
launch design and [enterprise-batch-recovery](../skills/enterprise-batch-recovery/SKILL.md)
for a failed-job recovery assessment. The lab has no restart API.

## 10. Observability & Tracing — inspect what actually happened

**What it means:** logs describe events, metrics summarize behavior, and traces
connect work across components. Together they help identify failures and evaluate
changes with evidence.

**When you use it:** during development, incident diagnosis, model evaluation,
and production operations—not only after something fails.

**Developer steps:**

1. Look in terminal A for `agent_run` and `agent_decision`. Match `run_id` to your
   saved batch ID, then match `job_execution_id` to the approval response.
2. Query the metrics after exercising the application:

```bash
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.runs
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.tool.calls
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.run.duration
curl -sS -u reader:reader-demo http://127.0.0.1:8094/actuator/metrics/agent.decisions
```

3. Interpret each metric at the boundary it measures:

| Metric/event | How a developer uses it |
|---|---|
| `agent.runs` | Count creation outcomes such as COMPLETED, WAITING_APPROVAL, or STEP_LIMIT |
| `agent.tool.calls` | See which allowed tools have executed |
| `agent.run.duration` | Inspect diagnostic-loop duration; it does not include later approval wait or batch execution |
| `agent.decisions` | Count recorded decision outcomes such as JOB_COMPLETED or REJECTED |
| Run + decision + Batch logs | Follow a specific proposal through launch and completion |

Metrics are registered when used; a metric queried before its first event may
return 404. Exact counts depend on how many requests you made. Approving a run
does not rewrite its earlier `agent.runs` creation counter; inspect
`agent.decisions` for the later transition.

**Expected result:** you can explain which tools ran, why the loop stopped, and
which job executed for the approved proposal. The lab has logs and Micrometer
metrics; it has no Grafana dashboard, alert rules, or distributed trace exporter.

**Apply it at work:** instrument model/tool boundaries, propagate trace context
through HTTP and queues, and correlate workflow and job IDs. Add alerts for failed
jobs, increasing tool errors, exhausted budgets, and stale approvals. Measure model
token usage/cost when a model exists. Keep IDs in controlled logs/traces, not
high-cardinality metric labels. Review framework logging too: validation messages
can include rejected input even if your custom audit logs omit payloads.

## Use this on your next real development ticket

You do not need every practice on every ticket. Choose the workflow that fits
the requested change and use the applicable controls.

| Your ticket | Start with | Give the assistant | Ask it to deliver |
|---|---|---|---|
| Add/change a REST endpoint | `enterprise-spring-rest` | Approved requirement, contract, relevant code and tests | Focused implementation, contract update, test evidence |
| Review an API change | `enterprise-openapi-review` | Released/proposed specs and affected consumers | Compatibility findings and migration options |
| Explain API failures | `enterprise-api-diagnose` | Sanitized observations, time window, versioned runbook | Evidence, hypotheses, next read-only probe |
| Build an ingestion job | `enterprise-batch-delivery` | Input identity, writer effects, transaction/review requirements | Job design/code and replay/approval tests |
| Assess a failed job | `enterprise-batch-recovery` | Execution state, parameters, checksum, committed progress | Exact recovery proposal and prerequisites |
| Add internal document Q&A | `enterprise-rag-context` | Approved sources, ACLs, version/retention requirements | Scoped context/retrieval design and grounded cases |
| Connect tools or a model | `enterprise-agent-loop` | Planner/tool interfaces, budgets, completion criteria | Bounded orchestration and failure tests |
| Evaluate an agent change | `enterprise-agent-evaluation` | Golden cases, baseline, model/prompt/tool versions | Evaluation plan or measured results, clearly distinguished |
| Challenge an uncertain design | `grill-me` | Proposal, existing decisions, desired question limit | Focused questions and a decision record |

For any skill, use this prompt pattern without installing anything globally:

```text
Read Phase14_Enterprise_Agent_Engineering/skills/<skill-name>/SKILL.md and its
scenario reference. My task is: <specific outcome>. Relevant files are: <paths>.
Use the existing project conventions and fictional examples. Deliver <artifact>
with verification evidence. Flag missing information that affects correctness.
```

The [skill-pack guide](skill-pack.md) has clickable skill links and optional
installation instructions. The Matt Pocock-inspired `grill-me` here is an
attributed enterprise adaptation. Invoke it when you want an interview; it is
not a required gate before ordinary development.

### Example: an end-to-end Spring Batch ticket

1. **Define:** “Refresh approved technical documents for one tenant after review.”
   If restart/approval semantics are unclear, use `grill-me` to settle them.
2. **Specify:** use `enterprise-openapi-review` to review the proposed
   request/status/decision contract and identify compatible consumer behavior.
3. **Implement:** use `enterprise-spring-rest` for the boundary and
   `enterprise-batch-delivery` for input identity, chunks, writes, and launch.
4. **Control:** use `enterprise-agent-loop` if a model chooses tools; ensure every
   execution still passes through policy and shared budgets.
5. **Verify:** run deterministic tests, then use `enterprise-agent-evaluation`
   for model behavior if a model is connected.
6. **Observe:** inspect the run, decision, and job evidence. Confirm business
   output and failure behavior rather than relying on a launch response alone.
7. **Review:** present the change, test/eval results, and operational limitations
   through the team's normal review process. Deploy only within authorized scope.

## Completion checklist

- [ ] REST diagnostics return evidence and two attempts.
- [ ] One allowed attempt returns STEP_LIMIT.
- [ ] OpenAPI review identifies the removed `name` guarantee.
- [ ] A saved run can be read by its tenant.
- [ ] A batch proposal waits without launching.
- [ ] Reader approval is denied and another tenant cannot read the run.
- [ ] Deterministic tests pass; model evals are understood as separate work.
- [ ] Reviewer approval executes the job and leaves two catalog documents.
- [ ] Repeated approval returns the same execution ID.
- [ ] Logs and metrics explain the run and decision.
- [ ] The developer can select a skill and state its expected output.

For deeper explanations, use [the ten practices](engineering-practices.md).
For implementation boundaries and the next adoption steps, use
[evaluation and production](evaluation-and-production.md). For more workplace
recipes, use [enterprise scenarios](enterprise-scenarios.md).
