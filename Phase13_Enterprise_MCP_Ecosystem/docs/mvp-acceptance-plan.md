# MVP Acceptance Plan

## Evidence policy

All tests use fictional identities, applications, builds, and failures. Evidence
contains trace IDs, status codes, policy reason codes, timing, and registry
digests—not prompts, arguments, results, credentials, source code, or real
enterprise identifiers.

## Mandatory functional scenarios

| ID | Scenario | Expected result |
|---|---|---|
| F-01 | VS Code initializes through the gateway | negotiated tools capability; no other server capability |
| F-02 | VS Code requests `tools/list` | exactly three registry-approved tools |
| F-03 | allowed user calls `get_build_status` for `APP-FICTION-001` | deterministic successful result and trace ID |
| F-04 | allowed user calls `get_test_failures` | at most 20 sanitized fictional failures |
| F-05 | allowed user calls `get_application_owner` | fictional team and support alias |
| F-06 | server becomes disabled in approved snapshot | subsequent discovery/calls fail closed |
| F-07 | upstream exceeds timeout | bounded sanitized tool error; no retry storm |

## Mandatory authorization and schema denials

| ID | Attempt | Expected reason |
|---|---|---|
| D-01 | missing token | `AUTHENTICATION_REQUIRED` |
| D-02 | expired token | `TOKEN_EXPIRED` |
| D-03 | wrong audience | `INVALID_AUDIENCE` |
| D-04 | unapproved client ID | `CLIENT_NOT_APPROVED` |
| D-05 | unknown tool | `TOOL_NOT_APPROVED` |
| D-06 | write-classified manifest/tool | `OPERATION_NOT_ALLOWED` |
| D-07 | other application ID | `APPLICATION_NOT_AUTHORIZED` |
| D-08 | unknown argument | `SCHEMA_VALIDATION_FAILED` |
| D-09 | oversized application ID or request | `REQUEST_LIMIT_EXCEEDED` |
| D-10 | stale registry snapshot | `REGISTRY_SNAPSHOT_EXPIRED` |
| D-11 | direct client-to-server call | connection or server identity rejection |
| D-12 | invalid Origin header | HTTP 403 |

## Protocol checks

- initialization uses the pinned MCP protocol version;
- only `tools` is declared by the server/gateway profile;
- `tools/list` pagination behavior is deterministic for the small catalog;
- JSON-RPC request IDs and errors are preserved correctly;
- tool input validation errors are returned in the form expected by the pinned
  MCP client/SDK;
- response content type works with the selected VS Code host;
- stateless or session behavior is recorded in the compatibility matrix;
- an unsupported method fails clearly rather than being routed as a tool.

## Security checks

- inbound user token is absent from gateway-to-server and server-to-CI calls;
- gateway assertion cannot be replayed against another server or tool;
- CI credential cannot call a write endpoint;
- log scan finds no token, fictional secret canary, prompt, tool arguments, or
  tool result;
- invalid snapshot digest is rejected;
- emergency denylist overrides the last-known-good snapshot;
- response cap prevents unbounded pipeline log retrieval;
- upstream error body and infrastructure URL are not returned to the client.

## Performance sanity targets

These are engineering guardrails, not service-level objectives:

| Measure | Sandbox target |
|---|---:|
| Gateway policy and routing overhead, p95 | under 100 ms excluding upstream |
| Successful fictional tool call, p95 | under 2 seconds |
| Hard upstream timeout | 5 seconds |
| Tool result cap | 256 KiB and 20 records |
| Concurrent demo calls | 10 without errors |

If the sandbox misses a target, capture the measurement and cause. Do not tune a
five-day MVP into an unmeasured production SLA.

## Demo script

1. Show the registry manifest and its digest.
2. Connect VS Code to the gateway URL.
3. Show that only three tools are discoverable.
4. Ask why `APP-FICTION-001` failed and allow the visible tool call.
5. Open the correlated metadata-only audit event.
6. attempt `delete_build` and show `TOOL_NOT_APPROVED`.
7. attempt the same read for `APP-RESTRICTED-999` and show
   `APPLICATION_NOT_AUTHORIZED`.
8. disable the server in the registry snapshot and show new calls fail closed.
9. State the unproven enterprise dependencies and the next decision.

## Go/no-go decision

**Go to pilot discovery** only when every mandatory functional, denial,
protocol, and security check passes and the security reviewer accepts the
recorded residual risks.

**Extend the sandbox** when the core controls work but IDE compatibility,
enterprise IdP, or CI sandbox integration remains unproven.

**Stop** when gateway-only routing, separate credential boundaries,
application-level authorization, read-only enforcement, or metadata-only audit
cannot be demonstrated.
