// ─────────────────────────────────────────────────────────────────────────
// api.js — thin client for the A2UI server (app/a2ui_server.py)
// Every response is a declarative A2UI payload the renderer validates against
// its trusted component catalog before drawing anything.
// ─────────────────────────────────────────────────────────────────────────

async function asJson(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new Error(`A2UI request failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export function fetchCatalog(query = "") {
  const q = encodeURIComponent(query);
  return fetch(`/api/a2ui/catalog?q=${q}`).then(asJson);
}

export function fetchCart(lineItems) {
  return fetch("/api/a2ui/cart", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ line_items: lineItems }),
  }).then(asJson);
}

export function fetchCheckout(lineItems, deliveryWindow, approved) {
  return fetch("/api/a2ui/checkout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      line_items: lineItems,
      delivery_window: deliveryWindow,
      approved,
    }),
  }).then(asJson);
}
