"""Streamable HTTP Sonar Analysis MCP server."""

from functools import lru_cache

import httpx
from mcp.server.fastmcp import FastMCP

from enterprise_mcp.servers.runtime import run_server
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.factory import build_api_client
from enterprise_mcp.shared.security import current_trace

from .service import SonarAnalysisService

mcp = FastMCP("Sonar Analysis", stateless_http=True, json_response=True)


@lru_cache
def _service() -> SonarAnalysisService:
    settings = load_settings()
    return SonarAnalysisService(
        build_api_client("sonar_analysis", settings, http_client=httpx.AsyncClient())
    )


@mcp.tool()
async def sonar_get_issues(project_key: str, severity: str = "MAJOR") -> dict:
    """Return bounded Sonar issues without source snippets or write actions."""
    return await _service().get_issues(project_key, severity, current_trace())


def main() -> None:
    run_server(mcp, "sonar_analysis")


if __name__ == "__main__":
    main()
