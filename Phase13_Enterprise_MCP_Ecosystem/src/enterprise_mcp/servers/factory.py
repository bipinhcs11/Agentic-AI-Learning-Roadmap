"""Create scenario MCP servers with environment-specific transport controls."""

from mcp.server.fastmcp import FastMCP

from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.transport import governed_fast_mcp


def scenario_fast_mcp(name: str, scenario: str) -> FastMCP:
    settings = load_settings()
    config = settings.scenarios[scenario]
    return governed_fast_mcp(
        name,
        bind_host=settings.runtime.service_host,
        port=config.port,
        public_url=config.server_url,
    )
