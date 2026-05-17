# ═══════════════════════════════════════════════════════════════
# Project 02 — CrewAI Research Crew
# Phase 5 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Builds a crew of role-based AI agents that work together
#   to produce a competitive analysis report.
#
#   Unlike Project 01 (which you coded the graph manually),
#   CrewAI handles the orchestration for you. You just define:
#     - WHO the agents are (role, goal, backstory)
#     - WHAT tasks they do (description, expected output)
#     - HOW they work together (sequential or hierarchical)
#
# CREW MEMBERS:
#   1. Researcher    — deep domain expertise, gathers raw info
#   2. Analyst       — patterns, trends, competitive positioning
#   3. Writer        — turns analysis into readable report
#
# KEY CONCEPTS:
#   - Agent: an AI with a role, goal, backstory (persona)
#   - Task: a specific job assigned to an agent
#   - Crew: the team + how they execute tasks (Process)
#   - Process.sequential: tasks run in order, output feeds next
#   - Process.hierarchical: manager agent delegates (advanced)
#
# WHY CREWAI vs LANGGRAPH?
#   LangGraph = you control every edge and routing decision
#   CrewAI    = framework handles routing, you define personas
#   Use LangGraph for complex custom control flow.
#   Use CrewAI for role-based teams with simpler coordination.
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python research_crew.py
# ═══════════════════════════════════════════════════════════════

import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import Field
from datetime import datetime
from typing import Type

# ─────────────────────────────────────────────────────────────
# SETUP: Ollama LLM for CrewAI
# CrewAI uses its own LLM wrapper — different from LangGraph
# ─────────────────────────────────────────────────────────────

ollama_llm = LLM(
    model="ollama/gemma3:4b",
    base_url="http://localhost:11434",
    temperature=0.4,
)


# ═══════════════════════════════════════════════════════════════
# STEP 1: DEFINE TOOLS
#
# CrewAI tools are Python classes that inherit from BaseTool.
# Agents choose which tools to use based on the task context.
# This is different from LangGraph where tools are registered
# in a ToolRegistry.
# ═══════════════════════════════════════════════════════════════

class MarketDataTool(BaseTool):
    """
    Simulates fetching market/industry data.
    In production this would call a real API (Crunchbase, PitchBook, etc.)
    We keep it local to avoid API keys.
    """
    name: str = "market_data"
    description: str = (
        "Retrieve market size, growth rates, and industry statistics "
        "for a given technology sector or company."
    )

    def _run(self, query: str) -> str:
        # Simulated market data — replace with real API calls in production
        data = {
            "ai coding": {
                "market_size_2024": "$4.7B",
                "cagr": "28.4%",
                "projected_2028": "$12.9B",
                "key_players": ["GitHub Copilot (Microsoft)", "Cursor", "Codeium", "Tabnine", "Amazon CodeWhisperer"],
                "adoption": "45% of developers use AI coding tools daily as of 2025",
            },
            "local llm": {
                "market_size_2024": "$1.2B",
                "cagr": "41.2%",
                "projected_2028": "$5.1B",
                "key_players": ["Ollama", "LM Studio", "GPT4All", "Jan.ai", "llamafile"],
                "adoption": "23% of enterprise AI deployments use on-premise LLMs",
            },
            "vector database": {
                "market_size_2024": "$1.5B",
                "cagr": "36.7%",
                "projected_2028": "$6.9B",
                "key_players": ["Pinecone", "Weaviate", "Qdrant", "Chroma", "pgvector"],
                "adoption": "67% of RAG implementations use dedicated vector DBs",
            },
        }
        # Find matching data (fuzzy match)
        query_lower = query.lower()
        for key, val in data.items():
            if key in query_lower or any(word in query_lower for word in key.split()):
                return str(val)
        return f"Market data for '{query}': Sector growing ~30% CAGR. Consult industry reports for specifics."


class CompetitorProfileTool(BaseTool):
    """Generates structured competitor profiles."""
    name: str = "competitor_profile"
    description: str = (
        "Get a detailed profile of a competitor including strengths, "
        "weaknesses, pricing, and market positioning."
    )

    def _run(self, company: str) -> str:
        profiles = {
            "github copilot": {
                "parent": "Microsoft / GitHub",
                "pricing": "$10/month individual, $19/month business",
                "strengths": ["Largest user base", "IDE integration", "GitHub ecosystem"],
                "weaknesses": ["Requires internet", "Privacy concerns", "No local model option"],
                "model": "GPT-4o based",
                "users": "1.8M paid users (2024)",
            },
            "cursor": {
                "parent": "Anysphere (independent)",
                "pricing": "$20/month Pro, $40/month Business",
                "strengths": ["Best-in-class autocomplete", "Codebase-aware chat", "Fast iteration"],
                "weaknesses": ["VS Code fork only", "Higher price point", "Newer player"],
                "model": "Claude + GPT-4 + custom models",
                "users": "500K+ developers (2025)",
            },
            "codeium": {
                "parent": "Exafunction (independent)",
                "pricing": "Free tier, Teams from $12/month",
                "strengths": ["Free tier", "40+ IDE support", "Enterprise security"],
                "weaknesses": ["Less code quality than Copilot/Cursor", "Smaller ecosystem"],
                "model": "Custom fine-tuned models",
                "users": "700K+ users (2025)",
            },
        }
        company_lower = company.lower()
        for key, profile in profiles.items():
            if key in company_lower or any(word in company_lower for word in key.split()):
                return str(profile)
        return f"Profile for {company}: Emerging player in the AI space. Limited public data available."


# ═══════════════════════════════════════════════════════════════
# STEP 2: DEFINE AGENTS (The Crew Members)
#
# Each agent has:
#   role:      Their job title / persona
#   goal:      What they're trying to achieve (guides decisions)
#   backstory: Context that shapes HOW they approach problems
#   tools:     Python tools they can call
#   llm:       The language model powering them
#   verbose:   Print their thinking process
#
# The backstory is NOT just flavor text — it primes the LLM
# to respond in character. A "skeptical analyst" backstory
# produces more critical output than an "enthusiastic" one.
# ═══════════════════════════════════════════════════════════════

def create_agents():
    """Create all crew members with their roles and tools."""

    researcher = Agent(
        role="Senior Technology Researcher",
        goal=(
            "Gather comprehensive, accurate information about market trends, "
            "key players, and competitive dynamics in the specified technology sector."
        ),
        backstory=(
            "You are a senior researcher at a top-tier technology consulting firm. "
            "You have 10 years of experience tracking AI/ML market trends. "
            "You are methodical, cite specific numbers when available, and flag "
            "when you're estimating vs. stating confirmed facts. "
            "You use available tools to get real data before drawing conclusions."
        ),
        tools=[MarketDataTool(), CompetitorProfileTool()],
        llm=ollama_llm,
        verbose=True,
        max_iter=5,          # max reasoning iterations per task
        memory=True,         # remember context within the crew session
    )

    analyst = Agent(
        role="Competitive Intelligence Analyst",
        goal=(
            "Analyze research findings to identify patterns, strategic opportunities, "
            "threats, and competitive positioning insights."
        ),
        backstory=(
            "You are a competitive intelligence analyst with a background in strategic consulting. "
            "You excel at identifying non-obvious patterns in data and synthesizing complex "
            "information into actionable insights. You are skeptical by nature — you always "
            "ask 'so what does this mean?' and 'what are the risks here?'. "
            "You do not repeat research findings — you interpret them."
        ),
        tools=[],    # analyst doesn't need tools — works from researcher's output
        llm=ollama_llm,
        verbose=True,
        memory=True,
    )

    writer = Agent(
        role="Senior Technology Writer",
        goal=(
            "Transform research and analysis into a clear, compelling competitive "
            "analysis report that executives can act on."
        ),
        backstory=(
            "You are a senior technology writer who has written for HBR, MIT Tech Review, "
            "and top consulting firm publications. You write with clarity and precision. "
            "You avoid jargon, use concrete examples, and structure information so "
            "busy executives can scan it in 2 minutes but dive deep if they want to. "
            "You never pad word count — every sentence earns its place."
        ),
        tools=[],
        llm=ollama_llm,
        verbose=True,
        memory=True,
    )

    return researcher, analyst, writer


# ═══════════════════════════════════════════════════════════════
# STEP 3: DEFINE TASKS
#
# Each Task has:
#   description:     What to do (detailed instructions)
#   expected_output: What the output should look like
#   agent:           Which crew member handles this task
#   context:         List of prior tasks whose output feeds this one
#
# In Process.sequential, tasks run in order.
# The 'context' parameter passes a prior task's output as input.
# ═══════════════════════════════════════════════════════════════

def create_tasks(researcher, analyst, writer, topic: str):
    """Create the task pipeline for a given analysis topic."""

    research_task = Task(
        description=(
            f"Conduct comprehensive research on: {topic}\n\n"
            "Your research must cover:\n"
            "1. Use the market_data tool to get market size and growth statistics\n"
            "2. Use the competitor_profile tool for the top 2-3 players you identify\n"
            "3. Identify technology trends driving this market\n"
            "4. Note key customer segments and use cases\n"
            "5. Flag any data gaps or areas of uncertainty\n\n"
            "Produce structured research notes, not a narrative essay."
        ),
        expected_output=(
            "Structured research notes with:\n"
            "- Market statistics (size, CAGR, projections)\n"
            "- Profiles of 2-3 key competitors with specific data\n"
            "- Top 3-5 technology trends\n"
            "- Customer segment breakdown\n"
            "- Data confidence levels"
        ),
        agent=researcher,
    )

    analysis_task = Task(
        description=(
            f"Analyze the research findings about {topic} and produce strategic insights.\n\n"
            "Do NOT restate the research. Your job is to INTERPRET it:\n"
            "1. What is the #1 strategic opportunity right now and why?\n"
            "2. What is the biggest threat or risk to watch?\n"
            "3. Who is positioned to win and why? Who is vulnerable?\n"
            "4. What would you advise a new entrant to do?\n"
            "5. What is the 12-month outlook?\n\n"
            "Be opinionated. Analysts who hedge everything are useless."
        ),
        expected_output=(
            "Strategic analysis with:\n"
            "- Clear opinion on market opportunity (not just 'it's growing')\n"
            "- Competitive positioning matrix or comparison\n"
            "- Top 3 strategic recommendations with reasoning\n"
            "- Risk assessment\n"
            "- 12-month forecast"
        ),
        agent=analyst,
        context=[research_task],  # analyst reads researcher's output
    )

    writing_task = Task(
        description=(
            f"Write a professional competitive analysis report on: {topic}\n\n"
            "Using the research notes and strategic analysis provided:\n"
            "1. Write an Executive Summary (3-4 sentences max)\n"
            "2. Market Overview section (data-driven)\n"
            "3. Competitive Landscape section (top players)\n"
            "4. Strategic Insights section (the analyst's key points)\n"
            "5. Recommendations section (actionable, specific)\n"
            "6. Outlook section (12-month forward view)\n\n"
            f"Report date: {datetime.now().strftime('%B %Y')}\n"
            "Target audience: Technology executives and investors.\n"
            "Tone: Professional, direct, no fluff."
        ),
        expected_output=(
            "A complete competitive analysis report with:\n"
            "- Professional formatting with clear section headers\n"
            "- Executive Summary at the top\n"
            "- 4-6 sections covering market, competition, strategy, and outlook\n"
            "- Specific data points and numbers throughout\n"
            "- 3-5 concrete recommendations\n"
            "- 500-800 words total"
        ),
        agent=writer,
        context=[research_task, analysis_task],  # writer reads both
        output_file="competitive_analysis_report.md",  # auto-saves to file
    )

    return research_task, analysis_task, writing_task


# ═══════════════════════════════════════════════════════════════
# STEP 4: ASSEMBLE AND RUN THE CREW
# ═══════════════════════════════════════════════════════════════

def run_research_crew(topic: str) -> str:
    """Assemble and run the full research crew."""

    print(f"\n{'═'*60}")
    print(f"  CREWAI RESEARCH CREW")
    print(f"{'═'*60}")
    print(f"  Topic: {topic}")
    print(f"  Crew: Researcher → Analyst → Writer")
    print(f"  Process: Sequential (each agent reads prior output)")
    print(f"{'═'*60}\n")

    researcher, analyst, writer = create_agents()
    research_task, analysis_task, writing_task = create_tasks(
        researcher, analyst, writer, topic
    )

    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.sequential,  # researcher → analyst → writer in order
        verbose=True,
        memory=False,    # crew-level memory (requires embeddings setup)
        max_rpm=10,      # rate limit: max 10 LLM calls/minute (safe for Ollama)
    )

    # Kickoff — this runs all tasks in order
    result = crew.kickoff(inputs={"topic": topic})

    return str(result)


# ═══════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("  PHASE 5 — PROJECT 02: CrewAI Research Crew")
    print("═"*60)
    print("\n  3 specialized agents collaborate on competitive analysis:")
    print("  Researcher (data) → Analyst (insights) → Writer (report)")
    print("\n  KEY DIFFERENCE from Project 01:")
    print("  → CrewAI manages orchestration for you")
    print("  → Agents have rich personas (role + goal + backstory)")
    print("  → Output auto-saves to competitive_analysis_report.md")

    topics = [
        "AI coding assistants competitive landscape",
        "Local LLM tools market (Ollama, LM Studio, Jan.ai)",
        "Vector database market competition",
    ]

    print("\n  Analysis Topics:")
    for i, t in enumerate(topics, 1):
        print(f"  [{i}] {t}")
    print("  [4] Enter your own topic")

    choice = input("\n  Choose (1-4): ").strip()
    if choice in ("1", "2", "3"):
        topic = topics[int(choice) - 1]
    elif choice == "4":
        topic = input("  Enter topic: ").strip()
    else:
        topic = topics[0]

    report = run_research_crew(topic)

    print("\n" + "═"*60)
    print("  FINAL REPORT")
    print("═"*60)
    print(report)
    print("\n" + "═"*60)
    print("  Report also saved to: competitive_analysis_report.md")
    print("═"*60)


if __name__ == "__main__":
    main()
