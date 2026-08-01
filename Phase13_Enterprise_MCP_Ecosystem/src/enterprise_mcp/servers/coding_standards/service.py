"""Versioned coding-standard lookup through the internal API gateway."""

from __future__ import annotations

import re
from typing import Any

from enterprise_mcp.shared.api_client import GatewayApiClient
from enterprise_mcp.shared.observability import TraceContext

RULE_ID = re.compile(r"^[A-Z][A-Z0-9_-]{2,31}$")


class CodingStandardsService:
    def __init__(self, api: GatewayApiClient) -> None:
        self._api = api

    async def get_rule(self, rule_id: str, trace: TraceContext | None = None) -> dict[str, Any]:
        if not RULE_ID.fullmatch(rule_id):
            raise ValueError("rule_id must be an approved uppercase rule identifier")
        current_trace = trace or TraceContext.new()
        rule = await self._api.get_json(
            operation="standards.rule.get",
            path=f"/standards/rules/{rule_id}",
            trace=current_trace,
        )
        return {"rule": rule, "traceId": current_trace.trace_id}
