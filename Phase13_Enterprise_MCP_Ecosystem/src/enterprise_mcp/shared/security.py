"""JWT validation at the gateway and one-call assertions for MCP servers."""

from __future__ import annotations

import os
import secrets
import time
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import jwt
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import GatewayConfig, JwtConfig, ScenarioConfig, Settings
from .errors import ConfigurationError
from .observability import AuditEvent, AuditSink, JsonLogAuditSink, TraceContext


@dataclass(frozen=True)
class Principal:
    subject: str
    client_id: str
    claims: dict[str, Any]


_principal: ContextVar[Principal | None] = ContextVar("mcp_principal", default=None)
_trace: ContextVar[TraceContext | None] = ContextVar("mcp_trace", default=None)


def current_principal() -> Principal:
    value = _principal.get()
    if value is None:
        raise RuntimeError("Authenticated principal is unavailable")
    return value


def current_trace() -> TraceContext:
    return _trace.get() or TraceContext.new()


def _bearer(headers: Headers) -> str | None:
    value = headers.get("authorization")
    if not value or not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    return token or None


class InboundJwtVerifier:
    def __init__(self, config: JwtConfig, approved_clients: list[str]) -> None:
        self._config = config
        self._approved_clients = set(approved_clients)
        self._jwk_client = jwt.PyJWKClient(config.jwks_url) if config.jwks_url else None

    def verify(self, encoded: str) -> Principal:
        try:
            if self._config.algorithm == "HS256":
                key = os.getenv(self._config.local_secret_env)
                if not key:
                    raise ConfigurationError(
                        f"Missing local JWT key: {self._config.local_secret_env}"
                    )
            else:
                if self._jwk_client is None:
                    raise ConfigurationError("RS256 requires a JWKS URL")
                key = self._jwk_client.get_signing_key_from_jwt(encoded).key

            claims = jwt.decode(
                encoded,
                key,
                algorithms=[self._config.algorithm],
                audience=self._config.audience,
                issuer=self._config.issuer,
                options={"require": ["exp", "iat", "iss", "aud", "sub", "client_id"]},
            )
            client_id = str(claims["client_id"])
            if client_id not in self._approved_clients:
                raise jwt.InvalidTokenError("client is not approved")
            return Principal(subject=str(claims["sub"]), client_id=client_id, claims=claims)
        except ConfigurationError:
            raise
        except Exception as exc:
            raise jwt.InvalidTokenError("access token validation failed") from exc


class GatewayJwtMiddleware:
    """Validate the IDE/user JWT and place only sanitized claims in request context."""

    def __init__(
        self,
        app: ASGIApp,
        verifier: InboundJwtVerifier,
        public_url: str,
        registry_digest: str,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.app = app
        self._verifier = verifier
        self._public_url = public_url.rstrip("/")
        self._registry_digest = registry_digest
        self._audit = audit_sink or JsonLogAuditSink()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        public_paths = {"/health", "/ready", "/.well-known/oauth-protected-resource"}
        if scope["type"] != "http" or scope.get("path") in public_paths:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        trace = TraceContext.from_traceparent(headers.get("traceparent"))
        encoded = _bearer(headers)
        if encoded is None:
            await self._deny(scope, receive, send, trace, "AUTHENTICATION_REQUIRED")
            return
        try:
            principal = self._verifier.verify(encoded)
        except Exception:
            await self._deny(scope, receive, send, trace, "INVALID_ACCESS_TOKEN")
            return

        principal_token: Token[Principal | None] = _principal.set(principal)
        trace_token: Token[TraceContext | None] = _trace.set(trace)
        try:
            await self.app(scope, receive, send)
        finally:
            _principal.reset(principal_token)
            _trace.reset(trace_token)

    async def _deny(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        trace: TraceContext,
        reason_code: str,
    ) -> None:
        self._audit.emit(
            AuditEvent(
                trace_id=trace.trace_id,
                service="enterprise-mcp-gateway",
                operation="authenticate",
                downstream_service="identity",
                decision="DENY",
                outcome="REJECTED",
                duration_ms=0,
                timestamp=datetime.now(UTC).isoformat(),
                registry_digest=self._registry_digest,
                reason_code=reason_code,
            )
        )
        metadata = f"{self._public_url}/.well-known/oauth-protected-resource"
        await JSONResponse(
            {"error": reason_code, "traceId": trace.trace_id},
            status_code=401,
            headers={"WWW-Authenticate": f'Bearer resource_metadata="{metadata}"'},
        )(scope, receive, send)


class InternalAssertionIssuer:
    def __init__(self, settings: Settings) -> None:
        self._gateway = settings.gateway
        self._scenarios = settings.scenarios

    def issue(self, *, scenario: str, tool: str, principal: Principal, trace: TraceContext) -> str:
        scenario_config = self._scenarios[scenario]
        secret = os.getenv(scenario_config.assertion_secret_env)
        if not secret:
            raise ConfigurationError(
                f"Missing internal assertion key: {scenario_config.assertion_secret_env}"
            )
        now = int(time.time())
        return jwt.encode(
            {
                "iss": "enterprise-mcp-gateway",
                "sub": principal.subject,
                "aud": f"{self._gateway.internal_assertion_audience_prefix}:{scenario}",
                "client_id": principal.client_id,
                "scenario": scenario,
                "tool": tool,
                "trace_id": trace.trace_id,
                "iat": now,
                "exp": now + self._gateway.internal_assertion_ttl_seconds,
                "jti": secrets.token_urlsafe(16),
            },
            secret,
            algorithm="HS256",
        )


class InternalAssertionMiddleware:
    """Reject direct IDE access to a scenario server; only gateway assertions pass."""

    def __init__(
        self,
        app: ASGIApp,
        gateway: GatewayConfig,
        scenario: str,
        scenario_config: ScenarioConfig,
        expected_tool: str,
    ) -> None:
        self.app = app
        self._gateway = gateway
        self._scenario = scenario
        self._scenario_config = scenario_config
        self._expected_tool = expected_tool

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in {"/health", "/ready"}:
            await self.app(scope, receive, send)
            return
        encoded = _bearer(Headers(scope=scope))
        secret = os.getenv(self._scenario_config.assertion_secret_env)
        if not encoded or not secret:
            await JSONResponse({"error": "GATEWAY_ASSERTION_REQUIRED"}, status_code=401)(
                scope, receive, send
            )
            return
        try:
            claims = jwt.decode(
                encoded,
                secret,
                algorithms=["HS256"],
                audience=f"{self._gateway.internal_assertion_audience_prefix}:{self._scenario}",
                issuer="enterprise-mcp-gateway",
                options={"require": ["exp", "iat", "jti", "scenario", "tool", "trace_id"]},
            )
            if claims["scenario"] != self._scenario or claims["tool"] != self._expected_tool:
                raise jwt.InvalidTokenError("Assertion is not bound to this tool")
        except Exception:
            await JSONResponse({"error": "INVALID_GATEWAY_ASSERTION"}, status_code=401)(
                scope, receive, send
            )
            return
        principal_token: Token[Principal | None] = _principal.set(
            Principal(
                subject=str(claims["sub"]),
                client_id=str(claims["client_id"]),
                claims=claims,
            )
        )
        trace_token: Token[TraceContext | None] = _trace.set(
            TraceContext.from_trace_id(str(claims["trace_id"]))
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _principal.reset(principal_token)
            _trace.reset(trace_token)
