"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 02 | demo_client.py                                         ║
║  Raw MCP client (no LLM) — shows the mechanics before agent.py adds routing.  ║
║                                                                                ║
║  It lists the tools, calls a couple of MOCK account tools, lists sources, and  ║
║  runs one RAG search. The mock tools work without Ollama; search needs the     ║
║  index (python ingest.py) + Ollama, and degrades to a clear message otherwise. ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
SERVER_PATH = HERE / "benefits_mcp_server.py"


def _normalize(payload):
    if hasattr(payload, "content"):
        return _normalize(payload.content)
    if hasattr(payload, "contents"):
        return _normalize(payload.contents)
    if isinstance(payload, list):
        out = [_normalize(item) for item in payload]
        return out[0] if len(out) == 1 else out
    text = getattr(payload, "text", None)
    if text is not None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return payload


def _show(title: str, payload) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(_normalize(payload), indent=2, default=str))


async def main() -> None:
    server = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            _show("Available MCP Tools", [t.name for t in tools.tools])

            # --- MOCK account tools (work without Ollama) ---
            match = await session.call_tool("calculate_primary_contribution_match", {})
            savings_account = await session.call_tool("estimate_savings_account_adjustment", {})
            _show("ACCOUNT · calculate_primary_contribution_match", match.content)
            _show("ACCOUNT · estimate_savings_account_adjustment", savings_account.content)

            # --- RAG tools (real docs; need index.npz + Ollama) ---
            sources = await session.call_tool("list_sources", {})
            search = await session.call_tool(
                "search_benefits_docs", {"query": "2026 savings account family contribution limit", "k": 2}
            )
            _show("RULES · list_sources", sources.content)
            _show("RULES · search_benefits_docs('2026 savings account family limit')", search.content)


if __name__ == "__main__":
    asyncio.run(main())
