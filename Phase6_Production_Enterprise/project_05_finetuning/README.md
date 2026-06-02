# Project 05 — Fine-Tuning Gemma3:4b on Apple Silicon M4
**Phase 6 · Production & Enterprise**

## What You Build
A domain-adapted version of Gemma3:4b that gives better coding responses — fine-tuned entirely on your Mac Mini M4 without any cloud GPU.

## What is LoRA? (Simple Analogy)
Imagine teaching a doctor to also be a lawyer. You don't retrain them from birth — you give them a focused law course that adds onto their existing knowledge.

LoRA works the same way:
- **Base model** = the doctor's existing medical knowledge (4B parameters, frozen)
- **LoRA adapter** = the law course additions (tiny matrices, ~0.1% of params, trained)
- **Result** = doctor who is also good at law, without forgetting medicine

## Pipeline

```
prepare_dataset.py    → Creates 100 training examples (Alpaca format)
        ↓
finetune.py           → Trains LoRA adapter on your Mac Mini M4
        ↓
export_gguf.py        → Merges adapter + exports to GGUF (Ollama format)
        ↓
ollama_deploy.py      → Registers model in Ollama, runs comparison test
        ↓
ollama run ai-coding-assistant   ← Your fine-tuned model!
```

## Install

```bash
# Make sure Ollama is NOT downloading large models during training (RAM contention)
bash install.sh

# Login to HuggingFace (required to download Gemma3)
huggingface-cli login
# Paste your token from: huggingface.co/settings/tokens
 hf update          # update to 1.17.0 first
  hf auth login      # then login

  It will prompt for your Hugging Face token — get one from https://huggingface.co/settings/tokens (read access is
  enough for downloading models).
```

## Run

```bash
# Step 1: Create training dataset
python prepare_dataset.py
# Output: dataset/train.jsonl (90 examples), dataset/eval.jsonl (10)

# Step 2: Fine-tune (30-60 min on M4)
python finetune.py
# Output: lora_adapter/ (LoRA weights)

# Step 3: Dry run first to validate setup
DRY_RUN=true python finetune.py

# Step 4: Export to GGUF
python export_gguf.py
# Output: exported/gemma3-4b-finetuned.gguf

# Step 5: Deploy to Ollama
ollama serve   # in another terminal
python ollama_deploy.py
# Registers model and runs comparison test
```

## LoRA Hyperparameter Guide

| Parameter | Value Used | Effect of Changing |
|---|---|---|
| `r` (rank) | 16 | Higher = more capacity, more RAM. Try 32 for complex tasks. |
| `lora_alpha` | 16 | Keep equal to r (alpha/r = 1 scaling) |
| `lora_dropout` | 0.05 | Higher = more regularization (good for tiny datasets <50 examples) |
| `learning_rate` | 2e-4 | Lower (1e-4) = safer but slower. Higher (5e-4) = may overfit. |
| `epochs` | 3 | More epochs = better fit but risk overfitting. 3 is good for 100 examples. |
| `batch_size` | 2 | Increase to 4 if you have >24GB RAM |

## Estimated Training Time on M4

| RAM | Time for 100 examples × 3 epochs |
|---|---|
| 16GB M4 | ~45-60 minutes |
| 24GB M4 Pro | ~25-35 minutes |
| 32GB M4 Max | ~15-20 minutes |

## Adapting to Your Own Domain

Edit `prepare_dataset.py` — replace `EXAMPLES` with your own data:

```python
# Your domain examples in Alpaca format
EXAMPLES = [
    {
        "instruction": "Your task description here",
        "input": "Optional context (code, document, etc.)",
        "output": "The ideal response you want the model to learn"
    },
    # ... more examples
]
```

**Good domains for fine-tuning:**
- Customer support (your company's FAQ style)
- Code review (your team's standards)
- Document Q&A (your internal docs as training data)
- Any task where the base model gives generic answers

**Rule of thumb:** 50-200 high-quality examples is usually enough for domain adaptation.

## Troubleshooting

**"MPS out of memory"**
```bash
# Reduce batch size in finetune.py
per_device_train_batch_size=1   # was 2
gradient_accumulation_steps=8  # was 4 (keeps effective batch size = 8)
```

**"Cannot access gated model"**
```bash
huggingface-cli login   # re-login
# Also visit: huggingface.co/google/gemma-3-4b-it and click "Accept license"
```

**"Unsloth install failed"**
Fine — the script falls back to standard PEFT automatically. Training takes ~2x longer but works.

**"ollama: model not found"**
```bash
ollama list   # check registered models
ollama rm ai-coding-assistant   # remove and re-register if needed
python ollama_deploy.py
```

## What's Different From Just Prompting?

| Approach | Quality | Latency | Cost |
|---|---|---|---|
| System prompt only | Good | Fast | Free |
| Few-shot examples in prompt | Better | Slower (more tokens) | Free |
| **Fine-tuning (this project)** | **Best** | **Fast** | **One-time training cost** |

Fine-tuning "bakes" your examples into the weights — no extra tokens needed at inference time.
