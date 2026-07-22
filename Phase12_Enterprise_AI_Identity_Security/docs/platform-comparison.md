# Enterprise AI Identity Platform Comparison

**Last verified:** 2026-07-20. Product names, availability, licensing, preview
status, and API details change quickly. Follow the linked primary documentation
before making an architecture or procurement decision.

The rows are not equivalent product categories. The table explicitly separates
agent-native identity control planes, general cloud workload IAM, model API
service accounts, and agent-runtime/workspace governance.

| Platform/surface | Primary principal | User delegation | Short-lived credential path | Governance and audit | Important limitation |
|---|---|---|---|---|---|
| AWS Bedrock AgentCore Identity | agent workload identity | workload access context can include end-user identity | workload access token plus credential providers/token vault | identity directory, IAM/provider controls, AWS and app audit | provider-specific; application still enforces task and tenant policy |
| Microsoft Entra Agent ID | blueprint-created agent identity with owner/sponsor | explicit autonomous and interactive/delegated patterns | blueprint acquires tokens on behalf of credential-less agent identity | lifecycle, permissions, Conditional Access/governance features by license | agent identities are tenant-local; licensing and availability vary |
| Google Cloud Vertex AI + IAM | service account, federated principal, or managed workload identity | caller can impersonate a privilege-bearing service account | WIF/ST​S and service-account impersonation | IAM Conditions and Cloud Audit Logs | not an identical agent-specific directory object |
| OpenAI API Platform | project service account and API key | handled by the customer's application and identity tier | API keys at the API boundary; customer can broker narrower internal task tokens | projects, roles, Admin/Audit Logs APIs and enterprise controls | project service account is not a general agent-to-agent delegation protocol |
| OpenAI Workspace Agents | workspace user/agent access and authenticated connections | connections can be user-, shared-, or agent-owned depending on configuration | product-managed sessions/connections | workspace RBAC, publishing controls, centralized administration | connection ownership can let other users act through the creator; review carefully |
| Anthropic API/MCP connector | API credential plus remote MCP authorization token | customer application and MCP authorization determine delegation | OAuth bearer token can be supplied for a protected remote MCP server | API/workspace controls plus MCP server audit | MCP connector support is not an enterprise agent identity directory |

## Why generic checkmarks are misleading

“Supports identity” could mean a cloud workload principal, an agent-specific
directory object, a project bot user, or an authenticated product connection.
Likewise, “delegation” could mean OAuth on-behalf-of, service-account
impersonation, a model invoking a tool with the user's connection, or an
application-defined task token. Evaluate the exact principal and token flow.

## Evaluation checklist

- Is there one governed principal per deployed agent or only per application?
- Can a human sponsor/owner be queried and required throughout the lifecycle?
- Can a child agent receive strictly less authority than its parent?
- Is the credential bound to an audience, task, tenant, and short lifetime?
- Can an operator revoke one agent or one task immediately?
- Do logs preserve both the delegating actor and acting workload/agent?
- Are MCP tool authorization and data-layer tenant checks still required?
- Are any exported API keys or client secrets being mistaken for agent identity?

## Primary references

- [AWS AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html)
- [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities)
- [Google Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation)
- [OpenAI project service accounts](https://platform.openai.com/docs/api-reference/project-service-accounts)
- [OpenAI Workspace Agents](https://help.openai.com/en/articles/20001143-chatgpt-workspace-agents-for-enterprise-and-business)
- [Anthropic MCP overview](https://docs.anthropic.com/en/docs/mcp)
- [MCP authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
