#!/usr/bin/env python3
"""Create a short-lived fictional IDE token for the local demo only."""

from __future__ import annotations

import argparse
import os
import time

import jwt

from enterprise_mcp.shared.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", default="vscode-devassist")
    parser.add_argument("--subject", default="fictional-developer")
    args = parser.parse_args()

    settings = load_settings("local")
    secret = os.getenv(
        settings.gateway.inbound_jwt.local_secret_env,
        "fictional-local-gateway-signing-key-at-least-32-bytes",
    )
    now = int(time.time())
    print(
        jwt.encode(
            {
                "iss": settings.gateway.inbound_jwt.issuer,
                "sub": args.subject,
                "aud": settings.gateway.inbound_jwt.audience,
                "client_id": args.client_id,
                "iat": now,
                "exp": now + 300,
            },
            secret,
            algorithm="HS256",
        )
    )


if __name__ == "__main__":
    main()
