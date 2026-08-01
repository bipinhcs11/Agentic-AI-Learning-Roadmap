"""Streamable HTTP Skills Catalog MCP server."""

from functools import lru_cache

import httpx
from mcp.server.fastmcp import FastMCP

from enterprise_mcp.servers.runtime import run_server
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.factory import build_api_client
from enterprise_mcp.shared.security import current_trace

from .service import SkillsCatalogService

mcp = FastMCP("Skills Catalog", stateless_http=True, json_response=True)


@lru_cache
def _service() -> SkillsCatalogService:
    settings = load_settings()
    return SkillsCatalogService(
        build_api_client("skills_catalog", settings, http_client=httpx.AsyncClient())
    )


@mcp.tool()
async def skills_list_approved(domain: str) -> dict:
    """List approved domain skills; this tool does not create or modify branches."""
    return await _service().list_approved(domain, current_trace())


def main() -> None:
    run_server(mcp, "skills_catalog")


if __name__ == "__main__":
    main()
