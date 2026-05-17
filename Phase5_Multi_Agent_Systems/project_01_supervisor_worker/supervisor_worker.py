# ═══════════════════════════════════════════════════════════════
# Project 01 — Supervisor-Worker Multi-Agent System
# Phase 5 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Builds a multi-agent system where a SUPERVISOR agent reads
#   your request and delegates work to specialist WORKER agents:
#
#   User → Supervisor → Researcher → Supervisor
#                    → Summarizer → Supervisor
#                    → Formatter  → Supervisor → DONE
#
#   This is the most important pattern in multi-agent AI.
#   LangGraph manages the graph of who talks to whom.
#
# KEY CONCEPTS:
#   - StateGraph: a directed graph where nodes are agents
#   - Shared State: all agents read/write the same "memory"
#   - Conditional Edges: supervisor decides which node runs next
#   - ReAct through delegation, not internal tool-calling
#
# TECH STACK:
#   - LangGraph 1.1.x  → agent graph orchestration
#   - LangChain Core   → message types (Human/AI/System)
#   - ChatOpenAI       → pointing to local Ollama (not real OpenAI)
#   - Ollama           → runs gemma3:4b locally
#
# HOW TO RUN:
#   1. ollama serve                  (separate terminal)
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python supervisor_worker.py
#
# ARCHITECTURE DIAGRAM:
#
#   ┌─────────────────────────────────────────────────┐
#   │              LANGGRAPH STATE                    │
#   │  messages: [...conversation history...]         │
#   │  next:     "researcher" | "summarizer" |        │
#   │            "formatter"  | "FINISH"              │
#   └─────────────────────────────────────────────────┘
#          ↑ read/write             ↑ read/write
#   ┌──────────────┐         ┌──────────────────────┐
#   │  SUPERVISOR  │ ──────► │  WORKER AGENTS       │
#   │  (decides    │ ◄────── │  researcher          │
#   │   who's next)│         │  summarizer          │
#   └──────────────┘         │  formatter           │
#                            └──────────────────────┘
# ═══════════════════════════════════════════════════════════════

import json
import re
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ─────────────────────────────────────────────────────────────
# SETUP: Connect to Ollama (same as previous phases)
# We use ChatOpenAI but point it at Ollama's OpenAI-compatible API
# ─────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",          # Ollama doesn't need a real key
    model="gemma3:4b",
    temperature=0.3,           # lower = more consistent routing decisions
)


# ═══════════════════════════════════════════════════════════════
# STEP 1: DEFINE THE SHARED STATE
#
# This is what ALL agents share. Every agent reads from it
# and writes back to it. Think of it as the "team whiteboard".
#
# TypedDict = a dict with fixed keys and types (Python typing)
# Annotated[list, add_messages] = LangGraph appends to this list
#   instead of overwriting it (critical for conversation history)
# ═══════════════════════════════════════════════════════════════

class BriefingState(TypedDict):
    # The full conversation history — every agent reads this
    # add_messages is a LangGraph reducer: it appends, not replaces
    messages: Annotated[list[BaseMessage], add_messages]

    # Which worker should run next? Supervisor sets this.
    next: str

    # The topic the user wants briefed on
    topic: str

    # Accumulated work from each worker agent
    research_notes: str
    summary: str
    final_briefing: str


# ═══════════════════════════════════════════════════════════════
# STEP 2: THE SUPERVISOR AGENT
#
# The supervisor reads the current state, decides which worker
# to call next, and sets state["next"] accordingly.
#
# It does NOT do the actual work — it only routes.
# This separation of concerns is the key insight of this pattern.
# ═══════════════════════════════════════════════════════════════

SUPERVISOR_SYSTEM_PROMPT = """You are a supervisor managing a news briefing team.
Your team consists of:
  - researcher: Gathers detailed facts and information about the topic
  - summarizer: Condenses research notes into key points
  - formatter:  Creates the final polished briefing document

Your job is ONLY to decide who should work next.
Respond with EXACTLY one of these words (nothing else):
  researcher
  summarizer
  formatter
  FINISH

Routing rules:
  - If research_notes is empty → researcher
  - If research_notes exists but summary is empty → summarizer
  - If summary exists but final_briefing is empty → formatter
  - If final_briefing exists → FINISH
"""

def supervisor_node(state: BriefingState) -> BriefingState:
    """
    The supervisor reads current progress and decides the next worker.
    Returns a state update with 'next' set to the chosen worker.
    """
    print("\n[SUPERVISOR] Reading current state...")

    # Build a status message so supervisor knows where we are
    status = f"""
Topic: {state.get('topic', 'unknown')}
research_notes: {'✓ exists' if state.get('research_notes') else '✗ empty'}
summary: {'✓ exists' if state.get('summary') else '✗ empty'}
final_briefing: {'✓ exists' if state.get('final_briefing') else '✗ empty'}

Who should work next?"""

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=status),
    ]

    response = llm.invoke(messages)
    decision = response.content.strip().lower()

    # Clean up — extract just the routing word in case model added extra text
    for keyword in ["researcher", "summarizer", "formatter", "finish"]:
        if keyword in decision:
            decision = keyword
            break
    else:
        decision = "researcher"  # safe fallback

    # Map "finish" to LangGraph's END marker
    next_node = "FINISH" if decision == "finish" else decision

    print(f"[SUPERVISOR] Routing to → {next_node}")

    return {
        "next": next_node,
        "messages": [AIMessage(content=f"[Supervisor] Next: {next_node}")]
    }


# ═══════════════════════════════════════════════════════════════
# STEP 3: WORKER AGENTS
#
# Each worker has ONE job. They read from state, do their work,
# and write their output back to a specific state field.
#
# Notice: workers do NOT know about each other. They only
# read state and write state. The supervisor connects them.
# ═══════════════════════════════════════════════════════════════

def researcher_node(state: BriefingState) -> BriefingState:
    """
    Researcher: Deep-dives into the topic and produces raw notes.
    Output goes into state['research_notes'].
    """
    topic = state.get("topic", "unknown topic")
    print(f"\n[RESEARCHER] Researching: {topic}")

    prompt = f"""You are an expert researcher. Your job is to gather comprehensive
information about the following topic:

Topic: {topic}

Provide detailed research notes covering:
1. Key facts and background
2. Current status or recent developments
3. Important figures, organizations, or entities involved
4. Data points and statistics if relevant
5. Different perspectives or angles

Format as structured notes. Be thorough — the summarizer will condense this later."""

    response = llm.invoke([
        SystemMessage(content="You are a thorough research specialist. Write detailed factual notes."),
        HumanMessage(content=prompt),
    ])

    research_notes = response.content
    print(f"[RESEARCHER] Generated {len(research_notes)} chars of notes")

    return {
        "research_notes": research_notes,
        "messages": [AIMessage(content=f"[Researcher] Research complete ({len(research_notes)} chars)")]
    }


def summarizer_node(state: BriefingState) -> BriefingState:
    """
    Summarizer: Reads research notes, distills into key bullet points.
    Output goes into state['summary'].
    """
    topic = state.get("topic", "unknown topic")
    research_notes = state.get("research_notes", "No research available")
    print(f"\n[SUMMARIZER] Summarizing research on: {topic}")

    prompt = f"""You are an expert summarizer. Condense the following research notes
into clear, concise key points.

Topic: {topic}

Research Notes:
{research_notes}

Create a summary with:
- 5-7 key bullet points (most important facts)
- 2-3 sentences of overall context
- Any critical numbers or statistics

Keep it brief but information-dense. The formatter will make it look nice."""

    response = llm.invoke([
        SystemMessage(content="You are a concise summarizer. Extract only the most important information."),
        HumanMessage(content=prompt),
    ])

    summary = response.content
    print(f"[SUMMARIZER] Summary: {len(summary)} chars")

    return {
        "summary": summary,
        "messages": [AIMessage(content=f"[Summarizer] Summary complete ({len(summary)} chars)")]
    }


def formatter_node(state: BriefingState) -> BriefingState:
    """
    Formatter: Takes the summary and creates a polished briefing document.
    Output goes into state['final_briefing'].
    """
    topic = state.get("topic", "unknown topic")
    summary = state.get("summary", "No summary available")
    print(f"\n[FORMATTER] Formatting briefing on: {topic}")

    prompt = f"""You are a professional briefing writer. Create a polished,
executive-style news briefing document from the following summary.

Topic: {topic}
Summary: {summary}

Format the output as a professional briefing with:
- A clear title
- Date line
- Executive Summary (2-3 sentences)
- Key Points section (formatted bullets)
- Why This Matters (1-2 sentences)
- Bottom Line (one punchy sentence)

Use clean formatting. This is the final deliverable."""

    response = llm.invoke([
        SystemMessage(content="You are a professional briefing writer. Create polished, executive-ready documents."),
        HumanMessage(content=prompt),
    ])

    final_briefing = response.content
    print(f"[FORMATTER] Final briefing: {len(final_briefing)} chars")

    return {
        "final_briefing": final_briefing,
        "messages": [AIMessage(content=f"[Formatter] Briefing complete")]
    }


# ═══════════════════════════════════════════════════════════════
# STEP 4: THE ROUTING FUNCTION
#
# This tells LangGraph WHERE to go after the supervisor runs.
# It reads state["next"] and returns the node name to go to.
#
# "Conditional edges" = edges whose destination depends on state.
# This is how LangGraph implements branching / decision logic.
# ═══════════════════════════════════════════════════════════════

def route_after_supervisor(state: BriefingState) -> Literal["researcher", "summarizer", "formatter", "__end__"]:
    """Read the supervisor's decision and return the next node name."""
    next_node = state.get("next", "researcher")
    if next_node == "FINISH":
        return END   # LangGraph's special terminal node
    return next_node


# ═══════════════════════════════════════════════════════════════
# STEP 5: BUILD THE GRAPH
#
# StateGraph is LangGraph's core class.
# You define:
#   - Nodes: agents (functions that transform state)
#   - Edges: connections between nodes
#   - Conditional Edges: branching based on state
#
# The graph is compiled once, then you can invoke it many times.
# ═══════════════════════════════════════════════════════════════

def build_briefing_graph() -> StateGraph:
    """Assemble the multi-agent graph."""

    # Create the graph with our state schema
    graph = StateGraph(BriefingState)

    # ── Add Nodes (the agents) ────────────────────────────────
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("formatter", formatter_node)

    # ── Add Edges (the connections) ───────────────────────────

    # Entry point: START always goes to supervisor first
    graph.add_edge(START, "supervisor")

    # After supervisor runs, decide where to go (conditional)
    graph.add_conditional_edges(
        "supervisor",            # from this node...
        route_after_supervisor,  # call this function to decide...
        {                        # map return values to node names
            "researcher": "researcher",
            "summarizer": "summarizer",
            "formatter":  "formatter",
            END:          END,
        }
    )

    # After each worker finishes, ALWAYS go back to supervisor
    # This creates the loop: supervisor → worker → supervisor → ...
    graph.add_edge("researcher", "supervisor")
    graph.add_edge("summarizer", "supervisor")
    graph.add_edge("formatter",  "supervisor")

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# STEP 6: RUN THE SYSTEM
# ═══════════════════════════════════════════════════════════════

def run_briefing(topic: str) -> str:
    """Run the full multi-agent briefing pipeline for a given topic."""

    print(f"\n{'═'*60}")
    print(f"  NEWS BRIEFING SYSTEM — Multi-Agent Pipeline")
    print(f"{'═'*60}")
    print(f"  Topic: {topic}")
    print(f"{'═'*60}\n")

    # Build the graph
    app = build_briefing_graph()

    # Initial state — only topic and first user message are set
    # Everything else starts empty; agents fill it in
    initial_state: BriefingState = {
        "messages": [HumanMessage(content=f"Please create a news briefing about: {topic}")],
        "next": "",
        "topic": topic,
        "research_notes": "",
        "summary": "",
        "final_briefing": "",
    }

    # Invoke the graph — it runs until it hits END
    # max_iterations protects against infinite loops
    final_state = app.invoke(
        initial_state,
        config={"recursion_limit": 20}  # max 20 node executions
    )

    return final_state.get("final_briefing", "No briefing generated.")


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE DEMO
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("  PHASE 5 — PROJECT 01: Supervisor-Worker Multi-Agent System")
    print("═"*60)
    print("\n  This system uses LangGraph to coordinate 4 AI agents:")
    print("  Supervisor → Researcher → Summarizer → Formatter")
    print("\n  Each agent has ONE job. The supervisor decides who's next.")

    # Demo topics — try each one
    demo_topics = [
        "The rise of AI coding assistants in software development",
        "Apple Silicon M4 chip performance for AI workloads",
        "Open source large language models in 2025",
    ]

    print("\n  Demo Topics:")
    for i, topic in enumerate(demo_topics, 1):
        print(f"  [{i}] {topic}")
    print("  [4] Enter your own topic")

    choice = input("\n  Choose (1-4): ").strip()

    if choice in ("1", "2", "3"):
        topic = demo_topics[int(choice) - 1]
    elif choice == "4":
        topic = input("  Enter topic: ").strip()
    else:
        topic = demo_topics[0]

    # Run the pipeline
    briefing = run_briefing(topic)

    # Display final result
    print("\n" + "═"*60)
    print("  FINAL BRIEFING")
    print("═"*60)
    print(briefing)
    print("\n" + "═"*60)
    print("  Pipeline complete! 4 agents collaborated to produce this.")
    print("═"*60)


if __name__ == "__main__":
    main()
