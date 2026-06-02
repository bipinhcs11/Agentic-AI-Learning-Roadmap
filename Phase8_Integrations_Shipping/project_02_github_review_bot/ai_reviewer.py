
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Integrations & Shipping | Project 2: GitHub Code Review Bot
# File: ai_reviewer.py
# Purpose: AI-powered code review logic.  Takes unified diffs and produces
#          structured review results with issues, scores, and suggestions.
#
# Design decisions:
#   • We use a dataclass (ReviewResult) rather than raw dicts so callers get
#     IDE autocomplete and type safety.
#   • Each file is reviewed independently — this keeps prompts short and avoids
#     the model losing focus on a single file when given a huge PR diff.
#   • We cap diff size at 5 000 chars per file.  Beyond that, we truncate and
#     note it — the model can't reliably review thousands of lines at once.
#   • Temperature is set low (0.2) for reviews to get consistent, deterministic
#     feedback.  Creativity is NOT what we want from a code reviewer.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

log = logging.getLogger("ai_reviewer")

# ── Configuration ─────────────────────────────────────────────────────────────
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemma3:4b")

# Maximum diff characters to send per file.  Larger diffs are truncated.
# This keeps prompts within the model's context window and response time sane.
MAX_DIFF_CHARS: int = 5_000

_client = OpenAI(
    base_url=f"{OLLAMA_URL}/v1",
    api_key="ollama",  # Ollama doesn't check this; any non-empty string works
)

# ── Data Types ────────────────────────────────────────────────────────────────

SEVERITY_LEVELS = ("critical", "warning", "suggestion")


@dataclass
class Issue:
    """A single code issue found during review."""
    line: int           # Line number in the diff (approximate)
    severity: str       # "critical" | "warning" | "suggestion"
    message: str        # Human-readable description of the issue


@dataclass
class ReviewResult:
    """Complete review output for a single file."""
    filename: str
    score: int                          # 1–10 (10 = excellent)
    issues: list[Issue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    summary: str = ""                   # One-paragraph overview of the file
    truncated: bool = False             # True if diff was cut to MAX_DIFF_CHARS


# ── Internal helpers ──────────────────────────────────────────────────────────

def _truncate_diff(diff: str) -> tuple[str, bool]:
    """
    Ensure diff doesn't exceed MAX_DIFF_CHARS.

    Returns (possibly_truncated_diff, was_truncated).
    We truncate at a line boundary to avoid sending half a line.
    """
    if len(diff) <= MAX_DIFF_CHARS:
        return diff, False

    # Find the last newline before the limit
    cut = diff.rfind("\n", 0, MAX_DIFF_CHARS)
    if cut == -1:
        cut = MAX_DIFF_CHARS

    truncated_diff = diff[:cut] + "\n\n[... diff truncated — only first 5 000 chars shown ...]"
    return truncated_diff, True


def _parse_review_json(raw: str, filename: str) -> ReviewResult:
    """
    Parse the AI's JSON response into a ReviewResult.

    The prompt asks for a specific JSON schema.  If the model produces
    slightly malformed JSON (which happens with smaller models), we fall
    back gracefully with a warning rather than crashing the whole pipeline.
    """
    # Strip markdown code fences if the model wrapped its JSON in ```json ... ```
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or just ```)
        text = text.split("\n", 1)[-1]
        # Remove closing fence
        if text.endswith("```"):
            text = text[: text.rfind("```")].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        log.warning("Could not parse AI review JSON for %s: %s", filename, exc)
        # Return a graceful fallback so the pipeline keeps running
        return ReviewResult(
            filename=filename,
            score=5,
            summary=f"AI returned unparseable output. Raw response excerpt: {raw[:300]}",
            issues=[],
            suggestions=["Re-run review — model returned malformed JSON."],
        )

    # Build Issues from the parsed data
    issues: list[Issue] = []
    for item in data.get("issues", []):
        severity = item.get("severity", "suggestion")
        if severity not in SEVERITY_LEVELS:
            severity = "suggestion"
        issues.append(
            Issue(
                line=int(item.get("line", 0)),
                severity=severity,
                message=str(item.get("message", "")),
            )
        )

    return ReviewResult(
        filename=filename,
        score=max(1, min(10, int(data.get("score", 5)))),
        issues=issues,
        suggestions=[str(s) for s in data.get("suggestions", [])],
        summary=str(data.get("summary", "")),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def review_file(filename: str, diff: str, context: str = "") -> ReviewResult:
    """
    Review a single file's diff and return a structured ReviewResult.

    Args:
        filename: The file path within the repository (e.g., "src/auth.py").
        diff:     The unified diff for this file.
        context:  Optional extra context (e.g., PR description, language hints).

    Returns:
        A ReviewResult with issues, score, and suggestions.
    """
    truncated_diff, was_truncated = _truncate_diff(diff)

    # We ask the model to return valid JSON so we can parse it reliably.
    # The schema is spelled out explicitly to reduce hallucination.
    system_prompt = """You are an expert code reviewer with deep knowledge of security, performance, and software design.

Review the provided unified diff carefully. Focus on:
1. BUGS — logic errors, null pointer dereferences, off-by-one errors, race conditions
2. SECURITY — SQL injection, XSS, insecure deserialization, hardcoded secrets, improper authentication
3. PERFORMANCE — unnecessary loops, N+1 queries, blocking I/O, memory leaks
4. STYLE — naming conventions, dead code, overly complex functions, missing error handling

Return ONLY valid JSON with this exact schema (no extra text, no markdown):
{
  "score": <integer 1-10, where 10 is perfect code>,
  "summary": "<one paragraph overview of the file and main concerns>",
  "issues": [
    {
      "line": <approximate line number in the diff, integer>,
      "severity": "<critical|warning|suggestion>",
      "message": "<specific, actionable description of the issue>"
    }
  ],
  "suggestions": [
    "<general improvement suggestion not tied to a specific line>"
  ]
}

Severity guide:
- critical: Must fix before merging (security holes, definite bugs, data loss risk)
- warning: Should fix (likely bugs, performance issues, unclear logic)
- suggestion: Nice to have (style, readability, minor improvements)

Be specific and constructive. Reference variable names and line numbers where possible."""

    user_prompt = f"File: {filename}\n"
    if context:
        user_prompt += f"Context: {context}\n"
    user_prompt += f"\nDiff:\n{truncated_diff}"

    log.info("Reviewing file: %s (%d chars diff)", filename, len(truncated_diff))

    try:
        response = _client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,    # Low temperature = consistent, repeatable reviews
            max_tokens=2048,    # Cap so we don't wait forever on large files
        )
        raw_output: str = response.choices[0].message.content or "{}"
    except Exception as exc:
        log.error("AI review failed for %s: %s", filename, exc)
        raw_output = '{"score": 5, "summary": "Review failed due to AI error.", "issues": [], "suggestions": []}'

    result = _parse_review_json(raw_output, filename)
    result.truncated = was_truncated
    return result


def review_pr_summary(files_reviewed: list[ReviewResult], overall_diff: str) -> str:
    """
    Generate an overall PR summary after all files have been reviewed.

    Args:
        files_reviewed: ReviewResult objects from review_file() for each file.
        overall_diff:   The complete PR diff (may be truncated internally).

    Returns:
        A markdown-formatted summary string suitable for posting as a PR comment.
    """
    if not files_reviewed:
        return "No files were reviewed."

    # Build a compact JSON summary of what we found — this fits in one prompt
    # without re-sending all the diffs (which would exceed context).
    review_digest = []
    for r in files_reviewed:
        review_digest.append({
            "file": r.filename,
            "score": r.score,
            "critical_count": sum(1 for i in r.issues if i.severity == "critical"),
            "warning_count": sum(1 for i in r.issues if i.severity == "warning"),
            "suggestion_count": sum(1 for i in r.issues if i.severity == "suggestion"),
            "summary": r.summary[:200],  # Truncate to keep the meta-prompt manageable
        })

    avg_score = sum(r.score for r in files_reviewed) / len(files_reviewed)
    total_critical = sum(1 for r in files_reviewed if any(i.severity == "critical" for i in r.issues))

    prompt = f"""You are summarising a code review for a pull request.
Here is the per-file review data (JSON):
{json.dumps(review_digest, indent=2)}

Overall stats:
- Files reviewed: {len(files_reviewed)}
- Average score: {avg_score:.1f}/10
- Files with critical issues: {total_critical}

Write a concise PR summary in markdown format (2-4 paragraphs):
1. Overall assessment — is this PR ready to merge?
2. Key issues found across all files
3. Positive observations (what was done well)
4. Recommended next steps

Use GitHub-flavoured markdown. Be direct and constructive."""

    try:
        response = _client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content or "Unable to generate summary."
    except Exception as exc:
        log.error("PR summary generation failed: %s", exc)
        return (
            f"**Automated Review Summary**\n\n"
            f"Files reviewed: {len(files_reviewed)}\n"
            f"Average score: {avg_score:.1f}/10\n\n"
            f"_(Summary generation failed: {exc})_"
        )
