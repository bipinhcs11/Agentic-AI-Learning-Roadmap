"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 01 | demo_client.py                                       ║
║  Tiny MCP client that launches benefits_mcp_server.py over stdio.            ║
║                                                                              ║
║  PURPOSE: Show the mechanical flow of MCP before adding an LLM router.       ║
║  The demo lists tools/resources, reads resources, and calls tools directly.  ║
║  Later modules let the LLM decide which tools to call dynamically.           ║
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


def _normalize_mcp_content(payload):
    """Convert MCP content objects into readable JSON/text for the demo output."""
    if hasattr(payload, "content"):
        return _normalize_mcp_content(payload.content)

    if hasattr(payload, "contents"):
        return _normalize_mcp_content(payload.contents)

    if isinstance(payload, list):
        normalized = [_normalize_mcp_content(item) for item in payload]
        return normalized[0] if len(normalized) == 1 else normalized

    text = getattr(payload, "text", None)
    if text is not None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    return payload


def _print_json(title: str, payload) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(_normalize_mcp_content(payload), indent=2, default=str))


async def main() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()

            _print_json("Available MCP Tools", [tool.name for tool in tools.tools])
            _print_json("Available MCP Resources", [str(resource.uri) for resource in resources.resources])
            _print_json("Available MCP Prompts", [prompt.name for prompt in prompts.prompts])

            profile = await session.call_tool("get_employee_profile", {})
            match = await session.call_tool("calculate_401k_match", {})
            contribution = await session.call_tool(
                "estimate_annual_401k_contribution",
                {"employee_contribution_percent": 10},
            )
            hsa = await session.call_tool("estimate_hsa_tax_savings", {})
            rules = await session.call_tool("search_plan_rules", {"query": "vesting employer match"})
            document = await session.call_tool("get_plan_document", {"document_id": "hsa_plan_summary"})

            _print_json("Prompt: Am I getting the full employer match?", profile.content)
            _print_json("Tool Call: calculate_401k_match", match.content)
            _print_json("Tool Call: estimate_annual_401k_contribution at 10%", contribution.content)
            _print_json("Prompt: What are my estimated HSA tax savings?", hsa.content)
            _print_json("Tool Call: search_plan_rules('vesting employer match')", rules.content)
            _print_json("Tool Call: get_plan_document('hsa_plan_summary')", document.content)

            employee_resource = await session.read_resource("benefits://employee/profile")
            faq_resource = await session.read_resource("benefits://documents/benefits-faq")

            _print_json("Resource Read: benefits://employee/profile", employee_resource.contents)
            _print_json("Resource Read: benefits://documents/benefits-faq", faq_resource.contents)


if __name__ == "__main__":
    asyncio.run(main())
