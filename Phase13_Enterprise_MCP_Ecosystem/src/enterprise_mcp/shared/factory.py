"""Construct a scenario-specific API client without sharing credentials across servers."""

from __future__ import annotations

import httpx

from .api_client import GatewayApiClient
from .config import Settings
from .oauth import ClientCredentialsTokenProvider
from .observability import AuditSink, JsonLogAuditSink
from .secrets import AwsIamVaultSecretProvider, EnvironmentSecretProvider, SecretProvider


def build_secret_provider(settings: Settings) -> SecretProvider:
    if settings.secret_provider == "vault":  # noqa: S105 - provider type, not secret
        return AwsIamVaultSecretProvider(settings.vault)
    return EnvironmentSecretProvider()


def build_api_client(
    scenario_name: str,
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
    secret_provider: SecretProvider | None = None,
    audit_sink: AuditSink | None = None,
) -> GatewayApiClient:
    scenario = settings.scenarios[scenario_name]
    client = http_client or httpx.AsyncClient(verify=settings.api_gateway.verify_tls)
    secrets = secret_provider or build_secret_provider(settings)
    tokens = ClientCredentialsTokenProvider(settings.oauth, scenario, secrets, client)
    return GatewayApiClient(
        service_name=scenario_name,
        downstream_service="internal-api-gateway",
        config=settings.api_gateway,
        token_provider=tokens,
        http_client=client,
        audit_sink=audit_sink or JsonLogAuditSink(),
    )
