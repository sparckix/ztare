#!/usr/bin/env python3
"""GP-116: Extract effective rank per layer from a transformer model.

For each layer, computes the effective rank of the output activation
matrix (singular value spectrum). Produces a univariate curve:
effective_rank(layer_index) — the ZTARE substrate.

Usage:
    python scripts/extract_effective_rank.py --model pythia-70m --n-prompts 100
    python scripts/extract_effective_rank.py --model pythia-410m --n-prompts 50

Requires: torch, transformers
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np


def extract_ranks(model_name: str, n_prompts: int = 100) -> list[dict]:
    """Extract effective rank per layer."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("ERROR: requires torch, transformers")
        return []

    repo = f"EleutherAI/{model_name}"
    tokenizer = AutoTokenizer.from_pretrained(repo)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float32  # need full precision for SVD
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=dtype,
                                                  output_hidden_states=True)
    model = model.to(device)
    model.eval()

    # Generate diverse prompts (simple patterns, text, numbers)
    prompts = [
        "The quick brown fox jumps over the lazy dog.",
        "1 2 3 4 5 6 7 8 9 10",
        "In mathematics, a prime number is a natural number greater than 1",
        "((()))(())()",
        "The weather today is sunny with a high of 72 degrees",
    ] * (n_prompts // 5 + 1)
    prompts = prompts[:n_prompts]

    n_layers = model.config.num_hidden_layers
    # Accumulate activations per layer
    layer_activations = [[] for _ in range(n_layers + 1)]

    print(f"  Running {n_prompts} forward passes...")
    for i, prompt in enumerate(prompts):
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True,
                          max_length=128).to(device)
        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)

        # hidden_states: tuple of (n_layers+1) tensors, each (batch, seq, hidden)
        for layer_idx, hidden in enumerate(outputs.hidden_states):
            # Take mean over sequence positions -> (hidden_dim,)
            vec = hidden[0].mean(dim=0).cpu().numpy()
            layer_activations[layer_idx].append(vec)

        if (i + 1) % 20 == 0:
            print(f"    {i+1}/{n_prompts} done")

    # Compute effective rank per layer
    results = []
    print(f"\n  Computing effective rank per layer...")
    for layer_idx in range(n_layers + 1):
        matrix = np.array(layer_activations[layer_idx])  # (n_prompts, hidden_dim)

        # SVD
        try:
            U, S, Vt = np.linalg.svd(matrix, full_matrices=False)

            # Effective rank: exp(entropy of normalized singular values)
            S_norm = S / S.sum()
            S_norm = S_norm[S_norm > 1e-10]  # avoid log(0)
            entropy = -np.sum(S_norm * np.log(S_norm))
            eff_rank = np.exp(entropy)

            # Also: fraction of variance explained by top-k
            total_var = np.sum(S**2)
            top1_var = S[0]**2 / total_var
            top10_var = np.sum(S[:10]**2) / total_var

            results.append({
                "layer": layer_idx,
                "effective_rank": round(float(eff_rank), 2),
                "spectral_entropy": round(float(entropy), 4),
                "top1_variance_fraction": round(float(top1_var), 4),
                "top10_variance_fraction": round(float(top10_var), 4),
                "max_singular": round(float(S[0]), 4),
                "n_singular_values": len(S),
            })

            print(f"    Layer {layer_idx:>2d}: eff_rank={eff_rank:.1f}, "
                  f"top1={top1_var:.3f}, top10={top10_var:.3f}")
        except Exception as e:
            print(f"    Layer {layer_idx}: SVD failed ({e})")

    del model
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--n-prompts", type=int, default=100)
    args = parser.parse_args()

    print(f"Model: {args.model}")
    t0 = time.time()
    results = extract_ranks(args.model, args.n_prompts)
    elapsed = time.time() - t0

    if results:
        # Save raw results
        out_dir = Path("projects/gp116_cot_exchange/raw")
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"effective_rank_{args.model.replace('-','_')}.json"
        out.write_text(json.dumps(results, indent=2))

        # Also save as ZTARE evidence (layer_index vs effective_rank)
        ev_out = Path("projects/gp116_cot_exchange") / "evidence_rank.txt"
        lines = ["# effective rank vs layer index", "# n\tz"]
        for r in results:
            lines.append(f"{r['layer']}\t{r['effective_rank']}")
        ev_out.write_text("\n".join(lines) + "\n")

        print(f"\nSaved to {out} and {ev_out}")
        print(f"Total time: {elapsed:.0f}s")
        print(f"\nTo compress: make compress PROJECT=gp116_cot_exchange")


if __name__ == "__main__":
    main()
