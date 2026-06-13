"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | config.py                                             ║
║  Tenant config loader for tool allowlists, API keys, and document corpora.  ║
║                                                                              ║
║  WHY: Phase 8's JWT tenant model becomes a tiny API-key map here so the      ║
║  learning capstone can prove isolation without rebuilding auth or billing.  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_TENANT_CONFIG = HERE / "config" / "tenants.yaml"
LIST_KEYS = {"api_keys", "allowed_tools", "args"}


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    display_name: str
    api_keys: tuple[str, ...]
    corpus: Path
    allowed_tools: frozenset[str]


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def _simple_yaml(text: str) -> dict:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"List item has no list parent: {raw}")
            parent.append(_parse_scalar(line[2:]))
            continue

        key, _, rest = line.partition(":")
        if not key or not _:
            raise ValueError(f"Unsupported tenants.yaml line: {raw}")
        key = key.strip()
        rest = rest.strip()
        if rest:
            value = _parse_scalar(rest)
        else:
            value = [] if key in LIST_KEYS else {}

        if isinstance(parent, dict):
            parent[key] = value
        else:
            raise ValueError(f"Cannot assign key under non-dict parent: {raw}")
        if isinstance(value, (dict, list)):
            stack.append((indent, value))

    return root


def _load_mapping(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        import yaml

        return yaml.safe_load(text) or {}
    except ImportError:
        return _simple_yaml(text)


def _resolve_path(path: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = path.parent.parent / candidate
    return candidate.resolve()


def load_config(path: Path | str = DEFAULT_TENANT_CONFIG) -> dict:
    return _load_mapping(Path(path))


def load_tenants(path: Path | str = DEFAULT_TENANT_CONFIG) -> dict[str, TenantConfig]:
    config_path = Path(path)
    raw = load_config(config_path)
    tenants = {}
    for tenant_id, entry in (raw.get("tenants") or {}).items():
        tenants[tenant_id] = TenantConfig(
            tenant_id=tenant_id,
            display_name=entry.get("display_name", tenant_id),
            api_keys=tuple(entry.get("api_keys") or ()),
            corpus=_resolve_path(config_path, entry["corpus"]),
            allowed_tools=frozenset(entry.get("allowed_tools") or ()),
        )
    return tenants


def tenant_for_api_key(api_key: str, path: Path | str = DEFAULT_TENANT_CONFIG) -> TenantConfig:
    for tenant in load_tenants(path).values():
        if api_key in tenant.api_keys:
            return tenant
    raise PermissionError("Unknown API key")


def load_mcp_servers(path: Path | str = DEFAULT_TENANT_CONFIG) -> dict:
    config_path = Path(path)
    raw = load_config(config_path)
    servers = raw.get("mcp_servers") or {}
    resolved = {}
    for name, entry in servers.items():
        command = sys.executable if entry.get("command") == "__python__" else entry.get("command")
        args = []
        for arg in entry.get("args") or []:
            if arg.endswith(".py") or arg.startswith("../"):
                args.append(str(_resolve_path(config_path, arg)))
            else:
                args.append(arg)
        resolved[name] = {
            "command": command,
            "args": args,
            "transport": entry.get("transport", "stdio"),
        }
    return resolved


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
