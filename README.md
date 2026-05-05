# 🤖 Agentic AI Learning Roadmap

> **From Zero AI Knowledge to Building Your Own Agent Framework**
> Mac Mini M4 · Ollama · Modal · AWS · LangChain · ChromaDB · FastAPI

---

## 🖥️ My Setup

| Component | Spec |
|-----------|------|
| Machine | Mac Mini M4 |
| RAM | 32 GB unified memory |
| Storage | 512 GB SSD |
| Local LLM | Ollama + Gemma3:27b |
| Cloud | Modal (learning) → AWS (production) |

---

## 📍 Roadmap Progress

| Phase | Goal | Weeks | Status |
|-------|------|-------|--------|
| [Phase 1 — Foundation](./Phase1_Foundation/) | Ollama, Gemma3, Python, VS Code, virtual env | 1–2 | ✅ Complete |
| [Phase 2 — RAG Projects](./Phase2_RAG_Projects/) | 10 hands-on RAG projects | 3–6 | 🔄 In Progress |
| [Phase 3 — Agentic Stack](./Phase3_Agentic_Stack/) | LangChain, ChromaDB, FastAPI, Modal deploy | 7–12 | ⏳ Pending |
| [Phase 4 — Agent Framework](./Phase4_Agent_Framework/) | Build your own agent platform | 13–16 | ⏳ Pending |

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/Agentic-AI-Learning-Roadmap.git
cd Agentic-AI-Learning-Roadmap

# Install Ollama and pull models
brew install ollama
ollama pull gemma3:27b
ollama pull nomic-embed-text

# Set up Python environment
python3.11 -m venv ai-env
source ai-env/bin/activate
pip install -r requirements.txt

# Start Ollama server (keep this running)
ollama serve

# Test your setup
python Phase1_Foundation/test_gemma3.py
```

---

## 📦 Tech Stack

### Local AI
- **[Ollama](https://ollama.com)** — Run LLMs locally (zero cost, 100% private)
- **Gemma3:27b** — Near GPT-4 quality model from Google DeepMind
- **nomic-embed-text** — Lightweight embedding model for RAG

### Python Libraries
- **openai** — OpenAI-compatible client (also works with Ollama)
- **langchain** — LLM orchestration and agent framework
- **chromadb** — Local vector database for RAG
- **fastapi** — Web API framework (portable to any cloud)
- **uvicorn** — ASGI server for FastAPI

### Cloud (Future)
- **Modal** — Serverless GPU deployment ($30 free credits/month)
- **AWS** — Production deployment target (ECS, Lambda, SageMaker)

---

## 📂 Repo Structure

```
Agentic-AI-Learning-Roadmap/
├── README.md                          ← You are here
├── requirements.txt                   ← All Python dependencies
├── .gitignore
│
├── Phase1_Foundation/                 ← ✅ Complete
│   ├── README.md
│   ├── test_gemma3.py                 ← Verify your setup
│   └── docs/
│       └── installation_guide.md
│
├── Phase2_RAG_Projects/               ← 🔄 In Progress
│   ├── README.md
│   ├── project_01_first_rag/          ← ✅ Built
│   ├── project_02_ibm_rag/            ← ⏳ Next
│   ├── project_03_graphrag/
│   ├── project_04_multi_doc_rag/
│   ├── project_05_agentic_rag/
│   ├── project_06_langchain_rag/
│   ├── project_07_document_analysis/
│   ├── project_08_multimodal_rag/
│   ├── project_09_research_agent/
│   └── project_10_realtime_assistant/
│
├── Phase3_Agentic_Stack/              ← ⏳ Weeks 7–12
│   └── README.md
│
└── Phase4_Agent_Framework/            ← ⏳ Weeks 13–16
    └── README.md
```

---

## 🔑 Key Concepts

**RAG (Retrieval-Augmented Generation)** — Give your LLM access to your own documents without retraining. Retrieve relevant chunks → feed to LLM → get grounded answers.

**Agentic AI** — AI that takes autonomous actions: uses tools, makes decisions, calls APIs, remembers context across sessions.

**Local-first** — All development runs on the Mac Mini M4 with Ollama. Zero API costs. Move to cloud only when needed.

---

## 📝 License

MIT — learn freely, build freely.
