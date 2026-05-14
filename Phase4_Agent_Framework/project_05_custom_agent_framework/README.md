# Project 05 — Custom Agent Framework 🧩

> **Week 15 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build your **own mini LangChain** from scratch — understand exactly how
agent frameworks work under the hood, with no black boxes.

## Concept: What Is an Agent Framework?

LangChain, LlamaIndex, and AutoGen all do the same thing at their core:

```
1. Plan    — Break the task into steps
2. Act     — Call a tool or LLM
3. Observe — Read the result
4. Loop    — Decide what to do next
```

This is called the **ReAct loop** (Reason + Act).

## What You're Building

A mini framework with these components:

| Component | Purpose |
|-----------|---------|
| `Agent` | The main controller (ReAct loop) |
| `Tool` | Decorator to register tools |
| `Memory` | Stores conversation + observations |
| `Planner` | Breaks big tasks into subtasks |
| `Runner` | Executes the agent loop |

## Stack

- **Pure Python** — no LangChain, no extra libraries
- **Ollama gemma3:4b** for intelligence
- **~200 lines of core framework code**

## How to Run

```bash
ollama serve
source ~/Documents/my-ai-project/ai-env/bin/activate
python custom_agent_framework.py
```

## Why Build From Scratch?

Once you build it yourself, LangChain becomes obvious.
You'll understand every line of production agent code.

## Status

⏳ Ready to run — the most educational project in Phase 4!
