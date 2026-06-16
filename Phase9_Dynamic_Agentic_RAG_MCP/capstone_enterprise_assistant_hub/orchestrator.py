"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | orchestrator.py                                       ║
║  Dynamic MCP + RAG routing with bounded tool calls and provider generation. ║
║                                                                              ║
║  WHY: enterprise questions are mixed. Some need only a direct answer, some  ║
║  need account tools, some need documents, and some need both. This router    ║
║  keeps that decision explicit and auditable.                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

try:
    from .audit import append_audit_record
    from .config import DEFAULT_TENANT_CONFIG, TenantConfig, env_bool, load_tenants
    from .mcp_gateway import MCPGateway
    from .providers import Completion, get_provider
    from .retrieval import TenantRAG, format_context
except ImportError:  # pragma: no cover
    from audit import append_audit_record
    from config import DEFAULT_TENANT_CONFIG, TenantConfig, env_bool, load_tenants
    from mcp_gateway import MCPGateway
    from providers import Completion, get_provider
    from retrieval import TenantRAG, format_context


ROUTES = {"direct", "mcp_only", "rag_only", "mcp+rag"}
MAX_TOOL_ITERATIONS = 4
DISCLAIMER = "Educational only; not financial, tax, legal, or investment advice."


@dataclass(frozen=True)
class RouteDecision:
    route: str
    reason: str


@dataclass
class HubResult:
    answer: str
    route: str
    tools_used: list[str]
    documents_used: list[str]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    sources: list[dict]


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

def heuristic_route(question: str) -> RouteDecision:
    q = question.lower()
    account_signal = any(
        token in q
        for token in (
            " my ",
            " i ",
            "me ",
            "am i",
            "salary",
            "paycheck",
            "contribute",
            "contribution rate",
            "match",
            "election",
            "tax savings",
            "account",
            "ytd",
        )
    ) or bool(re.search(r"\b\d+(\.\d+)?\s*%", q))
    rag_signal = any(
        token in q
        for token in (
            "2026",
            "limit",
            "rule",
            "irs",
            "fidelity",
            "source",
            "document",
            "policy",
            "eligible",
            "qualified",
            "hdhp",
            "vesting",
            "catch-up",
            "catch up",
        )
    )
    # HSA/401(k) alone can be conversational; pair it with a rule/account signal.
    if any(token in q for token in ("hsa", "401k", "401(k)")) and not account_signal:
        rag_signal = rag_signal or any(token in q for token in ("what", "how much", "can", "eligible"))

    if account_signal and rag_signal:
        return RouteDecision("mcp+rag", "Question mixes personal/mock account data with rules or documents.")
    if account_signal:
        return RouteDecision("mcp_only", "Question needs mock structured account tools.")
    if rag_signal:
        return RouteDecision("rag_only", "Question asks for limits, rules, policies, or citations.")
    return RouteDecision("direct", "No tenant document or account tool appears necessary.")


def _classify_with_qwen(question: str) -> Optional[RouteDecision]:
    if os.getenv("HUB_ROUTER_MODE", "").lower() == "heuristic":
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key="ollama",
            model=os.getenv("MCP_ROUTER_MODEL", "qwen2.5:3b"),
            temperature=0,
        )
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Classify the enterprise assistant route as JSON only. "
                        "Valid routes: direct, mcp_only, rag_only, mcp+rag. "
                        "Use mcp_only for personal/mock account values, rag_only for rules/documents, "
                        "mcp+rag for questions needing both."
                    )
                ),
                HumanMessage(content=f"Question: {question}\nReturn JSON like {{\"route\":\"rag_only\",\"reason\":\"...\"}}"),
            ]
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        match = re.search(r"\{.*\}", text, re.S)
        data = json.loads(match.group(0) if match else text)
        route = data.get("route", "")
        if route in ROUTES:
            return RouteDecision(route, data.get("reason", "qwen2.5 route decision"))
    except Exception:
        return None
    return None


def classify_route(question: str, classifier: Optional[Callable[[str], RouteDecision]] = None) -> RouteDecision:
    if classifier:
        decision = classifier(question)
        if decision.route not in ROUTES:
            raise ValueError(f"Invalid route from classifier: {decision.route}")
        return decision
    return _classify_with_qwen(question) or heuristic_route(question)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL PLAN
# ═══════════════════════════════════════════════════════════════════════════════

def _mcp_tool_plan(question: str) -> list[tuple[str, dict]]:
    q = question.lower()
    planned: list[tuple[str, dict]] = []
    if "hsa" in q:
        planned.append(("get_hsa_summary", {}))
        if "tax" in q or "saving" in q:
            planned.append(("estimate_hsa_tax_savings", {}))
    if "401" in q or "match" in q or "contribute" in q:
        planned.append(("get_401k_summary", {}))
        if "match" in q or "%" in q or "contribute" in q:
            planned.append(("calculate_401k_match", {}))
    if not planned:
        planned.append(("get_employee_profile", {}))
    return planned[:MAX_TOOL_ITERATIONS]


def _tool_documents(payload: Any) -> list[str]:
    docs: set[str] = set()
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                doc = item.get("document_id") or item.get("source")
                if doc:
                    docs.add(str(doc))
    if isinstance(payload, dict):
        doc = payload.get("document_id") or payload.get("source")
        if doc:
            docs.add(str(doc))
    return sorted(docs)


def _build_prompt(question: str, route: str, tool_outputs: list[dict], rag_context: str, tenant: TenantConfig) -> list[dict]:
    context_parts = [
        f"Tenant: {tenant.display_name} ({tenant.tenant_id})",
        f"Route: {route}",
    ]
    if tool_outputs:
        context_parts.append("Tool outputs:\n" + json.dumps(tool_outputs, indent=2, sort_keys=True))
    if rag_context:
        context_parts.append("Retrieved document context:\n" + rag_context)
    context_parts.append(f"Safety boundary: {DISCLAIMER}")

    return [
        {
            "role": "system",
            "content": (
                "You are an enterprise benefits assistant. Use only the supplied tool outputs "
                "and retrieved context for specific figures. Cite document filenames when they "
                "appear in context. Keep the answer concise and include the safety boundary."
            ),
        },
        {"role": "user", "content": "\n\n".join(context_parts) + f"\n\nQuestion: {question}"},
    ]


def _complete(messages: list[dict]) -> tuple[Completion, str]:
    provider = get_provider()
    completion = provider.complete(messages, temperature=0.2, max_tokens=800)
    return completion, provider.name


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def run_orchestrated(
    *,
    question: str,
    tenant_id: str,
    config_path=DEFAULT_TENANT_CONFIG,
    gateway: Optional[MCPGateway] = None,
    classifier: Optional[Callable[[str], RouteDecision]] = None,
    write_audit: bool = True,
) -> HubResult:
    tenants = load_tenants(config_path)
    if tenant_id not in tenants:
        raise PermissionError(f"Unknown tenant {tenant_id!r}")
    tenant = tenants[tenant_id]
    gateway = gateway or MCPGateway(config_path)
    rag = TenantRAG(tenant)
    decision = classify_route(question, classifier=classifier)

    tools_used: list[str] = []
    documents_used: list[str] = []
    sources: list[dict] = []
    tool_outputs: list[dict] = []
    rag_context = ""
    route = decision.route

    try:
        if route in {"mcp_only", "mcp+rag"}:
            for tool_name, kwargs in _mcp_tool_plan(question):
                payload = gateway.call_tool(tenant_id, tool_name, **kwargs)
                tools_used.append(tool_name)
                documents_used.extend(_tool_documents(payload))
                tool_outputs.append({"tool": tool_name, "result": payload})

        if route in {"rag_only", "mcp+rag"}:
            results = rag.search(question, k=4)
            sources = [
                {"document_id": r.document_id, "source": r.source, "score": r.score}
                for r in results
            ]
            documents_used.extend(r.document_id for r in results)
            rag_context = format_context(results)
    except Exception as exc:
        # Any MCP/tool failure falls back to direct tenant RAG, preserving isolation.
        route = "rag_only"
        tools_used = []
        tool_outputs = [{"tool_error": str(exc), "fallback": "direct tenant RAG"}]
        results = rag.search(question, k=4)
        sources = [{"document_id": r.document_id, "source": r.source, "score": r.score} for r in results]
        documents_used = [r.document_id for r in results]
        rag_context = format_context(results)

    messages = _build_prompt(question, route, tool_outputs, rag_context, tenant)
    completion, provider_name = _complete(messages)
    documents_used = sorted(set(documents_used))

    if write_audit:
        append_audit_record(
            tenant_id=tenant_id,
            question=question,
            route=route,
            tools_used=tools_used,
            documents_used=documents_used,
            provider=provider_name,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            extra={"model": completion.model, "router_reason": decision.reason},
        )

    return HubResult(
        answer=completion.text,
        route=route,
        tools_used=tools_used,
        documents_used=documents_used,
        provider=provider_name,
        model=completion.model,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        sources=sources,
    )


def answer_question(question: str, tenant_id: str, *, config_path=DEFAULT_TENANT_CONFIG) -> HubResult:
    # ENABLE_MCP=false preserves a direct tenant RAG path; true enables the dynamic route.
    if not env_bool("ENABLE_MCP", True):
        tenant = load_tenants(config_path)[tenant_id]
        rag = TenantRAG(tenant)
        results = rag.search(question, k=4)
        messages = _build_prompt(question, "rag_only", [], format_context(results), tenant)
        completion, provider_name = _complete(messages)
        documents_used = sorted({r.document_id for r in results})
        append_audit_record(
            tenant_id=tenant_id,
            question=question,
            route="rag_only",
            tools_used=[],
            documents_used=documents_used,
            provider=provider_name,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            extra={"model": completion.model, "router_reason": "ENABLE_MCP=false"},
        )
        return HubResult(
            answer=completion.text,
            route="rag_only",
            tools_used=[],
            documents_used=documents_used,
            provider=provider_name,
            model=completion.model,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            sources=[{"document_id": r.document_id, "source": r.source, "score": r.score} for r in results],
        )
    return run_orchestrated(question=question, tenant_id=tenant_id, config_path=config_path)
