# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Offline tests for the trusted A2UI catalog, builders, and server.

No cloud: the A2UI payloads are built from deterministic grocery/security
helpers, so the whole renderer backend is exercised without Vertex.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.a2ui import (
    TRUSTED_COMPONENTS,
    A2uiValidationError,
    cart_component,
    catalog_component,
    checkout_component,
    validate_a2ui,
)
from app.a2ui_server import app


# ── trusted-catalog validation ──────────────────────────────────────────────
def test_validate_rejects_unknown_component() -> None:
    errors = validate_a2ui({"component": "EvilScript", "props": {}})
    assert errors and "trusted catalog" in errors[0]


def test_validate_rejects_missing_required_prop() -> None:
    errors = validate_a2ui({"component": "CartSummary", "props": {"cart_id": "c1"}})
    assert any("items" in e for e in errors)
    assert any("total" in e for e in errors)


def test_every_builder_output_is_in_the_trusted_catalog() -> None:
    payloads = [
        catalog_component("breakfast"),
        cart_component([{"sku": "produce-avocado", "quantity": 1}]),
        checkout_component([{"sku": "produce-avocado", "quantity": 1}], "09:00-11:00", False),
    ]
    for payload in payloads:
        assert payload["component"] in TRUSTED_COMPONENTS
        assert validate_a2ui(payload) == []


# ── builders ─────────────────────────────────────────────────────────────────
def test_catalog_items_carry_dynamic_imagery() -> None:
    payload = catalog_component("breakfast")
    assert payload["props"]["items"]
    assert all(item["image_url"].startswith("https://") for item in payload["props"]["items"])


def test_cart_component_totals() -> None:
    payload = cart_component(
        [{"sku": "produce-berries", "quantity": 2}, {"sku": "dairy-yogurt", "quantity": 1}]
    )
    props = payload["props"]
    assert props["total"] == round(props["subtotal"] + props["service_fee"], 2)


def test_checkout_pending_shows_vibe_diff_and_no_mandate() -> None:
    payload = checkout_component([{"sku": "produce-avocado", "quantity": 2}], "09:00-11:00", False)
    sec = payload["props"]["security_status"]
    assert payload["props"]["status"] == "needs_human_approval"
    assert sec["vibe_diff_required"] is True
    assert sec["approved"] is False
    assert sec["ap2_mandate_id"] == "not created"


def test_checkout_approved_creates_scoped_mandate() -> None:
    payload = checkout_component([{"sku": "produce-avocado", "quantity": 2}], "09:00-11:00", True)
    sec = payload["props"]["security_status"]
    assert payload["props"]["status"] == "ready_for_fulfillment"
    assert sec["jit_scoped"] is True
    assert sec["ap2_mandate_id"].startswith("ap2_")
    assert "create_ap2_mandate" in sec["jit_scope"]


def test_checkout_rejects_unknown_sku() -> None:
    with pytest.raises(A2uiValidationError):
        checkout_component([{"sku": "does-not-exist", "quantity": 1}], "09:00-11:00", True)


# ── FastAPI server ───────────────────────────────────────────────────────────
def test_server_catalog_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/api/a2ui/catalog", params={"q": "breakfast"})
    assert resp.status_code == 200
    assert resp.json()["component"] == "GroceryCatalogGrid"


def test_server_checkout_flow_pending_then_approved() -> None:
    client = TestClient(app)
    body = {"line_items": [{"sku": "produce-avocado", "quantity": 2}]}

    pending = client.post("/api/a2ui/checkout", json={**body, "approved": False})
    assert pending.status_code == 200
    assert pending.json()["props"]["status"] == "needs_human_approval"

    approved = client.post("/api/a2ui/checkout", json={**body, "approved": True})
    assert approved.status_code == 200
    assert approved.json()["props"]["security_status"]["ap2_mandate_id"].startswith("ap2_")
