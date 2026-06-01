"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           Phase 7 · Project 5 — Self-Improving Agent (Reflexion)            ║
║                                                                              ║
║  WHY THIS EXISTS                                                             ║
║  LLMs are surprisingly good critics but mediocre first-draft generators.    ║
║  When you ask an LLM to evaluate an answer, it often spots flaws it missed  ║
║  when generating. Reflexion exploits this asymmetry: generate → critique    ║
║  → reflect → regenerate, looping until quality is high enough.             ║
║                                                                              ║
║  ACADEMIC FOUNDATION                                                         ║
║  Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement         ║
║  Learning" (2023) — https://arxiv.org/abs/2303.11366                        ║
║  Key insight: verbal self-feedback is a lightweight substitute for          ║
║  expensive gradient-based fine-tuning.                                       ║
║                                                                              ║
║  THE REFLEXION LOOP                                                          ║
║  User Query                                                                  ║
║    ↓                                                                         ║
║  [Generate] — first attempt at answering                                    ║
║    ↓                                                                         ║
║  [Critique] — evaluate own answer: what's wrong, missing, imprecise?        ║
║    ↓                                                                         ║
║  [Reflect]  — what specific improvements should be made? (3 concrete ones)  ║
║    ↓                                                                         ║
║  [Regenerate] — produce improved answer using critique as guidance           ║
║    ↓                                                                         ║
║  [Score]    — rate improvement 1–10. score ≥ 8 → done. else loop.          ║
║    max_iterations = 3 (safety brake — avoid infinite loops)                 ║
║                                                                              ║
║  WHY LANGGRAPH?                                                              ║
║  LangGraph models the loop as a directed graph with conditional edges.      ║
║  This makes the flow inspectable, debuggable, and easy to extend.           ║
║  The `should_continue_edge` function decides: keep improving or stop?       ║
║                                                                              ║
║  Model : gemma3:4b (Ollama)                                                 ║
║  Graph : LangGraph StateGraph                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import time
from typing import Literal

from langgraph.graph import END, StateGraph
from openai import OpenAI
from typing_extensions import TypedDict

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY  = "ollama"   # Ollama ignores the key; OpenAI client requires it
MODEL           = "gemma3:4b"

# How many self-improvement iterations before we force-stop.
# 3 is the "Goldilocks" number: enough to see real improvement, not so many
# that we waste compute on diminishing returns.
MAX_ITERATIONS = 3

# Minimum quality score (out of 10) to accept the answer as-is.
SCORE_THRESHOLD = 8


# ─────────────────────────────────────────────────────────────────────────────
# State definition
# ─────────────────────────────────────────────────────────────────────────────

class ReflexionState(TypedDict):
    """
    The shared mutable state that flows through every node in the graph.

    WHY TypedDict?
    LangGraph passes state as a plain dict between nodes. TypedDict gives us
    type-checker support (mypy, Pyright) while keeping serialisation trivial —
    no Pydantic overhead needed for a local demo.

    Fields
    ------
    query      : original user question, never modified after creation
    attempts   : list of generated answers (one per iteration)
    critiques  : what was wrong with each attempt
    reflections: concrete improvement plans derived from each critique
    scores     : numeric quality rating for each attempt (1-10)
    final_answer: the accepted answer (last attempt when we exit the loop)
    iterations  : counter so we never exceed MAX_ITERATIONS
    """
    query:       str
    attempts:    list[str]
    critiques:   list[str]
    reflections: list[str]
    scores:      list[int]
    final_answer: str
    iterations:  int


# ─────────────────────────────────────────────────────────────────────────────
# Helper: call the LLM
# ─────────────────────────────────────────────────────────────────────────────

def _chat(client: OpenAI, system: str, user: str, max_tokens: int = 1024) -> str:
    """
    Thin wrapper around OpenAI chat completions.

    WHY a wrapper?
    Every node in the graph calls the LLM.  Centralising the call means we
    only need to change retry logic, timeout settings, or model names in one
    place.
    """
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.7,   # some creativity on generation; deterministic on scoring
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Self-Improving Agent class
# ─────────────────────────────────────────────────────────────────────────────

class SelfImprovingAgent:
    """
    An agent that iteratively improves its own answers using the Reflexion pattern.

    Each call to `run()` spins up a LangGraph execution that:
      1. Generates an answer
      2. Critiques that answer harshly
      3. Extracts specific, actionable improvements
      4. Generates a better answer using those improvements as guidance
      5. Scores the result — stop if good enough, else loop

    The entire history (all attempts, critiques, reflections, scores) is
    returned so callers can show the learning journey, not just the endpoint.
    """

    def __init__(self) -> None:
        # Ollama exposes an OpenAI-compatible REST API, so we point the
        # standard OpenAI client at localhost instead of api.openai.com
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self._graph = self._build_graph()

    # ── Graph construction ───────────────────────────────────────────────────

    def _build_graph(self) -> object:
        """
        Wire up the LangGraph StateGraph.

        The graph has four nodes and one conditional edge:

            generate → critique → reflect → score
                ↑                              ↓
                └── (if score < 8 and iter < 3) ←┘
                                                ↓
                                           → END (otherwise)

        WHY compile()?
        LangGraph's compile step validates the graph topology (no dangling
        edges, no unreachable nodes) and returns a Runnable that we can
        `.invoke()`.
        """
        g = StateGraph(ReflexionState)

        g.add_node("generate",  self.generate_node)
        g.add_node("critique",  self.critique_node)
        g.add_node("reflect",   self.reflect_node)
        g.add_node("score",     self.score_node)

        # Linear flow for the "body" of the loop
        g.set_entry_point("generate")
        g.add_edge("generate", "critique")
        g.add_edge("critique",  "reflect")
        g.add_edge("reflect",   "score")

        # The exit decision lives after scoring
        g.add_conditional_edges(
            "score",
            self.should_continue_edge,
            {
                "continue": "generate",  # loop back for another improvement pass
                "end":      END,          # answer is good enough (or max iters hit)
            },
        )

        return g.compile()

    # ── Node: generate ───────────────────────────────────────────────────────

    def generate_node(self, state: ReflexionState) -> dict:
        """
        Produce (or improve) an answer.

        On the first iteration there is no prior critique, so we just answer
        the question.  On subsequent iterations we inject the previous attempt
        and the reflection (specific improvements) into the prompt so the model
        can act on the feedback.

        WHY include both the previous attempt AND the reflection?
        Showing the previous attempt gives the model something concrete to
        improve upon.  Showing the reflection tells it *how* to improve.
        Together they anchor the revision and prevent "hallucinating" an
        entirely different (possibly worse) answer.
        """
        query    = state["query"]
        attempts = state["attempts"]

        if not attempts:
            # First pass — no feedback yet
            system = (
                "You are a knowledgeable expert. Answer the following question "
                "as accurately and completely as you can."
            )
            user = query
        else:
            # Improvement pass — use the critique-derived reflection
            prev_attempt = attempts[-1]
            reflection   = state["reflections"][-1]

            system = (
                "You are a knowledgeable expert improving a previous answer. "
                "You have been given specific improvement points. Rewrite the "
                "answer to address ALL of them. Be precise and thorough."
            )
            user = (
                f"Original question: {query}\n\n"
                f"Previous answer:\n{prev_attempt}\n\n"
                f"Required improvements:\n{reflection}\n\n"
                "Please write an improved answer that addresses all the points above."
            )

        answer = _chat(self.client, system, user, max_tokens=800)

        return {
            "attempts":   state["attempts"]   + [answer],
            "iterations": state["iterations"] + 1,
        }

    # ── Node: critique ───────────────────────────────────────────────────────

    def critique_node(self, state: ReflexionState) -> dict:
        """
        Play devil's advocate against our own answer.

        WHY use a harsh critic persona?
        A gentle critic says "good answer, but maybe add X."  A harsh critic
        forces the model to find real flaws.  Prompting "Act as a harsh critic"
        shifts the model's prior toward finding problems rather than
        complimenting itself.

        The critique is kept separate from the reflection so we have two
        distinct thinking steps: (1) what's wrong, (2) how to fix it.
        Splitting them produces higher-quality improvement plans than asking
        the model to combine both in one shot.
        """
        latest_answer = state["attempts"][-1]
        query         = state["query"]

        system = (
            "Act as a harsh but fair critic. Your job is to find flaws, gaps, "
            "imprecision, and missing information in answers. Be specific — "
            "vague feedback like 'could be better' is useless. Point to exact "
            "claims, missing context, or logical weaknesses."
        )
        user = (
            f"Question that was asked:\n{query}\n\n"
            f"Answer to critique:\n{latest_answer}\n\n"
            "What is wrong, missing, or imprecise in this answer? Be specific."
        )

        critique = _chat(self.client, system, user, max_tokens=512)

        return {"critiques": state["critiques"] + [critique]}

    # ── Node: reflect ────────────────────────────────────────────────────────

    def reflect_node(self, state: ReflexionState) -> dict:
        """
        Convert the critique into a concrete improvement plan.

        WHY separate Reflect from Critique?
        Critique = diagnosis (what is broken).
        Reflect  = prescription (what to do about it).
        Asking the model to produce both at once leads to vague prescriptions.
        Two-step thinking produces actionable, numbered improvements that the
        Generate node can directly act on.

        We explicitly ask for exactly 3 improvements to bound the scope —
        too many and the next generation gets overwhelmed; too few and the
        improvement is superficial.
        """
        critique = state["critiques"][-1]
        query    = state["query"]
        answer   = state["attempts"][-1]

        system = (
            "You are a thoughtful editor turning a critique into an actionable "
            "improvement plan. Be specific, concrete, and numbered."
        )
        user = (
            f"Question: {query}\n\n"
            f"Answer that was critiqued:\n{answer}\n\n"
            f"Critique received:\n{critique}\n\n"
            "Based on this critique, list exactly 3 specific improvements that "
            "the next version of the answer MUST include. Number them 1, 2, 3. "
            "Each improvement should be actionable, not vague."
        )

        reflection = _chat(self.client, system, user, max_tokens=384)

        return {"reflections": state["reflections"] + [reflection]}

    # ── Node: score ──────────────────────────────────────────────────────────

    def score_node(self, state: ReflexionState) -> dict:
        """
        Rate the latest answer on a 1–10 scale.

        WHY LLM-as-judge for scoring?
        We don't have ground-truth labels, so we let a separate LLM "persona"
        act as an impartial evaluator.  This is an established technique —
        see Zheng et al. "Judging LLM-as-a-Judge" (2023).

        We set temperature=0.0 for scoring because we want a deterministic,
        reproducible number — no creativity needed here.

        The parse_score() helper uses a regex to extract the first integer 1-10
        from the response, which is robust to responses like "I'd give it a 7."
        """
        latest_answer = state["attempts"][-1]
        query         = state["query"]

        system = (
            "You are an impartial evaluator. Rate the answer to the question "
            "on a scale of 1 to 10 based on accuracy, completeness, and clarity. "
            "Reply with ONLY a single integer between 1 and 10. No explanation."
        )
        user = (
            f"Question: {query}\n\n"
            f"Answer: {latest_answer}"
        )

        # Lower temperature for scoring — we want determinism, not creativity
        resp = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=0.0,
            max_tokens=16,
        )
        raw_score = resp.choices[0].message.content.strip()
        score     = self._parse_score(raw_score)

        # Update final_answer at every step — if we exit early, this holds the best
        return {
            "scores":       state["scores"] + [score],
            "final_answer": latest_answer,
        }

    @staticmethod
    def _parse_score(text: str) -> int:
        """
        Extract a 1–10 integer from freeform text.

        WHY not just int(text)?
        Models sometimes reply with "7/10" or "Score: 8" instead of a bare
        digit.  A regex is more robust.  We cap the result to [1, 10] as a
        safety net against hallucinated values.
        """
        match = re.search(r"\b([1-9]|10)\b", text)
        if match:
            return int(match.group(1))
        # Fallback: if we truly can't parse, assume mediocre quality and continue
        return 5

    # ── Conditional edge ─────────────────────────────────────────────────────

    def should_continue_edge(
        self, state: ReflexionState
    ) -> Literal["continue", "end"]:
        """
        The routing function that decides whether to loop or stop.

        Exit if EITHER condition is met:
          • Score is high enough (≥ SCORE_THRESHOLD=8) — answer is good
          • Max iterations reached — safety brake, avoid infinite loops

        WHY have a max_iterations brake?
        In theory the agent could loop forever chasing perfection. In practice,
        after 3 passes the marginal improvement is negligible and we're burning
        compute for tiny gains. The brake is the responsible engineering choice.
        """
        latest_score = state["scores"][-1]
        iterations   = state["iterations"]

        if latest_score >= SCORE_THRESHOLD:
            return "end"
        if iterations >= MAX_ITERATIONS:
            return "end"
        return "continue"

    # ── Public API ───────────────────────────────────────────────────────────

    def run(self, query: str) -> ReflexionState:
        """
        Run the full Reflexion loop for a given query.

        Returns the complete state so callers can inspect all iterations,
        critiques, reflections, and scores — not just the final answer.
        Showing the journey is the whole point of this learning project.
        """
        initial_state: ReflexionState = {
            "query":        query,
            "attempts":     [],
            "critiques":    [],
            "reflections":  [],
            "scores":       [],
            "final_answer": "",
            "iterations":   0,
        }
        # LangGraph's invoke() runs the graph to completion and returns
        # the final state dict
        return self._graph.invoke(initial_state)


# ─────────────────────────────────────────────────────────────────────────────
# Demo / main
# ─────────────────────────────────────────────────────────────────────────────

def _divider(title: str, width: int = 78) -> None:
    """Print a titled section divider for readable console output."""
    pad = (width - len(title) - 4) // 2
    print(f"\n{'─' * pad}[ {title} ]{'─' * pad}")


def _print_state(state: ReflexionState) -> None:
    """
    Pretty-print the full Reflexion history.

    This is what makes the project a *learning* project: you can see exactly
    what the agent thought was wrong and how it improved.
    """
    query       = state["query"]
    attempts    = state["attempts"]
    critiques   = state["critiques"]
    reflections = state["reflections"]
    scores      = state["scores"]

    print(f"\n{'═' * 78}")
    print(f"QUERY: {query}")
    print(f"{'═' * 78}")

    for i, (attempt, score) in enumerate(zip(attempts, scores)):
        critique   = critiques[i]   if i < len(critiques)   else "(none)"
        reflection = reflections[i] if i < len(reflections) else "(none)"

        _divider(f"Iteration {i + 1}  ·  Score: {score}/10")

        print(f"\n[ANSWER]\n{attempt}")
        print(f"\n[CRITIQUE]\n{critique}")
        print(f"\n[REFLECTION / IMPROVEMENT PLAN]\n{reflection}")
        print(f"\n  → Score: {score}/10")

    # Side-by-side comparison of first vs final
    if len(attempts) > 1:
        _divider("First Answer vs Final Answer")
        print(f"\nFIRST ANSWER (score {scores[0]}/10):\n{attempts[0]}")
        print(f"\nFINAL ANSWER (score {scores[-1]}/10):\n{attempts[-1]}")

    # Score trajectory shows the improvement arc
    if scores:
        _divider("Score Trajectory")
        trajectory = " → ".join(f"{s}/10" for s in scores)
        improvement = scores[-1] - scores[0] if len(scores) > 1 else 0
        print(f"\n  {trajectory}")
        print(f"  Δ improvement: +{improvement} points over {len(scores)} iteration(s)")


def main() -> None:
    """
    Run three test questions that benefit from self-critique:
      1. Technical  — precision and correctness matter
      2. Analytical — nuanced reasoning required
      3. Creative   — structure and completeness matter

    WHY these three types?
    Reflexion shines when answers have multiple dimensions to get right.
    Simple factual questions (capital of France?) don't benefit — there's
    nothing to critique. Complex, open-ended questions do benefit.
    """
    agent = SelfImprovingAgent()

    test_queries = [
        # Technical question — many ways to get the details wrong
        (
            "Technical",
            "Explain exactly how Python's Global Interpreter Lock (GIL) works "
            "and under what specific conditions it is released."
        ),
        # Analytical — easy to give a one-sided or superficial answer
        (
            "Analytical",
            "What are the key trade-offs between microservices and monolithic "
            "architecture? When should you choose each?"
        ),
        # Creative — structure, engagement, completeness all matter
        (
            "Creative",
            "Explain the concept of recursion to a 10-year-old using a concrete, "
            "memorable analogy."
        ),
    ]

    for category, query in test_queries:
        print(f"\n{'═' * 78}")
        print(f"  CATEGORY: {category}")
        print(f"{'═' * 78}")

        start = time.time()
        state = agent.run(query)
        elapsed = time.time() - start

        _print_state(state)
        print(f"\n  Total time: {elapsed:.1f}s  |  Iterations: {state['iterations']}")
        print(f"\n{'═' * 78}\n")


if __name__ == "__main__":
    main()
