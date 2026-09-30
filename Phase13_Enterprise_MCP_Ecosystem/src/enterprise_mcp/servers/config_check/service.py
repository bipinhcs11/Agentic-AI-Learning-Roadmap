"""Read-only configuration diagnosis."""

from __future__ import annotations

import re
from typing import Any

from enterprise_mcp.shared.api_client import GatewayApiClient
from enterprise_mcp.shared.observability import TraceContext

PARTICIPANT_PATTERN = re.compile(r"^P-DEMO-[0-9]{3}$")


class ConfigCheckService:
    def __init__(self, api: GatewayApiClient) -> None:
        self._api = api

    async def check(self, participant_id: str, trace: TraceContext | None = None) -> dict[str, Any]:
        if not PARTICIPANT_PATTERN.fullmatch(participant_id):
            raise ValueError("participant_id must match P-DEMO-NNN")
        current_trace = trace or TraceContext.new()
        config = await self._api.get_json(
            operation="configuration.get",
            path=f"/configurations/participants/{participant_id}",
            trace=current_trace,
        )
        missing = sorted(key for key, value in config.items() if value in {None, "", False})
        diagnosis = "CONFIGURATION_PRESENT"
        if "enrollmentPlanConfigured" in missing:
            diagnosis = "MISSING_ENROLLMENT_CONFIGURATION"
        elif missing:
            diagnosis = "CONFIGURATION_GAP"
        return {
            "participantId": participant_id,
            "configuration": config,
            "missingConfiguration": missing,
            "diagnosis": diagnosis,
            "traceId": current_trace.trace_id,
        }
