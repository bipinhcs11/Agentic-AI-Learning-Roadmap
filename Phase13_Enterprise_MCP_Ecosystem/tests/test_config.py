from pathlib import Path

import pytest

from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.errors import ConfigurationError

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_local_overlay_uses_environment_credentials() -> None:
    settings = load_settings("local", CONFIG_DIR)

    assert settings.runtime.environment == "local"
    assert settings.secret_provider == "environment"
    assert settings.oauth.token_url == "http://127.0.0.1:9000/oauth2/token"
    assert settings.scenarios["work_item_analysis"].secret_path.startswith("mcp/local/")


def test_dev_overlay_uses_vault_and_tls() -> None:
    settings = load_settings("dev", CONFIG_DIR)

    assert settings.secret_provider == "vault"
    assert settings.vault.verify_tls is True
    assert settings.api_gateway.base_url.startswith("https://")
    assert all(item.server_url.startswith("https://") for item in settings.scenarios.values())
    assert settings.scenarios["config_check"].secret_path.startswith("mcp/dev/")


def test_unknown_environment_fails_closed() -> None:
    with pytest.raises(ConfigurationError):
        load_settings("unknown", CONFIG_DIR)


def test_container_endpoint_overrides_are_applied(monkeypatch) -> None:
    monkeypatch.setenv("MCP_SERVICE_HOST", "0.0.0.0")  # noqa: S104 - container test
    monkeypatch.setenv(
        "MCP_WORK_ITEM_SERVER_URL",
        "http://work-item-analysis:8101/mcp",
    )

    settings = load_settings("local", CONFIG_DIR)

    assert settings.runtime.service_host == "0.0.0.0"  # noqa: S104 - container test
    assert (
        settings.scenarios["work_item_analysis"].server_url == "http://work-item-analysis:8101/mcp"
    )


def test_shared_environment_rejects_http_override(monkeypatch) -> None:
    monkeypatch.setenv("MCP_API_GATEWAY_BASE_URL", "http://unsafe.example.invalid")
    with pytest.raises(ConfigurationError):
        load_settings("dev", CONFIG_DIR)
