# Project 05 — Custom Agent Framework 🧩

> **Week 15 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build your **own mini LangChain** from scratch — understand exactly how
agent frameworks work under the hood, with zero black boxes.
Once you build it yourself, LangChain becomes completely obvious.

---

## Concept: What Is an Agent Framework?

LangChain, LlamaIndex, and AutoGen all do the same thing at their core:

```
1. Plan    — Break the task into steps
2. Act     — Call a tool or the LLM
3. Observe — Read the result
4. Loop    — Decide what to do next
```

This is called the **ReAct loop** (Reason + Act).

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:27b` is pulled
- [ ] Virtual environment is active
- [ ] No extra libraries needed — pure Python

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
cd ~/Documents/"Agentic AI learning Roadmap"/Phase4_Agent_Framework/project_05_custom_agent_framework

# Run the agent
python custom_agent_framework.py
```

---

## Test Inputs — Try These

```
What is 144 divided by 12?
What time is it right now?
Save a note: custom frameworks are powerful
Read my notes
Convert 100 celsius to fahrenheit
How many words are in: the quick brown fox jumps over the lazy dog
```

Type `quit` or `exit` to stop.

---

## Built-in Tools

| Tool | What It Does |
|------|-------------|
| `calculator` | Evaluates math expressions |
| `get_time` | Returns current date and time |
| `save_note` | Saves text to a notes file |
| `read_notes` | Reads all saved notes |
| `celsius_to_fahrenheit` | Temperature conversion |
| `count_words` | Counts words in a string |

---

## Framework Components

| Class | Purpose |
|-------|---------|
| `ToolRegistry` | Stores tools via `@registry.tool()` decorator |
| `AgentMemory` | Tracks conversation + tool observations |
| `Planner` | Breaks big goals into sub-steps |
| `ReActAgent` | Main controller running the ReAct loop |

---

## Expected Terminal Output

```
🧩 Custom Agent Framework — Phase 4, Project 5
============================================================
Model: gemma3:27b | Tools: 6 registered | max_steps: 6

You: What is 144 divided by 12?
[Step 1] Thinking...
  → Tool: calculator
  → Input: 144/12
  → Result: 12.0
[Step 2] Composing answer...
Agent: 144 divided by 12 equals 12.

You: What time is it right now?
[Step 1] Thinking...
  → Tool: get_time
  → Result: Wednesday, 2026-05-13 10:42:07
Agent: The current time is 10:42 AM on Wednesday, May 13, 2026.
```

---

## Verification Checklist

- [ ] Math questions show `→ Tool: calculator` in the step output
- [ ] `get_time` returns the current date and time
- [ ] `save_note` creates a `notes.txt` file in the project folder
- [ ] `read_notes` reads back what you saved
- [ ] Verbose step-by-step reasoning is shown for each query
- [ ] Agent completes in at most 6 steps per query

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Unknown tool` in response | Model chose a non-existent tool — it will fall back to direct answer |
| Very slow first response | `gemma3:27b` is loading into memory — subsequent queries are faster |
| `Connection refused` | Ollama is not running — run `ollama serve` |
| Notes not saving | Check you have write permission in this folder |

---

## Status

⏳ Ready to run — the most educational project in Phase 4!
