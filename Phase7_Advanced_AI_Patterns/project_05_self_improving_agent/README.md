# Phase 7 · Project 5 — Self-Improving Agent (Reflexion Pattern)

## What Is Reflexion?

Reflexion is a technique introduced by Shinn et al. in **"Reflexion: Language Agents with Verbal Reinforcement Learning"** (2023) — [arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366).

The core insight: **LLMs are better at evaluating than generating**. When you ask a model to critique an answer, it reliably spots flaws it missed while writing it. Reflexion exploits this by turning self-critique into an iterative improvement loop — no gradient descent, no human labels, no fine-tuning required.

> "Verbal reinforcement" = using the model's own words as the feedback signal, just like RL uses reward signals.

---

## Why Self-Critique Works

| Why models miss things on generation | Why they catch them on critique |
|--------------------------------------|----------------------------------|
| Generation is a forward pass — no looking back | Critique is an evaluation task — looking at a finished product |
| "Satisficing" — stop when the answer seems good enough | Adversarial persona ("harsh critic") activates fault-finding |
| Hard to hold all constraints in mind simultaneously | Constraints become explicit evaluation criteria |
| Confidence bias — first draft feels correct | Distance from the text reduces anchoring bias |

This is why code review catches more bugs than the original author — same principle, different medium.

---

## The Reflexion Loop

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  [GENERATE]                                                      │
│  Produce an answer (first pass: cold start, later: improvement) │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  [CRITIQUE]                                                      │
│  "Act as a harsh critic. What is wrong, missing, or imprecise?" │
│  → Identifies specific flaws in the generated answer            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  [REFLECT]                                                       │
│  "Given this critique, list 3 specific improvements."           │
│  → Converts diagnosis into an actionable prescription           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  [REGENERATE]                                                    │
│  Previous answer + reflection → improved answer                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  [SCORE]                                                         │
│  LLM-as-judge rates the answer 1–10                             │
│  score ≥ 8  →  ACCEPT (done)                                    │
│  score < 8 and iterations < 3  →  LOOP (generate again)        │
└─────────────────────────────────────────────────────────────────┘
```

The loop is implemented as a **LangGraph StateGraph** with a conditional edge after the Score node.

---

## Architecture

```
SelfImprovingAgent
│
├── _build_graph()          Wires up the LangGraph StateGraph
│
├── generate_node()         Generates or improves the answer
├── critique_node()         Harsh critic — finds flaws
├── reflect_node()          Converts critique → 3 actionable improvements
├── score_node()            LLM-as-judge rates the answer 1-10
│
└── should_continue_edge()  Routing: loop back or accept?

ReflexionState (TypedDict)
├── query          : original question
├── attempts       : list of generated answers (one per iteration)
├── critiques      : one critique per attempt
├── reflections    : one improvement plan per critique
├── scores         : one score per attempt
├── final_answer   : the accepted answer
└── iterations     : iteration counter
```

---

## Setup & Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running with gemma3:4b
ollama pull gemma3:4b
ollama serve

# Run the demo
python self_improving_agent.py
```

---

## When to Use Reflexion

**Good fits:**
- Complex technical explanations where precision matters
- Analytical tasks with multiple dimensions (trade-offs, comparisons)
- Creative writing where structure and completeness matter
- Any task where you can define clear quality criteria

**Poor fits:**
- Simple factual lookups ("What is the capital of France?") — no room to improve
- Real-time applications — 3 iterations = 3× latency
- Tasks requiring external validation (math proofs, code execution)

---

## Limitations & Risks

### "Echo Chamber" Risk
If the model agrees with its own mistakes (confirmation bias), the critique will be too gentle and the loop terminates early with a mediocre answer. Mitigation: use a harsher critic prompt or separate critic/generator model instances.

### Over-Optimisation
The agent may optimise for sounding good rather than being correct. A high score from the LLM-judge does not guarantee factual accuracy — LLMs can hallucinate confidently. Mitigation: add external validation (unit tests, search, retrieval) for factual claims.

### Compute Cost
Each iteration triples the number of LLM calls (generate + critique + reflect + score = 4 calls per iteration). For production, cache critiques or use smaller models for evaluation.

### Score Calibration
Different models interpret "rate 1-10" differently. A Gemma 3 4b "8" may not equal a GPT-4o "8". The threshold (8) may need tuning per model.

---

## Further Reading

- Shinn et al. "Reflexion" (2023): https://arxiv.org/abs/2303.11366
- Zheng et al. "Judging LLM-as-a-Judge" (2023): https://arxiv.org/abs/2306.05685
- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- "Self-Refine" (Madaan et al. 2023) — similar approach: https://arxiv.org/abs/2303.17651
