"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Phase 9 · MCP Benefits Example | benefits_mcp_server.py                       ║
║  A local MCP server (stdio) that exposes RAG retrieval over the benefit docs   ║
║  as TOOLS an agent can choose to call.                                         ║
║                                                                                ║
║  This is the "R-as-a-tool" idea: instead of hardcoding retrieve→generate, we   ║
║  publish search_benefits_docs() over MCP and let the agent decide when to use  ║
║  it. Embeddings + cosine stay local (Ollama + NumPy).                          ║
║                                                                                ║
║  RUN (standalone test):  python benefits_mcp_server.py   # speaks MCP on stdio ║
║  Normally it is launched as a subprocess by agent.py.                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import os

import numpy as np
from openai import OpenAI
from mcp.server.fastmcp import FastMCP

# ─── Config ──────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
EMBED_MODEL = "nomic-embed-text"
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(HERE, "index.npz")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
mcp = FastMCP("benefits-kb")

# ─── Load the index once at startup ──────────────────────────────────────────
if not os.path.exists(INDEX_PATH):
    raise SystemExit(f"Index not found at {INDEX_PATH}. Run:  python ingest.py")

_data = np.load(INDEX_PATH, allow_pickle=True)
_EMB = _data["embeddings"].astype(np.float32)
_CHUNKS = _data["chunks"]
_SOURCES = _data["sources"]
_NORMS = np.linalg.norm(_EMB, axis=1)        # precomputed for fast cosine


def _embed(text: str) -> np.ndarray:
    vec = client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding
    return np.array(vec, dtype=np.float32)


# ═══ MCP TOOLS ═══════════════════════════════════════════════════════════════
# The docstrings below are NOT decoration — FastMCP sends them to the LLM as the
# tool descriptions, so the model knows when/how to call each tool.

@mcp.tool()
def search_benefits_docs(query: str, k: int = 4) -> str:
    """Search the 401(k) and HSA reference documents for the passages most
    relevant to a question. Use this for any question about contribution limits,
    catch-up rules, HDHP eligibility, tax treatment, or 401(k)-vs-HSA differences.

    Args:
        query: the user's question or search phrase.
        k: how many excerpts to return (default 4).
    """
    q = _embed(query)
    sims = (_EMB @ q) / (_NORMS * np.linalg.norm(q) + 1e-8)   # cosine similarity
    top = np.argsort(sims)[::-1][:max(1, k)]
    blocks = [f"[{_SOURCES[i]} · score {sims[i]:.3f}]\n{_CHUNKS[i]}" for i in top]
    return "\n\n---\n\n".join(blocks) if blocks else "No relevant content found."


@mcp.tool()
def list_topics() -> str:
    """List which benefit documents are available to search."""
    uniq = sorted({str(s) for s in _SOURCES})
    return "Available documents:\n" + "\n".join(f"- {s}" for s in uniq)


if __name__ == "__main__":
    mcp.run(transport="stdio")
