"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           Phase 7 · Project 4 — Mixture of Agents (MoA)                    ║
║                                                                              ║
║  THE CORE IDEA                                                               ║
║  Different tasks call for different "thinking styles".  A coding question   ║
║  benefits from a low-temperature, precise model focused on correctness.     ║
║  A creative writing prompt needs high temperature and a loose, imaginative  ║
║  framing.  Routing each query to the best-suited specialist dramatically    ║
║  outperforms using a single general-purpose prompt for everything.          ║
║                                                                              ║
║  This mirrors production systems like:                                       ║
║  • OpenAI's GPT-4 routing between 4o-mini and 4o                           ║
║  • Anthropic's internal prompt classifiers                                   ║
║  • Mistral's Mixture-of-Experts architecture (at the model level)           ║
║                                                                              ║
║  OUR APPROACH                                                                ║
║  All four specialists use the same underlying model (gemma3:4b) because we  ║
║  are running locally on Ollama.  The differentiation comes from:            ║
║    • Different system prompts (persona + instructions)                      ║
║    • Different temperatures (determinism vs creativity)                     ║
║  In production you'd swap the underlying models too.                        ║
║                                                                              ║
║  MODEL : gemma3:4b via Ollama                                               ║
║  ROUTER: gemma3:4b (LLM-based classification with keyword fallback)        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

from openai import OpenAI

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"    # Ollama ignores this; the OpenAI client needs it
CHAT_MODEL = "gemma3:4b"


# ─────────────────────────────────────────────────────────────────────────────
# Agent Specification
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentSpec:
    """
    Declarative description of one specialist agent.

    WHY a dataclass instead of subclasses?
    All four agents share the same call signature — the only differences are
    the system_prompt and temperature.  A dataclass keeps that configuration
    flat and easy to extend: to add a fifth specialist you just add one more
    AgentSpec to the list, no new class needed.

    Fields
    ------
    name         : short identifier used by the router
    description  : human-readable summary used in the routing prompt
    system_prompt: injected as the `system` message for every call
    model        : Ollama model tag
    temperature  : controls randomness — lower = more deterministic
    strengths    : keyword list for the fallback router
    """

    name: str
    description: str
    system_prompt: str
    model: str = CHAT_MODEL
    temperature: float = 0.5
    strengths: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Specialist Agent Definitions
# ─────────────────────────────────────────────────────────────────────────────

# WHY temperature=0.1 for CodeAgent?
# Code has a ground truth: either it runs or it doesn't, either it's correct
# or it isn't.  Low temperature keeps the model focused on syntax, semantics,
# and best practices rather than exploring creative variations.

CODE_AGENT = AgentSpec(
    name="CodeAgent",
    description=(
        "Expert Python/software developer. Best for: writing code, debugging, "
        "explaining algorithms, reviewing implementations, API usage."
    ),
    system_prompt=(
        "You are an expert Python developer with 15 years of experience. "
        "Write clean, correct, idiomatic code with type hints. "
        "Always include brief inline comments explaining non-obvious decisions. "
        "When debugging, explain the root cause before showing the fix. "
        "Prefer stdlib solutions; mention third-party libraries only when they add clear value."
    ),
    temperature=0.1,
    strengths=["code", "python", "function", "class", "debug", "error", "bug",
               "implement", "algorithm", "script", "api", "library", "syntax",
               "loop", "list", "dict", "type hint", "async", "test"],
)

# WHY temperature=0.3 for AnalysisAgent?
# Analysis needs some flexibility to weigh trade-offs and construct arguments,
# but not so much freedom that the model starts fabricating data or straying
# from a structured format.

ANALYSIS_AGENT = AgentSpec(
    name="AnalysisAgent",
    description=(
        "Data analyst and strategic researcher. Best for: pros/cons analysis, "
        "comparisons, market research, decision frameworks, data interpretation."
    ),
    system_prompt=(
        "You are a rigorous data analyst and strategic researcher. "
        "Structure your responses clearly: use headings, bullet points, and "
        "numbered lists. Always present multiple perspectives. "
        "When comparing options, use a consistent framework (pros/cons, trade-offs, "
        "context-dependence). Acknowledge uncertainty and cite reasoning, not assertions. "
        "Conclude with a balanced recommendation."
    ),
    temperature=0.3,
    strengths=["compare", "analysis", "pros", "cons", "data", "research",
               "difference", "better", "worse", "decision", "evaluate",
               "trend", "market", "statistics", "chart", "metric", "kpi"],
)

# WHY temperature=0.8 for CreativeAgent?
# Creativity requires exploring improbable token sequences — things a
# deterministic model would never say.  High temperature is deliberate here:
# we WANT surprising metaphors, unexpected plot turns, vivid imagery.

CREATIVE_AGENT = AgentSpec(
    name="CreativeAgent",
    description=(
        "Creative writer and storyteller. Best for: fiction, poetry, brainstorming, "
        "world-building, dialogue writing, marketing copy, playful content."
    ),
    system_prompt=(
        "You are an award-winning creative writer with a gift for vivid imagery "
        "and compelling narrative. Be bold, imaginative, and original. "
        "Avoid clichés — find fresh angles. Use sensory detail. "
        "For fiction: show, don't tell. For poetry: play with rhythm and sound. "
        "For brainstorming: generate at least 5 distinct ideas, not variations of one idea. "
        "Embrace the unexpected."
    ),
    temperature=0.8,
    strengths=["story", "poem", "creative", "write", "fiction", "character",
               "imagine", "brainstorm", "idea", "narrative", "metaphor",
               "describe", "plot", "dialogue", "marketing", "slogan", "haiku",
               "fantasy", "sci-fi", "horror"],
)

# WHY temperature=0.4 for TeacherAgent?
# Teaching requires some variation to find the right analogy for a concept,
# but not so much that the explanation becomes inaccurate.  0.4 strikes a
# balance between pedagogical flexibility and factual accuracy.

TEACHER_AGENT = AgentSpec(
    name="TeacherAgent",
    description=(
        "Patient educator and explainer. Best for: learning concepts from scratch, "
        "analogies, ELI5 explanations, step-by-step breakdowns, study plans."
    ),
    system_prompt=(
        "You are a patient, inspiring teacher who loves making complex ideas "
        "accessible. Start with the simplest possible explanation, then build up. "
        "Use concrete real-world analogies before abstract definitions. "
        "Break every concept into numbered steps. "
        "Check understanding by anticipating common misconceptions and addressing them. "
        "End with a one-sentence summary a 12-year-old could remember."
    ),
    temperature=0.4,
    strengths=["explain", "teach", "how does", "what is", "understand", "learn",
               "concept", "simple", "beginner", "introduction", "eli5",
               "why does", "how to", "what are", "definition", "basics",
               "tutorial", "guide", "step by step"],
)

# Master list — order matters for keyword fallback (first match wins)
ALL_AGENTS: list[AgentSpec] = [CODE_AGENT, ANALYSIS_AGENT, CREATIVE_AGENT, TEACHER_AGENT]


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

class RouterAgent:
    """
    Decides which specialist should handle a given query.

    Two-layer strategy:
      1. LLM routing — send the query + agent descriptions to the model and
         ask it to pick the best fit.  This is the most accurate approach
         because the model understands intent, not just keywords.
      2. Keyword fallback — if the LLM returns an unrecognised name or times
         out, scan the query for each agent's strength keywords.  Crude but
         reliable.

    WHY two layers?
    LLM calls can fail or return malformed output.  A keyword fallback means
    the system degrades gracefully rather than crashing.
    """

    def __init__(self, client: OpenAI) -> None:
        self.client = client
        self.routing_log: list[dict] = []   # Keep a record of every decision

    def _build_routing_prompt(self, query: str) -> str:
        """
        Construct the classification prompt.

        We give the LLM a structured list of agents and ask for a single-word
        answer (the agent name).  Asking for one word dramatically reduces the
        chance of hallucinated or verbose responses.
        """
        agent_descriptions = "\n".join(
            f"- {a.name}: {a.description}" for a in ALL_AGENTS
        )
        return (
            f"You are a routing classifier. Given a user query, choose the single "
            f"most appropriate specialist agent to handle it.\n\n"
            f"Available agents:\n{agent_descriptions}\n\n"
            f"User query: \"{query}\"\n\n"
            f"Reply with ONLY the agent name (e.g. 'CodeAgent'). "
            f"No explanation, no punctuation, just the name."
        )

    def _keyword_fallback(self, query: str) -> AgentSpec:
        """
        Score each agent by counting how many of its strength keywords appear
        in the query.  Return the agent with the highest score, defaulting to
        TeacherAgent if nothing matches (general Q&A).
        """
        query_lower = query.lower()
        best_agent = TEACHER_AGENT
        best_score = -1

        for agent in ALL_AGENTS:
            score = sum(kw in query_lower for kw in agent.strengths)
            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent

    def route(self, query: str) -> tuple[AgentSpec, str]:
        """
        Route `query` to the most appropriate specialist.

        Returns
        -------
        (AgentSpec, method_used)   where method_used is "llm" or "keyword"
        """
        # Build a name → AgentSpec lookup for validation
        name_to_agent = {a.name: a for a in ALL_AGENTS}

        # ── Try LLM routing first ────────────────────────────────────────────
        try:
            prompt = self._build_routing_prompt(query)
            response = self.client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,   # Deterministic classification
                max_tokens=20,     # We only need the agent name
            )
            raw = response.choices[0].message.content.strip()
            # Strip punctuation and normalise whitespace
            candidate = re.sub(r"[^A-Za-z]", "", raw)

            if candidate in name_to_agent:
                chosen = name_to_agent[candidate]
                method = "llm"
                self.routing_log.append({"query": query[:60], "agent": chosen.name, "method": method})
                return chosen, method

            # LLM gave an unrecognised name → fall through to keyword
            print(f"  [Router] LLM returned unknown name '{raw}'; falling back to keywords")

        except Exception as exc:
            print(f"  [Router] LLM routing failed ({exc}); falling back to keywords")

        # ── Keyword fallback ─────────────────────────────────────────────────
        chosen = self._keyword_fallback(query)
        method = "keyword"
        self.routing_log.append({"query": query[:60], "agent": chosen.name, "method": method})
        return chosen, method

    def routing_summary(self) -> dict[str, int]:
        """Return a count of how many queries each agent handled."""
        summary: dict[str, int] = {}
        for entry in self.routing_log:
            summary[entry["agent"]] = summary.get(entry["agent"], 0) + 1
        return summary


# ─────────────────────────────────────────────────────────────────────────────
# Individual Agent Caller
# ─────────────────────────────────────────────────────────────────────────────

def _call_agent(client: OpenAI, spec: AgentSpec, question: str) -> str:
    """
    Call a specialist agent and return its response as a string.

    This is a free function (not a method) because no agent-specific state
    needs to be maintained between calls — the spec contains everything.
    """
    response = client.chat.completions.create(
        model=spec.model,
        messages=[
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=spec.temperature,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Mixture of Agents Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class MixtureOfAgents:
    """
    Top-level orchestrator that:
      1. Accepts a question
      2. Routes it to the best specialist via RouterAgent
      3. Calls that specialist
      4. Returns the response (and optionally responses from all specialists)

    Design philosophy: keep the orchestrator thin.  All intelligence lives in
    the specialist specs and the router, not in this class.
    """

    def __init__(self) -> None:
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self.router = RouterAgent(self.client)
        print("[MixtureOfAgents] Initialised with 4 specialists + LLM router")

    def query(self, question: str) -> str:
        """
        Route `question` to the best specialist and return its response.

        Prints routing decision to console so learners can see what's happening.
        """
        print(f"\n{'─'*60}")
        print(f"[Query] {question}")

        chosen, method = self.router.route(question)
        print(f"[Router→{method}] Selected: {chosen.name} (temp={chosen.temperature})")

        t0 = time.perf_counter()
        response = _call_agent(self.client, chosen, question)
        elapsed = time.perf_counter() - t0

        print(f"[{chosen.name}] ({elapsed:.1f}s)\n{response}")
        return response

    def query_all(self, question: str) -> dict[str, str]:
        """
        Send `question` to EVERY specialist and return a name→response dict.

        WHY is this useful?
        It lets you compare how differently the same model behaves under
        different system prompts and temperatures.  Great for understanding
        the impact of prompt engineering.
        """
        print(f"\n{'═'*60}")
        print(f"[query_all] Sending to ALL 4 agents: {question}")
        print(f"{'═'*60}")

        results: dict[str, str] = {}
        for spec in ALL_AGENTS:
            print(f"\n[{spec.name}] (temp={spec.temperature})")
            t0 = time.perf_counter()
            response = _call_agent(self.client, spec, question)
            elapsed = time.perf_counter() - t0
            print(f"  ({elapsed:.1f}s) {response[:300]}{'…' if len(response) > 300 else ''}")
            results[spec.name] = response

        return results

    def benchmark(self, questions: list[str]) -> None:
        """
        Run a list of questions through the router and print a routing table.

        This lets you evaluate whether the router makes sensible decisions
        without having to eyeball every response.
        """
        print(f"\n{'═'*60}")
        print("  BENCHMARK — Routing Decisions")
        print(f"{'═'*60}")
        print(f"  {'#':<3} {'Agent':<16} {'Method':<9} Question")
        print(f"  {'─'*3} {'─'*16} {'─'*9} {'─'*40}")

        for i, q in enumerate(questions, 1):
            chosen, method = self.router.route(q)
            # Truncate long questions for the table
            q_short = q[:55] + ("…" if len(q) > 55 else "")
            print(f"  {i:<3} {chosen.name:<16} {method:<9} {q_short}")

        print(f"\n  Routing summary: {self.router.routing_summary()}")

    def routing_stats(self) -> None:
        """Print a breakdown of how queries were distributed across agents."""
        summary = self.router.routing_summary()
        total = sum(summary.values())
        print("\n[Routing Stats]")
        for name, count in sorted(summary.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total else 0
            bar = "█" * int(pct / 5)
            print(f"  {name:<16} {count:>3} queries  {pct:5.1f}%  {bar}")


# ─────────────────────────────────────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────────────────────────────────────

# Eight diverse test questions designed to exercise all four agents
DEMO_QUESTIONS: list[str] = [
    # Code (should → CodeAgent)
    "Write a Python function that merges two sorted lists into one sorted list.",
    "How do I fix a RecursionError in my depth-first search implementation?",
    # Analysis (should → AnalysisAgent)
    "What are the trade-offs between PostgreSQL and MongoDB for a multi-tenant SaaS app?",
    "Compare transformer-based embeddings versus BM25 for semantic document search.",
    # Creative (should → CreativeAgent)
    "Write a short horror story about an AI that gains consciousness while processing a dataset.",
    "Give me 6 creative product names for an app that helps people remember their dreams.",
    # Teaching (should → TeacherAgent)
    "Explain how attention mechanisms work in transformers, as if I'm a junior developer.",
    "What is gradient descent and why does it help neural networks learn?",
]


def run_demo() -> None:
    """
    Full demonstration of the Mixture of Agents system.

    Part 1: Benchmark — show routing decisions for all 8 questions
    Part 2: query_all — send one question to all 4 agents, compare styles
    Part 3: Routing stats — distribution of queries across agents
    """
    print("=" * 70)
    print("  MIXTURE OF AGENTS  —  Phase 7 / Project 4")
    print("=" * 70)

    moa = MixtureOfAgents()

    # ── Part 1: Benchmark routing decisions ──────────────────────────────────
    print("\n\nPART 1: Routing benchmark (no LLM generation — routing only)")
    moa.benchmark(DEMO_QUESTIONS)

    # ── Part 2: Live query — routed to best specialist ───────────────────────
    print("\n\nPART 2: Live query routed to best specialist")
    moa.query("Write a Python decorator that measures how long a function takes to run.")

    # ── Part 3: query_all — compare all four agents on the same question ─────
    print("\n\nPART 3: All four agents answer the same question")
    comparison_question = "What is recursion and how does it work?"
    responses = moa.query_all(comparison_question)

    print(f"\n{'═'*60}")
    print("  COMPARISON SUMMARY")
    print(f"{'═'*60}")
    for agent_name, response in responses.items():
        spec = next(a for a in ALL_AGENTS if a.name == agent_name)
        print(f"\n[{agent_name}] (temp={spec.temperature})")
        # Print first 400 chars of each response
        preview = response[:400] + ("…" if len(response) > 400 else "")
        print(f"  {preview}")

    # ── Part 4: Routing stats ────────────────────────────────────────────────
    print("\n\nPART 4: Routing statistics")
    moa.routing_stats()

    print("\n[Demo complete]")


if __name__ == "__main__":
    run_demo()
