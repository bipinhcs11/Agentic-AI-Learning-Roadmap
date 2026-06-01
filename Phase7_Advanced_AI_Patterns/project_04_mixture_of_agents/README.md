# Phase 7 · Project 4 — Mixture of Agents (MoA)

## What is Mixture of Experts / Agents?

**Mixture of Experts (MoE)** is a machine learning technique where a model is partitioned into specialist sub-networks ("experts"), and a lightweight "router" network decides which expert(s) to activate for each input. Only a fraction of the model parameters are used per forward pass, which makes large models computationally feasible (e.g., GPT-4, Mixtral, DeepSeek-V2 all use MoE internally).

**Mixture of Agents (MoA)** is the same idea applied at the agent level: instead of routing inside a model, you route between separate agents (or prompts). Each agent is tuned for a different task type. This project implements MoA on top of a single local model by using different system prompts and temperatures.

---

## Why One Model + Prompt Doesn't Fit All Tasks

| Task type | What it needs | What goes wrong with a generic prompt |
|-----------|---------------|---------------------------------------|
| Code generation | Determinism, syntax accuracy, type hints | Too verbose, too creative, wrong idioms |
| Creative writing | Surprise, vivid imagery, risk-taking | Too formal, too literal, clichéd |
| Data analysis | Structure, hedging, multiple perspectives | Overconfident, unsorted |
| Teaching | Analogies, step-by-step, no jargon | Too terse, skips over basics |

A single system prompt that tries to be all of these things ends up mediocre at all of them.

---

## Router Architecture

```
User query
     │
     ▼
┌─────────────────────────────────────┐
│           RouterAgent               │
│                                     │
│  1. Build routing prompt with all   │
│     agent descriptions              │
│                                     │
│  2. Call LLM → get agent name       │
│                                     │
│  3. Validate name                   │
│       ├── valid  → use LLM choice   │
│       └── invalid → keyword fallback│
│             (count strength matches)│
└──────────────┬──────────────────────┘
               │  chosen AgentSpec
               ▼
    ┌──────────────────────┐
    │   Specialist Agent   │
    │  (system prompt +    │
    │   temperature)       │
    └──────────┬───────────┘
               │
               ▼
         Response to user
```

---

## The Four Specialists

| Agent | Temperature | Optimised for |
|-------|------------|---------------|
| `CodeAgent` | 0.1 | Correct, idiomatic Python code |
| `AnalysisAgent` | 0.3 | Structured, balanced analysis |
| `CreativeAgent` | 0.8 | Imaginative, unexpected writing |
| `TeacherAgent` | 0.4 | Clear, analogy-rich explanations |

All four use `gemma3:4b` as the underlying model. In a production system you would also vary the model (e.g., a code-specific fine-tune for `CodeAgent`).

---

## How to Add Your Own Specialist

1. Add a new `AgentSpec` in `mixture_of_agents.py`:

```python
LEGAL_AGENT = AgentSpec(
    name="LegalAgent",
    description="Legal researcher. Best for: contract review, compliance questions, risk assessment.",
    system_prompt=(
        "You are a careful legal researcher. Always caveat that you are not a lawyer. "
        "Cite relevant principles. Structure answers by jurisdiction if applicable."
    ),
    temperature=0.2,
    strengths=["contract", "legal", "law", "compliance", "gdpr", "terms", "liability"],
)
```

2. Add it to `ALL_AGENTS`:

```python
ALL_AGENTS: list[AgentSpec] = [CODE_AGENT, ANALYSIS_AGENT, CREATIVE_AGENT, TEACHER_AGENT, LEGAL_AGENT]
```

That's it. The router will automatically include it in the LLM routing prompt and the keyword fallback.

---

## Real-World Applications

- **OpenAI's GPT-4 routing** — routes between GPT-4o-mini (fast, cheap) and GPT-4o (capable, expensive) based on query complexity.
- **Anthropic's Claude** — routes between Haiku, Sonnet, and Opus tiers.
- **Enterprise chatbots** — route between HR bot, IT bot, Sales bot depending on intent.
- **Coding assistants** — route between completion, explanation, debugging, and test-generation modes.
- **Mixtral 8×7B** — sparse MoE model where 2 of 8 expert FFN layers are activated per token.

---

## Setup & Run

```bash
# 1. Pull the Ollama model
ollama pull gemma3:4b

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Run the demo
python mixture_of_agents.py
```

The demo runs in four parts:
1. **Benchmark** — routes 8 questions and prints a routing table (fast, shows agent selection without waiting for full responses)
2. **Live query** — routes a coding question and shows the full CodeAgent response
3. **query_all** — sends "What is recursion?" to all 4 agents so you can compare styles
4. **Routing stats** — shows how queries were distributed

---

## Files

```
project_04_mixture_of_agents/
├── mixture_of_agents.py   — complete implementation
├── requirements.txt
└── README.md
```
