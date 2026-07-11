---
description: "Security rules applied to all source code, any language"
applyTo: "**/*.{java,kt,ts,tsx,js,jsx,py,swift,m,go,cs,rb}"
---

# Security instructions (all source files)

- Validate and constrain ALL external input at the boundary — request bodies, headers,
  query params, file uploads, message payloads. Reject early with a typed error.
- Authorization is checked at the resource level, not just the endpoint level:
  a user being logged in never implies they may see this record.
- Never log credentials, tokens, session ids, PII, or full request bodies.
  Log identifiers, not payloads.
- Secrets come from the environment or the approved secret store — never from code,
  test fixtures, or comments. If a secret-looking literal exists, flag it.
- Use parameterized queries / prepared statements exclusively. String-built SQL,
  NoSQL filters, or shell commands from user input are always a finding.
- Error responses expose no stack traces, no framework versions, no internal paths.
- New cryptography uses the platform's vetted library at current defaults —
  never hand-rolled primitives, MD5/SHA-1, or ECB mode.
- Any use of `eval`, dynamic code loading, reflection on user input, or deserialization
  of untrusted data must be explicitly justified in a comment and flagged in the PR.
- When generating anything auth-adjacent (login, password reset, token refresh,
  session handling), state the relevant OWASP ASVS section being satisfied.
