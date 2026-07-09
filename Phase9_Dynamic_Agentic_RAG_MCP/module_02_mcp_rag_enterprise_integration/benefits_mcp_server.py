"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 02 | benefits_mcp_server.py                                 ║
║  MCP + RAG: one server, two kinds of context.                                 ║
║                                                                                ║
║  ┌─ MOCK structured tools ("your account") ──────────────────────────────┐    ║
║  │  get_employee_profile · get_primary_contribution_summary · calculate_primary_contribution_match ·      │    ║
║  │  get_savings_account_summary · estimate_savings_account_adjustment   (fictional data only)    │    ║
║  └────────────────────────────────────────────────────────────────────────┘    ║
║  ┌─ RAG tools ("the rules") ─────────────────────────────────────────────┐    ║
║  │  search_benefits_docs · list_sources                                   │    ║
║  │  Corpus = public-source REFERENCE SUMMARIES compiled from fixture references │    ║
║  │  (our own wording + source links — not verbatim copies of any doc).    │    ║
║  └────────────────────────────────────────────────────────────────────────┘    ║
║                                                                                ║
║  Retrieval = cosine + a topic/keyword rerank, so an "savings account limit" query cannot   ║
║  rank the primary contribution summary first. Queries use the nomic "search_query:" prefix.  ║
║                                                                                ║
║  SAFETY: All employee/account data is fictional. Educational only — not        ║
║  professional, adjustment, legal, or allocation advice.                                  ║
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
    "estimated_federal_adjustment_rate": 0.24,
    "estimated_state_adjustment_rate": 0.05,
    "benefits_year": 2026,
}

PRIMARY_CONTRIBUTION_PLAN = {
    "plan_name": "Acme FutureBuilder primary contribution",
    "employee_contribution_percent": 6.0,
    "ytd_employee_contribution": 7200,
    "ytd_employer_match": 5400,
    "match_formula": "100% of the first 3% of pay, plus 50% of the next 3% of pay",
    "max_match_percent": 4.5,
}

SAVINGS_ACCOUNT_PLAN = {
    "plan_name": "Acme qualifying plan + savings account",
    "coverage": "family",
    "employee_annual_election": 4200,
    "employer_annual_contribution": 1000,
    "eligible_plan": True,
}

# ═══════════════════════════════════════════════════════════════════════════════
# CITATION SOURCES for the RAG corpus (public fixture references references)
# ═══════════════════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK STRUCTURED TOOLS  ("your account")
# ═══════════════════════════════════════════════════════════════════════════════
@mcp.tool()
def get_employee_profile() -> dict:
    """Return the mock employee profile (salary, age, filing status, adjustment assumptions).
    Use for the user's PERSONAL numbers before any account calculation."""
    return EMPLOYEE_PROFILE


@mcp.tool()
def get_primary_contribution_summary() -> dict:
    """Return the mock employee's current primary contribution plan + contribution summary (their account)."""
    return PRIMARY_CONTRIBUTION_PLAN


@mcp.tool()
def calculate_primary_contribution_match(
    salary: Optional[float] = None,
    employee_contribution_percent: Optional[float] = None,
) -> dict:
    """Estimate the mock employer primary contribution match (an account calculation, not a rule lookup).

    Args:
        salary: defaults to the mock employee's salary.
        employee_contribution_percent: defaults to the mock employee's current rate.
    """
    salary = salary if salary is not None else EMPLOYEE_PROFILE["annual_salary"]
    pct = (employee_contribution_percent if employee_contribution_percent is not None
           else PRIMARY_CONTRIBUTION_PLAN["employee_contribution_percent"])
    first = min(pct, 3.0)
    second = min(max(pct - 3.0, 0.0), 3.0)
    match_pct = min(first + second * 0.5, PRIMARY_CONTRIBUTION_PLAN["max_match_percent"])
    return {
        "salary": salary,
        "employee_contribution_percent": pct,
        "employer_match_percent": round(match_pct, 2),
        "estimated_annual_employer_match": round(salary * match_pct / 100, 2),
        "full_match_reached": pct >= 6.0,
        "educational_note": "Mock estimate. Not professional advice.",
    }


@mcp.tool()
def get_savings_account_summary() -> dict:
    """Return the mock employee's savings account coverage, election, and employer contribution (their account)."""
    return SAVINGS_ACCOUNT_PLAN


@mcp.tool()
def estimate_savings_account_adjustment(
    annual_contribution: Optional[float] = None,
    adjustment_rate: Optional[float] = None,
) -> dict:
    """Estimate adjustment savings from a mock savings account contribution (an account calculation).

    Args:
        annual_contribution: defaults to the mock employee's election.
        adjustment_rate: defaults to mock federal + state rates.
    """
    contribution = (annual_contribution if annual_contribution is not None
                    else SAVINGS_ACCOUNT_PLAN["employee_annual_election"])
    default_rate = (EMPLOYEE_PROFILE["estimated_federal_adjustment_rate"]
                    + EMPLOYEE_PROFILE["estimated_state_adjustment_rate"])
    rate = adjustment_rate if adjustment_rate is not None else default_rate
    record_system_rate = 0.0765  # record-system fixture contributions also avoid record-system
    income_adjustment_savings = contribution * rate
    record_system_savings = contribution * record_system_rate
    return {
        "annual_savings_account_employee_contribution": contribution,
        "estimated_income_adjustment_savings": round(income_adjustment_savings, 2),
        "estimated_record_system_savings": round(record_system_savings, 2),
        "estimated_total_savings": round(income_adjustment_savings + record_system_savings, 2),
        "record_system_note": "record-system estimate applies to record-system fixture contributions, not direct deposits.",
        "educational_note": "Educational estimate only. Not adjustment advice.",
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
    if "savings_account" in s:
        return "savings_account"
    if "primary_contribution" in s or "primary contribution" in s:
        return "primary_contribution"
    return ""


def _query_topics(query: str) -> set[str]:
    ql = query.lower()
    topics = set()
    if any(w in ql for w in ("savings_account", "savings account", "qualifying plan", "high-deductible",
                             "high deductible", "medical")):
        topics.add("savings_account")
    if any(w in ql for w in ("primary_contribution", "primary contribution", "match", "vest", "deferral",
                             "roth primary contribution", "elective")):
        topics.add("primary_contribution")
    return topics


def _keywords(query: str) -> set[str]:
    return {w.strip(".,()?:;'\"") for w in query.lower().split() if len(w) > 2}


# ─── Intent disambiguation within the primary contribution doc ──────────────────────────────
# Two primary contribution limits compete and SHARE the 'primary_contribution' topic, so the topic boost can't
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
    """Tag a primary contribution chunk by which limit it documents, read from its heading prefix."""
    head = str(chunk).splitlines()[0].lower() if chunk else ""
    if "combined" in head and "employer" in head:
        return "combined"
    if "employee contribution" in head:
        return "employee"
    return ""


def _rank(query: str, sims, chunks, sources) -> list[int]:
    """Pure hybrid rerank (no Ollama needed): cosine + topic-match boost + keyword
    overlap + a small employee-vs-combined intent boost. Guarantees an 'savings account family
    limit' query can't rank the primary contribution doc first, and that an "employee contribution
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
    """Search the public-source primary contribution/savings account reference summaries (fixture references, 2026).

    Use this for official RULES, LIMITS, eligibility, or adjustment treatment — anything
    not specific to the user's own account. Cite the returned source file and call
    list_sources for the URLs.

    Args:
        query: the rule/limit question, e.g. "2026 savings account family contribution limit".
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
