"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           DocuMind — Demo Seed Script                                        ║
║           Phase 6 / Project 06 Capstone — Agentic AI Learning Roadmap       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Run AFTER `docker compose up --build` to populate the system with:          ║
║    • 2 demo users  (admin/admin123, user1/user123)                           ║
║    • 3 sample documents about AI topics                                      ║
║    • 5 sample queries with printed results                                   ║
║                                                                              ║
║  Usage:                                                                      ║
║    python demo/seed_data.py                                                  ║
║    python demo/seed_data.py --url http://localhost:8000                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Sample documents — written inline, no external files needed
# ─────────────────────────────────────────────────────────────────────────────

DOCUMENTS = [
    {
        "filename": "intro_to_rag.txt",
        "content": """\
Introduction to Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation (RAG) is an AI framework that enhances large
language model (LLM) responses by incorporating relevant information retrieved
from an external knowledge base. Instead of relying solely on the LLM's
parametric knowledge (information baked into model weights during training),
RAG dynamically fetches supporting documents at inference time.

How RAG Works
-------------
1. Indexing: Documents are chunked into smaller passages and converted into
   dense vector embeddings using an embedding model (e.g., nomic-embed-text,
   text-embedding-ada-002). These vectors are stored in a vector database.

2. Retrieval: When a user submits a query, the query is also embedded. A
   similarity search (commonly cosine similarity) finds the top-k most
   relevant passages from the vector store.

3. Generation: The retrieved passages are injected into the LLM's prompt as
   context. The LLM then generates an answer grounded in this context rather
   than relying on training-time knowledge alone.

Key Benefits
------------
- Reduces hallucinations by anchoring answers to real documents.
- Keeps knowledge current without expensive model retraining.
- Provides citations so users can verify information.
- Works with any LLM, including locally-hosted models like Llama and Gemma.

Common Embedding Models
-----------------------
- nomic-embed-text: Open-source, high-quality, runs locally via Ollama.
- text-embedding-3-small: OpenAI's cost-efficient embedding model.
- sentence-transformers/all-MiniLM-L6-v2: Popular open-source alternative.

Vector Databases
----------------
Popular choices include ChromaDB (local, embedded), Qdrant (production-grade,
self-hostable), Pinecone (managed cloud), and FAISS (Facebook AI Research,
in-memory). DocuMind uses numpy-based in-memory cosine similarity for
simplicity and zero external dependencies.

RAG vs Fine-tuning
------------------
Fine-tuning updates model weights with new data—expensive and static.
RAG retrieves at inference time—cheap to update (just re-index documents)
and more transparent. For enterprise document Q&A, RAG is almost always the
better choice.
""",
    },
    {
        "filename": "agentic_ai_overview.txt",
        "content": """\
Agentic AI: From Chatbots to Autonomous Agents

Traditional AI assistants are reactive: a user asks, the model answers.
Agentic AI systems go further—they plan, use tools, remember context across
turns, and loop until a goal is achieved.

Core Components of an AI Agent
-------------------------------
1. LLM Brain: The reasoning engine. Modern agents use frontier models
   (GPT-4o, Claude 3.5, Gemini 1.5) or capable open-source models
   (Llama 3, Gemma 2, Mistral).

2. Tools: Functions the agent can call—web search, code execution, database
   queries, file operations, API calls. Tool use lets agents act, not just talk.

3. Memory:
   - Short-term: conversation context window.
   - Long-term: vector databases storing past interactions or knowledge.
   - Semantic: RAG retrieval from curated document stores.

4. Planning: Agents decompose complex goals into subtasks. Frameworks like
   LangGraph model this as a directed graph where nodes are agent actions and
   edges represent transitions or conditions.

Multi-Agent Systems
-------------------
Complex tasks benefit from specialised agents that collaborate:
- Orchestrator agent: breaks the task into subtasks, assigns to specialists.
- Research agent: searches the web or documents for information.
- Code agent: writes and executes code.
- Critic agent: reviews and improves other agents' outputs.

CrewAI and LangGraph are popular frameworks for building multi-agent systems.

Agent Frameworks Overview
--------------------------
- LangGraph: Graph-based state machine for agent workflows. Excellent for
  complex multi-step pipelines with conditional routing and loops.
- CrewAI: Role-based framework where agents have personas and collaborate
  like a work crew.
- AutoGen (Microsoft): Conversational agents that can chat with each other
  to solve tasks.
- Semantic Kernel (Microsoft): Enterprise-focused SDK for integrating LLMs
  into existing applications.

Challenges in Agentic AI
-------------------------
- Reliability: Agents can go off-track, especially with weak LLMs.
- Latency: Multi-step pipelines add up; each LLM call takes time.
- Cost: Multiple LLM calls per task multiply API costs.
- Safety: Agents with tool access can cause real-world side effects.
- Observability: Debugging multi-agent systems requires good tracing (LangSmith).
""",
    },
    {
        "filename": "local_llm_deployment.txt",
        "content": """\
Running Large Language Models Locally with Ollama

Ollama is an open-source tool that makes running LLMs on consumer hardware
as simple as running a Docker container. It manages model downloads, GGUF
quantization, GPU acceleration, and exposes an OpenAI-compatible REST API.

Installation
------------
macOS/Linux:  curl -fsSL https://ollama.ai/install.sh | sh
Windows:      Download installer from https://ollama.ai

Quick Start
-----------
  ollama run gemma3:4b          # Start chatting with Gemma 3 4B
  ollama pull nomic-embed-text  # Download embedding model
  ollama list                   # Show downloaded models
  ollama serve                  # Start API server (default: port 11434)

Ollama REST API
---------------
Ollama is OpenAI-compatible, meaning you can use the OpenAI Python SDK
by changing the base_url:

  from openai import OpenAI
  client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
  response = client.chat.completions.create(model="gemma3:4b", ...)

For embeddings:
  POST http://localhost:11434/api/embeddings
  {"model": "nomic-embed-text", "prompt": "Hello world"}

Recommended Models (as of 2025)
---------------------------------
General chat (4-8 GB VRAM):
  - gemma3:4b       (Google, excellent reasoning, 4B params)
  - llama3.2:3b     (Meta, fast, good for tool use)
  - phi3:mini       (Microsoft, efficient)

General chat (16+ GB VRAM):
  - gemma3:27b      (Google, near-frontier quality)
  - llama3.3:70b    (Meta, state of the art open source)
  - qwen2.5:32b     (Alibaba, great code + reasoning)

Embedding models:
  - nomic-embed-text  (768-dim, excellent quality, free)
  - mxbai-embed-large (1024-dim, top open-source performer)

Hardware Requirements
---------------------
Running models in RAM (CPU only):
  - 4B model:  ~4 GB RAM, slow but works on any laptop
  - 8B model:  ~8 GB RAM

With GPU acceleration (much faster):
  - NVIDIA: CUDA is auto-detected by Ollama
  - Apple Silicon: Metal GPU is used automatically
  - AMD: ROCm support available on Linux

Docker Deployment
-----------------
  # Run Ollama in Docker (CPU)
  docker run -d -p 11434:11434 --name ollama ollama/ollama

  # Run with NVIDIA GPU
  docker run -d --gpus=all -p 11434:11434 --name ollama ollama/ollama

  # Pull a model into the running container
  docker exec -it ollama ollama pull gemma3:4b

In a docker-compose setup, other containers can reach Ollama at
http://host.docker.internal:11434 (the extra_hosts mapping is needed on Linux).
""",
    },
]

SAMPLE_QUERIES = [
    "What is RAG and how does it reduce hallucinations?",
    "What are the key components of an AI agent?",
    "How do I run Gemma 3 locally with Ollama?",
    "What is the difference between RAG and fine-tuning?",
    "Which embedding models work best with Ollama?",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class Colors:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    RED    = "\033[91m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"


def info(msg: str) -> None:
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def _wait_for_backend(base_url: str, retries: int = 15, delay: float = 3.0) -> bool:
    """Poll /health until the backend is ready."""
    info(f"Waiting for backend at {base_url}/health …")
    for attempt in range(retries):
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            if r.status_code == 200:
                success("Backend is ready.")
                return True
        except requests.RequestException:
            pass
        time.sleep(delay)
        print(f"  attempt {attempt + 1}/{retries}…", end="\r")
    return False


def _login(base_url: str, username: str, password: str) -> Optional[str]:
    """Return JWT token or None on failure."""
    resp = requests.post(
        f"{base_url}/auth/login",
        data={"username": username, "password": password},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return None


def _create_user(base_url: str, admin_token: str, username: str,
                 password: str, role: str = "user") -> bool:
    resp = requests.post(
        f"{base_url}/admin/users",
        json={"username": username, "password": password, "role": role},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    return resp.status_code == 200


def _upload_document(base_url: str, token: str, filename: str, content: str) -> bool:
    resp = requests.post(
        f"{base_url}/documents/upload",
        files={"file": (filename, content.encode("utf-8"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    if resp.status_code == 200:
        doc = resp.json()
        success(f"Uploaded '{filename}' → {doc['chunk_count']} chunks, id={doc['id'][:8]}…")
        return True
    else:
        error(f"Upload failed for '{filename}': {resp.text[:200]}")
        return False


def _query(base_url: str, token: str, question: str) -> None:
    resp = requests.post(
        f"{base_url}/query",
        json={"question": question},
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    print(f"\n{Colors.BOLD}Q: {question}{Colors.RESET}")
    if resp.status_code == 200:
        body = resp.json()
        print(f"A: {body['answer'][:400]}{'…' if len(body['answer']) > 400 else ''}")
        print(f"   Quality: {body['quality_score']}/10  |  Citations: {len(body['citations'])}")
        for cit in body["citations"]:
            print(f"   - {cit['filename']} (score={cit['score']})")
    else:
        error(f"Query failed: {resp.text[:200]}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="DocuMind demo seed script")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  DocuMind Demo Seed Script{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

    # 1. Wait for backend
    if not _wait_for_backend(base):
        error("Backend did not become ready. Is `docker compose up` running?")
        sys.exit(1)

    # 2. Login as admin (auto-seeded on first startup)
    info("Logging in as admin…")
    admin_token = _login(base, "admin", "admin123")
    if not admin_token:
        error("Could not login as admin. Check backend logs.")
        sys.exit(1)
    success("Admin login successful.")

    # 3. Create demo user
    info("Creating demo user 'user1'…")
    if _create_user(base, admin_token, "user1", "user123"):
        success("Created user1/user123")
    else:
        warn("user1 may already exist — continuing.")

    # 4. Login as user1 to upload documents under that account
    info("Logging in as user1…")
    user_token = _login(base, "user1", "user123")
    if not user_token:
        error("Could not login as user1.")
        sys.exit(1)
    success("user1 login successful.")

    # 5. Upload sample documents
    print()
    info(f"Uploading {len(DOCUMENTS)} sample documents…")
    for doc in DOCUMENTS:
        _upload_document(base, user_token, doc["filename"], doc["content"])
        # Small delay to avoid overwhelming the embedding endpoint
        time.sleep(1)

    # 6. Run sample queries
    print()
    info("Running 5 sample queries…")
    for question in SAMPLE_QUERIES:
        _query(base, user_token, question)
        time.sleep(0.5)

    # 7. Show admin stats
    print()
    info("Fetching admin stats…")
    resp = requests.get(
        f"{base}/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )
    if resp.status_code == 200:
        stats = resp.json()
        print(f"\n{Colors.BOLD}Admin Stats:{Colors.RESET}")
        for key, val in stats.items():
            print(f"  {key}: {val}")

    print(f"\n{Colors.BOLD}{Colors.GREEN}Seed complete!{Colors.RESET}")
    print("Open http://localhost:8501 in your browser to use DocuMind.")
    print("Login: user1 / user123  (or admin / admin123 for the dashboard)\n")


if __name__ == "__main__":
    main()
