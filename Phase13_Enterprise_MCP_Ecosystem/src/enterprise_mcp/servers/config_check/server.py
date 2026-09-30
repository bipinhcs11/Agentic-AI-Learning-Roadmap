"""Streamable HTTP Config Check MCP server."""

from functools import lru_cache

import httpx

from enterprise_mcp.servers.factory import scenario_fast_mcp
from enterprise_mcp.servers.runtime import run_server
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.factory import build_api_client
from enterprise_mcp.shared.security import current_trace

from .service import ConfigCheckService

mcp = scenario_fast_mcp("Config Check", "config_check")


@lru_cache
def _service() -> ConfigCheckService:
    settings = load_settings()
    return ConfigCheckService(
        build_api_client("config_check", settings, http_client=httpx.AsyncClient())
    )


@mcp.tool()
async def config_check(participant_id: str) -> dict:
    """Read the approved participant configuration and identify missing values."""
    return await _service().check(participant_id, current_trace())


def main() -> None:
    run_server(mcp, "config_check")


if __name__ == "__main__":
    main()
