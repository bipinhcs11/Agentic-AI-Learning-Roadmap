from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from enterprise_mcp.gateway.policy import GatewayPolicy
from enterprise_mcp.gateway.registry import RegistrySnapshot
from enterprise_mcp.gateway.server import build_app, mcp
from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.errors import PolicyDeniedError
from enterprise_mcp.shared.observability import TraceContext
from enterprise_mcp.shared.security import Principal
from enterprise_mcp.shared.transport import transport_security_for_url

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"


class CaptureAudit:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


def _registry() -> RegistrySnapshot:
    return RegistrySnapshot.load(
        ROOT / "registry" / "manifests",
        ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
    )


def test_transport_security_accepts_configured_service_host() -> None:
    security = transport_security_for_url("http://work-item-analysis:8101/mcp")
    assert security.enable_dns_rebinding_protection is True
    assert security.allowed_hosts == ["work-item-analysis:8101"]
    assert "127.0.0.1:*" not in security.allowed_hosts


@pytest.mark.asyncio
async def test_gateway_advertises_and_enforces_manifest_schema() -> None:
    build_app(load_settings("local", CONFIG_DIR))
    tool = mcp._tool_manager._tools["config_check"]
    assert tool.parameters["additionalProperties"] is False
    assert tool.parameters["properties"]["participant_id"]["pattern"] == "^P-DEMO-[0-9]{3}$"

    with pytest.raises(ToolError, match="extra_forbidden"):
        await tool.run({"participant_id": "P-DEMO-001", "injected_field": "blocked"})


def test_policy_allows_only_role_client_and_fictional_resource(monkeypatch) -> None:
    settings = load_settings("test", CONFIG_DIR)
    audit = CaptureAudit()
    principal = Principal(
        subject="fictional-developer",
        client_id="vscode-devassist",
        claims={"roles": [settings.gateway.required_role]},
    )
    monkeypatch.setattr("enterprise_mcp.gateway.policy.current_principal", lambda: principal)
    monkeypatch.setattr(
        "enterprise_mcp.gateway.policy.current_trace",
        lambda: TraceContext.new(),
    )
    policy = GatewayPolicy(settings, _registry(), audit)

    allowed = policy.authorize(
        server_id="devassist.work-item-analysis",
        tool_name="work_item_analyze",
        resource_name="work_item_id",
        resource_value="WI-DEMO-001",
    )
    assert allowed.name == "work_item_analyze"
    assert audit.events[-1].decision == "ALLOW"
    assert audit.events[-1].registry_digest == _registry().digest
    assert audit.events[-1].subject_ref.startswith("sha256:")
    assert audit.events[-1].resource_ref.startswith("sha256:")
    assert audit.events[-1].resource_ref != "WI-DEMO-001"

    with pytest.raises(PolicyDeniedError):
        policy.authorize(
            server_id="devassist.work-item-analysis",
            tool_name="work_item_analyze",
            resource_name="work_item_id",
            resource_value="WI-DEMO-999",
        )
    assert audit.events[-1].decision == "DENY"
    assert audit.events[-1].reason_code == "POLICY_DENIED"
