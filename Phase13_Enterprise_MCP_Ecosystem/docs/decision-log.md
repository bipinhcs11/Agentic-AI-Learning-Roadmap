# Architecture Decision Log

## Decisions fixed for the MVP

| ID | Decision | Rationale |
|---|---|---|
| ADR-001 | Registry is the control plane; gateway is the runtime plane | separates governance history from request enforcement |
| ADR-002 | All client traffic goes through the gateway | creates one enforceable identity, policy, and audit boundary |
| ADR-003 | Registry is Git-backed for week one | reviewable, versioned, and feasible without a portal or database |
| ADR-004 | Gateway consumes a validated snapshot | avoids a synchronous registry dependency on each tool call |
| ADR-005 | One bounded Build Intelligence server | proves the vertical slice without a monolithic server |
| ADR-006 | Tools only; all other MCP capabilities rejected | matches the initial regulated-enterprise profile |
| ADR-007 | Read-only enforced at five layers | annotations alone are advisory |
| ADR-008 | No user-token passthrough | preserves OAuth audience boundaries and prevents confused-deputy behavior |
| ADR-009 | VS Code first; no custom plugin | fastest supported client path for the engineering use case |
| ADR-010 | IntelliJ is a post-MVP compatibility test | avoids promising parity before version, license, auth, and policy validation |
| ADR-011 | Docker Compose sandbox | deterministic and local-first; production hosting is a later decision |
| ADR-012 | Fictional data only | prevents plan work from creating an unapproved data access path |
| ADR-013 | Target state is a portfolio of bounded domain MCP servers | preserves ownership and least privilege; avoids a monolithic enterprise server |
| ADR-014 | Database servers expose named query tools, never arbitrary SQL | schema permissions alone do not bound query intent, cost, or data disclosure |
| ADR-015 | API-backed tools use fixed operations and workload identity | avoids creating a generic authenticated HTTP proxy |
| ADR-016 | Hybrid placement follows data gravity under one logical gateway contract | supports Azure, AWS, and on-prem backends without public database exposure |
| ADR-017 | Agent collaboration uses a separate permissioned A2A plane | separates tool invocation from task delegation and makes delegated authority explicit |

## Decisions required on day 1

| Decision | Owner | Evidence needed |
|---|---|---|
| pinned MCP protocol, SDK/starter, Java, and VS Code versions | platform lead | compatibility spike |
| stateful versus stateless Streamable HTTP behavior | platform lead | client handshake test |
| local issuer versus enterprise test IdP | identity lead | registration and claim availability |
| fictional adapter versus CI sandbox | CI owner + security | API contract and data approval |
| application entitlement source for the spike | security | fictional claim or approved test directory |
| maximum snapshot age and emergency disable process | platform + security | operating assumption |

## Decisions explicitly deferred

- public registry mirroring or federation;
- portal technology and search engine;
- database, event bus, and registry workflow engine;
- production API gateway extension versus dedicated MCP gateway;
- OPA or enterprise policy engine integration;
- Kubernetes/OpenShift topology, regions, and disaster recovery;
- source-code result handling and DLP;
- IntelliJ rollout and custom IDE plugins;
- write tools, human approval, compensation, and idempotency;
- agent identity, delegated authority, budgets, and kill switches;
- A2A gateway/broker implementation and Agent Registry federation;
- chargeback, business-unit segmentation, and server certification tiers.

## Required production-pilot ADRs

Before real internal data or users are onboarded, approve decisions for:

1. corporate identity discovery, client registration, PKCE, token audience, and
   workload identity;
2. how repository/application entitlements are resolved and cached;
3. signed registry distribution, rollback, revocation latency, and expiry;
4. MCP session ownership and gateway upgrade behavior;
5. request/response data classification, inspection, retention, and diagnostics;
6. gateway and server availability, rate limits, circuit breakers, and capacity;
7. tool and schema versioning, compatibility, deprecation, and rollback;
8. gateway-only network enforcement and certificate management;
9. audit sink, SIEM alerts, incident ownership, and emergency shutdown; and
10. exact meaning and verification of read-only for every backend operation.

## North-star proof decisions

After the MVP, prove capabilities one at a time: an API-backed tool, one
schema-limited database server, one analysis server, then two fictional
read-only agents with bounded A2A delegation. Do not combine Oracle,
PostgreSQL, Sonar, source-code handling, and A2A into the first pilot.
