# ═══════════════════════════════════════════════════════════════
# Project 05 — Fine-Tuning Gemma3:4b on Apple Silicon M4
# Step 2: Fine-Tune with LoRA
# Phase 6 · Production & Enterprise
# ═══════════════════════════════════════════════════════════════
#
# WHAT IS LORA?
#   Instead of retraining all 4 billion parameters (expensive),
#   LoRA adds small "adapter" matrices alongside the original
#   weights. Only the adapters are trained — ~0.1% of params.
#
#   Original weight W  →  W + ΔW   where ΔW = A × B
#   A and B are tiny matrices (rank r=16 means 16 dimensions)
#
#   Result: fine-tuning that costs 10x less RAM and is 5x faster,
#   with near-identical quality for domain adaptation tasks.
#
# HYPERPARAMETERS EXPLAINED:
#   r (rank):           16 = good balance. Higher = more capacity but more RAM.
#   alpha:              Same as r. Controls scaling. alpha/r = 1.0 is standard.
#   dropout:            0.05 = light regularization to prevent overfitting.
#   target_modules:     Which attention matrices to adapt. q/v = minimum;
#                       adding k/o/gate_proj improves quality.
#   learning_rate:      2e-4 = standard for LoRA. Too high = unstable training.
#   batch_size:         2 = safe for 16GB RAM. Increase if you have more memory.
#   gradient_accumulation: 4 = effective batch of 8 (2*4). Simulates larger batch.
#   epochs:             3 = usually enough for domain adaptation on small datasets.
#
# ESTIMATED TRAINING TIME ON M4 (16GB):
#   ~100 examples × 3 epochs = ~300 steps
#   ~30-60 minutes (MPS is slower than CUDA but workable)
#
# HOW TO RUN:
#   1. Install: bash install.sh
#   2. Login:   huggingface-cli login  (paste your HF token)
#   3. Prepare: python prepare_dataset.py
#   4. Train:   python finetune.py
# ═══════════════════════════════════════════════════════════════

import json
import os
import sys
import time
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Try Unsloth first (2x faster), fall back to standard PEFT
# Unsloth Apple Silicon support is experimental — we handle
# the case where it doesn't work gracefully.
# ─────────────────────────────────────────────────────────────
UNSLOTH_AVAILABLE = False
try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
    print("[INFO] Unsloth detected — using accelerated training")
except ImportError:
    print("[INFO] Unsloth not found — using standard PEFT (slower but works)")

# Standard imports (always available)
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, TaskType

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

HF_TOKEN       = os.getenv("HF_TOKEN", None)   # or set via huggingface-cli login
BASE_MODEL     = "google/gemma-3-4b-it"         # instruction-tuned base
OUTPUT_DIR     = "./lora_adapter"
DATASET_TRAIN  = "./dataset/train.jsonl"
DATASET_EVAL   = "./dataset/eval.jsonl"
DRY_RUN        = os.getenv("DRY_RUN", "false").lower() == "true"

# Detect device
if torch.backends.mps.is_available():
    DEVICE = "mps"
    print("[INFO] Apple Silicon MPS detected — GPU acceleration enabled")
elif torch.cuda.is_available():
    DEVICE = "cuda"
    print("[INFO] CUDA GPU detected")
else:
    DEVICE = "cpu"
    print("[WARN] No GPU detected — training will be very slow on CPU")

# ─────────────────────────────────────────────────────────────
# LoRA Configuration
# ─────────────────────────────────────────────────────────────

LORA_CONFIG = LoraConfig(
    r=16,                   # rank: dimensionality of low-rank matrices
    lora_alpha=16,          # scaling factor (alpha/r = 1 means no extra scaling)
    lora_dropout=0.05,      # small dropout prevents overfitting on small datasets
    bias="none",            # don't adapt bias terms — not needed for most tasks
    task_type=TaskType.CAUSAL_LM,
    target_modules=[        # which layers to adapt
        "q_proj",           # query projection (attention)
        "v_proj",           # value projection (attention)
        "k_proj",           # key projection (attention)
        "o_proj",           # output projection (attention)
        # Uncomment for higher quality (uses more RAM):
        # "gate_proj",      # FFN gating
        # "up_proj",        # FFN up-projection
        # "down_proj",      # FFN down-projection
    ],
)

# ─────────────────────────────────────────────────────────────
# Alpaca Prompt Template
# This is the format we'll use to structure training examples.
# The model learns to complete the Response given Instruction+Input.
# ─────────────────────────────────────────────────────────────

ALPACA_TEMPLATE = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Input:
{input}

### Response:
{output}"""

ALPACA_TEMPLATE_NO_INPUT = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{instruction}

### Response:
{output}"""


def format_example(example: dict) -> str:
    """Format a training example into the Alpaca prompt."""
    if example.get("input", "").strip():
        return ALPACA_TEMPLATE.format(**example)
    else:
        return ALPACA_TEMPLATE_NO_INPUT.format(
            instruction=example["instruction"],
            output=example["output"]
        )


def load_dataset_from_jsonl(path: str) -> Dataset:
    """Load JSONL dataset and format with Alpaca template."""
    if not Path(path).exists():
        raise FileNotFoundError(f"Dataset not found: {path}\nRun: python prepare_dataset.py")

    examples = []
    with open(path) as f:
        for line in f:
            ex = json.loads(line.strip())
            examples.append({"text": format_example(ex)})

    return Dataset.from_list(examples)


def load_model_standard():
    """Load model using standard HuggingFace transformers (no Unsloth)."""
    print(f"\n[LOADING] Loading {BASE_MODEL} with standard transformers...")
    print("[INFO] This will download ~8GB on first run. Be patient.")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        token=HF_TOKEN,
        trust_remote_code=True,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load in 4-bit quantization to fit in 16GB RAM
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )

    # MPS doesn't support bitsandbytes — load in float16 instead
    if DEVICE == "mps":
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            token=HF_TOKEN,
            torch_dtype=torch.float16,
            device_map="mps",
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            token=HF_TOKEN,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

    # Apply LoRA adapters
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    return model, tokenizer


def load_model_unsloth():
    """Load model using Unsloth for 2x faster training."""
    print(f"\n[LOADING] Loading {BASE_MODEL} with Unsloth...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=2048,
        dtype=None,   # auto-detect
        load_in_4bit=True,
        token=HF_TOKEN,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_CONFIG.r,
        target_modules=LORA_CONFIG.target_modules,
        lora_alpha=LORA_CONFIG.lora_alpha,
        lora_dropout=LORA_CONFIG.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    return model, tokenizer


def tokenize_dataset(dataset: Dataset, tokenizer, max_length: int = 1024):
    """Tokenize the formatted text examples."""
    def tokenize(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )
    return dataset.map(tokenize, batched=True, remove_columns=["text"])


def train(model, tokenizer, train_dataset, eval_dataset):
    """Run fine-tuning with SFTTrainer or standard Trainer."""
    try:
        from trl import SFTTrainer, SFTConfig
        use_sft = True
    except ImportError:
        from transformers import Trainer
        use_sft = False

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=4,   # effective batch = 2 × 4 = 8
        learning_rate=2e-4,
        warmup_steps=10,
        logging_steps=10,                # print loss every 10 steps
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        fp16=(DEVICE != "mps"),          # MPS doesn't support fp16 training
        bf16=False,
        optim="adamw_torch",
        dataloader_num_workers=0,        # 0 = no multiprocessing (safer on Mac)
        report_to="none",                # disable wandb/tensorboard for simplicity
        seed=42,
    )

    print(f"\n[TRAINING] Starting fine-tuning...")
    print(f"  Device:     {DEVICE}")
    print(f"  Epochs:     3")
    print(f"  Batch size: 2 (effective: 8 with gradient accumulation)")
    print(f"  LR:         2e-4")
    print(f"  Output:     {OUTPUT_DIR}")
    print(f"  Estimated time: 30-60 min on M4 (be patient)\n")

    if use_sft:
        trainer = SFTTrainer(
            model=model,
            args=SFTConfig(
                **{k: v for k, v in training_args.to_dict().items()
                   if k in SFTConfig.__dataclass_fields__},
                dataset_text_field="text",
                max_seq_length=1024,
            ),
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
        )
    else:
        tokenized_train = tokenize_dataset(train_dataset, tokenizer)
        tokenized_eval  = tokenize_dataset(eval_dataset, tokenizer)
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_train,
            eval_dataset=tokenized_eval,
            data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
        )

    start = time.time()
    trainer.train()
    duration = (time.time() - start) / 60
    print(f"\n[DONE] Training complete in {duration:.1f} minutes")

    # Save the LoRA adapter weights
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"[SAVED] Adapter saved to {OUTPUT_DIR}/")


def dry_run():
    """Validate setup without loading the full model."""
    print("\n[DRY RUN] Validating setup (DRY_RUN=true — not loading model)...")

    # Check dataset
    if not Path(DATASET_TRAIN).exists():
        print("[FAIL] Dataset missing. Run: python prepare_dataset.py")
        return False
    with open(DATASET_TRAIN) as f:
        n = sum(1 for _ in f)
    print(f"[OK] Dataset: {n} training examples found")

    # Check HF token
    token_path = Path.home() / ".cache" / "huggingface" / "token"
    if HF_TOKEN or token_path.exists():
        print("[OK] HuggingFace token found")
    else:
        print("[WARN] No HF token. Run: huggingface-cli login")

    # Check torch
    print(f"[OK] PyTorch {torch.__version__} | Device: {DEVICE}")
    print(f"[OK] Unsloth: {'available' if UNSLOTH_AVAILABLE else 'not installed (will use PEFT)'}")
    print(f"[OK] Output directory will be: {OUTPUT_DIR}")
    print("\n[DRY RUN] Setup looks good. Remove DRY_RUN=true to start real training.")
    return True


def main():
    print("=" * 60)
    print("  Phase 6 Project 05 — Fine-Tuning Gemma3:4b")
    print("=" * 60)

    if DRY_RUN:
        dry_run()
        return

    # Load datasets
    print("\n[DATASET] Loading training data...")
    train_ds = load_dataset_from_jsonl(DATASET_TRAIN)
    eval_ds  = load_dataset_from_jsonl(DATASET_EVAL)
    print(f"  Train: {len(train_ds)} examples")
    print(f"  Eval:  {len(eval_ds)} examples")

    # Load model
    if UNSLOTH_AVAILABLE:
        model, tokenizer = load_model_unsloth()
    else:
        model, tokenizer = load_model_standard()

    # Train
    train(model, tokenizer, train_ds, eval_ds)

    print("\n[NEXT] Run: python export_gguf.py")


if __name__ == "__main__":
    main()
