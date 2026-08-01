"""Validated base configuration plus environment-specific overlays."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import ConfigurationError


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: Literal["local", "test", "dev", "prod"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    service_host: str = "127.0.0.1"


class VaultConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str
    namespace: str | None = None
    verify_tls: bool | str = True
    auth_mount: str = "aws"
    aws_role: str
    aws_region: str = "us-east-1"
    iam_server_id_header: str | None = None
    kv_mount: str = "secret"
    cache_ttl_seconds: int = Field(default=300, ge=0, le=3600)


class OAuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token_url: str
    audience: str
    request_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    reuse_access_tokens: bool = False
    cache_skew_seconds: int = Field(default=30, ge=0, le=300)


class ApiGatewayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_url: str
    request_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    verify_tls: bool | str = True
    max_response_bytes: int = Field(default=262_144, ge=1024, le=1_048_576)


class JwtConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issuer: str
    audience: str
    algorithm: Literal["HS256", "RS256"] = "HS256"
    jwks_url: str | None = None
    local_secret_env: str = "MCP_GATEWAY_JWT_SECRET"  # noqa: S105 - env-var name


class GatewayConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)
    registry_dir: str = "registry/manifests"
    approved_clients: list[str]
    inbound_jwt: JwtConfig
    internal_assertion_audience_prefix: str = "enterprise-mcp"
    internal_assertion_secret_env: str = "MCP_INTERNAL_ASSERTION_SECRET"  # noqa: S105
    internal_assertion_ttl_seconds: int = Field(default=60, ge=10, le=300)


class ScenarioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str
    secret_path: str
    credential_env_prefix: str
    scope: str
    server_url: str
    port: int = Field(ge=1, le=65535)

    @field_validator("credential_env_prefix")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        if not value.startswith("MCP_") or not value.replace("_", "").isalnum():
            raise ValueError("credential_env_prefix must be an MCP_* environment prefix")
        return value


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeConfig
    secret_provider: Literal["environment", "vault"]
    vault: VaultConfig
    oauth: OAuthConfig
    api_gateway: ApiGatewayConfig
    gateway: GatewayConfig
    scenarios: dict[str, ScenarioConfig]


ENVIRONMENT_OVERRIDES: dict[str, tuple[str, ...]] = {
    "MCP_SERVICE_HOST": ("runtime", "service_host"),
    "MCP_VAULT_ADDRESS": ("vault", "address"),
    "MCP_VAULT_NAMESPACE": ("vault", "namespace"),
    "MCP_API_GATEWAY_BASE_URL": ("api_gateway", "base_url"),
    "MCP_TOKEN_URL": ("oauth", "token_url"),
    "MCP_GATEWAY_HOST": ("gateway", "host"),
    "MCP_GATEWAY_ISSUER": ("gateway", "inbound_jwt", "issuer"),
    "MCP_GATEWAY_JWKS_URL": ("gateway", "inbound_jwt", "jwks_url"),
    "MCP_WORK_ITEM_SERVER_URL": ("scenarios", "work_item_analysis", "server_url"),
    "MCP_CONFIG_CHECK_SERVER_URL": ("scenarios", "config_check", "server_url"),
    "MCP_SONAR_SERVER_URL": ("scenarios", "sonar_analysis", "server_url"),
    "MCP_STANDARDS_SERVER_URL": ("scenarios", "coding_standards", "server_url"),
    "MCP_SKILLS_SERVER_URL": ("scenarios", "skills_catalog", "server_url"),
}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"Configuration file not found: {path}")
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path.name}") from exc
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"Configuration root must be an object: {path.name}")
    return loaded


def _set_nested(config: dict[str, Any], path: tuple[str, ...], value: str) -> None:
    current = config
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


def _format_environment(value: Any, environment: str) -> Any:
    if isinstance(value, dict):
        return {key: _format_environment(item, environment) for key, item in value.items()}
    if isinstance(value, list):
        return [_format_environment(item, environment) for item in value]
    if isinstance(value, str):
        return value.replace("{environment}", environment)
    return value


def load_settings(
    environment: str | None = None,
    config_dir: Path | None = None,
) -> Settings:
    """Load base.yaml, overlay the selected environment, then apply safe URL overrides."""

    selected = environment or os.getenv("MCP_ENV", "local")
    if selected not in {"local", "test", "dev", "prod"}:
        raise ConfigurationError(f"Unsupported MCP_ENV: {selected}")

    root = config_dir or Path(__file__).resolve().parents[3] / "config"
    merged = _deep_merge(_read_yaml(root / "base.yaml"), _read_yaml(root / f"{selected}.yaml"))
    merged = _format_environment(merged, selected)
    for env_name, target_path in ENVIRONMENT_OVERRIDES.items():
        if value := os.getenv(env_name):
            _set_nested(merged, target_path, value)
    try:
        return Settings.model_validate(merged)
    except Exception as exc:
        raise ConfigurationError("Configuration validation failed") from exc
