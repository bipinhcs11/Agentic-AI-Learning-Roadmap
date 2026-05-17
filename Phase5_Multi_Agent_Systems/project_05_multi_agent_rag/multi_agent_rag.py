# ═══════════════════════════════════════════════════════════════
# Project 05 — Multi-Agent RAG with Domain Routing
# Phase 5 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   A router agent reads your question and decides which specialist
#   RAG agent to invoke. Each specialist has its own document set
#   and retrieval strategy.
#
# AGENTS:
#   [Router]     → reads question, picks the right specialist
#   [Tech RAG]   → answers from technology documentation
#   [Business RAG] → answers from business/strategy documents
#   [General RAG] → fallback for anything else
#
# KEY CONCEPTS:
#   - Domain routing: classify before you retrieve
#   - Each RAG agent has its own vector store (simulated here)
#   - Combining Phase 2 RAG skills with Phase 5 multi-agent
#   - In production: swap simulated docs for real ChromaDB/Qdrant
#
# ARCHITECTURE:
#
#   Question → [Router Agent] → domain classification
#                  ↓
#       ┌──────────┴──────────────┐
#   [Tech RAG]  [Business RAG]  [General RAG]
#       ↓              ↓               ↓
#   Retrieve + Answer from domain-specific docs
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python multi_agent_rag.py
# ═══════════════════════════════════════════════════════════════

import json
import math
import re
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# ─────────────────────────────────────────────────────────────
# LLM + Embeddings pointing at Ollama
# ─────────────────────────────────────────────────────────────

llm = ChatOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="gemma3:4b",
    temperature=0.3,
)

# Use Ollama's nomic-embed-text for embeddings (RAM-safe, no GPU needed)
embeddings = OpenAIEmbeddings(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model="nomic-embed-text",
)


# ═══════════════════════════════════════════════════════════════
# STEP 1: SIMULATED DOMAIN DOCUMENT STORES
#
# In production these would be real ChromaDB/Qdrant collections.
# Here we simulate them with in-memory document lists and
# numpy-based cosine similarity — same approach as Phase 2.
#
# Each domain has its own document set and retrieval logic.
# ═══════════════════════════════════════════════════════════════

# Domain knowledge bases — replace with real files in production
TECH_DOCS = [
    {"id": "t1", "content": "LangGraph is a framework for building stateful multi-actor applications with LLMs. It uses a graph structure where nodes are agents and edges define the flow of information between them. Key features: StateGraph, conditional edges, human-in-the-loop, streaming."},
    {"id": "t2", "content": "Ollama is a tool for running large language models locally. It provides an OpenAI-compatible API at http://localhost:11434/v1. Supported models include Gemma3, Llama3, Mistral, Phi3. Commands: ollama serve, ollama pull <model>, ollama list."},
    {"id": "t3", "content": "Vector databases store high-dimensional embeddings for semantic search. ChromaDB is easy to set up locally. Qdrant supports production workloads with filtering. Pinecone is a managed cloud service. Key operations: upsert embeddings, query by cosine similarity, filter by metadata."},
    {"id": "t4", "content": "RAG (Retrieval-Augmented Generation) combines vector search with LLM generation. The pipeline: chunk documents → embed chunks → store in vector DB → retrieve relevant chunks → augment LLM prompt. This reduces hallucination and grounds answers in your data."},
    {"id": "t5", "content": "FastAPI is a Python web framework for building APIs. It uses Pydantic for validation, Uvicorn as ASGI server. Key patterns: dependency injection, async endpoints, OpenAPI docs auto-generated at /docs. Install: pip install fastapi uvicorn."},
]

BUSINESS_DOCS = [
    {"id": "b1", "content": "The AI market is projected to reach $1.8 trillion by 2030, growing at 37% CAGR. Key drivers: enterprise automation, generative AI adoption, edge AI deployment. Major players: Microsoft, Google, Amazon, Meta, Anthropic, OpenAI."},
    {"id": "b2", "content": "Enterprise AI adoption: 77% of companies are using or exploring AI in 2025. Top use cases: customer service automation (42%), code assistance (38%), document processing (31%). Biggest barriers: data quality, security concerns, talent shortage."},
    {"id": "b3", "content": "AI ROI metrics: companies report 25-40% productivity gains in software development with AI tools. Customer service automation reduces costs by 30-50%. Key success factors: clear use case definition, quality training data, change management."},
    {"id": "b4", "content": "Competitive moats in AI: data advantage (proprietary datasets), distribution (Microsoft's Office integration), compute efficiency (Apple Silicon), open source community (Meta's Llama). Startups compete on specialization and fine-tuning."},
    {"id": "b5", "content": "AI pricing models: per-token (OpenAI/Anthropic), subscription (GitHub Copilot $10/month), enterprise contracts (custom). Infrastructure costs: GPU cloud $2-8/hour, or local inference on Apple M4 at near-zero marginal cost."},
]

GENERAL_DOCS = [
    {"id": "g1", "content": "Machine learning is a subset of AI where models learn patterns from data. Types: supervised learning (labeled data), unsupervised learning (clustering), reinforcement learning (reward signals). Common algorithms: neural networks, random forests, gradient boosting."},
    {"id": "g2", "content": "Python is the dominant language for AI/ML. Key libraries: NumPy (arrays), Pandas (data), scikit-learn (classical ML), PyTorch/TensorFlow (deep learning), Hugging Face (LLMs). Package management: pip, conda, poetry, uv."},
    {"id": "g3", "content": "Prompt engineering techniques: zero-shot (just ask), few-shot (give examples), chain-of-thought (ask to think step by step), ReAct (reason then act), structured output (ask for JSON). Temperature controls creativity vs. consistency."},
]

# Pre-compute embeddings for all documents at startup
_DOC_EMBEDDINGS: dict[str, list] = {}


def cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x**2 for x in a))
    norm_b = math.sqrt(sum(x**2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_documents(docs: list[dict], domain: str) -> None:
    """Embed all documents for a domain and cache them."""
    print(f"  [SETUP] Embedding {len(docs)} {domain} documents...")
    texts = [d["content"] for d in docs]
    embs = embeddings.embed_documents(texts)
    for doc, emb in zip(docs, embs):
        _DOC_EMBEDDINGS[f"{domain}:{doc['id']}"] = {"content": doc["content"], "embedding": emb}


def retrieve(query: str, domain: str, top_k: int = 2) -> list[str]:
    """Retrieve top-k documents from a domain using cosine similarity."""
    query_emb = embeddings.embed_query(query)
    domain_docs = {k: v for k, v in _DOC_EMBEDDINGS.items() if k.startswith(f"{domain}:")}

    scored = [
        (cosine_similarity(query_emb, v["embedding"]), v["content"])
        for v in domain_docs.values()
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [content for _, content in scored[:top_k]]


def setup_vector_stores():
    """Initialize all domain vector stores."""
    print("\n[SETUP] Building domain vector stores...")
    embed_documents(TECH_DOCS, "tech")
    embed_documents(BUSINESS_DOCS, "business")
    embed_documents(GENERAL_DOCS, "general")
    print("[SETUP] All vector stores ready\n")


# ═══════════════════════════════════════════════════════════════
# STEP 2: STATE
# ═══════════════════════════════════════════════════════════════

class RAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    question: str
    domain: str          # "tech", "business", or "general"
    retrieved_docs: list[str]
    answer: str
    next: str


# ═══════════════════════════════════════════════════════════════
# STEP 3: AGENT NODES
# ═══════════════════════════════════════════════════════════════

def router_node(state: RAGState) -> RAGState:
    """Classify the question into a domain."""
    question = state["question"]
    print(f"\n[ROUTER] Classifying: {question[:60]}...")

    response = llm.invoke([
        SystemMessage(content=(
            "You classify questions into exactly one domain.\n"
            "Domains:\n"
            "  tech     = programming, AI frameworks, APIs, databases, DevOps, models\n"
            "  business = markets, revenue, enterprise, strategy, pricing, competition\n"
            "  general  = ML concepts, Python basics, prompting, general AI knowledge\n\n"
            "Respond with EXACTLY one word: tech, business, or general"
        )),
        HumanMessage(content=f"Classify this question: {question}"),
    ])

    domain = response.content.strip().lower()
    if domain not in ("tech", "business", "general"):
        domain = "general"  # safe fallback

    print(f"[ROUTER] Domain → {domain}")

    return {
        "domain": domain,
        "next": f"{domain}_rag",
        "messages": [AIMessage(content=f"[Router] Routing to {domain} RAG agent")],
    }


def tech_rag_node(state: RAGState) -> RAGState:
    """RAG agent for technical questions."""
    return _rag_answer(state, domain="tech", persona="technical documentation expert")


def business_rag_node(state: RAGState) -> RAGState:
    """RAG agent for business/market questions."""
    return _rag_answer(state, domain="business", persona="business intelligence analyst")


def general_rag_node(state: RAGState) -> RAGState:
    """RAG agent for general AI/ML questions."""
    return _rag_answer(state, domain="general", persona="AI educator")


def _rag_answer(state: RAGState, domain: str, persona: str) -> RAGState:
    """Core RAG logic: retrieve + generate answer."""
    question = state["question"]
    print(f"\n[{domain.upper()} RAG] Retrieving relevant documents...")

    docs = retrieve(question, domain, top_k=2)
    context = "\n\n---\n\n".join(docs)

    print(f"[{domain.upper()} RAG] Retrieved {len(docs)} docs. Generating answer...")

    response = llm.invoke([
        SystemMessage(content=(
            f"You are a {persona}. Answer questions using ONLY the provided context. "
            "If the context doesn't contain the answer, say so. "
            "Be concise and cite specific facts from the context."
        )),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"),
    ])

    answer = response.content
    print(f"[{domain.upper()} RAG] Answer ready ({len(answer)} chars)")

    return {
        "retrieved_docs": docs,
        "answer": answer,
        "next": "FINISH",
        "messages": [AIMessage(content=f"[{domain.capitalize()} RAG] Answer generated")],
    }


# ═══════════════════════════════════════════════════════════════
# STEP 4: ROUTING
# ═══════════════════════════════════════════════════════════════

def route_from_router(state: RAGState) -> Literal["tech_rag", "business_rag", "general_rag"]:
    return state.get("next", "general_rag")


# ═══════════════════════════════════════════════════════════════
# STEP 5: GRAPH
# ═══════════════════════════════════════════════════════════════

def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("router",       router_node)
    graph.add_node("tech_rag",     tech_rag_node)
    graph.add_node("business_rag", business_rag_node)
    graph.add_node("general_rag",  general_rag_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        route_from_router,
        {"tech_rag": "tech_rag", "business_rag": "business_rag", "general_rag": "general_rag"}
    )
    graph.add_edge("tech_rag",     END)
    graph.add_edge("business_rag", END)
    graph.add_edge("general_rag",  END)

    return graph.compile()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "═"*60)
    print("  PHASE 5 — PROJECT 05: Multi-Agent RAG with Domain Routing")
    print("═"*60)
    print("\n  Router picks the right specialist RAG agent per question")
    print("  Each domain has its own document set and retrieval logic")

    # Setup vector stores once
    setup_vector_stores()

    app = build_rag_graph()

    test_questions = [
        "How does LangGraph handle state in multi-agent systems?",
        "What is the enterprise AI market size and growth rate?",
        "What is the difference between zero-shot and few-shot prompting?",
    ]

    print("\n  Sample Questions (tests all 3 domains):")
    for i, q in enumerate(test_questions, 1):
        print(f"  [{i}] {q}")
    print("  [4] Ask your own question")
    print("  [5] Run all 3 demo questions")

    choice = input("\n  Choose (1-5): ").strip()

    if choice == "5":
        questions = test_questions
    elif choice in ("1", "2", "3"):
        questions = [test_questions[int(choice) - 1]]
    elif choice == "4":
        questions = [input("  Your question: ").strip()]
    else:
        questions = [test_questions[0]]

    for question in questions:
        print(f"\n{'─'*60}")
        print(f"  QUESTION: {question}")
        print(f"{'─'*60}")

        state = app.invoke({
            "messages": [HumanMessage(content=question)],
            "question": question,
            "domain": "",
            "retrieved_docs": [],
            "answer": "",
            "next": "",
        }, config={"recursion_limit": 10})

        print(f"\n  DOMAIN: {state['domain'].upper()}")
        print(f"  RETRIEVED: {len(state['retrieved_docs'])} documents")
        print(f"\n  ANSWER:\n{state['answer']}")

    print("\n" + "═"*60)
    print("  Multi-Agent RAG complete!")
    print("  Next: swap simulated docs for real ChromaDB/Qdrant collections")
    print("═"*60)


if __name__ == "__main__":
    main()
