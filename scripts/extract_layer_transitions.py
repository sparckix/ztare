#!/usr/bin/env python3
"""GP-116 Phase 2: Extract layer-to-layer activation transitions.

For each adjacent pair of bottleneck layers (default: 6→7), extracts
the 1024-dim activation vectors per token, projects to 2D via SVD,
and outputs the transition as a ZTARE-compatible substrate.

The SVD basis is computed from the input layer's activations across
all tokens in the prompt set. The output layer's activations are
projected onto the SAME basis (consistency requirement — the 2D
coordinate system must be shared between input and output).

GP-072 information isolation: this script sees no thesis, no charter,
no prior rank data. It extracts raw activation pairs and writes
evidence files. The compression primitive tests the hypothesis
independently.

Output:
  - evidence.txt:          v1_in → v1_out (dominant component)
  - evidence_v2.txt:       v2_in → v2_out (second component)
  - evidence_holdout.txt:  holdout split of v1_in → v1_out
  - raw/layer_transitions_{model}_{L}_{L+1}.json: full data

Usage:
    python scripts/extract_layer_transitions.py --model pythia-410m
    python scripts/extract_layer_transitions.py --model pythia-410m --layer-start 6 --layer-end 7
    python scripts/extract_layer_transitions.py --model pythia-410m --all-bottleneck
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np


def extract_transitions(
    model_name: str,
    layer_start: int,
    layer_end: int,
    n_prompts: int = 100,
) -> dict:
    """Extract activation transitions between two adjacent layers.

    Returns a dict with:
      - v1_pairs: list of (v1_in, v1_out) in the SVD basis
      - v2_pairs: list of (v2_in, v2_out) in the SVD basis
      - svd_info: singular values, explained variance
      - reconstruction_error: how much the 2D projection loses
    """
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("ERROR: requires torch, transformers")
        return {}

    repo = f"EleutherAI/{model_name}"
    tokenizer = AutoTokenizer.from_pretrained(repo)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float32  # full precision for SVD
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    model = AutoModelForCausalLM.from_pretrained(
        repo, torch_dtype=dtype, output_hidden_states=True
    )
    model = model.to(device)
    model.eval()

    # Diverse prompts — reasoning, text, patterns, math
    # Important: must be diverse enough that the SVD basis is not
    # dominated by one prompt class
    base_prompts = [
        "The quick brown fox jumps over the lazy dog.",
        "1 2 3 4 5 6 7 8 9 10",
        "In mathematics, a prime number is a natural number greater than 1",
        "((()))(())()",
        "The weather today is sunny with a high of 72 degrees",
        "If all roses are flowers and all flowers are plants, then all roses are",
        "2 + 2 = 4, 3 + 3 = 6, 4 + 4 =",
        "The capital of France is Paris. The capital of Germany is",
        "Water freezes at 0 degrees Celsius and boils at 100 degrees",
        "A B C D E F G H I J K L M N O P Q R S T",
        "One two three four five six seven eight nine ten",
        "The Fibonacci sequence is 1 1 2 3 5 8 13 21 34",
        "To be or not to be, that is the question",
        "import numpy as np; x = np.array([1, 2, 3])",
        "The transformer architecture uses self-attention to process sequences",
        "def factorial(n): return 1 if n == 0 else n * factorial(n-1)",
        "Einstein showed that E = mc^2, relating energy to mass",
        "The mitochondria is the powerhouse of the cell",
        "SELECT * FROM users WHERE age > 18 ORDER BY name",
        "In 1969, Neil Armstrong became the first person to walk on the moon",
    ]
    prompts = (base_prompts * (n_prompts // len(base_prompts) + 1))[:n_prompts]

    # Collect per-token activations at both layers
    # Panel fix #4: tag each token with prompt_id and position
    acts_in = []      # list of 1D arrays, one per token across all prompts
    acts_residual = []  # Panel fix #1: h_out - h_in (layer residual, not total)
    token_meta = []   # (prompt_id, position) for stratification

    print(f"  Extracting layers {layer_start}→{layer_end} from {model_name}...")
    print(f"  Running {n_prompts} forward passes...")

    for i, prompt in enumerate(prompts):
        inputs = tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=128
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)

        # hidden_states[layer_start] shape: (1, seq_len, hidden_dim)
        h_in = outputs.hidden_states[layer_start][0].cpu().numpy()   # (seq, hidden)
        h_out = outputs.hidden_states[layer_end][0].cpu().numpy()    # (seq, hidden)

        # Panel fix #1: compute the RESIDUAL (what attention+MLP actually add)
        h_residual = h_out - h_in  # (seq, hidden)

        # Panel fix #2: exclude position 0 (BOS token has qualitatively
        # different representation, dominates SVD, creates false bimodality)
        for t in range(h_in.shape[0]):
            if t == 0:
                continue  # skip BOS
            acts_in.append(h_in[t])
            acts_residual.append(h_residual[t])
            token_meta.append({"prompt_id": i, "position": t})

        if (i + 1) % 20 == 0:
            print(f"    {i+1}/{n_prompts} done ({len(acts_in)} tokens collected, BOS excluded)")

    acts_in = np.array(acts_in)          # (N_tokens, hidden_dim)
    acts_residual = np.array(acts_residual)  # (N_tokens, hidden_dim)
    print(f"  Total tokens: {len(acts_in)} (position-0 excluded)")

    # Panel fix #3: center using INPUT mean only (not independent centering)
    # Independent centering pre-commits to an affine model. Using the input
    # mean preserves the output's relationship to the input coordinate system.
    mean_in = acts_in.mean(axis=0)
    acts_in_centered = acts_in - mean_in
    # Residual is NOT centered — it is what the layer actually computes
    # (centering the residual would subtract the mean perturbation,
    #  which is part of the signal we want to measure)

    print(f"  Computing SVD on input activations ({acts_in_centered.shape})...")
    U_in, S_in, Vt_in = np.linalg.svd(acts_in_centered, full_matrices=False)

    # The top-2 right singular vectors define the 2D basis
    basis = Vt_in[:2, :]  # (2, hidden_dim)

    # Project input and RESIDUAL onto the input's basis
    proj_in = acts_in_centered @ basis.T       # (N_tokens, 2)
    proj_residual = acts_residual @ basis.T     # (N_tokens, 2)

    # Reconstruction error for the residual projection
    recon_res = proj_residual @ basis  # (N_tokens, hidden_dim)
    res_recon_error = np.sqrt(np.mean(np.sum((acts_residual - recon_res)**2, axis=1)))
    res_total_norm = np.sqrt(np.mean(np.sum(acts_residual**2, axis=1)))
    relative_error = res_recon_error / res_total_norm if res_total_norm > 0 else float("inf")

    # Variance explained by top-2 (of the INPUT)
    total_var = np.sum(S_in**2)
    top2_var = np.sum(S_in[:2]**2) / total_var

    # How much of the residual's variance is captured by the INPUT basis?
    res_var_in_basis = np.sum(proj_residual**2) / np.sum(acts_residual**2)

    print(f"  Input SVD: top-2 explains {top2_var:.1%} of input variance")
    print(f"  Residual captured by input basis: {res_var_in_basis:.1%}")

    # The residual lives in its own subspace — compute SVD on the RESIDUAL
    # to find its intrinsic structure
    print(f"  Computing SVD on RESIDUAL ({acts_residual.shape})...")
    res_centered = acts_residual - acts_residual.mean(axis=0)
    U_res, S_res, Vt_res = np.linalg.svd(res_centered, full_matrices=False)

    res_total_var = np.sum(S_res**2)
    res_top1_var = S_res[0]**2 / res_total_var
    res_top2_var = np.sum(S_res[:2]**2) / res_total_var
    res_top5_var = np.sum(S_res[:5]**2) / res_total_var

    # Effective rank of the residual
    S_res_norm = S_res / S_res.sum()
    S_res_norm = S_res_norm[S_res_norm > 1e-10]
    res_entropy = -np.sum(S_res_norm * np.log(S_res_norm))
    res_eff_rank = np.exp(res_entropy)

    print(f"  Residual effective rank: {res_eff_rank:.1f}")
    print(f"  Residual top-1 variance: {res_top1_var:.1%}")
    print(f"  Residual top-2 variance: {res_top2_var:.1%}")
    print(f"  Residual top-5 variance: {res_top5_var:.1%}")

    # Use the RESIDUAL's own SVD basis for the substrate
    res_basis = Vt_res[:2, :]  # (2, hidden_dim)
    proj_in_resbasis = acts_in_centered @ res_basis.T    # input projected onto residual's basis
    proj_res_resbasis = res_centered @ res_basis.T       # residual in its own basis

    # Reconstruction error using residual's basis
    recon_res2 = proj_res_resbasis @ res_basis
    res_recon_error2 = np.sqrt(np.mean(np.sum((res_centered - recon_res2)**2, axis=1)))
    res_total_norm = np.sqrt(np.mean(np.sum(res_centered**2, axis=1)))
    relative_error = res_recon_error2 / res_total_norm if res_total_norm > 0 else float("inf")

    print(f"  Residual reconstruction error (own basis): {relative_error:.4f}")

    # Build the substrate: input's projection onto residual basis → residual's projection
    # This asks: given where the input is in the residual's subspace,
    # what does the layer compute?
    v1_in = proj_in_resbasis[:, 0]
    v2_in = proj_in_resbasis[:, 1]
    r1 = proj_res_resbasis[:, 0]
    r2 = proj_res_resbasis[:, 1]

    # Sort by v1_in for a clean substrate
    sort_idx = np.argsort(v1_in)
    v1_in = v1_in[sort_idx]
    v2_in = v2_in[sort_idx]
    r1 = r1[sort_idx]
    r2 = r2[sort_idx]

    # Diagnostic: residual magnitude vs input
    res_over_input = float(res_total_norm / np.sqrt(np.mean(np.sum(acts_in_centered**2, axis=1))))
    print(f"  |residual| / |input|: {res_over_input:.4f} (how much the layer adds)")

    # Bin to reduce noise: quantile-based binning so each bin has
    # roughly equal token count (uniform binning fails when the
    # distribution is concentrated — most bins end up empty)
    n_bins = min(200, len(v1_in) // 5)
    if n_bins < 10:
        n_bins = len(v1_in)  # too few tokens, no binning

    # Quantile bin edges: evenly spaced in CDF, not in value
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(v1_in, quantiles)
    # Deduplicate edges (can happen if many identical values)
    bin_edges = np.unique(bin_edges)
    n_bins = len(bin_edges) - 1

    v1_pairs = []  # (v1_in, residual_v1) — what attention+MLP adds in the v1 direction
    v2_pairs = []  # (v2_in, residual_v2)

    for b in range(n_bins):
        if b < n_bins - 1:
            mask = (v1_in >= bin_edges[b]) & (v1_in < bin_edges[b + 1])
        else:  # include right edge in last bin
            mask = (v1_in >= bin_edges[b]) & (v1_in <= bin_edges[b + 1])
        if mask.sum() == 0:
            continue
        v1_pairs.append((
            float(np.mean(v1_in[mask])),
            float(np.mean(r1[mask])),
        ))
        v2_pairs.append((
            float(np.mean(v2_in[mask])),
            float(np.mean(r2[mask])),
        ))

    print(f"  Binned {len(v1_in)} tokens into {len(v1_pairs)} quantile bins")

    del model
    try:
        import torch as _torch
        if _torch.backends.mps.is_available():
            _torch.mps.empty_cache()
    except Exception:
        pass

    return {
        "model": model_name,
        "layer_in": layer_start,
        "layer_out": layer_end,
        "n_tokens": len(acts_in),
        "n_bins": len(v1_pairs),
        "v1_pairs": v1_pairs,
        "v2_pairs": v2_pairs,
        "input_top2_variance": round(float(top2_var), 6),
        "residual_captured_by_input_basis": round(float(res_var_in_basis), 6),
        "residual_effective_rank": round(float(res_eff_rank), 2),
        "residual_top1_variance": round(float(res_top1_var), 6),
        "residual_top2_variance": round(float(res_top2_var), 6),
        "residual_top5_variance": round(float(res_top5_var), 6),
        "reconstruction_relative_error": round(float(relative_error), 6),
        "residual_over_input_ratio": round(float(res_over_input), 6),
        "input_singular_values_top5": [round(float(s), 4) for s in S_in[:5]],
        "residual_singular_values_top5": [round(float(s), 4) for s in S_res[:5]],
        "mean_in_norm": round(float(np.linalg.norm(mean_in)), 4),
    }


def write_evidence(result: dict, project_dir: Path, layer_suffix: str = "") -> None:
    """Write ZTARE-compatible evidence files from extraction result."""
    v1_pairs = result["v1_pairs"]
    v2_pairs = result["v2_pairs"]

    if not v1_pairs:
        print("  No data to write!")
        return

    # Split 70/15/15 for visible/holdout
    n = len(v1_pairs)
    n_vis = int(n * 0.70)
    n_ho = int(n * 0.15)

    vis = v1_pairs[:n_vis]
    ho = v1_pairs[n_vis:n_vis + n_ho]
    # remaining = test (not used by ZTARE)

    suffix = f"_{layer_suffix}" if layer_suffix else ""

    # evidence.txt (v1 component: input projection → layer residual in v1 direction)
    ev_path = project_dir / f"evidence{suffix}.txt"
    lines = [
        f"# v1_in → residual_v1 (what attention+MLP add), layers {result['layer_in']}→{result['layer_out']}",
        "# BOS tokens excluded, centered on input mean only",
        "# n\tz",
    ]
    for x, y in vis:
        lines.append(f"{x:.6f}\t{y:.6f}")
    ev_path.write_text("\n".join(lines) + "\n")

    # evidence_holdout.txt
    ho_path = project_dir / f"evidence_holdout{suffix}.txt"
    lines = ["# holdout"]
    for x, y in ho:
        lines.append(f"{x:.6f}\t{y:.6f}")
    ho_path.write_text("\n".join(lines) + "\n")

    # evidence_v2.txt (second component residual)
    v2_path = project_dir / f"evidence_v2{suffix}.txt"
    lines = [
        f"# v2_in → residual_v2 (attention+MLP add), layers {result['layer_in']}→{result['layer_out']}",
        "# n\tz",
    ]
    for x, y in v2_pairs:
        lines.append(f"{x:.6f}\t{y:.6f}")
    v2_path.write_text("\n".join(lines) + "\n")

    print(f"  Written: {ev_path} ({len(vis)} pts), {ho_path} ({len(ho)} pts), {v2_path} ({len(v2_pairs)} pts)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="pythia-410m")
    parser.add_argument("--layer-start", type=int, default=6)
    parser.add_argument("--layer-end", type=int, default=7)
    parser.add_argument("--all-bottleneck", action="store_true",
                        help="Extract all bottleneck pairs (6→7 through 16→17)")
    parser.add_argument("--n-prompts", type=int, default=100)
    parser.add_argument("--project-dir", type=str,
                        default="projects/gp116_cot_exchange")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    if args.all_bottleneck:
        layer_pairs = [(L, L + 1) for L in range(6, 17)]
    else:
        layer_pairs = [(args.layer_start, args.layer_end)]

    for L_in, L_out in layer_pairs:
        print(f"\n{'='*60}")
        print(f"Extracting {args.model}: Layer {L_in} → {L_out}")
        print(f"{'='*60}")

        t0 = time.time()
        result = extract_transitions(args.model, L_in, L_out, args.n_prompts)
        elapsed = time.time() - t0

        if not result:
            print(f"  FAILED")
            continue

        print(f"  Extraction time: {elapsed:.1f}s")
        print(f"  Residual effective rank: {result['residual_effective_rank']}")
        print(f"  Residual top-2 variance: {result['residual_top2_variance']:.1%}")
        print(f"  Recon error: {result['reconstruction_relative_error']:.4f}")

        # Save raw JSON
        raw_dir = project_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        model_slug = args.model.replace("-", "_")
        raw_path = raw_dir / f"layer_transitions_{model_slug}_{L_in}_{L_out}.json"
        raw_path.write_text(json.dumps(result, indent=2))
        print(f"  Raw saved to {raw_path}")

        # Write evidence files
        # For single pair: write directly to evidence.txt
        # For all-bottleneck: use layer suffix
        suffix = f"L{L_in}_{L_out}" if args.all_bottleneck else ""
        write_evidence(result, project_dir, suffix)

    print(f"\nDone. To compress: make compress PROJECT=gp116_cot_exchange")


if __name__ == "__main__":
    main()
