"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 02 | benefits_mcp_server.py                                 ║
║  MCP + RAG: one server, two kinds of context.                                 ║
║                                                                                ║
║  ┌─ MOCK structured tools ("your account") ──────────────────────────────┐    ║
║  │  get_employee_profile · get_401k_summary · calculate_401k_match ·      │    ║
║  │  get_hsa_summary · estimate_hsa_tax_savings   (fictional data only)    │    ║
║  └────────────────────────────────────────────────────────────────────────┘    ║
║  ┌─ RAG tools ("the rules") ─────────────────────────────────────────────┐    ║
║  │  search_benefits_docs · list_sources                                   │    ║
║  │  Corpus = public-source REFERENCE SUMMARIES compiled from IRS/Fidelity │    ║
║  │  (our own wording + source links — not verbatim copies of any doc).    │    ║
║  └────────────────────────────────────────────────────────────────────────┘    ║
║                                                                                ║
║  Retrieval = cosine + a topic/keyword rerank, so an "HSA limit" query cannot   ║
║  rank the 401(k) summary first. Queries use the nomic "search_query:" prefix.  ║
║                                                                                ║
║  SAFETY: All employee/account data is fictional. Educational only — not        ║
║  financial, tax, legal, or investment advice.                                  ║
║  RUN: python benefits_mcp_server.py   (speaks MCP over stdio)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

# ─── Config ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
EMBED_MODEL = "nomic-embed-text"
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(HERE, "index.npz")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
mcp = FastMCP("benefits-mcp-rag")

# ═══════════════════════════════════════════════════════════════════════════════
# MOCK STRUCTURED DATA  ("your account" — fictional, never embedded)
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

# ═══════════════════════════════════════════════════════════════════════════════
# CITATION SOURCES for the RAG corpus (public IRS / Fidelity references)
# ═══════════════════════════════════════════════════════════════════════════════
SOURCES = {
    "401k_reference.md": [
        "IRS — 401(k) limit increases to $24,500 for 2026: https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500",
        "Fidelity — 401(k) contribution limits 2025 and 2026: https://www.fidelity.com/learning-center/smart-money/401k-contribution-limits",
    ],
    "hsa_reference.md": [
        "IRS Revenue Procedure 2025-19 (official 2026 HSA/HDHP limits, PDF): https://www.irs.gov/pub/irs-drop/rp-25-19.pdf",
        "Fidelity — HSA contribution limits and eligibility 2026: https://www.fidelity.com/learning-center/smart-money/hsa-contribution-limits",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK STRUCTURED TOOLS  ("your account")
# ═══════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def get_employee_profile() -> dict:
    """Return the mock employee profile (salary, age, filing status, tax assumptions).
    Use for the user's PERSONAL numbers before any account calculation."""
    return EMPLOYEE_PROFILE


@mcp.tool()
def get_401k_summary() -> dict:
    """Return the mock employee's current 401(k) plan + contribution summary (their account)."""
    return PLAN_401K


@mcp.tool()
def calculate_401k_match(
    salary: Optional[float] = None,
    employee_contribution_percent: Optional[float] = None,
) -> dict:
    """Estimate the mock employer 401(k) match (an account calculation, not a rule lookup).

    Args:
        salary: defaults to the mock employee's salary.
        employee_contribution_percent: defaults to the mock employee's current rate.
    """
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    pct = (employee_contribution_percent if employee_contribution_percent is not None
           else PLAN_401K["employee_contribution_percent"])
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


@mcp.tool()
def get_hsa_summary() -> dict:
    """Return the mock employee's HSA coverage, election, and employer contribution (their account)."""
    return PLAN_HSA


@mcp.tool()
def estimate_hsa_tax_savings(
    annual_contribution: Optional[float] = None,
    marginal_tax_rate: Optional[float] = None,
) -> dict:
    """Estimate tax savings from a mock HSA contribution (an account calculation).

    Args:
        annual_contribution: defaults to the mock employee's election.
        marginal_tax_rate: defaults to mock federal + state rates.
    """
    contribution = (annual_contribution if annual_contribution is not None
                    else PLAN_HSA["employee_annual_election"])
    default_rate = (EMPLOYEE_PROFILE["estimated_federal_tax_rate"]
                    + EMPLOYEE_PROFILE["estimated_state_tax_rate"])
    rate = marginal_tax_rate if marginal_tax_rate is not None else default_rate
    fica_rate = 0.0765  # payroll (Section 125) contributions also avoid FICA
    income_tax_savings = contribution * rate
    fica_savings = contribution * fica_rate
    return {
        "annual_hsa_employee_contribution": contribution,
        "estimated_income_tax_savings": round(income_tax_savings, 2),
        "estimated_fica_savings": round(fica_savings, 2),
        "estimated_total_savings": round(income_tax_savings + fica_savings, 2),
        "fica_note": "FICA savings apply to payroll (Section 125) contributions, not direct deposits.",
        "educational_note": "Educational estimate only. Not tax advice.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RAG TOOLS  ("the rules" — public-source reference summaries)
# Index loads LAZILY: the mock tools above work with no Ollama and no index.
# Build the index with:  python ingest.py
# ═══════════════════════════════════════════════════════════════════════════════
_INDEX: Optional[dict] = None


def _load_index() -> dict:
    global _INDEX
    if _INDEX is None:
        data = np.load(INDEX_PATH, allow_pickle=True)
        emb = data["embeddings"].astype(np.float32)
        _INDEX = {"emb": emb, "chunks": data["chunks"], "sources": data["sources"],
                  "norms": np.linalg.norm(emb, axis=1)}
    return _INDEX


def _source_topic(source: str) -> str:
    s = str(source).lower()
    if "hsa" in s:
        return "hsa"
    if "401k" in s or "401(k)" in s:
        return "401k"
    return ""


def _query_topics(query: str) -> set[str]:
    ql = query.lower()
    topics = set()
    if any(w in ql for w in ("hsa", "health savings", "hdhp", "high-deductible",
                             "high deductible", "medical")):
        topics.add("hsa")
    if any(w in ql for w in ("401k", "401(k)", "match", "vest", "deferral",
                             "roth 401", "elective")):
        topics.add("401k")
    return topics


def _keywords(query: str) -> set[str]:
    return {w.strip(".,()?:;'\"") for w in query.lower().split() if len(w) > 2}


# ─── Intent disambiguation within the 401(k) doc ──────────────────────────────
# Two 401(k) limits compete and SHARE the '401k' topic, so the topic boost can't
# separate them: the employee-only salary-deferral limit ($24,500) vs the combined
# employee+employer annual cap ($72,000). A bare "employee contribution limit" query
# was ranking $72,000 first. Detect which limit the user asked for and nudge it up.
def _contribution_intent(query: str) -> str:
    ql = query.lower()
    # Combined-signal words win when both appear (e.g. "combined employee + employer").
    if any(w in ql for w in ("combined", "total contribution", "total limit", "overall",
                             "annual addition", "all contributions", "employee + employer",
                             "employee and employer", "415")):
        return "combined"
    if any(w in ql for w in ("employee", "elective", "salary deferral", "salary-deferral",
                             "defer", "i contribute", "i can contribute", "my contribution")):
        return "employee"
    return ""


def _chunk_contribution_kind(chunk: str) -> str:
    """Tag a 401(k) chunk by which limit it documents, read from its heading prefix."""
    head = str(chunk).splitlines()[0].lower() if chunk else ""
    if "combined" in head and "employer" in head:
        return "combined"
    if "employee contribution" in head:
        return "employee"
    return ""


def _rank(query: str, sims, chunks, sources) -> list[int]:
    """Pure hybrid rerank (no Ollama needed): cosine + topic-match boost + keyword
    overlap + a small employee-vs-combined intent boost. Guarantees an 'HSA family
    limit' query can't rank the 401(k) doc first, and that an "employee contribution
    limit" query ranks $24,500 above the combined $72,000 cap."""
    qtopics = _query_topics(query)
    qwords = _keywords(query)
    qintent = _contribution_intent(query)
    order = []
    for i in range(len(sims)):
        topic = _source_topic(sources[i])
        topic_boost = 0.15 if topic and topic in qtopics else 0.0
        kw = sum(1 for w in qwords if w in str(chunks[i]).lower())
        # Reward the limit the query asked for; penalize the other so it can't outrank it.
        intent_boost = 0.0
        if qintent:
            kind = _chunk_contribution_kind(chunks[i])
            if kind == qintent:
                intent_boost = 0.18
            elif kind:
                intent_boost = -0.18
        order.append((float(sims[i]) + topic_boost + 0.02 * kw + intent_boost, i))
    order.sort(key=lambda x: x[0], reverse=True)
    return [i for _, i in order]


@mcp.tool()
def search_benefits_docs(query: str, k: int = 4) -> str:
    """Search the public-source 401(k)/HSA reference summaries (IRS + Fidelity, 2026).

    Use this for official RULES, LIMITS, eligibility, or tax treatment — anything
    not specific to the user's own account. Cite the returned source file and call
    list_sources for the URLs.

    Args:
        query: the rule/limit question, e.g. "2026 HSA family contribution limit".
        k: number of excerpts to return (default 4).
    """
    if not os.path.exists(INDEX_PATH):
        return "RAG index not built yet. Run:  python ingest.py  (needs Ollama + nomic-embed-text)."
    try:
        idx = _load_index()
        q = np.array(
            client.embeddings.create(model=EMBED_MODEL, input=f"search_query: {query}").data[0].embedding,
            dtype=np.float32,
        )
        sims = (idx["emb"] @ q) / (idx["norms"] * np.linalg.norm(q) + 1e-8)
        ranked = _rank(query, sims, idx["chunks"], idx["sources"])[:max(1, k)]
        blocks = [f"[source: {idx['sources'][i]} · cosine {sims[i]:.3f}]\n{idx['chunks'][i]}"
                  for i in ranked]
        return "\n\n---\n\n".join(blocks) if blocks else "No relevant content found."
    except Exception as e:  # Ollama down, etc. — fail soft so the agent can recover
        return f"Retrieval unavailable ({e}). Is Ollama running with nomic-embed-text?"


@mcp.tool()
def list_sources() -> dict:
    """Return the citation sources (document → URLs) for the RAG corpus.
    Use to cite figures pulled from search_benefits_docs."""
    return SOURCES


if __name__ == "__main__":
    mcp.run(transport="stdio")
