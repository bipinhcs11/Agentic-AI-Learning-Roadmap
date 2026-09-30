# Architecture Requirements Document — Enterprise MCP Diagnostic POC

## 1. Purpose

Define the minimum architecture required to demonstrate one governed,
read-only Work Item → Config Check diagnostic flow from an approved developer
IDE. The runnable implementation uses fictional data only.

## 2. Scope

### Included

- GitHub Copilot Chat through an approved VS Code or JetBrains MCP host;
- one externally reachable MCP gateway;
- one validated Git-backed registry snapshot;
- Work Item Analysis MCP with `work_item_analyze`;
- Config Check MCP with `config_check`;
- fixed read-only calls through an internal API gateway shape;
- workload-secret, token, schema, policy, limit, trace, and audit controls; and
- local, test, dev, and prod-shaped configuration overlays.

### Excluded

Real enterprise/customer data, source code, writes, generic REST/SQL, direct
database access, Sonar/Jira/skills capabilities, autonomous agents, A2A,
dynamic routing, a registry portal, and production availability controls.

## 3. System requirements

| ID | Requirement |
|---|---|
| ARD-SYS-001 | The MCP client shall be configured with the gateway URL only. |
| ARD-SYS-002 | Scenario servers shall not publish developer-accessible endpoints. |
| ARD-SYS-003 | The gateway shall load only schema-valid, active, unexpired manifests. |
| ARD-SYS-004 | The gateway shall expose exactly the two registered read-only tools. |
| ARD-SYS-005 | Work Item and Config Check shall be independently deployable processes. |
| ARD-SYS-006 | Each server shall use fixed relative API paths and GET operations only. |
| ARD-SYS-007 | The flow shall complete without an embedded or autonomous agent. |

## 4. Identity and authorization requirements

| ID | Requirement |
|---|---|
| ARD-IAM-001 | The gateway shall validate signature, issuer, audience, time, subject, and client ID. |
| ARD-IAM-002 | Both global and per-manifest client approval shall be required. |
| ARD-IAM-003 | Calls shall require the `mcp.diagnostic.read` role. |
| ARD-IAM-004 | Only `WI-DEMO-001` and `P-DEMO-001` shall be allowed locally. |
| ARD-IAM-005 | The inbound user/client token shall never be forwarded downstream. |
| ARD-IAM-006 | Each scenario shall have a distinct assertion signing key. |
| ARD-IAM-007 | Assertions shall be short-lived and bound to server audience, scenario, tool, and trace. |
| ARD-IAM-008 | Each scenario shall have a separate backend credential path and OAuth scope. |
| ARD-IAM-009 | Backend tokens shall be obtained for the configured API audience before fixed API calls. |

## 5. Registry and policy requirements

| ID | Requirement |
|---|---|
| ARD-REG-001 | Manifests shall define ownership, hosting, lifecycle, classification, approved clients, and tools. |
| ARD-REG-002 | Tool schemas shall reject unknown properties and bound string length/pattern. |
| ARD-REG-003 | The gateway shall advertise and enforce the same manifest input schema. |
| ARD-REG-004 | Runtime timeout and response caps shall come from the registered tool. |
| ARD-REG-005 | Invalid, duplicate, disabled, or expired entries shall fail closed. |
| ARD-REG-006 | Every policy decision shall include the active registry digest. |

## 6. API and secret requirements

| ID | Requirement |
|---|---|
| ARD-API-001 | A tool shall not accept an arbitrary URL, method, header, query, or credential. |
| ARD-API-002 | Redirects shall be disabled and TLS verification required outside local/test. |
| ARD-API-003 | Response size shall be enforced while streaming, before full buffering/JSON parsing. |
| ARD-API-004 | Upstream bodies and infrastructure locations shall not be returned in errors. |
| ARD-SEC-001 | YAML and manifests shall not contain secrets. |
| ARD-SEC-002 | Shared environments shall obtain secrets using an approved workload identity. |
| ARD-SEC-003 | Static cloud access keys shall not be distributed to developers. |

The supplied shared-environment adapter authenticates to HashiCorp Vault with
the ordinary AWS credential chain. An Azure deployment must approve an AWS-IAM
workload mechanism for Container Apps or replace only the secret-provider
adapter with Azure Key Vault/managed identity.

## 7. Trace and audit requirements

| ID | Requirement |
|---|---|
| ARD-OBS-001 | A valid W3C trace context shall be propagated; otherwise the gateway shall create one. |
| ARD-OBS-002 | Gateway authentication and authorization shall emit allow/deny reason metadata. |
| ARD-OBS-003 | Server token and API operations shall emit child metadata events. |
| ARD-OBS-004 | Subjects and resource IDs shall be irreversibly referenced in logs. |
| ARD-OBS-005 | Prompts, arguments, results, payloads, tokens, secrets, and personal data shall not be logged. |

## 8. Deployment requirements

### Local proof

- gateway bound to loopback and published on port 8080;
- Work Item and Config Check reachable only on the Compose network;
- fictional identity/API fixture published on port 9000; and
- exact Host/Origin protection derived from configured service URLs.

### Azure enterprise target

| Component | Placement |
|---|---|
| MCP policy edge | Azure API Management |
| approved catalog | Azure API Center |
| gateway and servers | private Azure Container Apps |
| secrets | approved Vault integration or Azure Key Vault decision |
| traces | Application Insights and Log Analytics |
| APIs | existing internal API gateway over private networking |
| on-prem connectivity | approved VPN or ExpressRoute route |

Azure Foundry is not a dependency for the POC. Equivalent AWS or on-premises
hosting is acceptable when the same identity, gateway-only ingress,
least-privilege credential, private route, and audit requirements are met.

## 9. Acceptance and next gate

The architecture is accepted for a shared non-production integration test only
after the automated and manual evidence in
[MVP Acceptance Plan](mvp-acceptance-plan.md) passes. That next test shall keep
the same two tools and substitute approved identity, secrets, internal APIs, and
telemetry. Adding a new domain capability requires a separate review.

## 10. Future extension rule

A future Sonar, skills, database, or agent capability must be a separately
owned and deployed component with its own manifest, data classification,
credential, backend scope, network path, limits, audit evidence, and approval.
Generic SQL, arbitrary REST proxying, and permission inheritance across agents
remain prohibited patterns.
