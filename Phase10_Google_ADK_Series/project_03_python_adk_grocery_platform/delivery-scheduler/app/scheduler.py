"""Delivery scheduler domain logic for the remote A2A agent."""

from __future__ import annotations

from typing import Any


def recommend_delivery_windows(zip_code: str, requested_day: str) -> dict[str, Any]:
    """Return fictional delivery windows for a grocery order."""
    zone = "urban" if zip_code.startswith(("6", "7", "8", "9")) else "standard"
    windows = (
        ["09:00-11:00", "13:00-15:00", "18:00-20:00"]
        if zone == "urban"
        else ["10:00-12:00", "16:00-18:00"]
    )
    return {
        "status": "success",
        "requested_day": requested_day,
        "zip_code": zip_code,
        "available_windows": windows,
        "recommended_window": windows[0],
    }
