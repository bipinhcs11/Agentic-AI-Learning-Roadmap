"""Local token issuer and API gateway used only for the offline fictional demo."""

from __future__ import annotations

import os
import secrets
import time
from typing import Any
from urllib.parse import parse_qs

import jwt
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from enterprise_mcp.shared.config import load_settings

TOKEN_SECRET = "fictional-mock-api-signing-key-change-me"
TOKEN_ISSUER = "enterprise-mcp-mock-identity"
TOKEN_AUDIENCE = "internal-api-gateway"
USED_TOKEN_IDS: set[str] = set()


def _expected_clients() -> dict[str, str]:
    pairs = {
        "MCP_WORK_ITEM": ("work-item-local", "fictional-work-item-secret"),
        "MCP_CONFIG_CHECK": ("config-check-local", "fictional-config-check-secret"),
        "MCP_SONAR": ("sonar-local", "fictional-sonar-secret"),
        "MCP_STANDARDS": ("standards-local", "fictional-standards-secret"),
        "MCP_SKILLS": ("skills-local", "fictional-skills-secret"),
    }
    return {
        os.getenv(f"{prefix}_CLIENT_ID", defaults[0]): os.getenv(
            f"{prefix}_CLIENT_SECRET", defaults[1]
        )
        for prefix, defaults in pairs.items()
    }


async def token(request: Request) -> JSONResponse:
    form = parse_qs((await request.body()).decode("utf-8"))
    client_id = form.get("client_id", [""])[0]
    client_secret = form.get("client_secret", [""])[0]
    scope = form.get("scope", [""])[0]
    audience = form.get("audience", [""])[0]
    if (
        form.get("grant_type", [""])[0] != "client_credentials"
        or _expected_clients().get(client_id) != client_secret
        or audience != TOKEN_AUDIENCE
    ):
        return JSONResponse({"error": "invalid_client"}, status_code=401)
    now = int(time.time())
    access_token = jwt.encode(
        {
            "iss": TOKEN_ISSUER,
            "sub": client_id,
            "aud": TOKEN_AUDIENCE,
            "scope": scope,
            "jti": secrets.token_urlsafe(16),
            "iat": now,
            "exp": now + 300,
        },
        TOKEN_SECRET,
        algorithm="HS256",
    )
    return JSONResponse({"access_token": access_token, "token_type": "Bearer", "expires_in": 300})


def _authorize(request: Request) -> bool:
    value = request.headers.get("authorization", "")
    if not value.lower().startswith("bearer "):
        return False
    try:
        claims = jwt.decode(
            value[7:],
            TOKEN_SECRET,
            algorithms=["HS256"],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
        )
        token_id = str(claims["jti"])
        if token_id in USED_TOKEN_IDS:
            return False
        USED_TOKEN_IDS.add(token_id)
        return True
    except Exception:
        return False


def _protected(payload: Any, request: Request, status_code: int = 200) -> JSONResponse:
    if not _authorize(request):
        return JSONResponse({"error": "invalid_token"}, status_code=401)
    return JSONResponse(payload, status_code=status_code)


async def work_item(request: Request) -> JSONResponse:
    return _protected(
        {"workItemId": request.path_params["work_item_id"], "participantId": "P-DEMO-001"},
        request,
    )


async def participant(request: Request) -> JSONResponse:
    return _protected(
        {
            "participantRef": request.path_params["participant_id"],
            "status": "ACTIVE",
        },
        request,
    )


async def enrollment(request: Request) -> JSONResponse:
    return _protected({}, request)


async def rate(request: Request) -> JSONResponse:
    return _protected({"planYear": 2026, "rateBand": "FICTIONAL-A"}, request)


async def life_events(request: Request) -> JSONResponse:
    return _protected([{"type": "FICTIONAL_STATUS_CHANGE", "effectiveDate": "2026-05-15"}], request)


async def configuration(request: Request) -> JSONResponse:
    return _protected({"enrollmentPlanConfigured": False, "rateTableConfigured": True}, request)


async def sonar_issues(request: Request) -> JSONResponse:
    return _protected(
        {
            "issues": [
                {
                    "key": "SONAR-FICTION-001",
                    "severity": request.query_params.get("severity", "MAJOR"),
                    "rule": "python:S1481",
                    "message": "Remove the fictional unused local variable.",
                }
            ]
        },
        request,
    )


async def standard(request: Request) -> JSONResponse:
    return _protected(
        {
            "ruleId": request.path_params["rule_id"],
            "version": "1.0.0",
            "summary": "Use bounded timeouts for all internal HTTP calls.",
            "provenance": "fictional-engineering-standards",
        },
        request,
    )


async def skills(request: Request) -> JSONResponse:
    return _protected(
        {
            "skills": [
                {
                    "name": "fictional-domain-review",
                    "version": "1.0.0",
                    "status": "approved",
                    "domain": request.query_params.get("domain", "engineering"),
                }
            ]
        },
        request,
    )


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "fictional-enterprise-api"})


app = Starlette(
    routes=[
        Route("/health", health),
        Route("/oauth2/token", token, methods=["POST"]),
        Route("/work-items/{work_item_id}", work_item),
        Route("/participants/{participant_id}", participant),
        Route("/participants/{participant_id}/enrollment", enrollment),
        Route("/participants/{participant_id}/rate", rate),
        Route("/participants/{participant_id}/life-events", life_events),
        Route("/configurations/participants/{participant_id}", configuration),
        Route("/sonar/projects/{project_key}/issues", sonar_issues),
        Route("/standards/rules/{rule_id}", standard),
        Route("/skills", skills),
    ]
)


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        app,
        host=settings.runtime.service_host,
        port=9000,
        log_level=settings.runtime.log_level.lower(),
    )


if __name__ == "__main__":
    main()
