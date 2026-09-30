"""ASGI runtime shared by the separately deployable scenario servers."""

from __future__ import annotations

import contextlib
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from enterprise_mcp.shared.config import Settings, load_settings
from enterprise_mcp.shared.observability import configure_safe_logging
from enterprise_mcp.shared.security import InternalAssertionMiddleware

SCENARIO_TOOLS = {
    "work_item_analysis": "work_item_analyze",
    "config_check": "config_check",
}


async def _health(request: Any) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def protected_mcp_app(mcp: Any, scenario: str, settings: Settings | None = None) -> Starlette:
    resolved = settings or load_settings()
    configure_safe_logging()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp.session_manager.run():
            yield

    app = Starlette(
        routes=[Route("/health", _health), Mount("/", app=mcp.streamable_http_app())],
        lifespan=lifespan,
    )
    app.add_middleware(
        InternalAssertionMiddleware,
        gateway=resolved.gateway,
        scenario=scenario,
        scenario_config=resolved.scenarios[scenario],
        expected_tool=SCENARIO_TOOLS[scenario],
    )
    return app


def run_server(mcp: Any, scenario: str) -> None:
    settings = load_settings()
    scenario_config = settings.scenarios[scenario]
    uvicorn.run(
        protected_mcp_app(mcp, scenario, settings),
        host=settings.runtime.service_host,
        port=scenario_config.port,
        log_level=settings.runtime.log_level.lower(),
        access_log=False,
    )
