"""Narrow authorization policy for the fictional diagnostic POC."""

from __future__ import annotations

from datetime import UTC, datetime

from enterprise_mcp.shared.config import Settings
from enterprise_mcp.shared.errors import PolicyDeniedError
from enterprise_mcp.shared.observability import (
    AuditEvent,
    AuditSink,
    JsonLogAuditSink,
    subject_reference,
)
from enterprise_mcp.shared.security import Principal, current_principal, current_trace

from .registry import RegisteredTool, RegistrySnapshot


class GatewayPolicy:
    def __init__(
        self,
        settings: Settings,
        registry: RegistrySnapshot,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._audit = audit_sink or JsonLogAuditSink()

    def authorize(
        self,
        *,
        server_id: str,
        tool_name: str,
        resource_name: str,
        resource_value: str,
    ) -> RegisteredTool:
        principal = current_principal()
        registered: RegisteredTool | None = None
        try:
            registered = self._registry.require(server_id, tool_name, principal.client_id)
            roles = principal.claims.get("roles", [])
            if isinstance(roles, str):
                roles = [roles]
            if self._settings.gateway.required_role not in roles:
                raise PolicyDeniedError("Required diagnostic role is missing")
            allowed = self._settings.gateway.resource_allowlists.get(resource_name, [])
            if resource_value not in allowed:
                raise PolicyDeniedError("Resource is outside the approved fictional scope")
        except PolicyDeniedError:
            self._emit(
                principal=principal,
                server=registered,
                tool_name=tool_name,
                resource_value=resource_value,
                decision="DENY",
                outcome="REJECTED",
                reason_code="POLICY_DENIED",
            )
            raise

        self._emit(
            principal=principal,
            server=registered,
            tool_name=tool_name,
            resource_value=resource_value,
            decision="ALLOW",
            outcome="AUTHORIZED",
            reason_code="POLICY_MATCH",
        )
        return registered

    def _emit(
        self,
        *,
        principal: Principal,
        server: RegisteredTool | None,
        tool_name: str,
        resource_value: str,
        decision: str,
        outcome: str,
        reason_code: str,
    ) -> None:
        trace = current_trace()
        self._audit.emit(
            AuditEvent(
                trace_id=trace.trace_id,
                service="enterprise-mcp-gateway",
                operation="tools.call.authorize",
                downstream_service=server.server_id if server else "policy",
                decision=decision,
                outcome=outcome,
                duration_ms=0,
                timestamp=datetime.now(UTC).isoformat(),
                subject_ref=subject_reference(principal.subject),
                client_id=principal.client_id,
                server_id=server.server_id if server else None,
                server_version=server.server_version if server else None,
                tool=tool_name,
                resource_ref=subject_reference(resource_value),
                registry_digest=self._registry.digest,
                reason_code=reason_code,
            )
        )
