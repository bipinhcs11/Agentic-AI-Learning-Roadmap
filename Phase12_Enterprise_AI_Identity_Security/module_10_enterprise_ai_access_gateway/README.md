# Module 10 — Enterprise AI Access Gateway Capstone

The capstone composes the Phase 12 services into one local, fictional enterprise
flow:

```text
User login (Keycloak)
  -> delegation gateway
  -> OPA policy decision
  -> agent identity and credential broker
  -> Redis task state
  -> protected MCP tool
  -> tenant-filtered fictional data
  -> structured audit event and OpenTelemetry trace
```

## Stack

| Component | Purpose |
|---|---|
| Keycloak | human OIDC login, fictional roles, and tenant claim |
| Spring Boot identity service | agent registry, RS256/JWKS, task token broker, revocation |
| PostgreSQL | durable agent registrations and identity metadata |
| Redis | short-lived task state and immediate task revocation |
| Spring Boot delegation gateway | user-to-agent on-behalf-of boundary |
| OPA | tenant, scope, and audience policy decision |
| Spring Boot MCP server | protected tools and server-side authorization |
| OpenTelemetry Collector | receives and redacts distributed trace data |
| Jaeger | default local trace viewer |
| Langfuse | optional AI/agent trace destination through OTLP |

All data and credentials are local fixtures. No component sends a real email,
approves a payment, or accesses a real invoice.

## Prerequisites

```bash
docker --version
docker compose version
curl --version
jq --version
```

The hostnames `keycloak.localhost`, `gateway.localhost`,
`identity.localhost`, and `mcp.localhost` use the reserved `.localhost` domain
and should resolve to the local machine. If your environment does not support
wildcard localhost resolution, follow the host-run fallback below.

## Run the capstone

```bash
cp .env.example .env
docker compose up --build
```

Wait until the services report healthy, then seed the fictional agents:

```bash
./demo/seed_agents.sh
```

The script prints Finance and Email agent IDs. It does not write tokens or
credentials to disk.

Open:

- Keycloak: `http://keycloak.localhost:8080`
- Delegation gateway: `http://gateway.localhost:8084/delegation/context`
- Identity JWKS: `http://identity.localhost:8081/.well-known/jwks.json`
- MCP protected-resource metadata: `http://mcp.localhost:8086/.well-known/oauth-protected-resource`
- OPA health: `http://localhost:8181/health`
- Jaeger: `http://localhost:16686`

Log in to Keycloak with:

```text
username: demo.user
password: demo-only-password
```

The fictional user can delegate `invoice.read` and `email.draft`, but not
`invoice.approve` or any send action.

## Demonstration checklist

1. Register separate Finance and Email agents with `seed_agents.sh`.
2. Log in as the fictional user through the delegation gateway.
3. Request an `invoice.read` task credential for the Finance agent with audience
   `http://mcp.localhost:8086/mcp`.
4. Initialize an MCP session and call `get_fictional_invoice` for
   `inv-acme-001`.
5. Try `inv-globex-001` with the same token and observe tenant denial.
6. Try `draft_fictional_email` with the Finance token and observe scope denial.
7. Revoke the task using `/task/revoke`; repeat the call and observe denial even
   before the JWT expires.
8. Inspect the OPA decision, MCP audit event, and correlated trace in Jaeger.
9. Repeat with the Email agent and confirm it can create only an
   `example.invalid` draft and can never send it.

## Direct broker smoke test

The browser login demonstrates user delegation. For automated infrastructure
smoke checks only, `demo/request_task_token.sh AGENT_ID invoice.read` calls the
broker with the local workload credential and prints a task token. It is not a
replacement for the user-delegation exercise.

## OPA policy

The policy in `policy/phase12.rego` requires:

- user tenant equals registered agent tenant
- audience equals the protected MCP resource
- at least one requested scope
- every requested scope is in the capstone allow-list

The gateway also maps Keycloak roles to scopes before calling OPA. OPA cannot
grant a scope that the user role mapping already removed.

Validate the policy independently:

```bash
docker run --rm \
  -v "$PWD/policy:/policy:ro" \
  "${OPA_IMAGE:-openpolicyagent/opa:1.7.1-static}" test /policy
```

Expected output includes `PASS: 3/3`.

## Langfuse

Jaeger is included so the capstone works without another large dependency
stack. To use an existing local or hosted Langfuse deployment, copy
`otel/collector-langfuse.yaml.example`, follow the current Langfuse OTLP
authentication instructions, and configure the collector with the resulting
endpoint and authorization header. Never commit Langfuse keys.

Langfuse is used for agent/LLM traces; security decisions remain in the
application audit stream and should also be exported to the organization's
approved security log platform.

## Host-run fallback

If container-to-`.localhost` routing is unavailable, start only infrastructure:

```bash
docker compose up postgres redis keycloak opa otel-collector jaeger
```

Run Modules 02, 04, and 06 from the host with their default localhost settings.
This retains the same security flow without Docker hostname translation.

## Teardown

```bash
docker compose down
```

To also remove the fictional database and Redis state:

```bash
docker compose down -v
```

The second command permanently removes only the capstone's named local Docker
volumes.

## Production gaps

This is production-shaped, not production-ready. A real deployment must add an
approved KMS/HSM signing-key lifecycle, workload identity or mTLS instead of
the learning-only service tokens, high availability, secret management,
rate-limiting, durable security-log export, network policies, database row-level
security, incident runbooks, and independent penetration testing.
