from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.observability import TraceContext
from enterprise_mcp.shared.security import (
    GatewayJwtMiddleware,
    InboundJwtVerifier,
    InternalAssertionIssuer,
    InternalAssertionMiddleware,
    Principal,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


class CaptureAudit:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


async def ok(request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def test_gateway_middleware_denies_missing_token_with_discovery_header(monkeypatch) -> None:
    settings = load_settings("local", CONFIG_DIR)
    monkeypatch.setenv("MCP_GATEWAY_JWT_SECRET", "gateway-test-key-at-least-thirty-two-bytes")
    audit = CaptureAudit()
    app = Starlette(routes=[Route("/mcp", ok)])
    app.add_middleware(
        GatewayJwtMiddleware,
        verifier=InboundJwtVerifier(
            settings.gateway.inbound_jwt,
            settings.gateway.approved_clients,
        ),
        public_url=settings.gateway.public_url,
        registry_digest="sha256:fictional",
        audit_sink=audit,
    )

    response = TestClient(app).get("/mcp")
    assert response.status_code == 401
    assert "resource_metadata=" in response.headers["www-authenticate"]
    assert audit.events[-1].decision == "DENY"
    assert audit.events[-1].reason_code == "AUTHENTICATION_REQUIRED"


def test_scenario_middleware_rejects_assertion_for_another_tool(monkeypatch) -> None:
    settings = load_settings("test", CONFIG_DIR)
    secret = "config-assertion-test-key-at-least-thirty-two-bytes"
    monkeypatch.setenv("MCP_CONFIG_CHECK_ASSERTION_SECRET", secret)
    issuer = InternalAssertionIssuer(settings)
    principal = Principal("fictional-developer", "vscode-devassist", {})
    app = Starlette(routes=[Route("/mcp", ok)])
    app.add_middleware(
        InternalAssertionMiddleware,
        gateway=settings.gateway,
        scenario="config_check",
        scenario_config=settings.scenarios["config_check"],
        expected_tool="config_check",
    )
    client = TestClient(app)

    valid = issuer.issue(
        scenario="config_check",
        tool="config_check",
        principal=principal,
        trace=TraceContext.new(),
    )
    assert client.get("/mcp", headers={"Authorization": f"Bearer {valid}"}).status_code == 200

    wrong_tool = issuer.issue(
        scenario="config_check",
        tool="not_config_check",
        principal=principal,
        trace=TraceContext.new(),
    )
    response = client.get("/mcp", headers={"Authorization": f"Bearer {wrong_tool}"})
    assert response.status_code == 401
    assert response.json()["error"] == "INVALID_GATEWAY_ASSERTION"
