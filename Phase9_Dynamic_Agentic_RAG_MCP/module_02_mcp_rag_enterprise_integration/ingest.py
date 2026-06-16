"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · Module 02 | ingest.py                                              ║
║  Build the RAG index for the public-source 401(k)/HSA reference summaries.     ║
║                                                                                ║
║  CHUNKING: heading-anchored, not fixed-width. Markdown is split on '## '        ║
║  section headings; each chunk is prefixed with "[Doc — Heading]" so (a) it      ║
║  stays on ONE topic and (b) the embedding sees the topic words. Fixed-width     ║
║  slicing mixed 401(k) and HSA text in a single chunk and hurt retrieval.        ║
║                                                                                ║
║  EMBEDDING: Ollama nomic-embed-text with the recommended asymmetric prefix      ║
║  "search_document:" (queries use "search_query:" in the server). RAM-safe.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import glob
import os
import re

import numpy as np
from openai import OpenAI

# ─── Config ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
EMBED_MODEL = "nomic-embed-text"        # run: ollama pull nomic-embed-text
MAX_CHARS = 700                         # soft cap; longer sections split on paragraphs
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(HERE, "docs")
INDEX_PATH = os.path.join(HERE, "index.npz")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def _doc_title(text: str, fallback: str) -> str:
    m = re.search(r"(?m)^#\s+(.*)$", text)
    return m.group(1).strip() if m else fallback


def _split_long(body: str, prefix: str) -> list[str]:
    """Keep a section whole if short; otherwise split on blank lines (paragraphs)."""
    body = body.strip()
    if len(body) <= MAX_CHARS:
        return [f"[{prefix}]\n{body}"] if body else []
    out, buf = [], ""
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        if buf and len(buf) + len(para) + 1 > MAX_CHARS:
            out.append(f"[{prefix}]\n{buf.strip()}")
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf.strip():
        out.append(f"[{prefix}]\n{buf.strip()}")
    return out


def section_chunks(text: str, doc_title: str) -> list[str]:
    parts = re.split(r"(?m)^(##\s+.*)$", text)   # [pre, h1, body1, h2, body2, ...]
    chunks = _split_long(parts[0], doc_title)    # preamble under the doc title
    for i in range(1, len(parts), 2):
        heading = parts[i].lstrip("#").strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        if heading.lower() == "sources":         # skip the link list — not answerable content
            continue
        chunks.extend(_split_long(body, f"{doc_title} — {heading}"))
    return chunks


def embed_document(text: str) -> list[float]:
    # nomic-embed-text asymmetric search: documents get the "search_document:" prefix.
    return client.embeddings.create(
        model=EMBED_MODEL, input=f"search_document: {text}"
    ).data[0].embedding


def main() -> None:
    chunks, sources = [], []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.md"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for chunk in section_chunks(text, _doc_title(text, name)):
            chunks.append(chunk)
            sources.append(name)

    if not chunks:
        raise SystemExit(f"No .md docs found in {DOCS_DIR}")

    print(f"Embedding {len(chunks)} heading-anchored chunks via {EMBED_MODEL} ...")
    vectors = np.array([embed_document(c) for c in chunks], dtype=np.float32)

    np.savez(
        INDEX_PATH,
        embeddings=vectors,
        chunks=np.array(chunks, dtype=object),
        sources=np.array(sources, dtype=object),
    )
    print(f"Saved {vectors.shape[0]} vectors ({vectors.shape[1]}-dim) → {INDEX_PATH}")
    for i, c in enumerate(chunks):
        print(f"  chunk {i:2d} [{sources[i]}]: {c.splitlines()[0]}")


if __name__ == "__main__":
    main()
