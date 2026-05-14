# Project 02 — Memory Agent 🧠

> **Week 8 · Phase 3 · Agentic Stack**

## What You'll Learn

How to give an AI agent **persistent memory** — so it remembers your name,
preferences, and facts across sessions, even after you restart the program.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:4b` is pulled
- [ ] Virtual environment is active

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
cd ~/Documents/"Agentic AI learning Roadmap"/Phase3_Agentic_Stack/project_02_memory_agent

# Run — Session 1
python memory_agent.py
```

**The memory test (do this to see it work):**
```
You: My name is Sunita
You: I work as a data analyst
You: I like learning about AI
You: quit          ← important! this saves memory.json
```

Then run again:
```bash
python memory_agent.py   # Session 2 — it should greet you by name!
```

---

## Test Inputs

```
My name is Sunita
I work as a data analyst
I like learning about AI
show memory
What do you remember about me?
clear memory
quit
```

---

## Expected Terminal Output

**First run:**
```
👋 Hello! I'm your memory-powered assistant.
   Tell me your name and I'll remember it next time!

You: My name is Sunita
🧠 Remembered: your name is Sunita
🤖 Agent: Nice to meet you, Sunita! ...

You: quit
  💾 Memory saved to memory.json
👋 Goodbye! I'll remember our conversation.
```

**Second run:**
```
👋 Welcome back, Sunita! (Session #2)
```

---

## Verification Checklist

- [ ] `memory.json` file is created in this project folder after the first `quit`
- [ ] Second run shows `Welcome back, [name]!` instead of the generic greeting
- [ ] `show memory` command displays your profile and saved facts
- [ ] Agent uses your name in responses without being asked
- [ ] `clear memory` command resets the file

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| Memory not saved on restart | You must type `quit` to exit — Ctrl+C skips saving |
| Name not recognised | Use the phrase `My name is Sunita` exactly |
| `memory.json` not found | Run the script and type `quit` — the file is created on exit |

---

## Files Created by This Project

- `memory_agent.py` — the agent code
- `memory.json` — auto-created, stores your long-term memory (can be deleted to reset)

## Status

⏳ Ready to run — works best when you run it twice to see memory in action!
