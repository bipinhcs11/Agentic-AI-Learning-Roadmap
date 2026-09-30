"""Secret providers with AWS-IAM-authenticated HashiCorp Vault support."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, SecretStr

from .config import ScenarioConfig, VaultConfig
from .errors import SecretRetrievalError


class ApiCredential(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str
    client_secret: SecretStr


class SecretProvider(Protocol):
    def get_api_credential(self, scenario: ScenarioConfig) -> ApiCredential: ...


class EnvironmentSecretProvider:
    """Local/test provider. Shared environments must use Vault."""

    def get_api_credential(self, scenario: ScenarioConfig) -> ApiCredential:
        client_id = os.getenv(f"{scenario.credential_env_prefix}_CLIENT_ID")
        client_secret = os.getenv(f"{scenario.credential_env_prefix}_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise SecretRetrievalError(
                f"Missing local credential environment variables for {scenario.display_name}"
            )
        return ApiCredential(client_id=client_id, client_secret=SecretStr(client_secret))


@dataclass
class _CachedCredential:
    value: ApiCredential
    expires_at: float


class AwsIamVaultSecretProvider:
    """Authenticate to Vault using AWS IAM and read an API credential from KV v2."""

    def __init__(
        self,
        config: VaultConfig,
        *,
        vault_client_factory: Callable[..., Any] | None = None,
        aws_session_factory: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._vault_client_factory = vault_client_factory
        self._aws_session_factory = aws_session_factory
        self._clock = clock
        self._cache: dict[str, _CachedCredential] = {}

    def _factories(self) -> tuple[Callable[..., Any], Callable[..., Any]]:
        if self._vault_client_factory and self._aws_session_factory:
            return self._vault_client_factory, self._aws_session_factory
        try:
            import boto3
            import hvac
        except ImportError as exc:  # pragma: no cover - dependency installation problem
            raise SecretRetrievalError("Vault/AWS dependencies are not installed") from exc
        return self._vault_client_factory or hvac.Client, self._aws_session_factory or boto3.Session

    def get_api_credential(self, scenario: ScenarioConfig) -> ApiCredential:
        now = self._clock()
        cached = self._cache.get(scenario.secret_path)
        if cached and cached.expires_at > now:
            return cached.value

        vault_factory, session_factory = self._factories()
        try:
            session = session_factory(region_name=self._config.aws_region)
            credentials = session.get_credentials()
            if credentials is None:
                raise SecretRetrievalError("AWS workload credentials are unavailable")
            frozen = credentials.get_frozen_credentials()

            client = vault_factory(
                url=self._config.address,
                namespace=self._config.namespace,
                verify=self._config.verify_tls,
            )
            client.auth.aws.iam_login(
                frozen.access_key,
                frozen.secret_key,
                frozen.token,
                header_value=self._config.iam_server_id_header,
                role=self._config.aws_role,
                use_token=True,
                region=self._config.aws_region,
                mount_point=self._config.auth_mount,
            )
            response = client.secrets.kv.v2.read_secret_version(
                path=scenario.secret_path,
                mount_point=self._config.kv_mount,
            )
            secret = response["data"]["data"]
            value = ApiCredential.model_validate(
                {"client_id": secret["client_id"], "client_secret": secret["client_secret"]}
            )
        except SecretRetrievalError:
            raise
        except Exception as exc:
            raise SecretRetrievalError(
                f"Unable to retrieve API credential for {scenario.display_name}"
            ) from exc

        self._cache[scenario.secret_path] = _CachedCredential(
            value=value,
            expires_at=now + self._config.cache_ttl_seconds,
        )
        return value
