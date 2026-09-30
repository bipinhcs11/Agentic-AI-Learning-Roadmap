# Control Implementation Status

This document prevents the POC code, enterprise deployment target, and future
platform vision from being mistaken for the same maturity level.

## Implemented and tested locally

- one MCP gateway and exactly two registered tools;
- separate Work Item Analysis and Config Check processes;
- JWT issuer/audience/time/client validation;
- required role and two fictional resource allowlists;
- manifest validation plus advertised/enforced input schemas;
- exact tool registration, timeout, and response-size policy;
- separate per-scenario assertion secrets, API credential paths, and scopes;
- no inbound-token passthrough;
- Vault AWS-IAM adapter and environment-only fictional local provider;
- token acquisition before each fixed read-only API operation;
- streaming response cap, no redirects, and sanitized errors;
- W3C trace propagation and metadata-only allow/deny audit events;
- Host/Origin protection derived from configured URLs;
- gateway-only published scenario access in Docker Compose;
- locked Python dependencies and CI validation; and
- offline functional and negative tests using fictional data.

## Partially represented; requires enterprise integration

| Area | POC evidence | Still required |
|---|---|---|
| IDE/SSO | JWT contract and protected-resource metadata | approved client registration, IdP/JWKS, real IDE handshake |
| Azure policy edge | gateway contract is APIM-compatible | APIM policy, routing, certificates, and ownership |
| registry catalog | validated Git snapshot | API Center publication and activation process |
| secrets | Vault AWS-IAM adapter | approved Container Apps-to-Vault auth or Key Vault adapter |
| private network | Compose-only server ingress | Container Apps ingress, private DNS, API route, VPN/ExpressRoute if needed |
| telemetry | correlated JSON event contract | Application Insights/Log Analytics ingestion, retention, access, alerts |
| registry change | fail-closed startup snapshot | signed publication, reload, maximum staleness, emergency revocation |

## Deliberately deferred

- Sonar remediation, Jira integration, coding standards, and skill generation;
- Oracle/PostgreSQL and generic database access;
- agents, A2A, writes, prompts, resources, sampling, or human approval flows;
- dynamic routing, portal/self-service, multi-tenant policy, and scale testing;
- asymmetric internal assertions and distributed replay prevention;
- rate limits, circuit breakers, high availability, disaster recovery, and SLOs;
- production DLP/SIEM controls; and
- base-image digest pinning, SBOM generation, artifact signing, and deployment
  provenance.

No deferred item is necessary to demonstrate the agreed two-server POC. The
next recommended move is to test this unchanged flow with approved enterprise
non-production infrastructure.
