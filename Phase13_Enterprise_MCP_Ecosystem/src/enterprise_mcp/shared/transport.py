"""Explicit DNS-rebinding protection for every Streamable HTTP endpoint."""

from __future__ import annotations

from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


def transport_security_for_url(url: str) -> TransportSecuritySettings:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("MCP public URL must be an absolute HTTP(S) URL")
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[parsed.netloc],
        allowed_origins=[f"{parsed.scheme}://{parsed.netloc}"],
    )


def governed_fast_mcp(
    name: str,
    *,
    bind_host: str,
    port: int,
    public_url: str,
) -> FastMCP:
    return FastMCP(
        name,
        host=bind_host,
        port=port,
        stateless_http=True,
        json_response=True,
        transport_security=transport_security_for_url(public_url),
    )
