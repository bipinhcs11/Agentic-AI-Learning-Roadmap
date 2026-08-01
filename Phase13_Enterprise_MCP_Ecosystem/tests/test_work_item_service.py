import pytest

from enterprise_mcp.servers.work_item_analysis.service import WorkItemAnalysisService


class FakeApi:
    def __init__(self) -> None:
        self.operations: list[str] = []

    async def get_json(self, *, operation, path, trace, query=None):
        self.operations.append(operation)
        values = {
            "work_item.get": {"participantId": "P-DEMO-001"},
            "participant.get": {"status": "ACTIVE"},
            "enrollment.get": {},
            "rate.get": {"rateBand": "FICTIONAL-A"},
            "life_events.list": [{"type": "FICTIONAL_STATUS_CHANGE"}],
        }
        return values[operation]


@pytest.mark.asyncio
async def test_missing_enrollment_returns_config_check_as_next_tool() -> None:
    api = FakeApi()
    result = await WorkItemAnalysisService(api).analyze("WI-DEMO-001")

    assert result["participantId"] == "P-DEMO-001"
    assert result["missingEvidence"] == ["enrollment"]
    assert result["nextApprovedTool"] == "config_check"
    assert set(api.operations) == {
        "work_item.get",
        "participant.get",
        "enrollment.get",
        "rate.get",
        "life_events.list",
    }


@pytest.mark.asyncio
async def test_invalid_work_item_id_is_rejected_before_api_call() -> None:
    api = FakeApi()
    with pytest.raises(ValueError):
        await WorkItemAnalysisService(api).analyze("REAL-WORK-ITEM")
    assert api.operations == []
