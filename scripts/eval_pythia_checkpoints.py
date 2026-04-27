#!/usr/bin/env python3
"""Evaluate Pythia model checkpoints to extract validation loss at each training step.

Requires: torch, transformers, datasets (pip install torch transformers datasets)
Requires: GPU recommended (CPU works but slow)

Usage:
    python scripts/eval_pythia_checkpoints.py --model pythia-70m --steps 1000 10000 50000 100000 143000
    python scripts/eval_pythia_checkpoints.py --model pythia-70m --all-steps

This downloads each checkpoint from HuggingFace, runs a forward pass on a
validation sample, and records the cross-entropy loss. Output is saved to
projects/monotone_decay_01/raw/pythia_{model}_longitudinal.json
"""

import argparse
import json
import sys
from pathlib import Path


def eval_checkpoint(model_name: str, step: int, n_samples: int = 100) -> float | None:
    """Evaluate a single Pythia checkpoint and return validation loss."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from datasets import load_dataset
    except ImportError:
        print("ERROR: requires torch, transformers, datasets", file=sys.stderr)
        return None

    repo_id = f"EleutherAI/{model_name}"
    revision = f"step{step}"

    try:
        tokenizer = AutoTokenizer.from_pretrained(repo_id)
        model = AutoModelForCausalLM.from_pretrained(
            repo_id, revision=revision,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        if torch.cuda.is_available():
            model = model.cuda()
        model.eval()

        # Use a slice of The Pile validation set
        dataset = load_dataset("monology/pile-uncopyrighted", split="validation",
                              streaming=True)

        total_loss = 0.0
        count = 0
        with torch.no_grad():
            for i, sample in enumerate(dataset):
                if i >= n_samples:
                    break
                tokens = tokenizer(sample["text"], return_tensors="pt",
                                  truncation=True, max_length=2048)
                if torch.cuda.is_available():
                    tokens = {k: v.cuda() for k, v in tokens.items()}
                outputs = model(**tokens, labels=tokens["input_ids"])
                total_loss += outputs.loss.item()
                count += 1

        avg_loss = total_loss / count if count > 0 else None
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return avg_loss

    except Exception as e:
        print(f"  step {step}: FAILED ({e})")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="e.g., pythia-70m, pythia-410m")
    parser.add_argument("--steps", nargs="+", type=int, default=None)
    parser.add_argument("--all-steps", action="store_true",
                       help="Evaluate every 1000 steps from 1000 to 143000")
    parser.add_argument("--n-samples", type=int, default=100,
                       help="Number of validation samples per checkpoint")
    args = parser.parse_args()

    if args.all_steps:
        steps = list(range(1000, 144000, 1000))
    elif args.steps:
        steps = args.steps
    else:
        # Default: 20 evenly-spaced checkpoints
        steps = list(range(1000, 144000, 7000))

    print(f"Model: {args.model}")
    print(f"Steps: {len(steps)} checkpoints")
    print(f"Samples per checkpoint: {args.n_samples}")

    results = []
    for step in steps:
        print(f"  Evaluating step {step}...", end=" ", flush=True)
        loss = eval_checkpoint(args.model, step, args.n_samples)
        if loss is not None:
            results.append({"model": args.model, "step": step, "val_loss": round(loss, 6)})
            print(f"loss={loss:.4f}")
        else:
            print("FAILED")

    out = Path(f"projects/monotone_decay_01/raw/pythia_{args.model.replace('-','_')}_longitudinal.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nSaved {len(results)} points to {out}")


if __name__ == "__main__":
    main()
