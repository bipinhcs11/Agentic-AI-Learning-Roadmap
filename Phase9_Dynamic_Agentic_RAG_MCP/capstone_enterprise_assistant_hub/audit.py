"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | audit.py                                              ║
║  Structured JSONL request audit log.                                        ║
║                                                                              ║
║  WHY: enterprise assistant behavior needs a plain trail of tenant, route,   ║
║  tools, documents, provider, and token counts before adding observability.  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_AUDIT_PATH = HERE / "audit_log.jsonl"


def audit_path() -> Path:
    return Path(os.getenv("HUB_AUDIT_PATH", str(DEFAULT_AUDIT_PATH))).resolve()


def append_audit_record(
    *,
    tenant_id: str,
    question: str,
    route: str,
    tools_used: list[str],
    documents_used: list[str],
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "question": question,
        "route": route,
        "tools_used": tools_used,
        "documents_used": documents_used,
        "provider": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    if extra:
        record.update(extra)

    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record
