
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Integrations & Shipping | Project 2: GitHub Code Review Bot
# File: github_client.py
# Purpose: Thin wrapper around the GitHub REST API v3.
#
# Why a separate client module?
#   • Centralises all GitHub API logic.  If GitHub changes their API or
#     we switch to their GraphQL API, we only change this file.
#   • Keeps review_bot.py focused on orchestration, not HTTP details.
#   • Makes unit testing easy — mock this module in tests.
#
# Authentication:
#   GitHub API calls use a Personal Access Token (PAT) or a fine-grained
#   token.  For public repos, GET requests work without authentication but
#   are rate-limited to 60 requests/hour.  With a token you get 5 000/hour.
#
# Error handling:
#   We raise exceptions on HTTP errors so the caller (review_bot.py) can
#   decide whether to retry, log, or skip.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("github_client")

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """
    Thin wrapper around the GitHub REST API.

    Usage:
        client = GitHubClient()  # reads GITHUB_TOKEN from env
        diff = client.get_pr_diff("octocat", "hello-world", 1)
    """

    def __init__(self, token: str | None = None) -> None:
        """
        Args:
            token: GitHub personal access token.  If None, reads GITHUB_TOKEN
                   from the environment.  Works without a token for public repos
                   (but rate-limited to 60 req/hour).
        """
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        self._session = requests.Session()

        # Set common headers for all requests
        self._session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

        # Only add the Authorization header if we have a token.
        # This allows the client to work (rate-limited) with public repos.
        if self._token:
            self._session.headers["Authorization"] = f"Bearer {self._token}"

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        """
        Make an authenticated GET request and raise on HTTP errors.

        Centralising GET calls here means we can add retries, caching,
        or logging in one place if needed later.
        """
        response = self._session.get(url, **kwargs)
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
        return response

    def _post(self, url: str, json_body: dict[str, Any]) -> requests.Response:
        """Make an authenticated POST request and raise on HTTP errors."""
        response = self._session.post(url, json=json_body)
        response.raise_for_status()
        return response

    # ── Pull Request Methods ───────────────────────────────────────────────────

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """
        Fetch the unified diff for a pull request.

        GitHub returns the diff when you request the PR with the
        `application/vnd.github.diff` Accept header.

        Args:
            owner:     Repository owner (username or org name).
            repo:      Repository name.
            pr_number: The pull request number.

        Returns:
            The raw unified diff as a string.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
        log.info("Fetching diff for %s/%s PR #%d", owner, repo, pr_number)

        # GitHub serves the diff when we request this specific content type
        response = self._get(
            url,
            headers={"Accept": "application/vnd.github.diff"},
        )
        return response.text

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """
        List all files changed in a pull request.

        Returns a list of file objects.  Each dict has (among others):
          - filename:    The file path (e.g., "src/auth.py")
          - status:      "added" | "modified" | "removed" | "renamed"
          - additions:   Number of lines added
          - deletions:   Number of lines deleted
          - patch:       The file-level unified diff (may be absent for binary files)

        See: https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files

        We use this instead of parsing the full diff ourselves — GitHub already
        splits the diff into per-file chunks for us.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        log.info("Fetching files for %s/%s PR #%d", owner, repo, pr_number)

        # The API paginates at 100 files per page.  We handle pagination so
        # large PRs don't silently drop files.
        all_files: list[dict[str, Any]] = []
        page = 1

        while True:
            response = self._get(url, params={"per_page": 100, "page": page})
            batch: list[dict[str, Any]] = response.json()

            if not batch:
                break  # No more pages

            all_files.extend(batch)

            # If we got fewer than 100 results, we've reached the last page
            if len(batch) < 100:
                break

            page += 1

        log.info("Found %d changed files", len(all_files))
        return all_files

    def get_pr_info(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """
        Fetch metadata about a pull request (title, body, head commit SHA, etc.).

        The head commit SHA is needed for posting inline review comments — GitHub
        requires you to specify which commit the comment refers to.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = self._get(url)
        return response.json()

    def post_pr_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict[str, Any]:
        """
        Post a general comment on a pull request (not inline on a specific line).

        This is the PR's "Review" or "Conversation" tab comment — it appears
        at the bottom of the PR and is visible to all reviewers.

        Args:
            owner:     Repository owner.
            repo:      Repository name.
            pr_number: The pull request number.
            body:      Comment text in GitHub-flavoured markdown.

        Returns:
            The created comment object from the GitHub API.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        # Note: We use the Issues API endpoint here — in GitHub's data model,
        # PRs are a special type of issue, so issue comments appear on PRs too.
        log.info("Posting general comment on %s/%s PR #%d", owner, repo, pr_number)
        response = self._post(url, json_body={"body": body})
        return response.json()

    def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        path: str,
        line: int,
        body: str,
    ) -> dict[str, Any]:
        """
        Post an inline review comment on a specific line of a specific file.

        This creates a comment that appears inline in the diff view — the kind
        of comment you see when a reviewer clicks on a line and types a note.

        Args:
            owner:      Repository owner.
            repo:       Repository name.
            pr_number:  The pull request number.
            commit_sha: SHA of the head commit — GitHub needs this to anchor
                        the comment to the exact version of the code.
            path:       File path within the repo (e.g., "src/auth.py").
            line:       Line number in the *new* version of the file.
            body:       Comment text (GitHub-flavoured markdown).

        Returns:
            The created review comment object from the GitHub API.

        Note:
            This is different from a pull request review (which has an
            "approve" or "request changes" state).  We're posting individual
            inline comments directly.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        log.info(
            "Posting inline comment on %s/%s PR #%d, file %s line %d",
            owner, repo, pr_number, path, line,
        )
        payload = {
            "body": body,
            "commit_id": commit_sha,
            "path": path,
            "line": line,
            # "side": "RIGHT" means the comment goes on the new version of the
            # file (the right side of the diff).  "LEFT" would be the old version.
            "side": "RIGHT",
        }
        try:
            response = self._post(url, json_body=payload)
            return response.json()
        except requests.HTTPError as exc:
            # Inline comments fail if the line isn't part of the diff hunk.
            # We log and skip rather than crashing the whole review pipeline.
            log.warning(
                "Could not post inline comment on %s:%d (line may not be in diff): %s",
                path, line, exc,
            )
            return {}
