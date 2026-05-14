# Project 03 — Web Scraping Agent 🌐

> **Week 9 · Phase 3 · Agentic Stack**

## What You'll Learn

How to feed **real web content** to your AI agent using web scraping —
so it can answer questions about any public website in real time.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:4b` is pulled
- [ ] Virtual environment is active
- [ ] `requests` and `beautifulsoup4` installed (see install step below)
- [ ] Internet connection

---

## How to Run — Step by Step

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2:**
```bash
# Step 1 — Install libraries (one time only)
pip install requests beautifulsoup4 --break-system-packages

# Step 2 — Activate venv
source ~/Documents/my-ai-project/ai-env/bin/activate

# Step 3 — Navigate to project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase3_Agentic_Stack/project_03_web_scraping_agent

# Step 4 — Run the agent
python web_scraping_agent.py
```

Then in the agent:
```
scrape https://en.wikipedia.org/wiki/Artificial_intelligence
ask What are the main types of AI?
```

---

## Commands Inside the Agent

| Command | What It Does |
|---------|-------------|
| `scrape <url>` | Fetch and read a web page |
| `ask <question>` | Ask about the last scraped page |
| `list` | Show all scraped pages this session |
| `show` | Show the current page content |
| `help` | Show all commands |
| `quit` | Exit |

---

## Test It — Try These

```
scrape https://en.wikipedia.org/wiki/Python_(programming_language)
ask Who created Python and when?

scrape https://news.ycombinator.com
ask What are the top 3 stories?
```

---

## Expected Terminal Output

```
🌐 Fetching: https://en.wikipedia.org/wiki/Python_(programming_language)
  ✅ Scraped 3842 characters from 'Python (programming language)'

📄 Preview: Python is a high-level, general-purpose programming language...

✅ Page loaded! Now use 'ask <your question>' to query it.

You: ask Who created Python?
🤔 Thinking... done
🤖 Agent: Python was created by Guido van Rossum and was first released in 1991.
```

---

## Verification Checklist

- [ ] Scraping Wikipedia shows the character count and preview text
- [ ] Agent answers questions **only from the scraped content**, not from training data
- [ ] Try asking something NOT on the page — agent should say it's not there
- [ ] `list` command shows all pages scraped this session
- [ ] Scraping two different pages and switching between them works

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `ConnectionError on scrape` | No internet — check your Wi-Fi |
| `HTTP 403 / 429 error` | Site blocked the request — try Wikipedia or news.ycombinator.com |
| `ImportError: No module named 'bs4'` | Run: `pip install beautifulsoup4 --break-system-packages` |
| `ImportError: No module named 'requests'` | Run: `pip install requests --break-system-packages` |
| Answer seems wrong | The agent only knows what it scraped — re-scrape the page if needed |

## Status

⏳ Ready to run — needs internet connection for web scraping
