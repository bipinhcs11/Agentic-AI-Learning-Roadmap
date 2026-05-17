# ═══════════════════════════════════════════════════════════════
# Project 06 — Autonomous Research Pipeline (Phase 5 Capstone)
# Phase 5 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   A full autonomous research pipeline with 5 specialized agents
#   and HUMAN-IN-THE-LOOP approval gates between key stages.
#
# AGENTS + FLOW:
#   [Planner]    → breaks topic into research sub-questions
#       ↓ [HUMAN GATE 1] approve plan or edit it
#   [Researcher] → answers each sub-question in depth
#       ↓
#   [Synthesizer]→ merges research into unified narrative
#       ↓ [HUMAN GATE 2] approve synthesis or request changes
#   [Writer]     → creates polished long-form article
#       ↓
#   [Critic]     → final quality check and scoring
#       ↓
#   Published output file
#
# KEY CONCEPTS:
#   - Human-in-the-loop: LangGraph interrupts for human input
#   - Streaming: see agent output token by token as it generates
#   - Multi-hop research: planner's sub-questions drive researcher
#   - Quality gate: critic scores output before it's accepted
#   - Full pipeline combining ALL Phase 5 patterns
#
# THIS IS THE CAPSTONE — it ties together:
#   ✓ Supervisor routing (Project 01)
#   ✓ Role-based agents with personas (Project 02 — CrewAI style)
#   ✓ Event-driven state updates (Project 03)
#   ✓ Review-revise loops (Project 04)
#   ✓ Domain routing patterns (Project 05)
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python autonomous_research.py
# ═══════════════════════════════════════════════════════════════

import json
import os
from datetime import datetime
from typing import TypedDict, Annotated, Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# ─────────────────────────────────────────────────────────────
# LLM Setup
# ─────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="gemma3:4b",
    temperature=0.4,
)


# ═══════════════════════════════════════════════════════════════
# STEP 1: STATE
#
# This is the most complex state we've used — it stores the
# full research pipeline output at every stage.
# ═══════════════════════════════════════════════════════════════

class ResearchState(TypedDict):
    messages:       Annotated[list[BaseMessage], add_messages]
    topic:          str
    sub_questions:  list[str]       # planner's research questions
    research_data:  dict[str, str]  # {question: answer} pairs
    synthesis:      str             # synthesizer's unified narrative
    article:        str             # writer's final article
    critic_score:   int             # 1-10, critic's quality rating
    critic_feedback: str            # critic's written feedback
    human_feedback: str             # human's feedback at gates
    next:           str
    iteration:      int             # how many times article was revised


# ═══════════════════════════════════════════════════════════════
# STEP 2: AGENT NODES
# ═══════════════════════════════════════════════════════════════

def planner_node(state: ResearchState) -> ResearchState:
    """Break the research topic into 4-6 focused sub-questions."""
    topic = state["topic"]
    print(f"\n[PLANNER] Breaking down topic: {topic}")

    response = llm.invoke([
        SystemMessage(content=(
            "You are a research director. Break complex topics into 4-5 specific, "
            "answerable research questions. Each question should target a distinct angle. "
            "Format: numbered list, one question per line. Just the questions, no intro text."
        )),
        HumanMessage(content=f"Research topic: {topic}\n\nGenerate 4-5 focused research sub-questions:"),
    ])

    raw = response.content
    # Parse numbered list
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    questions = []
    for line in lines:
        # Strip numbering: "1. ...", "1) ...", "- ..."
        clean = line.lstrip("0123456789.-) ").strip()
        if len(clean) > 10 and "?" in clean:
            questions.append(clean)
    if not questions:
        questions = [l.strip() for l in lines[:5] if len(l.strip()) > 10]

    print(f"[PLANNER] Generated {len(questions)} sub-questions")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")

    return {
        "sub_questions": questions,
        "messages": [AIMessage(content=f"[Planner] {len(questions)} research questions ready")],
        "next": "human_gate_1",
    }


def human_gate_1_node(state: ResearchState) -> ResearchState:
    """
    Human-in-the-loop gate after planning.
    LangGraph can interrupt here — we implement as a terminal input.
    In production: use LangGraph's interrupt() for web UI integration.
    """
    print(f"\n{'═'*60}")
    print(f"  [HUMAN GATE 1] Review the research plan")
    print(f"{'═'*60}")
    print(f"\n  Topic: {state['topic']}")
    print(f"\n  Proposed sub-questions:")
    for i, q in enumerate(state["sub_questions"], 1):
        print(f"  {i}. {q}")

    print(f"\n  Options:")
    print(f"  [A] Approve and continue")
    print(f"  [S] Skip remaining questions (run faster)")
    print(f"  [E] Edit — replace all questions with your own")

    choice = input("\n  Your choice (A/S/E): ").strip().upper()

    if choice == "E":
        print("\n  Enter your research questions (one per line, empty line to finish):")
        new_questions = []
        while True:
            q = input("  > ").strip()
            if not q:
                break
            new_questions.append(q)
        if new_questions:
            return {
                "sub_questions": new_questions,
                "human_feedback": "Human replaced questions",
                "messages": [AIMessage(content="[Gate 1] Human replaced research questions")],
                "next": "researcher",
            }
    elif choice == "S":
        # Keep only first 2 questions for speed
        trimmed = state["sub_questions"][:2]
        return {
            "sub_questions": trimmed,
            "human_feedback": "Human trimmed to 2 questions for speed",
            "messages": [AIMessage(content="[Gate 1] Trimmed to 2 questions")],
            "next": "researcher",
        }

    return {
        "human_feedback": "Human approved the plan",
        "messages": [AIMessage(content="[Gate 1] Plan approved")],
        "next": "researcher",
    }


def researcher_node(state: ResearchState) -> ResearchState:
    """Answer each sub-question with a focused research response."""
    questions = state["sub_questions"]
    topic = state["topic"]
    print(f"\n[RESEARCHER] Answering {len(questions)} sub-questions...")

    research_data = {}
    for i, question in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {question[:60]}...")
        response = llm.invoke([
            SystemMessage(content=(
                "You are an expert researcher. Answer the question with specific facts, "
                "data points, examples, and nuance. Aim for 150-200 words per answer. "
                f"The broader research topic is: {topic}"
            )),
            HumanMessage(content=f"Research question: {question}"),
        ])
        research_data[question] = response.content

    print(f"[RESEARCHER] Answered {len(research_data)} questions")

    return {
        "research_data": research_data,
        "messages": [AIMessage(content=f"[Researcher] {len(research_data)} questions answered")],
        "next": "synthesizer",
    }


def synthesizer_node(state: ResearchState) -> ResearchState:
    """Merge all research answers into a cohesive narrative."""
    topic = state["topic"]
    research_data = state["research_data"]
    print(f"\n[SYNTHESIZER] Merging {len(research_data)} research threads...")

    # Build the research context
    research_block = "\n\n".join([
        f"Q: {q}\nA: {a}" for q, a in research_data.items()
    ])

    response = llm.invoke([
        SystemMessage(content=(
            "You are a senior editor. Synthesize multiple research answers into a "
            "unified, flowing narrative. Identify connections, tensions, and themes "
            "across the different angles. Do NOT just concatenate — actively synthesize. "
            "This synthesis will be used as the foundation for a final article."
        )),
        HumanMessage(content=f"Topic: {topic}\n\nResearch Q&A:\n{research_block}\n\nSynthesize into a unified narrative:"),
    ])

    synthesis = response.content
    print(f"[SYNTHESIZER] Synthesis ready ({len(synthesis)} chars)")

    return {
        "synthesis": synthesis,
        "messages": [AIMessage(content="[Synthesizer] Narrative synthesis complete")],
        "next": "human_gate_2",
    }


def human_gate_2_node(state: ResearchState) -> ResearchState:
    """Human review of the synthesis before article writing begins."""
    print(f"\n{'═'*60}")
    print(f"  [HUMAN GATE 2] Review the research synthesis")
    print(f"{'═'*60}")
    print(f"\n  Synthesis preview (first 600 chars):")
    print(f"  {state['synthesis'][:600]}...")

    print(f"\n  Options:")
    print(f"  [A] Approve — proceed to writing")
    print(f"  [F] Give feedback — add notes for the writer")

    choice = input("\n  Your choice (A/F): ").strip().upper()

    if choice == "F":
        feedback = input("  Your feedback for the writer: ").strip()
        return {
            "human_feedback": feedback,
            "messages": [AIMessage(content=f"[Gate 2] Human gave writer feedback: {feedback[:50]}")],
            "next": "writer",
        }

    return {
        "human_feedback": "",
        "messages": [AIMessage(content="[Gate 2] Synthesis approved")],
        "next": "writer",
    }


def writer_node(state: ResearchState) -> ResearchState:
    """Write the full polished article from the synthesis."""
    topic = state["topic"]
    synthesis = state["synthesis"]
    feedback = state.get("human_feedback", "")
    iteration = state.get("iteration", 0)
    print(f"\n[WRITER] Writing article (iteration {iteration + 1})...")

    feedback_section = f"\n\nSpecial instructions from editor: {feedback}" if feedback else ""

    response = llm.invoke([
        SystemMessage(content=(
            "You are a professional technology writer. Write a well-structured, "
            "engaging article. Use: a compelling headline, introduction hook, "
            "clear sections with headers, specific examples, and a strong conclusion. "
            "Target length: 600-800 words. Tone: authoritative but accessible."
        )),
        HumanMessage(content=f"Topic: {topic}\n\nResearch synthesis:\n{synthesis}{feedback_section}\n\nWrite the complete article:"),
    ])

    article = response.content
    print(f"[WRITER] Article written ({len(article)} chars)")

    return {
        "article": article,
        "iteration": iteration + 1,
        "human_feedback": "",  # clear after use
        "messages": [AIMessage(content=f"[Writer] Article complete (iteration {iteration + 1})")],
        "next": "critic",
    }


def critic_node(state: ResearchState) -> ResearchState:
    """Score the article quality 1-10 and provide feedback."""
    article = state["article"]
    topic = state["topic"]
    iteration = state.get("iteration", 1)
    print(f"\n[CRITIC] Evaluating article quality...")

    response = llm.invoke([
        SystemMessage(content=(
            "You are a harsh but fair editorial critic. Score articles 1-10 on:\n"
            "- Accuracy and depth of information\n"
            "- Clarity and flow of writing\n"
            "- Compelling headline and intro\n"
            "- Actionable insights for the reader\n\n"
            "Format your response EXACTLY as:\n"
            "SCORE: <number 1-10>\n"
            "VERDICT: <PUBLISH | REVISE>\n"
            "FEEDBACK: <specific improvements needed>\n\n"
            "Score 8+ = PUBLISH. Score below 8 = REVISE (unless iteration 2+)."
        )),
        HumanMessage(content=f"Topic: {topic}\n\nArticle to critique:\n{article}"),
    ])

    critique = response.content

    # Parse score
    score = 7  # default
    score_match = __import__("re").search(r"SCORE:\s*(\d+)", critique)
    if score_match:
        score = int(score_match.group(1))

    verdict = "PUBLISH" if "PUBLISH" in critique else "REVISE"

    # Auto-publish after 2 iterations regardless of score
    if iteration >= 2:
        verdict = "PUBLISH"

    print(f"[CRITIC] Score: {score}/10 | Verdict: {verdict}")

    return {
        "critic_score": score,
        "critic_feedback": critique,
        "messages": [AIMessage(content=f"[Critic] Score: {score}/10 — {verdict}")],
        "next": "writer" if verdict == "REVISE" else "FINISH",
    }


# ═══════════════════════════════════════════════════════════════
# STEP 3: ROUTING
# ═══════════════════════════════════════════════════════════════

def route_node(state: ResearchState) -> str:
    """Generic router — reads state['next'] and routes accordingly."""
    next_node = state.get("next", "")
    if next_node == "FINISH":
        return END
    return next_node


def route_after_critic(state: ResearchState) -> Literal["writer", "__end__"]:
    next_node = state.get("next", "FINISH")
    return "writer" if next_node == "writer" else END


# ═══════════════════════════════════════════════════════════════
# STEP 4: GRAPH
# ═══════════════════════════════════════════════════════════════

def build_research_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner",       planner_node)
    graph.add_node("human_gate_1",  human_gate_1_node)
    graph.add_node("researcher",    researcher_node)
    graph.add_node("synthesizer",   synthesizer_node)
    graph.add_node("human_gate_2",  human_gate_2_node)
    graph.add_node("writer",        writer_node)
    graph.add_node("critic",        critic_node)

    graph.add_edge(START,          "planner")
    graph.add_edge("planner",      "human_gate_1")
    graph.add_edge("human_gate_1", "researcher")
    graph.add_edge("researcher",   "synthesizer")
    graph.add_edge("synthesizer",  "human_gate_2")
    graph.add_edge("human_gate_2", "writer")
    graph.add_edge("writer",       "critic")

    # Critic either loops back to writer or ends
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"writer": "writer", END: END}
    )

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def save_article(topic: str, article: str, score: int) -> str:
    """Save the final article to a file."""
    filename = f"article_{topic[:30].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    content = f"# {topic}\n\n*Generated by Autonomous Research Pipeline | Score: {score}/10*\n\n---\n\n{article}"
    with open(filename, "w") as f:
        f.write(content)
    return filename


def main():
    print("\n" + "═"*60)
    print("  PHASE 5 CAPSTONE — Autonomous Research Pipeline")
    print("═"*60)
    print("\n  Full pipeline with human-in-the-loop approval gates:")
    print("  Planner → [HUMAN GATE] → Researcher → Synthesizer")
    print("  → [HUMAN GATE] → Writer → Critic (⟲ loop) → Published")
    print("\n  This combines ALL Phase 5 patterns.")

    default_topics = [
        "The future of local AI models and what it means for privacy",
        "How multi-agent AI systems are changing software development",
        "Apple Silicon M4 and the democratization of AI computing",
    ]

    print("\n  Research Topics:")
    for i, t in enumerate(default_topics, 1):
        print(f"  [{i}] {t}")
    print("  [4] Enter your own topic")

    choice = input("\n  Choose (1-4): ").strip()
    if choice in ("1", "2", "3"):
        topic = default_topics[int(choice) - 1]
    elif choice == "4":
        topic = input("  Enter research topic: ").strip()
    else:
        topic = default_topics[0]

    print(f"\n  Starting autonomous research on: {topic}")
    print(f"  (You will be asked to approve at 2 checkpoints)\n")

    app = build_research_graph()

    initial_state: ResearchState = {
        "messages": [HumanMessage(content=f"Research: {topic}")],
        "topic": topic,
        "sub_questions": [],
        "research_data": {},
        "synthesis": "",
        "article": "",
        "critic_score": 0,
        "critic_feedback": "",
        "human_feedback": "",
        "next": "",
        "iteration": 0,
    }

    final_state = app.invoke(initial_state, config={"recursion_limit": 40})

    # Save and display
    score = final_state.get("critic_score", 0)
    article = final_state.get("article", "No article generated")

    saved_to = save_article(topic, article, score)

    print("\n" + "═"*60)
    print(f"  FINAL ARTICLE (Critic Score: {score}/10)")
    print("═"*60)
    print(article)
    print("\n" + "═"*60)
    print(f"  Article saved to: {saved_to}")
    print(f"  Research questions answered: {len(final_state.get('research_data', {}))}")
    print(f"  Writing iterations: {final_state.get('iteration', 0)}")
    print("═"*60)


if __name__ == "__main__":
    main()
