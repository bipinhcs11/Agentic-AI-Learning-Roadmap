"""
Project 1 — First RAG System from Scratch (RAM-Safe Version)
=============================================================
Agentic AI Learning Roadmap — Phase 2, Week 3

Zero heavy dependencies — no PyTorch, no sentence-transformers, no chromadb.
Uses only: openai (Ollama client) + numpy (cosine similarity).
All embedding and generation goes through Ollama via its API.

Prerequisites (already installed):
  pip install openai numpy

Ollama models needed:
  ollama pull nomic-embed-text   (~274 MB — embedding model)
  ollama pull gemma3:27b         (generation model)

Run: python rag_from_scratch.py
"""

import json
import numpy as np
from openai import OpenAI

# ── Configuration ───────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
LLM_MODEL       = "gemma3:27b"
EMBED_MODEL     = "nomic-embed-text"  # tiny 274MB embedding model via Ollama
CHUNK_SIZE      = 400
CHUNK_OVERLAP   = 60
TOP_K           = 3

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

# ── Sample documents ────────────────────────────────────────────
DOCUMENTS = [
    """
    Artificial intelligence (AI) is the simulation of human intelligence processes
    by machines, especially computer systems. Specific applications include expert
    systems, natural language processing, speech recognition and machine vision.
    AI systems are trained on large datasets and use that training to make
    predictions and decisions autonomously.
    """,
    """
    Machine learning is a subset of artificial intelligence that gives systems
    the ability to automatically learn and improve from experience without being
    explicitly programmed. It focuses on developing programs that can access data
    and use it to learn for themselves, starting from observations or examples.
    """,
    """
    Deep learning uses artificial neural networks with many layers to learn
    representations of data. Transformer architectures revolutionised natural
    language processing and are the foundation of modern LLMs like GPT and Gemma.
    Deep learning models require large datasets and significant compute to train.
    """,
    """
    Retrieval-Augmented Generation (RAG) enhances LLM responses by retrieving
    relevant information from a knowledge base before generating an answer.
    Instead of relying on training data alone, RAG looks up fresh, specific
    information and gives it to the model as context. RAG is the most important
    pattern in production AI applications today because it prevents hallucination
    and allows models to answer questions about your own documents.
    """,
    """
    Vector databases store embeddings — high-dimensional numerical vectors that
    capture semantic meaning. When you search a vector database, it finds items
    semantically similar to your query using cosine similarity or dot products.
    ChromaDB, Qdrant and Pinecone are popular vector databases for RAG systems.
    """,
    """
    Ollama is an open-source tool that runs large language models locally on
    your Mac. It supports Gemma3, Llama3, Mistral and many others, and exposes
    an OpenAI-compatible API at http://localhost:11434. It also supports
    embedding models like nomic-embed-text, so you can create vector embeddings
    without any external API calls or costs.
    """,
]


# ════════════════════════════════════════════════════════════════
# STEP 1 — Chunk documents
# ════════════════════════════════════════════════════════════════
def chunk_text(text: str) -> list:
    text = text.strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            period = text.find('. ', end)
            if period != -1 and period < end + 100:
                end = period + 1
        chunk = text[start:end].strip()
        if len(chunk) > 30:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


# ════════════════════════════════════════════════════════════════
# STEP 2 — Embed text via Ollama (no PyTorch, no heavy libs)
# ════════════════════════════════════════════════════════════════
def embed_one(text: str) -> np.ndarray:
    """Embed a single string using nomic-embed-text via Ollama."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=text)
    return np.array(resp.data[0].embedding, dtype=np.float32)


# ════════════════════════════════════════════════════════════════
# STEP 3 — Build in-memory vector store (pure numpy, no chromadb)
# ════════════════════════════════════════════════════════════════
def build_store(documents: list) -> tuple:
    """Chunk, embed, and return a simple in-memory vector store."""
    print("Chunking documents...")
    chunks, ids = [], []
    for i, doc in enumerate(documents):
        for j, chunk in enumerate(chunk_text(doc)):
            chunks.append(chunk)
            ids.append(f"d{i}c{j}")
    print(f"  {len(chunks)} chunks from {len(documents)} documents")

    print(f"Embedding via Ollama ({EMBED_MODEL})...")
    vectors = []
    for k, chunk in enumerate(chunks):
        vectors.append(embed_one(chunk))
        print(f"  {k+1}/{len(chunks)} embedded", end="\r")
    print()

    matrix = np.stack(vectors)  # shape: (n_chunks, embedding_dim)
    print(f"  Vector store ready: {matrix.shape}\n")
    return chunks, matrix


# ════════════════════════════════════════════════════════════════
# STEP 4 — Cosine similarity search (pure numpy)
# ════════════════════════════════════════════════════════════════
def retrieve(query: str, chunks: list, matrix: np.ndarray) -> list:
    """Find TOP_K most similar chunks to the query using cosine similarity."""
    q_vec = embed_one(query)
    # Normalise for cosine similarity
    q_norm  = q_vec / (np.linalg.norm(q_vec) + 1e-10)
    m_norms = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    scores  = m_norms @ q_norm                  # cosine similarity for all chunks
    top_idx = np.argsort(scores)[::-1][:TOP_K]  # indices of best matches
    return [chunks[i] for i in top_idx]


# ════════════════════════════════════════════════════════════════
# STEP 5 — Generate answer with Gemma3
# ════════════════════════════════════════════════════════════════
def generate(query: str, context_chunks: list) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    prompt  = (
        "You are a helpful assistant. Answer the question using ONLY the context below.\n"
        "If the answer is not in the context, say 'I don't have enough information.'\n\n"
        f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    )
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return resp.choices[0].message.content


# ════════════════════════════════════════════════════════════════
# STEP 6 — Full RAG pipeline
# ════════════════════════════════════════════════════════════════
def rag(query: str, chunks: list, matrix: np.ndarray) -> str:
    print(f"\nQuery: {query}")
    print("-" * 60)
    top_chunks = retrieve(query, chunks, matrix)
    print(f"Top match: {top_chunks[0][:90]}...")
    answer = generate(query, top_chunks)
    print(f"\nAnswer:\n{answer}")
    print("=" * 60)
    return answer


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  Project 1 — First RAG System from Scratch")
    print(f"  Embed: {EMBED_MODEL}  |  LLM: {LLM_MODEL}")
    print("  No PyTorch. No ChromaDB. Pure Python + NumPy.")
    print("=" * 60 + "\n")

    # Build knowledge base
    chunks, matrix = build_store(DOCUMENTS)

    # Test queries
    for q in [
        "What is RAG and why does it matter?",
        "How does Ollama support embeddings?",
        "What is the difference between machine learning and deep learning?",
    ]:
        rag(q, chunks, matrix)

    # Interactive
    print("\n" + "=" * 60)
    print("Interactive mode — ask anything (type 'quit' to exit)")
    print("=" * 60)
    while True:
        q = input("\nYour question: ").strip()
        if q.lower() in ("quit", "exit", "q", "bye", "/bye"):
            print("Goodbye!")
            break
        if q:
            rag(q, chunks, matrix)
