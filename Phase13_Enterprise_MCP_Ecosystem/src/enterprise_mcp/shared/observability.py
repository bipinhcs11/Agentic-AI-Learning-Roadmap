"""Metadata-only W3C trace context and audit events."""

from __future__ import annotations

import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol


def _hex(bytes_count: int) -> str:
    return secrets.token_hex(bytes_count)


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    trace_flags: str = "01"

    @classmethod
    def new(cls) -> TraceContext:
        return cls(trace_id=_hex(16), span_id=_hex(8))

    @classmethod
    def from_traceparent(cls, value: str | None) -> TraceContext:
        if value:
            parts = value.split("-")
            if (
                len(parts) == 4
                and parts[0] == "00"
                and len(parts[1]) == 32
                and len(parts[2]) == 16
                and len(parts[3]) == 2
                and all(c in "0123456789abcdef" for c in "".join(parts[1:]))
            ):
                return cls(trace_id=parts[1], span_id=_hex(8), trace_flags=parts[3])
        return cls.new()

    @classmethod
    def from_trace_id(cls, trace_id: str) -> TraceContext:
        normalized = trace_id.lower()
        if len(normalized) != 32 or any(c not in "0123456789abcdef" for c in normalized):
            return cls.new()
        return cls(trace_id=normalized, span_id=_hex(8))

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags}"


@dataclass(frozen=True)
class AuditEvent:
    trace_id: str
    service: str
    operation: str
    downstream_service: str
    decision: str
    outcome: str
    duration_ms: int
    timestamp: str


class AuditSink(Protocol):
    def emit(self, event: AuditEvent) -> None: ...


class JsonLogAuditSink:
    """Log only allowlisted metadata; never payloads, bearer tokens, or secrets."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("enterprise_mcp.audit")

    def emit(self, event: AuditEvent) -> None:
        self._logger.info(json.dumps(asdict(event), separators=(",", ":"), sort_keys=True))


class NullAuditSink:
    def emit(self, event: AuditEvent) -> None:
        return None


def completed_event(
    *,
    trace: TraceContext,
    service: str,
    operation: str,
    downstream_service: str,
    decision: str,
    outcome: str,
    started_at: float,
) -> AuditEvent:
    return AuditEvent(
        trace_id=trace.trace_id,
        service=service,
        operation=operation,
        downstream_service=downstream_service,
        decision=decision,
        outcome=outcome,
        duration_ms=max(0, int((time.monotonic() - started_at) * 1000)),
        timestamp=datetime.now(UTC).isoformat(),
    )
