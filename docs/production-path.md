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

## Production Checklist

- Clear local startup command
- Health endpoint
- Auth or API key boundary where needed
- Config through environment variables
- Logs and metrics
- Safe sample data
- Expected output or screenshots
- Known limitations and next steps

## Good Portfolio Outcome

Run DocuMind locally, seed demo data, capture screenshots, and explain how the
same service would be hardened for a private deployment.
