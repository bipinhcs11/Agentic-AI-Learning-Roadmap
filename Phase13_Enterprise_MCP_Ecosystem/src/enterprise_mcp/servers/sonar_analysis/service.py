"""Bounded read-only Sonar issue retrieval."""

from __future__ import annotations

import re
from typing import Any

from enterprise_mcp.shared.api_client import GatewayApiClient
from enterprise_mcp.shared.observability import TraceContext

PROJECT_KEY = re.compile(r"^[A-Za-z0-9_.:-]{3,100}$")


class SonarAnalysisService:
    def __init__(self, api: GatewayApiClient) -> None:
        self._api = api

    async def get_issues(
        self, project_key: str, severity: str = "MAJOR", trace: TraceContext | None = None
    ) -> dict[str, Any]:
        if not PROJECT_KEY.fullmatch(project_key):
            raise ValueError("project_key contains unsupported characters")
        normalized_severity = severity.upper()
        if normalized_severity not in {"INFO", "MINOR", "MAJOR", "CRITICAL", "BLOCKER"}:
            raise ValueError("severity is not supported")
        current_trace = trace or TraceContext.new()
        payload = await self._api.get_json(
            operation="sonar.issues.list",
            path=f"/sonar/projects/{project_key}/issues",
            query={"severity": normalized_severity, "limit": 50},
            trace=current_trace,
        )
        issues = payload.get("issues", [])[:50]
        return {
            "projectKey": project_key,
            "issues": issues,
            "issueCount": len(issues),
            "traceId": current_trace.trace_id,
        }
