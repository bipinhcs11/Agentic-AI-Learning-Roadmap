
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Integrations & Shipping | Project 1: Slack AI Bot
# File: ai_handler.py
# Purpose: AI processing layer that talks to Ollama and formats responses
#          for Slack's markdown syntax.
#
# Why a separate module?
#   The AI logic is intentionally decoupled from the Slack event-handling code.
#   This makes it easy to swap the underlying model, add caching, or unit-test
#   the AI responses without touching any Slack-specific code.
#
# Ollama ↔ OpenAI-compatible API:
#   Ollama exposes an OpenAI-compatible endpoint at /v1. We point the
#   openai client's base_url there so we can use the same SDK we'd use
#   with GPT-4 — zero vendor lock-in at the code level.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import os
import re
import textwrap
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
# We read from .env so nothing sensitive lives in source code.
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemma3:4b")

# Ollama's OpenAI-compatible endpoint lives at <base>/v1
_client = OpenAI(
    base_url=f"{OLLAMA_URL}/v1",
    api_key="ollama",  # Ollama doesn't require a real key; any non-empty string works
)

# Slack's maximum message length is 3 000 characters per block. We split at
# a slightly smaller threshold to leave room for any formatting we add.
SLACK_MAX_CHARS: int = 3_000


# ── Slack Markdown Helper ─────────────────────────────────────────────────────

def _to_slack_md(text: str) -> str:
    """
    Convert a plain AI response into Slack-flavoured markdown.

    Slack uses a subset of markdown that differs from CommonMark:
      • *bold*  (not **bold**)
      • _italic_  (not *italic*)
      • `inline code`  (same as CommonMark)
      • ```code block```  (same but no language hint on the opening fence)

    We do a lightweight replacement — we don't want to break code blocks
    that the model already emitted, so we only touch text outside ``` fences.
    """
    lines: list[str] = text.split("\n")
    result: list[str] = []
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if not in_code_block:
            # ORDER MATTERS. CommonMark uses **bold** and *italic*; Slack uses
            # *bold* and _italic_.  If we naively did line.replace("**","*")
            # first, the just-created single-* bold would then be caught by the
            # italic regex and downgraded to _italic_ — destroying every bold
            # span the model emitted (and our system prompt tells it to use bold).
            #
            # So we protect bold BEFORE touching italics:
            #   1. Stash **bold** spans behind a NUL placeholder.
            #   2. Convert the remaining lone-* italics to _italics_.  We require
            #      the opening * to be followed by a non-space and the closing *
            #      to be preceded by a non-space, so a list-marker "* " bullet is
            #      never mistaken for an emphasis marker.
            #   3. Restore the bold spans as Slack single-* bold.
            line = re.sub(r"\*\*(.+?)\*\*", lambda m: "\x00" + m.group(1) + "\x00", line)
            line = re.sub(
                r"(?<!\*)\*(?!\*)(?!\s)(.+?)(?<!\s)(?<!\*)\*(?!\*)", r"_\1_", line
            )
            line = line.replace("\x00", "*")

        result.append(line)

    return "\n".join(result)


def _split_long_response(text: str) -> list[str]:
    """
    Split a response that exceeds Slack's character limit.

    Slack rejects messages longer than 3 000 chars. Rather than truncating
    (which loses information), we break the text at paragraph boundaries
    when possible, falling back to hard wrapping at the char limit.

    Returns a list of strings, each safe to send as a separate Slack message.
    """
    if len(text) <= SLACK_MAX_CHARS:
        return [text]

    chunks: list[str] = []
    remaining = text

    while len(remaining) > SLACK_MAX_CHARS:
        # Try to break at the last paragraph boundary before the limit
        split_at = remaining.rfind("\n\n", 0, SLACK_MAX_CHARS)
        if split_at == -1:
            # Fall back to the last newline
            split_at = remaining.rfind("\n", 0, SLACK_MAX_CHARS)
        if split_at == -1:
            # Hard cut — no natural boundary found
            split_at = SLACK_MAX_CHARS

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


# ── Public API ────────────────────────────────────────────────────────────────

def process_slack_message(text: str, context: dict[str, Any] | None = None) -> list[str]:
    """
    Generate an AI response to a user's message and return it as one or
    more Slack-safe strings (each ≤ 3 000 chars).

    Args:
        text:    The user's raw message text (already stripped of bot mentions).
        context: Optional dict with extra info, e.g. {"channel": "C123", "user": "U456"}.
                 Currently used for future extensibility (e.g., per-channel personas).

    Returns:
        A list of message strings.  Usually just one item, but may be several
        if the AI produces a very long answer.
    """
    context = context or {}

    # System prompt: we tell the model it's a helpful Slack assistant and to
    # use Slack-flavoured markdown so it looks polished in the UI.
    system_prompt = (
        "You are a helpful AI assistant embedded in a Slack workspace. "
        "Format your responses using Slack markdown: "
        "*bold* for emphasis, _italic_ for secondary emphasis, "
        "`code` for inline code, ```code blocks``` for multi-line code. "
        "Be concise and direct. Use bullet points for lists."
    )

    response = _client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        temperature=0.7,
        # max_tokens is omitted intentionally — we let the model decide length,
        # then handle over-length output ourselves via _split_long_response.
    )

    raw_answer: str = response.choices[0].message.content or ""
    formatted = _to_slack_md(raw_answer)
    return _split_long_response(formatted)


def summarize_messages(messages: list[dict[str, Any]]) -> list[str]:
    """
    Summarise a list of Slack messages (typically the last 10 in a channel).

    Args:
        messages: List of Slack message dicts, each with at least:
                  {"user": "U123", "text": "...", "ts": "1234567890.000100"}

    Returns:
        A list of Slack-formatted strings comprising the summary.
    """
    if not messages:
        return ["No messages to summarise."]

    # Build a readable transcript from the raw message objects
    transcript_lines: list[str] = []
    for msg in messages:
        user = msg.get("user", "unknown")
        text = msg.get("text", "")
        # We use the user ID for now; the bot caller can resolve display names
        # before calling this function if richer output is needed.
        transcript_lines.append(f"{user}: {text}")

    transcript = "\n".join(transcript_lines)

    prompt = (
        f"Summarise the following Slack conversation in 3–5 bullet points. "
        f"Highlight key decisions, action items, and open questions.\n\n"
        f"Conversation:\n{transcript}"
    )

    response = _client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful meeting-notes assistant. "
                    "Use Slack markdown (*bold*, _italic_, `code`). "
                    "Be concise."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,  # Lower temperature → more factual, less creative
    )

    raw: str = response.choices[0].message.content or ""
    formatted = _to_slack_md(raw)
    return _split_long_response(formatted)


def brainstorm(topic: str) -> list[str]:
    """
    Generate exactly 5 creative ideas about `topic` and return them as
    a formatted Slack message.

    Args:
        topic: The brainstorming subject (e.g., "ways to improve team morale").

    Returns:
        A list containing one (or rarely more) Slack-formatted strings.
    """
    prompt = (
        f"Generate exactly 5 creative, practical ideas about: {topic}\n\n"
        "Format as a numbered list. For each idea provide:\n"
        "• A short catchy title\n"
        "• One sentence explanation\n"
        "Be imaginative but realistic."
    )

    response = _client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a creative brainstorming partner. "
                    "Use Slack markdown. Keep each idea concise."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,  # Higher temperature → more diverse / creative ideas
    )

    raw: str = response.choices[0].message.content or ""
    formatted = _to_slack_md(raw)
    # Prepend a header so the Slack message has context
    header = f"*5 ideas for: {topic}*\n\n"
    return _split_long_response(header + formatted)
