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
            "roles": [settings.gateway.required_role],
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


@pytest.mark.parametrize(
    ("claim_override", "expected_exception"),
    [
        ({"exp": 1}, jwt.InvalidTokenError),
        ({"aud": "another-resource"}, jwt.InvalidTokenError),
        ({"client_id": "unapproved-client"}, jwt.InvalidTokenError),
    ],
)
def test_gateway_rejects_invalid_identity_boundaries(
    monkeypatch, claim_override: dict[str, object], expected_exception: type[Exception]
) -> None:
    settings = load_settings("local", CONFIG_DIR)
    secret = "local-gateway-test-secret-at-least-32-bytes"
    monkeypatch.setenv("MCP_GATEWAY_JWT_SECRET", secret)
    now = int(time.time())
    claims = {
        "iss": settings.gateway.inbound_jwt.issuer,
        "sub": "fictional-user",
        "aud": settings.gateway.inbound_jwt.audience,
        "client_id": "vscode-devassist",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(claim_override)
    encoded = jwt.encode(claims, secret, algorithm="HS256")

    with pytest.raises(expected_exception):
        InboundJwtVerifier(settings.gateway.inbound_jwt, settings.gateway.approved_clients).verify(
            encoded
        )


def test_internal_assertion_is_tool_and_audience_bound(monkeypatch) -> None:
    settings = load_settings("test", CONFIG_DIR)
    secret = "internal-assertion-test-secret-at-least-32-bytes"
    monkeypatch.setenv("MCP_CONFIG_CHECK_ASSERTION_SECRET", secret)
    principal = Principal("fictional-user", "vscode-devassist", {})
    trace = TraceContext.new()

    encoded = InternalAssertionIssuer(settings).issue(
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
            audience="enterprise-mcp:work_item_analysis",
            issuer="enterprise-mcp-gateway",
        )
