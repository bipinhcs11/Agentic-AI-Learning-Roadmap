"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · MCP Benefits Example | ingest.py                                    ║
║  Build the vector index for the 401(k)/HSA reference docs.                     ║
║                                                                                ║
║  PIPELINE: docs/*.md → overlapping chunks → embed (Ollama nomic-embed-text)    ║
║            → save vectors + chunks + sources to index.npz (NumPy).             ║
║  WHY NumPy + Ollama? RAM-safe on the M4, no PyTorch / sentence-transformers,   ║
║  no external vector DB — exactly the project constraints.                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import glob
import os

import numpy as np
from openai import OpenAI

# ─── Config ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
EMBED_MODEL = "nomic-embed-text"        # run: ollama pull nomic-embed-text
CHUNK_SIZE = 500                        # chars per chunk
CHUNK_OVERLAP = 50                      # chars shared between neighbours
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(HERE, "docs")
INDEX_PATH = os.path.join(HERE, "index.npz")

# Embeddings go through Ollama's OpenAI-compatible endpoint (project convention)
client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


# ─── Chunking ────────────────────────────────────────────────────────────────
# WHY overlap? A figure that lands on a chunk boundary would be split in half and
# missed at retrieval time. Overlap keeps each fact whole in at least one chunk.
def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        piece = text[start:start + CHUNK_SIZE].strip()
        if piece:
            chunks.append(piece)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def embed(text: str) -> list[float]:
    return client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding


# ─── Build the index ─────────────────────────────────────────────────────────
def main() -> None:
    chunks, sources = [], []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.md"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as fh:
            for piece in chunk_text(fh.read()):
                chunks.append(piece)
                sources.append(name)

    if not chunks:
        raise SystemExit(f"No .md docs found in {DOCS_DIR}")

    print(f"Embedding {len(chunks)} chunks via {EMBED_MODEL} ...")
    vectors = np.array([embed(c) for c in chunks], dtype=np.float32)

    np.savez(
        INDEX_PATH,
        embeddings=vectors,
        chunks=np.array(chunks, dtype=object),
        sources=np.array(sources, dtype=object),
    )
    print(f"Saved {vectors.shape[0]} vectors ({vectors.shape[1]}-dim) → {INDEX_PATH}")


if __name__ == "__main__":
    main()
