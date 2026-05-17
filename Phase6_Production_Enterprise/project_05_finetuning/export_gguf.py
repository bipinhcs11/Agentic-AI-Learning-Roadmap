# ═══════════════════════════════════════════════════════════════
# Project 05 — Fine-Tuning Gemma3:4b
# Step 3: Export to GGUF for Ollama
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT IS GGUF?
#   GGUF (GPT-Generated Unified Format) is the file format
#   that Ollama uses to load models. It combines the model
#   weights + tokenizer + metadata into one portable file.
#
# QUANTIZATION LEVELS:
#   Q2_K  — smallest (2-bit), lowest quality, fastest
#   Q4_K_M — 4-bit, BEST balance of quality and size (recommended)
#   Q5_K_M — 5-bit, better quality, larger file
#   Q8_0  — 8-bit, near full quality, large file
#   F16   — full float16, largest, best quality
#
#   For Ollama + Mac Mini M4: Q4_K_M is the sweet spot.
#   Gemma3:4b in Q4_K_M = ~2.5GB file, fits easily in RAM.
#
# HOW TO RUN:
#   python export_gguf.py
#   Output: exported/gemma3-4b-finetuned.gguf
# ═══════════════════════════════════════════════════════════════

import os
import sys
import subprocess
from pathlib import Path

LORA_ADAPTER_DIR = "./lora_adapter"
BASE_MODEL       = "google/gemma-3-4b-it"
OUTPUT_DIR       = "./exported"
OUTPUT_FILENAME  = "gemma3-4b-finetuned.gguf"
HF_TOKEN         = os.getenv("HF_TOKEN", None)
QUANTIZATION     = "Q4_K_M"   # change to Q8_0 for higher quality


def check_prerequisites():
    """Make sure adapter exists and llama.cpp is available."""
    if not Path(LORA_ADAPTER_DIR).exists():
        print(f"[ERROR] Adapter not found at {LORA_ADAPTER_DIR}")
        print("  Run: python finetune.py  first")
        sys.exit(1)

    # Check if llama.cpp convert script is available
    convert_paths = [
        Path("llama.cpp/convert_hf_to_gguf.py"),
        Path(os.path.expanduser("~/llama.cpp/convert_hf_to_gguf.py")),
    ]
    for p in convert_paths:
        if p.exists():
            return str(p)

    print("[WARN] llama.cpp not found locally.")
    print("  Using Unsloth's built-in GGUF export instead.")
    return None


def export_with_unsloth():
    """Export GGUF using Unsloth's built-in method (simplest)."""
    try:
        from unsloth import FastLanguageModel
        from transformers import AutoTokenizer

        print(f"[EXPORT] Loading fine-tuned model from {LORA_ADAPTER_DIR}...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=LORA_ADAPTER_DIR,
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=True,
            token=HF_TOKEN,
        )

        output_path = str(Path(OUTPUT_DIR) / OUTPUT_FILENAME)
        Path(OUTPUT_DIR).mkdir(exist_ok=True)

        print(f"[EXPORT] Saving GGUF ({QUANTIZATION}) to {output_path}...")
        model.save_pretrained_gguf(
            OUTPUT_DIR,
            tokenizer,
            quantization_method=QUANTIZATION.lower(),
        )
        print(f"[DONE] GGUF saved to {output_path}")
        return output_path

    except ImportError:
        print("[WARN] Unsloth not available for export.")
        return None


def export_with_transformers_merge():
    """
    Merge LoRA adapter into base model and save as merged HuggingFace model.
    Then convert to GGUF using llama.cpp.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    merged_dir = "./merged_model"
    Path(merged_dir).mkdir(exist_ok=True)
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    print(f"[MERGE] Loading base model: {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(LORA_ADAPTER_DIR, token=HF_TOKEN)

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="cpu",   # merge on CPU to avoid MPS memory issues
        token=HF_TOKEN,
    )

    print(f"[MERGE] Loading and merging LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_DIR)
    model = model.merge_and_unload()   # bakes adapter into base weights

    print(f"[MERGE] Saving merged model to {merged_dir}...")
    model.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    print(f"[MERGE] Merged model saved.")

    # Try converting with llama.cpp if available
    convert_script = check_prerequisites()
    if convert_script:
        output_path = str(Path(OUTPUT_DIR) / OUTPUT_FILENAME)
        print(f"[CONVERT] Running llama.cpp conversion to GGUF {QUANTIZATION}...")
        result = subprocess.run([
            sys.executable, convert_script,
            merged_dir,
            "--outfile", output_path,
            "--outtype", "q4_k_m",
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[DONE] GGUF saved to {output_path}")
            return output_path
        else:
            print(f"[ERROR] Conversion failed:\n{result.stderr}")
            return merged_dir  # return merged model path as fallback
    else:
        print(f"[INFO] Install llama.cpp to convert to GGUF:")
        print(f"  git clone https://github.com/ggerganov/llama.cpp")
        print(f"  cd llama.cpp && pip install -r requirements.txt")
        print(f"\n  Merged HuggingFace model saved at: {merged_dir}")
        print(f"  You can load it directly with Ollama using a Modelfile.")
        return merged_dir


def main():
    print("=" * 60)
    print("  Phase 6 Project 05 — Export Fine-Tuned Model to GGUF")
    print("=" * 60)

    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    # Try Unsloth export first (fastest, best integration)
    output = export_with_unsloth()

    # Fall back to transformers merge + llama.cpp conversion
    if output is None:
        output = export_with_transformers_merge()

    print(f"\n[RESULT] Model ready at: {output}")
    print(f"\n[NEXT] Run: python ollama_deploy.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
