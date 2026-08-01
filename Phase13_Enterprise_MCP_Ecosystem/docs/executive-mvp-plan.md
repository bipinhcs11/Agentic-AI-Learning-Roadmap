# Enterprise MCP Ecosystem — Executive MVP Plan

## Recommendation

Approve a five-day, non-production technical MVP to determine whether an
internal MCP control plane and enforcement gateway can safely support one
developer build-intelligence use case.

The MVP should not attempt to prove enterprise scale. It should prove the
architecture's hardest boundaries early:

- the IDE connects to one governed gateway, not arbitrary servers;
- only registry-approved tools are visible and callable;
- user, client, server, tool, and application scope are checked on each call;
- inbound user tokens are not forwarded to internal backends;
- one trace ID explains every allow or deny decision; and
- the entire path remains read-only and free of customer data.

This vertical slice supports a north-star portfolio of bounded Oracle,
PostgreSQL, work-item, Sonar, coding-standards, and security-review MCP servers.
Those servers can run in Azure, AWS, or on-premises close to their backends while
sharing one logical gateway, registry, policy, and trace contract. Permissioned
agent-to-agent collaboration is a separate A2A plane and is not part of week one.

## Why this is the right first investment

MCP can standardize how approved developer tools are presented to AI-enabled
IDEs, but the protocol alone is not an enterprise governance system. A regulated
enterprise still needs authoritative ownership, tool classification, runtime
authorization, schema enforcement, auditability, and emergency shutdown.

The first useful ecosystem therefore has two distinct responsibilities:

| Control plane — Registry | Runtime plane — Gateway |
|---|---|
| Approved server and tool catalog | Authenticate user and client |
| Ownership and lifecycle | Authorize server, tool, and application scope |
| Schemas and risk metadata | Validate requests and bound responses |
| Version and status | Route, time out, fail closed, and audit |

Keeping the registry out of the synchronous invocation path reduces availability
coupling. The gateway consumes a signed or checksum-verified snapshot and keeps
the last known approved configuration only for a bounded period.

## Scope for five days

### Build

- one VS Code remote MCP configuration;
- one stateless gateway endpoint using Streamable HTTP semantics;
- a Git-backed internal registry with JSON Schema validation;
- one Build Intelligence MCP server;
- `get_build_status`, `get_test_failures`, and
  `get_application_owner` tools;
- a fictional CI API adapter and deterministic demo fixtures;
- local OAuth/JWT-compatible identity, with an enterprise test IdP used only if
  its client registration and claims are ready on day 1;
- deny-by-default policy, bounded inputs/outputs, timeouts, correlation IDs,
  metadata-only audit events, health checks, and negative tests.

### Do not build

- source-code retrieval, customer data, production pipeline access, or write
  operations;
- MCP resources, prompts, sampling, elicitation, tasks, or autonomous agents;
- custom IDE plugins, a registry portal, self-service access requests, or
  database-backed workflow;
- production SSO certification, Kubernetes, high availability, SIEM/DLP
  integration, chargeback, or disaster recovery.

## Business outcome and evidence

The week answers four questions:

1. **Compatibility:** Can the chosen VS Code host complete initialization, tool
   discovery, and calls through the gateway?
2. **Control:** Can the platform make reliable tool-level and application-level
   allow/deny decisions?
3. **Operability:** Can an operator correlate, disable, and diagnose the path
   without capturing source code or prompts?
4. **Delivery:** What work remains for a safe pilot with real enterprise identity
   and one approved internal CI integration?

Success is a recorded demo, passing acceptance suite, risk register, the
[Architecture Requirements Document](architecture-requirements-document.md),
and a costed pilot backlog. User adoption or productivity improvement is not a
valid week-one success claim.

## Resourcing assumption

| Role | Commitment | Primary ownership |
|---|---:|---|
| Platform/gateway engineer | 5 days | protocol adapter, registry snapshot, policy, audit |
| MCP/integration engineer | 5 days | server, fictional CI adapter, schemas, test harness |
| Identity/security reviewer | 2–3 hours total | claims, trust boundaries, threat review, demo evidence |
| Product/DevEx owner | 1–2 hours total | use case, acceptance, stakeholder demo |

With one engineer, reduce to one tool. Do not remove deny-by-default policy,
identity boundaries, audit correlation, or negative tests.

## Dependencies that can stop the week

| Dependency | Needed by | Fallback |
|---|---|---|
| Supported VS Code build and MCP host | Day 1 | protocol test client; mark IDE proof incomplete |
| Enterprise test IdP registration | Day 1 | local issuer with identical claims; defer SSO proof |
| Internal CI sandbox/API contract | Day 1 | deterministic fictional adapter; defer live integration |
| Security reviewer | Day 3 | no stakeholder demo until review is completed |
| Network route and certificates | Day 2 | run all services on localhost/Docker Compose |

These fallbacks preserve engineering momentum but must be reported as unproven
production dependencies, not silently counted as success.

## Risk posture

| Risk | MVP treatment | Pilot treatment |
|---|---|---|
| Arbitrary client-to-server connectivity | publish only gateway URL; server binds to private sandbox network | network policy and gateway-only server ingress |
| Token theft or confused deputy | audience validation, short TTL, no token passthrough | enterprise issuer, workload identity, key rotation |
| Tool metadata says read-only but code writes | backend read-only credential plus negative tests | certification and continuous conformance |
| Prompt or result leakage through logs | metadata-only logs and hashes | protected diagnostic workflow, retention policy, DLP |
| Registry outage or stale approval | local verified snapshot with expiry and fail closed | signed distribution, revocation channel, HA registry |
| Protocol or client changes | isolate protocol adapter and pin tested versions | compatibility matrix and upgrade cadence |

## Decision requested

Approve:

- the one-use-case, tools-only, read-only sandbox scope;
- the registry/control-plane and gateway/runtime-plane separation;
- two engineers for five days plus named security and DevEx reviewers;
- use of fictional data until a separate data-access approval is granted; and
- a day-5 go/no-go review for the production-pilot discovery phase.

Do not approve production rollout from the MVP alone.
