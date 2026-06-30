# Getting Started

Use this when you want the fastest useful win: clone the repo, run a local model,
and build the first RAG pipeline from scratch.

## Prerequisites

- Python 3.11 or newer
- Ollama installed and available as `ollama`
- Git
- Optional later: Docker Desktop for production and capstone projects

## 30-Minute Quick Win

```bash
git clone https://github.com/bipinhcs11/Agentic-AI-Learning-Roadmap.git
cd Agentic-AI-Learning-Roadmap

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

ollama pull gemma3:4b
ollama pull nomic-embed-text
ollama serve
```

In another terminal:

```bash
cd Agentic-AI-Learning-Roadmap
source .venv/bin/activate
python Phase2_RAG_Systems/project_01_first_rag/rag_from_scratch.py
```

Expected shape:

```text
Project 1 - First RAG System from Scratch
Chunking documents...
Embedding via Ollama (nomic-embed-text)...
Vector store ready: (..., ...)

Query: What is RAG and why does it matter?
Top match: Retrieval-Augmented Generation (RAG) enhances LLM responses...
Answer:
...
```

After the scripted questions finish, the program enters interactive mode. Type
`quit` to exit.

## What To Do Next

| Goal | Next step |
|---|---|
| Understand RAG deeply | Continue through `Phase2_RAG_Systems/` in order |
| Build agent services | Jump to `Phase3_Agentic_Stack/` after Project 01 |
| Learn production packaging | Go to `Phase6_Production_Enterprise/` |
| Explore MCP | Go to `Phase9_Dynamic_Agentic_RAG_MCP/` |
| Explore Google ADK | Go to `Phase10_Google_ADK_Series/` |

## Local Safety Notes

- The core path runs locally through Ollama.
- Cloud examples are isolated to phases that explicitly teach deployment.
- Benefits, billing, customer, HR, and financial examples use fictional mock data.
