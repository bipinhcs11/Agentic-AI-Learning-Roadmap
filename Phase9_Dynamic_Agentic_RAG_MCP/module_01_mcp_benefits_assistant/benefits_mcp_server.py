"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 01 | benefits_mcp_server.py                               ║
║  Local MCP Benefits Assistant for mock 401(k) and HSA data.                  ║
║                                                                              ║
║  PURPOSE: Teach MCP tools and resources before adding RAG, AWS, or SaaS      ║
║  complexity. This server exposes structured benefits data over MCP so an     ║
║  LLM client can inspect employee data, calculate matches, estimate HSA tax   ║
║  savings, and read simple plan rules.                                        ║
║                                                                              ║
║  SAFETY: All data is fictional. This is educational only and is not          ║
║  financial, tax, legal, or investment advice.                                ║
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
# resources, and client calls without connecting to payroll, retirement, banking,
# or benefits-provider systems. Later modules replace this dictionary with real
# tenant-scoped APIs, databases, and RAG-backed plan documents.
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
    "provider": "MockRetire",
    "plan_name": "Acme FutureBuilder 401(k)",
    "employee_contribution_percent": 6.0,
    "ytd_employee_contribution": 7200,
    "ytd_employer_match": 5400,
    "mock_employee_limit": 24500,
    "catch_up_age": 50,
    "match_formula": "100% of the first 3% of pay, plus 50% of the next 3% of pay",
    "max_match_percent": 4.5,
    "vesting": "Employer match vests 25% per year over four years.",
}

PLAN_HSA = {
    "provider": "MockHealth Bank",
    "plan_name": "Acme HDHP + HSA",
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
    "401k_plan_summary": """
The Acme FutureBuilder 401(k) lets employees contribute a percentage of pay.
The mock employer match is 100% of the first 3% of pay plus 50% of the next
3% of pay, for a maximum employer match of 4.5% of eligible pay. Employer
matching dollars vest 25% per year over four years.
""".strip(),
    "hsa_plan_summary": """
The Acme HDHP + HSA lets eligible employees contribute to a Health Savings
Account when enrolled in the qualifying high-deductible health plan. In this
mock plan, Acme contributes $1,000 per year for family coverage. HSA funds roll
over year to year and can be used for qualified medical expenses.
""".strip(),
    "benefits_faq": """
Frequently asked mock benefits questions:
- 401(k) contribution changes can be made any payroll period.
- HSA election changes may require a qualifying life event unless made during
  open enrollment.
- This training example does not provide financial, tax, legal, or investment
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
    estimated tax-rate assumptions before calculating 401(k) or HSA outcomes.
    """
    return EMPLOYEE_PROFILE


@mcp.tool()
def get_401k_summary() -> dict:
    """Return the mock employee's current 401(k) plan and contribution summary."""
    return PLAN_401K


@mcp.tool()
def calculate_401k_match(
    salary: Optional[float] = None,
    employee_contribution_percent: Optional[float] = None,
) -> dict:
    """Estimate the annual employer 401(k) match for the mock plan.

    Args:
        salary: Annual salary. Defaults to the mock employee salary.
        employee_contribution_percent: Employee contribution percent of pay.
            Defaults to the mock employee's current contribution rate.
    """
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    contribution_percent = (
        employee_contribution_percent
        if employee_contribution_percent is not None
        else PLAN_401K["employee_contribution_percent"]
    )

    first_tier = min(contribution_percent, 3.0)
    second_tier = min(max(contribution_percent - 3.0, 0.0), 3.0)
    match_percent = first_tier + (second_tier * 0.5)
    max_match_percent = PLAN_401K["max_match_percent"]
    match_percent = min(match_percent, max_match_percent)
    annual_match = salary * (match_percent / 100)

    return {
        "salary": salary,
        "employee_contribution_percent": contribution_percent,
        "employer_match_percent": round(match_percent, 2),
        "estimated_annual_employer_match": round(annual_match, 2),
        "full_match_reached": contribution_percent >= 6.0,
        "formula": PLAN_401K["match_formula"],
        "educational_note": "Mock estimate only. Confirm rules with the real plan document.",
    }


@mcp.tool()
def estimate_annual_401k_contribution(
    salary: Optional[float] = None,
    employee_contribution_percent: Optional[float] = None,
) -> dict:
    """Estimate annual employee 401(k) contributions and remaining mock limit.

    Args:
        salary: Annual salary. Defaults to the mock employee salary.
        employee_contribution_percent: Contribution percent. Defaults to the
            mock employee's current contribution rate.
    """
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    contribution_percent = (
        employee_contribution_percent
        if employee_contribution_percent is not None
        else PLAN_401K["employee_contribution_percent"]
    )
    annual_employee_contribution = salary * (contribution_percent / 100)
    remaining_to_mock_limit = PLAN_401K["mock_employee_limit"] - annual_employee_contribution

    return {
        "salary": salary,
        "employee_contribution_percent": contribution_percent,
        "estimated_annual_employee_contribution": round(annual_employee_contribution, 2),
        "mock_employee_limit": PLAN_401K["mock_employee_limit"],
        "remaining_to_mock_limit": round(max(0.0, remaining_to_mock_limit), 2),
        "would_exceed_mock_limit": annual_employee_contribution > PLAN_401K["mock_employee_limit"],
        "educational_note": "This uses mock plan assumptions, not official tax guidance.",
    }


@mcp.tool()
def get_hsa_summary() -> dict:
    """Return the mock employee's HSA coverage, election, balance, and plan summary."""
    return PLAN_HSA


@mcp.tool()
def estimate_hsa_tax_savings(
    annual_contribution: Optional[float] = None,
    marginal_tax_rate: Optional[float] = None,
) -> dict:
    """Estimate tax savings from a mock HSA contribution.

    Args:
        annual_contribution: Employee HSA contribution amount. Defaults to the
            mock employee annual election.
        marginal_tax_rate: Combined estimated tax rate. Defaults to the mock
            federal plus state rates from the employee profile.
    """
    contribution = (
        annual_contribution
        if annual_contribution is not None
        else PLAN_HSA["employee_annual_election"]
    )
    default_rate = (
        EMPLOYEE_PROFILE["estimated_federal_tax_rate"]
        + EMPLOYEE_PROFILE["estimated_state_tax_rate"]
    )
    tax_rate = marginal_tax_rate if marginal_tax_rate is not None else default_rate

    # HSA payroll contributions (Section 125) also avoid FICA, not just income tax.
    fica_rate = 0.0765  # Social Security 6.2% + Medicare 1.45%
    income_tax_savings = contribution * tax_rate
    fica_savings = contribution * fica_rate
    return {
        "annual_hsa_employee_contribution": contribution,
        "estimated_combined_income_tax_rate": round(tax_rate, 4),
        "estimated_income_tax_savings": round(income_tax_savings, 2),
        "estimated_fica_savings": round(fica_savings, 2),
        "estimated_total_savings": round(income_tax_savings + fica_savings, 2),
        "mock_family_limit": PLAN_HSA["mock_family_limit"],
        "within_mock_limit": contribution + PLAN_HSA["employer_annual_contribution"] <= PLAN_HSA["mock_family_limit"],
        "fica_note": "FICA savings apply to HSA contributions made through payroll (Section 125 cafeteria plan), not direct deposits.",
        "educational_note": "Educational estimate only. Tax treatment depends on facts and law.",
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
        document_id: e.g. "401k_plan_summary", "hsa_plan_summary", "benefits_faq".
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
        query: Search phrase such as "vesting", "match", "HSA rollover".
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


@mcp.resource("benefits://401k/plan-summary")
def plan_401k_resource() -> str:
    """Read-only mock 401(k) plan summary."""
    return _as_json(PLAN_401K)


@mcp.resource("benefits://hsa/plan-summary")
def hsa_plan_resource() -> str:
    """Read-only mock HSA plan summary."""
    return _as_json(PLAN_HSA)


@mcp.resource("benefits://documents/benefits-faq")
def benefits_faq_resource() -> str:
    """Read-only mock benefits FAQ."""
    return PLAN_DOCUMENTS["benefits_faq"]


@mcp.prompt()
def benefits_question_prompt(question: str) -> str:
    """Create a safe prompt for educational benefits questions."""
    return f"""You are an educational benefits assistant.

Use MCP tools and resources to answer the user's question from mock data.
Be clear when numbers are estimates. Do not provide financial, tax, legal, or
investment advice.

Question: {question}
"""


if __name__ == "__main__":
    mcp.run(transport="stdio")
