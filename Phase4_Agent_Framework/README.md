# Phase 4 — Build Your Own Agent Framework 🔄

> **Goal:** Build something similar to Ollama / your own agent platform · Weeks 13–16 · IN PROGRESS

## Projects

| # | Project | Concept | Week | Status |
|---|---------|---------|------|--------|
| 01 | [Model Manager](project_01_model_manager/) | Ollama API, model control | 13 | ⏳ Ready |
| 02 | [Inference Server](project_02_inference_server/) | FastAPI wrapper, streaming, logging | 13 | ⏳ Ready |
| 03 | [OpenAI-Compatible API](project_03_openai_compatible_api/) | Drop-in OpenAI replacement | 14 | ⏳ Ready |
| 04 | [Streamlit Web UI](project_04_streamlit_web_ui/) | Browser chat interface | 14 | ⏳ Ready |
| 05 | [Custom Agent Framework](project_05_custom_agent_framework/) | Build your own mini LangChain | 15 | ⏳ Ready |
| 06 | [Full Platform (Capstone)](project_06_full_platform/) | Everything combined | 16 | ⏳ Ready |

## Overview

The final phase — building a custom agent framework from scratch, understanding every layer of the stack.

## Components to Build

| Component | Tech | Complexity |
|-----------|------|------------|
| Model download & management | Python, httpx, tqdm | Medium |
| Local inference server | FastAPI, llama-cpp-python | High |
| REST API (OpenAI compatible) | FastAPI, Pydantic | Medium |
| Web UI | React or Streamlit | Medium |
| Agent orchestration layer | LangChain / custom | High |
| Memory system | ChromaDB + SQLite | Medium |
| Tool/plugin system | Python decorators, FastAPI | High |
| Cloud deployment | Modal → AWS ECS | Medium |

## Status

🔄 All 6 projects are set up — the final phase of your 16-week journey!
