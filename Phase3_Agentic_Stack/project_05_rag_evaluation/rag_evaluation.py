# ═══════════════════════════════════════════════════════════════
# Project 05 — RAG Evaluation (LLM-as-Judge)
# Phase 3 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Evaluates a RAG system using another LLM as the "judge".
#   This is how real companies measure RAG quality (no PyTorch needed).
#
# CONCEPT: LLM-as-Judge
#   Instead of fancy metrics libraries, we ask an LLM:
#   "Score this answer 0-10 for accuracy/relevance/faithfulness"
#   This works surprisingly well and needs no extra libraries!
#
# HOW TO RUN:
#   1. ollama serve  (needs nomic-embed-text + gemma3:4b)
#   2. ollama pull nomic-embed-text  (if not already pulled)
#   3. source ~/Documents/my-ai-project/ai-env/bin/activate
#   4. python rag_evaluation.py
# ═══════════════════════════════════════════════════════════════

import json
import math
import re
from dataclasses import dataclass, field
from typing import List
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
JUDGE_MODEL = "gemma3:4b"
EMBED_MODEL = "nomic-embed-text"

# ═══════════════════════════════════════════════════════════════
# MINI RAG SYSTEM (same approach as Phase 2)
# ═══════════════════════════════════════════════════════════════

def get_embedding(text: str) -> list:
    """Get text embedding via Ollama nomic-embed-text."""
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(x ** 2 for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def build_vector_store(documents: list) -> list:
    """Embed all document chunks."""
    print("  📊 Building vector store...", end="", flush=True)
    store = []
    for doc_id, text in enumerate(documents):
        chunks = chunk_text(text)
        for chunk_id, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            store.append({"id": f"doc{doc_id}_chunk{chunk_id}", "text": chunk, "embedding": embedding})
    print(f" {len(store)} chunks indexed")
    return store


def retrieve(query: str, store: list, top_k: int = 3) -> list:
    """Find most relevant chunks for a query."""
    query_emb = get_embedding(query)
    scored = [(cosine_similarity(query_emb, item["embedding"]), item["text"]) for item in store]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]


def generate_answer(question: str, context_chunks: list) -> str:
    """Generate an answer using retrieved context."""
    context = "\n\n".join(context_chunks)
    messages = [
        {"role": "system", "content": "Answer the question using ONLY the provided context. Be concise."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"}
    ]
    resp = client.chat.completions.create(model=JUDGE_MODEL, messages=messages, temperature=0.1)
    return resp.choices[0].message.content


# ═══════════════════════════════════════════════════════════════
# LLM-AS-JUDGE EVALUATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class EvalResult:
    question: str
    expected: str
    generated: str
    context: List[str]
    faithfulness: float = 0.0
    relevance: float = 0.0
    correctness: float = 0.0


def score_with_llm(question: str, answer: str, context: str, expected: str) -> dict:
    """Use the LLM to judge answer quality. Returns scores 0-10."""
    prompt = f"""You are an expert evaluator for AI question-answering systems.
Score the GENERATED ANSWER on three dimensions (0-10 each):

QUESTION: {question}
CONTEXT: {context[:800]}
EXPECTED ANSWER: {expected}
GENERATED ANSWER: {answer}

Score each dimension:
1. FAITHFULNESS (0-10): Does the answer only use information from the context?
   10 = only uses context | 0 = makes up facts not in context

2. RELEVANCE (0-10): Does the answer address the question asked?
   10 = perfectly answers the question | 0 = completely off-topic

3. CORRECTNESS (0-10): How close is it to the expected answer?
   10 = matches expected answer | 0 = completely wrong

Respond in JSON format ONLY:
{{"faithfulness": 8, "relevance": 9, "correctness": 7, "explanation": "brief reason"}}
"""
    try:
        resp = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        text = resp.choices[0].message.content
        # Extract JSON from response
        match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if match:
            scores = json.loads(match.group())
            return {
                "faithfulness": min(10, max(0, float(scores.get("faithfulness", 5)))) / 10,
                "relevance": min(10, max(0, float(scores.get("relevance", 5)))) / 10,
                "correctness": min(10, max(0, float(scores.get("correctness", 5)))) / 10,
                "explanation": scores.get("explanation", "")
            }
    except Exception as e:
        print(f"    ⚠️  Scoring error: {e}")
    # Fallback scores
    return {"faithfulness": 0.5, "relevance": 0.5, "correctness": 0.5, "explanation": "could not parse"}


# ═══════════════════════════════════════════════════════════════
# TEST DATASET
# ═══════════════════════════════════════════════════════════════

# Knowledge base documents
DOCUMENTS = [
    """Python is a high-level, general-purpose programming language. Its design philosophy
    emphasizes code readability with the use of significant indentation. Python is dynamically
    typed and garbage-collected. It supports multiple programming paradigms, including structured,
    object-oriented and functional programming. Python was created by Guido van Rossum and first
    released in 1991. Python consistently ranks as one of the most popular programming languages.""",

    """Machine learning is a subset of artificial intelligence (AI) that provides systems the ability
    to automatically learn and improve from experience without being explicitly programmed. Machine
    learning focuses on the development of computer programs that can access data and use it to learn
    for themselves. The process begins with observations or data, such as examples, direct experience,
    or instruction. There are three main types: supervised learning, unsupervised learning, and
    reinforcement learning.""",

    """RAG stands for Retrieval-Augmented Generation. It is a technique that combines information
    retrieval with text generation. In a RAG system, when a question is asked, relevant documents
    are first retrieved from a knowledge base, then those documents are provided as context to a
    language model to generate an answer. RAG helps reduce hallucinations and keeps AI answers
    grounded in factual documents. It is widely used in enterprise AI applications.""",

    """LangChain is a framework for developing applications powered by language models. It provides
    tools and components for building RAG systems, AI agents, and chains of LLM calls. LangChain
    supports multiple LLM providers including OpenAI, Anthropic, and local models via Ollama.
    Key components include document loaders, text splitters, vector stores, retrievers, and chains.
    LangChain was created in 2022 and became one of the most popular AI development frameworks.""",
]

# Test questions with expected answers
TEST_CASES = [
    {
        "question": "Who created Python and when was it first released?",
        "expected": "Python was created by Guido van Rossum and first released in 1991."
    },
    {
        "question": "What are the three main types of machine learning?",
        "expected": "The three main types are supervised learning, unsupervised learning, and reinforcement learning."
    },
    {
        "question": "What does RAG stand for and what problem does it solve?",
        "expected": "RAG stands for Retrieval-Augmented Generation. It helps reduce hallucinations and keeps AI answers grounded in factual documents."
    },
    {
        "question": "What is LangChain used for?",
        "expected": "LangChain is a framework for developing applications powered by language models, including RAG systems and AI agents."
    },
    {
        "question": "What programming paradigms does Python support?",
        "expected": "Python supports structured, object-oriented and functional programming."
    },
]


# ═══════════════════════════════════════════════════════════════
# RUN EVALUATION
# ═══════════════════════════════════════════════════════════════

def run_evaluation():
    print("=" * 65)
    print("📊 RAG Evaluation — Phase 3, Project 5")
    print("=" * 65)
    print(f"Documents: {len(DOCUMENTS)} | Test cases: {len(TEST_CASES)}")
    print(f"Judge model: {JUDGE_MODEL}")
    print()

    # Step 1: Build vector store
    print("Step 1: Indexing documents...")
    vector_store = build_vector_store(DOCUMENTS)
    print()

    # Step 2: Run each test case
    print("Step 2: Running test cases...")
    results = []

    for i, test in enumerate(TEST_CASES):
        question = test["question"]
        expected = test["expected"]

        print(f"\n  Test {i+1}/{len(TEST_CASES)}: {question[:55]}...")

        # Retrieve context
        context_chunks = retrieve(question, vector_store, top_k=2)
        context_str = "\n".join(context_chunks)

        # Generate answer
        print("  🤖 Generating answer...", end="", flush=True)
        generated = generate_answer(question, context_chunks)
        print(" done")

        # Score with LLM judge
        print("  ⚖️  Scoring...", end="", flush=True)
        scores = score_with_llm(question, generated, context_str, expected)
        print(f" F:{scores['faithfulness']:.1f} R:{scores['relevance']:.1f} C:{scores['correctness']:.1f}")

        result = EvalResult(
            question=question,
            expected=expected,
            generated=generated,
            context=context_chunks,
            faithfulness=scores["faithfulness"],
            relevance=scores["relevance"],
            correctness=scores["correctness"],
        )
        results.append(result)

    # Step 3: Print report
    print("\n" + "=" * 65)
    print("📋 EVALUATION REPORT")
    print("=" * 65)

    print(f"\n{'#':<3} {'Question':<45} {'Faith':>6} {'Relev':>6} {'Corr':>6}")
    print("-" * 65)

    for i, r in enumerate(results):
        q_short = r.question[:44]
        print(f"{i+1:<3} {q_short:<45} {r.faithfulness:>6.2f} {r.relevance:>6.2f} {r.correctness:>6.2f}")

    # Averages
    avg_faith = sum(r.faithfulness for r in results) / len(results)
    avg_relev = sum(r.relevance for r in results) / len(results)
    avg_corr  = sum(r.correctness for r in results) / len(results)
    avg_overall = (avg_faith + avg_relev + avg_corr) / 3

    print("-" * 65)
    print(f"{'AVERAGES':<48} {avg_faith:>6.2f} {avg_relev:>6.2f} {avg_corr:>6.2f}")
    print(f"\n🎯 Overall Score: {avg_overall:.2f}/1.0  ({avg_overall*100:.1f}%)")

    # Grade
    if avg_overall >= 0.85:
        grade = "🌟 Excellent"
    elif avg_overall >= 0.70:
        grade = "✅ Good"
    elif avg_overall >= 0.55:
        grade = "⚠️  Needs improvement"
    else:
        grade = "❌ Poor — check your RAG pipeline"
    print(f"📊 Grade: {grade}")

    # Show one detailed example
    print("\n" + "=" * 65)
    print("📝 SAMPLE DETAIL (Question 1):")
    r = results[0]
    print(f"Q:        {r.question}")
    print(f"Expected: {r.expected}")
    print(f"Got:      {r.generated[:200]}...")
    print(f"Scores → Faithfulness: {r.faithfulness:.2f} | Relevance: {r.relevance:.2f} | Correctness: {r.correctness:.2f}")
    print()

    # Save results to JSON
    output_file = os.path.join(os.path.dirname(__file__), "evaluation_results.json")
    with open(output_file, "w") as f:
        json.dump([{
            "question": r.question,
            "expected": r.expected,
            "generated": r.generated,
            "faithfulness": r.faithfulness,
            "relevance": r.relevance,
            "correctness": r.correctness,
        } for r in results], f, indent=2)
    print(f"💾 Results saved to {output_file}")


import os
if __name__ == "__main__":
    run_evaluation()
