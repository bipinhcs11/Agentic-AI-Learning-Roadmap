# Local AI Setup

The default path uses Ollama so the main projects can run without paid API keys.

## Install Ollama

Install Ollama from <https://ollama.com>, then verify it:

```bash
ollama --version
ollama serve
```

Keep `ollama serve` running while you execute projects that call local models.

## Recommended Models

| Use | Model | Command |
|---|---|---|
| Lightweight chat/generation | `gemma3:4b` | `ollama pull gemma3:4b` |
| Embeddings for RAG | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Phase 9 capstone default | `qwen2.5:3b` | `ollama pull qwen2.5:3b` |

Start with smaller models. Larger models can improve answer quality, but they
also increase memory pressure and latency.

## Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The root `requirements.txt` intentionally avoids heavy ML dependencies such as
PyTorch for the shared path. Individual projects may document optional extras.

## Verify The Local API

```bash
python Phase1_Foundations/test_gemma3.py
```

This script expects Ollama to be running and `gemma3:4b` to be available.

## Model Selection Rule Of Thumb

| Machine | Suggested default |
|---|---|
| 8-16 GB RAM | `gemma3:4b`, `qwen2.5:3b` |
| 24-32 GB RAM | Try medium models after the small path works |
| 64 GB+ RAM | Larger local models become practical for demos |

When something fails, first prove the small model path works before changing
framework code.
