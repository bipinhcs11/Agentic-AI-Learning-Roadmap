
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Integrations & Shipping | Project 2: GitHub Code Review Bot
# File: review_bot.py
# Purpose: FastAPI webhook server that receives GitHub PR events, triggers
#          AI code review, and posts results back to GitHub.
#
# How the webhook flow works:
#   1. You configure a webhook in your GitHub repo (Settings → Webhooks).
#   2. When a PR is opened or pushed to, GitHub sends a POST to /webhook.
#   3. We validate the HMAC-SHA256 signature to prove it really came from GitHub.
#   4. We extract owner/repo/PR number from the payload.
#   5. We fetch the diff via the GitHub API.
#   6. We send each file's diff to the AI reviewer.
#   7. We post inline comments and a summary back to the PR.
#
# Running locally with ngrok:
#   ngrok http 8000        # gives you a public URL like https://abc123.ngrok.io
#   Set webhook URL to:   https://abc123.ngrok.io/webhook
#   python review_bot.py
#
# Security — HMAC signature verification:
#   GitHub signs every webhook payload with a secret you choose.
#   The signature is in the X-Hub-Signature-256 header.
#   We compute our own HMAC-SHA256(secret, body) and compare.
#   If they don't match, we reject the request with 401.
#   This prevents anyone on the internet from fake-triggering reviews.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, status

import ai_reviewer
from github_client import GitHubClient

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("review_bot")

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# Skip review for files that aren't source code (images, lock files, docs, etc.)
# This saves time and avoids unhelpful "review" of generated files.
# NOTE: these are matched as filename *suffixes*, not just the last extension —
# os.path.splitext() only returns the final component, so ".min.js" would never
# match (it returns ".js").  We use str.endswith() against the whole filename so
# multi-part suffixes like ".min.js"/".min.css" work correctly.
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",          # Images
    ".lock", ".sum",                                            # Lock files
    ".min.js", ".min.css",                                     # Minified assets
    ".pb", ".onnx", ".h5",                                     # Model files
    ".pdf", ".docx", ".xlsx",                                  # Documents
}

# Generated lock files we skip by exact basename — ".json" is too broad to add
# to SKIP_EXTENSIONS (it would skip every legitimate JSON source file), so we
# match these well-known generated manifests explicitly.
SKIP_BASENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "composer.lock",
}

# Maximum number of files to review per PR.
# If a PR touches 200 files, reviewing all of them would take minutes and
# flood the PR with comments.  We cap at 10 most-significant files.
MAX_FILES_TO_REVIEW = 10

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="GitHub Code Review Bot",
    description="Automatically reviews pull requests using local Ollama AI.",
    version="1.0.0",
)


# ── Signature Verification ────────────────────────────────────────────────────

def _verify_github_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """
    Verify that the webhook payload was signed by GitHub using our secret.

    GitHub computes: HMAC-SHA256(secret, payload_body) and sends it as
    "sha256=<hex_digest>" in the X-Hub-Signature-256 header.

    We compute the same HMAC and use hmac.compare_digest() for the comparison.
    IMPORTANT: We must use hmac.compare_digest() instead of == to prevent
    timing attacks — a naive == comparison can leak information about how many
    bytes match, which helps an attacker brute-force the secret.

    Returns True if signature is valid, False otherwise.
    """
    if not GITHUB_WEBHOOK_SECRET:
        # If no secret is configured, skip verification (useful for local testing
        # without a real webhook — but never do this in production).
        log.warning("GITHUB_WEBHOOK_SECRET not set — skipping signature verification!")
        return True

    if not signature_header:
        log.warning("Missing X-Hub-Signature-256 header")
        return False

    # GitHub format: "sha256=<hex_digest>"
    if not signature_header.startswith("sha256="):
        log.warning("Unexpected signature format: %s", signature_header[:20])
        return False

    expected_signature = "sha256=" + hmac.new(
        key=GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison — prevents timing attacks
    return hmac.compare_digest(expected_signature, signature_header)


# ── Diff Parsing ──────────────────────────────────────────────────────────────

def _parse_diff_into_files(full_diff: str) -> dict[str, str]:
    """
    Split a full PR diff (multi-file unified diff) into per-file diffs.

    A unified diff starts each file with a line like:
        diff --git a/src/auth.py b/src/auth.py

    We split on those lines and associate each chunk with its filename.

    Returns:
        Dict mapping filename → file-level diff string.
    """
    file_diffs: dict[str, str] = {}
    current_file: str | None = None
    current_lines: list[str] = []

    for line in full_diff.splitlines(keepends=True):
        if line.startswith("diff --git "):
            # Save the previous file's diff before starting a new one
            if current_file and current_lines:
                file_diffs[current_file] = "".join(current_lines)

            # Extract the filename from "diff --git a/src/auth.py b/src/auth.py"
            # The "b/" prefix is the new filename in the diff format.
            parts = line.split(" b/", 1)
            current_file = parts[1].strip() if len(parts) > 1 else "unknown"
            current_lines = [line]
        elif current_file is not None:
            current_lines.append(line)

    # Don't forget the last file
    if current_file and current_lines:
        file_diffs[current_file] = "".join(current_lines)

    return file_diffs


def _should_skip_file(filename: str) -> bool:
    # Match on the whole filename suffix (not just the last extension) so
    # multi-part suffixes like ".min.js"/".min.css" are honoured, then fall
    # back to exact-basename matching for lock files like package-lock.json.
    name = filename.lower()
    if any(name.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    return os.path.basename(name) in SKIP_BASENAMES


def _prioritize_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort and limit the list of changed files to review.

    We prioritise files with more changes (additions + deletions) and skip
    binary/generated files.  This ensures we review the most impactful files
    when a PR touches many files.
    """
    reviewable = [
        f for f in files
        if not _should_skip_file(f.get("filename", ""))
        and f.get("status") != "removed"   # No point reviewing deleted files
        and f.get("patch")                  # Skip if no diff (e.g., pure binary)
    ]

    # Sort by total changes descending — biggest changes get reviewed first
    reviewable.sort(
        key=lambda f: f.get("additions", 0) + f.get("deletions", 0),
        reverse=True,
    )

    return reviewable[:MAX_FILES_TO_REVIEW]


# ── Review Pipeline ───────────────────────────────────────────────────────────

async def _run_review_pipeline(
    owner: str, repo: str, pr_number: int, pr_title: str, commit_sha: str
) -> None:
    """
    Orchestrate the full review pipeline for a pull request.

    This runs asynchronously (kicked off after ack'ing the webhook) so GitHub
    doesn't time out waiting for us to finish the review.

    Steps:
    1. Fetch changed files list from GitHub API
    2. Filter to reviewable files
    3. Review each file with AI
    4. Post inline comments for each issue found
    5. Post overall summary comment
    """
    github = GitHubClient(token=GITHUB_TOKEN)
    log.info("Starting review pipeline: %s/%s PR #%d (%s)", owner, repo, pr_number, pr_title)

    # ── Step 1: Get changed files ──────────────────────────────────────────
    try:
        all_files = github.get_pr_files(owner, repo, pr_number)
    except Exception as exc:
        log.error("Failed to fetch PR files: %s", exc)
        github.post_pr_comment(
            owner, repo, pr_number,
            f"**AI Review Bot** failed to fetch PR files: `{exc}`\n\n"
            "Please check that the bot has `repo` scope on its GitHub token."
        )
        return

    # ── Step 2: Filter to reviewable files ────────────────────────────────
    files_to_review = _prioritize_files(all_files)
    skipped = len(all_files) - len(files_to_review)

    if not files_to_review:
        github.post_pr_comment(
            owner, repo, pr_number,
            "**AI Review Bot**: No reviewable source files found in this PR "
            "(only binary files, lock files, or deleted files were changed)."
        )
        return

    log.info(
        "Reviewing %d/%d files (%d skipped)",
        len(files_to_review), len(all_files), skipped,
    )

    # ── Step 3: Review each file ───────────────────────────────────────────
    review_results: list[ai_reviewer.ReviewResult] = []

    for file_info in files_to_review:
        filename: str = file_info["filename"]
        patch: str = file_info.get("patch", "")

        if not patch:
            log.info("Skipping %s — no patch available", filename)
            continue

        context = (
            f"PR: {pr_title}\n"
            f"File status: {file_info.get('status', 'modified')}\n"
            f"Lines added: {file_info.get('additions', 0)}, "
            f"Lines removed: {file_info.get('deletions', 0)}"
        )

        result = ai_reviewer.review_file(filename, patch, context)
        review_results.append(result)

        # ── Step 4: Post inline comments ───────────────────────────────────
        for issue in result.issues:
            # Only post critical and warning inline (suggestions go in summary)
            if issue.severity == "suggestion":
                continue

            severity_emoji = "🔴" if issue.severity == "critical" else "🟡"
            comment_body = (
                f"{severity_emoji} **{issue.severity.upper()}** — {issue.message}\n\n"
                f"_Automated review by AI bot (model: {ai_reviewer.DEFAULT_MODEL})_"
            )

            github.post_review_comment(
                owner, repo, pr_number, commit_sha,
                path=filename,
                line=max(1, issue.line),
                body=comment_body,
            )

    if not review_results:
        log.warning("No review results generated")
        return

    # ── Step 5: Post overall summary ───────────────────────────────────────
    # Fetch the full diff for the summary context
    try:
        full_diff = github.get_pr_diff(owner, repo, pr_number)
        # Truncate to keep the summary prompt manageable
        if len(full_diff) > 10_000:
            full_diff = full_diff[:10_000] + "\n\n[... full diff truncated ...]"
    except Exception:
        full_diff = ""

    summary_text = ai_reviewer.review_pr_summary(review_results, full_diff)

    # Build the full summary comment
    score_line = " | ".join(
        f"`{r.filename.split('/')[-1]}`: {r.score}/10" for r in review_results
    )
    truncated_files = [r.filename for r in review_results if r.truncated]
    truncation_note = ""
    if truncated_files:
        truncation_note = (
            f"\n\n> **Note:** The following files had diffs larger than 5 000 chars "
            f"and were truncated for review: {', '.join(f'`{f}`' for f in truncated_files)}"
        )

    skipped_note = ""
    if skipped > 0:
        skipped_note = f"\n\n> **{skipped} file(s) skipped** (binary, lock files, or deleted)."

    full_comment = (
        f"## AI Code Review Summary\n\n"
        f"**Files reviewed:** {len(review_results)} | "
        f"**Model:** `{ai_reviewer.DEFAULT_MODEL}`\n\n"
        f"**Scores:** {score_line}\n\n"
        f"---\n\n"
        f"{summary_text}"
        f"{truncation_note}"
        f"{skipped_note}"
    )

    github.post_pr_comment(owner, repo, pr_number, full_comment)
    log.info("Review complete for PR #%d", pr_number)


# ── Webhook Endpoint ──────────────────────────────────────────────────────────

@app.post("/webhook", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Receive and process GitHub webhook events.

    GitHub sends events as JSON POST requests.  We handle:
      - pull_request.opened  → new PR opened, run full review
      - pull_request.synchronize → new commits pushed to PR, re-review

    Other events are acknowledged but ignored (returning 200 so GitHub
    doesn't mark the webhook as failing).
    """
    # Read the raw body before parsing JSON — we need bytes for HMAC verification.
    # FastAPI doesn't give us the raw body after parsing, so we read it ourselves.
    body_bytes: bytes = await request.body()

    # ── Security: Verify webhook signature ────────────────────────────────────
    if not _verify_github_signature(body_bytes, x_hub_signature_256):
        log.warning("Invalid webhook signature — possible forgery attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature. Ensure GITHUB_WEBHOOK_SECRET matches your GitHub webhook secret.",
        )

    # ── Parse the event ───────────────────────────────────────────────────────
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = x_github_event or "unknown"
    log.info("Received GitHub event: %s", event_type)

    # We only care about pull_request events
    if event_type != "pull_request":
        return {"status": "ignored", "event": event_type}

    action: str = payload.get("action", "")
    if action not in ("opened", "synchronize"):
        log.info("Ignoring pull_request action: %s", action)
        return {"status": "ignored", "action": action}

    # ── Extract PR details ────────────────────────────────────────────────────
    pr_data: dict[str, Any] = payload.get("pull_request", {})
    repo_data: dict[str, Any] = payload.get("repository", {})

    pr_number: int = pr_data.get("number", 0)
    pr_title: str = pr_data.get("title", "")
    commit_sha: str = pr_data.get("head", {}).get("sha", "")
    owner: str = repo_data.get("owner", {}).get("login", "")
    repo: str = repo_data.get("name", "")

    if not all([pr_number, commit_sha, owner, repo]):
        log.error("Missing required PR fields in payload")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payload missing required fields (pr_number, commit_sha, owner, or repo)",
        )

    log.info(
        "Queuing review: %s/%s PR #%d '%s' (commit %s)",
        owner, repo, pr_number, pr_title, commit_sha[:8],
    )

    # ── Kick off the review pipeline ─────────────────────────────────────────
    # We run the review in a background task so this endpoint returns quickly.
    # GitHub requires a response within 10 seconds — AI review takes much longer.
    import asyncio
    asyncio.create_task(
        _run_review_pipeline(owner, repo, pr_number, pr_title, commit_sha)
    )

    return {
        "status": "accepted",
        "pr": f"{owner}/{repo}#{pr_number}",
        "message": "Review pipeline started",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health check endpoint — useful for ngrok tunnel testing."""
    return {
        "status": "ok",
        "model": ai_reviewer.DEFAULT_MODEL,
        "ollama_url": ai_reviewer.OLLAMA_URL,
    }


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not GITHUB_WEBHOOK_SECRET:
        log.warning(
            "GITHUB_WEBHOOK_SECRET is not set! "
            "Webhook signature verification is disabled. "
            "Set this before deploying!"
        )
    if not GITHUB_TOKEN:
        log.warning(
            "GITHUB_TOKEN is not set! "
            "The bot can read public repos without a token (rate-limited), "
            "but cannot post comments."
        )

    log.info("Starting GitHub Review Bot on http://0.0.0.0:8000")
    log.info("Webhook endpoint: POST http://0.0.0.0:8000/webhook")
    log.info("Health check:     GET  http://0.0.0.0:8000/health")
    log.info("Model: %s  |  Ollama: %s", ai_reviewer.DEFAULT_MODEL, ai_reviewer.OLLAMA_URL)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
