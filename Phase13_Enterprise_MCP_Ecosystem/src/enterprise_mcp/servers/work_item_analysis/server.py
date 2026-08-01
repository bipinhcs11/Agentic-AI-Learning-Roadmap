"""Streamable HTTP Work Item Analysis MCP server."""

from functools import lru_cache

import httpx
from mcp.server.fastmcp import FastMCP

from enterprise_mcp.servers.runtime import run_server
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.factory import build_api_client
from enterprise_mcp.shared.security import current_trace

from .service import WorkItemAnalysisService

mcp = FastMCP("Work Item Analysis", stateless_http=True, json_response=True)


@lru_cache
def _service() -> WorkItemAnalysisService:
    settings = load_settings()
    return WorkItemAnalysisService(
        build_api_client("work_item_analysis", settings, http_client=httpx.AsyncClient())
    )


@mcp.tool()
async def work_item_analyze(work_item_id: str) -> dict:
    """Read participant, enrollment, rate, and six months of life-event evidence."""
    return await _service().analyze(work_item_id, current_trace())


def main() -> None:
    run_server(mcp, "work_item_analysis")


if __name__ == "__main__":
    main()
