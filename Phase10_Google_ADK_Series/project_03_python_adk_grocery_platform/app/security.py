"""Local security primitives for the grocery ADK learning module.

These helpers intentionally simulate enterprise controls without contacting
real identity providers, payment processors, or policy services.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

SHARED_DEMO_SECRET = "local-learning-only-secret"

RiskLevel = Literal["low", "medium", "high", "blocked"]


@dataclass(frozen=True)
class AgentIdentity:
    """SPIFFE-style identity used to teach A2A spoofing defenses."""

    agent_id: str
    audience: str
    trust_domain: str = "local.grocery.example"

    @property
    def spiffe_id(self) -> str:
        return f"spiffe://{self.trust_domain}/{self.agent_id}"


@dataclass
class TrustLedger:
    """Tracks trust decay and circuit-breaker state for one agent."""

    agent_id: str
    trust_score: int = 100
    violations: list[str] = field(default_factory=list)

    def record_violation(self, reason: str, severity: int) -> None:
        self.trust_score = max(0, self.trust_score - severity)
        self.violations.append(reason)

    @property
    def circuit_open(self) -> bool:
        return self.trust_score < 65 or len(self.violations) >= 3


TRUSTED_AGENTS: dict[str, AgentIdentity] = {
    "grocery-concierge": AgentIdentity(
        agent_id="grocery-concierge",
        audience="grocery-platform",
    ),
    "delivery-scheduler": AgentIdentity(
        agent_id="delivery-scheduler",
        audience="grocery-platform",
    ),
}

TRUST_LEDGERS: dict[str, TrustLedger] = {
    agent_id: TrustLedger(agent_id=agent_id) for agent_id in TRUSTED_AGENTS
}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sign(payload: dict[str, Any], secret: str = SHARED_DEMO_SECRET) -> str:
    message = _canonical_json(payload).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def mint_agent_assertion(agent_id: str, audience: str, ttl_seconds: int) -> dict[str, Any]:
    """Mint a signed local assertion for trusted demo agents.

    Args:
        agent_id: Registered agent id.
        audience: Intended recipient audience.
        ttl_seconds: Assertion lifetime in seconds.

    Returns:
        Signed assertion containing a SPIFFE-style subject and expiry.
    """
    identity = TRUSTED_AGENTS.get(agent_id)
    if identity is None:
        return {"status": "denied", "reason": "unknown_agent"}

    payload = {
        "agent_id": identity.agent_id,
        "audience": audience,
        "spiffe_id": identity.spiffe_id,
        "expires_at": int(time.time()) + ttl_seconds,
        "nonce": str(uuid.uuid4()),
    }
    return {"status": "issued", "assertion": payload | {"signature": _sign(payload)}}


def verify_agent_assertion(assertion: dict[str, Any], expected_audience: str) -> dict[str, Any]:
    """Verify a signed agent assertion and detect spoofed identities."""
    signature = assertion.get("signature")
    payload = {key: value for key, value in assertion.items() if key != "signature"}
    agent_id = payload.get("agent_id", "unknown")
    ledger = TRUST_LEDGERS.setdefault(agent_id, TrustLedger(agent_id=agent_id))

    trusted = TRUSTED_AGENTS.get(agent_id)
    if trusted is None:
        ledger.record_violation("unknown agent identity", severity=20)
        return {"status": "denied", "reason": "unknown_agent", "trust_score": ledger.trust_score}
    if payload.get("spiffe_id") != trusted.spiffe_id:
        ledger.record_violation("spiffe subject mismatch", severity=30)
        return {"status": "denied", "reason": "spoofed_spiffe_id", "trust_score": ledger.trust_score}
    if payload.get("audience") != expected_audience:
        ledger.record_violation("audience mismatch", severity=20)
        return {"status": "denied", "reason": "audience_mismatch", "trust_score": ledger.trust_score}
    if int(payload.get("expires_at", 0)) < int(time.time()):
        ledger.record_violation("expired assertion", severity=15)
        return {"status": "denied", "reason": "expired_assertion", "trust_score": ledger.trust_score}
    if not hmac.compare_digest(str(signature), _sign(payload)):
        ledger.record_violation("signature mismatch", severity=30)
        return {"status": "denied", "reason": "bad_signature", "trust_score": ledger.trust_score}
    if ledger.circuit_open:
        return {"status": "denied", "reason": "circuit_breaker_open", "trust_score": ledger.trust_score}
    return {
        "status": "trusted",
        "agent_id": agent_id,
        "spiffe_id": trusted.spiffe_id,
        "trust_score": ledger.trust_score,
    }


def issue_jit_token(agent_id: str, action: str, resource: str, ttl_seconds: int) -> dict[str, Any]:
    """Issue a just-in-time, downscoped token for one action/resource pair."""
    if agent_id not in TRUSTED_AGENTS:
        return {"status": "denied", "reason": "unknown_agent"}
    token_payload = {
        "token_id": f"jit_{uuid.uuid4().hex[:12]}",
        "agent_id": agent_id,
        "allowed_action": action,
        "resource": resource,
        "expires_at": int(time.time()) + ttl_seconds,
    }
    return {"status": "issued", "token": token_payload | {"signature": _sign(token_payload)}}


def verify_jit_token(token: dict[str, Any], action: str, resource: str) -> dict[str, Any]:
    """Verify that a JIT token is valid for exactly this operation."""
    signature = token.get("signature")
    payload = {key: value for key, value in token.items() if key != "signature"}
    if not hmac.compare_digest(str(signature), _sign(payload)):
        return {"status": "denied", "reason": "bad_signature"}
    if int(payload.get("expires_at", 0)) < int(time.time()):
        return {"status": "denied", "reason": "expired_token"}
    if payload.get("allowed_action") != action:
        return {"status": "denied", "reason": "action_scope_mismatch"}
    if payload.get("resource") != resource:
        return {"status": "denied", "reason": "resource_scope_mismatch"}
    return {"status": "authorized", "token_id": payload["token_id"]}


def hybrid_policy_gate(action: str, amount: float, cart_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply structural and semantic policy checks before risky actions."""
    reasons: list[str] = []
    item_names = " ".join(item.get("name", "") for item in cart_items).lower()

    if action == "checkout" and amount > 150:
        reasons.append("checkout total exceeds local demo limit")
    if any(term in item_names for term in ("alcohol", "medicine", "gift card")):
        reasons.append("restricted grocery category requires stronger review")
    if amount <= 0:
        reasons.append("checkout amount must be positive")

    if reasons:
        return {
            "decision": "manual_review",
            "risk_level": "high",
            "reasons": reasons,
            "semantic_gate": "simulated_semantic_policy_review",
        }
    return {
        "decision": "allow",
        "risk_level": "low",
        "reasons": [],
        "semantic_gate": "simulated_semantic_policy_review",
    }


def build_vibe_diff(cart_items: list[dict[str, Any]], total: float, delivery_window: str) -> dict[str, Any]:
    """Create a plain-English approval summary before checkout."""
    names = ", ".join(f"{item['quantity']} x {item['name']}" for item in cart_items)
    return {
        "summary": (
            f"Approve a grocery order containing {names}. "
            f"The demo total is ${total:.2f}, scheduled for {delivery_window}."
        ),
        "high_stakes_action": "place_order_and_create_payment_mandate",
        "requires_human_approval": True,
    }


def build_agbom() -> dict[str, Any]:
    """Return a compact Agent Bill of Materials for the module."""
    return {
        "name": "phase10-module03-grocery-platform",
        "agents": [
            "grocery-concierge",
            "catalog-specialist",
            "checkout-security-specialist",
            "delivery-scheduler",
        ],
        "controls": [
            "signed_agent_identity",
            "jit_downscoped_tokens",
            "hybrid_policy_gate",
            "vibe_diff_hitl",
            "trust_decay_circuit_breaker",
            "ap2_payment_mandate_simulation",
            "ucp_checkout_lane",
            "a2ui_payloads",
        ],
        "data_classification": "fictional educational grocery data only",
    }
