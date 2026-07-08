"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Capstone | retrieval.py                                          ║
║  Tenant-scoped RAG over small public-source benefit reference summaries.    ║
║                                                                              ║
║  WHY: the capstone reuses Module 02's retrieval shape without sharing        ║
║  mutable indexes across tenants: heading chunks, local Ollama embeddings,    ║
║  NumPy cosine, topic/keyword rerank, and primary contribution limit intent disambiguation. ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

try:
    from .config import TenantConfig
except ImportError:  # pragma: no cover - lets `python hub.py` run from this folder
    from config import TenantConfig


EMBED_MODEL = "nomic-embed-text"
MAX_CHARS = 700


@dataclass(frozen=True)
class DocumentChunk:
    document_id: str
    source: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    source: str
    text: str
    score: float


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNKING
# ═══════════════════════════════════════════════════════════════════════════════

def _doc_title(text: str, fallback: str) -> str:
    match = re.search(r"(?m)^#\s+(.*)$", text)
    return match.group(1).strip() if match else fallback


def _split_long(body: str, prefix: str) -> list[str]:
    body = body.strip()
    if not body:
        return []
    if len(body) <= MAX_CHARS:
        return [f"[{prefix}]\n{body}"]

    chunks, buf = [], ""
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        if buf and len(buf) + len(para) + 1 > MAX_CHARS:
            chunks.append(f"[{prefix}]\n{buf.strip()}")
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf:
        chunks.append(f"[{prefix}]\n{buf.strip()}")
    return chunks


def section_chunks(text: str, doc_title: str) -> list[str]:
    parts = re.split(r"(?m)^(##\s+.*)$", text)
    chunks = _split_long(parts[0], doc_title)
    for i in range(1, len(parts), 2):
        heading = parts[i].lstrip("#").strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if heading.lower() == "sources":
            continue
        chunks.extend(_split_long(body, f"{doc_title} — {heading}"))
    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 02 HYBRID RERANK, INCLUDING THE primary contribution INTENT FIX
# ═══════════════════════════════════════════════════════════════════════════════

def _source_topic(source: str) -> str:
    source_l = str(source).lower()
    if "savings_account" in source_l:
        return "savings_account"
    if "primary_contribution" in source_l or "primary contribution" in source_l:
        return "primary_contribution"
    return ""


def _query_topics(query: str) -> set[str]:
    query_l = query.lower()
    topics = set()
    if any(w in query_l for w in ("savings_account", "savings account", "qualifying plan", "medical")):
        topics.add("savings_account")
    if any(w in query_l for w in ("primary_contribution", "primary contribution", "match", "vest", "deferral", "roth primary contribution", "elective")):
        topics.add("primary_contribution")
    return topics


def _keywords(query: str) -> set[str]:
    return {w.strip(".,()?:;'\"").lower() for w in query.split() if len(w.strip(".,()?:;'\"")) > 2}


def _contribution_intent(query: str) -> str:
    query_l = query.lower()
    if any(
        w in query_l
        for w in (
            "combined",
            "total contribution",
            "total limit",
            "overall",
            "annual addition",
            "all contributions",
            "employee + employer",
            "employee and employer",
            "415",
        )
    ):
        return "combined"
    if any(
        w in query_l
        for w in (
            "employee",
            "elective",
            "salary deferral",
            "salary-deferral",
            "defer",
            "i contribute",
            "i can contribute",
            "my contribution",
        )
    ):
        return "employee"
    return ""


def _chunk_contribution_kind(chunk: str) -> str:
    head = str(chunk).splitlines()[0].lower() if chunk else ""
    if "combined" in head and "employer" in head:
        return "combined"
    if "employee contribution" in head or "salary-deferral" in head:
        return "employee"
    return ""


def _rank(query: str, sims, chunks, sources) -> list[int]:
    qtopics = _query_topics(query)
    qwords = _keywords(query)
    qintent = _contribution_intent(query)
    order = []
    for i in range(len(sims)):
        chunk_text = str(chunks[i]).lower()
        topic = _source_topic(sources[i]) or _source_topic(chunks[i])
        topic_boost = 0.15 if topic and topic in qtopics else 0.0
        kw = sum(1 for w in qwords if w in chunk_text)
        intent_boost = 0.0
        if qintent:
            kind = _chunk_contribution_kind(chunks[i])
            if kind == qintent:
                intent_boost = 0.18
            elif kind:
                intent_boost = -0.18
        order.append((float(sims[i]) + topic_boost + 0.02 * kw + intent_boost, i))
    order.sort(key=lambda item: item[0], reverse=True)
    return [i for _, i in order]


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT RAG ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TenantRAG:
    def __init__(self, tenant: TenantConfig) -> None:
        self.tenant = tenant
        self._chunks: Optional[list[DocumentChunk]] = None
        self._embeddings: Optional[np.ndarray] = None
        self._client = None

    def _ollama_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                api_key="ollama",
            )
        return self._client

    def _embed(self, text: str, prefix: str) -> list[float]:
        response = self._ollama_client().embeddings.create(
            model=EMBED_MODEL,
            input=f"{prefix}: {text}",
        )
        return response.data[0].embedding

    def chunks(self) -> list[DocumentChunk]:
        if self._chunks is not None:
            return self._chunks

        chunks: list[DocumentChunk] = []
        for path in sorted(self.tenant.corpus.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = _doc_title(text, path.name)
            for chunk in section_chunks(text, title):
                chunks.append(DocumentChunk(document_id=path.name, source=path.name, text=chunk))
        self._chunks = chunks
        return chunks

    def _document_embeddings(self) -> np.ndarray:
        if self._embeddings is None:
            vectors = [self._embed(chunk.text, "search_document") for chunk in self.chunks()]
            self._embeddings = np.array(vectors, dtype=np.float32)
        return self._embeddings

    def _lexical_scores(self, query: str) -> np.ndarray:
        qwords = _keywords(query)
        scores = []
        for chunk in self.chunks():
            text = chunk.text.lower()
            scores.append(float(sum(1 for word in qwords if word in text)))
        return np.array(scores, dtype=np.float32)

    def search(self, query: str, k: int = 4, *, prefer_embeddings: bool = True) -> list[SearchResult]:
        chunks = self.chunks()
        if not chunks:
            return []

        sources = [chunk.source for chunk in chunks]
        texts = [chunk.text for chunk in chunks]
        try:
            if not prefer_embeddings:
                raise RuntimeError("Embedding search disabled")
            emb = self._document_embeddings()
            q = np.array(self._embed(query, "search_query"), dtype=np.float32)
            sims = (emb @ q) / (np.linalg.norm(emb, axis=1) * np.linalg.norm(q) + 1e-8)
        except Exception:
            # Tests and docs checks should never require Ollama. The live path still
            # uses local embeddings as soon as Ollama is available.
            sims = self._lexical_scores(query)

        ranked = _rank(query, sims, texts, sources)[: max(1, k)]
        return [
            SearchResult(
                document_id=chunks[i].document_id,
                source=chunks[i].source,
                text=chunks[i].text,
                score=float(sims[i]),
            )
            for i in ranked
        ]

    def list_documents(self) -> list[dict]:
        return [
            {"document_id": path.name, "filename": path.name, "status": "ready"}
            for path in sorted(self.tenant.corpus.glob("*.md"))
        ]

    def get_document_excerpt(self, document_id: str, max_chars: int = 600) -> dict:
        safe_name = Path(document_id).name
        path = (self.tenant.corpus / safe_name).resolve()
        if path.parent != self.tenant.corpus.resolve() or not path.exists():
            raise PermissionError("Document is not available for this tenant")
        text = path.read_text(encoding="utf-8")
        return {
            "document_id": safe_name,
            "filename": safe_name,
            "excerpt": text[: max(1, max_chars)],
        }


def format_context(results: list[SearchResult]) -> str:
    blocks = []
    for result in results:
        blocks.append(f"[source: {result.source} · score {result.score:.3f}]\n{result.text}")
    return "\n\n---\n\n".join(blocks)
