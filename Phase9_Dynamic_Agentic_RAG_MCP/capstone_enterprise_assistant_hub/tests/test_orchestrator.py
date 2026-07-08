from __future__ import annotations

import json

import orchestrator
from mcp_gateway import MCPGateway
from providers import Completion


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def complete(self, messages, *, temperature=0.2, max_tokens=800):
        return Completion(
            text="fake answer",
            input_tokens=11,
            output_tokens=3,
            model=self.model,
        )

    def stream(self, messages, *, temperature=0.2, max_tokens=800):
        yield "fake answer"


def test_route_logic_examples(monkeypatch):
    monkeypatch.setenv("HUB_ROUTER_MODE", "heuristic")

    assert orchestrator.classify_route("hello there").route == "direct"
    assert orchestrator.classify_route("Am I getting my full primary contribution match?").route == "mcp_only"
    assert orchestrator.classify_route("What is the 2026 savings account family limit?").route == "rag_only"
    assert orchestrator.classify_route("I contribute 6%. Am I maxing the match, and what is the 2026 primary_contribution limit?").route == "mcp+rag"


def test_run_orchestrated_mcp_and_rag_with_stub_provider(monkeypatch):
    monkeypatch.setenv("HUB_ROUTER_MODE", "heuristic")
    monkeypatch.setattr(orchestrator, "get_provider", lambda: FakeProvider())
    gateway = MCPGateway(external_enabled=False)

    result = orchestrator.run_orchestrated(
        question="I contribute 6%. Am I maxing the match, and what is the 2026 primary_contribution employee limit?",
        tenant_id="acme",
        gateway=gateway,
        write_audit=False,
    )

    assert result.route == "mcp+rag"
    assert "calculate_primary_contribution_match" in result.tools_used
    assert "primary_contribution_reference.md" in result.documents_used
    assert result.provider == "fake"


def test_mcp_error_falls_back_to_tenant_rag(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_provider", lambda: FakeProvider())

    class BrokenGateway(MCPGateway):
        def call_tool(self, tenant_id: str, tool_name: str, **kwargs):
            raise RuntimeError("mcp down")

    result = orchestrator.run_orchestrated(
        question="Am I getting my full primary contribution match?",
        tenant_id="acme",
        gateway=BrokenGateway(external_enabled=False),
        classifier=lambda _: orchestrator.RouteDecision("mcp_only", "forced"),
        write_audit=False,
    )

    assert result.route == "rag_only"
    assert result.tools_used == []
    assert result.documents_used


def test_audit_jsonl_written(monkeypatch, tmp_path):
    monkeypatch.setenv("HUB_ROUTER_MODE", "heuristic")
    monkeypatch.setenv("HUB_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setattr(orchestrator, "get_provider", lambda: FakeProvider())

    orchestrator.run_orchestrated(
        question="What is the 2026 savings account family limit?",
        tenant_id="acme",
        gateway=MCPGateway(external_enabled=False),
    )

    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[-1])
    assert record["tenant_id"] == "acme"
    assert record["route"] == "rag_only"
    assert record["provider"] == "fake"
    assert record["documents_used"]
