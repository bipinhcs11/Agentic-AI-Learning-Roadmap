
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Integrations & Shipping | Project 1: Slack AI Bot
# File: bot.py
# Purpose: Main Slack bot entry point using Bolt for Python with Socket Mode.
#
# Architecture overview:
#
#   Slack servers ──WebSocket──► slack_bolt (SocketModeHandler)
#                                      │
#                                      ▼
#                               Event handlers (this file)
#                                      │
#                                      ▼
#                               ai_handler.py
#                                      │
#                                      ▼
#                        Ollama (local LLM via OpenAI API)
#
# Why Socket Mode?
#   The alternative is an HTTP endpoint that Slack POSTs events to — which
#   requires a public URL (e.g., via ngrok).  Socket Mode keeps a persistent
#   WebSocket connection open FROM your machine TO Slack, so you never need
#   to expose a port.  Perfect for local development and secure deployments
#   behind a firewall.
#
# Tokens needed:
#   SLACK_BOT_TOKEN  (xoxb-…)  — authenticates the bot's API calls
#   SLACK_APP_TOKEN  (xapp-…)  — authenticates the Socket Mode connection
#
# See setup_guide.md for the step-by-step Slack app creation walkthrough.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
import os
import re
import time
from collections import defaultdict
from typing import Any

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import ai_handler

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
# Bolt's default logging is quite noisy. We set it to INFO so we see the
# important events without drowning in debug output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("slack_bot")

# ── App Initialisation ────────────────────────────────────────────────────────
# Bolt reads the token and signing secret for us.
# process_before_response=True is required for Socket Mode so that slow
# handlers (our AI calls can take several seconds) don't time out.
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.getenv("SLACK_SIGNING_SECRET", "unused_in_socket_mode"),
    process_before_response=True,
)

# Resolve our own bot user id ONCE at startup. The bot's user id is static, so
# calling auth.test on every incoming channel message (as we used to) just burns
# a Slack API round-trip and rate-limit budget per message. We cache it here and
# use the public app.client (not the private app._client).
BOT_USER_ID: str = app.client.auth_test()["user_id"]

# ── Rate Limiting ─────────────────────────────────────────────────────────────
# A simple in-memory rate limiter: map user_id → last_request_timestamp.
# We allow one AI request per user every RATE_LIMIT_SECONDS seconds.
# This protects against accidental loops and excessive Ollama usage.
# For production you'd use Redis so it persists across restarts.
RATE_LIMIT_SECONDS: int = 10
_last_request: dict[str, float] = defaultdict(float)


def _check_rate_limit(user_id: str) -> bool:
    """Return True if the user is allowed to make a request right now."""
    now = time.monotonic()
    if now - _last_request[user_id] < RATE_LIMIT_SECONDS:
        return False  # Too soon
    _last_request[user_id] = now
    return True


# ── Hourglass Indicator ───────────────────────────────────────────────────────
# While the AI is thinking we add an ⏳ reaction to the triggering message.
# This gives instant feedback so users know the bot received their message.

def _add_thinking(client: Any, channel: str, ts: str) -> None:
    """Add the hourglass reaction to a message (fire-and-forget)."""
    try:
        client.reactions_add(channel=channel, name="hourglass_flowing_sand", timestamp=ts)
    except Exception:
        pass  # Non-critical; don't crash the handler if reactions aren't enabled


def _remove_thinking(client: Any, channel: str, ts: str) -> None:
    """Remove the hourglass reaction once we have the AI response."""
    try:
        client.reactions_remove(channel=channel, name="hourglass_flowing_sand", timestamp=ts)
    except Exception:
        pass


def _post_chunks(client: Any, channel: str, chunks: list[str]) -> None:
    """
    Post a list of message strings to a Slack channel.

    When the AI response exceeds 3 000 chars, ai_handler splits it into
    multiple chunks.  We post each as a separate message so they flow
    naturally in the thread.
    """
    for chunk in chunks:
        client.chat_postMessage(channel=channel, text=chunk, mrkdwn=True)


# ── Message Handler ───────────────────────────────────────────────────────────
# This catches every message the bot can see — DMs and any channel it's in.
# We use a wildcard pattern ".*" to match all text.
# Note: Slack sends a `subtype` field for system messages (joins, topic changes).
#       We ignore those to avoid the bot responding to noise.

@app.message(".*")
def handle_message(message: dict[str, Any], client: Any, say: Any) -> None:
    """Respond to direct messages and any message in channels the bot joined."""
    # Ignore bot messages (including our own) to prevent infinite loops
    if message.get("bot_id") or message.get("subtype"):
        return

    user_id: str = message.get("user", "unknown")
    channel: str = message["channel"]
    ts: str = message["ts"]
    text: str = message.get("text", "").strip()

    # Only respond in DMs (channel starts with "D") or when explicitly mentioned
    channel_type: str = message.get("channel_type", "")
    if channel_type != "im" and f"<@{BOT_USER_ID}>" not in text:
        # Not a DM and not a mention — skip (app_mention handler covers mentions)
        return

    if not _check_rate_limit(user_id):
        # say() is already bound to this event's channel, so no channel= kwarg.
        say(text=f"_Slow down! I can only handle one request every {RATE_LIMIT_SECONDS} seconds per user._")
        return

    log.info("DM from %s: %s", user_id, text[:80])
    _add_thinking(client, channel, ts)

    try:
        chunks = ai_handler.process_slack_message(text, {"channel": channel, "user": user_id})
    except Exception as exc:
        log.exception("AI processing failed: %s", exc)
        chunks = [f":warning: Sorry, I hit an error: `{exc}`"]
    finally:
        _remove_thinking(client, channel, ts)

    _post_chunks(client, channel, chunks)


# ── Mention Handler ───────────────────────────────────────────────────────────
# When a user @-mentions the bot in a public/private channel, Slack fires the
# `app_mention` event.  We strip the mention text before passing to the AI.

@app.event("app_mention")
def handle_mention(event: dict[str, Any], client: Any, say: Any) -> None:
    """Respond when the bot is @-mentioned in a channel."""
    user_id: str = event.get("user", "unknown")
    channel: str = event["channel"]
    ts: str = event["ts"]
    raw_text: str = event.get("text", "")

    # Remove the @mention token (e.g., "<@U12345>") from the text
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", raw_text).strip()

    if not clean_text:
        # say() is already scoped to the event's channel — no channel= kwarg.
        say(text="Hey! Ask me anything — I'm here to help. :wave:")
        return

    if not _check_rate_limit(user_id):
        say(text=f"_Please wait {RATE_LIMIT_SECONDS}s between requests._")
        return

    log.info("Mention from %s: %s", user_id, clean_text[:80])
    _add_thinking(client, channel, ts)

    try:
        chunks = ai_handler.process_slack_message(
            clean_text, {"channel": channel, "user": user_id}
        )
    except Exception as exc:
        log.exception("AI processing failed: %s", exc)
        chunks = [f":warning: Sorry, I hit an error: `{exc}`"]
    finally:
        _remove_thinking(client, channel, ts)

    _post_chunks(client, channel, chunks)


# ── Slash Command: /ask ───────────────────────────────────────────────────────
# Usage: /ask <question>
# The bot answers the question using the AI.

@app.command("/ask")
def handle_ask(ack: Any, body: dict[str, Any], client: Any) -> None:
    """
    /ask <question>  — Get an AI answer to any question.

    We must call ack() within 3 seconds (Slack's timeout for slash commands).
    We call it immediately with a "thinking" message, then do the AI work.
    """
    ack()  # Acknowledge receipt immediately — Slack will show a spinner

    user_id: str = body["user_id"]
    channel_id: str = body["channel_id"]
    question: str = body.get("text", "").strip()

    if not question:
        client.chat_postMessage(
            channel=channel_id,
            text="_Usage: `/ask <your question>`_",
        )
        return

    if not _check_rate_limit(user_id):
        client.chat_postMessage(
            channel=channel_id,
            text=f"_Rate limited. Please wait {RATE_LIMIT_SECONDS}s._",
        )
        return

    log.info("/ask from %s: %s", user_id, question[:80])

    # Post a placeholder so the user sees instant feedback
    placeholder = client.chat_postMessage(
        channel=channel_id,
        text=":hourglass_flowing_sand: Thinking...",
    )

    try:
        chunks = ai_handler.process_slack_message(question)
    except Exception as exc:
        log.exception("/ask AI failed: %s", exc)
        chunks = [f":warning: Error: `{exc}`"]

    # Update the placeholder with the first chunk, then post the rest
    client.chat_update(
        channel=channel_id,
        ts=placeholder["ts"],
        text=chunks[0],
    )
    for extra_chunk in chunks[1:]:
        client.chat_postMessage(channel=channel_id, text=extra_chunk, mrkdwn=True)


# ── Slash Command: /summarize ─────────────────────────────────────────────────
# Usage: /summarize  (no arguments)
# Fetches the last 10 messages in the current channel and summarises them.

@app.command("/summarize")
def handle_summarize(ack: Any, body: dict[str, Any], client: Any) -> None:
    """
    /summarize — Summarise the last 10 messages in the current channel.

    We use conversations.history to fetch messages.  The bot must have the
    `channels:history` (for public channels) or `groups:history` (for private
    channels) OAuth scope for this to work.
    """
    ack()

    user_id: str = body["user_id"]
    channel_id: str = body["channel_id"]

    if not _check_rate_limit(user_id):
        client.chat_postMessage(
            channel=channel_id,
            text=f"_Rate limited. Please wait {RATE_LIMIT_SECONDS}s._",
        )
        return

    # Fetch the last 10 messages
    try:
        history = client.conversations_history(channel=channel_id, limit=10)
        messages: list[dict[str, Any]] = history.get("messages", [])
    except Exception as exc:
        log.exception("Could not fetch channel history: %s", exc)
        client.chat_postMessage(
            channel=channel_id,
            text=f":warning: Could not fetch messages: `{exc}`\n"
                 "Make sure the bot has `channels:history` scope.",
        )
        return

    if not messages:
        client.chat_postMessage(channel=channel_id, text="_No messages found to summarise._")
        return

    # Reverse so oldest messages come first (history returns newest-first)
    messages = list(reversed(messages))

    placeholder = client.chat_postMessage(
        channel=channel_id,
        text=f":hourglass_flowing_sand: Summarising {len(messages)} messages...",
    )

    try:
        chunks = ai_handler.summarize_messages(messages)
    except Exception as exc:
        log.exception("/summarize AI failed: %s", exc)
        chunks = [f":warning: Error: `{exc}`"]

    client.chat_update(
        channel=channel_id,
        ts=placeholder["ts"],
        text=f"*Thread Summary* :scroll:\n\n{chunks[0]}",
    )
    for extra_chunk in chunks[1:]:
        client.chat_postMessage(channel=channel_id, text=extra_chunk, mrkdwn=True)


# ── Slash Command: /brainstorm ────────────────────────────────────────────────
# Usage: /brainstorm <topic>
# Returns 5 creative ideas about the given topic.

@app.command("/brainstorm")
def handle_brainstorm(ack: Any, body: dict[str, Any], client: Any) -> None:
    """
    /brainstorm <topic> — Generate 5 creative ideas about a topic.
    """
    ack()

    user_id: str = body["user_id"]
    channel_id: str = body["channel_id"]
    topic: str = body.get("text", "").strip()

    if not topic:
        client.chat_postMessage(
            channel=channel_id,
            text="_Usage: `/brainstorm <topic>`_\nExample: `/brainstorm ways to improve team retrospectives`",
        )
        return

    if not _check_rate_limit(user_id):
        client.chat_postMessage(
            channel=channel_id,
            text=f"_Rate limited. Please wait {RATE_LIMIT_SECONDS}s._",
        )
        return

    log.info("/brainstorm from %s: %s", user_id, topic[:80])

    placeholder = client.chat_postMessage(
        channel=channel_id,
        text=f":brain: Brainstorming ideas for *{topic}*...",
    )

    try:
        chunks = ai_handler.brainstorm(topic)
    except Exception as exc:
        log.exception("/brainstorm AI failed: %s", exc)
        chunks = [f":warning: Error: `{exc}`"]

    client.chat_update(
        channel=channel_id,
        ts=placeholder["ts"],
        text=chunks[0],
    )
    for extra_chunk in chunks[1:]:
        client.chat_postMessage(channel=channel_id, text=extra_chunk, mrkdwn=True)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit(
            "SLACK_APP_TOKEN is not set. "
            "Add it to your .env file. See setup_guide.md for instructions."
        )

    log.info("Starting Slack bot in Socket Mode…")
    log.info("Model: %s  |  Ollama: %s", ai_handler.DEFAULT_MODEL, ai_handler.OLLAMA_URL)

    # SocketModeHandler manages the WebSocket connection to Slack.
    # It handles reconnection automatically on network hiccups.
    handler = SocketModeHandler(app, app_token)
    handler.start()  # Blocks until Ctrl-C
