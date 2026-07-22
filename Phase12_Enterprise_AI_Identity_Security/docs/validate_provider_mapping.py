"""Offline structural check for Phase 12 provider mapping manifests."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED = {
    "platform",
    "principal",
    "delegated_actor",
    "credential_strategy",
    "audience_binding",
    "revocation",
    "audit",
    "no_long_lived_keys",
    "limitations",
    "official_sources",
    "last_verified",
}


def validate(path: Path) -> list[str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    errors = [f"missing field: {name}" for name in sorted(REQUIRED - document.keys())]
    if document.get("no_long_lived_keys") is not True:
        errors.append("no_long_lived_keys must be true for the recommended mapping")
    sources = document.get("official_sources", [])
    if not sources or not all(str(source).startswith("https://") for source in sources):
        errors.append("official_sources must contain HTTPS documentation links")
    if not document.get("limitations"):
        errors.append("limitations must explain non-equivalent or provider-specific behavior")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 validate_provider_mapping.py PATH_TO_MAPPING_JSON")
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
