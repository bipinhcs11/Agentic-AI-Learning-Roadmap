"""Deterministic work-item evidence aggregation; no server-side agent."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from enterprise_mcp.shared.api_client import GatewayApiClient
from enterprise_mcp.shared.observability import TraceContext

WORK_ITEM_PATTERN = re.compile(r"^WI-DEMO-[0-9]{3}$")


class WorkItemAnalysisService:
    def __init__(self, api: GatewayApiClient) -> None:
        self._api = api

    async def analyze(self, work_item_id: str, trace: TraceContext | None = None) -> dict[str, Any]:
        if not WORK_ITEM_PATTERN.fullmatch(work_item_id):
            raise ValueError("work_item_id must match WI-DEMO-NNN")
        current_trace = trace or TraceContext.new()
        work_item = await self._api.get_json(
            operation="work_item.get",
            path=f"/work-items/{work_item_id}",
            trace=current_trace,
        )
        participant_id = str(work_item["participantId"])
        participant, enrollment, rate, life_events = await asyncio.gather(
            self._api.get_json(
                operation="participant.get",
                path=f"/participants/{participant_id}",
                trace=current_trace,
            ),
            self._api.get_json(
                operation="enrollment.get",
                path=f"/participants/{participant_id}/enrollment",
                trace=current_trace,
            ),
            self._api.get_json(
                operation="rate.get",
                path=f"/participants/{participant_id}/rate",
                trace=current_trace,
            ),
            self._api.get_json(
                operation="life_events.list",
                path=f"/participants/{participant_id}/life-events",
                query={"months": 6},
                trace=current_trace,
            ),
        )
        missing = [
            name
            for name, value in {
                "participant": participant,
                "enrollment": enrollment,
                "rate": rate,
            }.items()
            if not value
        ]
        return {
            "workItemId": work_item_id,
            "participantId": participant_id,
            "evidence": {
                "participant": participant,
                "enrollment": enrollment,
                "rate": rate,
                "lifeEvents": life_events[:20] if isinstance(life_events, list) else life_events,
            },
            "missingEvidence": missing,
            "nextApprovedTool": "config_check" if missing else None,
            "traceId": current_trace.trace_id,
        }
