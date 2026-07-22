# Module 01 — AI Identity Fundamentals

This module establishes a vocabulary before any agent receives a credential.

## Identity types

| Identity | Represents | Typical authenticator | Important distinction |
|---|---|---|---|
| Human | a person | passkey, MFA, OIDC session | can provide intent and consent |
| Service | an application integration | client assertion or managed secret | usually stable and deterministic |
| Workload | a running software workload | attested short-lived certificate/token | bound to runtime properties |
| Managed | a cloud-managed workload principal | platform metadata/federation | avoids exported private keys |
| Agent | a governed AI actor | agent/workload token plus metadata | needs owner, purpose, and lifecycle |

An agent identity does not replace its workload identity. The agent identifies
the governed actor; the workload identity proves which deployed process is
making the request.

## Protocol map

- OAuth defines delegated authorization flows and access tokens.
- OpenID Connect adds authentication and ID tokens on top of OAuth.
- JWT is a token format, not an authentication or authorization policy.
- SPIFFE defines portable workload identities and short-lived SVIDs.
- SPIRE is an implementation that attests workloads and issues SPIFFE identities.

## Run the claims lab

```bash
python3 claims_lab.py
python3 -m unittest -q
```

Expected output:

```text
Identity: agent:finance-assistant
Audience: fictional-invoice-api
Scopes: invoice.read
Tenant: fictional-acme
Decision: ALLOW
Negative check: DENY (audience mismatch)
```

The lab intentionally uses an unsigned, local fixture so it can explain claim
semantics with the Python standard library. It never treats the decoded payload
as authenticated. Cryptographic signing and validation begin in Module 02.
