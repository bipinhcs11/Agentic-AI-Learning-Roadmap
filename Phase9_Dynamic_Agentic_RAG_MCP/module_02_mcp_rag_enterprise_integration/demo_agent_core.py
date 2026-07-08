"""
Recording-friendly Python demo agent for Module 02.

This mirrors the Spring Boot playground response contract so one UI can switch
between the Python MCP + RAG flow and the Spring Boot microservice flow.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DOCS_DIR = HERE / "docs"

DEFAULT_QUESTION = (
    "I contribute 6% to my primary contribution. Am I getting the full match, "
    "and what is the 2026 employee limit?"
)

EMPLOYEE_PROFILE = {
    "employee_id": "EMP-1042",
    "name": "Jordan Lee",
    "age": 36,
    "annual_salary": 120000.0,
    "filing_status": "single",
    "estimated_federal_adjustment_rate": 0.24,
    "estimated_state_adjustment_rate": 0.05,
    "benefits_year": 2026,
}

PRIMARY_CONTRIBUTION_PLAN = {
    "plan_name": "Acme FutureBuilder primary contribution",
    "employee_contribution_percent": 6.0,
    "ytd_employee_contribution": 7200.0,
    "ytd_employer_match": 5400.0,
    "match_formula": "100% of the first 3% of pay, plus 50% of the next 3% of pay",
    "max_match_percent": 4.5,
}

SAVINGS_ACCOUNT_PLAN = {
    "plan_name": "Acme qualifying plan + savings account",
    "coverage": "family",
    "employee_annual_election": 4200.0,
    "employer_annual_contribution": 1000.0,
    "eligible_plan": True,
}

SOURCES = {
    "primary_contribution_reference.md": [
        "Fixture source summary",
        "Fixture source summary",
    ],
    "savings_account_reference.md": [
        "Fixture source summary",
        "Fixture source summary",
    ],
}

WORD_SPLIT = re.compile(r"[^a-z0-9$+]+")
PERCENT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def answer(question: str | None) -> dict[str, Any]:
    safe_question = question.strip() if question and question.strip() else DEFAULT_QUESTION
    lower = safe_question.lower()
    route = _choose_route(lower)
    use_mcp = route in {"mcp", "mcp+rag"}
    use_rag = route in {"rag", "mcp+rag"}

    tools: list[dict[str, Any]] = []
    profile = None
    match = None
    savings_account_adjustment_savings = None

    if use_mcp:
        profile = EMPLOYEE_PROFILE
        tools.append(_tool("get_employee_profile", "Python MCP account tool", {
            "employee_id": profile["employee_id"],
        }))

        if _is_savings_account_question(lower) and not _is_primary_contribution_question(lower):
            tools.append(_tool("get_savings_account_summary", "Python MCP account tool", {
                "plan_name": SAVINGS_ACCOUNT_PLAN["plan_name"],
            }))
            savings_account_adjustment_savings = estimate_savings_account_adjustment()
            tools.append(_tool("estimate_savings_account_adjustment", "Python MCP account tool", {
                "annual_contribution": SAVINGS_ACCOUNT_PLAN["employee_annual_election"],
                "adjustment_rate": (
                    profile["estimated_federal_adjustment_rate"]
                    + profile["estimated_state_adjustment_rate"]
                ),
            }))
        else:
            tools.append(_tool("get_primary_contribution_summary", "Python MCP account tool", {
                "plan_name": PRIMARY_CONTRIBUTION_PLAN["plan_name"],
            }))
            percent = _first_percent(lower, PRIMARY_CONTRIBUTION_PLAN["employee_contribution_percent"])
            match = calculate_primary_contribution_match(profile["annual_salary"], percent)
            tools.append(_tool("calculate_primary_contribution_match", "Python MCP account tool", {
                "salary": profile["annual_salary"],
                "employee_contribution_percent": percent,
            }))

    docs: list[dict[str, Any]] = []
    if use_rag:
        docs = search_benefits_docs(safe_question, 3)
        tools.append(_tool("search_benefits_docs", "Python RAG retrieval tool", {
            "query": safe_question,
            "k": 3,
        }))
        tools.append(_tool("list_sources", "Python RAG citation tool", {}))

    return {
        "route": route,
        "routeLabel": _route_label(route),
        "backend": "Python MCP + RAG router (Module 02)",
        "answer": _build_answer(route, safe_question, profile, match, savings_account_adjustment_savings, docs),
        "toolCalls": tools,
        "retrievedDocuments": docs,
        "citations": _citations_for(docs) if use_rag else [],
    }


def calculate_primary_contribution_match(
    salary: float | None = None,
    employee_contribution_percent: float | None = None,
) -> dict[str, Any]:
    resolved_salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    pct = (
        employee_contribution_percent
        if employee_contribution_percent is not None
        else PRIMARY_CONTRIBUTION_PLAN["employee_contribution_percent"]
    )
    first = min(pct, 3.0)
    second = min(max(pct - 3.0, 0.0), 3.0)
    match_pct = min(first + second * 0.5, PRIMARY_CONTRIBUTION_PLAN["max_match_percent"])
    return {
        "salary": resolved_salary,
        "employee_contribution_percent": pct,
        "employer_match_percent": round(match_pct, 2),
        "estimated_annual_employer_match": round(resolved_salary * match_pct / 100, 2),
        "full_match_reached": pct >= 6.0,
        "educational_note": "Mock estimate. Not professional advice.",
    }


def estimate_savings_account_adjustment(
    annual_contribution: float | None = None,
    adjustment_rate: float | None = None,
) -> dict[str, Any]:
    contribution = annual_contribution if annual_contribution is not None else SAVINGS_ACCOUNT_PLAN["employee_annual_election"]
    default_rate = (
        EMPLOYEE_PROFILE["estimated_federal_adjustment_rate"]
        + EMPLOYEE_PROFILE["estimated_state_adjustment_rate"]
    )
    rate = adjustment_rate if adjustment_rate is not None else default_rate
    record_system_rate = 0.0765
    return {
        "annual_savings_account_employee_contribution": contribution,
        "estimated_income_adjustment_savings": round(contribution * rate, 2),
        "estimated_record_system_savings": round(contribution * record_system_rate, 2),
        "estimated_total_savings": round(contribution * (rate + record_system_rate), 2),
        "record_system_note": "record-system estimate applies to record-system fixture contributions, not direct deposits.",
        "educational_note": "Educational estimate only. Not adjustment advice.",
    }


def search_benefits_docs(query: str, k: int = 3) -> list[dict[str, Any]]:
    chunks = _load_chunks()
    scored = [
        {
            "source": chunk["source"],
            "heading": chunk["heading"],
            "text": chunk["text"],
            "score": _score(query, chunk),
        }
        for chunk in chunks
    ]
    scored.sort(key=lambda hit: hit["score"], reverse=True)
    return scored[: max(1, k)]


def _choose_route(lower: str) -> str:
    account = _mentions_account(lower)
    rules = _mentions_rules(lower)
    if account and rules:
        return "mcp+rag"
    if account:
        return "mcp"
    if rules:
        return "rag"
    return "direct"


def _mentions_account(lower: str) -> bool:
    return any(
        phrase in lower
        for phrase in (
            "my ",
            " i ",
            "me ",
            "profile",
            "salary",
            "paycheck",
            "full match",
            "adjustment savings",
        )
    ) or lower.startswith("i ")


def _mentions_rules(lower: str) -> bool:
    return any(
        phrase in lower
        for phrase in (
            "2026",
            "limit",
            "public fixture",
            "fixture reference",
            "rule",
            "eligible",
            "eligibility",
            "source",
            "reference",
            "document",
            "maximum",
            "cap",
        )
    )


def _route_label(route: str) -> str:
    return {
        "mcp": "MCP only",
        "rag": "RAG only",
        "mcp+rag": "MCP + RAG",
    }.get(route, "Direct")


def _is_primary_contribution_question(lower: str) -> bool:
    return "primary_contribution" in lower or "primary contribution" in lower or "match" in lower


def _is_savings_account_question(lower: str) -> bool:
    return "savings_account" in lower or "savings account" in lower or "qualifying plan" in lower


def _first_percent(lower: str, fallback: float) -> float:
    match = PERCENT_PATTERN.search(lower)
    return float(match.group(1)) if match else fallback


def _tool(name: str, target: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "target": target,
        "arguments": arguments,
        "status": "ok",
    }


def _load_chunks() -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        chunks.extend(_section_chunks(path.name, path.read_text(encoding="utf-8")))
    if not chunks:
        raise RuntimeError(f"No markdown docs found in {DOCS_DIR}")
    return chunks


def _section_chunks(source: str, text: str) -> list[dict[str, str]]:
    title = source
    current_heading = title
    body: list[str] = []
    chunks: list[dict[str, str]] = []

    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            current_heading = title
            continue
        if line.startswith("## "):
            _add_chunk(chunks, source, current_heading, body)
            current_heading = f"{title} - {line[3:].strip()}"
            body = []
            continue
        body.append(line)
    _add_chunk(chunks, source, current_heading, body)
    return chunks


def _add_chunk(
    chunks: list[dict[str, str]],
    source: str,
    heading: str,
    body: list[str],
) -> None:
    text = "\n".join(body).strip()
    if text and not heading.lower().endswith("sources"):
        chunks.append({
            "source": source,
            "heading": heading,
            "text": f"[{heading}]\n{text}",
        })


def _score(query: str, chunk: dict[str, str]) -> float:
    lower = query.lower()
    text_lower = chunk["text"].lower()
    words = _keywords(lower)
    score = float(sum(1 for word in words if word in text_lower))

    topic = _topic(chunk["source"] + " " + chunk["heading"])
    if topic and topic in _query_topics(lower):
        score += 3.0

    heading_lower = chunk["heading"].lower()
    if "savings account" in lower and "limit" in lower and "contribution limits" in heading_lower:
        score += 4.0
    if "family" in lower and "$8,750" in chunk["text"]:
        score += 2.0

    intent = _contribution_intent(lower)
    if intent:
        kind = _contribution_kind(chunk["heading"])
        if kind == intent:
            score += 5.0
        elif kind:
            score -= 5.0

    return score


def _keywords(text: str) -> set[str]:
    return {word for word in WORD_SPLIT.split(text.lower()) if len(word) > 2}


def _query_topics(lower: str) -> set[str]:
    topics: set[str] = set()
    if "savings_account" in lower or "savings account" in lower or "qualifying plan" in lower:
        topics.add("savings_account")
    if (
        "primary_contribution" in lower
        or "primary contribution" in lower
        or "match" in lower
        or "deferral" in lower
        or "elective" in lower
    ):
        topics.add("primary_contribution")
    return topics


def _topic(text: str) -> str:
    lower = text.lower()
    if "savings_account" in lower:
        return "savings_account"
    if "primary_contribution" in lower or "primary contribution" in lower:
        return "primary_contribution"
    return ""


def _contribution_intent(lower: str) -> str:
    if any(
        phrase in lower
        for phrase in (
            "combined",
            "total limit",
            "overall",
            "annual addition",
            "employee + employer",
            "employee and employer",
        )
    ):
        return "combined"
    if any(
        phrase in lower
        for phrase in (
            "employee",
            "elective",
            "salary deferral",
            "salary-deferral",
            "my contribution",
            "i contribute",
        )
    ):
        return "employee"
    return ""


def _contribution_kind(heading: str) -> str:
    lower = heading.lower()
    if "combined" in lower and "employer" in lower:
        return "combined"
    if "employee contribution" in lower or "salary-deferral" in lower:
        return "employee"
    return ""


def _citations_for(docs: list[dict[str, Any]]) -> list[str]:
    citations: list[str] = []
    for doc in docs:
        for citation in SOURCES.get(doc["source"], []):
            if citation not in citations:
                citations.append(citation)
    return citations


def _build_answer(
    route: str,
    question: str,
    profile: dict[str, Any] | None,
    match: dict[str, Any] | None,
    savings_account_adjustment_savings: dict[str, Any] | None,
    docs: list[dict[str, Any]],
) -> str:
    if route == "direct":
        return (
            "This Python demo can answer general benefits questions directly, "
            "then escalate to MCP tools, RAG retrieval, or both when the question "
            "needs account data or policy references. Educational only - not "
            "professional, adjustment, legal, or allocation advice."
        )

    parts: list[str] = []
    if match and profile:
        parts.append(
            f"For {profile['name']}, a {match['employee_contribution_percent']:.1f}% "
            f"primary contribution on a ${match['salary']:,.0f} salary estimates a "
            f"{match['employer_match_percent']:.1f}% employer match, or about "
            f"${match['estimated_annual_employer_match']:,.0f} per year. "
            f"{'That reaches the full mock match.' if match['full_match_reached'] else 'That does not reach the full mock match yet.'}"
        )

    if savings_account_adjustment_savings:
        parts.append(
            "The mock savings account election estimates about "
            f"${savings_account_adjustment_savings['estimated_total_savings']:,.0f} in total adjustment savings, "
            "including income-adjustment and record system-adjustment components."
        )

    if docs:
        top = docs[0]
        parts.append(
            f"RAG retrieved {top['source']} under \"{top['heading']}\". "
            f"{_compact(top['text'])}"
        )

    if not parts:
        parts.append(f"I routed \"{question}\" but did not find a stronger demo path.")

    return " ".join(parts) + " Educational only - not professional, adjustment, legal, or allocation advice."


def _compact(text: str) -> str:
    cleaned = re.sub(r"\[[^\]]+\]\s*", "", text)
    cleaned = cleaned.replace("**", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) <= 260 else cleaned[:257].strip() + "..."
