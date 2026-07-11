# ═══════════════════════════════════════════════════════════════════════════
# a2ui.py — trusted A2UI component catalog + server-side validation
# ───────────────────────────────────────────────────────────────────────────
# The plan's rule: "A2UI server-side validation is mandatory — validate the
# model's A2UI JSON against the trusted catalog before sending." The browser must
# only ever render components it already knows how to render; anything else is a
# vector (a model could emit a <script> component, an off-catalog widget, etc.).
#
# So every A2UI payload leaving the server passes validate_a2ui() first:
#   • the component name must be in TRUSTED_COMPONENTS, and
#   • all of that component's required props must be present.
#
# The React renderer holds the *same* catalog and refuses unknown components — a
# second, independent gate. Data stays fictional grocery data.
# ═══════════════════════════════════════════════════════════════════════════

from __future__ import annotations

from typing import Any

from app.grocery import build_a2ui_catalog_payload, build_cart, create_ucp_checkout

A2UI_SCHEMA_VERSION = "a2ui.grocery.v1"

# The trusted catalog: component name -> required prop keys. If the browser and
# the server disagree on this set, the payload is rejected before it renders.
TRUSTED_COMPONENTS: dict[str, tuple[str, ...]] = {
    "GroceryCatalogGrid": ("title", "items"),
    "CartSummary": ("cart_id", "items", "total"),
    "CheckoutApproval": ("status", "vibe_diff", "security_status"),
}


class A2uiValidationError(ValueError):
    """Raised when an A2UI payload is not renderable by the trusted catalog."""


def validate_a2ui(payload: dict[str, Any]) -> list[str]:
    """Return a list of validation errors ([] means the payload is trusted)."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    component = payload.get("component")
    if component not in TRUSTED_COMPONENTS:
        errors.append(f"component '{component}' is not in the trusted catalog")
        return errors  # cannot check props for an unknown component

    props = payload.get("props")
    if not isinstance(props, dict):
        errors.append("props must be an object")
        return errors

    for required in TRUSTED_COMPONENTS[component]:
        if required not in props:
            errors.append(f"{component} is missing required prop '{required}'")
    return errors


def assert_valid_a2ui(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and return the payload, or raise A2uiValidationError."""
    errors = validate_a2ui(payload)
    if errors:
        raise A2uiValidationError("; ".join(errors))
    return payload


# ── Component builders — each returns a validated A2UI payload ───────────────
def catalog_component(query: str) -> dict[str, Any]:
    """Trusted GroceryCatalogGrid payload with dynamic product imagery."""
    return assert_valid_a2ui(build_a2ui_catalog_payload(query))


def cart_component(line_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a cart into a trusted CartSummary A2UI payload."""
    cart = build_cart(line_items)
    if cart.get("status") != "success":
        # Surface the error as an off-happy-path CartSummary rather than raising,
        # so the UI can show why the cart could not be built.
        return assert_valid_a2ui(
            {
                "schema": A2UI_SCHEMA_VERSION,
                "component": "CartSummary",
                "props": {
                    "title": "Cart error",
                    "cart_id": "none",
                    "items": [],
                    "total": 0.0,
                    "error": cart.get("reason", "could not build cart"),
                    "actions": [],
                },
            }
        )
    return assert_valid_a2ui(
        {
            "schema": A2UI_SCHEMA_VERSION,
            "component": "CartSummary",
            "props": {
                "title": "Your grocery cart",
                "cart_id": cart["cart_id"],
                "items": cart["items"],
                "subtotal": cart["subtotal"],
                "service_fee": cart["service_fee"],
                "total": cart["total"],
                "actions": [
                    {"id": "review_checkout", "label": "Review checkout"},
                ],
            },
        }
    )


def _security_status(checkout: dict[str, Any]) -> dict[str, Any]:
    """Distil the security posture of a checkout into UI-friendly chips."""
    txn = checkout.get("ucp_transaction") or {}
    mandate = checkout.get("ap2_mandate") or {}
    policy = checkout.get("policy") or {}
    token = txn.get("jit_token") or {}
    return {
        "vibe_diff_required": bool(
            (checkout.get("vibe_diff") or {}).get("requires_human_approval")
        ),
        "approved": checkout.get("status") == "ready_for_fulfillment",
        "policy_decision": policy.get("decision", "n/a"),
        "policy_risk": policy.get("risk_level", "n/a"),
        "jit_scoped": bool(mandate.get("jit_token_id")),
        "jit_scope": (
            f"{token.get('allowed_action', 'n/a')} @ {token.get('resource', 'n/a')}"
            if token
            else "not yet issued"
        ),
        "identity_check": "signed A2A identity verified before delivery scheduling",
        "ap2_mandate_id": mandate.get("mandate_id", "not created"),
    }


def checkout_component(
    line_items: list[dict[str, Any]], delivery_window: str, approved: bool
) -> dict[str, Any]:
    """Wrap a UCP checkout into a trusted CheckoutApproval A2UI payload.

    Before approval this renders the Vibe-Diff and pauses; after approval it
    renders the created AP2 mandate and its JIT scope. The human approval gate
    lives in the browser but the decision is enforced server-side.
    """
    cart = build_cart(line_items)
    if cart.get("status") != "success":
        raise A2uiValidationError(cart.get("reason", "cart could not be built"))

    checkout = create_ucp_checkout(cart, delivery_window=delivery_window, approved=approved)
    return assert_valid_a2ui(
        {
            "schema": A2UI_SCHEMA_VERSION,
            "component": "CheckoutApproval",
            "props": {
                "title": "Checkout approval (Vibe-Diff)",
                "status": checkout["status"],
                "cart_id": cart["cart_id"],
                "total": cart["total"],
                "delivery_window": delivery_window,
                "vibe_diff": checkout.get("vibe_diff", {}),
                "security_status": _security_status(checkout),
                "ucp_transaction": checkout.get("ucp_transaction", {}),
                "ap2_mandate": checkout.get("ap2_mandate", {}),
                "actions": (
                    [{"id": "approve_checkout", "label": "Approve & create mandate"}]
                    if checkout["status"] == "needs_human_approval"
                    else [{"id": "done", "label": "Done"}]
                ),
            },
        }
    )
