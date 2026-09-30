# Python MVP implementation guide

This implementation is a fictional, local-first vertical slice of the proposed
enterprise MCP ecosystem. It demonstrates the security and interaction model;
it is not production infrastructure and contains no real organization,
customer, repository, participant, or credential data.

## Implemented request path

```text
GitHub Copilot / IDE MCP host
  -> user/client JWT
  -> Enterprise MCP Gateway
  -> approved registry manifest
  -> scenario-bound internal assertion
  -> scenario MCP server
  -> AWS IAM authentication to HashiCorp Vault
  -> scenario-specific API client credential from Vault KV v2
  -> OAuth client-credentials token request
  -> short-lived API JWT
  -> fixed read-only operation through the internal API gateway
  -> trace-correlated result returned through the MCP Gateway
```

For the local demo, environment variables replace Vault and the included mock
service replaces both the identity provider and internal API gateway. The
shared-environment code path uses the ordinary AWS credential chain, Vault AWS
IAM login, and a scenario-specific Vault KV v2 path. No AWS access key is stored
in configuration.

The default is `reuse_access_tokens: false`: every internal API operation first
requests a token and then makes the actual API call. The mock API also rejects a
second use of the same token ID. If the enterprise identity platform issues
normal reusable access tokens, token reuse can be enabled only after identity
and threat-model review.

## What is deployed separately

```text
gateway                             :8080
work_item_analysis MCP server       :8101
config_check MCP server             :8102
fictional local identity/API fixture:9000
```

The scenario layout and allowed operations are documented in
[`src/enterprise_mcp/servers/README.md`](../src/enterprise_mcp/servers/README.md).

## Environment configuration

Configuration is loaded as `config/base.yaml` plus exactly one overlay:

| Overlay | Purpose | Secret source | Transport |
|---|---|---|---|
| `local` | laptop or Docker Compose demo | fictional environment values | loopback HTTP |
| `test` | deterministic automated tests | test doubles | in-process mock transport |
| `dev` | enterprise non-production deployment | Vault using AWS IAM | private TLS endpoints |
| `prod` | future production-shaped baseline | Vault using AWS IAM | private TLS endpoints |

Set `MCP_ENV` to select the overlay. Endpoint environment overrides exist for
container service discovery and deployment injection. Secret values are not
accepted in YAML.

For Azure Container Apps, use an AWS-compatible workload credential mechanism
approved by the enterprise or replace only the `SecretProvider` adapter with an
approved Vault authentication method. The MCP protocol, gateway policy, and
scenario servers remain unchanged. For an AWS runtime, use its attached IAM
role. For an on-prem runtime, use an approved Vault auth method or AWS IAM role
delivery mechanism; do not distribute static AWS keys to developers.

## Run locally

Prerequisites: Python 3.11+ and Docker Compose.

Create the development environment and run focused checks:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
```

Start the isolated services:

```bash
docker compose up --build
```

In another shell, create a short-lived fictional IDE token and run the gateway
demo:

```bash
MCP_DEMO_TOKEN=$(.venv/bin/python scripts/create_local_gateway_token.py)
.venv/bin/python scripts/demo_client.py --token "$MCP_DEMO_TOKEN"
```

Expected result, abbreviated:

```json
{
  "configCheck": {
    "diagnosis": "MISSING_ENROLLMENT_CONFIGURATION",
    "participantId": "P-DEMO-001"
  },
  "workItemAnalysis": {
    "missingEvidence": ["enrollment"],
    "nextApprovedTool": "config_check",
    "participantId": "P-DEMO-001",
    "workItemId": "WI-DEMO-001"
  }
}
```

Each API operation emits metadata-only JSON with a trace ID, span ID, service,
operation, decision, outcome, and duration. It intentionally excludes request
arguments, API payloads, bearer tokens, Vault secrets, and personal data.

## Production substitutions

| MVP component | Enterprise substitution |
|---|---|
| local IDE token script | enterprise SSO/OIDC token presented by the approved MCP host |
| Python MCP gateway | gateway runtime behind Azure API Management or equivalent policy edge |
| Git manifest loader | approved registry snapshot published by Azure API Center or equivalent |
| environment secret provider | HashiCorp Vault using workload identity |
| mock token endpoint | approved identity/token service |
| mock APIs | existing internal API gateway and allowlisted read APIs |
| JSON audit sink | OpenTelemetry/Application Insights/Log Analytics or approved SIEM pipeline |
| Docker Compose | private Azure Container Apps, Kubernetes, OpenShift, or equivalent |

## Guardrails preserved in code

- The IDE connects only to the MCP gateway.
- Registry entries must be approved, unexpired, sandbox-enabled, and schema-valid.
- Gateway JWTs are issuer-, audience-, expiry-, and approved-client-validated.
- Inbound developer tokens are never forwarded to MCP servers or internal APIs.
- Each MCP server receives a scenario-bound internal assertion.
- Each scenario has a separate credential location and least-privilege API scope.
- Outbound operations use fixed relative paths, bounded timeouts, response-size
  limits, no redirects, and read-only HTTP GET.
- Errors are sanitized and audit events never include payloads or secrets.
- The example performs deterministic evidence aggregation; it does not embed or
  autonomously invoke an AI agent.

## Known MVP limits

- Real enterprise SSO, Vault, API gateway, and private-network connectivity are
  represented by production-shaped adapters but are not exercised locally.
- The in-memory registry snapshot and JSON audit sink are single-instance MVP
  choices.
- The gateway assertion is short-lived and scenario-bound, but distributed
  replay prevention requires an enterprise token service or shared replay store.
- Database MCP servers and agent-to-agent delegation remain outside this slice.
- Sonar remediation guidance and skill branch generation require separate
  reviewed capabilities; the current MCP tools only read approved evidence.

## Primary implementation references

- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [HashiCorp Vault AWS auth](https://developer.hashicorp.com/vault/docs/auth/aws)
- [Vault Agent AWS auto-auth guidance](https://developer.hashicorp.com/vault/docs/agent-and-proxy/autoauth/methods/aws)
- [hvac AWS IAM login](https://python-hvac.org/en/stable/usage/auth_methods/aws.html)
- [hvac KV v2 reads](https://python-hvac.org/en/stable/usage/secrets_engines/kv.html)
- [OAuth 2.0 client credentials](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4)
