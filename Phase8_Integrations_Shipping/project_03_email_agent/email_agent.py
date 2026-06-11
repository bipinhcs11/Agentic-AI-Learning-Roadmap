"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║          Phase 8 — Integrations & Shipping | Project 03: Email Intelligence    ║
║                          email_agent.py — Main Implementation                  ║
║                                                                                ║
║  PURPOSE: An AI agent that reads emails, classifies them by category and        ║
║  priority, drafts professional replies, and generates a daily digest.           ║
║                                                                                ║
║  WHY SIMULATE EMAILS? Real Gmail/Outlook APIs require OAuth2 app registration   ║
║  and approval. Simulating locally lets us focus on the agent architecture —     ║
║  the same logic plugs directly into real APIs (see README for how).             ║
║                                                                                ║
║  ARCHITECTURE:                                                                  ║
║    EmailDatabase  ──→  stores/retrieves emails (SQLite)                        ║
║    EmailClassifier ──→  LLM classifies category, priority, sentiment           ║
║    ReplyDrafter    ──→  LLM drafts professional reply                          ║
║    DigestGenerator ──→  LLM summarizes inbox into daily digest                 ║
║    EmailAgent      ──→  orchestrates all components, provides interactive UI   ║
║                                                                                ║
║  TECH: Python 3.11+, SQLite, OpenAI client → Ollama, Rich terminal UI          ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import sqlite3
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from openai import OpenAI

# ─── Ollama client setup ─────────────────────────────────────────────────────
# We use the OpenAI-compatible API that Ollama exposes. This lets us swap
# between Ollama (local, free) and real OpenAI (cloud) by changing the base_url
# and api_key — zero code changes required.
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama ignores this but the client requires it
)
MODEL = "gemma3:4b"  # Lightweight model that runs on consumer hardware

# ─── Database path ────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "emails.db"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODEL
# Using dataclass instead of Pydantic here because we want a simple,
# stdlib-only data container. Pydantic adds validation overhead we don't need
# for a local demo — but in production you'd use Pydantic for API boundaries.
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Email:
    """Represents a single email message.

    WHY store labels as a list? Emails can belong to multiple categories
    simultaneously — e.g. an email can be both "support" AND "urgent".
    Using a list in SQLite (JSON serialized) is the simplest approach.
    In a real system you'd have a separate email_labels join table.
    """
    id: int
    from_addr: str
    subject: str
    body: str
    timestamp: datetime
    labels: list[str] = field(default_factory=list)
    processed: bool = False
    category: Optional[str] = None
    priority: Optional[str] = None
    sentiment: Optional[str] = None
    requires_reply: bool = False


@dataclass
class Classification:
    """Result of classifying an email.

    We return a structured object (not just a dict) so callers get
    type hints and IDE autocomplete. The LLM returns JSON which we
    parse into this dataclass.
    """
    category: str      # support | sales | spam | newsletter | urgent | meeting | other
    priority: str      # high | medium | low
    sentiment: str     # positive | neutral | negative | mixed
    requires_reply: bool
    reason: str        # Human-readable explanation — helps with debugging LLM decisions


# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE EMAIL DATA
# 20 realistic emails covering all the categories we classify.
# Mixing realistic sender names, subjects, and bodies gives the LLM
# enough context to make meaningful classification decisions.
# ═══════════════════════════════════════════════════════════════════════════════

SAMPLE_EMAILS = [
    {
        "from_addr": "alice.johnson@techcorp.com",
        "subject": "URGENT: Production database down!",
        "body": """Hi team,

Our production database has been throwing connection errors for the last 20 minutes.
All customer-facing features are broken. Error: "max_connections exceeded" on postgres.

I've tried restarting the app servers but it didn't help. We're losing ~$5000/minute
in potential revenue and customers are complaining on Twitter.

Please escalate immediately. On-call engineer contact: +1-555-0192.

This needs to be fixed NOW.

Alice Johnson
CTO, TechCorp""",
        "labels": [],
        "hours_ago": 1,
    },
    {
        "from_addr": "sales@quantumleap.io",
        "subject": "Partnership opportunity — 40% revenue share",
        "body": """Hello,

I'm reaching out from QuantumLeap.io. We help SaaS companies like yours grow
their revenue by 3x in 6 months through our AI-powered sales automation platform.

We'd love to explore a partnership. We offer:
- 40% revenue share on all referred customers
- Co-marketing opportunities
- Joint webinars to our 50,000-subscriber list

Would you have 30 minutes next week for a quick call?

Best,
Marcus Rivera
VP Partnerships, QuantumLeap""",
        "labels": [],
        "hours_ago": 3,
    },
    {
        "from_addr": "noreply@medium.com",
        "subject": "Top stories for you this week — AI, Python, and SaaS",
        "body": """Your weekly digest from Medium

Stories curated for you:
• "How I built a $10M SaaS in 18 months" — 12 min read
• "Python asyncio: the definitive guide" — 8 min read
• "Why most AI startups fail (and how to avoid it)" — 6 min read
• "Postgres vs MySQL in 2025" — 5 min read

Read on Medium → medium.com/personalized

To unsubscribe, click here.
Medium, 548 Market St, San Francisco, CA 94104""",
        "labels": [],
        "hours_ago": 6,
    },
    {
        "from_addr": "bob.smith@clientco.com",
        "subject": "Question about your Enterprise plan",
        "body": """Hi,

I'm evaluating your platform for our team of 200 engineers. I had a few questions:

1. Does the Enterprise plan include SSO with Okta?
2. Can we get a dedicated account manager?
3. What's your SLA for P1 incidents?
4. Do you have a SOC 2 Type II certification?
5. Can we host on our own AWS account (BYOC)?

We're comparing you against two other vendors and need to make a decision by end
of month. Budget is approved. Looking forward to your response.

Bob Smith
Engineering Director, ClientCo""",
        "labels": [],
        "hours_ago": 8,
    },
    {
        "from_addr": "winner@lottery-global.win",
        "subject": "CONGRATULATIONS! You've won $2,500,000!!!",
        "body": """DEAR LUCKY WINNER!!!

You have been SELECTED as our GRAND PRIZE WINNER of TWO MILLION FIVE HUNDRED
THOUSAND US DOLLARS ($2,500,000.00) in our monthly draw!

To claim your prize, you must:
1. Send us your full name, address, and bank account details
2. Pay a small processing fee of $250 via Western Union

DO NOT TELL ANYONE about this prize until funds are transferred!

Contact our claims agent: Mr. Emmanuel Okafor at claims@lottery-global.win

CONGRATULATIONS AGAIN!!!""",
        "labels": [],
        "hours_ago": 2,
    },
    {
        "from_addr": "sarah.lee@startup.dev",
        "subject": "Can we schedule a product demo?",
        "body": """Hi there,

I'm the Head of Product at Startup.dev. We're a Series A startup (just raised $8M)
looking for a reliable AI infrastructure solution.

I saw your product mentioned in the "Top AI Tools 2025" roundup and was impressed
by the pricing and feature set.

Could we schedule a 45-minute demo? I'm available:
- Tuesday May 20, 2pm-5pm EST
- Wednesday May 21, 10am-12pm EST
- Thursday May 22, anytime after 3pm EST

Please include your sales engineer if possible — we'll have technical questions.

Thanks,
Sarah Lee""",
        "labels": [],
        "hours_ago": 12,
    },
    {
        "from_addr": "support@zapier.com",
        "subject": "Your Zap failed 47 times in the last hour",
        "body": """Hi,

We noticed your Zap "New GitHub Issue → Slack notification" failed 47 times in
the last hour.

Error details:
  Step 2 (Slack): channel_not_found — The channel #dev-alerts no longer exists

This may have happened because the Slack channel was deleted or renamed.

To fix this:
1. Open your Zap in the editor
2. Update Step 2 to use a valid Slack channel
3. Turn your Zap back on

If you need help, reply to this email or visit our support docs.

The Zapier Team""",
        "labels": [],
        "hours_ago": 4,
    },
    {
        "from_addr": "newsletter@tldr.tech",
        "subject": "TLDR: OpenAI's new model beats GPT-5, Python 3.14 released",
        "body": """TLDR — Daily Tech Newsletter | May 21, 2026

TODAY'S TOP STORIES:

🤖 AI: OpenAI releases o4-mini with 2M context window. Benchmarks show 15%
improvement over previous SOTA on coding tasks. Available via API now.

🐍 PYTHON: Python 3.14 officially released with experimental JIT compiler.
Early benchmarks show 25-40% speedup on CPU-bound tasks.

💰 STARTUPS: Y Combinator W26 batch raises record $3.2B total in first 6 months.
AI and climate tech dominate the cohort.

🔒 SECURITY: Critical CVE in OpenSSL affects 40% of web servers. Patch now.

To unsubscribe: tldr.tech/unsubscribe
TLDR, Inc. | 340 Pine St, San Francisco, CA 94104""",
        "labels": [],
        "hours_ago": 7,
    },
    {
        "from_addr": "david.chen@bigenterprise.com",
        "subject": "Meeting request: AI strategy alignment — Fri May 24",
        "body": """Hi,

As discussed in our last call, I'd like to schedule a follow-up meeting to align
on our AI strategy for Q3.

Proposed agenda:
1. Review of Q2 AI pilot results (15 min)
2. Q3 roadmap priorities (20 min)
3. Budget allocation discussion (15 min)
4. Next steps and owners (10 min)

Proposed time: Friday May 24, 2026 at 2:00 PM EST (60 minutes)
Location: Zoom (link will follow)

Please confirm attendance. I'll also invite our CTO and CISO.

Best regards,
David Chen
VP Technology, BigEnterprise Corp""",
        "labels": [],
        "hours_ago": 18,
    },
    {
        "from_addr": "priya.patel@acmecustomer.com",
        "subject": "API returning 500 errors since this morning — BLOCKING us",
        "body": """Hello support team,

We're experiencing consistent 500 Internal Server errors from your REST API
since approximately 9 AM EST today. This is affecting our production pipeline.

Endpoint: POST /v2/embeddings
Error: {"error": "Internal server error", "request_id": "req_8xk2mNp"}
Frequency: 100% failure rate (was working fine yesterday)
Impact: Our ML pipeline is completely down. 8 engineers are blocked.

We have an investor demo in 4 hours. Please help ASAP.

Priya Patel
Lead Engineer, AcmeCustomer Inc.
Ticket ref: TKT-20481""",
        "labels": [],
        "hours_ago": 5,
    },
    {
        "from_addr": "noreply@github.com",
        "subject": "[GitHub] Your PR #142 was merged",
        "body": """Your pull request was merged.

Repository: yourorg/your-repo
PR #142: feat: add streaming support for chat completions
Merged by: @sarah-tech

The following branches can now be safely deleted:
• feature/streaming-chat

View the merged pull request:
https://github.com/yourorg/your-repo/pull/142

Thanks for contributing to yourorg/your-repo!
GitHub""",
        "labels": [],
        "hours_ago": 22,
    },
    {
        "from_addr": "legal@competitor.com",
        "subject": "Cease and desist — trademark infringement",
        "body": """NOTICE OF TRADEMARK INFRINGEMENT

Dear Sir/Madam,

Our client, Competitor Corp, is the registered owner of the trademark "AskAI Pro"
(Registration No. 7,291,847, filed January 15, 2024).

It has come to our attention that your company is using a confusingly similar
mark "AskMyDocs Pro" in connection with similar AI services.

We hereby demand that you:
1. Immediately cease all use of the infringing mark
2. Confirm in writing within 10 business days that you have complied
3. Provide an accounting of all revenue derived from the infringing use

Failure to comply may result in legal action seeking injunctive relief and damages.

This is a serious matter that requires your immediate attention.

Regards,
James Morrison, Esq.
Morrison & Associates LLP""",
        "labels": [],
        "hours_ago": 30,
    },
    {
        "from_addr": "carlos.mendez@potential-partner.com",
        "subject": "Interested in white-labeling your AI platform",
        "body": """Hi,

I'm Carlos, CEO of Potential Partner Inc. We build vertical SaaS for the legal
industry (50,000 lawyers use our tools daily).

We're very interested in white-labeling your AI platform to offer our customers
AI-powered document analysis. This would be a significant contract — potentially
$500K+ ARR.

Questions:
- Do you offer white-label/OEM licensing?
- What's your enterprise pricing model?
- Can we have a technical deep-dive with your team?

I'm happy to sign an NDA before we get into details.

Carlos Mendez
CEO, Potential Partner Inc.""",
        "labels": [],
        "hours_ago": 36,
    },
    {
        "from_addr": "newsletter@substack.com",
        "subject": "The Pragmatic Engineer: How big tech builds internal AI tools",
        "body": """The Pragmatic Engineer | Weekly Issue #312

How Big Tech Actually Uses AI Internally

This week I interviewed 12 engineers at FAANG companies about their internal
AI tooling. Key findings:

1. Code review automation is #1 use case — all 12 companies have it
2. Copilot adoption is ~80% among engineers, but productivity gains vary wildly
3. The bottleneck isn't the AI — it's the prompting skills of engineers
4. Internal "AI Centers of Excellence" are a common failure mode

Full analysis and interviews: pragmaticengineer.substack.com/p/big-tech-ai

——
Gergely Orosz | The Pragmatic Engineer
300,000+ subscribers | Unsubscribe at footer""",
        "labels": [],
        "hours_ago": 48,
    },
    {
        "from_addr": "tom.baker@startup.io",
        "subject": "Quick question about your Python SDK",
        "body": """Hey,

Love your product! Quick question:

I'm using your Python SDK v2.3.1 and I can't figure out how to set a timeout
on the embedding calls. The docs show a `timeout` parameter but it seems to be
ignored — the call hangs forever when the server is slow.

Here's my code:
  client = YourSDK(api_key="...", timeout=30)
  result = client.embed("hello world")  # still hangs after 30 seconds!

Is this a known bug? Is there a workaround?

Thanks,
Tom""",
        "labels": [],
        "hours_ago": 14,
    },
    {
        "from_addr": "billing@stripe.com",
        "subject": "Invoice #INV-2026-05 for $4,850.00 due June 1",
        "body": """Invoice from Stripe

Invoice #: INV-2026-05
Date: May 21, 2026
Due: June 1, 2026

Bill to: Your Company Inc.
Account: acct_1Mx6Aa2eZvKYlo

Line items:
  Stripe Payments (0.25% + $0.05/transaction)   $3,200.00
  Stripe Billing (0.5% of recurring revenue)      $950.00
  Stripe Radar (Advanced fraud protection)         $700.00
                                          ──────────────
  Total:                                         $4,850.00

Payment will be automatically charged to Visa ending in 4242 on June 1.

View invoice: dashboard.stripe.com/invoices/INV-2026-05""",
        "labels": [],
        "hours_ago": 20,
    },
    {
        "from_addr": "recruiter@bigtech.com",
        "subject": "Exciting opportunity — Staff Engineer at BigTech ($350K TC)",
        "body": """Hi there,

I'm a technical recruiter at BigTech. I came across your profile and was
impressed by your work in AI infrastructure.

We're hiring Staff Engineers for our AI Platform team:
- Total comp: $350K-$420K (base + RSUs + bonus)
- Remote-first, with quarterly team offsites
- Working on AI products used by 500M+ users

Would you be open to a quick 20-minute intro call this week?

Best,
Jennifer Park
Technical Recruiter, BigTech
jennifer.park@bigtech.com | (415) 555-0187""",
        "labels": [],
        "hours_ago": 26,
    },
    {
        "from_addr": "ops@cloudprovider.com",
        "subject": "[RESOLVED] Network degradation in us-east-1 — Post-incident report",
        "body": """Service Health Update — Resolved

INCIDENT: Network degradation affecting us-east-1 region
DURATION: 47 minutes (14:22 - 15:09 EST, May 20, 2026)
STATUS: RESOLVED

IMPACT: ~15% of API requests in us-east-1 experienced elevated latency (P99 > 5s)

ROOT CAUSE: A misconfigured BGP route advertisement caused traffic to be routed
suboptimally through our European PoPs, adding significant round-trip latency.

RESOLUTION: BGP configuration corrected; traffic returned to normal routing.

PREVENTION:
• Added BGP configuration validation to deployment pipeline
• Increased automated monitoring coverage for route announcements
• Updated runbook with faster rollback procedure

We apologize for the inconvenience.
Cloud Provider Operations Team""",
        "labels": [],
        "hours_ago": 33,
    },
    {
        "from_addr": "feedback@typeform.com",
        "subject": "🌟 New response on your customer satisfaction survey",
        "body": """You have a new response!

Survey: Customer Satisfaction — Q2 2026
Respondent: Anonymous

Q1: How satisfied are you with our product? (1-10)
A: 9

Q2: What do you like most?
A: The API is incredibly well-designed and the documentation is excellent.
   Response times are consistently fast and the pricing is very fair.

Q3: What could be improved?
A: Would love better search within the docs. Also a Python async client would
   be amazing — the sync client blocks our event loop.

Q4: Would you recommend us to a colleague?
A: Absolutely! Already told 3 friends about it.

NPS Score: 9

View all responses: typeform.com/results""",
        "labels": [],
        "hours_ago": 40,
    },
    {
        "from_addr": "admin@hackernews-digest.com",
        "subject": "Top HN posts this week: AI coding assistants, Rust in Linux kernel",
        "body": """Hacker News Weekly Digest | Week of May 19-25, 2026

TOP POSTS THIS WEEK:

1. "Claude 4 achieves 92% on SWE-bench" (847 points, 312 comments)
   news.ycombinator.com/item?id=38291847

2. "Rust is now the third language in the Linux kernel" (734 points, 189 comments)
   news.ycombinator.com/item?id=38289234

3. "I replaced my entire backend with a single SQLite file" (692 points, 445 comments)
   news.ycombinator.com/item?id=38287621

4. "Why I'm leaving Silicon Valley after 15 years" (589 points, 762 comments)
   news.ycombinator.com/item?id=38285012

5. "Ask HN: What's the best way to learn distributed systems in 2026?" (412 points)
   news.ycombinator.com/item?id=38282901

Unsubscribe: hackernews-digest.com/unsubscribe""",
        "labels": [],
        "hours_ago": 55,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE LAYER
# SQLite is perfect for this demo — zero setup, file-based, built into Python.
# In production you'd use PostgreSQL, but the SQL is identical for our queries.
# ═══════════════════════════════════════════════════════════════════════════════

class EmailDatabase:
    """SQLite-backed email store.

    WHY use raw sqlite3 instead of SQLAlchemy? SQLAlchemy is great for complex
    apps, but for a focused demo it adds setup complexity. Raw sqlite3 with
    context managers is clear and explicit about what SQL is running.

    Design decisions:
    - labels stored as JSON array (simple, avoids join table)
    - processed flag lets us track which emails need attention
    - classification results stored on the email row (denormalized for speed)
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema and seed sample emails if empty."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_addr   TEXT    NOT NULL,
                    subject     TEXT    NOT NULL,
                    body        TEXT    NOT NULL,
                    timestamp   TEXT    NOT NULL,  -- ISO 8601 format
                    labels      TEXT    DEFAULT '[]',  -- JSON array
                    processed   INTEGER DEFAULT 0,
                    category    TEXT,
                    priority    TEXT,
                    sentiment   TEXT,
                    requires_reply INTEGER DEFAULT 0
                )
            """)
            conn.commit()

            # Seed sample emails only if the table is empty (first run)
            count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
            if count == 0:
                print("First run detected — seeding 20 sample emails...")
                self._seed_emails(conn)

    def _seed_emails(self, conn: sqlite3.Connection) -> None:
        """Insert the 20 sample emails with realistic timestamps."""
        now = datetime.now()
        for email_data in SAMPLE_EMAILS:
            # Calculate realistic past timestamp
            hours_ago = email_data["hours_ago"]
            ts = now - timedelta(hours=hours_ago)
            conn.execute(
                """INSERT INTO emails (from_addr, subject, body, timestamp, labels)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    email_data["from_addr"],
                    email_data["subject"],
                    email_data["body"],
                    ts.isoformat(),
                    json.dumps(email_data["labels"]),
                ),
            )
        conn.commit()
        print(f"  ✓ Seeded {len(SAMPLE_EMAILS)} emails into {self.db_path}")

    def get_all_emails(self) -> list[Email]:
        """Retrieve all emails, newest first."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM emails ORDER BY timestamp DESC"
            ).fetchall()
        return [self._row_to_email(r) for r in rows]

    def get_unprocessed_emails(self) -> list[Email]:
        """Retrieve only emails not yet classified by the agent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM emails WHERE processed = 0 ORDER BY timestamp DESC"
            ).fetchall()
        return [self._row_to_email(r) for r in rows]

    def get_email_by_id(self, email_id: int) -> Optional[Email]:
        """Retrieve a single email by its ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM emails WHERE id = ?", (email_id,)
            ).fetchone()
        return self._row_to_email(row) if row else None

    def update_classification(
        self,
        email_id: int,
        category: str,
        priority: str,
        sentiment: str,
        requires_reply: bool,
    ) -> None:
        """Persist classification results back to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE emails
                   SET category = ?, priority = ?, sentiment = ?,
                       requires_reply = ?, processed = 1
                   WHERE id = ?""",
                (category, priority, sentiment, int(requires_reply), email_id),
            )
            conn.commit()

    def _row_to_email(self, row: sqlite3.Row) -> Email:
        """Convert a database row to an Email dataclass instance."""
        return Email(
            id=row["id"],
            from_addr=row["from_addr"],
            subject=row["subject"],
            body=row["body"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            labels=json.loads(row["labels"]),
            processed=bool(row["processed"]),
            category=row["category"],
            priority=row["priority"],
            sentiment=row["sentiment"],
            requires_reply=bool(row["requires_reply"]),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL CLASSIFIER
# Uses the LLM to classify emails. We use structured output via JSON mode
# to get reliable, parseable results from the model.
# ═══════════════════════════════════════════════════════════════════════════════

class EmailClassifier:
    """Classifies emails using an LLM.

    WHY use an LLM instead of rules/ML? Rule-based classification is brittle —
    it fails on new patterns. Traditional ML needs labeled training data.
    LLMs understand context and can reason about nuanced cases (e.g., a
    newsletter that is also urgent, or a sales email that's actually valuable).

    We use structured JSON output to make the LLM's response machine-readable.
    This is a core technique for reliable LLM applications.
    """

    # This prompt is carefully engineered. The key techniques:
    # 1. Explicit output format — prevents the model from being verbose
    # 2. Category definitions — reduces ambiguity in classification
    # 3. Few-shot examples embedded in the definitions
    # 4. Return "requires_reply: true" only for actionable items
    CLASSIFICATION_PROMPT = """You are an expert email classifier for a B2B SaaS company.

Analyze the email below and return a JSON object with EXACTLY these fields:
{{
  "category": "<one of: support|sales|spam|newsletter|urgent|meeting|other>",
  "priority": "<one of: high|medium|low>",
  "sentiment": "<one of: positive|neutral|negative|mixed>",
  "requires_reply": <true|false>,
  "reason": "<one sentence explaining your classification>"
}}

Category definitions:
- support: Technical questions, bug reports, API issues, how-to questions
- sales: Sales inquiries, partnership proposals, pricing questions, demos
- spam: Obvious unsolicited commercial email, phishing, scams, bulk mail
- newsletter: Automated newsletters, digests, subscription content
- urgent: Production outages, legal threats, time-critical issues needing immediate action
- meeting: Meeting requests, calendar invites, scheduling emails
- other: Everything else (billing, automated notifications, job offers, feedback)

Priority rules:
- high: Needs response within 4 hours (outages, legal, angry customers, active sales)
- medium: Needs response within 24 hours (support questions, meeting requests, sales)
- low: Can wait 72+ hours (newsletters, cold outreach, automated notifications)

Email to classify:
FROM: {from_addr}
SUBJECT: {subject}
BODY:
{body}

Return ONLY the JSON object. No other text."""

    def classify(self, email: Email) -> Classification:
        """Classify an email using the LLM.

        WHY we truncate the body: LLMs have context limits and classifying
        email category/priority rarely requires reading 10,000 words.
        We take the first 800 characters — enough for any reasonable email.
        """
        body_preview = email.body[:800]  # Limit to avoid context overflow

        try:
            # WHY inside the try: prompt construction (.format) can itself raise —
            # keeping it here means any formatting error falls back gracefully
            # instead of crashing the whole inbox sweep.
            prompt = self.CLASSIFICATION_PROMPT.format(
                from_addr=email.from_addr,
                subject=email.subject,
                body=body_preview,
            )

            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature = more consistent, less creative
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()

            # Parse the JSON response — LLMs sometimes wrap it in markdown code blocks
            if "```" in raw:
                # Extract just the JSON from markdown code fence
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            data = json.loads(raw)

            return Classification(
                category=data.get("category", "other"),
                priority=data.get("priority", "low"),
                sentiment=data.get("sentiment", "neutral"),
                requires_reply=bool(data.get("requires_reply", False)),
                reason=data.get("reason", "No reason provided"),
            )

        except Exception as e:  # Broad catch: Ollama/JSON/format errors all fall back
            # Fallback classification if LLM fails — better than crashing
            print(f"  Warning: Classification error for email {email.id}: {e}")
            return Classification(
                category="other",
                priority="low",
                sentiment="neutral",
                requires_reply=False,
                reason="Classification failed — defaulting to 'other'",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# REPLY DRAFTER
# Generates professional email replies using the LLM.
# ═══════════════════════════════════════════════════════════════════════════════

class ReplyDrafter:
    """Drafts professional email replies using an LLM.

    WHY have a separate class from EmailClassifier? Single Responsibility
    Principle — classification and reply drafting have different prompts,
    different temperature settings, and different failure modes.
    Separating them makes each easier to test, tune, and maintain.
    """

    REPLY_PROMPT = """You are a professional email assistant for a B2B SaaS company.
Draft a professional, helpful reply to the email below.

Guidelines:
- Be professional but warm (not stiff)
- Address every question or concern raised in the original email
- If it's a support issue: acknowledge the problem, provide next steps, set timeline expectations
- If it's a sales inquiry: be enthusiastic, answer questions, suggest a next step (call/demo)
- If it's a meeting request: confirm or suggest alternative times
- If it's spam or a newsletter: reply with just the word "SKIP" (we won't reply to these)
- Flag if human review is needed by starting with [HUMAN REVIEW NEEDED] and explaining why
  (use this for: legal matters, complex technical bugs, angry customers, large deal negotiations)
- Keep it concise — no more than 3-4 paragraphs
- End with a professional sign-off

Context about our company:
- We build AI infrastructure for developers
- Our product: document Q&A SaaS with REST API and Python SDK
- Standard support SLA: 4 hours for critical, 24 hours for standard
- Enterprise sales: handled by Account Executives (offer to connect them)

Original email:
FROM: {from_addr}
SUBJECT: {subject}
{context_section}
BODY:
{body}

Write only the email reply text. No preamble like "Here's a draft:". Start with the greeting."""

    def draft_reply(self, email: Email, context: str = "") -> str:
        """Draft a reply to the given email.

        Args:
            email: The email to reply to
            context: Optional additional context (e.g., "customer has been with us 3 years")

        Returns:
            Draft reply string, possibly prefixed with [HUMAN REVIEW NEEDED]
        """
        context_section = f"ADDITIONAL CONTEXT: {context}\n" if context else ""

        prompt = self.REPLY_PROMPT.format(
            from_addr=email.from_addr,
            subject=email.subject,
            body=email.body[:1000],  # Enough for the model to understand the full email
            context_section=context_section,
        )

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Higher temperature = more natural-sounding replies
                max_tokens=600,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"[DRAFT FAILED] Error generating reply: {e}"

    def needs_human_review(self, draft: str) -> bool:
        """Check if the draft requires human review before sending."""
        return draft.startswith("[HUMAN REVIEW NEEDED]")


# ═══════════════════════════════════════════════════════════════════════════════
# DIGEST GENERATOR
# Creates a structured daily summary of the inbox.
# ═══════════════════════════════════════════════════════════════════════════════

class DigestGenerator:
    """Generates a daily email digest with statistics and action items.

    WHY generate a digest? Email overload is a real problem. A daily digest
    gives you a bird's-eye view: what needs action, what can wait, what to ignore.
    This pattern is used by tools like Superhuman, SaneBox, and Gmail's
    Priority Inbox — but here we build it ourselves with full control.
    """

    def daily_digest(self, emails: list[Email]) -> str:
        """Generate a formatted daily digest string.

        We do the aggregation in Python (fast) and only ask the LLM for
        the natural-language summary section. Mixing code + LLM this way
        is more reliable than asking the LLM to count and categorize.
        """
        if not emails:
            return "No emails to digest."

        # ── Statistics (pure Python, no LLM needed) ──────────────────────────
        total = len(emails)
        processed = [e for e in emails if e.processed]
        unprocessed = [e for e in emails if not e.processed]
        requires_action = [e for e in processed if e.requires_reply]
        spam = [e for e in processed if e.category == "spam"]
        newsletters = [e for e in processed if e.category == "newsletter"]
        urgent = [e for e in processed if e.priority == "high"]

        # Group processed emails by category
        by_category: dict[str, list[Email]] = {}
        for email in processed:
            cat = email.category or "unclassified"
            by_category.setdefault(cat, []).append(email)

        # ── Build the digest ───────────────────────────────────────────────────
        now = datetime.now()
        lines = []

        lines.append("=" * 70)
        lines.append("  DAILY EMAIL DIGEST")
        lines.append(f"  Generated: {now.strftime('%A, %B %d %Y at %I:%M %p')}")
        lines.append("=" * 70)

        # Summary block
        lines.append("\n📊 SUMMARY")
        lines.append(f"   Total emails:      {total}")
        lines.append(f"   Processed:         {len(processed)}")
        lines.append(f"   Unprocessed:       {len(unprocessed)}")
        lines.append(f"   Require action:    {len(requires_action)}")
        lines.append(f"   Spam filtered:     {len(spam)}")
        lines.append(f"   Newsletters:       {len(newsletters)}")
        lines.append(f"   Urgent (high pri): {len(urgent)}")

        # Action items — the most important section
        if requires_action:
            lines.append("\n🔔 ACTION REQUIRED")
            lines.append("   These emails need a reply:")
            lines.append("")
            for i, email in enumerate(requires_action, 1):
                priority_icon = "🔴" if email.priority == "high" else "🟡" if email.priority == "medium" else "🟢"
                lines.append(f"   {i}. {priority_icon} [{email.category.upper()}] {email.subject}")
                lines.append(f"      From: {email.from_addr}")
                lines.append(f"      Received: {email.timestamp.strftime('%b %d at %I:%M %p')}")
                lines.append("")

        # Emails by category
        if by_category:
            lines.append("\n📁 EMAILS BY CATEGORY")
            for category in ["urgent", "support", "sales", "meeting", "other", "newsletter", "spam"]:
                if category in by_category:
                    cat_emails = by_category[category]
                    lines.append(f"\n   {category.upper()} ({len(cat_emails)})")
                    for email in cat_emails[:5]:  # Show max 5 per category
                        reply_flag = " [NEEDS REPLY]" if email.requires_reply else ""
                        lines.append(f"   • {email.subject[:60]}{reply_flag}")
                        lines.append(f"     From: {email.from_addr}")
                    if len(cat_emails) > 5:
                        lines.append(f"   ... and {len(cat_emails) - 5} more")

        # Unprocessed emails
        if unprocessed:
            lines.append(f"\n⏳ UNPROCESSED ({len(unprocessed)})")
            lines.append("   Run 'Process Inbox' to classify these:")
            for email in unprocessed[:5]:
                lines.append(f"   • {email.subject[:60]}")
                lines.append(f"     From: {email.from_addr}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL AGENT — THE ORCHESTRATOR
# Combines all components and provides the user interface.
# ═══════════════════════════════════════════════════════════════════════════════

class EmailAgent:
    """The main agent that orchestrates email processing.

    WHY orchestrate components through a single Agent class? This is the
    "Facade" design pattern — it provides a simple interface to the complex
    subsystem. Users (and code calling this) don't need to know about
    EmailDatabase, EmailClassifier, etc. They just call process_inbox().

    The interactive menu makes this runnable as a standalone CLI tool.
    In production, you'd expose these methods as API endpoints.
    """

    def __init__(self):
        print("\n" + "═" * 60)
        print("  EMAIL INTELLIGENCE AGENT — Phase 8 Project 03")
        print("═" * 60)
        print(f"  Model: {MODEL}")
        print(f"  Database: {DB_PATH}")
        print("═" * 60 + "\n")

        self.db = EmailDatabase()
        self.classifier = EmailClassifier()
        self.drafter = ReplyDrafter()
        self.digest_gen = DigestGenerator()

    def process_inbox(self) -> None:
        """Classify all unprocessed emails using the LLM.

        WHY process in batches? Making one LLM call per email is slow.
        For 20 emails that's 20 sequential API calls. In production you'd
        use asyncio + semaphore to process ~5 emails concurrently. For this
        demo, sequential is fine and easier to follow.
        """
        unprocessed = self.db.get_unprocessed_emails()

        if not unprocessed:
            print("✓ All emails already processed! Nothing to do.")
            return

        print(f"\nProcessing {len(unprocessed)} unprocessed emails...")
        print("(This may take a minute — making one LLM call per email)\n")

        for i, email in enumerate(unprocessed, 1):
            print(f"[{i}/{len(unprocessed)}] Classifying: {email.subject[:50]}...")

            classification = self.classifier.classify(email)

            # Persist the classification results
            self.db.update_classification(
                email_id=email.id,
                category=classification.category,
                priority=classification.priority,
                sentiment=classification.sentiment,
                requires_reply=classification.requires_reply,
            )

            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                classification.priority, "⚪"
            )
            reply_flag = " [REPLY NEEDED]" if classification.requires_reply else ""
            print(
                f"  {priority_icon} {classification.category.upper()} | "
                f"{classification.priority} priority{reply_flag}"
            )
            print(f"  Reason: {classification.reason}\n")

        print(f"✓ Processed {len(unprocessed)} emails successfully!")

    def handle_email(self, email_id: int) -> None:
        """Show full details for an email and draft a reply if needed.

        This is the "single email workflow":
        1. Classify the email (if not already done)
        2. Show classification results
        3. Draft a reply
        4. Show the draft + flag if human review needed
        """
        email = self.db.get_email_by_id(email_id)
        if not email:
            print(f"  Error: No email found with ID {email_id}")
            return

        print("\n" + "─" * 60)
        print(f"  EMAIL #{email.id}")
        print("─" * 60)
        print(f"  From:    {email.from_addr}")
        print(f"  Subject: {email.subject}")
        print(f"  Date:    {email.timestamp.strftime('%B %d, %Y at %I:%M %p')}")
        print("─" * 60)
        print("\n  BODY:")
        # Wrap long lines for terminal readability
        for line in email.body.split("\n"):
            if line.strip():
                print(textwrap.fill(f"  {line}", width=70))
            else:
                print()

        # Classify if not already done
        if not email.processed:
            print("\n  Classifying email...")
            classification = self.classifier.classify(email)
            self.db.update_classification(
                email_id=email.id,
                category=classification.category,
                priority=classification.priority,
                sentiment=classification.sentiment,
                requires_reply=classification.requires_reply,
            )
            # Reload the email with updated classification
            email = self.db.get_email_by_id(email_id)
            if not email:
                return

        print("\n  CLASSIFICATION:")
        print(f"  Category:      {email.category}")
        print(f"  Priority:      {email.priority}")
        print(f"  Sentiment:     {email.sentiment}")
        print(f"  Needs reply:   {'Yes' if email.requires_reply else 'No'}")

        # Skip reply drafting for spam and newsletters
        if email.category in ("spam", "newsletter"):
            print(f"\n  This is {email.category} — no reply will be drafted.")
            return

        if not email.requires_reply:
            print("\n  This email doesn't require a reply.")
            draft_anyway = input("  Draft a reply anyway? (y/N): ").strip().lower()
            if draft_anyway != "y":
                return

        print("\n  Drafting reply...\n")
        context = input("  Optional context for the reply (press Enter to skip): ").strip()

        draft = self.drafter.draft_reply(email, context=context)

        print("\n" + "─" * 60)
        print("  DRAFT REPLY:")
        print("─" * 60)

        if self.drafter.needs_human_review(draft):
            print("  ⚠️  HUMAN REVIEW REQUIRED before sending!\n")

        print(draft)
        print("─" * 60)

    def generate_digest(self) -> None:
        """Generate and print the daily email digest."""
        all_emails = self.db.get_all_emails()
        digest = self.digest_gen.daily_digest(all_emails)
        print("\n" + digest)

    def list_emails(self) -> None:
        """Display a summary table of all emails."""
        emails = self.db.get_all_emails()

        print(f"\n{'ID':<4} {'FROM':<35} {'SUBJECT':<40} {'CAT':<12} {'PRI':<7} {'REPLY'}")
        print("─" * 110)

        for email in emails:
            cat = email.category or "unprocessed"
            pri = email.priority or "─"
            reply = "YES" if email.requires_reply else "─"
            processed_flag = "✓" if email.processed else " "
            subject = email.subject[:37] + "..." if len(email.subject) > 40 else email.subject
            from_short = email.from_addr[:32] + "..." if len(email.from_addr) > 35 else email.from_addr

            print(f"{processed_flag}{email.id:<3} {from_short:<35} {subject:<40} {cat:<12} {pri:<7} {reply}")

    def run_interactive(self) -> None:
        """Run the interactive CLI menu.

        This is the main entry point for the demo. A real production system
        would expose these as REST API endpoints, not a CLI menu — but the
        CLI is perfect for learning and demonstration.
        """
        while True:
            print("\n" + "─" * 50)
            print("  EMAIL INTELLIGENCE AGENT — MAIN MENU")
            print("─" * 50)
            print("  [1] List all emails")
            print("  [2] Process inbox (classify unprocessed emails)")
            print("  [3] Handle specific email (classify + draft reply)")
            print("  [4] Generate daily digest")
            print("  [5] Quit")
            print("─" * 50)

            choice = input("  Choose [1-5]: ").strip()

            if choice == "1":
                self.list_emails()
            elif choice == "2":
                self.process_inbox()
            elif choice == "3":
                self.list_emails()
                email_id_str = input("\n  Enter email ID to handle: ").strip()
                try:
                    self.handle_email(int(email_id_str))
                except ValueError:
                    print("  Invalid ID — please enter a number")
            elif choice == "4":
                self.generate_digest()
            elif choice == "5":
                print("\n  Goodbye!\n")
                break
            else:
                print("  Invalid choice — please enter 1-5")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    agent = EmailAgent()
    agent.run_interactive()
