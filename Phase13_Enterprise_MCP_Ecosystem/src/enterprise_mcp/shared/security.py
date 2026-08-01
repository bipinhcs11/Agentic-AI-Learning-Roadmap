"""JWT validation at the gateway and one-call assertions for MCP servers."""

from __future__ import annotations

import os
import secrets
import time
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

import jwt
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import GatewayConfig, JwtConfig
from .errors import ConfigurationError
from .observability import TraceContext


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

    def __init__(self, app: ASGIApp, verifier: InboundJwtVerifier) -> None:
        self.app = app
        self._verifier = verifier

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in {"/health", "/ready"}:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        encoded = _bearer(headers)
        if encoded is None:
            await JSONResponse({"error": "AUTHENTICATION_REQUIRED"}, status_code=401)(
                scope, receive, send
            )
            return
        try:
            principal = self._verifier.verify(encoded)
        except Exception:
            await JSONResponse({"error": "INVALID_ACCESS_TOKEN"}, status_code=401)(
                scope, receive, send
            )
            return

        principal_token: Token[Principal | None] = _principal.set(principal)
        trace_token: Token[TraceContext | None] = _trace.set(
            TraceContext.from_traceparent(headers.get("traceparent"))
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _principal.reset(principal_token)
            _trace.reset(trace_token)


class InternalAssertionIssuer:
    def __init__(self, gateway: GatewayConfig) -> None:
        self._gateway = gateway

    def issue(self, *, scenario: str, tool: str, principal: Principal, trace: TraceContext) -> str:
        secret = os.getenv(self._gateway.internal_assertion_secret_env)
        if not secret:
            raise ConfigurationError(
                f"Missing internal assertion key: {self._gateway.internal_assertion_secret_env}"
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

    def __init__(self, app: ASGIApp, gateway: GatewayConfig, scenario: str) -> None:
        self.app = app
        self._gateway = gateway
        self._scenario = scenario

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in {"/health", "/ready"}:
            await self.app(scope, receive, send)
            return
        encoded = _bearer(Headers(scope=scope))
        secret = os.getenv(self._gateway.internal_assertion_secret_env)
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
