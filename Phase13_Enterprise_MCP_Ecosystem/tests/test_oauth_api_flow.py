from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from enterprise_mcp.shared.api_client import GatewayApiClient
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.errors import UpstreamApiError
from enterprise_mcp.shared.oauth import ClientCredentialsTokenProvider
from enterprise_mcp.shared.observability import NullAuditSink, TraceContext
from enterprise_mcp.shared.secrets import ApiCredential

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


class StaticSecrets:
    def get_api_credential(self, scenario):
        return ApiCredential(client_id="test-client", client_secret=SecretStr("test-secret"))


@pytest.mark.asyncio
async def test_fresh_token_call_happens_before_each_api_operation() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth2/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "header.payload.fictional-signature-value",
                    "token_type": "Bearer",
                    "expires_in": 300,
                },
            )
        assert request.headers["authorization"] == (
            "Bearer header.payload.fictional-signature-value"
        )
        return httpx.Response(200, json={"status": "ok"})

    settings = load_settings("test", CONFIG_DIR)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        token_provider = ClientCredentialsTokenProvider(
            settings.oauth,
            settings.scenarios["work_item_analysis"],
            StaticSecrets(),
            http,
            clock=lambda: 100.0,
        )
        client = GatewayApiClient(
            service_name="work_item_analysis",
            downstream_service="internal-api-gateway",
            config=settings.api_gateway,
            token_provider=token_provider,
            http_client=http,
            audit_sink=NullAuditSink(),
        )
        trace = TraceContext.new()
        first = await client.get_json(
            operation="participant.get", path="/participants/P-DEMO-001", trace=trace
        )
        second = await client.get_json(
            operation="participant.get", path="/participants/P-DEMO-001", trace=trace
        )

    assert first == {"status": "ok"}
    assert second == {"status": "ok"}
    assert [request.method for request in requests] == ["POST", "GET", "POST", "GET"]
    form = dict(item.split("=", 1) for item in requests[0].content.decode().split("&"))
    assert form["grant_type"] == "client_credentials"
    assert "test-secret" in requests[0].content.decode()
    assert "test-secret" not in json.dumps(first)


@pytest.mark.asyncio
async def test_api_client_rejects_arbitrary_url() -> None:
    settings = load_settings("test", CONFIG_DIR)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: None)) as http:
        token_provider = ClientCredentialsTokenProvider(
            settings.oauth,
            settings.scenarios["work_item_analysis"],
            StaticSecrets(),
            http,
        )
        client = GatewayApiClient(
            service_name="work_item_analysis",
            downstream_service="internal-api-gateway",
            config=settings.api_gateway,
            token_provider=token_provider,
            http_client=http,
            audit_sink=NullAuditSink(),
        )
        with pytest.raises(UpstreamApiError):
            await client.get_json(
                operation="bad", path="https://attacker.invalid/data", trace=TraceContext.new()
            )
