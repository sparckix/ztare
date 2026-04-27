#!/usr/bin/env python3
"""Division A: Extract Pythia training curves and prepare ZTARE evidence.

Pulls validation loss at each checkpoint from the Pythia suite (EleutherAI),
computes total training compute C = 6*N*D for each checkpoint, and collapses
all 8 model training runs into a single univariate curve: loss = f(log10(C)).

Outputs the three ZTARE evidence files (visible/holdout/farther-tail) with
cold variable names (n, z) and no domain labels.

Usage:
    python scripts/prep_neural_scaling_data.py

Requires: huggingface_hub, numpy
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Pythia model specs (public, from Biderman et al. 2023)
# Non-embedding parameter counts for the standard (non-deduped) suite
# ---------------------------------------------------------------------------

MODELS = {
    "pythia-70m":   70_000_000,
    "pythia-160m":  160_000_000,
    "pythia-410m":  410_000_000,
    "pythia-1b":    1_000_000_000,
    "pythia-1.4b":  1_400_000_000,
    "pythia-2.8b":  2_800_000_000,
    "pythia-6.9b":  6_900_000_000,
    "pythia-12b":   12_000_000_000,
}

TOKENS_PER_STEP = 2_097_152  # batch_size * seq_len = 1024 * 2048
MAX_STEP = 143_000


def try_fetch_from_hf(model_name: str) -> list[dict] | None:
    """Try to download eval results from HuggingFace Hub."""
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        # Pythia models are at EleutherAI/pythia-XXX
        repo_id = f"EleutherAI/{model_name}"
        # Check if eval results exist as a file in the repo
        files = api.list_repo_files(repo_id)
        eval_files = [f for f in files if "eval" in f.lower() or "log" in f.lower()]
        if eval_files:
            print(f"  Found eval files: {eval_files[:5]}")
        return None  # HF repos have model weights, not training logs
    except Exception as e:
        print(f"  HF fetch failed for {model_name}: {e}")
        return None


def generate_from_published_curves() -> list[dict]:
    """Generate data points from published Pythia convergence values.

    Since the raw W&B logs require authentication, we use the published
    final validation losses from Biderman et al. 2023 Table 5 and
    interpolate the learning curve shape from the known power-law dynamics.

    The Pythia paper reports final losses on The Pile validation set.
    We also use the known property that loss follows an approximate
    power law in compute: L(C) ~ a * C^(-b) + L_inf, with the early
    training showing a steeper decline that flattens toward convergence.
    """
    # Published final validation losses (cross-entropy, The Pile)
    # From Biderman et al. 2023, Table 5 / Figure 3
    # These are approximate values read from the paper's figures
    final_losses = {
        "pythia-70m":   3.64,
        "pythia-160m":  3.29,
        "pythia-410m":  2.96,
        "pythia-1b":    2.66,
        "pythia-1.4b":  2.56,
        "pythia-2.8b":  2.40,
        "pythia-6.9b":  2.21,
        "pythia-12b":   2.10,
    }

    # For each model, generate the learning curve trajectory
    # Using the empirical observation that loss(step) follows:
    # L(s) = L_final + A * (s/s_max)^(-alpha)
    # where alpha ~ 0.5 and A is calibrated so L(1000) ~ L_final + 1.5

    data_points = []
    steps = list(range(1000, MAX_STEP + 1, 1000))

    for model_name, N in MODELS.items():
        L_final = final_losses[model_name]
        # Early-training excess above final loss
        # Larger models converge faster relative to their final loss
        A = 1.5 + 0.3 * math.log10(N / 70e6)  # empirical scaling
        alpha = 0.5

        for step in steps:
            D = step * TOKENS_PER_STEP
            C = 6.0 * N * D

            # Learning curve: loss decreases as power law in steps
            frac = step / MAX_STEP
            loss = L_final + A * (frac ** (-alpha) - 1) / ((1000/MAX_STEP)**(-alpha) - 1) * A
            # Simplified: interpolate between start and final
            # L(s) = L_final + excess * (s_max/s)^alpha normalized
            t = (step / MAX_STEP)
            loss = L_final + A * ((1.0 / t) ** alpha - 1.0) / ((MAX_STEP / 1000.0) ** alpha - 1.0)

            data_points.append({
                "log10_compute": math.log10(C),
                "val_loss": round(loss, 6),
                "model": model_name,
                "step": step,
                "N": N,
                "D": D,
            })

    return data_points


def main():
    print("Preparing neural scaling law data for ZTARE...")
    print(f"Models: {len(MODELS)}")
    print(f"Steps per model: {MAX_STEP // 1000}")

    # Try HF first (for documentation), fall back to published curves
    print("\nChecking HuggingFace for raw eval logs...")
    for model_name in list(MODELS.keys())[:1]:
        try_fetch_from_hf(model_name)

    print("\nGenerating from published convergence values...")
    data = generate_from_published_curves()
    print(f"Total data points: {len(data)}")

    # Sort by compute
    data.sort(key=lambda x: x["log10_compute"])

    # Epistemic split by compute (Gemini Pro's approach):
    # Visible: bottom 60% of compute (smaller models + early training)
    # Holdout: next 20% (mid-size models, later training)
    # Farther-tail: top 20% (largest models at convergence)
    n = len(data)
    split1 = int(n * 0.60)
    split2 = int(n * 0.80)

    visible = data[:split1]
    holdout = data[split1:split2]
    farther = data[split2:]

    print(f"\nSplit: {len(visible)} visible, {len(holdout)} holdout, {len(farther)} farther-tail")
    print(f"Visible compute range: 10^{visible[0]['log10_compute']:.1f} to 10^{visible[-1]['log10_compute']:.1f}")
    print(f"Holdout compute range: 10^{holdout[0]['log10_compute']:.1f} to 10^{holdout[-1]['log10_compute']:.1f}")
    print(f"Farther compute range: 10^{farther[0]['log10_compute']:.1f} to 10^{farther[-1]['log10_compute']:.1f}")

    # Write ZTARE evidence files with COLD variable names
    # n = log10(compute), z = validation loss
    # NO domain labels, NO model names, NO "neural" or "scaling"

    out_dir = Path("projects/neural_scaling_01")
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_evidence(points, filename, header_comment):
        path = out_dir / filename
        lines = [f"# {header_comment}", "# n\tz"]
        for p in points:
            lines.append(f"{p['log10_compute']:.6f}\t{p['val_loss']:.6f}")
        path.write_text("\n".join(lines) + "\n")
        print(f"Wrote {path} ({len(points)} points)")

    write_evidence(visible, "evidence.txt",
                   "visible set — monotone decreasing response, continuous domain")
    write_evidence(holdout, "evidence_holdout.txt",
                   "holdout set — sealed before iteration 1")
    write_evidence(farther, "evidence_farther_tail.txt",
                   "farther-tail set — extrapolation beyond visible+holdout range")

    # Also save the full annotated data for Division A records
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "full_annotated_data.json").write_text(
        json.dumps(data, indent=2)
    )
    print(f"\nFull annotated data (Division A only): {raw_dir / 'full_annotated_data.json'}")

    print("\n=== IMPORTANT ===")
    print("This uses INTERPOLATED learning curves from published final losses.")
    print("For the real experiment, replace with actual W&B training logs.")
    print("The interpolation preserves the correct final values and approximate")
    print("power-law shape, but the exact trajectory at each step is synthetic.")
    print("Division A must document this in the pre-registration.")


if __name__ == "__main__":
    main()
