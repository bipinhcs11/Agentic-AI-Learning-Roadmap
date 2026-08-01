"""OAuth 2.0 client-credentials token acquisition with optional bounded caching."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .config import OAuthConfig, ScenarioConfig
from .errors import TokenAcquisitionError
from .secrets import SecretProvider


class _TokenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str = Field(min_length=20)
    token_type: str
    expires_in: int = Field(gt=0, le=86_400)


@dataclass(frozen=True)
class AccessToken:
    value: str
    expires_at: float


class ClientCredentialsTokenProvider:
    """Make the first call: exchange a Vault-sourced credential for a short-lived JWT."""

    def __init__(
        self,
        oauth: OAuthConfig,
        scenario: ScenarioConfig,
        secrets: SecretProvider,
        http_client: httpx.AsyncClient,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._oauth = oauth
        self._scenario = scenario
        self._secrets = secrets
        self._http = http_client
        self._clock = clock
        self._cached: AccessToken | None = None
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if not self._oauth.reuse_access_tokens:
            return await self._acquire_token()

        now = self._clock()
        if self._cached and self._cached.expires_at > now:
            return self._cached.value

        async with self._lock:
            now = self._clock()
            if self._cached and self._cached.expires_at > now:
                return self._cached.value

            token = await self._acquire_token_response()

            usable_seconds = max(1, token.expires_in - self._oauth.cache_skew_seconds)
            self._cached = AccessToken(token.access_token, now + usable_seconds)
            return token.access_token

    async def _acquire_token(self) -> str:
        return (await self._acquire_token_response()).access_token

    async def _acquire_token_response(self) -> _TokenResponse:
        credential = await asyncio.to_thread(
            self._secrets.get_api_credential,
            self._scenario,
        )
        try:
            response = await self._http.post(
                self._oauth.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": credential.client_id,
                    "client_secret": credential.client_secret.get_secret_value(),
                    "scope": self._scenario.scope,
                    "audience": self._oauth.audience,
                },
                headers={"Accept": "application/json"},
                timeout=self._oauth.request_timeout_seconds,
                follow_redirects=False,
            )
            response.raise_for_status()
            token = _TokenResponse.model_validate(response.json())
            if token.token_type.lower() != "bearer":
                raise TokenAcquisitionError("Token endpoint returned an unsupported token type")
            return token
        except TokenAcquisitionError:
            raise
        except Exception as exc:
            raise TokenAcquisitionError("Unable to acquire downstream API token") from exc
