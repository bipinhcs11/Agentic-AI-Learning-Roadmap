#!/usr/bin/env python3
"""Run the fictional work-item -> config-check flow through the MCP gateway."""

from __future__ import annotations

import argparse
import asyncio
import json

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from enterprise_mcp.shared.observability import TraceContext


def _structured(result: object) -> dict:
    value = getattr(result, "structuredContent", None)
    if isinstance(value, dict):
        return value
    content = [getattr(item, "text", "") for item in getattr(result, "content", [])]
    if len(content) == 1:
        try:
            parsed = json.loads(content[0])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {"content": content}


async def run(gateway_url: str, token: str) -> dict:
    trace = TraceContext.new()
    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {token}",
            "traceparent": trace.traceparent,
        },
        follow_redirects=False,
    ) as http_client:
        async with streamable_http_client(
            gateway_url,
            http_client=http_client,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                work_item = _structured(
                    await session.call_tool(
                        "work_item_analyze",
                        arguments={"work_item_id": "WI-DEMO-001"},
                    )
                )
                output = {"workItemAnalysis": work_item}
                if work_item.get("nextApprovedTool") == "config_check":
                    output["configCheck"] = _structured(
                        await session.call_tool(
                            "config_check",
                            arguments={"participant_id": work_item["participantId"]},
                        )
                    )
                output["traceId"] = trace.trace_id
                return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default="http://127.0.0.1:8080/mcp")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.gateway, args.token)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
