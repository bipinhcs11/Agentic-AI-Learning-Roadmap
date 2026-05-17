# ═══════════════════════════════════════════════════════════════
# Project 05 — Fine-Tuning Gemma3:4b
# Step 4: Deploy Fine-Tuned Model to Ollama
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   1. Creates an Ollama Modelfile for our fine-tuned model
#   2. Registers the model with Ollama via CLI
#   3. Tests it with a sample prompt
#   4. Compares base gemma3:4b vs fine-tuned response
#
# HOW TO RUN:
#   1. ollama serve  (in another terminal)
#   2. python ollama_deploy.py
#   3. After deployment, use: ollama run ai-coding-assistant
# ═══════════════════════════════════════════════════════════════

import subprocess
import sys
import time
from pathlib import Path
from openai import OpenAI

GGUF_PATH    = "./exported/gemma3-4b-finetuned.gguf"
MERGED_PATH  = "./merged_model"          # fallback if GGUF wasn't created
MODEL_NAME   = "ai-coding-assistant"
MODELFILE    = "./Modelfile"

# Ollama client
ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def create_modelfile():
    """Write the Ollama Modelfile for our fine-tuned model."""

    # Determine which model source to use
    if Path(GGUF_PATH).exists():
        from_line = f"FROM {GGUF_PATH}"
        print(f"[MODELFILE] Using GGUF: {GGUF_PATH}")
    elif Path(MERGED_PATH).exists():
        from_line = f"FROM {MERGED_PATH}"
        print(f"[MODELFILE] Using merged HF model: {MERGED_PATH}")
    else:
        print("[ERROR] No model found. Run export_gguf.py first.")
        sys.exit(1)

    modelfile_content = f"""{from_line}

# System prompt — defines the assistant's persona
# Fine-tuning taught the model HOW to respond.
# The system prompt teaches it WHO it is in this deployment.
SYSTEM \"\"\"You are an expert Python and AI coding assistant. You help developers write better code by:
- Providing specific, runnable code examples (not pseudocode)
- Explaining WHY something works, not just what to do
- Pointing out edge cases and potential bugs proactively
- Using Python 3.11+ best practices and type hints
- Being direct and concise — no unnecessary preamble

When you see an error message, diagnose the root cause.
When asked to write code, include error handling.
When explaining a concept, use a minimal working example.\"\"\"

# Model parameters
PARAMETER temperature 0.3      # lower = more consistent, less creative
PARAMETER top_p 0.9            # nucleus sampling — keeps output focused
PARAMETER repeat_penalty 1.1   # discourages repetition
PARAMETER num_ctx 4096         # context window — 4K tokens is plenty for coding
"""

    with open(MODELFILE, "w") as f:
        f.write(modelfile_content)
    print(f"[MODELFILE] Written to {MODELFILE}")


def register_with_ollama():
    """Run 'ollama create' to register the model."""
    print(f"\n[OLLAMA] Registering model as '{MODEL_NAME}'...")
    print(f"  Command: ollama create {MODEL_NAME} -f {MODELFILE}")

    result = subprocess.run(
        ["ollama", "create", MODEL_NAME, "-f", MODELFILE],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"[OK] Model '{MODEL_NAME}' registered successfully")
    else:
        print(f"[ERROR] ollama create failed:\n{result.stderr}")
        print("\n  Make sure: ollama serve  is running in another terminal")
        sys.exit(1)


def test_model(model_name: str, prompt: str) -> str:
    """Run a test prompt and return the response."""
    try:
        resp = ollama.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[Error: {e}]"


def compare_models():
    """Compare base model vs fine-tuned model on the same prompt."""
    test_prompts = [
        "What's wrong with this code and how do I fix it?\n\ndef get_user(users, id):\n    return users[id]",
        "Write a Python function to validate an email address.",
        "Explain what a Python decorator is in simple terms with an example.",
    ]

    print("\n" + "=" * 60)
    print("  MODEL COMPARISON: Base vs Fine-Tuned")
    print("=" * 60)

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[Test {i}] Prompt: {prompt[:60]}...\n")

        print("  BASE MODEL (gemma3:4b):")
        base_response = test_model("gemma3:4b", prompt)
        print(f"  {base_response[:300]}...\n")

        print(f"  FINE-TUNED ({MODEL_NAME}):")
        ft_response = test_model(MODEL_NAME, prompt)
        print(f"  {ft_response[:300]}...\n")

        print("  " + "─" * 56)

    print(f"\n[DONE] Fine-tuned model is live as '{MODEL_NAME}'")
    print(f"  Use it: ollama run {MODEL_NAME}")
    print(f"  API:    curl http://localhost:11434/api/chat \\")
    print(f"          -d '{{\"model\":\"{MODEL_NAME}\",\"messages\":[{{\"role\":\"user\",\"content\":\"hello\"}}]}}'")


def main():
    print("=" * 60)
    print("  Phase 6 Project 05 — Deploy Fine-Tuned Model to Ollama")
    print("=" * 60)

    create_modelfile()
    register_with_ollama()

    print(f"\n[TEST] Waiting 2s for model to load...")
    time.sleep(2)

    compare_models()
    print("=" * 60)


if __name__ == "__main__":
    main()
