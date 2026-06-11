# Phase 8 — Project 1: Slack AI Bot

A Slack bot that brings your local Ollama AI directly into your workspace. Answer questions, summarise threads, and brainstorm ideas — all powered by a model running on your own machine.

---

## What It Does

The bot responds to three types of input:

**Direct Messages**
Send any message to the bot in a DM and it replies with an AI-generated answer. The bot adds an ⏳ hourglass reaction while it's thinking, then removes it when the response is ready.

**@Mentions in Channels**
Tag the bot in any channel it belongs to:
```
@OllamaBot can you explain the CAP theorem?
```

**Slash Commands**

| Command | What it does | Example |
|---|---|---|
| `/ask <question>` | Get an AI answer | `/ask what is Docker?` |
| `/summarize` | Summarise last 10 messages in current channel | `/summarize` |
| `/brainstorm <topic>` | Generate 5 creative ideas | `/brainstorm onboarding improvements` |

---

## Architecture

```
Slack workspace
     │
     │  WebSocket (persistent connection — no public URL needed)
     ▼
slack_bolt SocketModeHandler
     │
     ├── @app.message(".*")        → DMs and channel messages
     ├── @app.event("app_mention") → When bot is @mentioned
     ├── @app.command("/ask")      → /ask slash command
     ├── @app.command("/summarize")→ /summarize slash command
     └── @app.command("/brainstorm")→ /brainstorm slash command
                  │
                  ▼
          ai_handler.py
          ├── process_slack_message()
          ├── summarize_messages()
          └── brainstorm()
                  │
                  ▼
     Ollama (local LLM server)
     http://localhost:11434/v1
     Model: gemma3:4b (configurable)
```

**Why Socket Mode?**
Socket Mode keeps a WebSocket connection from your machine to Slack's servers. This means you don't need a public IP address or a tool like ngrok — perfect for local development and private deployments.

**Why Ollama?**
All AI processing stays on your machine. No data sent to OpenAI, no API costs, no rate limits from a cloud provider.

---

## Setup

See [setup_guide.md](setup_guide.md) for the complete step-by-step guide, including:
- Creating the Slack app at api.slack.com
- Configuring OAuth scopes
- Enabling Socket Mode
- Adding slash commands
- Getting your tokens

**Quick start (after setup):**
```bash
# Activate the project virtualenv first so deps land in the right interpreter
source ~/Documents/my-ai-project/ai-env/bin/activate

cp .env.example .env
# Fill in SLACK_BOT_TOKEN and SLACK_APP_TOKEN

pip install -r requirements.txt
python bot.py
```

> Requires a running Ollama (`ollama serve`) with the `gemma3:4b` model pulled,
> plus a Slack app with a Bot Token (`xoxb-…`) and an App-Level Token (`xapp-…`)
> for Socket Mode. See setup_guide.md for how to obtain both tokens.

---

## Slash Commands Reference

### `/ask <question>`
Sends your question to the AI and posts the answer in the current channel.

```
/ask what are the SOLID principles in software engineering?
```

The bot posts a "Thinking..." placeholder immediately (so Slack doesn't show an error), then updates it with the real answer.

### `/summarize`
Fetches the 10 most recent messages in the current channel and asks the AI to summarise them in bullet points, highlighting key decisions, action items, and open questions.

Requires the `channels:history` scope (or `groups:history` for private channels).

### `/brainstorm <topic>`
Generates 5 creative, practical ideas about the given topic.

```
/brainstorm ways to make our weekly standups more engaging
```

The AI uses a higher temperature (0.9) for brainstorming to produce more diverse ideas compared to factual Q&A (0.7).

---

## Rate Limiting

The bot enforces a 10-second cooldown per user. This prevents:
- Accidental loops (a bot responding to itself)
- Overloading the local Ollama server
- Runaway usage in shared workspaces

The limit is configured via `RATE_LIMIT_SECONDS` in `bot.py`.

---

## How to Extend

**Add a new slash command:**
1. Register the command in the Slack app dashboard (Slash Commands → Create New Command)
2. Add a handler in `bot.py`:
```python
@app.command("/mycommand")
def handle_mycommand(ack, body, client):
    ack()
    topic = body.get("text", "")
    # ... call ai_handler or custom logic
```
3. Optionally add a new function in `ai_handler.py`

**Add a new AI function:**
Add a function to `ai_handler.py` following the existing pattern:
```python
def my_function(input: str) -> list[str]:
    response = _client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": input}],
    )
    return _split_long_response(response.choices[0].message.content or "")
```

**Use a different model:**
Change `DEFAULT_MODEL` in `.env`:
```
DEFAULT_MODEL=llama3:8b
```
Any model installed in Ollama works without code changes.

**Add thread-aware context:**
The `context` dict passed to `process_slack_message()` is designed for future thread context. You can fetch thread history via `client.conversations_replies()` and pass it along.
