"""Single governed MCP endpoint for IDE clients."""

from __future__ import annotations

import contextlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from enterprise_mcp.shared.config import Settings, load_settings
from enterprise_mcp.shared.security import GatewayJwtMiddleware, InboundJwtVerifier

from .downstream import DownstreamMcpClient
from .registry import RegistrySnapshot

mcp = FastMCP("Enterprise MCP Gateway", stateless_http=True, json_response=True)


@lru_cache
def _settings() -> Settings:
    return load_settings()


@lru_cache
def _downstream() -> DownstreamMcpClient:
    return DownstreamMcpClient(_settings())


@lru_cache
def _registry() -> RegistrySnapshot:
    root = Path(__file__).resolve().parents[3]
    return RegistrySnapshot.load(
        root / _settings().gateway.registry_dir,
        root / "contracts" / "enterprise-mcp-manifest.schema.json",
    )


@mcp.tool()
async def work_item_analyze(work_item_id: str) -> Any:
    """Analyze a fictional work item using approved read-only domain APIs."""
    _registry().require("devassist.work-item-analysis", "work_item_analyze")
    return await _downstream().call_tool(
        scenario="work_item_analysis",
        tool="work_item_analyze",
        arguments={"work_item_id": work_item_id},
    )


@mcp.tool()
async def config_check(participant_id: str) -> Any:
    """Check approved configuration values when work-item evidence is missing."""
    _registry().require("devassist.config-check", "config_check")
    return await _downstream().call_tool(
        scenario="config_check",
        tool="config_check",
        arguments={"participant_id": participant_id},
    )


@mcp.tool()
async def sonar_get_issues(project_key: str, severity: str = "MAJOR") -> Any:
    """Read bounded Sonar issues for an approved project."""
    _registry().require("devassist.sonar-analysis", "sonar_get_issues")
    return await _downstream().call_tool(
        scenario="sonar_analysis",
        tool="sonar_get_issues",
        arguments={"project_key": project_key, "severity": severity},
    )


@mcp.tool()
async def standards_get_rule(rule_id: str) -> Any:
    """Read one approved and versioned coding standard."""
    _registry().require("devassist.coding-standards", "standards_get_rule")
    return await _downstream().call_tool(
        scenario="coding_standards",
        tool="standards_get_rule",
        arguments={"rule_id": rule_id},
    )


@mcp.tool()
async def skills_list_approved(domain: str) -> Any:
    """List approved domain skills without creating or modifying a branch."""
    _registry().require("devassist.skills-catalog", "skills_list_approved")
    return await _downstream().call_tool(
        scenario="skills_catalog",
        tool="skills_list_approved",
        arguments={"domain": domain},
    )


async def _health(request: Any) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "enterprise-mcp-gateway"})


def build_app(settings: Settings | None = None) -> Starlette:
    resolved = settings or _settings()
    _registry()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[Route("/health", _health), Mount("/", app=mcp.streamable_http_app())],
        lifespan=lifespan,
    )
    app.add_middleware(
        GatewayJwtMiddleware,
        verifier=InboundJwtVerifier(
            resolved.gateway.inbound_jwt,
            resolved.gateway.approved_clients,
        ),
    )
    return app


def main() -> None:
    settings = _settings()
    uvicorn.run(
        build_app(settings),
        host=settings.gateway.host,
        port=settings.gateway.port,
        log_level=settings.runtime.log_level.lower(),
    )


if __name__ == "__main__":
    main()
