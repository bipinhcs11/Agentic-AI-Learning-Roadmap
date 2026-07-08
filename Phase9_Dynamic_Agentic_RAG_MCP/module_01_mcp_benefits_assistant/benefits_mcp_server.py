"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 01 | benefits_mcp_server.py                               ║
║  Local MCP Benefits Assistant for mock primary contribution and savings account data.                  ║
║                                                                              ║
║  PURPOSE: Teach MCP tools and resources before adding RAG, AWS, or SaaS      ║
║  complexity. This server exposes structured benefits data over MCP so an     ║
║  LLM client can inspect employee data, calculate matches, estimate savings account adjustment   ║
║  savings, and read simple plan rules.                                        ║
║                                                                              ║
║  SAFETY: All data is fictional. This is educational only and is not          ║
║  professional, adjustment, legal, or allocation advice.                                ║
║                                                                              ║
║  RUN: python benefits_mcp_server.py                                          ║
║  The process speaks MCP over stdio and is normally launched by a client.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP


logging.getLogger("mcp").setLevel(logging.WARNING)

mcp = FastMCP("mock-benefits-assistant")


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA
# WHY mock data? MCP is a protocol boundary. You can learn the shape of tools,
# resources, and client calls without connecting to record system, future planning, banking,
# or benefits-provider systems. Later modules replace this dictionary with real
# tenant-scoped APIs, databases, and RAG-backed plan documents.
# ═══════════════════════════════════════════════════════════════════════════════

EMPLOYEE_PROFILE = {
    "employee_id": "EMP-1042",
    "name": "Jordan Lee",
    "age": 36,
    "annual_salary": 120000,
    "filing_status": "single",
    "estimated_federal_adjustment_rate": 0.24,
    "estimated_state_adjustment_rate": 0.05,
    "benefits_year": 2026,
}

PRIMARY_CONTRIBUTION_PLAN = {
    "provider": "MockRetire",
    "plan_name": "Acme FutureBuilder primary contribution",
    "employee_contribution_percent": 6.0,
    "ytd_employee_contribution": 7200,
    "ytd_employer_match": 5400,
    "mock_employee_limit": 24500,
    "catch_up_age": 50,
    "match_formula": "100% of the first 3% of pay, plus 50% of the next 3% of pay",
    "max_match_percent": 4.5,
    "vesting": "Employer match vests 25% per year over four years.",
}

SAVINGS_ACCOUNT_PLAN = {
    "provider": "MockHealth Bank",
    "plan_name": "Acme qualifying plan + savings account",
    "coverage": "family",
    "employee_annual_election": 4200,
    "employer_annual_contribution": 1000,
    "ytd_employee_contribution": 2100,
    "ytd_employer_contribution": 500,
    "mock_family_limit": 8750,
    "catch_up_age": 55,
    "catch_up_amount": 1000,
    "eligible_plan": True,
}

PLAN_DOCUMENTS = {
    "primary_contribution_plan_summary": """
The Acme FutureBuilder primary contribution lets employees contribute a percentage of pay.
The mock employer match is 100% of the first 3% of pay plus 50% of the next
3% of pay, for a maximum employer match of 4.5% of eligible pay. Employer
matching dollars vest 25% per year over four years.
""".strip(),
    "savings_account_plan_summary": """
The Acme qualifying plan + savings account lets eligible employees contribute to a savings account when enrolled in the qualifying plan. In this
mock plan, Acme contributes $1,000 per year for family coverage. savings account funds roll
over year to year and can be used for qualified medical expenses.
""".strip(),
    "benefits_faq": """
Frequently asked mock benefits questions:
- primary contribution changes can be made any record system period.
- savings account election changes may require a qualifying life event unless made during
  open enrollment.
- This training example does not provide professional, adjustment, legal, or allocation
  advice.
""".strip(),
}


def _as_json(data: dict | list) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOLS
# Tool docstrings matter: MCP clients show them to the model so it can decide
# which function to call and what arguments to provide.
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_employee_profile() -> dict:
    """Return the mock employee profile used by the benefits assistant.

    Use this when a question needs employee salary, age, filing status, or
    estimated adjustment-rate assumptions before calculating primary contribution or savings account outcomes.
    """
    return EMPLOYEE_PROFILE


@mcp.tool()
def get_primary_contribution_summary() -> dict:
    """Return the mock employee's current primary contribution plan and contribution summary."""
    return PRIMARY_CONTRIBUTION_PLAN


@mcp.tool()
def calculate_primary_contribution_match(
    salary: Optional[float] = None,
    employee_contribution_percent: Optional[float] = None,
) -> dict:
    """Estimate the annual employer primary contribution match for the mock plan.

    Args:
        salary: Annual salary. Defaults to the mock employee salary.
        employee_contribution_percent: Employee contribution percent of pay.
            Defaults to the mock employee's current contribution rate.
    """
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    contribution_percent = (
        employee_contribution_percent
        if employee_contribution_percent is not None
        else PRIMARY_CONTRIBUTION_PLAN["employee_contribution_percent"]
    )

    first_tier = min(contribution_percent, 3.0)
    second_tier = min(max(contribution_percent - 3.0, 0.0), 3.0)
    match_percent = first_tier + (second_tier * 0.5)
    max_match_percent = PRIMARY_CONTRIBUTION_PLAN["max_match_percent"]
    match_percent = min(match_percent, max_match_percent)
    annual_match = salary * (match_percent / 100)

    return {
        "salary": salary,
        "employee_contribution_percent": contribution_percent,
        "employer_match_percent": round(match_percent, 2),
        "estimated_annual_employer_match": round(annual_match, 2),
        "full_match_reached": contribution_percent >= 6.0,
        "formula": PRIMARY_CONTRIBUTION_PLAN["match_formula"],
        "educational_note": "Mock estimate only. Confirm rules with the real plan document.",
    }


@mcp.tool()
def estimate_annual_primary_contribution(
    salary: Optional[float] = None,
    employee_contribution_percent: Optional[float] = None,
) -> dict:
    """Estimate annual employee primary contributions and remaining mock limit.

    Args:
        salary: Annual salary. Defaults to the mock employee salary.
        employee_contribution_percent: Contribution percent. Defaults to the
            mock employee's current contribution rate.
    """
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    contribution_percent = (
        employee_contribution_percent
        if employee_contribution_percent is not None
        else PRIMARY_CONTRIBUTION_PLAN["employee_contribution_percent"]
    )
    annual_employee_contribution = salary * (contribution_percent / 100)
    remaining_to_mock_limit = PRIMARY_CONTRIBUTION_PLAN["mock_employee_limit"] - annual_employee_contribution

    return {
        "salary": salary,
        "employee_contribution_percent": contribution_percent,
        "estimated_annual_employee_contribution": round(annual_employee_contribution, 2),
        "mock_employee_limit": PRIMARY_CONTRIBUTION_PLAN["mock_employee_limit"],
        "remaining_to_mock_limit": round(max(0.0, remaining_to_mock_limit), 2),
        "would_exceed_mock_limit": annual_employee_contribution > PRIMARY_CONTRIBUTION_PLAN["mock_employee_limit"],
        "educational_note": "This uses mock plan assumptions, not fixture guidance.",
    }


@mcp.tool()
def get_savings_account_summary() -> dict:
    """Return the mock employee's savings account coverage, election, balance, and plan summary."""
    return SAVINGS_ACCOUNT_PLAN


@mcp.tool()
def estimate_savings_account_adjustment(
    annual_contribution: Optional[float] = None,
    adjustment_rate: Optional[float] = None,
) -> dict:
    """Estimate adjustment savings from a mock savings account contribution.

    Args:
        annual_contribution: Employee savings account contribution amount. Defaults to the
            mock employee annual election.
        adjustment_rate: Combined estimated adjustment rate. Defaults to the mock
            federal plus state rates from the employee profile.
    """
    contribution = (
        annual_contribution
        if annual_contribution is not None
        else SAVINGS_ACCOUNT_PLAN["employee_annual_election"]
    )
    default_rate = (
        EMPLOYEE_PROFILE["estimated_federal_adjustment_rate"]
        + EMPLOYEE_PROFILE["estimated_state_adjustment_rate"]
    )
    adjustment_rate = adjustment_rate if adjustment_rate is not None else default_rate

    # savings account record system contributions (Section 125) also avoid record-system, not just income adjustment.
    record_system_rate = 0.0765  # mock record-system rate
    income_adjustment_savings = contribution * adjustment_rate
    record_system_savings = contribution * record_system_rate
    return {
        "annual_savings_account_employee_contribution": contribution,
        "estimated_combined_income_adjustment_rate": round(adjustment_rate, 4),
        "estimated_income_adjustment_savings": round(income_adjustment_savings, 2),
        "estimated_record_system_savings": round(record_system_savings, 2),
        "estimated_total_savings": round(income_adjustment_savings + record_system_savings, 2),
        "mock_family_limit": SAVINGS_ACCOUNT_PLAN["mock_family_limit"],
        "within_mock_limit": contribution + SAVINGS_ACCOUNT_PLAN["employer_annual_contribution"] <= SAVINGS_ACCOUNT_PLAN["mock_family_limit"],
        "record_system_note": "record-system estimate applies to savings account contributions made through record system (fixture plan), not direct deposits.",
        "educational_note": "Educational estimate only. Adjustment treatment depends on facts and law.",
    }


@mcp.tool()
def list_plan_documents() -> list[dict]:
    """List the mock plan documents available as MCP resources or keyword search."""
    return [
        {"document_id": key, "title": key.replace("_", " ").title()}
        for key in sorted(PLAN_DOCUMENTS)
    ]


@mcp.tool()
def get_plan_document(document_id: str) -> dict:
    """Return the full text of a mock plan document by id.

    Use list_plan_documents first to see valid ids, then fetch the whole document
    here (vs. search_plan_rules, which only returns matching snippets).

    Args:
        document_id: e.g. "primary_contribution_plan_summary", "savings_account_plan_summary", "benefits_faq".
    """
    text = PLAN_DOCUMENTS.get(document_id)
    if text is None:
        return {
            "error": f"Unknown document_id '{document_id}'.",
            "available_document_ids": sorted(PLAN_DOCUMENTS),
        }
    return {
        "document_id": document_id,
        "title": document_id.replace("_", " ").title(),
        "text": text,
    }


@mcp.tool()
def search_plan_rules(query: str, max_results: int = 3) -> list[dict]:
    """Keyword-search the mock plan rules.

    This is intentionally not RAG. It is a tiny rule lookup so Module 01 stays
    focused on MCP. Module 02 replaces this with embeddings, retrieval, and
    citations over real document chunks.

    Args:
        query: Search phrase such as "vesting", "match", "savings account rollover".
        max_results: Maximum number of matching snippets to return.
    """
    words = {word.lower().strip(".,()") for word in query.split() if len(word) > 2}
    scored = []
    for document_id, text in PLAN_DOCUMENTS.items():
        normalized = text.lower()
        score = sum(1 for word in words if word in normalized)
        if score > 0:
            scored.append((score, document_id, text))

    scored.sort(reverse=True)
    return [
        {
            "document_id": document_id,
            "match_score": score,
            "snippet": text,
        }
        for score, document_id, text in scored[:max(1, max_results)]
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# MCP RESOURCES
# Resources are read-only context endpoints. Tools are verbs; resources are
# nouns. This contrast is the core beginner lesson in this module.
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("benefits://employee/profile")
def employee_profile_resource() -> str:
    """Read-only mock employee profile."""
    return _as_json(EMPLOYEE_PROFILE)


@mcp.resource("benefits://primary-contribution/plan-summary")
def plan_primary_contribution_resource() -> str:
    """Read-only mock primary contribution plan summary."""
    return _as_json(PRIMARY_CONTRIBUTION_PLAN)


@mcp.resource("benefits://savings-account/plan-summary")
def savings_account_plan_resource() -> str:
    """Read-only mock savings account plan summary."""
    return _as_json(SAVINGS_ACCOUNT_PLAN)


@mcp.resource("benefits://documents/benefits-faq")
def benefits_faq_resource() -> str:
    """Read-only mock benefits FAQ."""
    return PLAN_DOCUMENTS["benefits_faq"]


@mcp.prompt()
def benefits_question_prompt(question: str) -> str:
    """Create a safe prompt for educational benefits questions."""
    return f"""You are an educational benefits assistant.

Use MCP tools and resources to answer the user's question from mock data.
Be clear when numbers are estimates. Do not provide professional, adjustment, legal, or
allocation advice.

Question: {question}
"""


if __name__ == "__main__":
    mcp.run(transport="stdio")
