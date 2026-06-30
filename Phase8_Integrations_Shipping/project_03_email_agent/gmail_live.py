"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║          Phase 8 — Integrations & Shipping | Project 03: Email Intelligence      ║
║                  gmail_live.py — REAL Gmail API integration                      ║
║                                                                                  ║
║  PURPOSE: Point the SAME agent brain (EmailClassifier / ReplyDrafter /           ║
║  DigestGenerator from email_agent.py) at a REAL Gmail inbox instead of the       ║
║  simulated SQLite store. The "data layer" swaps; the AI logic is untouched.      ║
║                                                                                  ║
║  SAFETY (read this):                                                             ║
║    • Everything is READ-ONLY by default. We list, classify, and summarise.       ║
║    • Replies are written as Gmail DRAFTS only — we NEVER auto-send. A human       ║
║      reviews and clicks Send. There is intentionally no send() in this file.     ║
║    • Draft creation only happens when you pass --create-drafts.                  ║
║                                                                                  ║
║  AUTH: OAuth2 "Desktop app" flow.                                                ║
║    credentials.json  (you downloaded this)  ──►  browser consent  ──►            ║
║    token.json        (saved login, auto-refreshed)                               ║
║    Scope: gmail.modify  (read inbox + create drafts; matches your consent screen)║
║                                                                                  ║
║  USAGE:                                                                          ║
║    python gmail_live.py list                  # show recent inbox (read-only)    ║
║    python gmail_live.py classify              # LLM-classify each email          ║
║    python gmail_live.py digest                # daily digest of the inbox        ║
║    python gmail_live.py triage                # classify + DRY-RUN draft replies ║
║    python gmail_live.py triage --create-drafts# actually create Gmail drafts     ║
║    (any command) --max 5 --query "is:unread"  # tune how many / which emails     ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import base64
import sys
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import parseaddr
from pathlib import Path

# Google API client stack (installed via: pip install google-api-python-client
# google-auth-oauthlib google-auth-httplib2)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Reuse the EXACT agent components from the simulation. This is the whole point:
# the classifier/drafter/digest don't know or care where the email came from.
from email_agent import Classification, Email, EmailClassifier, ReplyDrafter, DigestGenerator

# ─── OAuth configuration ──────────────────────────────────────────────────────
# gmail.modify = read messages + create/modify drafts. It does NOT grant the
# ability to permanently delete, and we never call send() anyway.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

HERE = Path(__file__).parent
CREDENTIALS_FILE = HERE / "credentials.json"  # the OAuth client you downloaded
TOKEN_FILE = HERE / "token.json"              # written after first login, reused after


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

def get_gmail_service():
    """
    Return an authenticated Gmail API service object.

    First run: opens a browser for consent and writes token.json.
    Later runs: silently loads token.json and refreshes it if expired.
    """
    if not CREDENTIALS_FILE.exists():
        sys.exit(
            f"❌ {CREDENTIALS_FILE.name} not found in {HERE}\n"
            "   Download your OAuth 'Desktop app' client from Google Cloud Console\n"
            "   (APIs & Services → Credentials) and save it as credentials.json here."
        )

    creds: Credentials | None = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # No valid cached login → refresh it, or run the full browser consent flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            # port=0 lets the OS pick a free port for the one-time local redirect.
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        print(f"✅ Saved login to {TOKEN_FILE.name} (you won't be prompted again)")

    return build("gmail", "v1", credentials=creds)


# ═══════════════════════════════════════════════════════════════════════════════
# GMAIL → Email  (the data-layer adapter)
# ═══════════════════════════════════════════════════════════════════════════════
# Gmail message IDs are strings; our Email.id is an int (it was a SQLite PK).
# So we keep the raw Gmail handles alongside the parsed Email in a small wrapper,
# and hand the agent a plain Email exactly like the SQLite layer did.

@dataclass
class LiveMessage:
    gmail_id: str        # needed to act on the message later
    thread_id: str       # needed so a draft reply threads correctly
    email: Email         # the agent-facing object


def _decode_body(payload: dict) -> str:
    """
    Walk a Gmail payload tree and return the best plain-text body we can find.

    Gmail bodies are base64url-encoded and often nested inside multipart trees
    (text/plain + text/html). We prefer text/plain; if there's only HTML we fall
    back to it; if all else fails the caller uses the snippet.
    """
    def walk(part: dict) -> tuple[str, str]:
        """Return (plain_text, html_text) collected from this part downward."""
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        text = ""
        if data:
            text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        plain, html = "", ""
        if mime == "text/plain":
            plain = text
        elif mime == "text/html":
            html = text

        for sub in part.get("parts", []) or []:
            p, h = walk(sub)
            plain += p
            html += h
        return plain, html

    plain, html = walk(payload)
    if plain.strip():
        return plain.strip()
    if html.strip():
        # Crude tag strip — good enough to feed an LLM; we don't render HTML.
        import re
        return re.sub(r"<[^>]+>", " ", html).strip()
    return ""


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def fetch_inbox(service, max_results: int = 10, query: str = "in:inbox") -> list[LiveMessage]:
    """
    Fetch recent inbox messages and adapt each into a LiveMessage (Email + ids).

    `query` uses normal Gmail search syntax: "is:unread", "from:boss@x.com",
    "newer_than:2d", etc. Default lists the inbox newest-first.
    """
    listing = (
        service.users().messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    refs = listing.get("messages", [])
    if not refs:
        return []

    messages: list[LiveMessage] = []
    for i, ref in enumerate(refs, start=1):
        full = (
            service.users().messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        payload = full.get("payload", {})
        headers = payload.get("headers", [])

        body = _decode_body(payload) or full.get("snippet", "")
        email = Email(
            id=i,  # local display index; the real handle lives on LiveMessage
            from_addr=_header(headers, "From"),
            subject=_header(headers, "Subject") or "(no subject)",
            body=body,
            labels=full.get("labelIds", []),
        )
        messages.append(
            LiveMessage(gmail_id=full["id"], thread_id=full["threadId"], email=email)
        )
    return messages


# ═══════════════════════════════════════════════════════════════════════════════
# WRITE PATH — create a DRAFT reply (never send)
# ═══════════════════════════════════════════════════════════════════════════════

def create_draft_reply(service, msg: LiveMessage, body: str) -> str:
    """
    Create a Gmail draft reply to `msg`, threaded under the original.

    Returns the new draft id. This does NOT send anything — the draft sits in
    your Drafts folder for you to review and send manually.
    """
    original = msg.email
    to_addr = parseaddr(original.from_addr)[1]  # strip "Name <addr>" → addr

    mime = MIMEText(body)
    mime["To"] = to_addr
    subject = original.subject
    mime["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    draft = (
        service.users().drafts()
        .create(userId="me", body={"message": {"raw": raw, "threadId": msg.thread_id}})
        .execute()
    )
    return draft["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# USE CASES (CLI commands)
# ═══════════════════════════════════════════════════════════════════════════════

def _short(text: str, n: int = 70) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def cmd_list(messages: list[LiveMessage]) -> None:
    """Use case 1 — just see what's in the inbox (read-only, no LLM)."""
    print(f"\n📥 {len(messages)} message(s):\n")
    for m in messages:
        e = m.email
        print(f"  [{e.id}] {parseaddr(e.from_addr)[1]:<32} {_short(e.subject, 50)}")
    print()


def cmd_classify(messages: list[LiveMessage], classifier: EmailClassifier) -> list[tuple[LiveMessage, Classification]]:
    """Use case 2 — LLM-classify every real email (read-only)."""
    print(f"\n🧠 Classifying {len(messages)} email(s) with the local LLM…\n")
    results: list[tuple[LiveMessage, Classification]] = []
    for m in messages:
        c = classifier.classify(m.email)
        results.append((m, c))
        reply_flag = "✏️ reply" if c.requires_reply else "—"
        print(
            f"  [{m.email.id}] {c.category:<10} {c.priority:<7} {c.sentiment:<9} "
            f"{reply_flag:<8} {_short(m.email.subject, 40)}"
        )
    print()
    return results


def cmd_digest(messages: list[LiveMessage], digest: DigestGenerator) -> None:
    """Use case 3 — one-paragraph daily digest of the real inbox (read-only)."""
    print("\n📰 Generating daily digest…\n")
    emails = [m.email for m in messages]
    print(digest.daily_digest(emails))
    print()


def cmd_triage(
    messages: list[LiveMessage],
    classifier: EmailClassifier,
    drafter: ReplyDrafter,
    service,
    create_drafts: bool,
) -> None:
    """
    Use case 4 — the full agent loop on real mail:
      classify → for reply-worthy mail, draft a reply → (optionally) save as Gmail draft.

    Without --create-drafts this is a DRY RUN: it prints the drafts it WOULD save.
    """
    mode = "CREATE DRAFTS" if create_drafts else "DRY RUN (no drafts saved)"
    print(f"\n🚦 Triage — mode: {mode}\n")

    for m, c in cmd_classify(messages, classifier):
        if not c.requires_reply:
            continue

        draft_text = drafter.draft_reply(m.email)
        flagged = drafter.needs_human_review(draft_text)

        print("  " + "─" * 72)
        print(f"  ✉️  Reply to [{m.email.id}] {_short(m.email.subject, 50)}")
        if flagged:
            print("  ⚠️  Flagged as complex — review carefully before sending.")
        print("  " + "\n  ".join(draft_text.splitlines()))

        if create_drafts:
            draft_id = create_draft_reply(service, m, draft_text)
            print(f"  💾 Saved as Gmail draft (id={draft_id}). Review & send manually.")
        else:
            print("  (dry run — pass --create-drafts to save this to Gmail Drafts)")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the email agent against REAL Gmail.")
    parser.add_argument(
        "command",
        choices=["list", "classify", "digest", "triage"],
        help="list=show inbox · classify=LLM tag · digest=summary · triage=draft replies",
    )
    parser.add_argument("--max", type=int, default=10, help="how many emails to fetch (default 10)")
    parser.add_argument("--query", default="in:inbox", help='Gmail search, e.g. "is:unread" (default in:inbox)')
    parser.add_argument(
        "--create-drafts",
        action="store_true",
        help="triage only: actually save reply drafts to Gmail (still never sends)",
    )
    args = parser.parse_args()

    try:
        service = get_gmail_service()
        messages = fetch_inbox(service, max_results=args.max, query=args.query)
    except HttpError as e:
        sys.exit(f"❌ Gmail API error: {e}")

    if not messages:
        print(f"\n(no messages matched query: {args.query!r})\n")
        return

    if args.command == "list":
        cmd_list(messages)
    elif args.command == "classify":
        cmd_classify(messages, EmailClassifier())
    elif args.command == "digest":
        cmd_digest(messages, DigestGenerator())
    elif args.command == "triage":
        cmd_triage(
            messages,
            EmailClassifier(),
            ReplyDrafter(),
            service,
            create_drafts=args.create_drafts,
        )


if __name__ == "__main__":
    main()
