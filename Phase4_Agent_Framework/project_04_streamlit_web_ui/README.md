# Project 04 — Streamlit Web UI 💬

> **Week 14 · Phase 4 · Build Your Own Agent Framework**

## What You'll Learn

Build a **real chat web interface** for your local AI —
like ChatGPT, but running 100% on your Mac Mini with no cloud, no API key, no cost.

---

## Prerequisites

- [ ] Ollama is running (`ollama serve`)
- [ ] `gemma3:27b` is pulled
- [ ] Virtual environment is active
- [ ] `streamlit` installed (see Install step below)

---

## Install Streamlit (one time only)

```bash
pip install streamlit --break-system-packages
```

---

## How to Run — Step by Step

**Terminal 1:**
```bash
ollama serve
```

**Terminal 2:**
```bash
# Activate venv
source ~/Documents/my-ai-project/ai-env/bin/activate

# Navigate to project
cd ~/Documents/"Agentic AI learning Roadmap"/Phase4_Agent_Framework/project_04_streamlit_web_ui

# Start the web UI
streamlit run streamlit_ui.py
```

Your browser will open automatically at:
```
http://localhost:8501
```

---

## Using the Chat UI

Once the browser opens:

1. **Select model** from the dropdown in the left sidebar (gemma3:27b or others you have installed)
2. **Adjust temperature** with the slider — lower = more focused, higher = more creative
3. **Optionally add a system prompt** to give the AI a persona
4. **Type your message** in the chat box at the bottom and press Enter
5. Watch the response stream in word by word
6. Use the **Clear conversation** button to start fresh

---

## Expected Terminal Output

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501

  Running on: gemma3:27b
```

In the browser you'll see a full chat interface with your messages on the right
and AI responses on the left, streaming in real time.

---

## Verification Checklist

- [ ] Terminal shows `Local URL: http://localhost:8501`
- [ ] Browser opens and shows the chat interface
- [ ] Sending a message gets a streaming response (text appears word by word)
- [ ] Model selector in sidebar shows your installed models
- [ ] Clear conversation button resets the chat history
- [ ] Response time is shown after each reply
- [ ] `Ctrl+C` in Terminal 2 stops the server

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: streamlit` | Run: `pip install streamlit --break-system-packages` |
| `Port 8501 already in use` | Run: `streamlit run streamlit_ui.py --server.port 8502` |
| Browser doesn't open automatically | Navigate to `http://localhost:8501` manually |
| Responses are very slow | Normal for `gemma3:27b` — each reply may take 10-30s |
| `Connection refused` in UI | Ollama is not running — start `ollama serve` first |

---

## Status

⏳ Ready — install `streamlit` first, then run
