# Project 04 — Multi-Tool Agent 🛠️

> **Week 10 · Phase 3 · Agentic Stack**

## What You'll Learn

How to build an agent with **8 tools** working together — the agent
automatically picks the right tool for each question.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:4b` is pulled
- [ ] Virtual environment is active
- [ ] `requests` and `beautifulsoup4` installed

---

## How to Run — Step by Step

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2:**
```bash
# Activate venv
source ~/Documents/my-ai-project/ai-env/bin/activate

# Navigate to project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase3_Agentic_Stack/project_04_multi_tool_agent

# Run the agent
python multi_tool_agent.py
```

---

## Available Tools

| Tool | What It Does |
|------|-------------|
| `calculator` | Evaluates math expressions |
| `save_note` | Saves text to `notes.txt` |
| `read_notes` | Reads all saved notes |
| `clear_notes` | Deletes all notes |
| `list_files` | Lists files in a directory |
| `word_count` | Counts words in text |
| `web_fetch` | Fetches a web page |
| `get_current_time` | Returns current date & time |

Type `tools` inside the agent to see all 8 tools with descriptions.

---

## Test Inputs — Try These

```
What is 17% of 2500?
Save a note: learn LangChain this week
What notes do I have?
List files in ~/Downloads
What time is it?
How many words are in 'Agentic AI is the future of software'?
tools
```

---

## Expected Terminal Output

```
🛠️  Multi-Tool Agent — Phase 3, Project 4
============================================================
Model: gemma3:4b | Tools: 8 available
Notes saved to: notes.txt

You: What is 17% of 2500?
🤔 ...
🔧 calculator → 425.0
🤖 Agent: 17% of 2500 is 425.

You: Save a note: learn LangChain this week
🔧 save_note → Note saved: learn LangChain this week
🤖 Agent: Done! I've saved that note for you.
```

---

## Verification Checklist

- [ ] Math questions show `🔧 calculator →` in the output
- [ ] After `save_note`, a `notes.txt` file appears in this project folder
- [ ] `What notes do I have?` reads back the saved notes
- [ ] Type `tools` to see all 8 tools listed
- [ ] Different questions trigger different tools automatically

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Unknown tool` in output | Normal — model used a slightly different name. It still answers. |
| File listing fails | Make sure the path exists. Try: `List files in ~/Desktop` |
| Web fetch fails | Needs internet + `pip install requests beautifulsoup4 --break-system-packages` |
| Notes not saving | Check you have write permission in this folder |

---

## Files Created by This Project

- `multi_tool_agent.py` — the agent code
- `notes.txt` — auto-created when you first save a note

## Status

⏳ Ready to run — the most feature-rich agent in Phase 3!
