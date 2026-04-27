#!/usr/bin/env python3
"""GP-116 Candidate 0: Generate synthetic bracket-matching data.

Creates sequences of nested brackets where the task is to predict
whether the sequence is balanced. The "observable" for ZTARE is
accuracy as a function of sequence length L.

This substrate isolates sequential state-tracking: the only information
needed is the current bracket depth (a single integer). A recurrence
tracks this in O(L). Attention must look back at all previous tokens O(L^2).

Usage:
    python scripts/generate_bracket_challenge.py --lengths 10 20 50 100 200 500
"""

import argparse
import json
import random
from pathlib import Path


def generate_balanced_brackets(length: int) -> str:
    """Generate a balanced bracket sequence of given length."""
    if length % 2 != 0:
        length -= 1
    seq = []
    depth = 0
    remaining = length
    for _ in range(length):
        remaining -= 1
        if depth == 0:
            seq.append("(")
            depth += 1
        elif depth == remaining:
            seq.append(")")
            depth -= 1
        elif random.random() < 0.5:
            seq.append("(")
            depth += 1
        else:
            seq.append(")")
            depth -= 1
    return "".join(seq)


def generate_unbalanced_brackets(length: int) -> str:
    """Generate an unbalanced bracket sequence."""
    seq = list(generate_balanced_brackets(length))
    # Flip one random bracket
    idx = random.randint(0, len(seq) - 1)
    seq[idx] = ")" if seq[idx] == "(" else "("
    return "".join(seq)


def generate_dataset(length: int, n_samples: int = 100) -> list[dict]:
    """Generate balanced/unbalanced pairs at a given length."""
    samples = []
    for _ in range(n_samples // 2):
        balanced = generate_balanced_brackets(length)
        samples.append({"sequence": balanced, "label": 1, "length": length})
        unbalanced = generate_unbalanced_brackets(length)
        samples.append({"sequence": unbalanced, "label": 0, "length": length})
    random.shuffle(samples)
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lengths", nargs="+", type=int,
                       default=[10, 20, 50, 100, 200, 500])
    parser.add_argument("--samples-per-length", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    out_dir = Path("projects/gp116_cot_exchange/raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_data = []
    for L in args.lengths:
        data = generate_dataset(L, args.samples_per_length)
        all_data.extend(data)
        balanced_acc = sum(1 for d in data if d["label"] == 1) / len(data)
        print(f"  L={L:>4d}: {len(data)} samples, {balanced_acc:.0%} balanced")

    out_path = out_dir / "bracket_challenge.json"
    out_path.write_text(json.dumps(all_data, indent=2))
    print(f"\nSaved {len(all_data)} samples to {out_path}")
    print(f"\nTo evaluate a model:")
    print(f"  python scripts/eval_bracket_challenge.py --model pythia-70m")


if __name__ == "__main__":
    main()
