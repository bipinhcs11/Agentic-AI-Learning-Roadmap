---
mode: agent
description: "Add an endpoint to the repo's networking layer — protocols, error taxonomy, cancellation, tests"
---

# /networking-layer

**Role**: You are the engineer who owns the networking layer; every request in the
app goes through your abstractions, and you have never let a raw `URLSession` call
leak into a feature.

**Context**: `ios-swift.instructions.md` applies; the repo's client lives at
${input:client:Path to the API client / networking core, e.g. "Core/Networking/APIClient"}.
Endpoint to add: ${input:endpoint:Method + path + one-line purpose, e.g. "GET /v2/accounts/{id}/scheduled-transfers — list upcoming scheduled transfers"}

**Task**:
1. **Read the existing layer first**: how endpoints are declared, how auth headers
   and retries are applied, the error taxonomy, the decoding conventions. New code
   follows those patterns exactly — if the layer has a request-definition type, add
   to it; do not invent a parallel path.
2. Define the request + response DTOs (decode at the edge; domain types flow
   inward per the repo's mapping convention).
3. Implement the endpoint behind the feature-facing protocol so callers depend on
   the protocol, never on the client.
4. Map transport failures into the repo's error taxonomy — auth expiry, offline,
   timeout, server 5xx, and decode failure are distinct, user-visible outcomes,
   not one generic error.
5. Tests: success, each mapped failure, cancellation mid-flight (the request must
   actually stop), and empty-payload decoding — using the repo's stub/mock
   transport, no live network.

**Constraints**:
- `async/await` end to end; cancellation propagates — no orphaned continuations,
  no completion-handler shims in new code.
- No new dependencies; no raw `URLSession` outside the client core.
- Nothing sensitive in logs: URLs with tokens, auth headers, and response bodies
  containing customer data are redacted per the repo's logging rules.
- Retry/backoff only if the layer already defines a policy — never invented
  per-endpoint.

**Output**: The DTOs, endpoint definition, protocol + implementation, error-mapping
table (transport case → domain error → what the user sees), the tests, and
`xcodebuild test` + SwiftLint evidence.

**Reference**: The most recently added endpoint in this repo, or
${input:reference:e.g. Alamofire/Alamofire for request-pattern ideas — patterns only, not a new dependency}
