# Project 03: Email Intelligence Agent

## What It Does

An AI agent that reads a local email database, classifies emails by category and priority, drafts professional replies, and generates a structured daily digest — all powered by a local LLM via Ollama.

## Architecture

```
EmailDatabase      — SQLite store with 20 seeded realistic emails
EmailClassifier    — LLM classifies: category, priority, sentiment, requires_reply
ReplyDrafter       — LLM drafts professional replies, flags complex issues
DigestGenerator    — Aggregates inbox into daily summary (Python stats + LLM)
EmailAgent         — Orchestrates everything, provides interactive CLI
```

## How to Run

```bash
# 1. Ensure Ollama is running with gemma3:4b
ollama pull gemma3:4b
ollama serve

# 2. Install dependencies (stdlib + openai)
pip install openai

# 3. Run the agent
python email_agent.py
```

On first run, 20 realistic sample emails are seeded into `emails.db`.

## Interactive Menu

```
[1] List all emails          — Show all emails with their classification status
[2] Process inbox            — Classify all unprocessed emails (LLM call per email)
[3] Handle specific email    — Classify + draft reply for one email
[4] Generate daily digest    — Print structured summary of the full inbox
[5] Quit
```

## Email Categories

| Category | Description | Example |
|----------|-------------|---------|
| support | Technical questions, bug reports | SDK timeout question |
| sales | Inquiries, partnerships, demos | White-label request |
| spam | Unsolicited/phishing email | Lottery winning scam |
| newsletter | Automated subscriptions | TLDR Tech, HN Digest |
| urgent | Production outages, legal threats | DB down, C&D letter |
| meeting | Meeting requests, scheduling | AI strategy alignment |
| other | Billing, notifications, job offers | Stripe invoice |

## Extending to Real Gmail API

This simulation uses the same classification/drafting logic that would work with the real Gmail API. To connect to real Gmail:

### Step 1: Set up Gmail API credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable Gmail API
3. Create OAuth 2.0 credentials → Download `credentials.json`

### Step 2: Install the Gmail client
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Step 3: Replace `EmailDatabase` with a Gmail reader

```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

def fetch_inbox_emails(service, max_results=20):
    results = service.users().messages().list(
        userId='me', labelIds=['INBOX'], maxResults=max_results
    ).execute()
    
    emails = []
    for msg_ref in results.get('messages', []):
        msg = service.users().messages().get(
            userId='me', id=msg_ref['id'], format='full'
        ).execute()
        # Parse headers and body from the Gmail message format
        # Then pass to your EmailClassifier — it works identically
        emails.append(parse_gmail_message(msg))
    return emails
```

Full Gmail quickstart: https://developers.google.com/gmail/api/quickstart/python

### Step 4: Send drafted replies via Gmail API

```python
import base64
from email.mime.text import MIMEText

def send_reply(service, to, subject, body, thread_id):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = f"Re: {subject}"
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(
        userId='me',
        body={'raw': raw, 'threadId': thread_id}
    ).execute()
```

The `EmailClassifier`, `ReplyDrafter`, and `DigestGenerator` classes work identically — you only replace the data layer.

## Key Learning Points

1. **Structured LLM output** — Using JSON prompts to get machine-readable responses
2. **Fallback handling** — Every LLM call has a fallback if the model returns garbage
3. **Separation of concerns** — Each class has one job; the Agent orchestrates
4. **Human-in-the-loop** — The agent flags complex emails for human review instead of auto-sending
5. **SQLite for persistence** — Zero-setup database perfect for demos and small-scale production
