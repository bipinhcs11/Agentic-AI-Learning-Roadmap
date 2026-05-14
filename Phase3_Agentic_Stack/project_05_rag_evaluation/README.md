# Project 05 — RAG Evaluation 📊

> **Week 11 · Phase 3 · Agentic Stack**

## What You'll Learn

How to **measure the quality** of your RAG system using LLM-as-Judge —
scoring each answer on Faithfulness, Relevance, and Correctness.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:4b` is pulled
- [ ] `nomic-embed-text` is pulled — **required for this project**
- [ ] Virtual environment is active

---

## How to Run — Step by Step

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2:**
```bash
# Step 1 — Pull the embedding model (one time only, ~274MB)
ollama pull nomic-embed-text

# Step 2 — Activate venv
source ~/Documents/my-ai-project/ai-env/bin/activate

# Step 3 — Navigate to project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase3_Agentic_Stack/project_05_rag_evaluation

# Step 4 — Run the evaluation (no interaction needed — runs automatically)
python rag_evaluation.py
```

This script runs **automatically** through 5 test cases. No typing needed — just wait for results.

---

## What It Tests

The script evaluates answers on 5 questions about these topics:
- Python programming language
- Machine learning types
- What RAG stands for and does
- LangChain framework
- Python programming paradigms

---

## Expected Terminal Output

```
=================================================================
📊 RAG Evaluation — Phase 3, Project 5
=================================================================
Documents: 4 | Test cases: 5
Judge model: gemma3:4b

Step 1: Indexing documents...
  📊 Building vector store... 8 chunks indexed

Step 2: Running test cases...

  Test 1/5: Who created Python and when was it first released?...
  🤖 Generating answer... done
  ⚖️  Scoring... F:0.9 R:0.9 C:0.8

  [... 4 more test cases ...]

=================================================================
📋 EVALUATION REPORT
=================================================================

#   Question                                      Faith  Relev   Corr
-----------------------------------------------------------------
1   Who created Python and when...               0.90   0.90   0.80
2   What are the three main types of ML...       0.85   0.90   0.85
3   What does RAG stand for...                   0.90   0.85   0.80
4   What is LangChain used for...                0.85   0.90   0.85
5   What programming paradigms does Python...    0.90   0.85   0.80
-----------------------------------------------------------------
AVERAGES                                         0.88   0.88   0.82

🎯 Overall Score: 0.86/1.0  (86.0%)
📊 Grade: 🌟 Excellent

💾 Results saved to evaluation_results.json
```

---

## Verification Checklist

- [ ] All 5 test cases complete without crashing
- [ ] `evaluation_results.json` created in this project folder
- [ ] Overall Score is above **0.60 (60%)** — below that means scoring had issues
- [ ] Faithfulness scores are **0.7 or higher** — model staying grounded in context

---

## Understanding the Scores

| Metric | What It Checks | Good Score |
|--------|---------------|-----------|
| **Faithfulness** | Answer only uses the provided context | ≥ 0.80 |
| **Relevance** | Answer addresses the question asked | ≥ 0.80 |
| **Correctness** | Answer matches the expected answer | ≥ 0.70 |

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `nomic-embed-text not found` | Run: `ollama pull nomic-embed-text` |
| All scores are exactly `0.5` | Model struggled to parse judge JSON — defaults to 0.5. Still works for learning. |
| Very slow (more than 10 min) | Switch to 4b model: edit `JUDGE_MODEL = "gemma3:4b"` in the script |
| `JSONDecodeError` during scoring | Fallback score `0.5` is used automatically — this is OK |

---

## Files Created by This Project

- `rag_evaluation.py` — the evaluation script
- `evaluation_results.json` — auto-created with all scores after running

## Status

⏳ Ready to run — make sure `nomic-embed-text` is pulled first!
