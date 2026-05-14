# Project 01 — Tool-Calling Agent 🔧

> **Week 7 · Phase 3 · Agentic Stack**

## What You'll Learn

How to give an AI agent the ability to **use tools** — like a calculator, clock,
and word counter — so it can do real work, not just chat.

The pattern you're learning is called **ReAct**: Reason → Act → Observe.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve` in a separate terminal)
- [ ] `gemma3:4b` is pulled (`ollama pull gemma3:4b`)
- [ ] Virtual environment is active (`source ~/Documents/my-ai-project/ai-env/bin/activate`)

---

## How to Run — Step by Step

**Terminal 1** (keep open the whole time):
```bash
ollama serve
```

**Terminal 2** (run the project):
```bash
# Step 1 — Activate your virtual environment
source ~/Documents/my-ai-project/ai-env/bin/activate

# Step 2 — Navigate to this project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase3_Agentic_Stack/project_01_tool_calling_agent

# Step 3 — Run the agent
python tool_calling_agent.py
```

---

## Test It — Try These Inputs

```
What is 1234 * 5678?
What time is it right now?
How many words are in 'The quick brown fox jumps over the lazy dog'?
Convert 100 Celsius to Fahrenheit
```

---

## Expected Terminal Output

```
============================================================
🤖 Tool-Calling Agent — Phase 3, Project 1
============================================================
Model: gemma3:4b (local via Ollama)

Available tools: calculator, get_current_time,
                 word_counter, temperature_converter

You: What is 1234 * 5678?

🤔 Thinking... done
🔧 Using tool: calculator
✅ Tool result: 7006652
🤖 Agent: The result of 1234 × 5678 is 7,006,652.
```

---

## Verification Checklist

- [ ] Agent prints `🔧 Using tool: calculator` for math questions
- [ ] Agent prints `🔧 Using tool: get_current_time` for time questions
- [ ] Tool results appear **before** the final answer
- [ ] Conversation history works — ask a follow-up about a previous answer
- [ ] Type `quit` to exit cleanly

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `ConnectionError` / `Failed to connect` | Ollama is not running → run `ollama serve` in Terminal 1 |
| `model not found` | Pull the model: `ollama pull gemma3:4b` |
| `ModuleNotFoundError: openai` | Activate venv first: `source ~/Documents/my-ai-project/ai-env/bin/activate` |
| Agent answers without using a tool | Normal — try a more explicit question like `Calculate 25 * 48` |

---

## Key Concepts

- **ReAct pattern**: Reason → Act → Observe (the backbone of all agents)
- **Tool registry**: A dictionary mapping tool names to Python functions
- **Tool parsing**: The model returns JSON like `{"tool": "calculator", "args": {"expression": "2+2"}}`
- **Two LLM calls**: First call decides what to do, second call summarises the tool result

## Status

⏳ Ready to run — `ollama serve` must be running first
