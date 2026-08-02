# POC Delivery Plan

The POC is sequenced by evidence milestones, not calendar-day promises. Keep the
same two-server diagnostic flow through every milestone.

## Milestone 1 — Contract and boundary

- approve the fictional Work Item → Config Check story;
- approve the two manifests, input schemas, client ID, role, and resource IDs;
- confirm the client connects only to the gateway; and
- record the target identity, secret, network, API, and telemetry owners.

Exit evidence: architecture, manifest, and threat-boundary review.

## Milestone 2 — Functional vertical slice

- run gateway, Work Item, Config Check, and fictional API fixture separately;
- complete both approved MCP calls;
- obtain a backend token before each fixed API operation; and
- show the deterministic missing-configuration diagnosis.

Exit evidence: successful local demo and expected output.

## Milestone 3 — Fail-closed controls

- prove JWT, approved-client, role, resource, registry, and schema denials;
- prove direct-server and wrong-assertion denials;
- prove timeout, response-size, invalid Host/Origin, and token-replay behavior;
- scan logs for sensitive fixture values; and
- validate dev/prod-shaped HTTPS and Vault configuration.

Exit evidence: passing negative test matrix.

## Milestone 4 — Operability and presentation

- correlate gateway, server, token, and API events with one trace ID;
- show allow/deny reason and registry digest without payloads;
- validate locked dependencies and Docker Compose topology; and
- present implemented, partial, and deferred controls without claiming
  production readiness.

Exit evidence: CI output, trace sample, deck, and control-status document.

## Milestone 5 — Enterprise integration decision

Choose whether the same flow may be tested with approved non-production
identity, workload secrets, internal API gateway, private routing, and telemetry.
Do not add Sonar, skills, database, or agent scope to that integration test.

Exit evidence: named owners, approved substitutions, residual risks, and a
go/no-go decision.
