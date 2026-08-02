# Enterprise MCP Security Profile — POC

## Allowed profile

| Dimension | POC rule |
|---|---|
| users | fictional internal test identity only |
| clients | approved VS Code or JetBrains client ID |
| hosting | local or internal non-production runtime |
| servers | Work Item Analysis and Config Check only |
| capabilities | tools only |
| operations | fixed read-only API calls |
| data | two allowlisted fictional identifiers |
| agents | none |
| external exposure | MCP gateway only |

## Enforcement chain

“Read-only” is accepted only when the registry classification, gateway policy,
server implementation, fixed GET operation, backend API scope, and negative
tests agree. MCP annotations are descriptive and are not authorization.

### Gateway checks

Before a call reaches a scenario server, the gateway:

1. validates JWT signature, issuer, audience, time, and required claims;
2. verifies the client ID is approved globally and for the target server;
3. requires `mcp.diagnostic.read`;
4. resolves an active, unexpired manifest and exact registered tool;
5. validates arguments against the manifest JSON Schema;
6. authorizes `WI-DEMO-001` or `P-DEMO-001` as appropriate;
7. enforces the registered timeout and response size;
8. creates a short-lived assertion signed with that scenario's key; and
9. emits an allow or deny event with a registry digest and hashed subject and
   resource references.

### Scenario-server checks

Each server:

- accepts the gateway assertion only for its own audience, scenario, and tool;
- has a separate assertion secret, Vault path, API client, and API scope;
- exposes one tool and fixed read-only paths;
- obtains a backend token before each API operation by default;
- streams and caps the backend response before JSON parsing;
- rejects redirects and uses bounded timeouts; and
- returns sanitized errors without credentials or upstream bodies.

The local fixture also rejects a second use of the same backend token ID.

## Audit event policy

Events may contain:

- trace/span IDs;
- service, operation, server, version, and tool;
- approved client ID;
- hashed subject and resource references;
- registry digest, decision, reason, outcome, duration, and timestamp.

Events must not contain prompts, tool arguments/results, API payloads, source
code, personal identifiers, tokens, secrets, authorization headers, Vault
responses, or stack traces. Default `httpx`, `httpcore`, and access logging is
suppressed to avoid recording request paths that include fictional business IDs.

## Threats and POC controls

| Threat | Control | Evidence |
|---|---|---|
| unapproved client/server/tool | JWT client allowlist and manifest policy | negative tests |
| direct server access | unpublished port plus required gateway assertion | middleware/Compose tests |
| confused deputy | separate audiences and no inbound-token forwarding | token flow tests |
| assertion blast radius | separate scenario secrets and tool binding | wrong-tool/key denial |
| resource overreach | gateway allowlists | unapproved-ID denial |
| schema smuggling | advertised and enforced manifest schema | unknown-field denial |
| DNS rebinding | exact Host/Origin transport protection | configuration test |
| slow/oversized upstream | timeout and streaming byte cap | API client tests |
| credential leakage | environment/Vault adapter and safe logs | log scan tests |
| stale approval | startup snapshot validation and lifecycle checks | registry tests |

## POC limits requiring a later decision

- Local HS256 identity and assertion keys are demonstration mechanisms. A shared
  enterprise environment should use its approved IdP/JWKS and decide whether
  server assertions move to asymmetric workload identity.
- The registry snapshot is loaded at process startup. Signed publication,
  bounded staleness, hot reload, and emergency revocation are production-pilot
  work.
- The included Vault adapter uses AWS IAM. An Azure deployment must approve how
  Container Apps authenticate to Vault or replace the adapter with Azure Key
  Vault/managed identity.
- JSON audit output proves the event contract, not SIEM integration, retention,
  alerting, or operational ownership.
- Network isolation is represented by Docker Compose. Cloud network policies,
  certificates, private DNS, rate limits, circuit breakers, and availability
  require environment-specific implementation.

## Stop conditions

Do not connect real data or present the POC as production-ready if the client
can bypass the gateway, a developer token reaches a downstream service, an
unknown resource/tool/field executes, server credentials are shared, sensitive
payloads appear in logs, or a clear deny decision cannot be reconstructed from
the trace.
