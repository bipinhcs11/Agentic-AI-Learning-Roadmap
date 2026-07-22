"""Inspect a fictional JWT payload and apply resource-server claim checks.

The fixture is not signed. Decoding is not verification; this lab only teaches
the meaning of claims before Module 02 introduces signed tokens.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def decode_payload(encoded_payload: str) -> dict[str, object]:
    padding = "=" * (-len(encoded_payload) % 4)
    decoded = base64.urlsafe_b64decode(encoded_payload + padding)
    return json.loads(decoded)


def encode_fixture(claims: dict[str, object]) -> str:
    payload = json.dumps(claims, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def authorize(
    claims: dict[str, object], *, audience: str, scope: str, tenant: str
) -> Decision:
    audiences = claims.get("aud", [])
    if isinstance(audiences, str):
        audiences = [audiences]
    if audience not in audiences:
        return Decision(False, "audience mismatch")

    scopes = str(claims.get("scope", "")).split()
    if scope not in scopes:
        return Decision(False, "missing scope")
    if claims.get("tenant_id") != tenant:
        return Decision(False, "tenant mismatch")
    return Decision(True, "claims satisfy the illustrative policy")


def main() -> None:
    fixture = {
        "sub": "agent:finance-assistant",
        "aud": "fictional-invoice-api",
        "scope": "invoice.read",
        "tenant_id": "fictional-acme",
    }
    claims = decode_payload(encode_fixture(fixture))
    decision = authorize(
        claims,
        audience="fictional-invoice-api",
        scope="invoice.read",
        tenant="fictional-acme",
    )
    negative = authorize(
        claims,
        audience="fictional-email-api",
        scope="invoice.read",
        tenant="fictional-acme",
    )

    print(f"Identity: {claims['sub']}")
    print(f"Audience: {claims['aud']}")
    print(f"Scopes: {claims['scope']}")
    print(f"Tenant: {claims['tenant_id']}")
    print(f"Decision: {'ALLOW' if decision.allowed else 'DENY'}")
    print(f"Negative check: {'ALLOW' if negative.allowed else 'DENY'} ({negative.reason})")


if __name__ == "__main__":
    main()
