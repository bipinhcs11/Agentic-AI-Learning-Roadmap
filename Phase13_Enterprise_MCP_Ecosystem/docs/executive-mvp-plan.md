# Enterprise MCP Ecosystem — Executive POC Plan

## Recommendation

Approve a non-production technical POC for one read-only developer diagnostic
scenario. It should prove that an enterprise can place a reliable identity,
policy, registry, and audit boundary between an AI-enabled IDE and internal
tools without exposing those tools directly.

The POC is deliberately limited to:

- GitHub Copilot Chat in an approved VS Code or JetBrains host;
- one MCP gateway;
- one Git-backed approved registry snapshot;
- Work Item Analysis and Config Check MCP servers;
- two read-only tools using fictional records; and
- fixed calls through a fictional internal API gateway.

It does not include Sonar remediation, skill generation, databases, write
operations, autonomous agents, or agent-to-agent delegation.

## What decision this enables

The POC answers four questions:

1. **Compatibility:** Can the chosen client initialize, discover, and call tools
   through one gateway endpoint?
2. **Control:** Can the gateway enforce client, role, server, tool, schema, and
   fictional resource scope on every call?
3. **Isolation:** Can every MCP server use a distinct assertion and backend
   credential without receiving the developer token?
4. **Operability:** Can a reviewer reconstruct an allow or deny path from one
   trace ID without recording business payloads?

Productivity improvement and production readiness are not POC claims.

## Architecture decision

| Control plane — Registry | Runtime plane — Gateway |
|---|---|
| approved servers, tools, schemas, owners, status | authenticate user and client |
| versioned, reviewable Git source | authorize role, tool, and resource scope |
| validated snapshot digest | validate schema and bound timeout/size |
| future publication via an approved catalog | route, trace, audit, and fail closed |

The registry is not a synchronous dependency for every call. The gateway uses a
validated snapshot. The two MCP servers remain separately deployable and are
reachable only from the gateway network.

## Target deployment without expanding POC scope

| Component | Recommended Azure location |
|---|---|
| MCP client | GitHub Copilot Chat in VS Code or JetBrains |
| registry/catalog | Azure API Center |
| policy edge | Azure API Management |
| gateway and two MCP servers | private Azure Container Apps |
| secrets | approved HashiCorp Vault integration or Azure Key Vault decision |
| telemetry | Application Insights and Log Analytics |
| existing APIs | current internal API gateway over private connectivity |

Azure Foundry is not required for this client-to-tool path. AWS and on-premises
hosting remain possible by preserving the same gateway contract and replacing
only approved identity, secret, private-network, and telemetry adapters.

## Evidence required

- exactly two tools are discoverable;
- the fictional Work Item → Config Check diagnosis completes;
- negative tests prove missing/invalid identity, policy, schema, direct-access,
  wrong-assertion, timeout, and response-limit denials;
- traces show gateway and downstream operations without inputs or results; and
- the target environment decision names its identity, secret, network, and
  telemetry owners.

## Explicit non-goals

- production rollout, high availability, or multi-region recovery;
- a registry portal, dynamic routing, or self-service onboarding;
- customer, participant, employee, repository, or source-code data;
- arbitrary REST, generic SQL, or write-capable tools;
- Sonar/Jira integrations, skill branch generation, agents, or A2A; and
- a custom IDE plugin.

## Decision requested

Approve this two-server fictional POC and a single follow-on enterprise
integration test of the same flow. Do not approve additional capabilities until
the existing identity, policy, trace, and credential boundaries have passed the
acceptance plan and received architecture/security review.
