"""Single governed MCP endpoint for the two-server diagnostic POC."""

from __future__ import annotations

import asyncio
import contextlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from enterprise_mcp.shared.config import Settings, load_settings
from enterprise_mcp.shared.errors import UpstreamApiError
from enterprise_mcp.shared.observability import configure_safe_logging
from enterprise_mcp.shared.security import GatewayJwtMiddleware, InboundJwtVerifier
from enterprise_mcp.shared.transport import governed_fast_mcp

from .downstream import DownstreamMcpClient
from .policy import GatewayPolicy
from .registry import RegistrySnapshot
from .schema_controls import bind_registry_schemas


@lru_cache
def _settings() -> Settings:
    return load_settings()


mcp = governed_fast_mcp(
    "Enterprise MCP Gateway",
    bind_host=_settings().gateway.host,
    port=_settings().gateway.port,
    public_url=_settings().gateway.public_url,
)


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


@lru_cache
def _policy() -> GatewayPolicy:
    return GatewayPolicy(_settings(), _registry())


@lru_cache
def _bind_registry_controls() -> None:
    bind_registry_schemas(mcp, _registry())


async def _invoke(
    *,
    server_id: str,
    scenario: str,
    tool: str,
    arguments: dict[str, Any],
    resource_name: str,
) -> Any:
    registered = _policy().authorize(
        server_id=server_id,
        tool_name=tool,
        resource_name=resource_name,
        resource_value=str(arguments[resource_name]),
    )
    try:
        async with asyncio.timeout(registered.timeout_ms / 1000):
            result = await _downstream().call_tool(
                scenario=scenario,
                tool=tool,
                arguments=arguments,
            )
    except TimeoutError as exc:
        raise UpstreamApiError("Approved MCP server call exceeded its registry timeout") from exc
    encoded = json.dumps(result, separators=(",", ":")).encode("utf-8")
    if len(encoded) > registered.max_response_bytes:
        raise UpstreamApiError("Approved MCP server result exceeded its registry limit")
    return result


@mcp.tool()
async def work_item_analyze(work_item_id: str) -> Any:
    """Analyze one approved fictional work item using read-only domain APIs."""
    return await _invoke(
        server_id="devassist.work-item-analysis",
        scenario="work_item_analysis",
        tool="work_item_analyze",
        arguments={"work_item_id": work_item_id},
        resource_name="work_item_id",
    )


@mcp.tool()
async def config_check(participant_id: str) -> Any:
    """Check approved configuration when fictional work-item evidence is missing."""
    return await _invoke(
        server_id="devassist.config-check",
        scenario="config_check",
        tool="config_check",
        arguments={"participant_id": participant_id},
        resource_name="participant_id",
    )


async def _health(request: Any) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "enterprise-mcp-gateway"})


async def _ready(request: Any) -> JSONResponse:
    return JSONResponse({"status": "ready", "registryDigest": _registry().digest})


async def _protected_resource_metadata(request: Any) -> JSONResponse:
    settings = _settings()
    public_url = settings.gateway.public_url.rstrip("/")
    return JSONResponse(
        {
            "resource": f"{public_url}/mcp",
            "authorization_servers": [settings.gateway.inbound_jwt.issuer],
            "bearer_methods_supported": ["header"],
            "resource_name": "Enterprise MCP Gateway",
        }
    )


def build_app(settings: Settings | None = None) -> Starlette:
    resolved = settings or _settings()
    _bind_registry_controls()
    configure_safe_logging()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/health", _health),
            Route("/ready", _ready),
            Route("/.well-known/oauth-protected-resource", _protected_resource_metadata),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(
        GatewayJwtMiddleware,
        verifier=InboundJwtVerifier(
            resolved.gateway.inbound_jwt,
            resolved.gateway.approved_clients,
        ),
        public_url=resolved.gateway.public_url,
        registry_digest=_registry().digest,
    )
    return app


def main() -> None:
    settings = _settings()
    uvicorn.run(
        build_app(settings),
        host=settings.gateway.host,
        port=settings.gateway.port,
        log_level=settings.runtime.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
