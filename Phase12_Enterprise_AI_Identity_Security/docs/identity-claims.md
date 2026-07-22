# Identity and Task Credential Claims

## Example task token

```json
{
  "iss": "http://localhost:8081",
  "sub": "agent:finance-assistant",
  "aud": "fictional-invoice-api",
  "scope": "invoice.read",
  "tenant_id": "fictional-acme",
  "owner_id": "user-101",
  "task_id": "task-789",
  "actor_id": "agent:planner",
  "delegation_depth": 1,
  "audit_id": "audit-456",
  "jti": "token-123",
  "iat": 1784500000,
  "nbf": 1784500000,
  "exp": 1784500600
}
```

## Validation checklist

Resource servers must validate all applicable properties before using claims:

1. The algorithm is explicitly allowed; never accept `alg=none`.
2. The signature resolves to a trusted issuer key.
3. `iss` exactly matches the configured issuer.
4. The resource server appears in `aud`.
5. `nbf` and `exp` contain the current time, with small bounded clock skew.
6. Required scopes exist and the tool is on the agent allow-list.
7. `tenant_id` matches the requested resource and database predicate.
8. `task_id` is active and not exhausted or revoked.
9. The agent is active and delegation depth is within policy.
10. `jti` has not been revoked or replayed where single-use is required.

## ID tokens versus access tokens

An ID token tells a client about an authentication event. It is not a general
API credential. The examples use access tokens minted for a named audience.
Passing a user ID token to an MCP server is deliberately treated as an error.

## JWT revocation limitation

JWTs are normally valid until expiry. Phase 12 demonstrates three complementary
controls: short lifetimes, an agent/task status check, and a Redis deny-list for
urgent revocation. This adds a stateful lookup by design.
