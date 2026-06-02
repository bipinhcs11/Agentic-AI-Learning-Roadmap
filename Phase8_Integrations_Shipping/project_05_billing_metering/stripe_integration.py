"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║     Phase 8 — Project 05: Billing | stripe_integration.py                      ║
║                    Simulated Stripe API (No Real Stripe Needed)                 ║
║                                                                                 ║
║  PURPOSE: Teaches the Stripe API surface without requiring a real Stripe        ║
║  account or credit card. Every method in StripeSimulator maps 1:1 to the       ║
║  real Stripe Python library — swap the class for real Stripe when ready.       ║
║                                                                                 ║
║  THE REAL STRIPE EQUIVALENTS (shown in comments):                               ║
║    stripe.Customer.create()       ↔ create_customer()                          ║
║    stripe.Subscription.create()   ↔ create_subscription()                      ║
║    stripe.PaymentIntent.create()  ↔ charge()                                   ║
║    stripe.Invoice.create()        ↔ create_invoice()                           ║
║                                                                                 ║
║  STRIPE CONCEPTS:                                                               ║
║  - Customer: The billable entity (one per tenant in multi-tenant SaaS)          ║
║  - Subscription: Recurring billing plan (maps to free/pro/enterprise)           ║
║  - PaymentIntent: A single charge (one-time payment)                            ║
║  - Invoice: A detailed bill (used for usage-based billing)                      ║
║  - Webhook: Stripe calls YOUR server when payments succeed/fail                 ║
║                                                                                 ║
║  WHY SIMULATE? Real Stripe requires API keys, test credit cards, and            ║
║  webhook setup. The simulation lets you build the entire billing flow           ║
║  and test it before connecting to Stripe.                                       ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ─── Database for the Stripe simulation ──────────────────────────────────────
STRIPE_DB_PATH = Path(__file__).parent / "stripe_sim.db"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# Mirroring Stripe's object structure so code is easy to migrate to real Stripe
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StripeCustomer:
    """Mirrors the Stripe Customer object.

    Real Stripe: https://stripe.com/docs/api/customers/object
    In real Stripe: customer_id starts with 'cus_' (e.g., 'cus_Nxyz123')
    We prefix with 'sim_cus_' to make it obvious this is simulated.
    """
    customer_id: str
    email: str
    name: str
    tenant_id: str
    created_at: str  # ISO 8601 timestamp
    # In real Stripe: also has address, default_payment_method, metadata dict


@dataclass
class StripeSubscription:
    """Mirrors the Stripe Subscription object.

    Real Stripe: https://stripe.com/docs/api/subscriptions/object
    In real Stripe: subscription_id starts with 'sub_'
    """
    subscription_id: str
    customer_id: str
    plan: str                # Maps to a Stripe Price ID in real life
    status: str              # active | past_due | canceled | trialing
    current_period_start: str
    current_period_end: str
    amount_cents: int        # Monthly amount in cents (e.g., 2900 = $29.00)
    created_at: str
    # In real Stripe: also has items (list of prices), billing_cycle_anchor, etc.


@dataclass
class StripePaymentIntent:
    """Mirrors the Stripe PaymentIntent object.

    Real Stripe: https://stripe.com/docs/api/payment_intents/object
    PaymentIntent is the modern way to handle payments in Stripe.
    It replaced Charges for most use cases.
    """
    payment_intent_id: str
    customer_id: str
    amount_cents: int        # Amount in cents (Stripe never uses floats for money)
    currency: str            # ISO 4217 code: "usd", "eur", etc.
    description: str
    status: str              # requires_payment_method | requires_confirmation | succeeded | failed
    created_at: str
    # In real Stripe: also has payment_method, client_secret (for frontend), metadata


@dataclass
class StripeInvoiceLineItem:
    """One line item on a Stripe Invoice."""
    description: str
    amount_cents: int
    quantity: int = 1


@dataclass
class StripeInvoice:
    """Mirrors the Stripe Invoice object.

    Real Stripe: https://stripe.com/docs/api/invoices/object
    Invoices in Stripe are used for:
    - Subscription billing (auto-generated monthly)
    - Usage-based billing (metered subscriptions)
    - One-time charges with itemized breakdown
    """
    invoice_id: str
    customer_id: str
    line_items: list[StripeInvoiceLineItem]
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    status: str              # draft | open | paid | void | uncollectible
    pdf_url: str             # In real Stripe, this is a real PDF hosted by Stripe
    created_at: str
    due_date: Optional[str] = None
    # In real Stripe: also has hosted_invoice_url, payment_intent, charge


# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE PLAN CONFIGURATION
# In real Stripe, these would be Price IDs from your Stripe Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

STRIPE_PLANS = {
    # Plan name → {stripe_price_id (simulated), amount_cents, description}
    "free": {
        "price_id": "price_sim_free_2026",
        "amount_cents": 0,
        "description": "Free Plan — 100 requests/month",
    },
    "pro": {
        "price_id": "price_sim_pro_2026",
        "amount_cents": 4900,          # $49.00/month
        "description": "Pro Plan — 1,000 requests/month",
    },
    "enterprise": {
        "price_id": "price_sim_enterprise_2026",
        "amount_cents": 49900,         # $499.00/month flat rate
        "description": "Enterprise Plan — Unlimited requests",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class StripeSimulator:
    """Simulates the Stripe API using SQLite for storage.

    HOW TO MIGRATE TO REAL STRIPE:
    1. pip install stripe
    2. import stripe; stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    3. Replace each method with the equivalent stripe.X.create() call
    4. See migration notes in each method's docstring

    IMPORTANT: In real Stripe, amounts are ALWAYS in the smallest currency unit:
    - USD: cents ($29.00 = 2900 cents)
    - JPY: yen (¥300 = 300 yen — no subdivision)
    - GBP: pence (£29.00 = 2900 pence)
    Never use floats for money. Always integers in smallest unit.
    """

    def __init__(self, db_path: Path = STRIPE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the Stripe simulation database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stripe_customers (
                    customer_id   TEXT PRIMARY KEY,
                    email         TEXT NOT NULL,
                    name          TEXT NOT NULL,
                    tenant_id     TEXT NOT NULL,
                    created_at    TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stripe_subscriptions (
                    subscription_id       TEXT PRIMARY KEY,
                    customer_id           TEXT NOT NULL,
                    plan                  TEXT NOT NULL,
                    status                TEXT NOT NULL DEFAULT 'active',
                    current_period_start  TEXT NOT NULL,
                    current_period_end    TEXT NOT NULL,
                    amount_cents          INTEGER NOT NULL,
                    created_at            TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stripe_payment_intents (
                    payment_intent_id  TEXT PRIMARY KEY,
                    customer_id        TEXT NOT NULL,
                    amount_cents       INTEGER NOT NULL,
                    currency           TEXT NOT NULL DEFAULT 'usd',
                    description        TEXT,
                    status             TEXT NOT NULL,
                    created_at         TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stripe_invoices (
                    invoice_id      TEXT PRIMARY KEY,
                    customer_id     TEXT NOT NULL,
                    line_items      TEXT NOT NULL,  -- JSON array
                    subtotal_cents  INTEGER NOT NULL,
                    tax_cents       INTEGER NOT NULL,
                    total_cents     INTEGER NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'open',
                    pdf_url         TEXT,
                    due_date        TEXT,
                    created_at      TEXT NOT NULL
                )
            """)
            conn.commit()

    def _generate_id(self, prefix: str) -> str:
        """Generate a Stripe-style ID with a prefix.

        Real Stripe IDs: cus_Nxyz123, sub_Nxyz456, pi_Nxyz789
        We use 'sim_' prefix to distinguish simulated from real.
        """
        short_uuid = str(uuid.uuid4()).replace("-", "")[:16]
        return f"sim_{prefix}_{short_uuid}"

    # ─── Customer Management ──────────────────────────────────────────────────

    def create_customer(self, email: str, name: str, tenant_id: str) -> dict:
        """Create a new Stripe customer for a tenant.

        REAL STRIPE EQUIVALENT:
            import stripe
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"tenant_id": tenant_id}  # Stripe metadata for your reference
            )
            return {"customer_id": customer.id}

        WHY one customer per tenant? Each tenant = one billable entity.
        Stripe Customer is the central object — subscriptions, invoices,
        and payment methods all attach to the Customer.
        """
        customer_id = self._generate_id("cus")
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO stripe_customers VALUES (?, ?, ?, ?, ?)""",
                (customer_id, email, name, tenant_id, now),
            )
            conn.commit()

        print(f"  [Stripe] Created customer: {customer_id} ({name})")
        return {
            "customer_id": customer_id,
            "email": email,
            "name": name,
            "object": "customer",  # Stripe includes "object" in every response
        }

    def get_customer(self, customer_id: str) -> Optional[StripeCustomer]:
        """Retrieve a customer by ID.

        REAL STRIPE EQUIVALENT:
            stripe.Customer.retrieve(customer_id)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM stripe_customers WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()

        if not row:
            return None
        return StripeCustomer(**dict(row))

    # ─── Subscriptions ────────────────────────────────────────────────────────

    def create_subscription(self, customer_id: str, plan: str) -> dict:
        """Create a recurring subscription for a customer.

        REAL STRIPE EQUIVALENT:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": STRIPE_PLANS[plan]["price_id"]}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )
            return {"subscription_id": subscription.id}

        WHY "default_incomplete"? This is the modern Stripe pattern:
        1. Create subscription (status: incomplete)
        2. Return client_secret to the frontend
        3. Frontend collects payment via Stripe Elements
        4. Stripe confirms payment, subscription becomes "active"
        5. Your webhook receives "customer.subscription.updated" event

        Without payment_behavior="default_incomplete", Stripe immediately
        charges the card — fine for server-side flows, but not recommended
        for new subscriptions with a frontend.
        """
        if plan not in STRIPE_PLANS:
            raise ValueError(f"Unknown plan: {plan}. Valid: {list(STRIPE_PLANS)}")

        plan_config = STRIPE_PLANS[plan]
        subscription_id = self._generate_id("sub")
        now = datetime.utcnow()

        # Billing period: start now, end in 1 month
        period_start = now.isoformat()
        period_end = (now + timedelta(days=30)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO stripe_subscriptions VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    subscription_id,
                    customer_id,
                    plan,
                    "active",
                    period_start,
                    period_end,
                    plan_config["amount_cents"],
                    now.isoformat(),
                ),
            )
            conn.commit()

        print(f"  [Stripe] Created subscription: {subscription_id} ({plan} plan, ${plan_config['amount_cents']/100:.2f}/mo)")
        return {
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "plan": plan,
            "status": "active",
            "amount_cents": plan_config["amount_cents"],
            "current_period_end": period_end,
            "object": "subscription",
        }

    def cancel_subscription(self, subscription_id: str) -> dict:
        """Cancel a subscription immediately.

        REAL STRIPE EQUIVALENT:
            stripe.Subscription.delete(subscription_id)
            # Or for cancellation at period end:
            stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)

        WHY two options? Immediate cancellation is refund-eligible.
        "cancel_at_period_end" is more customer-friendly — they keep access
        until their paid period ends, then the subscription deactivates.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE stripe_subscriptions SET status = 'canceled' WHERE subscription_id = ?",
                (subscription_id,),
            )
            conn.commit()

        print(f"  [Stripe] Canceled subscription: {subscription_id}")
        return {"subscription_id": subscription_id, "status": "canceled"}

    # ─── Charges (PaymentIntents) ─────────────────────────────────────────────

    def charge(self, customer_id: str, amount_cents: int, description: str) -> dict:
        """Create a one-time charge for a customer.

        REAL STRIPE EQUIVALENT:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                customer=customer_id,
                payment_method=customer.default_payment_method,
                description=description,
                confirm=True,          # Charge immediately
                return_url="https://yourdomain.com/payment/return",
            )
            return {
                "payment_intent_id": payment_intent.id,
                "status": payment_intent.status,
            }

        WHY PaymentIntent and not Charge? Stripe deprecated direct Charges
        for new integrations. PaymentIntents handle Strong Customer Authentication
        (SCA/3D Secure) required in Europe, and work across all payment methods.

        STATUS FLOW in real Stripe:
        requires_payment_method → requires_confirmation → requires_action
        (3D Secure) → processing → succeeded / requires_payment_method (failed)
        """
        payment_intent_id = self._generate_id("pi")
        now = datetime.utcnow().isoformat()

        # Simulate payment success (real Stripe would call payment processor)
        # In testing, Stripe test cards: 4242424242424242 always succeeds
        status = "succeeded"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO stripe_payment_intents VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (payment_intent_id, customer_id, amount_cents, "usd", description, status, now),
            )
            conn.commit()

        print(f"  [Stripe] Charged: {payment_intent_id} — ${amount_cents/100:.2f} ({status})")
        return {
            "payment_intent_id": payment_intent_id,
            "customer_id": customer_id,
            "amount_cents": amount_cents,
            "amount_dollars": amount_cents / 100,
            "currency": "usd",
            "status": status,
            "object": "payment_intent",
        }

    # ─── Invoices ─────────────────────────────────────────────────────────────

    def create_invoice(
        self,
        customer_id: str,
        line_items: list[dict],
        due_days: int = 30,
    ) -> dict:
        """Create a detailed invoice with line items.

        REAL STRIPE EQUIVALENT:
            # Step 1: Add invoice items
            for item in line_items:
                stripe.InvoiceItem.create(
                    customer=customer_id,
                    amount=item["amount_cents"],
                    currency="usd",
                    description=item["description"],
                )

            # Step 2: Create and finalize the invoice
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=True,  # Automatically finalize and send
                collection_method="send_invoice",
                days_until_due=due_days,
            )
            invoice.finalize_invoice()  # Generates PDF and hosted URL

            return {
                "invoice_id": invoice.id,
                "pdf_url": invoice.invoice_pdf,
                "hosted_url": invoice.hosted_invoice_url,
            }

        IMPORTANT: In real Stripe, invoice items must be added BEFORE creating
        the invoice. The invoice picks up all pending invoice items for the customer.

        WHY use invoices vs direct charges for SaaS?
        - Invoices are professional (PDF with line items)
        - They support net-30/60 payment terms
        - They integrate with accounting software (QuickBooks, Xero)
        - They support dunning (automatic retry + reminder emails)
        """
        invoice_id = self._generate_id("in")
        now = datetime.utcnow()
        due_date = (now + timedelta(days=due_days)).isoformat()

        # Calculate totals
        subtotal_cents = sum(item.get("amount_cents", 0) for item in line_items)
        tax_cents = int(subtotal_cents * 0.10)
        total_cents = subtotal_cents + tax_cents

        # Simulated PDF URL — real Stripe generates actual PDFs
        pdf_url = f"https://invoice.stripe.com/i/{invoice_id}/pdf"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO stripe_invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_id,
                    customer_id,
                    json.dumps(line_items),
                    subtotal_cents,
                    tax_cents,
                    total_cents,
                    "open",
                    pdf_url,
                    due_date,
                    now.isoformat(),
                ),
            )
            conn.commit()

        print(f"  [Stripe] Created invoice: {invoice_id} — ${total_cents/100:.2f} due {due_date[:10]}")
        return {
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "total_dollars": total_cents / 100,
            "status": "open",
            "pdf_url": pdf_url,  # In real Stripe: actual PDF hosted on Stripe CDN
            "due_date": due_date[:10],
            "object": "invoice",
        }

    def pay_invoice(self, invoice_id: str) -> dict:
        """Mark an invoice as paid.

        REAL STRIPE EQUIVALENT:
            stripe.Invoice.pay(invoice_id)
            # Stripe will charge the customer's default payment method
            # and mark the invoice as paid automatically

        In real Stripe, you'd receive a webhook "invoice.paid" event when
        the payment succeeds, and "invoice.payment_failed" if it fails.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE stripe_invoices SET status = 'paid' WHERE invoice_id = ?",
                (invoice_id,),
            )
            conn.commit()

        print(f"  [Stripe] Invoice paid: {invoice_id}")
        return {"invoice_id": invoice_id, "status": "paid"}

    # ─── Reporting ────────────────────────────────────────────────────────────

    def get_customer_invoices(self, customer_id: str) -> list[dict]:
        """List all invoices for a customer.

        REAL STRIPE EQUIVALENT:
            invoices = stripe.Invoice.list(customer=customer_id, limit=100)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM stripe_invoices WHERE customer_id = ? ORDER BY created_at DESC",
                (customer_id,),
            ).fetchall()

        result = []
        for row in rows:
            d = dict(row)
            d["line_items"] = json.loads(d["line_items"])
            d["total_dollars"] = d["total_cents"] / 100
            result.append(d)
        return result

    def get_all_subscriptions(self) -> list[dict]:
        """List all subscriptions — for platform-level monitoring.

        REAL STRIPE EQUIVALENT:
            stripe.Subscription.list(limit=100, expand=['data.customer'])
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM stripe_subscriptions ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def simulate_webhook(self, event_type: str, object_id: str) -> dict:
        """Simulate a Stripe webhook event.

        REAL STRIPE WEBHOOKS:
        In production, Stripe calls your server's /webhook endpoint with events:
        - customer.created
        - customer.subscription.updated
        - invoice.paid
        - invoice.payment_failed
        - payment_intent.succeeded
        - payment_intent.payment_failed

        To receive webhooks locally during development:
            pip install stripe stripe-cli
            stripe listen --forward-to localhost:8000/webhook

        CRITICAL: Always verify webhook signatures!
            stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        This prevents spoofed webhook attacks.
        """
        print(f"\n  [Stripe Webhook] Event: {event_type}")
        print(f"  [Stripe Webhook] Object: {object_id}")
        print(f"  [Stripe Webhook] Timestamp: {datetime.utcnow().isoformat()}")
        print("  [Stripe Webhook] → Your handler would:")

        if event_type == "invoice.paid":
            print("    → Mark tenant as paid in your database")
            print("    → Send receipt email to customer")
            print("    → Reset monthly quota")
        elif event_type == "invoice.payment_failed":
            print("    → Send dunning email to customer")
            print("    → Downgrade plan after N failed attempts")
            print("    → Flag account for review")
        elif event_type == "customer.subscription.updated":
            print("    → Update tenant plan in your database")
            print("    → Update quota limits")
            print("    → Log audit event")
        elif event_type == "payment_intent.succeeded":
            print("    → Provision service immediately")
            print("    → Send welcome/confirmation email")

        return {
            "event_type": event_type,
            "object_id": object_id,
            "handled": True,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO — End-to-End Billing Simulation
# ═══════════════════════════════════════════════════════════════════════════════

def run_stripe_demo() -> None:
    """Demonstrate the full Stripe billing lifecycle."""

    print("\n" + "═" * 68)
    print("  STRIPE INTEGRATION SIMULATOR — Phase 8 Project 05")
    print("  Demonstrating the complete billing lifecycle")
    print("═" * 68)

    stripe = StripeSimulator()

    # ── Step 1: Create customers (one per tenant) ────────────────────────────
    print("\n[Step 1] Creating Stripe customers for tenants...")
    customer_acme = stripe.create_customer(
        email="billing@acme-corp.example",
        name="Acme Corp",
        tenant_id="acme-corp",
    )
    customer_startup = stripe.create_customer(
        email="billing@startup-inc.example",
        name="Startup Inc",
        tenant_id="startup-inc",
    )

    # ── Step 2: Create subscriptions ─────────────────────────────────────────
    print("\n[Step 2] Creating subscriptions...")
    sub_acme = stripe.create_subscription(customer_acme["customer_id"], "pro")
    sub_startup = stripe.create_subscription(customer_startup["customer_id"], "free")

    # ── Step 3: Create usage-based invoice ───────────────────────────────────
    print("\n[Step 3] Generating usage-based invoice for Acme Corp...")
    invoice = stripe.create_invoice(
        customer_id=customer_acme["customer_id"],
        line_items=[
            {
                "description": "gemma3:4b — Input tokens (50,000)",
                "amount_cents": 50,   # $0.50
                "quantity": 50000,
            },
            {
                "description": "gemma3:4b — Output tokens (25,000)",
                "amount_cents": 75,   # $0.75
                "quantity": 25000,
            },
            {
                "description": "Pro Plan — Base fee",
                "amount_cents": 4900,  # $49.00
                "quantity": 1,
            },
        ],
        due_days=30,
    )

    # ── Step 4: Charge for the invoice ───────────────────────────────────────
    print("\n[Step 4] Processing payment...")
    payment = stripe.charge(
        customer_id=customer_acme["customer_id"],
        amount_cents=invoice["total_cents"],
        description=f"Invoice {invoice['invoice_id']} — Acme Corp",
    )

    if payment["status"] == "succeeded":
        stripe.pay_invoice(invoice["invoice_id"])

    # ── Step 5: Simulate webhooks ─────────────────────────────────────────────
    print("\n[Step 5] Simulating webhook events...")
    stripe.simulate_webhook("invoice.paid", invoice["invoice_id"])
    stripe.simulate_webhook("payment_intent.succeeded", payment["payment_intent_id"])

    # ── Step 6: List customer invoices ────────────────────────────────────────
    print("\n[Step 6] Customer invoice history...")
    invoices = stripe.get_customer_invoices(customer_acme["customer_id"])
    for inv in invoices:
        print(
            f"  Invoice {inv['invoice_id']}: ${inv['total_dollars']:.2f} — {inv['status']}"
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "═" * 68)
    print("  SIMULATION COMPLETE")
    print("═" * 68)
    print("\n  Objects created:")
    print(f"  Customer (Acme):    {customer_acme['customer_id']}")
    print(f"  Customer (Startup): {customer_startup['customer_id']}")
    print(f"  Subscription Acme:  {sub_acme['subscription_id']}")
    print(f"  Invoice:            {invoice['invoice_id']}")
    print(f"  Payment:            {payment['payment_intent_id']}")
    print(f"\n  Stored in: {STRIPE_DB_PATH}")
    print("\n  To connect to REAL Stripe:")
    print("  1. pip install stripe")
    print("  2. Set STRIPE_SECRET_KEY environment variable")
    print("  3. Replace StripeSimulator with real stripe.* calls")
    print("     (each method docstring shows the equivalent real call)")
    print()


if __name__ == "__main__":
    run_stripe_demo()
