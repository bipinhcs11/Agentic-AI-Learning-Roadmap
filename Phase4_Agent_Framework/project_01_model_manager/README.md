# Project 01 — Model Manager 📦

> **Week 13 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

How to programmatically manage your local AI models —
download, list, inspect, and delete them using the Ollama API.

## Concept

Ollama exposes a local REST API at http://localhost:11434.
This project shows you how to control it with Python —
which is exactly how tools like Open WebUI and LM Studio work under the hood.

## What It Does

```bash
python model_manager.py list        # Show all installed models
python model_manager.py info gemma3:4b   # Show model details
python model_manager.py pull nomic-embed-text  # Download a model
python model_manager.py delete <model>   # Remove a model
python model_manager.py test gemma3:4b   # Quick test
```

## Stack

- **API:** Ollama REST API (http://localhost:11434)
- **Libraries:** requests, rich (pretty terminal output)
- **No ML libraries needed**

## Install

```bash
pip install requests rich --break-system-packages
```

## How to Run

```bash
ollama serve
source ~/Documents/my-ai-project/ai-env/bin/activate
python model_manager.py
```

## Status

⏳ Ready to run
