# Azure Live Deployment Track

This track deploys the Phase 12 security contract to a dedicated Azure sandbox
subscription. It is a specification until its Terraform and automated tests
are added.

## Target mapping

| Phase 12 responsibility | Azure target |
|---|---|
| Agent and service execution | Azure Container Apps |
| Workload identity | User-assigned or system-assigned Managed Identity |
| Agent identity | Microsoft Entra Agent ID blueprint and agent identity |
| Human delegation | Microsoft Entra OIDC and delegated authorization |
| Container images | Azure Container Registry with immutable image references |
| Durable identity data | Azure Database for PostgreSQL |
| Task and revocation state | Managed Redis-compatible cache |
| Secrets and signing keys | Azure Key Vault |
| Policy and MCP services | Internal-only Container Apps |
| Audit and traces | Azure Monitor and OpenTelemetry export |
| Keyless CI/CD | GitHub OIDC federated credential to a deployment identity |

Managed Identity must replace local workload tokens for Azure resource access.
Agent ID objects may require Microsoft Graph operations if the current
Terraform providers do not expose the required agent subtype. Such operations
must be idempotent and use only the documented Agent ID permissions.

## Required demonstrations

- Container Apps obtain Azure tokens through Managed Identity without a client
  secret.
- The Agent ID sponsor and accountable fictional owner are recorded.
- Finance and Email identities receive different app roles and cannot exchange
  them through delegation.
- Key Vault access is identity-based and secret values never enter Terraform
  output.
- Internal MCP, policy, database, and cache endpoints are not internet-facing.
- Disabling or revoking the agent causes the next protected action to fail.
- Resource Graph inventory is empty after teardown.

## References

- [Microsoft Entra agent identities](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities)
- [Managed identities in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [Create Microsoft Entra agent identities](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/create-delete-agent-identities)
