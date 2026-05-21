"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           DocuMind — RAG Pipeline (Multi-Agent via LangGraph)                ║
║           Phase 6 / Project 06 Capstone — Agentic AI Learning Roadmap       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Agent roster:                                                               ║
║    1. RAGAgent        — retrieves top-k chunks, generates grounded answer   ║
║    2. CitationAgent   — identifies which chunks were used in the answer      ║
║    3. QualityAgent    — scores answer 1-10, decides if "IDK" is better      ║
║                                                                              ║
║  Coordination: LangGraph StateGraph (Phase 5 pattern extended here).         ║
║  The graph is linear:  retrieve → answer → cite → quality → END             ║
║                                                                              ║
║  VectorStore is an in-memory dict so the service stays stateless from the   ║
║  persistence layer's perspective (SQLite owns metadata; numpy owns vectors). ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional, TypedDict

import httpx
import numpy as np
from langgraph.graph import StateGraph, END

from document_processor import Chunk, embed_text

logger = logging.getLogger(__name__)

OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemma3:4b")
TOP_K: int = 4   # number of chunks to retrieve


# ─────────────────────────────────────────────────────────────────────────────
# VectorStore — thread-safe in-memory store
# ─────────────────────────────────────────────────────────────────────────────

class VectorStore:
    """
    Lightweight in-memory vector store using numpy cosine similarity.

    Structure:
        _store[doc_id] = {
            "chunks":     List[str],           # raw text per chunk
            "embeddings": np.ndarray (N, D),   # float32 matrix
            "metadata":   List[dict],          # chunk_index, page, filename
        }

    This mirrors the Phase 2 RAG approach but encapsulated into a class
    so multiple documents can coexist and be filtered by doc_id.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def add_document(self, doc_id: str, chunks: List[Chunk], filename: str) -> None:
        """Index a document's chunks.  Replaces any previous entry for doc_id."""
        if not chunks:
            logger.warning("add_document called with empty chunk list for %s", doc_id)
            return

        texts = [c.text for c in chunks]
        embeddings = np.array([c.embedding for c in chunks], dtype=np.float32)
        metadata = [
            {"chunk_index": c.chunk_index, "page": c.page, "filename": filename}
            for c in chunks
        ]

        self._store[doc_id] = {
            "chunks": texts,
            "embeddings": embeddings,
            "metadata": metadata,
        }
        logger.info("VectorStore: indexed %d chunks for doc_id=%s", len(chunks), doc_id)

    def remove_document(self, doc_id: str) -> None:
        self._store.pop(doc_id, None)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: List[float],
        doc_ids: Optional[List[str]] = None,
        top_k: int = TOP_K,
    ) -> List[Dict[str, Any]]:
        """
        Return top-k chunks by cosine similarity across specified doc_ids
        (or all docs if doc_ids is None).

        Each result dict: {text, score, doc_id, filename, chunk_index}
        """
        q = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []

        results: List[Dict[str, Any]] = []
        search_ids = doc_ids if doc_ids is not None else list(self._store.keys())

        for did in search_ids:
            entry = self._store.get(did)
            if entry is None:
                continue

            E = entry["embeddings"]           # (N, D)
            norms = np.linalg.norm(E, axis=1, keepdims=True)
            # Avoid division by zero for zero-vector embeddings (fallback case)
            norms = np.where(norms == 0, 1e-9, norms)
            E_norm = E / norms
            scores = E_norm @ (q / q_norm)    # cosine similarity for each chunk

            for i, score in enumerate(scores.tolist()):
                results.append({
                    "text": entry["chunks"][i],
                    "score": float(score),
                    "doc_id": did,
                    "filename": entry["metadata"][i]["filename"],
                    "chunk_index": entry["metadata"][i]["chunk_index"],
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def has_document(self, doc_id: str) -> bool:
        return doc_id in self._store

    def document_count(self) -> int:
        return len(self._store)


# Global singleton — shared across request handlers in a single process.
# In multi-worker deployments, use an external vector DB (e.g., Qdrant).
vector_store = VectorStore()


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph state
# ─────────────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    query: str
    doc_ids: List[str]           # restrict search to these docs (user scope)
    retrieved_chunks: List[Dict[str, Any]]
    answer: str
    citations: List[Dict[str, str]]  # [{filename, excerpt}]
    quality_score: int               # 1-10
    quality_note: str


# ─────────────────────────────────────────────────────────────────────────────
# Ollama LLM helper
# ─────────────────────────────────────────────────────────────────────────────

def _call_llm(prompt: str, system: str = "") -> str:
    """
    Thin wrapper around Ollama /api/generate.
    Using the generate (completion) API keeps us independent of
    the chat-formatted endpoint so any Ollama-supported model works.
    """
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": LLM_MODEL, "prompt": full_prompt, "stream": False},
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return "I was unable to generate a response due to an internal error."


# ─────────────────────────────────────────────────────────────────────────────
# Agent node functions (each mutates and returns the state dict)
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_node(state: PipelineState) -> PipelineState:
    """
    RAGAgent — embed the query, search the vector store scoped to the
    user's documents, and attach the top-k chunks to state.
    """
    q_embed = embed_text(state["query"])
    chunks = vector_store.search(
        query_embedding=q_embed,
        doc_ids=state["doc_ids"] if state["doc_ids"] else None,
        top_k=TOP_K,
    )
    state["retrieved_chunks"] = chunks
    logger.info("Retrieved %d chunks for query: '%s'", len(chunks), state["query"][:60])
    return state


def answer_node(state: PipelineState) -> PipelineState:
    """
    RAGAgent (answer phase) — synthesise an answer grounded in the
    retrieved context.  If no chunks were found, signals that clearly.
    """
    chunks = state["retrieved_chunks"]

    if not chunks:
        state["answer"] = (
            "I don't have enough information in your documents to answer this question. "
            "Please upload relevant documents and try again."
        )
        return state

    context_parts = []
    for i, c in enumerate(chunks, 1):
        context_parts.append(f"[Source {i}: {c['filename']}]\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)

    system = (
        "You are DocuMind, an expert document analyst. "
        "Answer the user's question using ONLY the provided document excerpts. "
        "Be concise and factual. If the context does not contain the answer, "
        "say 'I don't have enough information in the provided documents.'"
    )
    prompt = f"Context:\n{context}\n\nQuestion: {state['query']}\n\nAnswer:"

    state["answer"] = _call_llm(prompt, system)
    return state


def citation_node(state: PipelineState) -> PipelineState:
    """
    CitationAgent — maps the answer back to specific document sections.
    Uses a simple LLM call to identify which sources were actually used;
    falls back to listing all retrieved chunks if the LLM is unreliable.
    """
    chunks = state["retrieved_chunks"]
    if not chunks:
        state["citations"] = []
        return state

    # Build a numbered source list for the LLM to reference
    sources_summary = "\n".join(
        f"{i+1}. [{c['filename']} chunk {c['chunk_index']}]: {c['text'][:120]}..."
        for i, c in enumerate(chunks)
    )

    system = (
        "You are a citation extractor. "
        "Given an answer and a list of source excerpts, "
        "return ONLY the numbers (comma-separated) of the sources that were used "
        "to write the answer. Example: 1,3"
    )
    prompt = (
        f"Answer: {state['answer']}\n\n"
        f"Sources:\n{sources_summary}\n\n"
        "Which source numbers were used? Reply with numbers only."
    )

    raw = _call_llm(prompt, system)

    # Parse the LLM response; fall back to top-2 chunks on parse failure
    used_indices: List[int] = []
    for token in raw.replace(" ", "").split(","):
        try:
            idx = int(token.strip()) - 1
            if 0 <= idx < len(chunks):
                used_indices.append(idx)
        except ValueError:
            pass

    if not used_indices:
        used_indices = list(range(min(2, len(chunks))))

    citations = [
        {
            "filename": chunks[i]["filename"],
            "excerpt": chunks[i]["text"][:300] + ("..." if len(chunks[i]["text"]) > 300 else ""),
            "score": f"{chunks[i]['score']:.3f}",
        }
        for i in used_indices
    ]

    state["citations"] = citations
    return state


def quality_node(state: PipelineState) -> PipelineState:
    """
    AnswerQualityAgent — rates the answer 1-10 and flags low-quality
    responses so the UI can show a warning.

    A score ≤ 3 means the agent recommends saying "I don't know" instead.
    """
    if not state["retrieved_chunks"]:
        state["quality_score"] = 0
        state["quality_note"] = "No relevant documents found."
        return state

    system = (
        "You are a quality evaluator. Rate the following answer on a scale of 1-10 "
        "based on how well it answers the question using the given context. "
        "Reply with ONLY a single integer between 1 and 10."
    )
    prompt = (
        f"Question: {state['query']}\n"
        f"Answer: {state['answer']}\n\n"
        "Quality score (1-10):"
    )

    raw = _call_llm(prompt, system).strip()

    score = 5  # neutral default
    for token in raw.split():
        try:
            val = int(token)
            if 1 <= val <= 10:
                score = val
                break
        except ValueError:
            pass

    note = ""
    if score <= 3:
        note = "Low confidence — the documents may not contain sufficient information."

    state["quality_score"] = score
    state["quality_note"] = note
    return state


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph pipeline assembly
# ─────────────────────────────────────────────────────────────────────────────

def _build_graph() -> Any:
    """
    Wire up the four agent nodes into a linear StateGraph.
    Linear here means no conditional branching — every query passes through
    all agents.  Future work: add a router that skips quality_node for
    simple factual lookups to reduce latency.
    """
    g = StateGraph(PipelineState)

    g.add_node("retrieve", retrieve_node)
    g.add_node("answer", answer_node)
    g.add_node("cite", citation_node)
    g.add_node("quality", quality_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", "cite")
    g.add_edge("cite", "quality")
    g.add_edge("quality", END)

    return g.compile()


# Compiled graph — reused across requests (thread-safe since nodes are pure functions)
_pipeline = _build_graph()


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Thin facade used by the FastAPI backend.
    Wraps the LangGraph compiled app and provides a clean run() method.
    """

    def run(self, query: str, doc_ids: List[str]) -> Dict[str, Any]:
        """
        Execute the full retrieve → answer → cite → quality pipeline.

        Returns:
            {
                "answer": str,
                "citations": [{filename, excerpt, score}],
                "quality_score": int,
                "quality_note": str,
            }
        """
        initial_state: PipelineState = {
            "query": query,
            "doc_ids": doc_ids,
            "retrieved_chunks": [],
            "answer": "",
            "citations": [],
            "quality_score": 0,
            "quality_note": "",
        }

        final_state = _pipeline.invoke(initial_state)

        return {
            "answer": final_state["answer"],
            "citations": final_state["citations"],
            "quality_score": final_state["quality_score"],
            "quality_note": final_state["quality_note"],
        }
