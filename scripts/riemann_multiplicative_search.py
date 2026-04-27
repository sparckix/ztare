#!/usr/bin/env python3
"""GP-125 multiplicative variant: H = H_poly @ (I + eps * H_arith).

Per Gemini Pro inversion (2026-04-23): the additive composition
H = H_poly + H_arith forces a zero-sum game between magnitude (controlled
by polynomial) and spacing variance (controlled by arithmetic). The
multiplicative form lets arithmetic phase-modulate the polynomial
backbone, injecting off-diagonal coupling without spectral competition.

Mathematical form per layer-pair:
    H_poly    = sum_i c_i * P_i        (Sierra-Townsend polynomial part)
    H_arith   = sum_j d_j * A_j        (Λ(n), ψ(n), prime, μ·log diagonals)
    H_total   = (H_poly + H_poly.T)/2 @ (I + eps * (H_arith + H_arith.T)/2)
    H_sym     = (H_total + H_total.T)/2  (symmetrize, eigh requires)

The eps coefficient is itself a learned parameter. Initial eps ~ 0.1.

Loss is the same MSE as the original script — the question this experiment
answers is whether multiplicative composition allows lower-MSE basins
than additive composition AT THE SAME spacing CV (target ~0.452).

Smoke test scope: ~10 min on GH200 / A100.
Usage:
    python riemann_multiplicative_search.py --n-zeros 50 --n-matrix 200 --restarts 5 --steps 2000
"""

import sys
sys.path.insert(0, "scripts")
from riemann_operator_search_gpu import (
    compute_riemann_zeros, build_operators, GENERATORS,
    HARDCODED_ZEROS,
)

import argparse, json, time
import numpy as np
import torch


def make_multiplicative_hamiltonian(poly_params, arith_params, eps,
                                     ops, poly_terms, arith_terms):
    """Build H_total = sym(H_poly) @ (I + eps * sym(H_arith)), then symmetrize."""
    # H_poly part
    H_poly = torch.zeros_like(ops["I"])
    for i, term in enumerate(poly_terms):
        H_poly = H_poly + poly_params[i] * ops[term]
    H_poly = (H_poly + H_poly.T) / 2

    # H_arith part
    H_arith = torch.zeros_like(ops["I"])
    for j, term in enumerate(arith_terms):
        H_arith = H_arith + arith_params[j] * ops[term]
    H_arith = (H_arith + H_arith.T) / 2

    # Multiplicative composition: H_poly @ (I + eps * H_arith)
    modulator = ops["I"] + eps * H_arith
    H_total = H_poly @ modulator

    # Symmetrize for eigh (matrix product of two symmetric matrices need not be symmetric)
    return (H_total + H_total.T) / 2


# Multiplicative generator families: poly backbone × arith modulation
MULT_GENERATORS = {
    "ST_x_mangoldt": {
        "poly_terms": ["n", "log", "nlogn", "x2", "I"],
        "arith_terms": ["mangoldt"],
        "n_poly": 5, "n_arith": 1,
        "desc": "Sierra-Townsend backbone × von Mangoldt modulation",
    },
    "ST_x_psi": {
        "poly_terms": ["n", "log", "nlogn", "x2", "I"],
        "arith_terms": ["psi"],
        "n_poly": 5, "n_arith": 1,
        "desc": "ST × Chebyshev ψ modulation",
    },
    "ST_x_arith_dual": {
        "poly_terms": ["n", "log", "nlogn", "x2", "I"],
        "arith_terms": ["mangoldt", "psi"],
        "n_poly": 5, "n_arith": 2,
        "desc": "ST × (Λ + ψ) modulation",
    },
    "ST_x_arith_full": {
        "poly_terms": ["n", "log", "nlogn", "x2", "I"],
        "arith_terms": ["mangoldt", "psi", "prime", "moblog"],
        "n_poly": 5, "n_arith": 4,
        "desc": "ST × full arithmetic modulation",
    },
    "ST_n2_x_mangoldt": {
        "poly_terms": ["n", "log", "nlogn", "n2", "x2", "I"],  # ST_n2 was best polynomial
        "arith_terms": ["mangoldt"],
        "n_poly": 6, "n_arith": 1,
        "desc": "ST_n2 (best polynomial baseline) × von Mangoldt modulation",
    },
}


def fit_one_restart(target, ops, poly_terms, arith_terms, n_poly, n_arith,
                     n_steps, lr, device, dtype, eps_init=0.1):
    """Single restart for multiplicative-form Hamiltonian fitting."""
    N = ops["I"].shape[0]
    n_match = len(target)

    # Init poly params (mirrors original script's init)
    poly_params = torch.randn(n_poly, device=device, dtype=dtype) * 0.5
    poly_params[0] = 2.0 + torch.randn(1, device=device, dtype=dtype).item()
    poly_params[-1] = 10.0 + torch.randn(1, device=device, dtype=dtype).item() * 5.0
    poly_params.requires_grad_(True)

    # Init arith params (small magnitude — modulation should be perturbative)
    arith_params = (torch.randn(n_arith, device=device, dtype=dtype) * 0.1).requires_grad_(True)

    # eps as learned scalar (initial small)
    eps = torch.tensor([eps_init], device=device, dtype=dtype, requires_grad=True)

    opt = torch.optim.AdamW([poly_params, arith_params, eps], lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=n_steps, eta_min=lr / 100
    )

    best_loss = float("inf")
    best_params = None
    best_eigs = None
    best_eps = eps_init

    for step in range(n_steps):
        opt.zero_grad()
        try:
            H = make_multiplicative_hamiltonian(
                poly_params, arith_params, eps,
                ops, poly_terms, arith_terms,
            )
            eigs, _ = torch.linalg.eigh(H)
        except Exception:
            break

        pred = eigs[:n_match]
        loss = torch.mean((pred - target) ** 2)

        # Coulomb repulsion (same as original)
        n_rep = min(2 * n_match, N)
        diffs = eigs[:n_rep].unsqueeze(0) - eigs[:n_rep].unsqueeze(1)
        mask = 1.0 - torch.eye(n_rep, device=device, dtype=dtype)
        repulsion = torch.sum(mask / (diffs.abs() + 1e-6)) * 1e-8

        total = loss + repulsion
        if torch.isnan(total):
            break
        total.backward()
        torch.nn.utils.clip_grad_norm_([poly_params, arith_params, eps], 1.0)
        opt.step()
        scheduler.step()

        if loss.item() < best_loss:
            best_loss = loss.item()
            best_params = (poly_params.detach().clone(),
                           arith_params.detach().clone(),
                           float(eps.item()))
            best_eigs = eigs[:n_match].detach().tolist()
            best_eps = float(eps.item())

    return best_loss, best_params, best_eigs, best_eps


def run_multiplicative_search(zeros, n_matrix, n_restarts, n_steps, lr,
                               device, dtype):
    target = torch.tensor(zeros, device=device, dtype=dtype)
    ops = build_operators(n_matrix, device, dtype)

    print(f"\n=== MULTIPLICATIVE Operator Search ===")
    print(f"{len(zeros)} zeros, N={n_matrix}, {n_restarts} restarts, "
          f"{n_steps} steps, device={device}\n")

    all_results = []
    best_global_loss = float("inf")
    best_global_name = ""
    best_global_record = None

    for gen_name, gen_cfg in MULT_GENERATORS.items():
        print(f"\nGenerator: {gen_name} ({gen_cfg['desc']})")
        gen_best_loss = float("inf")
        gen_best_record = None
        t0 = time.time()

        for r in range(n_restarts):
            loss, params, eigs, eps_val = fit_one_restart(
                target, ops,
                gen_cfg["poly_terms"], gen_cfg["arith_terms"],
                gen_cfg["n_poly"], gen_cfg["n_arith"],
                n_steps, lr, device, dtype,
            )
            if loss < gen_best_loss:
                gen_best_loss = loss
                gen_best_record = {
                    "poly_params": params[0].tolist(),
                    "arith_params": params[1].tolist(),
                    "eps": eps_val,
                    "eigs": eigs,
                }
            if (r + 1) % max(1, n_restarts // 5) == 0:
                print(f"  R{r+1}/{n_restarts}: best_loss={gen_best_loss:.6f} "
                      f"eps={gen_best_record['eps']:.4f}")

        elapsed = time.time() - t0
        sp = np.diff(gen_best_record["eigs"]) if gen_best_record else [0]
        sp_var = np.std(sp) / np.mean(sp) if np.mean(sp) > 0 else 0

        result = {
            "generator": gen_name,
            "loss": gen_best_loss,
            "eps_learned": gen_best_record["eps"] if gen_best_record else None,
            "poly_params": dict(zip(gen_cfg["poly_terms"], gen_best_record["poly_params"]))
                if gen_best_record else {},
            "arith_params": dict(zip(gen_cfg["arith_terms"], gen_best_record["arith_params"]))
                if gen_best_record else {},
            "eig_range": [gen_best_record["eigs"][0], gen_best_record["eigs"][-1]]
                if gen_best_record else [0, 0],
            "spacing_var": float(sp_var),
            "time_seconds": round(elapsed, 1),
        }
        all_results.append(result)

        if gen_best_loss < best_global_loss:
            best_global_loss = gen_best_loss
            best_global_name = gen_name
            best_global_record = gen_best_record

        print(f"  BEST: loss={gen_best_loss:.6f}, eps={gen_best_record['eps']:.4f}, "
              f"spvar={sp_var:.4f}, range=[{result['eig_range'][0]:.2f}, "
              f"{result['eig_range'][1]:.2f}], time={elapsed:.1f}s")

    # Target spacing stats
    tsp = np.diff(zeros)
    target_sp_var = np.std(tsp) / np.mean(tsp)

    print("\n" + "=" * 60)
    print(f"BEST OVERALL: {best_global_name}, loss={best_global_loss:.8f}")
    print(f"Target spacing var: {target_sp_var:.4f}")
    if best_global_record:
        print(f"Best eps: {best_global_record['eps']:.6f}")

    output = {
        "test": "riemann_multiplicative",
        "best_generator": best_global_name,
        "best_loss": best_global_loss,
        "best_eps": best_global_record["eps"] if best_global_record else None,
        "target_spacing_var": float(target_sp_var),
        "all_results": all_results,
        "config": {"n_matrix": n_matrix, "n_restarts": n_restarts,
                   "n_steps": n_steps, "device": str(device)},
    }
    with open("riemann_multiplicative_result.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: riemann_multiplicative_result.json")

    # Quick verdict
    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    additive_baseline_mse = 0.289  # ST_n2 best from previous smoke test
    print(f"Additive smoke test best (ST_n2): MSE={additive_baseline_mse}")
    print(f"Multiplicative best ({best_global_name}): MSE={best_global_loss:.6f}")
    if best_global_loss < additive_baseline_mse * 0.5:
        print("VERDICT: Multiplicative SUBSTANTIALLY beats additive (>2x improvement).")
        print("Recommend full Pareto sweep at deeper restarts.")
    elif best_global_loss < additive_baseline_mse * 0.95:
        print("VERDICT: Multiplicative MARGINALLY beats additive.")
        print("Worth investigating with more restarts before committing $15 sweep.")
    elif best_global_loss < additive_baseline_mse * 1.5:
        print("VERDICT: Multiplicative similar to additive — Pareto frontier still")
        print("dominates. Worth running full $15 Pareto sweep to map the curve.")
    else:
        print("VERDICT: Multiplicative MUCH WORSE than additive — operator family")
        print("is genuinely too restrictive. Pivot to sky survey.")
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-zeros", type=int, default=50)
    p.add_argument("--n-matrix", type=int, default=200)
    p.add_argument("--restarts", type=int, default=5)
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--lr", type=float, default=0.01)
    p.add_argument("--cpu", action="store_true")
    args = p.parse_args()

    device = "cpu"
    if not args.cpu and torch.cuda.is_available():
        device = "cuda"
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    zeros = compute_riemann_zeros(args.n_zeros)
    print(f"Zeros: {len(zeros)} loaded, {zeros[0]:.4f} to {zeros[-1]:.4f}")

    run_multiplicative_search(
        zeros=zeros, n_matrix=args.n_matrix, n_restarts=args.restarts,
        n_steps=args.steps, lr=args.lr, device=device, dtype=torch.float64,
    )


if __name__ == "__main__":
    main()
