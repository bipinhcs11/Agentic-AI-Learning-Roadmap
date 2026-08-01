"""Validated, versioned registry snapshot loaded out of the runtime request path."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from enterprise_mcp.shared.errors import ConfigurationError, PolicyDeniedError


@dataclass(frozen=True)
class RegisteredTool:
    server_id: str
    server_version: str
    name: str
    timeout_ms: int
    max_response_bytes: int
    input_schema: dict[str, Any]


class RegistrySnapshot:
    def __init__(self, tools: dict[tuple[str, str], RegisteredTool], digest: str) -> None:
        self._tools = tools
        self.digest = digest

    @classmethod
    def load(cls, registry_dir: Path, schema_path: Path) -> RegistrySnapshot:
        if not registry_dir.is_dir():
            raise ConfigurationError(f"Registry directory not found: {registry_dir}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        manifests: list[dict[str, Any]] = []
        tools: dict[tuple[str, str], RegisteredTool] = {}

        for path in sorted(registry_dir.glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.path))
            if errors:
                raise ConfigurationError(f"Registry manifest failed validation: {path.name}")
            lifecycle = manifest["lifecycle"]
            if lifecycle["status"] != "sandbox" or lifecycle["approvalStatus"] != "approved":
                continue
            if date.fromisoformat(lifecycle["expiresOn"]) < date.today():
                raise ConfigurationError(f"Registry manifest is expired: {path.name}")
            manifests.append(manifest)
            for tool in manifest["tools"]:
                key = (manifest["serverId"], tool["name"])
                if key in tools:
                    raise ConfigurationError(f"Duplicate registered tool: {key}")
                tools[key] = RegisteredTool(
                    server_id=manifest["serverId"],
                    server_version=manifest["version"],
                    name=tool["name"],
                    timeout_ms=tool["timeoutMs"],
                    max_response_bytes=tool["maxResponseBytes"],
                    input_schema=tool["inputSchema"],
                )

        if not manifests:
            raise ConfigurationError("Registry snapshot contains no approved manifests")
        canonical = json.dumps(manifests, separators=(",", ":"), sort_keys=True).encode()
        return cls(tools, f"sha256:{hashlib.sha256(canonical).hexdigest()}")

    def require(self, server_id: str, tool_name: str) -> RegisteredTool:
        tool = self._tools.get((server_id, tool_name))
        if tool is None:
            raise PolicyDeniedError(f"Tool is not approved: {server_id}/{tool_name}")
        return tool

    def catalog(self) -> list[RegisteredTool]:
        return sorted(self._tools.values(), key=lambda tool: (tool.server_id, tool.name))
