"""Fixed-destination API-gateway client using a short-lived JWT."""

from __future__ import annotations

import time
from typing import Any

import httpx

from .config import ApiGatewayConfig
from .errors import UpstreamApiError
from .oauth import ClientCredentialsTokenProvider
from .observability import AuditSink, TraceContext, completed_event


class GatewayApiClient:
    """Make the second call: invoke one fixed read operation through the API gateway."""

    def __init__(
        self,
        *,
        service_name: str,
        downstream_service: str,
        config: ApiGatewayConfig,
        token_provider: ClientCredentialsTokenProvider,
        http_client: httpx.AsyncClient,
        audit_sink: AuditSink,
    ) -> None:
        self._service_name = service_name
        self._downstream_service = downstream_service
        self._config = config
        self._tokens = token_provider
        self._http = http_client
        self._audit = audit_sink

    @staticmethod
    def _validate_path(path: str) -> None:
        if not path.startswith("/") or "://" in path or ".." in path or "\\" in path:
            raise UpstreamApiError("Operation path is not an approved relative API path")

    async def get_json(
        self,
        *,
        operation: str,
        path: str,
        trace: TraceContext,
        query: dict[str, str | int] | None = None,
    ) -> Any:
        self._validate_path(path)
        started_at = time.monotonic()
        outcome = "ERROR"
        try:
            token = await self._tokens.get_token()
            response = await self._http.get(
                f"{self._config.base_url.rstrip('/')}{path}",
                params=query,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                    "traceparent": trace.traceparent,
                    "x-operation-id": operation,
                },
                timeout=self._config.request_timeout_seconds,
                follow_redirects=False,
            )
            response.raise_for_status()
            if len(response.content) > self._config.max_response_bytes:
                raise UpstreamApiError("Downstream API response exceeded the configured limit")
            outcome = "SUCCESS"
            return response.json()
        except UpstreamApiError:
            raise
        except Exception as exc:
            raise UpstreamApiError(
                f"Downstream operation failed: {self._downstream_service}/{operation}"
            ) from exc
        finally:
            self._audit.emit(
                completed_event(
                    trace=trace,
                    service=self._service_name,
                    operation=operation,
                    downstream_service=self._downstream_service,
                    decision="ALLOW",
                    outcome=outcome,
                    started_at=started_at,
                )
            )
