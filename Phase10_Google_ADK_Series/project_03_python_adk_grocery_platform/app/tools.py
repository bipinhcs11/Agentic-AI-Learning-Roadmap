"""ADK tool functions for the grocery platform agent."""

from __future__ import annotations

from typing import Any

from app.a2a_client import request_delivery_window
from app.grocery import (
    build_a2ui_catalog_payload,
    build_cart,
    create_ucp_checkout,
    search_catalog,
)
from app.security import (
    build_agbom,
    issue_jit_token,
    mint_agent_assertion,
    verify_agent_assertion,
)


def search_grocery_catalog(query: str) -> dict[str, Any]:
    """Search the fictional local grocery catalog by category, product, or tag."""
    return search_catalog(query)


def render_grocery_a2ui(query: str) -> dict[str, Any]:
    """Return A2UI JSON for a grocery catalog grid with dynamic product imagery."""
    return {"status": "success", "a2ui": build_a2ui_catalog_payload(query)}


def create_cart(line_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Create a cart from grocery SKU and quantity pairs."""
    return build_cart(line_items)


def ask_delivery_scheduler(zip_code: str, requested_day: str) -> dict[str, Any]:
    """Call the delivery scheduler across a signed A2A-style service boundary."""
    return request_delivery_window(zip_code=zip_code, requested_day=requested_day)


def prepare_checkout(
    line_items: list[dict[str, Any]],
    delivery_window: str,
    approved: bool,
) -> dict[str, Any]:
    """Prepare a UCP checkout transaction and AP2 mandate after human approval."""
    cart = build_cart(line_items)
    return create_ucp_checkout(cart=cart, delivery_window=delivery_window, approved=approved)


def issue_demo_jit_token(agent_id: str, action: str, resource: str) -> dict[str, Any]:
    """Issue a short-lived JIT token for a single action/resource pair."""
    return issue_jit_token(agent_id=agent_id, action=action, resource=resource, ttl_seconds=300)


def verify_demo_agent_identity(agent_id: str, audience: str) -> dict[str, Any]:
    """Mint and verify a signed agent identity assertion for spoofing-defense demos."""
    assertion = mint_agent_assertion(agent_id=agent_id, audience=audience, ttl_seconds=120)
    if assertion["status"] != "issued":
        return assertion
    return verify_agent_assertion(assertion["assertion"], expected_audience=audience)


def show_agent_bill_of_materials() -> dict[str, Any]:
    """Return the Agent Bill of Materials for this learning module."""
    return {"status": "success", "agbom": build_agbom()}
