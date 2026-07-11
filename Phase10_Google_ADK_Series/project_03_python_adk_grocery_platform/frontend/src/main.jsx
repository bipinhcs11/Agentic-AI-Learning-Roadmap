// ═══════════════════════════════════════════════════════════════════════════
// main.jsx — A2UI renderer with a trusted component catalog
// ───────────────────────────────────────────────────────────────────────────
// The agent/server sends declarative A2UI JSON; this app renders ONLY the
// components in TRUSTED_COMPONENTS. An unknown component name is refused, not
// rendered — the browser-side half of "A2UI validation is mandatory" (the server
// validates too, in app/a2ui.py). The flow it drives:
//   catalog  →  add to cart  →  cart summary  →  Vibe-Diff approval  →  AP2 mandate
// Every screen is a server-built, validated A2UI payload. Data is fictional.
// ═══════════════════════════════════════════════════════════════════════════

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BadgeCheck,
  Package,
  ShieldCheck,
  ShoppingCart,
  Truck,
} from "lucide-react";
import { fetchCart, fetchCatalog, fetchCheckout } from "./api.js";
import "./styles.css";

// ── Dynamic imagery with a guaranteed fallback ─────────────────────────────
const CATEGORY_COLORS = {
  Produce: "#3f9d5a",
  Dairy: "#e0b64a",
  Bakery: "#c9822e",
  Pantry: "#8a6d3b",
  Frozen: "#4a90c9",
};

function fallbackImage(name = "Grocery", category = "Grocery") {
  const color = CATEGORY_COLORS[category] ?? "#1f6f43";
  const label = (name || category).slice(0, 22);
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='600' height='450'>
    <defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0' stop-color='${color}'/>
      <stop offset='1' stop-color='#14311f'/></linearGradient></defs>
    <rect width='600' height='450' fill='url(#g)'/>
    <text x='50%' y='48%' fill='white' font-size='34' font-family='sans-serif'
      font-weight='700' text-anchor='middle'>${label}</text>
    <text x='50%' y='60%' fill='rgba(255,255,255,0.75)' font-size='20'
      font-family='sans-serif' text-anchor='middle'>${category}</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function ProductImage({ item }) {
  const [src, setSrc] = useState(item.image_url || fallbackImage(item.name, item.category));
  return (
    <img
      src={src}
      alt={item.name}
      loading="lazy"
      onError={() => setSrc(fallbackImage(item.name, item.category))}
    />
  );
}

// ── Trusted A2UI components (must mirror app/a2ui.TRUSTED_COMPONENTS) ────────
function GroceryCatalogGrid({ props, onAddToCart }) {
  return (
    <section className="catalog-grid" aria-label="grocery items">
      {props.items.map((item) => (
        <article className="product-card" key={item.sku}>
          <ProductImage item={item} />
          <div className="product-body">
            <div>
              <p className="category">{item.category}</p>
              <h2>{item.name}</h2>
            </div>
            <p className="price">${item.price.toFixed(2)}</p>
            <div className="tags">
              {(item.tags ?? []).map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
            <button type="button" onClick={() => onAddToCart(item.sku)}>
              <ShoppingCart size={16} /> Add to cart
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}

function CartSummary({ props, onReviewCheckout }) {
  if (props.error) {
    return <p className="notice error">Cart error: {props.error}</p>;
  }
  return (
    <section className="cart-panel" aria-label="cart">
      <h2>{props.title}</h2>
      <ul className="cart-lines">
        {props.items.map((item) => (
          <li key={item.sku}>
            <span>
              {item.quantity} × {item.name}
            </span>
            <span>${item.line_total.toFixed(2)}</span>
          </li>
        ))}
      </ul>
      <dl className="totals">
        <div>
          <dt>Subtotal</dt>
          <dd>${props.subtotal.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Service fee</dt>
          <dd>${props.service_fee.toFixed(2)}</dd>
        </div>
        <div className="grand">
          <dt>Total</dt>
          <dd>${props.total.toFixed(2)}</dd>
        </div>
      </dl>
      <button type="button" onClick={onReviewCheckout}>
        Review checkout
      </button>
    </section>
  );
}

function SecurityChip({ ok, label }) {
  return (
    <span className={`chip ${ok ? "ok" : "pending"}`}>
      {ok ? <BadgeCheck size={15} /> : <AlertTriangle size={15} />} {label}
    </span>
  );
}

function CheckoutApproval({ props, onApprove, busy }) {
  const sec = props.security_status;
  const approved = props.status === "ready_for_fulfillment";
  return (
    <section className="checkout-panel" aria-label="checkout approval">
      <h2>{props.title}</h2>

      <div className="vibe-diff">
        <p className="eyebrow">Vibe-Diff — plain-English summary you approve</p>
        <p>{props.vibe_diff.summary}</p>
        <p className="high-stakes">
          High-stakes action: <code>{props.vibe_diff.high_stakes_action}</code>
        </p>
      </div>

      <div className="sec-chips">
        <SecurityChip ok label={sec.identity_check} />
        <SecurityChip
          ok={sec.policy_decision === "allow"}
          label={`policy: ${sec.policy_decision} (${sec.policy_risk})`}
        />
        <SecurityChip ok={sec.jit_scoped} label={`JIT: ${sec.jit_scope}`} />
        <SecurityChip
          ok={approved}
          label={approved ? "human approval captured" : "awaiting human approval"}
        />
      </div>

      {approved ? (
        <div className="mandate">
          <p className="eyebrow">
            <ShieldCheck size={15} /> AP2 payment mandate created
          </p>
          <ul>
            <li>
              Mandate: <code>{props.ap2_mandate.mandate_id}</code>
            </li>
            <li>
              Amount: ${Number(props.ap2_mandate.amount).toFixed(2)}{" "}
              {props.ap2_mandate.currency}
            </li>
            <li>
              Merchant category: <code>{props.ap2_mandate.allowed_merchant_category}</code>
            </li>
            <li>
              <Truck size={14} /> Delivery window: {props.delivery_window}
            </li>
            <li>UCP state: {props.ucp_transaction.state}</li>
          </ul>
        </div>
      ) : (
        <button type="button" className="approve" onClick={onApprove} disabled={busy}>
          {busy ? "Creating mandate…" : "Approve & create payment mandate"}
        </button>
      )}
    </section>
  );
}

// The browser-side trusted catalog. Server sends a component name; if it is not
// one of these, we refuse to render it.
const TRUSTED_COMPONENTS = {
  GroceryCatalogGrid,
  CartSummary,
  CheckoutApproval,
};

function A2uiRenderer({ payload, handlers }) {
  if (!payload) return null;
  const Component = TRUSTED_COMPONENTS[payload.component];
  if (!Component) {
    return (
      <p className="notice error">
        <AlertTriangle size={16} /> Blocked: component &ldquo;{payload.component}&rdquo; is
        not in the trusted A2UI catalog.
      </p>
    );
  }
  return <Component props={payload.props} {...handlers} />;
}

// ── App ─────────────────────────────────────────────────────────────────────
function App() {
  const [query, setQuery] = useState("");
  const [view, setView] = useState("catalog"); // catalog | cart | checkout
  const [catalog, setCatalog] = useState(null);
  const [cart, setCart] = useState(null);
  const [checkout, setCheckout] = useState(null);
  const [lineItems, setLineItems] = useState({}); // sku -> qty
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const lineItemArray = useMemo(
    () => Object.entries(lineItems).map(([sku, quantity]) => ({ sku, quantity })),
    [lineItems],
  );
  const itemCount = useMemo(
    () => Object.values(lineItems).reduce((a, b) => a + b, 0),
    [lineItems],
  );

  const loadCatalog = useCallback((q) => {
    setError(null);
    fetchCatalog(q).then(setCatalog).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    loadCatalog("");
  }, [loadCatalog]);

  const addToCart = (sku) => {
    setLineItems((prev) => ({ ...prev, [sku]: (prev[sku] ?? 0) + 1 }));
  };

  const openCart = () => {
    if (lineItemArray.length === 0) return;
    setError(null);
    fetchCart(lineItemArray)
      .then((p) => {
        setCart(p);
        setView("cart");
      })
      .catch((e) => setError(e.message));
  };

  const reviewCheckout = () => {
    setError(null);
    fetchCheckout(lineItemArray, "09:00-11:00", false)
      .then((p) => {
        setCheckout(p);
        setView("checkout");
      })
      .catch((e) => setError(e.message));
  };

  const approveCheckout = () => {
    setBusy(true);
    setError(null);
    fetchCheckout(lineItemArray, "09:00-11:00", true)
      .then(setCheckout)
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  };

  const title =
    view === "catalog"
      ? catalog?.props?.title ?? "Fresh grocery picks"
      : view === "cart"
        ? "Cart"
        : "Secure checkout";

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <p className="eyebrow">A2UI payload renderer · trusted catalog</p>
          <h1>{title}</h1>
        </div>
        <div className="status-strip" aria-label="security controls">
          <span>
            <ShieldCheck size={16} /> JIT scoped
          </span>
          <span>
            <Truck size={16} /> A2A delivery
          </span>
          <span>
            <ShoppingCart size={16} /> UCP + AP2
          </span>
        </div>
      </section>

      <nav className="tabs">
        <button
          type="button"
          className={view === "catalog" ? "active" : ""}
          onClick={() => setView("catalog")}
        >
          <Package size={15} /> Catalog
        </button>
        <button
          type="button"
          className={view === "cart" ? "active" : ""}
          onClick={openCart}
          disabled={itemCount === 0}
        >
          <ShoppingCart size={15} /> Cart ({itemCount})
        </button>
        {view === "catalog" && (
          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              loadCatalog(query);
            }}
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search e.g. breakfast, dinner, snack"
              aria-label="search groceries"
            />
            <button type="submit">Search</button>
          </form>
        )}
      </nav>

      {error && (
        <p className="notice error">
          <AlertTriangle size={16} /> {error} — is the A2UI server running on :8000?
        </p>
      )}

      {view === "catalog" && (
        <A2uiRenderer payload={catalog} handlers={{ onAddToCart: addToCart }} />
      )}
      {view === "cart" && (
        <A2uiRenderer payload={cart} handlers={{ onReviewCheckout: reviewCheckout }} />
      )}
      {view === "checkout" && (
        <A2uiRenderer
          payload={checkout}
          handlers={{ onApprove: approveCheckout, busy }}
        />
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
