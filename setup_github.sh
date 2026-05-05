#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# GitHub Repository Setup Script
# Agentic AI Learning Roadmap
# 
# Run this once from inside your project folder:
#   chmod +x setup_github.sh && ./setup_github.sh
# ═══════════════════════════════════════════════════════════════

set -e

REPO_NAME="Agentic-AI-Learning-Roadmap"
echo ""
echo "Setting up GitHub repo: $REPO_NAME"
echo "============================================"

# 1. Check git
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    brew install git
fi

# 2. Check gh CLI
if ! command -v gh &> /dev/null; then
    echo "Installing GitHub CLI..."
    brew install gh
    echo ""
    echo "Login to GitHub now:"
    gh auth login
fi

# 3. Configure git identity if not set
if [ -z "$(git config --global user.email)" ]; then
    echo "Enter your GitHub email:"
    read email
    git config --global user.email "$email"
    git config --global user.name "$(gh api user --jq .name)"
fi

# 4. Initialise git repo
echo ""
echo "Initialising git repository..."
git init
git add .
git commit -m "Initial commit: Phase 1 complete, Phase 2 in progress

- Ollama + Gemma3:27b running locally on Mac Mini M4
- Python 3.11, VS Code, virtual env configured
- Phase 1 foundation fully verified
- Phase 2 RAG Projects: Project 1 complete
- Full project structure with READMEs for all phases"

# 5. Create GitHub repo and push
echo ""
echo "Creating GitHub repo and pushing..."
gh repo create "$REPO_NAME" \
    --public \
    --description "From zero AI knowledge to building your own agent framework — Mac Mini M4, Ollama, Gemma3, LangChain, Modal, AWS" \
    --push \
    --source .

echo ""
echo "============================================"
echo "SUCCESS! Your repo is live at:"
gh repo view --web
echo "============================================"
