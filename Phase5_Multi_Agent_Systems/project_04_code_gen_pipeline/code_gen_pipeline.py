# ═══════════════════════════════════════════════════════════════
# Project 04 — Code Generation Multi-Agent Pipeline
# Phase 5 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   A 4-agent pipeline that turns a feature request into working,
#   tested Python code — with each agent reviewing the previous
#   agent's output before passing it forward.
#
# PIPELINE:
#   [Planner]  → breaks request into clear spec
#       ↓
#   [Coder]    → writes Python code from spec
#       ↓
#   [Reviewer] → reviews code, requests fixes if needed (loops!)
#       ↓
#   [Tester]   → writes and RUNS tests against the code
#       ↓
#   Final working code + tests
#
# KEY CONCEPTS:
#   - Review-revise loop: reviewer can send code back to coder
#   - Code execution: tests are actually run via subprocess
#   - LangGraph state machine with conditional back-edges
#   - Safety sandbox: only runs code in a temp directory
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python code_gen_pipeline.py
# ═══════════════════════════════════════════════════════════════

import subprocess
import tempfile
import textwrap
import re
import os
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ─────────────────────────────────────────────────────────────
# LLM Setup
# ─────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="gemma3:4b",
    temperature=0.2,   # low temp for code generation = more deterministic
)


# ═══════════════════════════════════════════════════════════════
# STEP 1: STATE
# ═══════════════════════════════════════════════════════════════

class CodeGenState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    feature_request: str     # user's original request
    spec: str                # planner's output
    code: str                # coder's output
    review_feedback: str     # reviewer's feedback (empty = approved)
    test_code: str           # tester's test suite
    test_results: str        # actual output from running tests
    revision_count: int      # how many times code was revised
    approved: bool           # True when reviewer is satisfied
    next: str                # routing


MAX_REVISIONS = 2  # max times coder can revise before we accept as-is


# ═══════════════════════════════════════════════════════════════
# STEP 2: UTILITY — Extract code blocks from LLM output
# ═══════════════════════════════════════════════════════════════

def extract_code(text: str, lang: str = "python") -> str:
    """
    Pull code out of markdown fenced blocks.
    Handles: ```python ... ``` and ``` ... ```
    """
    # Try to find a fenced code block
    pattern = rf"```(?:{lang})?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return matches[0].strip()

    # If no fenced block, assume the whole response is code
    # Strip common non-code lines
    lines = [l for l in text.split("\n") if not l.startswith("#!")]
    return "\n".join(lines).strip()


def run_code_safely(code: str, test_code: str) -> str:
    """
    Execute code + tests in a temp directory with a timeout.
    Returns stdout + stderr combined.

    SAFETY: subprocess with timeout prevents infinite loops.
    The temp dir is cleaned up automatically.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write the implementation
        impl_path = os.path.join(tmpdir, "implementation.py")
        with open(impl_path, "w") as f:
            f.write(code)

        # Write the test file — it imports from implementation
        test_path = os.path.join(tmpdir, "test_implementation.py")
        test_content = f"import sys\nsys.path.insert(0, '{tmpdir}')\nfrom implementation import *\n\n{test_code}"
        with open(test_path, "w") as f:
            f.write(test_content)

        # Run with python (not pytest — no extra dependencies)
        try:
            result = subprocess.run(
                ["python", test_path],
                capture_output=True,
                text=True,
                timeout=15,          # kill after 15s
                cwd=tmpdir,
            )
            output = result.stdout + result.stderr
            return output if output.strip() else "Tests ran with no output (possible silent pass)"
        except subprocess.TimeoutExpired:
            return "ERROR: Code execution timed out (>15s). Possible infinite loop."
        except Exception as e:
            return f"ERROR running tests: {e}"


# ═══════════════════════════════════════════════════════════════
# STEP 3: AGENT NODES
# ═══════════════════════════════════════════════════════════════

def planner_node(state: CodeGenState) -> CodeGenState:
    """Turn a vague feature request into a precise spec."""
    request = state["feature_request"]
    print(f"\n[PLANNER] Breaking down: {request[:60]}...")

    response = llm.invoke([
        SystemMessage(content=(
            "You are a software architect. Turn feature requests into clear, "
            "precise technical specifications for a Python developer. "
            "Include: function signatures, input/output types, edge cases to handle, "
            "and examples. Be specific — no vague requirements."
        )),
        HumanMessage(content=f"Feature request: {request}\n\nWrite a precise Python implementation spec."),
    ])

    spec = response.content
    print(f"[PLANNER] Spec ready ({len(spec)} chars)")

    return {
        "spec": spec,
        "messages": [AIMessage(content=f"[Planner] Spec complete")],
        "next": "coder",
    }


def coder_node(state: CodeGenState) -> CodeGenState:
    """Write Python code from the spec. Re-runs if reviewer sent feedback."""
    spec = state["spec"]
    feedback = state.get("review_feedback", "")
    revision = state.get("revision_count", 0)

    print(f"\n[CODER] Writing code (revision {revision + 1})...")

    if feedback:
        prompt = (
            f"Revise your Python code based on this reviewer feedback:\n\n"
            f"FEEDBACK:\n{feedback}\n\n"
            f"ORIGINAL SPEC:\n{spec}\n\n"
            f"CURRENT CODE:\n{state.get('code', 'No code yet')}\n\n"
            f"Write corrected Python code only. No explanations outside code blocks."
        )
    else:
        prompt = (
            f"Write Python code for this spec:\n\n{spec}\n\n"
            f"Requirements:\n"
            f"- Clean, readable Python 3.11+\n"
            f"- Proper error handling\n"
            f"- Type hints\n"
            f"- Wrap in functions (not scripts)\n"
            f"Output only the code in a ```python block."
        )

    response = llm.invoke([
        SystemMessage(content="You are an expert Python developer. Write clean, working code."),
        HumanMessage(content=prompt),
    ])

    code = extract_code(response.content)
    print(f"[CODER] Code written ({len(code)} chars)")

    return {
        "code": code,
        "revision_count": revision + 1,
        "review_feedback": "",  # clear feedback after revision
        "messages": [AIMessage(content=f"[Coder] Code written (revision {revision + 1})")],
        "next": "reviewer",
    }


def reviewer_node(state: CodeGenState) -> CodeGenState:
    """Review the code. Either approve it or send back for revision."""
    code = state["code"]
    spec = state["spec"]
    revision = state.get("revision_count", 0)
    print(f"\n[REVIEWER] Reviewing code (revision {revision})...")

    # After MAX_REVISIONS, auto-approve to prevent infinite loops
    if revision >= MAX_REVISIONS:
        print(f"[REVIEWER] Max revisions reached — auto-approving")
        return {
            "approved": True,
            "review_feedback": "",
            "messages": [AIMessage(content=f"[Reviewer] Auto-approved after {MAX_REVISIONS} revisions")],
            "next": "tester",
        }

    response = llm.invoke([
        SystemMessage(content=(
            "You are a senior code reviewer. Review Python code for: "
            "correctness, edge cases, error handling, and spec compliance. "
            "Be critical but constructive. "
            "End your review with EXACTLY one of:\n"
            "VERDICT: APPROVED\n"
            "VERDICT: NEEDS_REVISION"
        )),
        HumanMessage(content=f"SPEC:\n{spec}\n\nCODE TO REVIEW:\n```python\n{code}\n```\n\nReview and give verdict."),
    ])

    review_text = response.content
    approved = "APPROVED" in review_text and "NEEDS_REVISION" not in review_text
    print(f"[REVIEWER] Verdict: {'APPROVED' if approved else 'NEEDS REVISION'}")

    if approved:
        return {
            "approved": True,
            "review_feedback": "",
            "messages": [AIMessage(content="[Reviewer] Code APPROVED")],
            "next": "tester",
        }
    else:
        feedback = review_text
        return {
            "approved": False,
            "review_feedback": feedback,
            "messages": [AIMessage(content=f"[Reviewer] NEEDS REVISION — feedback sent to coder")],
            "next": "coder",  # send back for revision
        }


def tester_node(state: CodeGenState) -> CodeGenState:
    """Write tests AND execute them. Report real test results."""
    code = state["code"]
    spec = state["spec"]
    print(f"\n[TESTER] Writing and running tests...")

    # Write test code
    test_response = llm.invoke([
        SystemMessage(content=(
            "You are a test engineer. Write Python test code using assert statements "
            "(no pytest, no unittest — just assert). "
            "Test normal cases, edge cases, and error cases. "
            "Print 'TEST PASSED: <name>' for each passing test. "
            "The tests import from 'implementation' module. "
            "Output only the test code in a ```python block."
        )),
        HumanMessage(content=f"SPEC:\n{spec}\n\nIMPLEMENTATION:\n```python\n{code}\n```\n\nWrite comprehensive tests."),
    ])

    test_code = extract_code(test_response.content)
    print(f"[TESTER] Tests written ({len(test_code)} chars) — running...")

    # Actually execute the tests
    test_results = run_code_safely(code, test_code)
    passed = "error" not in test_results.lower() and "traceback" not in test_results.lower()

    print(f"[TESTER] Results: {'TESTS PASSED' if passed else 'TESTS FAILED'}")
    print(f"[TESTER] Output:\n{test_results[:500]}")

    return {
        "test_code": test_code,
        "test_results": test_results,
        "messages": [AIMessage(content=f"[Tester] Tests complete. {'PASSED' if passed else 'FAILED'}.")],
        "next": "FINISH",
    }


# ═══════════════════════════════════════════════════════════════
# STEP 4: ROUTING
# ═══════════════════════════════════════════════════════════════

def route_from_reviewer(state: CodeGenState) -> Literal["coder", "tester"]:
    return "coder" if not state.get("approved") else "tester"


def route_next(state: CodeGenState) -> str:
    next_node = state.get("next", "")
    return END if next_node == "FINISH" else next_node


# ═══════════════════════════════════════════════════════════════
# STEP 5: BUILD THE GRAPH
# ═══════════════════════════════════════════════════════════════

def build_code_gen_graph():
    graph = StateGraph(CodeGenState)

    graph.add_node("planner",  planner_node)
    graph.add_node("coder",    coder_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("tester",   tester_node)

    graph.add_edge(START,      "planner")
    graph.add_edge("planner",  "coder")

    # Coder → Reviewer always
    graph.add_edge("coder", "reviewer")

    # Reviewer → either back to Coder (revision) or forward to Tester (approved)
    graph.add_conditional_edges(
        "reviewer",
        route_from_reviewer,
        {"coder": "coder", "tester": "tester"}
    )

    graph.add_edge("tester", END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_code_gen(feature_request: str) -> dict:
    print(f"\n{'═'*60}")
    print(f"  CODE GENERATION MULTI-AGENT PIPELINE")
    print(f"{'═'*60}")
    print(f"  Request: {feature_request}")
    print(f"  Flow: Planner → Coder → Reviewer ⟲ (loop until approved) → Tester")
    print(f"{'═'*60}\n")

    app = build_code_gen_graph()

    initial_state: CodeGenState = {
        "messages": [HumanMessage(content=feature_request)],
        "feature_request": feature_request,
        "spec": "",
        "code": "",
        "review_feedback": "",
        "test_code": "",
        "test_results": "",
        "revision_count": 0,
        "approved": False,
        "next": "",
    }

    final_state = app.invoke(initial_state, config={"recursion_limit": 30})
    return final_state


def main():
    print("\n" + "═"*60)
    print("  PHASE 5 — PROJECT 04: Code Generation Multi-Agent Pipeline")
    print("═"*60)
    print("\n  4 agents turn a feature request into tested code:")
    print("  Planner → Coder → Reviewer (loops!) → Tester (runs real tests)")
    print("\n  KEY DIFFERENCE from previous projects:")
    print("  → Back-edges: reviewer can loop coder for revisions")
    print("  → Code actually executes — real test results, not simulated")

    requests = [
        "A function that validates email addresses and returns True/False with detailed error messages",
        "A simple in-memory cache with TTL (time-to-live) expiry support",
        "A function that flattens a nested dictionary to dot-notation keys",
    ]

    print("\n  Feature Requests:")
    for i, r in enumerate(requests, 1):
        print(f"  [{i}] {r}")
    print("  [4] Enter your own request")

    choice = input("\n  Choose (1-4): ").strip()
    if choice in ("1", "2", "3"):
        request = requests[int(choice) - 1]
    elif choice == "4":
        request = input("  Enter request: ").strip()
    else:
        request = requests[0]

    result = run_code_gen(request)

    print("\n" + "═"*60)
    print("  FINAL CODE")
    print("═"*60)
    print(result.get("code", "No code generated"))

    print("\n" + "═"*60)
    print("  TEST RESULTS")
    print("═"*60)
    print(result.get("test_results", "No test results"))
    print(f"\n  Revisions needed: {result.get('revision_count', 0)}")
    print("═"*60)


if __name__ == "__main__":
    main()
