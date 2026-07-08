from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np


def load_module02_server(monkeypatch):
    class FakeMCP:
        def __init__(self, *_args, **_kwargs):
            pass

        def tool(self):
            return lambda func: func

        def run(self, *_args, **_kwargs):
            return None

    fake_fastmcp = types.ModuleType("mcp.server.fastmcp")
    fake_fastmcp.FastMCP = FakeMCP
    fake_server = types.ModuleType("mcp.server")
    fake_server.fastmcp = fake_fastmcp
    fake_mcp = types.ModuleType("mcp")
    fake_mcp.server = fake_server
    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = lambda *_args, **_kwargs: object()

    monkeypatch.setitem(sys.modules, "mcp", fake_mcp)
    monkeypatch.setitem(sys.modules, "mcp.server", fake_server)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_fastmcp)
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    path = Path(__file__).resolve().parents[2] / "module_02_mcp_rag_enterprise_integration" / "benefits_mcp_server.py"
    spec = importlib.util.spec_from_file_location("module02_benefits_for_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_employee_limit_intent_ranks_employee_limit_above_combined(monkeypatch):
    module = load_module02_server(monkeypatch)
    chunks = np.array(
        [
            "[primary contribution Reference — Combined employee + employer limit]\nThe combined limit is $72,000.",
            "[primary contribution Reference — Employee contribution limits]\nThe employee salary-deferral limit is $24,500.",
        ],
        dtype=object,
    )
    sources = np.array(["primary_contribution_reference.md", "primary_contribution_reference.md"], dtype=object)
    sims = np.array([0.90, 0.70], dtype=np.float32)

    order = module._rank("What is the 2026 primary contribution employee contribution limit?", sims, chunks, sources)

    assert order[0] == 1
