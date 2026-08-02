import json
from pathlib import Path

import pytest

from enterprise_mcp.gateway.registry import RegistrySnapshot
from enterprise_mcp.shared.errors import ConfigurationError, PolicyDeniedError

ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_only_the_two_approved_poc_tools() -> None:
    snapshot = RegistrySnapshot.load(
        ROOT / "registry" / "manifests",
        ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
    )

    assert len(snapshot.catalog()) == 2
    assert snapshot.digest.startswith("sha256:")
    assert snapshot.require("devassist.work-item-analysis", "work_item_analyze").timeout_ms == 5000


def test_registry_denies_unknown_tool() -> None:
    snapshot = RegistrySnapshot.load(
        ROOT / "registry" / "manifests",
        ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
    )
    with pytest.raises(PolicyDeniedError):
        snapshot.require("devassist.work-item-analysis", "delete_work_item")


def test_registry_enforces_manifest_client_scope() -> None:
    snapshot = RegistrySnapshot.load(
        ROOT / "registry" / "manifests",
        ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
    )
    with pytest.raises(PolicyDeniedError, match="Client is not approved"):
        snapshot.require(
            "devassist.work-item-analysis",
            "work_item_analyze",
            "unapproved-client",
        )


def test_expired_manifest_fails_snapshot_load(tmp_path) -> None:
    source = ROOT / "registry" / "manifests" / "work-item-analysis.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    manifest["lifecycle"]["expiresOn"] = "2020-01-01"
    (tmp_path / source.name).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="expired"):
        RegistrySnapshot.load(
            tmp_path,
            ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
        )
