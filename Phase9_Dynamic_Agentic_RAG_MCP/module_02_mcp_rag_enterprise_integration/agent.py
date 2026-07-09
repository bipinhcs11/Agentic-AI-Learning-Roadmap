"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 02 | agent.py                                               ║
║  The dynamic MCP + RAG flow: qwen2.5:3b decides the context path at runtime.  ║
║                                                                                ║
║      router (qwen2.5 + tools) ──tool_calls?──▶ tools (MCP) ──┐                 ║
║            ▲                                                  │                 ║
║            └──────────────────────────────────────────────-──┘                 ║
║      no tool_calls ▶ END (final grounded answer)                              ║
║                                                                                ║
║  The model picks one of four paths per question:                               ║
║    direct     — answer without tools                                           ║
║    MCP-only   — ACCOUNT tool(s), e.g. "am I getting my full match?"           ║
║    RAG-only   — search_benefits_docs, e.g. "2026 savings account family limit?"           ║
║    MCP + RAG  — both, e.g. "I do 6% — maxing match? + the 2026 limit?"        ║
║                                                                                ║
║  An audit line (tools + documents used) is appended to audit_log.jsonl.        ║
║  RUN:  python agent.py "What is the 2026 primary contribution employee limit?"               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
ROUTER_MODEL = os.getenv("MCP_ROUTER_MODEL", "qwen2.5:3b")   # ollama pull qwen2.5:3b
HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_PATH = os.path.join(HERE, "audit_log.jsonl")

SYSTEM = SystemMessage(content=(
    "You are an educational benefits assistant with two kinds of MCP tools:\n"
    "- ACCOUNT tools (get_employee_profile, get_primary_contribution_summary, calculate_primary_contribution_match, "
    "get_savings_account_summary, estimate_savings_account_adjustment) for the user's own (mock) account numbers.\n"
    "- RULES tools (search_benefits_docs, list_sources) for fixture references limits "
    "and rules from real public documents.\n"
    "Choose the right tool(s) per question; use BOTH when a question mixes personal numbers "
    "with official rules. For any figure that came from search_benefits_docs, cite the source "
    "document and URL (call list_sources). Be clear that estimates are estimates. "
    "This is educational only — not professional, adjustment, legal, or allocation advice."
))


async def build_graph():
    client = MultiServerMCPClient({
        "benefits": {
            "command": sys.executable,
            "args": [os.path.join(HERE, "benefits_mcp_server.py")],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()                      # MCP tools → LangChain tools
    llm = ChatOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama",
                     model=ROUTER_MODEL, temperature=0.1)
    llm_with_tools = llm.bind_tools(tools)

    async def router(state: MessagesState):
        return {"messages": [await llm_with_tools.ainvoke(state["messages"])]}

    def decide(state: MessagesState):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    g = StateGraph(MessagesState)
    g.add_node("router", router)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "router")
    g.add_conditional_edges("router", decide, {"tools": "tools", END: END})
    g.add_edge("tools", "router")
    return g.compile()


# ─── Lightweight audit trail (which tools + documents were used) ──────────────
def _audit(question: str, messages: list) -> dict:
    tools_used = [c["name"] for m in messages for c in (getattr(m, "tool_calls", None) or [])]
    docs: set[str] = set()
    for m in messages:
        content = getattr(m, "content", "") or ""
        if isinstance(content, str):
            docs.update(re.findall(r"source:\s*([\w./-]+\.md)", content))
    account_tools = {"get_employee_profile", "get_primary_contribution_summary", "calculate_primary_contribution_match",
                     "get_savings_account_summary", "estimate_savings_account_adjustment"}
    rag_tools = {"search_benefits_docs", "list_sources"}
    used_account = any(t in account_tools for t in tools_used)
    used_rag = any(t in rag_tools for t in tools_used)
    mode = ("mcp+rag" if used_account and used_rag
            else "rag_only" if used_rag
            else "mcp_only" if used_account
            else "direct")
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "route": mode,
        "tools_used": tools_used,
        "documents_used": sorted(docs),
    }
    with open(AUDIT_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


async def ask(question: str) -> None:
    graph = await build_graph()
    result = await graph.ainvoke({"messages": [SYSTEM, HumanMessage(content=question)]})

    print(f"\nQ: {question}\n")
    for m in result["messages"]:
        for call in getattr(m, "tool_calls", None) or []:
            print(f"  ↳ tool: {call['name']}({call['args']})")

    rec = _audit(question, result["messages"])
    print("\nANSWER:\n" + (result["messages"][-1].content or "").strip())
    print(f"\n[audit] route={rec['route']} tools={rec['tools_used']} docs={rec['documents_used']}")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or \
        "I contribute 6% to my primary contribution. Am I getting the full match, and what's the 2026 employee limit?"
    asyncio.run(ask(q))
