"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · MCP Benefits Example | agent.py                                     ║
║  A dynamic MCP + RAG agent: qwen2.5:3b decides WHEN to retrieve.               ║
║                                                                                ║
║  FLOW (explicit LangGraph loop):                                               ║
║      router (qwen2.5 + tools) ──tool_calls?──▶ tools (MCP) ──┐                 ║
║            ▲                                                  │                 ║
║            └──────────────────────────────────────────────-──┘                 ║
║      no tool_calls ▶ END (the model's last message is the answer)             ║
║                                                                                ║
║  WHY qwen2.5:3b (not gemma3)? It has strong native tool-calling, which MCP     ║
║  leans on. Embeddings + retrieval stay local via the MCP server.              ║
║                                                                                ║
║  RUN:  python agent.py "What is the 2026 HSA family contribution limit?"       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import asyncio
import os
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode

# ─── Config ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
ROUTER_MODEL = os.getenv("MCP_ROUTER_MODEL", "qwen2.5:3b")   # ollama pull qwen2.5:3b
HERE = os.path.dirname(os.path.abspath(__file__))

SYSTEM = SystemMessage(content=(
    "You are a benefits assistant for 401(k) and HSA questions. "
    "ALWAYS call search_benefits_docs to ground your answer before replying. "
    "Answer ONLY from the retrieved excerpts; if the answer isn't there, say so. "
    "State the exact figures and name the source document."
))


# ─── Build the graph (loads MCP tools over stdio) ────────────────────────────
async def build_graph():
    # MCP client launches benefits_mcp_server.py as a subprocess and speaks MCP.
    client = MultiServerMCPClient({
        "benefits": {
            "command": sys.executable,
            "args": [os.path.join(HERE, "benefits_mcp_server.py")],
            "transport": "stdio",
        }
    })
    tools = await client.get_tools()                    # MCP tools → LangChain tools

    llm = ChatOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama",
                     model=ROUTER_MODEL, temperature=0.1)
    llm_with_tools = llm.bind_tools(tools)

    async def router(state: MessagesState):
        return {"messages": [await llm_with_tools.ainvoke(state["messages"])]}

    # Explicit branch: if the model asked for a tool, run it; otherwise we're done.
    def decide(state: MessagesState):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    g = StateGraph(MessagesState)
    g.add_node("router", router)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "router")
    g.add_conditional_edges("router", decide, {"tools": "tools", END: END})
    g.add_edge("tools", "router")            # loop back after a tool result
    return g.compile()


async def ask(question: str) -> None:
    graph = await build_graph()
    result = await graph.ainvoke({"messages": [SYSTEM, HumanMessage(content=question)]})

    # Show the dynamic decisions the agent made, then the grounded answer.
    print(f"\nQ: {question}\n")
    for m in result["messages"]:
        for call in getattr(m, "tool_calls", None) or []:
            print(f"  ↳ tool: {call['name']}({call['args']})")
    print("\nANSWER:\n" + (result["messages"][-1].content or "").strip())


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or \
        "What is the 2026 401(k) employee limit and the catch-up for someone over 50?"
    asyncio.run(ask(q))
