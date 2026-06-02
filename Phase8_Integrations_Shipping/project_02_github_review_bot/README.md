# Phase 8 — Project 2: GitHub Code Review Bot

An automated code review bot that triggers on GitHub pull requests, sends each changed file's diff to a local Ollama AI for review, and posts inline comments and a summary back to the PR.

---

## What It Does

When a pull request is opened or updated:

1. GitHub sends a webhook event to your bot
2. The bot fetches the list of changed files via the GitHub API
3. Each file's diff is sent to the local AI for review
4. The AI identifies bugs, security issues, performance problems, and style issues
5. Inline comments are posted on the specific lines with issues
6. An overall summary comment is posted on the PR

**Example inline comment:**
> 🔴 **CRITICAL** — SQL query is constructed with string formatting, making it vulnerable to SQL injection. Use parameterized queries instead.
> *Automated review by AI bot (model: gemma3:4b)*

**Example summary:**
> ## AI Code Review Summary
> Files reviewed: 3 | Model: gemma3:4b
> Scores: auth.py: 4/10 | utils.py: 8/10 | models.py: 7/10
> ...

---

## Architecture

```
GitHub repository
       │
       │  PR opened / commits pushed
       │
       ▼
GitHub Webhook  ──POST /webhook──►  FastAPI (review_bot.py)
                                          │
                                          │  1. Verify HMAC-SHA256 signature
                                          │  2. Parse PR event
                                          │  3. Background task →
                                          │
                              ┌───────────┴───────────────────┐
                              │                               │
                       github_client.py               ai_reviewer.py
                       get_pr_files()                 review_file()
                       get_pr_diff()                  review_pr_summary()
                       post_pr_comment()                      │
                       post_review_comment()                  ▼
                              │                    Ollama (local LLM)
                              │                    http://localhost:11434
                              ▼
                    GitHub PR — inline comments + summary posted
```

**Why FastAPI?**
FastAPI is async-native, which lets us return a 200 response to GitHub immediately (GitHub times out after 10 seconds) while running the review pipeline in the background via `asyncio.create_task()`.

**Why HMAC signature verification?**
The `/webhook` endpoint is publicly accessible when using ngrok.  Without signature verification, anyone could POST fake PR events and trigger your bot.  GitHub signs every payload with your webhook secret — we verify this signature on every request.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in:
- `GITHUB_TOKEN` — Personal access token with `repo` scope (for private repos) or just `public_repo` for public repos
- `GITHUB_WEBHOOK_SECRET` — Any random secret string (you'll enter the same one in GitHub)
- `DEFAULT_MODEL` — Ollama model name (must be pulled with `ollama pull <model>`)

Generate a secure webhook secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start the bot

```bash
python review_bot.py
```

The server starts on `http://0.0.0.0:8000`.

---

## Setting Up the GitHub Webhook

### Using ngrok for local testing

You need a public URL that GitHub can reach.  ngrok creates an encrypted tunnel from a public URL to your local port.

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
```

ngrok outputs something like:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

### Configure the webhook in GitHub

1. Go to your repository on GitHub
2. Click **Settings** → **Webhooks** → **Add webhook**
3. Fill in:
   - **Payload URL:** `https://abc123.ngrok-free.app/webhook` (your ngrok URL)
   - **Content type:** `application/json`
   - **Secret:** The same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
   - **Which events:** Select "Let me select individual events" → check **"Pull requests"**
4. Click **Add webhook**

GitHub will immediately send a ping event to verify the connection.  You should see it in the bot's logs.

---

## Testing Without a Webhook

Run `test_review.py` to test the AI review pipeline against any public PR:

```bash
# Test with the default target (psf/requests PR #6710)
python test_review.py

# Test with a specific PR
python test_review.py --owner microsoft --repo vscode --pr 200000

# With your GitHub token (higher rate limit)
python test_review.py --token ghp_yourtoken
```

This runs the full pipeline and prints what would be posted to GitHub, without actually posting anything.

---

## Webhook Payload Format

GitHub sends a JSON body like this for `pull_request` events:

```json
{
  "action": "opened",
  "pull_request": {
    "number": 42,
    "title": "Fix authentication bug",
    "head": {
      "sha": "abc123..."
    }
  },
  "repository": {
    "name": "my-repo",
    "owner": {
      "login": "my-username"
    }
  }
}
```

Actions we handle: `opened`, `synchronize` (new commits pushed).
All other actions return `{"status": "ignored"}`.

---

## Files That Are Reviewed

The bot reviews source code files and skips:
- Binary files (images, model weights, PDFs)
- Lock files (package-lock.json, Pipfile.lock, go.sum)
- Minified files (*.min.js, *.min.css)
- Deleted files (no value in reviewing removed code)

Files are prioritised by number of changed lines — the most-changed files get reviewed first.  A maximum of 10 files are reviewed per PR to keep response time reasonable.

---

## Review Severity Levels

| Level | Icon | Meaning |
|---|---|---|
| `critical` | 🔴 | Must fix before merging — security holes, definite bugs, data loss risk |
| `warning` | 🟡 | Should fix — likely bugs, performance issues, unclear logic |
| `suggestion` | 💡 | Nice to have — style, readability, minor improvements |

Critical and warning issues are posted as inline comments on the specific line.
Suggestions appear only in the overall summary.

---

## How to Extend

**Add a custom review rule:**
Modify the system prompt in `ai_reviewer.py → review_file()`. Add your rule to the numbered list:
```python
"5. DEPENDENCY — flag use of deprecated or unmaintained libraries"
```

**Filter specific file types:**
Add extensions to `SKIP_EXTENSIONS` in `review_bot.py`:
```python
SKIP_EXTENSIONS = {".png", ..., ".generated.ts"}  # skip generated TypeScript
```

**Review more files per PR:**
Increase `MAX_FILES_TO_REVIEW` in `review_bot.py` (at the cost of longer review time).

**Post a GitHub "Review" instead of individual comments:**
Replace `post_review_comment()` calls with the Pull Request Reviews API
(`POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews`) to submit all comments
as a single review with an approve/request-changes state.

**Deploy to a server:**
Remove ngrok and configure the webhook to point to your server's public IP/domain.
Add a reverse proxy (nginx/caddy) in front of uvicorn for TLS termination.
