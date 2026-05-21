"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           DocuMind — Document Processor                                      ║
║           Phase 6 / Project 06 Capstone — Agentic AI Learning Roadmap       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Responsibilities:                                                           ║
║    • Parse uploaded files (PDF, TXT, MD) into raw text                       ║
║    • Chunk text with sliding-window overlap so context spans chunk borders   ║
║    • Obtain dense embeddings from Ollama nomic-embed-text                    ║
║    • Return typed Chunk objects ready for VectorStore ingestion              ║
║                                                                              ║
║  Design note: chunking is token-approximate (split on whitespace). For       ║
║  production one would use tiktoken; here we keep the stack dependency-light. ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import io
import logging
from dataclasses import dataclass, field
from typing import List

import httpx
import numpy as np

logger = logging.getLogger(__name__)

OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL: str = "nomic-embed-text"

CHUNK_TOKENS: int = 500   # approximate tokens per chunk
OVERLAP_TOKENS: int = 50  # overlap keeps context across boundaries


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single text segment with provenance metadata."""
    doc_id: str
    chunk_index: int
    text: str
    page: int = 0                        # 0-based; meaningful for PDFs
    embedding: List[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PDF / plain-text parsing
# ---------------------------------------------------------------------------

def _parse_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def _parse_text(data: bytes) -> str:
    """Decode plain-text or Markdown bytes to str."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_file(filename: str, data: bytes) -> str:
    """Dispatch to the correct parser based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return _parse_pdf(data)
    return _parse_text(data)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _words(text: str) -> List[str]:
    return text.split()


def chunk_text(text: str, doc_id: str) -> List[Chunk]:
    """
    Split text into overlapping windows of ~CHUNK_TOKENS words.

    Overlap ensures that answers straddling a boundary are still retrievable
    — a technique borrowed from Phase 2's RAG experiments.
    """
    words = _words(text)
    if not words:
        return []

    chunks: List[Chunk] = []
    start = 0
    idx = 0

    while start < len(words):
        end = min(start + CHUNK_TOKENS, len(words))
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        chunks.append(Chunk(
            doc_id=doc_id,
            chunk_index=idx,
            text=chunk_text_str,
            page=0,   # page-level tracking requires PDF-specific splitting (future work)
        ))

        idx += 1
        # Advance by chunk size minus overlap so consecutive chunks share context
        start += CHUNK_TOKENS - OVERLAP_TOKENS

    return chunks


# ---------------------------------------------------------------------------
# Embedding via Ollama
# ---------------------------------------------------------------------------

def embed_text(text: str) -> List[float]:
    """
    Call Ollama's embedding endpoint for a single string.
    Returns a float list; falls back to a zero vector on error so the
    pipeline degrades gracefully rather than crashing on embedding failure.
    """
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as exc:
        logger.warning("Embedding failed for text snippet: %s", exc)
        # Return zero vector; cosine similarity will score 0 — acceptable fallback
        return [0.0] * 768


def embed_chunks(chunks: List[Chunk]) -> List[Chunk]:
    """Attach embeddings to every chunk in place and return the list."""
    for chunk in chunks:
        chunk.embedding = embed_text(chunk.text)
    return chunks


# ---------------------------------------------------------------------------
# Main entry point used by the backend
# ---------------------------------------------------------------------------

class DocumentProcessor:
    """
    Stateless helper consumed by the FastAPI upload endpoint.

    Usage:
        processor = DocumentProcessor()
        chunks = processor.process(doc_id="uuid", filename="report.pdf", data=bytes_obj)
    """

    def process(self, doc_id: str, filename: str, data: bytes) -> List[Chunk]:
        """
        Full pipeline: parse → chunk → embed.
        Returns chunks with embeddings attached, ready for VectorStore.
        """
        raw_text = parse_file(filename, data)
        logger.info("Parsed %d chars from '%s'", len(raw_text), filename)

        chunks = chunk_text(raw_text, doc_id)
        logger.info("Split into %d chunks", len(chunks))

        chunks = embed_chunks(chunks)
        logger.info("Embedded %d chunks for doc_id=%s", len(chunks), doc_id)

        return chunks
