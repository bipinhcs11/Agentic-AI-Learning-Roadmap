import time
from pathlib import Path

import jwt
import pytest

from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.observability import TraceContext
from enterprise_mcp.shared.security import InboundJwtVerifier, InternalAssertionIssuer, Principal

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_gateway_verifies_approved_local_client(monkeypatch) -> None:
    settings = load_settings("local", CONFIG_DIR)
    secret = "local-gateway-test-secret-at-least-32-bytes"
    monkeypatch.setenv("MCP_GATEWAY_JWT_SECRET", secret)
    now = int(time.time())
    encoded = jwt.encode(
        {
            "iss": settings.gateway.inbound_jwt.issuer,
            "sub": "fictional-user",
            "aud": settings.gateway.inbound_jwt.audience,
            "client_id": "vscode-devassist",
            "iat": now,
            "exp": now + 300,
        },
        secret,
        algorithm="HS256",
    )
    principal = InboundJwtVerifier(
        settings.gateway.inbound_jwt, settings.gateway.approved_clients
    ).verify(encoded)
    assert principal.client_id == "vscode-devassist"


def test_internal_assertion_is_tool_and_audience_bound(monkeypatch) -> None:
    settings = load_settings("test", CONFIG_DIR)
    secret = "internal-assertion-test-secret-at-least-32-bytes"
    monkeypatch.setenv("MCP_INTERNAL_ASSERTION_SECRET", secret)
    principal = Principal("fictional-user", "vscode-devassist", {})
    trace = TraceContext.new()

    encoded = InternalAssertionIssuer(settings.gateway).issue(
        scenario="config_check",
        tool="config_check",
        principal=principal,
        trace=trace,
    )
    claims = jwt.decode(
        encoded,
        secret,
        algorithms=["HS256"],
        audience="enterprise-mcp:config_check",
        issuer="enterprise-mcp-gateway",
    )
    assert claims["tool"] == "config_check"
    assert claims["trace_id"] == trace.trace_id

    with pytest.raises(jwt.InvalidAudienceError):
        jwt.decode(
            encoded,
            secret,
            algorithms=["HS256"],
            audience="enterprise-mcp:sonar_analysis",
            issuer="enterprise-mcp-gateway",
        )
