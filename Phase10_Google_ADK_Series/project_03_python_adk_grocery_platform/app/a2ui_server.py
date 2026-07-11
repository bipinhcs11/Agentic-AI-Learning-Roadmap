# ═══════════════════════════════════════════════════════════════════════════
# a2ui_server.py — thin A2UI backend for the React renderer (offline, no cloud)
# ───────────────────────────────────────────────────────────────────────────
# Serves *validated* A2UI payloads built from the deterministic grocery/security
# helpers — no Gemini call is needed to run the UI, so the whole catalog → cart →
# Vibe-Diff → approved-mandate flow works offline. Every response passes through
# the trusted-catalog validator (app/a2ui.assert_valid_a2ui) before it leaves the
# server, demonstrating "A2UI server-side validation is mandatory".
#
# Run:
#   uv run uvicorn app.a2ui_server:app --port 8000
# The React dev server (vite, port 5174) proxies /api to here.
# ═══════════════════════════════════════════════════════════════════════════

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.a2ui import (
    A2uiValidationError,
    cart_component,
    catalog_component,
    checkout_component,
)

app = FastAPI(
    title="grocery-a2ui-server",
    description="Serves validated A2UI payloads for the grocery renderer (offline).",
)

# The React dev/preview servers; A2UI is same-data-classification demo content.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://localhost:4174",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:4174",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class LineItem(BaseModel):
    sku: str
    quantity: int


class CartRequest(BaseModel):
    line_items: list[LineItem]


class CheckoutRequest(BaseModel):
    line_items: list[LineItem]
    delivery_window: str = "09:00-11:00"
    approved: bool = False


def _items(line_items: list[LineItem]) -> list[dict[str, Any]]:
    return [{"sku": li.sku, "quantity": li.quantity} for li in line_items]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/a2ui/catalog")
def get_catalog(q: str = "") -> dict[str, Any]:
    """Return a validated GroceryCatalogGrid A2UI payload."""
    try:
        return catalog_component(q)
    except A2uiValidationError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail=f"A2UI rejected: {exc}") from exc


@app.post("/api/a2ui/cart")
def post_cart(req: CartRequest) -> dict[str, Any]:
    """Return a validated CartSummary A2UI payload for the given line items."""
    try:
        return cart_component(_items(req.line_items))
    except A2uiValidationError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=422, detail=f"A2UI rejected: {exc}") from exc


@app.post("/api/a2ui/checkout")
def post_checkout(req: CheckoutRequest) -> dict[str, Any]:
    """Return a validated CheckoutApproval A2UI payload (Vibe-Diff gate).

    approved=False renders the Vibe-Diff and pauses; approved=True creates the
    JIT-scoped AP2 mandate. The gate is enforced here, not in the browser.
    """
    try:
        return checkout_component(
            _items(req.line_items),
            delivery_window=req.delivery_window,
            approved=req.approved,
        )
    except A2uiValidationError as exc:
        raise HTTPException(status_code=422, detail=f"A2UI rejected: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
