# Slack App Setup Guide

This guide walks you through creating a Slack app, configuring it for Socket Mode, and connecting it to the bot.

---

## Step 1 — Create the Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and sign in.
2. Click **"Create New App"**.
3. Choose **"From scratch"**.
4. Enter an **App Name** (e.g., `OllamaBot`) and select your **workspace**.
5. Click **"Create App"**.

---

## Step 2 — Enable Socket Mode

Socket Mode lets your bot connect to Slack via a WebSocket instead of requiring a public HTTP endpoint.

1. In the left sidebar, click **"Socket Mode"**.
2. Toggle **"Enable Socket Mode"** to **On**.
3. You'll be prompted to create an **App-Level Token**:
   - Name it something like `socket-token`.
   - Add the scope: `connections:write`.
   - Click **"Generate"**.
4. Copy the token — it starts with `xapp-`. Save it as `SLACK_APP_TOKEN` in your `.env`.

---

## Step 3 — Add OAuth Scopes (Bot Token Scopes)

Your bot needs these permissions to function:

1. In the left sidebar, click **"OAuth & Permissions"**.
2. Scroll to **"Scopes" → "Bot Token Scopes"**.
3. Click **"Add an OAuth Scope"** and add each of the following:

| Scope | Why it's needed |
|---|---|
| `chat:write` | Post messages to channels and DMs |
| `channels:history` | Read public channel history (for /summarize) |
| `groups:history` | Read private channel history (for /summarize in private channels) |
| `im:history` | Read DM history |
| `app_mentions:read` | Receive events when bot is @mentioned |
| `reactions:write` | Add/remove the ⏳ hourglass reaction |
| `commands` | Register and handle slash commands |

---

## Step 4 — Add Slash Commands

1. In the left sidebar, click **"Slash Commands"**.
2. Click **"Create New Command"** for each command:

### /ask
- **Command:** `/ask`
- **Request URL:** Leave blank (Socket Mode handles this)
- **Short Description:** `Ask the AI a question`
- **Usage Hint:** `[your question]`

### /summarize
- **Command:** `/summarize`
- **Request URL:** Leave blank
- **Short Description:** `Summarise the last 10 messages`
- **Usage Hint:** (no arguments)

### /brainstorm
- **Command:** `/brainstorm`
- **Request URL:** Leave blank
- **Short Description:** `Generate 5 ideas on a topic`
- **Usage Hint:** `[topic]`

3. Click **"Save"** after each command.

> **Note:** For Socket Mode apps, Slack routes slash commands through the WebSocket — you don't need a public URL.

---

## Step 5 — Enable Event Subscriptions

1. In the left sidebar, click **"Event Subscriptions"**.
2. Toggle **"Enable Events"** to **On**.
3. Under **"Subscribe to bot events"**, add:
   - `app_mention` — fires when someone @-mentions the bot
   - `message.im` — fires for DM messages

4. Click **"Save Changes"**.

---

## Step 6 — Install the App to Your Workspace

1. In the left sidebar, click **"Install App"**.
2. Click **"Install to Workspace"**.
3. Review the permissions and click **"Allow"**.
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`). Save it as `SLACK_BOT_TOKEN` in your `.env`.

---

## Step 7 — Configure Your .env File

```bash
cp .env.example .env
```

Fill in:
```
SLACK_BOT_TOKEN=xoxb-...   # from Step 6
SLACK_APP_TOKEN=xapp-...   # from Step 2
OLLAMA_URL=http://localhost:11434
DEFAULT_MODEL=gemma3:4b
```

---

## Step 8 — Run the Bot

```bash
# Activate the project virtualenv so deps install into the right interpreter
source ~/Documents/my-ai-project/ai-env/bin/activate

pip install -r requirements.txt
python bot.py
```

You should see:
```
INFO  slack_bot  Starting Slack bot in Socket Mode…
INFO  slack_bolt.App  Starting to receive messages from a new connection
```

---

## Step 9 — Test It

In Slack:
- Send a DM to your bot: `What is the capital of France?`
- In a channel where the bot is present: `@OllamaBot explain recursion`
- Type `/ask what is the meaning of life?`
- Type `/brainstorm team building activities`
- In a busy channel, type `/summarize`

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `SLACK_APP_TOKEN is not set` | Missing env var | Check your `.env` file |
| `not_allowed_token_type` | Wrong token type | Make sure APP token (xapp-) is SLACK_APP_TOKEN and BOT token (xoxb-) is SLACK_BOT_TOKEN |
| Bot doesn't respond to messages | Missing event scope | Add `message.im` to bot event subscriptions |
| `/summarize` returns permission error | Missing scope | Add `channels:history` and reinstall app |
| Bot responds to every message in channels | Unintended | By default bot only responds to DMs and @mentions in channels — check the `handle_message` logic |
