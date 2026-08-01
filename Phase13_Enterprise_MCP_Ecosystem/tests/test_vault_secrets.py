from pathlib import Path

from enterprise_mcp.shared.config import load_settings
from enterprise_mcp.shared.secrets import AwsIamVaultSecretProvider

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


class FakeFrozenCredentials:
    access_key = "fictional-access-key"
    secret_key = "fictional-secret-key"
    token = "fictional-session-token"


class FakeCredentials:
    def get_frozen_credentials(self) -> FakeFrozenCredentials:
        return FakeFrozenCredentials()


class FakeSession:
    def get_credentials(self) -> FakeCredentials:
        return FakeCredentials()


class FakeAwsAuth:
    def __init__(self) -> None:
        self.calls = []

    def iam_login(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


class FakeKvV2:
    def __init__(self) -> None:
        self.calls = []

    def read_secret_version(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "data": {
                "data": {
                    "client_id": "vault-client",
                    "client_secret": "vault-secret-canary",
                }
            }
        }


class FakeVaultClient:
    def __init__(self) -> None:
        self.auth = type("Auth", (), {"aws": FakeAwsAuth()})()
        kv_v2 = FakeKvV2()
        self.secrets = type("Secrets", (), {"kv": type("Kv", (), {"v2": kv_v2})()})()


def test_vault_provider_uses_aws_iam_then_reads_kv_v2() -> None:
    settings = load_settings("dev", CONFIG_DIR)
    fake_client = FakeVaultClient()
    provider = AwsIamVaultSecretProvider(
        settings.vault,
        vault_client_factory=lambda **kwargs: fake_client,
        aws_session_factory=lambda **kwargs: FakeSession(),
        clock=lambda: 100.0,
    )

    scenario = settings.scenarios["work_item_analysis"]
    credential = provider.get_api_credential(scenario)
    cached = provider.get_api_credential(scenario)

    assert credential.client_id == "vault-client"
    assert credential.client_secret.get_secret_value() == "vault-secret-canary"
    assert cached is credential
    assert len(fake_client.auth.aws.calls) == 1
    args, kwargs = fake_client.auth.aws.calls[0]
    assert args[:3] == (
        "fictional-access-key",
        "fictional-secret-key",
        "fictional-session-token",
    )
    assert kwargs["role"] == "enterprise-mcp-dev"
    assert fake_client.secrets.kv.v2.calls == [
        {"path": scenario.secret_path, "mount_point": settings.vault.kv_mount}
    ]
