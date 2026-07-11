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
    verify_jit_token,
)


def test_catalog_search_and_a2ui_payload_include_dynamic_images() -> None:
    results = search_catalog("breakfast")
    assert results["status"] == "success"
    assert results["items"]

    payload = build_a2ui_catalog_payload("breakfast")
    assert payload["schema"] == "a2ui.grocery.catalog.v1"
    assert payload["component"] == "GroceryCatalogGrid"
    assert all(item["image_url"].startswith("https://") for item in payload["props"]["items"])


def test_ucp_checkout_requires_approval_before_ap2_mandate() -> None:
    cart = build_cart([{"sku": "produce-avocado", "quantity": 2}])
    pending = create_ucp_checkout(cart, delivery_window="09:00-11:00", approved=False)
    assert pending["status"] == "needs_human_approval"
    assert pending["vibe_diff"]["requires_human_approval"] is True
    assert pending["ucp_transaction"]["state"] == "awaiting_user_approval"

    approved = create_ucp_checkout(cart, delivery_window="09:00-11:00", approved=True)
    assert approved["status"] == "ready_for_fulfillment"
    assert approved["ucp_transaction"]["state"] == "payment_mandate_created"
    assert approved["ap2_mandate"]["allowed_merchant_category"] == "grocery_delivery"


def test_jit_token_is_hyper_scoped_to_action_and_resource() -> None:
    token = issue_jit_token(
        agent_id="grocery-concierge",
        action="create_ap2_mandate",
        resource="cart_123",
        ttl_seconds=300,
    )["token"]
    assert verify_jit_token(token, "create_ap2_mandate", "cart_123")["status"] == "authorized"
    assert verify_jit_token(token, "refund_payment", "cart_123")["reason"] == "action_scope_mismatch"
    assert verify_jit_token(token, "create_ap2_mandate", "cart_999")["reason"] == "resource_scope_mismatch"


def test_signed_agent_identity_blocks_spoofed_a2a_call() -> None:
    assertion = mint_agent_assertion(
        agent_id="grocery-concierge",
        audience="grocery-platform",
        ttl_seconds=120,
    )["assertion"]
    assert verify_agent_assertion(assertion, "grocery-platform")["status"] == "trusted"

    spoofed = assertion | {"spiffe_id": "spiffe://local.grocery.example/delivery-scheduler"}
    denied = request_delivery_window(
        zip_code="60601",
        requested_day="tomorrow",
        agent_assertion=spoofed,
    )
    assert denied["status"] == "denied"
    assert denied["identity"]["reason"] in {"spoofed_spiffe_id", "bad_signature"}


def test_agbom_lists_learning_controls() -> None:
    agbom = build_agbom()
    assert "jit_downscoped_tokens" in agbom["controls"]
    assert "ap2_payment_mandate_simulation" in agbom["controls"]
    assert agbom["data_classification"] == "fictional educational grocery data only"
