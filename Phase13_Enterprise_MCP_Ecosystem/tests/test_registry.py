from pathlib import Path

import pytest

from enterprise_mcp.gateway.registry import RegistrySnapshot
from enterprise_mcp.shared.errors import PolicyDeniedError

ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_all_approved_scenario_tools() -> None:
    snapshot = RegistrySnapshot.load(
        ROOT / "registry" / "manifests",
        ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
    )

    assert len(snapshot.catalog()) == 5
    assert snapshot.digest.startswith("sha256:")
    assert snapshot.require("devassist.work-item-analysis", "work_item_analyze").timeout_ms == 5000


def test_registry_denies_unknown_tool() -> None:
    snapshot = RegistrySnapshot.load(
        ROOT / "registry" / "manifests",
        ROOT / "contracts" / "enterprise-mcp-manifest.schema.json",
    )
    with pytest.raises(PolicyDeniedError):
        snapshot.require("devassist.work-item-analysis", "delete_work_item")
