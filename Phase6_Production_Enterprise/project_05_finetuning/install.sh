#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Install Script — Fine-Tuning on Apple Silicon M4
# Phase 6 · Project 05
# ═══════════════════════════════════════════════════════════════
#
# WHY ORDER MATTERS:
#   PyTorch must be installed BEFORE transformers/peft/trl.
#   On Apple Silicon, we need the MPS-enabled torch build.
#   bitsandbytes (4-bit quantization) doesn't support MPS,
#   so we skip it and use float16 instead.
# ═══════════════════════════════════════════════════════════════

set -e   # stop on any error

echo "═══════════════════════════════════════════════════════"
echo "  Fine-Tuning Install — Apple Silicon M4"
echo "═══════════════════════════════════════════════════════"

# Activate venv if it exists
if [ -f "$HOME/Documents/my-ai-project/ai-env/bin/activate" ]; then
    source "$HOME/Documents/my-ai-project/ai-env/bin/activate"
    echo "[OK] Activated: ai-env"
fi

echo ""
echo "[1/5] Installing PyTorch with MPS support..."
pip install torch torchvision torchaudio --quiet

echo "[2/5] Verifying MPS availability..."
python -c "
import torch
if torch.backends.mps.is_available():
    print('  [OK] MPS (Apple Silicon GPU) is available')
else:
    print('  [WARN] MPS not available — will use CPU (slower)')
print(f'  PyTorch version: {torch.__version__}')
"

echo "[3/5] Installing HuggingFace training stack..."
pip install \
    transformers>=4.40.0 \
    datasets>=2.18.0 \
    peft>=0.10.0 \
    trl>=0.8.0 \
    accelerate>=0.28.0 \
    huggingface_hub>=0.22.0 \
    tokenizers>=0.19.0 \
    --quiet

echo "[4/5] Attempting Unsloth install (optional, may fail on M4)..."
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" --quiet 2>/dev/null \
    && echo "  [OK] Unsloth installed" \
    || echo "  [WARN] Unsloth install failed — will use standard PEFT (still works)"

echo "[5/5] Verifying installation..."
python -c "
import transformers, peft, trl, datasets, accelerate
print(f'  transformers: {transformers.__version__}')
print(f'  peft:         {peft.__version__}')
print(f'  trl:          {trl.__version__}')
print(f'  datasets:     {datasets.__version__}')
"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Install complete!"
echo ""
echo "  Next steps:"
echo "  1. Login to HuggingFace:"
echo "     huggingface-cli login"
echo "     (paste your token from huggingface.co/settings/tokens)"
echo ""
echo "  2. Accept Gemma3 license on HuggingFace:"
echo "     Visit: huggingface.co/google/gemma-3-4b-it"
echo "     Click 'Accept license'"
echo ""
echo "  3. Run the pipeline:"
echo "     python prepare_dataset.py"
echo "     python finetune.py"
echo "     python export_gguf.py"
echo "     python ollama_deploy.py"
echo "═══════════════════════════════════════════════════════"
