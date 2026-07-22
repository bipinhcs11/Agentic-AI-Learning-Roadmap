# Module 04 — User Delegation

This module separates the authenticated user from the agent acting for that
user. Keycloak authenticates the fictional user with Authorization Code + PKCE;
the gateway maps approved user roles to delegable scopes and requests a narrow
task token from Module 02.

The gateway never receives or stores the user's password.

## Start Keycloak

```bash
docker compose up -d
```

The imported `phase12` realm contains one fictional learning account:

```text
username: demo.user
password: demo-only-password
roles: invoice-reader, email-drafter
tenant: fictional-acme
```

These credentials are deliberately local and fictional. Do not reuse this
configuration or password outside the lab.

## Run the delegation gateway

Start Module 02 on port `8081`, then:

```bash
mvn spring-boot:run
```

Open `http://localhost:8084/delegation/context`. Spring redirects to Keycloak.
After login, the endpoint shows the user subject and scopes that policy permits
the user to delegate.

Register the target agent in Module 02 with the same scopes and send:

```bash
curl -s -X POST http://localhost:8084/delegation/request \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{
    "agentId":"REPLACE_WITH_ID",
    "taskId":"task-user-delegation-001",
    "requestedScopes":["invoice.read"],
    "audience":"fictional-invoice-api"
  }'
```

For an interactive curl session, first complete the browser login and export
its session cookie. Using the browser or an API client with OAuth support is
usually simpler than manually reconstructing Authorization Code + PKCE.

Requesting `invoice.approve` returns `403`: neither the user role mapping nor the
agent allow-list grants it.

## Security boundary

This focused module demonstrates user login and scope attenuation. The capstone
also authenticates the gateway workload and makes the credential broker verify
the incoming user access token before issuing a task token.

## Test

```bash
mvn test
```
