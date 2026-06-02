
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Integrations & Shipping | Project 2: GitHub Code Review Bot
# File: test_review.py
# Purpose: Test the review pipeline without setting up a real GitHub webhook.
#
# This script manually fetches a public PR from a popular open-source repo
# and runs it through the review pipeline, printing what would be posted
# to GitHub.  No GitHub token required for reading public repos (though you'll
# be rate-limited to 60 requests/hour without one).
#
# Usage:
#   python test_review.py
#   python test_review.py --owner facebook --repo react --pr 25000
#
# The default test target is a real PR from the `requests` library — it's
# a readable Python project with clear diffs, making it ideal for demos.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import ai_reviewer
from github_client import GitHubClient

# ── Default test target ───────────────────────────────────────────────────────
# Using the `requests` library as the test target — it's Python, readable,
# and has many merged PRs with clean diffs.
DEFAULT_OWNER = "psf"
DEFAULT_REPO = "requests"
DEFAULT_PR = 6710  # A real merged PR — "Add support for IDNA 3.x"

SEPARATOR = "═" * 70


def _print_header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def _format_issue(issue: ai_reviewer.Issue) -> str:
    """Format a single issue for console display."""
    icon = {"critical": "🔴", "warning": "🟡", "suggestion": "💡"}.get(
        issue.severity, "  "
    )
    return f"  {icon} [{issue.severity.upper():10s}] Line {issue.line:4d}: {issue.message}"


def run_test(owner: str, repo: str, pr_number: int, github_token: str = "") -> None:
    """
    Fetch a PR and run the full review pipeline, printing output to stdout.

    This is the same logic as the webhook handler, just driven from the
    command line for easy testing.
    """
    github = GitHubClient(token=github_token)

    _print_header(f"GitHub Code Review Bot — Test Run")
    print(f"  Target:  {owner}/{repo} PR #{pr_number}")
    print(f"  Model:   {ai_reviewer.DEFAULT_MODEL}")
    print(f"  Ollama:  {ai_reviewer.OLLAMA_URL}")
    print(f"  Token:   {'yes (authenticated)' if github_token else 'no (public, rate-limited)'}")

    # ── Step 1: Fetch PR metadata ─────────────────────────────────────────────
    _print_header("Step 1: Fetching PR metadata")
    try:
        pr_info = github.get_pr_info(owner, repo, pr_number)
    except Exception as exc:
        print(f"  ERROR: Could not fetch PR info: {exc}")
        sys.exit(1)

    pr_title: str = pr_info.get("title", "")
    pr_state: str = pr_info.get("state", "")
    commit_sha: str = pr_info.get("head", {}).get("sha", "")
    author: str = pr_info.get("user", {}).get("login", "unknown")

    print(f"  Title:   {pr_title}")
    print(f"  State:   {pr_state}")
    print(f"  Author:  {author}")
    print(f"  Commit:  {commit_sha[:10]}...")

    # ── Step 2: Fetch changed files ───────────────────────────────────────────
    _print_header("Step 2: Fetching changed files")
    try:
        all_files = github.get_pr_files(owner, repo, pr_number)
    except Exception as exc:
        print(f"  ERROR: Could not fetch files: {exc}")
        sys.exit(1)

    print(f"  Total files changed: {len(all_files)}")
    for f in all_files:
        status_icon = {"added": "+", "modified": "~", "removed": "-", "renamed": "→"}.get(
            f.get("status", ""), "?"
        )
        print(f"  [{status_icon}] {f['filename']}  (+{f.get('additions', 0)} -{f.get('deletions', 0)})")

    # ── Step 3: Filter to reviewable files ───────────────────────────────────
    from review_bot import _prioritize_files
    files_to_review = _prioritize_files(all_files)
    skipped = len(all_files) - len(files_to_review)

    _print_header(f"Step 3: Filtering — {len(files_to_review)} files to review, {skipped} skipped")
    for f in files_to_review:
        print(f"  → {f['filename']}")

    if not files_to_review:
        print("  No reviewable files found. Exiting.")
        return

    # ── Step 4: Review each file ──────────────────────────────────────────────
    review_results: list[ai_reviewer.ReviewResult] = []
    total_start = time.perf_counter()

    for i, file_info in enumerate(files_to_review, 1):
        filename: str = file_info["filename"]
        patch: str = file_info.get("patch", "")

        if not patch:
            print(f"  Skipping {filename} — no patch")
            continue

        _print_header(f"Step 4.{i}: Reviewing {filename}")
        start = time.perf_counter()

        context = (
            f"PR: {pr_title}\n"
            f"File status: {file_info.get('status', 'modified')}\n"
            f"Lines added: {file_info.get('additions', 0)}, "
            f"Lines removed: {file_info.get('deletions', 0)}"
        )

        print(f"  Sending {min(len(patch), ai_reviewer.MAX_DIFF_CHARS)} chars to AI...")
        result = ai_reviewer.review_file(filename, patch, context)
        elapsed = time.perf_counter() - start

        print(f"  Score:    {result.score}/10  ({elapsed:.1f}s)")
        print(f"  Summary:  {result.summary[:200]}{'...' if len(result.summary) > 200 else ''}")
        if result.truncated:
            print(f"  WARNING:  Diff was truncated to {ai_reviewer.MAX_DIFF_CHARS} chars")

        if result.issues:
            print(f"\n  Issues ({len(result.issues)}):")
            for issue in result.issues:
                print(_format_issue(issue))
        else:
            print("  No issues found.")

        if result.suggestions:
            print(f"\n  Suggestions:")
            for sug in result.suggestions:
                print(f"    • {sug}")

        review_results.append(result)

    # ── Step 5: Generate overall summary ──────────────────────────────────────
    _print_header("Step 5: Generating PR Summary")
    print("  Fetching full diff for context...")

    try:
        full_diff = github.get_pr_diff(owner, repo, pr_number)
        if len(full_diff) > 10_000:
            full_diff = full_diff[:10_000] + "\n[... truncated ...]"
    except Exception:
        full_diff = ""

    summary = ai_reviewer.review_pr_summary(review_results, full_diff)
    total_elapsed = time.perf_counter() - total_start

    _print_header("Summary Comment (what would be posted to GitHub)")
    score_line = " | ".join(f"{r.filename.split('/')[-1]}: {r.score}/10" for r in review_results)
    print(f"\n## AI Code Review Summary")
    print(f"Files reviewed: {len(review_results)} | Model: {ai_reviewer.DEFAULT_MODEL}")
    print(f"Scores: {score_line}\n")
    print("---")
    print(summary)

    # ── Final statistics ──────────────────────────────────────────────────────
    _print_header("Test Complete")
    print(f"  Files reviewed:   {len(review_results)}")
    print(f"  Total issues:     {sum(len(r.issues) for r in review_results)}")
    print(f"    Critical:       {sum(1 for r in review_results for i in r.issues if i.severity == 'critical')}")
    print(f"    Warnings:       {sum(1 for r in review_results for i in r.issues if i.severity == 'warning')}")
    print(f"    Suggestions:    {sum(1 for r in review_results for i in r.issues if i.severity == 'suggestion')}")
    print(f"  Average score:    {sum(r.score for r in review_results) / len(review_results):.1f}/10" if review_results else "  N/A")
    print(f"  Total time:       {total_elapsed:.1f}s")
    print(f"\n  NOTE: In real use, these comments would be posted to GitHub PR #{pr_number}")
    print(f"  URL: https://github.com/{owner}/{repo}/pull/{pr_number}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test the GitHub Code Review Bot without a webhook.",
        epilog="Example: python test_review.py --owner psf --repo requests --pr 6710",
    )
    parser.add_argument(
        "--owner", default=DEFAULT_OWNER,
        help=f"GitHub repo owner (default: {DEFAULT_OWNER})"
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO,
        help=f"GitHub repo name (default: {DEFAULT_REPO})"
    )
    parser.add_argument(
        "--pr", type=int, default=DEFAULT_PR,
        help=f"Pull request number (default: {DEFAULT_PR})"
    )
    parser.add_argument(
        "--token", default="",
        help="GitHub personal access token (optional — public repos work without one)"
    )

    args = parser.parse_args()

    import os
    from dotenv import load_dotenv
    load_dotenv()

    # Use CLI arg if provided, otherwise fall back to env var
    token = args.token or os.getenv("GITHUB_TOKEN", "")

    run_test(args.owner, args.repo, args.pr, github_token=token)


if __name__ == "__main__":
    main()
