# Threat Model

## Assets

- agent registrations, owners, and tenant assignments
- signing keys and identity-provider configuration
- task grants and delegation chains
- MCP tools and fictional tenant records
- policy decisions, audit events, and traces

## Primary threats and controls

| Threat | Control taught in this phase |
|---|---|
| Stolen long-lived secret | workload federation and short-lived credentials |
| Over-privileged general agent | task and audience-scoped tokens |
| Permission amplification in a handoff | monotonic attenuation and delegation-depth policy |
| Confused deputy | explicit actor, task, resource audience, and policy context |
| Cross-tenant access | token tenant check plus tenant-filtered database query |
| JWT replay | short TTL, unique `jti`, optional one-use state, Redis deny-list |
| Revoked agent continuing to act | agent status and task-status introspection |
| Prompt injection selecting a dangerous tool | server-side tool allow-list and policy decision |
| Forged or malformed token | pinned issuer, algorithms, audience, time, and JWKS validation |
| Audit log leakage | redact authorization headers, secrets, prompts, and sensitive payloads |
| Signing-key compromise | documented rotation and emergency deny/reissue procedure |
| SSRF against identity endpoints | fixed allow-listed issuer/JWKS locations and network controls |

## Explicit non-goals

These educational projects do not provide hardware-backed keys, production key
ceremonies, high-availability identity infrastructure, certified compliance, or
complete prompt-injection prevention. Production adoption requires a formal
security review and the organization's approved identity platform.
