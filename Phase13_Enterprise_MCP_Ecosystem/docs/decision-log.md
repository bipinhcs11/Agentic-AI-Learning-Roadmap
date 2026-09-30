# Architecture Decision Log

## Fixed for this POC

| ID | Decision | Reason |
|---|---|---|
| ADR-001 | Registry is the approval control plane; gateway is the runtime enforcement plane | separates reviewed metadata from request processing |
| ADR-002 | All MCP client traffic enters through one gateway | creates one identity, policy, schema, and trace boundary |
| ADR-003 | Exactly two active servers and two tools | proves the diagnostic sequence without platform sprawl |
| ADR-004 | Work Item and Config Check deploy separately | preserves ownership and credential isolation |
| ADR-005 | Tools only and read-only | matches the permitted non-production profile |
| ADR-006 | Fictional IDs are gateway allowlisted | keeps data and authorization evidence deterministic |
| ADR-007 | No inbound-token passthrough | preserves audience and least-privilege boundaries |
| ADR-008 | One backend token per API operation by default | demonstrates the requested one-operation token constraint |
| ADR-009 | Separate assertion key and API credential per scenario | limits cross-server compromise impact |
| ADR-010 | Registry schemas are advertised and enforced | avoids drift between governance and runtime validation |
| ADR-011 | Git snapshot plus restart for change activation | simplest reviewable POC control plane |
| ADR-012 | Python and Docker Compose for the runnable slice | fastest clear implementation with separate processes |
| ADR-013 | Azure target does not require Azure Foundry | this flow is client, policy, tool, API, and trace infrastructure |

## Required before a shared enterprise test

| Decision | Required evidence |
|---|---|
| approved IDE/client registration and issuer/JWKS | client authentication handshake and claims |
| Azure Vault-auth method or approved Key Vault substitution | workload identity and key-rotation review |
| private gateway-to-server and server-to-API routes | network and certificate test |
| API scopes and fictional/synthetic test contract | API owner and data-governance approval |
| trace/audit destination and access | operator can reconstruct allow and deny paths |
| registry publication and emergency disable process | owner, signature/checksum, activation, rollback test |

## Deferred

- Sonar remediation, Jira/PAT integration, coding standards, and skill lifecycle;
- Oracle/PostgreSQL MCP servers and all generic SQL/REST capabilities;
- real source code, customer data, or production API access;
- portal, database registry, dynamic routing, and self-service onboarding;
- autonomous agents, A2A, write tools, and human-approval workflows;
- asymmetric internal assertions, distributed replay cache, DLP/SIEM, rate
  limiting, circuit breaking, high availability, and disaster recovery; and
- SBOM/signing/base-image digest controls.

These are not rejected ideas. They are intentionally sequenced after the same
two-server flow passes an approved enterprise integration test.
