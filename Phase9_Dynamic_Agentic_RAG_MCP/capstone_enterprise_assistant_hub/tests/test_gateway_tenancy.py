from __future__ import annotations

import json

import pytest

from mcp_gateway import MCPGateway, ToolPermissionError


def test_disallowed_tool_is_blocked():
    gateway = MCPGateway(external_enabled=False)

    with pytest.raises(ToolPermissionError):
        gateway.call_tool("globex", "get_primary_contribution_summary")


def test_tenant_a_cannot_retrieve_tenant_b_document():
    gateway = MCPGateway(external_enabled=False)

    acme_results = gateway.call_tool("acme", "search_tenant_docs", query="Globex blue-folder policy", k=3)
    globex_results = gateway.call_tool("globex", "search_tenant_docs", query="Globex blue-folder policy", k=3)

    assert "Globex blue-folder policy" not in json.dumps(acme_results)
    assert "Globex blue-folder policy" in json.dumps(globex_results)


def test_document_excerpt_rechecks_tenant_corpus():
    gateway = MCPGateway(external_enabled=False)

    with pytest.raises(PermissionError):
        gateway.call_tool("acme", "get_document_excerpt", document_id="benefits_reference.md")

    excerpt = gateway.call_tool("globex", "get_document_excerpt", document_id="benefits_reference.md")
    assert "Globex" in excerpt["excerpt"]
