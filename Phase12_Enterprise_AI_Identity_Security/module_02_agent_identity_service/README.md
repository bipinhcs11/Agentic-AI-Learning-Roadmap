# Module 02 — Build an Agent Identity Service

This Spring Boot service registers fictional AI agents and issues signed access
tokens containing owner, tenant, scope, audience, expiry, and audit context.

> This project makes identity internals visible for learning. In production,
> use an approved identity provider, protected administration APIs, durable key
> management, rotation, rate limits, and formal security review.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/agent/register` | register an agent, owner, tenant, and maximum scopes |
| `GET` | `/agent/{id}` | read non-secret registration metadata |
| `GET` | `/agent/{id}/status` | resource-server revocation/status check |
| `POST` | `/agent/token` | issue an agent credential for an allowed audience and scopes |
| `POST` | `/agent/task-token` | issue a credential bound to a task, actor, and max 10-minute TTL |
| `POST` | `/agent/revoke` | disable an agent and stop future issuance |
| `GET` | `/task/{taskId}/status?agentId=...` | check short-lived task state |
| `POST` | `/task/revoke` | immediately revoke one task context |
| `GET` | `/.well-known/jwks.json` | publish the current public signing key |

## Run

```bash
mvn spring-boot:run
```

Register an agent:

```bash
curl -s http://localhost:8081/agent/register \
  -H 'X-Identity-Token: local-admin-only' \
  -H 'Content-Type: application/json' \
  -d '{
    "displayName":"Finance Assistant",
    "ownerId":"user-101",
    "tenantId":"fictional-acme",
    "scopes":["invoice.read","invoice.list"]
  }'
```

Copy the returned `id`, then request a task token:

```bash
curl -s http://localhost:8081/agent/task-token \
  -H 'X-Identity-Token: local-broker-only' \
  -H 'Content-Type: application/json' \
  -d '{
    "agentId":"REPLACE_WITH_ID",
    "taskId":"task-demo-001",
    "actorId":"user-101",
    "requestedScopes":["invoice.read"],
    "audience":"fictional-invoice-api",
    "ttlSeconds":600,
    "delegationDepth":0
  }'
```

Expected response shape:

```json
{
  "tokenType": "Bearer",
  "accessToken": "eyJraWQiOi...",
  "expiresIn": 600,
  "scope": "invoice.read",
  "auditId": "..."
}
```

The local key pair is generated at startup, so tokens from a previous process
become invalid after restart. That is useful for the lab but intentionally not
a production key-management strategy.

Task state uses an in-memory store by default. Set `IDENTITY_REDIS_ENABLED=true`
and `REDIS_HOST` to use Redis, as the capstone does. Reusing an active `taskId`
returns `409` to prevent one task identifier from being rebound silently.

The local defaults use separate learning-only credentials for administration,
token brokerage, and status checks: `local-admin-only`, `local-broker-only`, and
`local-status-only`. Override all three in Docker. Production systems should
replace these shared tokens with authenticated workload identities and mTLS.

## Test

```bash
mvn test
```

Tests cover token claims, overbroad scopes, TTL limits, and revoked agents.
