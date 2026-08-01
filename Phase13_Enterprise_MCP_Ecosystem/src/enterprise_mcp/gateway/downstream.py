"""Gateway-to-server MCP client using a one-call internal assertion."""

from __future__ import annotations

import json
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from enterprise_mcp.shared.config import Settings
from enterprise_mcp.shared.errors import UpstreamApiError
from enterprise_mcp.shared.security import (
    InternalAssertionIssuer,
    current_principal,
    current_trace,
)


class DownstreamMcpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._assertions = InternalAssertionIssuer(settings.gateway)

    async def call_tool(
        self,
        *,
        scenario: str,
        tool: str,
        arguments: dict[str, Any],
    ) -> Any:
        principal = current_principal()
        trace = current_trace()
        assertion = self._assertions.issue(
            scenario=scenario,
            tool=tool,
            principal=principal,
            trace=trace,
        )
        scenario_config = self._settings.scenarios[scenario]
        headers = {
            "Authorization": f"Bearer {assertion}",
            "traceparent": trace.traceparent,
        }
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=self._settings.api_gateway.request_timeout_seconds,
                follow_redirects=False,
            ) as http_client:
                async with streamable_http_client(
                    scenario_config.server_url,
                    http_client=http_client,
                ) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(tool, arguments=arguments)
        except Exception as exc:
            raise UpstreamApiError(f"MCP server call failed: {scenario}/{tool}") from exc

        if getattr(result, "isError", False):
            raise UpstreamApiError(f"MCP server returned a tool error: {scenario}/{tool}")
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            return structured
        text_items = [getattr(item, "text", None) for item in getattr(result, "content", [])]
        populated = [item for item in text_items if item is not None]
        if len(populated) == 1:
            try:
                return json.loads(populated[0])
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "content": populated,
            "traceId": trace.trace_id,
        }
