# Production Path

Use this path if you want to turn local AI projects into services that look like
real products.

## Recommended Order

| Step | Folder | Skill |
|---:|---|---|
| 1 | `Phase3_Agentic_Stack/project_06_agent_api_server/` | Serve an agent through FastAPI |
| 2 | `Phase6_Production_Enterprise/project_01_dockerize/` | Add Docker, UI, API, and nginx |
| 3 | `Phase6_Production_Enterprise/project_02_auth_rbac/` | Add JWT, roles, and API keys |
| 4 | `Phase6_Production_Enterprise/project_04_observability/` | Add Prometheus and Grafana |
| 5 | `Phase6_Production_Enterprise/project_06_capstone_product/` | Run the DocuMind SaaS-style capstone |
| 6 | `Phase8_Integrations_Shipping/project_04_multitenant_saas/` | Add tenant isolation and quotas |
| 7 | `Phase8_Integrations_Shipping/project_06_capstone_launch/` | Practice launch packaging |
| 8 | `Phase10_Google_ADK_Series/` | Study a containerized ADK + A2A multi-service demo |
| 9 | `Phase12_Enterprise_AI_Identity_Security/module_02_agent_identity_service/` | Register governed agents and issue signed short-lived credentials |
| 10 | `Phase12_Enterprise_AI_Identity_Security/module_06_mcp_security/` | Enforce scope, audience, tenant, task, and revocation at MCP tools |
| 11 | `Phase12_Enterprise_AI_Identity_Security/module_10_enterprise_ai_access_gateway/` | Compose Keycloak, OPA, PostgreSQL, Redis, MCP, and traces |
| 12 | `Phase12_Enterprise_AI_Identity_Security/module_11_live_cloud_deployment/` | Plan a keyless Terraform-first deployment to one isolated cloud sandbox |

## Production Checklist

- Clear local startup command
- Health endpoint
- Auth or API key boundary where needed
- Config through environment variables
- Logs and metrics
- Safe sample data
- Expected output or screenshots
- Known limitations and next steps
- Separate human, workload, agent, and task identities
- Audience-bound credentials with explicit revocation and tenant enforcement
- Correlated policy, tool, audit, and trace identifiers
- Keyless cloud CI/CD, cost controls, automated denial tests, and verified teardown

## Good Portfolio Outcome

Run DocuMind and the Phase 12 Enterprise AI Access Gateway locally. Explain how
identity, delegation, policy, tenant isolation, revocation, and audit work across
the complete agent tool-call path. Then design or complete one Module 11 cloud
track and demonstrate the same controls with native workload identity.
