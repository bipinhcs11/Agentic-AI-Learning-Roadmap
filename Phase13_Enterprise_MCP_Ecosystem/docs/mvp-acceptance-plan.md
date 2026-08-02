# MVP Acceptance Plan

## Evidence policy

All tests use fictional identities and diagnostic records. Evidence may contain
trace IDs, status, reason codes, timing, server/tool identifiers, and a registry
digest. It must not contain prompts, tool arguments/results, tokens, secrets,
source code, personal data, or real enterprise identifiers.

## Functional acceptance

| ID | Scenario | Expected result |
|---|---|---|
| F-01 | client initializes through the gateway | tools capability is available |
| F-02 | client requests `tools/list` | exactly `work_item_analyze` and `config_check` |
| F-03 | approved call for `WI-DEMO-001` | missing enrollment evidence and `config_check` recommendation |
| F-04 | approved call for `P-DEMO-001` | `MISSING_ENROLLMENT_CONFIGURATION` |
| F-05 | each server calls its fixed read-only APIs | new backend token for each API operation |
| F-06 | trace is reviewed | one trace ID correlates the full request path |
| F-07 | registry entry is disabled or expired | discovery/call fails closed after snapshot reload |

## Required denials

| ID | Attempt | Expected outcome |
|---|---|---|
| D-01 | missing gateway token | HTTP 401 and protected-resource metadata pointer |
| D-02 | expired token or wrong audience | HTTP 401 with sanitized error |
| D-03 | unapproved client | HTTP 401 with sanitized error |
| D-04 | missing `mcp.diagnostic.read` role | policy denial |
| D-05 | resource outside the two fictional allowlists | policy denial |
| D-06 | unregistered tool or server | registry/policy denial |
| D-07 | unknown or malformed argument | schema validation error before proxying |
| D-08 | direct call to an MCP server | gateway assertion required |
| D-09 | assertion used for another server/tool | invalid gateway assertion |
| D-10 | slow or oversized upstream response | bounded sanitized error |
| D-11 | invalid Host or Origin | request rejected by transport protection |
| D-12 | backend token replay | rejected by the fictional fixture |

## Automated evidence

Run:

```bash
uv sync --locked --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
docker compose config --quiet
```

CI runs the same checks using `uv.lock`. Tests cover configuration fail-closed
rules, JWT validation, gateway authentication middleware, registry enforcement,
manifest-bound schemas, role/resource policy, per-server assertions, fixed API
calls, response limits, token non-reuse, and sensitive-log suppression.

## Manual demonstration

1. Show the two registry manifests and snapshot digest.
2. Connect the client only to the gateway URL.
3. Show that only two tools are discoverable.
4. Run the Work Item Analysis call for `WI-DEMO-001`.
5. Run Config Check for the returned fictional participant.
6. Show the diagnosis and correlated metadata-only events.
7. Attempt an unapproved ID and a direct MCP-server call; show both denials.
8. State which enterprise identity, secret, network, and telemetry integrations
   remain unproven.

## Decision rule

Proceed to an enterprise integration test only when the functional path and
mandatory denials pass, the logs contain no sensitive payloads, and architecture
and security reviewers accept the residual risks. The next test should connect
this same two-server flow to approved non-production identity, secret, API
gateway, and telemetry services. It must not add another business capability.
