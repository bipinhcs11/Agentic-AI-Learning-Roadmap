"""Read-only approved-skill discovery."""

from __future__ import annotations

import re
from typing import Any

from enterprise_mcp.shared.api_client import GatewayApiClient
from enterprise_mcp.shared.observability import TraceContext

DOMAIN = re.compile(r"^[a-z][a-z0-9-]{1,31}$")


class SkillsCatalogService:
    def __init__(self, api: GatewayApiClient) -> None:
        self._api = api

    async def list_approved(self, domain: str, trace: TraceContext | None = None) -> dict[str, Any]:
        if not DOMAIN.fullmatch(domain):
            raise ValueError("domain must be a lowercase approved identifier")
        current_trace = trace or TraceContext.new()
        payload = await self._api.get_json(
            operation="skills.catalog.list",
            path="/skills",
            query={"domain": domain, "status": "approved", "limit": 50},
            trace=current_trace,
        )
        skills = payload.get("skills", [])[:50]
        return {"domain": domain, "skills": skills, "traceId": current_trace.trace_id}
