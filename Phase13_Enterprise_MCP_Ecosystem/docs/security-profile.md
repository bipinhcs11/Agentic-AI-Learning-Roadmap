# Enterprise MCP Security Profile — MVP

## Allowed profile

| Dimension | MVP rule |
|---|---|
| Users | internal test users only |
| Clients | pinned VS Code host only |
| Hosting | local or internal sandbox only |
| Servers | internally built and registered only |
| Capabilities | tools only |
| Operations | read-only only |
| Data | fictional internal engineering metadata |
| Agents | no autonomous execution |
| Human control | visible invocation with the host's confirmation controls |
| Backends | fictional CI adapter or separately approved sandbox API |

## Enforcement layers

“Read-only” is true only when every layer agrees:

```text
registry classification
  AND gateway allow policy
  AND server implementation
  AND backend API method allowlist
  AND backend read-only credential
  AND negative test evidence
```

MCP `readOnlyHint` and similar annotations describe behavior to clients. They do
not prove that the implementation is read-only and must not be treated as an
authorization decision.

## Required gateway checks

Before routing a call, the gateway must:

1. validate token signature, issuer, audience, expiry, and not-before time;
2. identify the approved client application separately from the user;
3. require an approved and non-expired registry snapshot;
4. allow only an active, internally hosted, tools-only server;
5. allow only an approved `READ` tool;
6. authorize the requested fictional application ID;
7. validate arguments against JSON Schema and reject unknown fields;
8. enforce string length, list cardinality, request size, timeout, and response
   size limits;
9. attach a new correlation ID and a short-lived target-server assertion; and
10. fail closed on ambiguous identity, policy, route, or classification state.

## Required server checks

The MCP server must:

- accept requests only from the gateway network and identity;
- validate the internal assertion's issuer, audience, expiry, tool, application
  scope, and trace ID;
- map tools to explicit GET-only backend operations;
- use its own read-only workload credential;
- parameterize backend requests and normalize application IDs;
- sanitize upstream errors and cap returned records;
- never expose configuration, environment variables, credentials, or raw
  pipeline logs; and
- log decision metadata only.

## Token rules

- Inbound tokens are audience-bound to the gateway.
- Gateway assertions are audience-bound to one MCP server and expire quickly.
- Backend tokens are audience-bound to the CI API.
- The gateway never passes the IDE/user token to the MCP server or CI API.
- Tokens never appear in URLs, tool arguments, logs, traces, or error messages.
- Local demo secrets are generated and ignored by Git.

The MCP authorization specification explicitly requires protected MCP servers to
validate tokens intended for themselves and prohibits token passthrough to
upstream APIs. See [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
and [security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices).

## Audit event

Minimum event shape:

```json
{
  "eventVersion": "1.0",
  "traceId": "mcp-example-001",
  "subjectRef": "sha256:fictional-user-ref",
  "clientId": "vscode-devassist",
  "serverId": "devassist.build-intelligence",
  "serverVersion": "0.1.0",
  "tool": "get_test_failures",
  "applicationRef": "APP-FICTION-001",
  "registryDigest": "sha256:example",
  "decision": "ALLOW",
  "reasonCode": "POLICY_MATCH",
  "durationMs": 84,
  "outcome": "SUCCESS",
  "timestamp": "2026-07-31T13:24:00-05:00"
}
```

Do not record prompts, source code, tool inputs, tool outputs, stack traces,
tokens, employee IDs, or CI credentials. If protected diagnostics become
necessary later, design a separate access-controlled workflow with explicit
retention.

## Threats and controls

| Threat | MVP control | Required negative evidence |
|---|---|---|
| Unapproved server | gateway-only URL and private server network | direct connection fails |
| Unapproved tool | registry-derived allowlist | unknown tool is denied |
| Repository/application overreach | application scope in policy and server assertion | other app is denied |
| Confused deputy/token passthrough | separate audiences and credentials | CI adapter never sees user token |
| Schema smuggling | JSON Schema and `additionalProperties: false` | unknown field is denied |
| Oversized or slow response | record, byte, and timeout caps | timeout and oversize paths fail safely |
| Secret leakage in logs | metadata allowlist | scan test finds no sensitive fixture values |
| Stale approval | snapshot age and emergency denylist | disabled server fails closed |
| DNS rebinding/local exposure | Origin validation and localhost binding | invalid Origin is denied |

The Streamable HTTP specification requires Origin validation and recommends
localhost-only binding for local servers. See [MCP transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

## Stop conditions

Do not present the MVP as successful if any of these is true:

- the client can reach the MCP server directly;
- a user token is forwarded downstream;
- an unknown or write-classified tool executes;
- application-level authorization is absent;
- tool inputs or results appear in default logs;
- registry disablement does not stop new calls;
- the chosen IDE requires bypassing the intended identity or gateway boundary;
- the demo requires real customer, account, portfolio, employee, or source-code
  data.

## Future domain controls

- Oracle and PostgreSQL servers use named query templates, schema-limited
  read-only roles, timeouts, row/byte caps, and private network placement. A
  generic SQL tool is prohibited.
- API-backed tools use fixed destinations, methods, and operation templates;
  arbitrary URLs, redirects, credentials in arguments, and caller-supplied
  headers are prohibited.
- Sonar, coding-standards, and security-review servers expose only inventoried
  read tools. Source code and snippets require a separate data-classification,
  retention, model-boundary, and DLP decision.
- Agent-to-agent calls use a separate A2A Gateway/Broker, audience-bound target
  credentials, monotonic scope reduction, depth/fan-out/budget limits, loop
  detection, cancellation, kill switch, and an auditable delegation chain.

See the [Architecture Requirements Document](architecture-requirements-document.md)
for the full target-state controls.
