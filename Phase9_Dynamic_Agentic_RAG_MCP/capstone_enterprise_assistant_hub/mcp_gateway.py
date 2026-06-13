"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | mcp_gateway.py                                        ║
║  Tenant-scoped gateway for MCP tools and hub-owned RAG/account utilities.   ║
║                                                                              ║
║  WHY: the model never receives a raw cross-tenant integration surface. The   ║
║  gateway filters by tenant allowlist first, injects tenant context for hub   ║
║  tools, and only then invokes MCP or local read-only tools.                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .audit import audit_path
    from .config import DEFAULT_TENANT_CONFIG, TenantConfig, env_bool, load_mcp_servers, load_tenants
    from .retrieval import TenantRAG
except ImportError:  # pragma: no cover
    from audit import audit_path
    from config import DEFAULT_TENANT_CONFIG, TenantConfig, env_bool, load_mcp_servers, load_tenants
    from retrieval import TenantRAG


class ToolPermissionError(PermissionError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str


@dataclass
class TenantBoundTool:
    name: str
    description: str
    tenant_id: str
    gateway: "MCPGateway"

    def invoke(self, args: dict | None = None) -> Any:
        return self.gateway.call_tool(self.tenant_id, self.name, **(args or {}))

    async def ainvoke(self, args: dict | None = None) -> Any:
        return self.invoke(args)


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK ACCOUNT FALLBACKS
# These mirror Module 02's fictional data so the hub is runnable in import-only
# and test environments. When the MCP adapter is available, the gateway can call
# the Module 02 FastMCP server for the same tool names.
# ═══════════════════════════════════════════════════════════════════════════════

EMPLOYEE_PROFILE = {
    "employee_id": "EMP-1042",
    "name": "Jordan Lee",
    "age": 36,
    "annual_salary": 120000,
    "filing_status": "single",
    "estimated_federal_tax_rate": 0.24,
    "estimated_state_tax_rate": 0.05,
    "benefits_year": 2026,
}

PLAN_401K = {
    "plan_name": "Acme FutureBuilder 401(k)",
    "employee_contribution_percent": 6.0,
    "ytd_employee_contribution": 7200,
    "ytd_employer_match": 5400,
    "match_formula": "100% of the first 3% of pay, plus 50% of the next 3% of pay",
    "max_match_percent": 4.5,
}

PLAN_HSA = {
    "plan_name": "Acme HDHP + HSA",
    "coverage": "family",
    "employee_annual_election": 4200,
    "employer_annual_contribution": 1000,
    "eligible_plan": True,
}


def _calculate_401k_match(salary: Optional[float] = None, employee_contribution_percent: Optional[float] = None) -> dict:
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    pct = employee_contribution_percent if employee_contribution_percent is not None else PLAN_401K["employee_contribution_percent"]
    first = min(pct, 3.0)
    second = min(max(pct - 3.0, 0.0), 3.0)
    match_pct = min(first + second * 0.5, PLAN_401K["max_match_percent"])
    return {
        "salary": salary,
        "employee_contribution_percent": pct,
        "employer_match_percent": round(match_pct, 2),
        "estimated_annual_employer_match": round(salary * match_pct / 100, 2),
        "full_match_reached": pct >= 6.0,
        "educational_note": "Mock estimate. Not financial advice.",
    }


def _estimate_hsa_tax_savings(annual_contribution: Optional[float] = None, marginal_tax_rate: Optional[float] = None) -> dict:
    contribution = annual_contribution if annual_contribution is not None else PLAN_HSA["employee_annual_election"]
    default_rate = EMPLOYEE_PROFILE["estimated_federal_tax_rate"] + EMPLOYEE_PROFILE["estimated_state_tax_rate"]
    rate = marginal_tax_rate if marginal_tax_rate is not None else default_rate
    fica_rate = 0.0765
    return {
        "annual_hsa_employee_contribution": contribution,
        "estimated_income_tax_savings": round(contribution * rate, 2),
        "estimated_fica_savings": round(contribution * fica_rate, 2),
        "estimated_total_savings": round(contribution * (rate + fica_rate), 2),
        "educational_note": "Educational estimate only. Not tax advice.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GATEWAY
# ═══════════════════════════════════════════════════════════════════════════════

class MCPGateway:
    def __init__(
        self,
        config_path: Path | str = DEFAULT_TENANT_CONFIG,
        *,
        external_enabled: Optional[bool] = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.tenants = load_tenants(self.config_path)
        self.server_configs = load_mcp_servers(self.config_path)
        self.external_enabled = env_bool("ENABLE_EXTERNAL_MCP", True) if external_enabled is None else external_enabled
        self._rag: dict[str, TenantRAG] = {}
        self._external_tools: Optional[dict[str, Any]] = None
        self._local_specs = {
            "get_employee_profile": "Return the fictional employee profile.",
            "get_401k_summary": "Return the fictional 401(k) plan and contribution summary.",
            "calculate_401k_match": "Estimate the fictional employer 401(k) match.",
            "get_hsa_summary": "Return the fictional HSA plan summary.",
            "estimate_hsa_tax_savings": "Estimate fictional HSA tax savings.",
            "search_benefits_docs": "Search the tenant's benefits reference summaries.",
            "list_sources": "List citation sources in the tenant corpus.",
            "search_tenant_docs": "Search only this tenant's document corpus.",
            "list_documents": "List only this tenant's available documents.",
            "get_document_excerpt": "Return an excerpt only if the document belongs to this tenant.",
            "usage_summary": "Summarize this tenant's month-to-date hub requests.",
        }

    def tenant(self, tenant_id: str) -> TenantConfig:
        if tenant_id not in self.tenants:
            raise ToolPermissionError(f"Unknown tenant: {tenant_id}")
        return self.tenants[tenant_id]

    def _tenant_rag(self, tenant_id: str) -> TenantRAG:
        if tenant_id not in self._rag:
            self._rag[tenant_id] = TenantRAG(self.tenant(tenant_id))
        return self._rag[tenant_id]

    def _check_allowed(self, tenant_id: str, tool_name: str) -> TenantConfig:
        tenant = self.tenant(tenant_id)
        if tool_name not in tenant.allowed_tools:
            raise ToolPermissionError(f"Tool {tool_name!r} is not allowed for tenant {tenant_id!r}")
        if tool_name not in self._local_specs and not self.external_enabled:
            raise ToolPermissionError(f"Unknown tool {tool_name!r}")
        return tenant

    def list_tools(self, tenant_id: str) -> list[ToolSpec]:
        tenant = self.tenant(tenant_id)
        return [
            ToolSpec(name=name, description=self._local_specs.get(name, "Tenant-allowed MCP tool."))
            for name in sorted(tenant.allowed_tools)
        ]

    def tenant_bound_tools(self, tenant_id: str) -> list[TenantBoundTool]:
        return [
            TenantBoundTool(spec.name, spec.description, tenant_id, self)
            for spec in self.list_tools(tenant_id)
        ]

    async def _ensure_external_tools(self) -> dict[str, Any]:
        if self._external_tools is not None:
            return self._external_tools
        if not self.external_enabled:
            self._external_tools = {}
            return self._external_tools

        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(self.server_configs)
        tools = await client.get_tools()
        self._external_tools = {tool.name: tool for tool in tools}
        return self._external_tools

    async def _call_external_tool(self, tool_name: str, kwargs: dict) -> Any:
        tools = await self._ensure_external_tools()
        tool = tools.get(tool_name)
        if tool is None:
            raise ToolPermissionError(f"Unknown MCP tool {tool_name!r}")
        if hasattr(tool, "ainvoke"):
            return await tool.ainvoke(kwargs)
        return tool.invoke(kwargs)

    def _call_external_sync(self, tool_name: str, kwargs: dict) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._call_external_tool(tool_name, kwargs))
        raise RuntimeError("Synchronous MCP calls cannot run inside an active event loop")

    def _usage_summary(self, tenant_id: str) -> dict:
        now = datetime.now(timezone.utc)
        total = 0
        path = audit_path()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("tenant_id") != tenant_id:
                    continue
                timestamp = str(record.get("timestamp", ""))
                if timestamp.startswith(f"{now.year:04d}-{now.month:02d}"):
                    total += 1
        return {"tenant_id": tenant_id, "month": f"{now.year:04d}-{now.month:02d}", "requests": total}

    def _call_local_tool(self, tenant_id: str, tool_name: str, kwargs: dict) -> Any:
        rag = self._tenant_rag(tenant_id)

        local: dict[str, Callable[..., Any]] = {
            "get_employee_profile": lambda: EMPLOYEE_PROFILE,
            "get_401k_summary": lambda: PLAN_401K,
            "calculate_401k_match": _calculate_401k_match,
            "get_hsa_summary": lambda: PLAN_HSA,
            "estimate_hsa_tax_savings": _estimate_hsa_tax_savings,
            "search_benefits_docs": lambda query, k=4: [
                {"document_id": r.document_id, "source": r.source, "text": r.text, "score": r.score}
                for r in rag.search(query, k=k)
            ],
            "list_sources": lambda: {doc["document_id"]: "See source links in document." for doc in rag.list_documents()},
            "search_tenant_docs": lambda query, k=4: [
                {"document_id": r.document_id, "source": r.source, "text": r.text, "score": r.score}
                for r in rag.search(query, k=k)
            ],
            "list_documents": rag.list_documents,
            "get_document_excerpt": rag.get_document_excerpt,
            "usage_summary": lambda: self._usage_summary(tenant_id),
        }
        if tool_name not in local:
            raise ToolPermissionError(f"Unknown local tool {tool_name!r}")
        return local[tool_name](**kwargs)

    def call_tool(self, tenant_id: str, tool_name: str, **kwargs) -> Any:
        self._check_allowed(tenant_id, tool_name)
        if self.external_enabled and tool_name not in {"search_tenant_docs", "list_documents", "get_document_excerpt", "usage_summary"}:
            try:
                return self._call_external_sync(tool_name, kwargs)
            except Exception:
                # The learning project should still run before optional MCP deps are
                # installed; the orchestrator also has a RAG fallback around this path.
                if tool_name not in self._local_specs:
                    raise
        return self._call_local_tool(tenant_id, tool_name, kwargs)
