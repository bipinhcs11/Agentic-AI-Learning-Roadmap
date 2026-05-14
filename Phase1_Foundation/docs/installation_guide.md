# Phase 1 Installation Guide

Complete step-by-step setup for the Mac Mini M4.

## Prerequisites

- macOS 13 Ventura or later
- Mac Mini M4 with 32GB RAM
- Internet connection (for initial downloads)

## Step-by-Step

### 1. Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
source ~/.zprofile
```

### 2. Install Ollama
```bash
brew install ollama
ollama --version   # verify
```

### 3. Start Ollama and Pull Models
```bash
# Keep this running in Tab 1
ollama serve

# In Tab 2 — pull models
ollama pull gemma3:4b          # ~3GB  — fast, for development
ollama pull gemma3:27b         # ~17GB — near GPT-4 quality (optional, for high-quality tasks)
ollama pull nomic-embed-text   # ~274MB — for RAG embeddings
```

### 4. Install Python 3.11
```bash
brew install python@3.11
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
python3.11 --version   # verify: Python 3.11.x
```

### 5. Install VS Code
```bash
brew install --cask visual-studio-code
code --version   # verify
```

### 6. Set Up Virtual Environment
```bash
cd ~/Documents/my-ai-project   # or wherever you work
python3.11 -m venv ai-env
source ai-env/bin/activate     # run this each session
```

### 7. Install AI Libraries
```bash
pip install -r requirements.txt
pip list | grep -E 'openai|langchain|fastapi'   # verify
```

### 8. Verify Full Stack
```bash
python Phase1_Foundation/test_gemma3.py
# Expected: SUCCESS: Gemma3 is working via Ollama API!
```

## Verified Output (May 3, 2026)

```
Gemma3:27b response:
An AI agent is a software entity that perceives its environment and takes
actions to achieve specific goals...
SUCCESS: Gemma3 is working via Ollama API!
```

## RAM Usage Reference

| State | RAM Used |
|-------|----------|
| macOS idle | ~6 GB |
| + gemma3:4b loaded | ~9 GB |
| + gemma3:4b loaded  | ~9 GB  |
| + gemma3:27b loaded | ~24 GB | (optional)
| + nomic-embed-text | +1 GB |

**Tip:** Run `ollama stop gemma3:4b` to free RAM when not in use.
