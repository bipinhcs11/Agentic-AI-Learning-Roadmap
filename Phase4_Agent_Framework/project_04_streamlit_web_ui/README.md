# Project 04 — Streamlit Web UI 💬

> **Week 14 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build a **real chat web interface** for your local AI —
like ChatGPT but running 100% on your Mac Mini!

## What It Looks Like

A full browser-based chat app with:
- Chat bubbles (user vs AI)
- Model selector dropdown
- Conversation history
- Clear chat button
- Streaming responses (text appears word by word)

## Stack

- **Streamlit** — Python web apps with no HTML/CSS needed
- **Ollama** — local model backend
- **Port 8501** (Streamlit default)

## Install Streamlit

```bash
pip install streamlit --break-system-packages
```

## How to Run

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start the web UI
source ~/Documents/my-ai-project/ai-env/bin/activate
streamlit run streamlit_ui.py

# Browser opens automatically at http://localhost:8501
```

## Features

- 🤖 Select between gemma3:4b and gemma3:27b
- 💬 Full chat history in the session
- 🌊 Streaming responses
- 🗑️ Clear conversation button
- ℹ️ Shows token count and response time

## Status

⏳ Ready — install streamlit first, then run
