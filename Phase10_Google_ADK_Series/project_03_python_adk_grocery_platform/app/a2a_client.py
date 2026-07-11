"""Local A2A boundary demo for the grocery concierge."""

from __future__ import annotations

from typing import Any

from app.security import mint_agent_assertion, verify_agent_assertion


def request_delivery_window(
    zip_code: str,
    requested_day: str,
    agent_assertion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Simulate a signed A2A call to the delivery scheduler agent.

    Args:
        zip_code: Delivery ZIP code.
        requested_day: Requested delivery day.
        agent_assertion: Optional signed identity assertion from caller.

    Returns:
        Available delivery windows or a spoofing-related denial.
    """
    assertion = agent_assertion or mint_agent_assertion(
        agent_id="grocery-concierge",
        audience="grocery-platform",
        ttl_seconds=120,
    )["assertion"]
    verification = verify_agent_assertion(assertion, expected_audience="grocery-platform")
    if verification["status"] != "trusted":
        return {"status": "denied", "identity": verification}

    zone = "urban" if zip_code.startswith(("6", "7", "8", "9")) else "standard"
    windows = (
        ["09:00-11:00", "13:00-15:00", "18:00-20:00"]
        if zone == "urban"
        else ["10:00-12:00", "16:00-18:00"]
    )
    return {
        "status": "success",
        "protocol": "A2A",
        "remote_agent": "delivery-scheduler",
        "identity": verification,
        "requested_day": requested_day,
        "zip_code": zip_code,
        "available_windows": windows,
        "recommended_window": windows[0],
    }
