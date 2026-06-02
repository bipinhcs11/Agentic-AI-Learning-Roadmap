#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# install_phase3_4.sh — Install Phase 3 & 4 Libraries
# Agentic AI Learning Roadmap | Mac Mini M4
# ═══════════════════════════════════════════════════════════════
#
# HOW TO RUN:
#   1. Open Terminal
#   2. cd ~/Documents/"Agentic AI learning Roadmap"
#   3. source ~/Documents/my-ai-project/ai-env/bin/activate
#   4. bash install_phase3_4.sh
# ═══════════════════════════════════════════════════════════════

set -e  # stop on any error

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   Phase 3 & 4 Library Installer                     ║"
echo "║   Agentic AI Learning Roadmap                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check we're in the virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not active!"
    echo "   Run first: source ~/Documents/my-ai-project/ai-env/bin/activate"
    echo ""
    read -p "Continue anyway? (y/n): " confirm
    if [[ "$confirm" != "y" ]]; then
        echo "Exiting. Activate your venv and try again."
        exit 1
    fi
fi

echo "📦 Installing Phase 3 libraries..."
echo "   (Web scraping, HTTP, formatting)"
echo ""

pip install requests>=2.28.0 --quiet
echo "  ✅ requests"

pip install beautifulsoup4>=4.12.0 --quiet
echo "  ✅ beautifulsoup4"

pip install python-dotenv>=1.0.0 --quiet
echo "  ✅ python-dotenv"

pip install rich>=13.0.0 --quiet
echo "  ✅ rich"

pip install numpy>=1.24.0 --quiet
echo "  ✅ numpy"

echo ""
echo "📦 Installing Phase 4 libraries..."
echo "   (Web UI, database, CLI tools)"
echo ""

pip install streamlit>=1.28.0 --quiet
echo "  ✅ streamlit"

pip install sqlalchemy>=2.0.0 --quiet
echo "  ✅ sqlalchemy"

pip install tqdm>=4.65.0 --quiet
echo "  ✅ tqdm"

pip install typer>=0.9.0 --quiet
echo "  ✅ typer"

echo ""
echo "📦 Ensuring Phase 1 & 2 libs are up to date..."
pip install openai fastapi uvicorn pydantic httpx --quiet
echo "  ✅ core libs confirmed"

echo ""
echo "📦 Checking Ollama models..."
if command -v ollama &> /dev/null; then
    echo "  ✅ Ollama installed"
    echo "  Checking for nomic-embed-text..."
    ollama list | grep -q "nomic-embed-text" && echo "  ✅ nomic-embed-text found" || echo "  💡 Pull with: ollama pull nomic-embed-text"
    ollama list | grep -q "gemma3:4b" && echo "  ✅ gemma3:4b found" || echo "  💡 Pull with: ollama pull gemma3:4b"
else
    echo "  ⚠️  Ollama not found. Install: brew install ollama"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ Installation Complete!                          ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║   Start each project with:                          ║"
echo "║   1. ollama serve  (new terminal tab)               ║"
echo "║   2. source ~/Documents/my-ai-project/ai-env/bin/activate"
echo "║   3. cd Phase3_Agentic_Stack/project_01_...          ║"
echo "║   4. python <script_name>.py                        ║"
echo "║                                                      ║"
echo "║   For Streamlit UI (Project 4):                     ║"
echo "║   streamlit run streamlit_ui.py                     ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
