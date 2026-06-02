"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║       Phase 8 — Integrations & Shipping | Project 05: Usage Billing & Metering ║
║                          billing.py — Billing Engine                            ║
║                                                                                 ║
║  PURPOSE: Track AI usage by token, calculate costs, generate professional       ║
║  invoices, and visualize consumption — the financial backbone of any AI SaaS.  ║
║                                                                                 ║
║  WHY BILLING MATTERS: AI APIs (OpenAI, Anthropic, Cohere) charge by token.     ║
║  If you're building a SaaS on top of these, you need to:                        ║
║  1. Track what each tenant uses (metering)                                      ║
║  2. Calculate what they owe (pricing)                                           ║
║  3. Generate invoices they can pay (billing)                                    ║
║  4. Show them their usage (dashboard)                                           ║
║  5. Forecast end-of-month costs (planning)                                      ║
║                                                                                 ║
║  TOKEN-BASED BILLING: Unlike per-request billing, token billing is fair —       ║
║  a "what did I actually compute?" pricing model. Long prompts cost more than    ║
║  short ones. This aligns cost with value delivered.                             ║
║                                                                                 ║
║  TECH: Python 3.11+, SQLite, FastAPI middleware, ASCII visualizations           ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import math
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import calendar
import random

# ─── Database path ────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "billing.db"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UsageEvent:
    """A single metered usage event — one LLM API call.

    WHY separate input and output tokens? Because they have different prices.
    Input tokens (your prompt) are cheaper to process — the model just reads them.
    Output tokens (the generated response) are more expensive — the model generates
    them auto-regressively, one token at a time.

    Real OpenAI pricing (May 2025):
    - GPT-4o: $5 input / $15 output per 1M tokens
    - GPT-4o-mini: $0.15 input / $0.60 output per 1M tokens

    We simulate Ollama costs at much lower rates since it runs locally.
    """
    tenant_id: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime
    cost_usd: float = 0.0
    request_id: Optional[str] = None


@dataclass
class InvoiceLineItem:
    """One line item on an invoice — e.g., 'gemma3:4b — 50,000 input tokens'."""
    description: str
    quantity: float
    unit: str
    unit_price: float  # USD per unit
    total: float


@dataclass
class Invoice:
    """A complete invoice for a tenant for a given month.

    WHY include tax? Most jurisdictions require sales tax on SaaS services.
    10% is a round number for demo purposes. Real products use services like
    Stripe Tax or Avalara to calculate jurisdiction-specific tax rates.
    """
    invoice_id: str
    tenant_id: str
    tenant_name: str
    month: int
    year: int
    line_items: list[InvoiceLineItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax_rate: float = 0.10  # 10% for demo
    tax: float = 0.0
    total: float = 0.0
    generated_at: datetime = field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PricingEngine:
    """Calculates the cost of LLM API calls.

    WHY per-1K-token pricing? It's the industry standard (OpenAI, Anthropic use
    per-million, but per-thousand is easier to think about at small scale).

    Real pricing philosophy:
    - Input tokens are cheaper: model just processes existing text (read-only)
    - Output tokens are expensive: model generates new text auto-regressively
    - Different models have wildly different costs (GPT-4 vs GPT-3.5: 10x)

    For Ollama (local), costs are simulated — in reality, local models cost
    only electricity (fractions of a cent). We simulate to teach the billing
    architecture, even if the dollar amounts aren't meaningful locally.
    """

    # Price table: dollars per 1,000 tokens
    # Format: {model_id: {input: price_per_1k, output: price_per_1k}}
    PRICE_TABLE: dict[str, dict[str, float]] = {
        "gemma3:4b": {
            "input": 0.0001,   # $0.0001 per 1K input tokens (~$0.10 per million)
            "output": 0.0003,  # $0.0003 per 1K output tokens (~$0.30 per million)
        },
        "llama3.2:3b": {
            "input": 0.00008,
            "output": 0.00025,
        },
        "mistral:7b": {
            "input": 0.00015,
            "output": 0.00045,
        },
        "codellama:7b": {
            "input": 0.00020,
            "output": 0.00060,
        },
        # Reference pricing for real APIs (not used in demo, but educational)
        "gpt-4o": {
            "input": 0.005,    # $5.00 per million input tokens
            "output": 0.015,   # $15.00 per million output tokens
        },
        "gpt-4o-mini": {
            "input": 0.00015,
            "output": 0.00060,
        },
        "claude-3-5-sonnet": {
            "input": 0.003,
            "output": 0.015,
        },
    }

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of a single LLM call.

        WHY return float (not Decimal)? For display/demo purposes, float is fine.
        In production billing systems, ALWAYS use Python's Decimal to avoid
        floating-point rounding errors that can cost or overcalculate fractions of cents.

        Example:
        >>> engine.calculate_cost("gemma3:4b", 1000, 500)
        0.00025  # ($0.0001 * 1) + ($0.0003 * 0.5)
        """
        if model not in self.PRICE_TABLE:
            # Unknown model — use a default price and log a warning
            print(f"  Warning: Unknown model '{model}'. Using default pricing.")
            pricing = {"input": 0.0001, "output": 0.0003}
        else:
            pricing = self.PRICE_TABLE[model]

        # Per-1K pricing: divide token count by 1000, multiply by price
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return round(input_cost + output_cost, 8)  # 8 decimal places for precision

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        WHY estimate instead of count exactly? Token counting requires
        loading a tokenizer (like tiktoken for GPT, or SentencePiece for Llama).
        For billing estimation, the approximation is accurate enough.

        The rule of thumb: 1 token ≈ 0.75 words (or ~4 characters)
        We use word_count * 1.3 to account for punctuation and subword tokens.

        For production: use tiktoken (OpenAI) or the model's specific tokenizer.

        Example:
        >>> engine.estimate_tokens("Hello world!")  # 2 words
        3  # 2 * 1.3 = 2.6 → 3
        """
        if not text:
            return 0
        word_count = len(text.split())
        return max(1, int(word_count * 1.3))

    def get_model_pricing(self, model: str) -> dict[str, float]:
        """Get pricing info for a model."""
        return self.PRICE_TABLE.get(model, {"input": 0.0001, "output": 0.0003})

    def list_models_with_pricing(self) -> list[dict]:
        """List all models with their pricing info."""
        result = []
        for model, prices in self.PRICE_TABLE.items():
            result.append({
                "model": model,
                "input_per_1k": prices["input"],
                "output_per_1k": prices["output"],
                "input_per_1m": prices["input"] * 1000,
                "output_per_1m": prices["output"] * 1000,
            })
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

class UsageDatabase:
    """SQLite-backed store for usage events.

    WHY not reuse the multi-tenant DB? In a microservices architecture,
    billing has its own database. Billing data has different retention
    requirements (often 7 years for legal/tax reasons) than operational data.

    In a monolith, you'd add these tables to the main DB. In a microservices
    setup, billing is usually a separate service with its own database.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables and seed demo usage data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id   TEXT    NOT NULL,
                    model       TEXT    NOT NULL,
                    input_tokens  INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd    REAL    NOT NULL DEFAULT 0,
                    timestamp   TEXT    NOT NULL,
                    request_id  TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants_billing (
                    tenant_id   TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    email       TEXT NOT NULL,
                    plan        TEXT NOT NULL DEFAULT 'pro'
                )
            """)
            conn.commit()

            # Seed demo data on first run
            count = conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
            if count == 0:
                print("Seeding demo billing data (30 days of usage)...")
                self._seed_demo_data(conn)

    def _seed_demo_data(self, conn: sqlite3.Connection) -> None:
        """Create 30 days of realistic usage data for 3 demo tenants."""
        pricing = PricingEngine()

        tenants = [
            ("acme-corp", "Acme Corp", "billing@acme-corp.example", "pro"),
            ("startup-inc", "Startup Inc", "billing@startup-inc.example", "free"),
            ("bigcorp", "BigCorp Enterprise", "billing@bigcorp.example", "enterprise"),
        ]

        # Seed tenant billing info
        for t in tenants:
            conn.execute(
                "INSERT OR IGNORE INTO tenants_billing VALUES (?, ?, ?, ?)", t
            )

        # Generate 30 days of usage events
        now = datetime.utcnow()
        events = []

        for tenant_id, name, _, plan in tenants:
            # Different usage patterns by plan
            if plan == "free":
                daily_requests = random.randint(2, 5)
            elif plan == "pro":
                daily_requests = random.randint(30, 80)
            else:  # enterprise
                daily_requests = random.randint(200, 500)

            for days_ago in range(30):
                day = now - timedelta(days=days_ago)
                # Simulate business hours (more usage Mon-Fri during work hours)
                requests_today = daily_requests + random.randint(-5, 10)
                requests_today = max(0, requests_today)

                for _ in range(requests_today):
                    # Randomize time within the day
                    hour = random.randint(7, 22)
                    minute = random.randint(0, 59)
                    ts = day.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    # Random model (mostly gemma3:4b, occasionally others)
                    model = random.choices(
                        ["gemma3:4b", "llama3.2:3b", "mistral:7b"],
                        weights=[0.7, 0.2, 0.1],
                    )[0]

                    # Realistic token counts
                    input_tokens = random.randint(50, 800)
                    output_tokens = random.randint(30, 400)
                    cost = pricing.calculate_cost(model, input_tokens, output_tokens)

                    events.append((
                        tenant_id, model, input_tokens, output_tokens,
                        cost, ts.isoformat()
                    ))

        conn.executemany(
            """INSERT INTO usage_events
               (tenant_id, model, input_tokens, output_tokens, cost_usd, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            events,
        )
        conn.commit()
        print(f"  ✓ Seeded {len(events)} usage events across 3 tenants, 30 days")

    def log_event(self, event: UsageEvent) -> None:
        """Persist a usage event to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO usage_events
                   (tenant_id, model, input_tokens, output_tokens, cost_usd, timestamp, request_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.tenant_id,
                    event.model,
                    event.input_tokens,
                    event.output_tokens,
                    event.cost_usd,
                    event.timestamp.isoformat(),
                    event.request_id,
                ),
            )
            conn.commit()

    def get_events_for_month(
        self, tenant_id: str, month: int, year: int
    ) -> list[UsageEvent]:
        """Get all usage events for a tenant in a given month."""
        # Calculate month boundaries
        _, last_day = calendar.monthrange(year, month)
        start = datetime(year, month, 1).isoformat()
        end = datetime(year, month, last_day, 23, 59, 59).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM usage_events
                   WHERE tenant_id = ?
                   AND timestamp >= ?
                   AND timestamp <= ?
                   ORDER BY timestamp""",
                (tenant_id, start, end),
            ).fetchall()

        return [
            UsageEvent(
                tenant_id=row["tenant_id"],
                model=row["model"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                cost_usd=row["cost_usd"],
            )
            for row in rows
        ]

    def get_all_tenants(self) -> list[dict]:
        """Get all billing tenant records."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM tenants_billing").fetchall()
        return [dict(r) for r in rows]

    def get_monthly_totals_by_day(
        self, tenant_id: str, month: int, year: int
    ) -> dict[str, dict]:
        """Get usage totals grouped by day of month."""
        events = self.get_events_for_month(tenant_id, month, year)
        by_day: dict[str, dict] = {}

        for event in events:
            day_key = event.timestamp.strftime("%Y-%m-%d")
            if day_key not in by_day:
                by_day[day_key] = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0}
            by_day[day_key]["requests"] += 1
            by_day[day_key]["input_tokens"] += event.input_tokens
            by_day[day_key]["output_tokens"] += event.output_tokens
            by_day[day_key]["cost"] += event.cost_usd

        return by_day


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI MIDDLEWARE — METERING
# ═══════════════════════════════════════════════════════════════════════════════

# NOTE: This middleware is defined here for use in any FastAPI app.
# To use it, add: app.add_middleware(MeteringMiddleware)
# The middleware intercepts every /chat request automatically.
# Import in your main.py: from billing import MeteringMiddleware, UsageDatabase

try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    import json as _json

    class MeteringMiddleware(BaseHTTPMiddleware):
        """FastAPI middleware that automatically meters every /chat request.

        WHY use middleware instead of logging inside the endpoint?
        Middleware runs around the endpoint — you can't forget to add logging
        to a new endpoint. It's automatic, consistent, and keeps billing logic
        out of business logic.

        HOW IT WORKS:
        1. Intercepts the request before it reaches the endpoint
        2. Records the request body (to estimate input tokens)
        3. Lets the endpoint process normally
        4. Intercepts the response
        5. Estimates token usage from request + response
        6. Logs a UsageEvent to the database

        LIMITATION: For streaming responses, you'd need to buffer the chunks
        and count after the stream completes. This example handles non-streaming.
        """

        def __init__(self, app, usage_db: "UsageDatabase", pricing: "PricingEngine"):
            super().__init__(app)
            self.usage_db = usage_db
            self.pricing = pricing

        async def dispatch(self, request: Request, call_next):
            # Only meter /chat endpoints
            if not request.url.path.endswith("/chat"):
                return await call_next(request)

            # Read the request body to estimate input tokens
            body_bytes = await request.body()
            try:
                body_json = _json.loads(body_bytes)
                message = body_json.get("message", "")
            except Exception:
                message = ""

            # Process the request normally
            response = await call_next(request)

            # Estimate tokens and log (fire-and-forget in production)
            # Note: reading response body here requires buffering — see stripe_integration.py
            # for the production pattern using response.body()
            input_tokens = self.pricing.estimate_tokens(message)
            output_tokens = input_tokens // 2  # rough estimate for middleware

            # Extract tenant_id from the JWT if available
            tenant_id = "unknown"
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                try:
                    from jose import jwt as jose_jwt
                    SECRET_KEY = os.getenv("SECRET_KEY", "phase8-multitenant-demo-secret-change-in-production")
                    payload = jose_jwt.decode(
                        auth[7:], SECRET_KEY, algorithms=["HS256"]
                    )
                    tenant_id = str(payload.get("tenant_id", "unknown"))
                except Exception:
                    pass

            event = UsageEvent(
                tenant_id=tenant_id,
                model="gemma3:4b",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                timestamp=datetime.utcnow(),
                cost_usd=self.pricing.calculate_cost("gemma3:4b", input_tokens, output_tokens),
            )
            self.usage_db.log_event(event)

            return response

except ImportError:
    # FastAPI not installed — that's fine for billing.py used standalone
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# INVOICE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class InvoiceGenerator:
    """Generates professional invoices from usage data.

    WHY generate invoices programmatically? Real billing systems generate
    invoices from metering data automatically — no manual data entry.
    This is what Stripe Billing, Chargebee, and Recurly do under the hood:
    collect usage events → aggregate → generate invoice → charge the customer.
    """

    def __init__(self, usage_db: UsageDatabase, pricing: PricingEngine):
        self.usage_db = usage_db
        self.pricing = pricing

    def generate_invoice(self, tenant_id: str, month: int, year: int) -> Invoice:
        """Generate an invoice for a tenant for a specific month.

        Aggregates all usage events into line items by model, calculates
        subtotal, adds tax, and produces the final Invoice object.
        """
        # Get all usage events for this tenant and month
        events = self.usage_db.get_events_for_month(tenant_id, month, year)

        # Get tenant info
        tenants = {t["tenant_id"]: t for t in self.usage_db.get_all_tenants()}
        tenant = tenants.get(tenant_id, {"name": tenant_id, "email": "unknown"})

        # Aggregate by model
        # WHY aggregate? Invoices show "gemma3:4b — 50,000 tokens" not one row per request
        model_usage: dict[str, dict] = {}
        for event in events:
            if event.model not in model_usage:
                model_usage[event.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                }
            model_usage[event.model]["input_tokens"] += event.input_tokens
            model_usage[event.model]["output_tokens"] += event.output_tokens
            model_usage[event.model]["total_cost"] += event.cost_usd

        # Build line items
        line_items: list[InvoiceLineItem] = []

        for model, usage in model_usage.items():
            pricing = self.pricing.get_model_pricing(model)

            # Input tokens line item
            if usage["input_tokens"] > 0:
                line_items.append(InvoiceLineItem(
                    description=f"{model} — Input tokens",
                    quantity=usage["input_tokens"],
                    unit="tokens",
                    unit_price=pricing["input"] / 1000,  # per-token price
                    total=round((usage["input_tokens"] / 1000) * pricing["input"], 6),
                ))

            # Output tokens line item
            if usage["output_tokens"] > 0:
                line_items.append(InvoiceLineItem(
                    description=f"{model} — Output tokens",
                    quantity=usage["output_tokens"],
                    unit="tokens",
                    unit_price=pricing["output"] / 1000,
                    total=round((usage["output_tokens"] / 1000) * pricing["output"], 6),
                ))

        subtotal = sum(item.total for item in line_items)
        tax = round(subtotal * 0.10, 4)
        total = round(subtotal + tax, 4)

        month_name = calendar.month_name[month]
        invoice_id = f"INV-{year}-{month:02d}-{tenant_id.upper()[:6]}"

        return Invoice(
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            tenant_name=tenant["name"],
            month=month,
            year=year,
            line_items=line_items,
            subtotal=round(subtotal, 4),
            tax=tax,
            total=total,
        )

    def render_invoice(self, invoice: Invoice) -> str:
        """Render an Invoice as an ASCII-formatted string.

        WHY ASCII? It's universally readable — can be emailed as plain text,
        logged, printed, or displayed in a terminal. Real systems also generate
        PDFs (using WeasyPrint, ReportLab, or a PDF service like Anvil).
        """
        month_name = calendar.month_name[invoice.month]
        width = 68

        lines = []
        lines.append("┌" + "─" * (width - 2) + "┐")
        lines.append(f"│{'INVOICE':^{width-2}}│")
        lines.append("├" + "─" * (width - 2) + "┤")
        lines.append(f"│  Invoice #: {invoice.invoice_id:<{width-16}}│")
        lines.append(f"│  Tenant:    {invoice.tenant_name:<{width-16}}│")
        lines.append(f"│  Period:    {month_name} {invoice.year:<{width-23}}│")
        lines.append(f"│  Generated: {invoice.generated_at.strftime('%Y-%m-%d %H:%M UTC'):<{width-16}}│")
        lines.append("├" + "─" * (width - 2) + "┤")
        lines.append(f"│  {'DESCRIPTION':<32} {'QTY':>12} {'UNIT $':>8} {'TOTAL':>8}│")
        lines.append("├" + "─" * (width - 2) + "┤")

        if not invoice.line_items:
            lines.append(f"│  {'No usage recorded for this period':<{width-4}}│")
        else:
            for item in invoice.line_items:
                desc = item.description[:32]
                qty = f"{item.quantity:,}"
                unit_price = f"${item.unit_price:.7f}"
                total = f"${item.total:.4f}"
                lines.append(f"│  {desc:<32} {qty:>12} {unit_price:>8} {total:>8}│")

        lines.append("├" + "─" * (width - 2) + "┤")
        lines.append(f"│  {'Subtotal':<48} ${invoice.subtotal:>9.4f}  │")
        lines.append(f"│  {'Tax (10%)':<48} ${invoice.tax:>9.4f}  │")
        lines.append("├" + "─" * (width - 2) + "┤")
        lines.append(f"│  {'TOTAL DUE':<48} ${invoice.total:>9.4f}  │")
        lines.append("└" + "─" * (width - 2) + "┘")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING DASHBOARD
# ASCII visualizations of usage data.
# ═══════════════════════════════════════════════════════════════════════════════

class BillingDashboard:
    """Provides usage visualizations for tenants and admins.

    WHY ASCII charts? They work everywhere — terminals, log files, Slack messages,
    CI/CD outputs. Libraries like rich, plotext, or uniplot give nicer charts,
    but pure ASCII ensures zero dependencies and maximum portability.

    In production you'd use Grafana, Metabase, or a custom React dashboard.
    These ASCII charts are the "API response" that feeds those visualizations.
    """

    def __init__(self, usage_db: UsageDatabase, pricing: PricingEngine):
        self.usage_db = usage_db
        self.pricing = pricing

    def monthly_summary(self, tenant_id: str, month: Optional[int] = None, year: Optional[int] = None) -> str:
        """Generate an ASCII bar chart of daily usage for a tenant.

        The bar chart uses Unicode block characters for visual appeal while
        still being renderable in any UTF-8 terminal.
        """
        now = datetime.utcnow()
        month = month or now.month
        year = year or now.year

        by_day = self.usage_db.get_monthly_totals_by_day(tenant_id, month, year)

        if not by_day:
            return f"No usage data for {tenant_id} in {calendar.month_name[month]} {year}"

        # Get all days in the month
        _, last_day = calendar.monthrange(year, month)

        # Build the chart
        max_requests = max((d["requests"] for d in by_day.values()), default=1)
        bar_width = 20  # Character width of bars

        lines = []
        month_name = calendar.month_name[month]
        lines.append(f"\n  DAILY USAGE — {tenant_id} — {month_name} {year}")
        lines.append("  " + "─" * 60)

        for day_num in range(1, last_day + 1):
            day_key = f"{year}-{month:02d}-{day_num:02d}"
            data = by_day.get(day_key, {"requests": 0, "cost": 0.0})
            count = data["requests"]
            cost = data["cost"]

            # Calculate bar length proportional to max
            bar_len = int((count / max_requests) * bar_width) if max_requests > 0 else 0
            bar = "█" * bar_len + "░" * (bar_width - bar_len)

            # Highlight today
            is_today = (
                day_num == now.day and month == now.month and year == now.year
            )
            today_marker = " ← TODAY" if is_today else ""

            lines.append(
                f"  {day_num:2d} │{bar}│ {count:4d} reqs  ${cost:.4f}{today_marker}"
            )

        # Summary row
        total_reqs = sum(d["requests"] for d in by_day.values())
        total_cost = sum(d["cost"] for d in by_day.values())
        lines.append("  " + "─" * 60)
        lines.append(f"  Total: {total_reqs} requests | ${total_cost:.4f} this month")

        return "\n".join(lines)

    def top_consumers(self, month: Optional[int] = None, year: Optional[int] = None) -> str:
        """Ranked list of tenants by usage cost for the month.

        WHY this view? Platform operators need to know which tenants are driving
        costs — both for billing verification and capacity planning.
        """
        now = datetime.utcnow()
        month = month or now.month
        year = year or now.year

        tenants = self.usage_db.get_all_tenants()
        ranked = []

        for tenant in tenants:
            events = self.usage_db.get_events_for_month(tenant["tenant_id"], month, year)
            total_cost = sum(e.cost_usd for e in events)
            total_requests = len(events)
            total_tokens = sum(e.input_tokens + e.output_tokens for e in events)

            ranked.append({
                "tenant_id": tenant["tenant_id"],
                "name": tenant["name"],
                "plan": tenant["plan"],
                "total_cost": total_cost,
                "total_requests": total_requests,
                "total_tokens": total_tokens,
            })

        # Sort by cost descending
        ranked.sort(key=lambda x: x["total_cost"], reverse=True)

        lines = []
        month_name = calendar.month_name[month]
        lines.append(f"\n  TOP CONSUMERS — {month_name} {year}")
        lines.append("  " + "─" * 75)
        lines.append(f"  {'#':<3} {'TENANT':<25} {'PLAN':<12} {'REQUESTS':>10} {'TOKENS':>12} {'COST':>10}")
        lines.append("  " + "─" * 75)

        total_platform_cost = 0.0
        for i, t in enumerate(ranked, 1):
            total_platform_cost += t["total_cost"]
            lines.append(
                f"  {i:<3} {t['name']:<25} {t['plan']:<12} {t['total_requests']:>10,} "
                f"{t['total_tokens']:>12,} ${t['total_cost']:>9.4f}"
            )

        lines.append("  " + "─" * 75)
        lines.append(f"  {'PLATFORM TOTAL':<40} ${total_platform_cost:>9.4f}")

        return "\n".join(lines)

    def cost_forecast(self, tenant_id: str) -> str:
        """Forecast end-of-month cost based on current usage trajectory.

        WHY forecast? Tenants want to know if they'll exceed their budget.
        Operators want to know expected revenue for the month.

        METHOD: Simple linear projection — current spend / days elapsed * total days.
        More sophisticated methods: moving average, day-of-week adjustment.
        Real tools like Stripe use ML for more accurate forecasts.
        """
        now = datetime.utcnow()
        month = now.month
        year = now.year
        _, last_day = calendar.monthrange(year, month)

        events = self.usage_db.get_events_for_month(tenant_id, month, year)
        actual_cost = sum(e.cost_usd for e in events)
        actual_requests = len(events)

        # Calculate elapsed days (at least 1 to avoid division by zero)
        elapsed_days = max(1, now.day)
        remaining_days = last_day - elapsed_days

        # Linear projection
        daily_rate = actual_cost / elapsed_days
        projected_remaining = daily_rate * remaining_days
        projected_total = actual_cost + projected_remaining

        lines = []
        lines.append(f"\n  COST FORECAST — {tenant_id} — {calendar.month_name[month]} {year}")
        lines.append("  " + "─" * 50)
        lines.append(f"  Days elapsed:          {elapsed_days}/{last_day}")
        lines.append(f"  Days remaining:        {remaining_days}")
        lines.append(f"  Requests to date:      {actual_requests:,}")
        lines.append(f"  Actual cost to date:   ${actual_cost:.4f}")
        lines.append(f"  Daily run rate:        ${daily_rate:.4f}/day")
        lines.append(f"  Projected remaining:   ${projected_remaining:.4f}")
        lines.append("  " + "─" * 50)
        lines.append(f"  PROJECTED MONTH TOTAL: ${projected_total:.4f}")

        # Confidence indicator
        if elapsed_days < 5:
            lines.append("  ⚠️  Low confidence (< 5 days of data)")
        elif elapsed_days < 15:
            lines.append("  🟡 Medium confidence (< half month elapsed)")
        else:
            lines.append("  🟢 High confidence (> half month of data)")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE DEMO
# ═══════════════════════════════════════════════════════════════════════════════

def run_billing_demo() -> None:
    """Interactive demo of the billing system."""
    print("\n" + "═" * 68)
    print("  BILLING & METERING SYSTEM — Phase 8 Project 05")
    print("═" * 68)

    # Initialize components
    db = UsageDatabase()
    pricing = PricingEngine()
    invoice_gen = InvoiceGenerator(db, pricing)
    dashboard = BillingDashboard(db, pricing)

    tenants = db.get_all_tenants()
    tenant_ids = [t["tenant_id"] for t in tenants]

    now = datetime.utcnow()

    while True:
        print("\n" + "─" * 50)
        print("  BILLING DASHBOARD — MAIN MENU")
        print("─" * 50)
        print("  [1] View monthly usage chart (ASCII bar chart)")
        print("  [2] Top consumers this month")
        print("  [3] Generate invoice")
        print("  [4] Cost forecast")
        print("  [5] List models & pricing")
        print("  [6] Log a new usage event")
        print("  [7] Quit")
        print("─" * 50)

        choice = input("  Choose [1-7]: ").strip()

        if choice == "1":
            print(f"\n  Available tenants: {', '.join(tenant_ids)}")
            tid = input("  Tenant ID: ").strip()
            if tid in tenant_ids:
                print(dashboard.monthly_summary(tid, now.month, now.year))
            else:
                print(f"  Unknown tenant '{tid}'")

        elif choice == "2":
            print(dashboard.top_consumers(now.month, now.year))

        elif choice == "3":
            print(f"\n  Available tenants: {', '.join(tenant_ids)}")
            tid = input("  Tenant ID: ").strip()
            if tid in tenant_ids:
                invoice = invoice_gen.generate_invoice(tid, now.month, now.year)
                print("\n" + invoice_gen.render_invoice(invoice))
            else:
                print(f"  Unknown tenant '{tid}'")

        elif choice == "4":
            print(f"\n  Available tenants: {', '.join(tenant_ids)}")
            tid = input("  Tenant ID: ").strip()
            if tid in tenant_ids:
                print(dashboard.cost_forecast(tid))
            else:
                print(f"  Unknown tenant '{tid}'")

        elif choice == "5":
            print("\n  MODEL PRICING TABLE")
            print("  " + "─" * 70)
            print(f"  {'MODEL':<25} {'INPUT/1K':>10} {'OUTPUT/1K':>12} {'INPUT/1M':>12} {'OUTPUT/1M':>12}")
            print("  " + "─" * 70)
            for m in pricing.list_models_with_pricing():
                print(
                    f"  {m['model']:<25} ${m['input_per_1k']:>9.5f} ${m['output_per_1k']:>11.5f} "
                    f"${m['input_per_1m']:>11.4f} ${m['output_per_1m']:>11.4f}"
                )

        elif choice == "6":
            print(f"\n  Available tenants: {', '.join(tenant_ids)}")
            tid = input("  Tenant ID: ").strip()
            model = input("  Model (e.g. gemma3:4b): ").strip() or "gemma3:4b"
            text = input("  Sample text to estimate tokens: ").strip()

            input_tokens = pricing.estimate_tokens(text)
            output_tokens = input_tokens // 2
            cost = pricing.calculate_cost(model, input_tokens, output_tokens)

            event = UsageEvent(
                tenant_id=tid,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                timestamp=datetime.utcnow(),
                cost_usd=cost,
            )
            db.log_event(event)
            print(f"\n  ✓ Logged: {input_tokens} input + {output_tokens} output tokens = ${cost:.6f}")

        elif choice == "7":
            print("\n  Goodbye!\n")
            break

        else:
            print("  Invalid choice — please enter 1-7")


if __name__ == "__main__":
    import os
    run_billing_demo()
