"""Streamable HTTP Coding Standards MCP server."""

from functools import lru_cache

import httpx
from mcp.server.fastmcp import FastMCP

from enterprise_mcp.servers.runtime import run_server
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.factory import build_api_client
from enterprise_mcp.shared.security import current_trace

from .service import CodingStandardsService

mcp = FastMCP("Coding Standards", stateless_http=True, json_response=True)


@lru_cache
def _service() -> CodingStandardsService:
    settings = load_settings()
    return CodingStandardsService(
        build_api_client("coding_standards", settings, http_client=httpx.AsyncClient())
    )


@mcp.tool()
async def standards_get_rule(rule_id: str) -> dict:
    """Return an approved versioned coding standard by rule ID."""
    return await _service().get_rule(rule_id, current_trace())


def main() -> None:
    run_server(mcp, "coding_standards")


if __name__ == "__main__":
    main()
