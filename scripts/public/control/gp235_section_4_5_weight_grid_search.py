#!/usr/bin/env python3
"""gp235_section_4_5_weight_grid_search.py — Per §4.5 ablation dominance prep.

Grid search over (w1, w2, w3, w4) with constraint w1+w2+w3+w4=1.0. For each
weight tuple, compute the §4.1 + §4.2 pass-rates on TRAIN + TEST sets.

This answers: CAN the surface_fingerprint primitive structurally pass the
pre-registered §4 gates at ANY weight choice? If even optimal weights cap
under 80%, the surface-only fingerprint is fundamentally limited and the
kernel_fingerprint augmentation is required.

To avoid leakage:
- Split current TRAIN (30 pairs) into TUNE (first 15) and HELD (last 15).
- Grid-search optimal weights on TUNE only.
- Lock weights; report §4.1 pass-rate on HELD (the proper held-out).
- Report §4.2 pass-rate on TEST (independent dataset).
- Also report optimal pass-rates ASSUMING all data is fair game (overfit
  upper bound), so we know the structural ceiling.

Grid: w1 ∈ {0.1, 0.2, ..., 0.8}, w2, w3, w4 similar, with sum-to-1 constraint
and each ≥ 0.05. ~285 weight tuples evaluated.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from statistics import mean
from itertools import product

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from proof_route_fingerprint import parse_proof_body, surface_distance, levenshtein, jaccard_distance  # type: ignore
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore


def load_train_pairs() -> list[dict]:
    data = json.load(open("/tmp/gp235_train_set_30pairs.json"))
    return data if isinstance(data, list) else data.get("pairs", [])


def load_test_pairs() -> list[dict]:
    raw = json.load(open("/tmp/gp235_test_set_50pairs.json"))
    if isinstance(raw, dict):
        return raw.get("test_set") or raw.get("pairs") or []
    return raw


def extract_fingerprints(pairs: list[dict]) -> list[dict]:
    """Pre-compute fingerprints once so the grid search is fast."""
    out = []
    for pair in pairs:
        left = pair.get("left", {})
        right = pair.get("right", {})
        body_l = extract_proof_body(left.get("file_path", ""), left.get("name", ""))
        body_r = extract_proof_body(right.get("file_path", ""), right.get("name", ""))
        if body_l is None or body_r is None:
            continue
        fp_l = parse_proof_body(body_l)
        fp_r = parse_proof_body(body_r)
        out.append({
            "pair_id": pair.get("pair_id", "?"),
            "fp_l": fp_l,
            "fp_r": fp_r,
        })
    return out


def compute_components(fp_l: dict, fp_r: dict) -> tuple[float, float, float, float]:
    """The 4 distance components (un-weighted)."""
    seq_a = fp_l["tactic_family_sequence"]
    seq_b = fp_r["tactic_family_sequence"]
    lev_seq = levenshtein(seq_a, seq_b) / max(max(len(seq_a), len(seq_b)), 1)
    jac_consts = jaccard_distance(fp_l["cited_constants"], fp_r["cited_constants"])
    skel_diff = 0.0 if fp_l["skeleton_kind"] == fp_r["skeleton_kind"] else 1.0
    norm_a = fp_l["normalization_path"]
    norm_b = fp_r["normalization_path"]
    lev_norm = (levenshtein(norm_a, norm_b) / max(max(len(norm_a), len(norm_b)), 1)) if (norm_a or norm_b) else 0.0
    return (lev_seq, jac_consts, skel_diff, lev_norm)


def evaluate_weights(components_list: list[tuple], weights: tuple, threshold: float, direction: str) -> tuple[int, int, float]:
    """direction = 'under' (intra) or 'over' (inter). Returns (n_pass, n_total, mean_dist)."""
    w1, w2, w3, w4 = weights
    dists = [w1*c[0] + w2*c[1] + w3*c[2] + w4*c[3] for c in components_list]
    if direction == "under":
        n_pass = sum(1 for d in dists if d < threshold)
    else:
        n_pass = sum(1 for d in dists if d > threshold)
    return n_pass, len(dists), mean(dists) if dists else 0.0


def main():
    train_pairs = load_train_pairs()
    test_pairs = load_test_pairs()
    print(f"# §4.5 Weight grid search\n")
    print(f"TRAIN raw: {len(train_pairs)} pairs")
    print(f"TEST raw: {len(test_pairs)} pairs")

    train_fps = extract_fingerprints(train_pairs)
    test_fps = extract_fingerprints(test_pairs)
    print(f"TRAIN with proof bodies: {len(train_fps)}")
    print(f"TEST with proof bodies: {len(test_fps)}")

    # Split TRAIN 50/50 into TUNE / HELD for honest evaluation
    n_train = len(train_fps)
    tune_set = train_fps[:n_train//2]
    held_set = train_fps[n_train//2:]
    print(f"TUNE: {len(tune_set)}, HELD: {len(held_set)}")

    # Pre-compute components for all sets (un-weighted)
    tune_comps = [compute_components(p["fp_l"], p["fp_r"]) for p in tune_set]
    held_comps = [compute_components(p["fp_l"], p["fp_r"]) for p in held_set]
    test_comps = [compute_components(p["fp_l"], p["fp_r"]) for p in test_fps]

    # Grid search weights on TUNE only.
    # Objective: maximize intra-pass-rate AND inter-pass-rate simultaneously.
    # Use a weighted sum: 0.5 * intra_pass_pct + 0.5 * inter_pass_pct
    # (where intra uses TUNE under 0.30 and inter uses TEST over 0.60).
    # NOTE: this leaks TEST into the tuning if we use TEST inter directly.
    # Strict: tune ONLY on TUNE intra. Then lock weights and evaluate.

    grid_step = 0.05
    candidates = []
    for w1 in [round(x * grid_step, 2) for x in range(1, 20)]:  # 0.05..0.95
        for w2 in [round(x * grid_step, 2) for x in range(1, 20)]:
            for w3 in [round(x * grid_step, 2) for x in range(1, 20)]:
                w4 = round(1.0 - w1 - w2 - w3, 2)
                if w4 < 0.05 or w4 > 0.85:
                    continue
                candidates.append((w1, w2, w3, w4))

    print(f"Grid candidates: {len(candidates)}")

    # For each candidate, eval on TUNE intra (target: maximize pairs under 0.30).
    # We do NOT use TEST during tuning.
    best_tune_score = -1.0
    best_tune_weights = None
    for w in candidates:
        n_under, n_tot, mean_d = evaluate_weights(tune_comps, w, 0.30, "under")
        score = n_under / n_tot if n_tot else 0
        if score > best_tune_score:
            best_tune_score = score
            best_tune_weights = w

    print(f"\n## Optimal weights on TUNE (intra-cluster): {best_tune_weights}")
    print(f"## TUNE intra-pass rate at optimal: {100*best_tune_score:.1f}%")

    # Lock weights, evaluate on HELD + TEST
    held_n, held_tot, held_mean = evaluate_weights(held_comps, best_tune_weights, 0.30, "under")
    test_n, test_tot, test_mean = evaluate_weights(test_comps, best_tune_weights, 0.60, "over")
    print(f"\n## HELD §4.1 with locked optimal weights: {held_n}/{held_tot} = {100*held_n/held_tot:.1f}% (target ≥80%)")
    print(f"## TEST §4.2 with locked optimal weights: {test_n}/{test_tot} = {100*test_n/test_tot:.1f}% (target ≥80%)")
    print(f"## Mean intra (HELD): {held_mean:.3f}")
    print(f"## Mean inter (TEST): {test_mean:.3f}")
    print(f"## Separation: {test_mean - held_mean:.3f}")

    # Also: what's the ABSOLUTE BEST possible if we OVERFIT to both TUNE+HELD?
    # (Upper bound — shows the ceiling.)
    all_train_comps = tune_comps + held_comps
    best_overfit_intra = max(
        evaluate_weights(all_train_comps, w, 0.30, "under")[0] / len(all_train_comps)
        for w in candidates
    )
    best_overfit_inter = max(
        evaluate_weights(test_comps, w, 0.60, "over")[0] / len(test_comps)
        for w in candidates
    )
    print(f"\n## CEILING (overfit upper bound):")
    print(f"   §4.1 intra: best possible = {100*best_overfit_intra:.1f}%")
    print(f"   §4.2 inter: best possible = {100*best_overfit_inter:.1f}%")

    # Verdict
    print(f"\n## Honest verdict")
    if held_n/held_tot >= 0.80 and test_n/test_tot >= 0.80:
        print(f"   PRIMITIVE PASSES §4 with optimal weights — proceed to §4.5 ablation dominance test")
    elif best_overfit_intra < 0.80 or best_overfit_inter < 0.80:
        print(f"   PRIMITIVE STRUCTURALLY CANNOT PASS §4 with surface_fingerprint alone")
        print(f"   (Even overfitting to all data, ceiling is intra={100*best_overfit_intra:.1f}% / inter={100*best_overfit_inter:.1f}%)")
        print(f"   → kernel_fingerprint augmentation is REQUIRED, or TRAIN set definition needs change")
    else:
        print(f"   Primitive can theoretically pass (ceiling allows), but the TUNE→HELD generalization didn't carry")
        print(f"   → likely TRAIN-set definition issue (statement-near vs proof-route-near)")
        print(f"   → wait for v2 TRAIN set with alpha-renamed proof-body pairs, then re-run")

    # Save
    out = {
        "n_train_with_proofs": len(train_fps),
        "n_test_with_proofs": len(test_fps),
        "n_tune": len(tune_set),
        "n_held": len(held_set),
        "optimal_weights_on_tune": best_tune_weights,
        "tune_intra_pass_pct": best_tune_score,
        "held_intra_pass_pct": held_n/held_tot if held_tot else None,
        "held_mean_distance": held_mean,
        "test_inter_pass_pct": test_n/test_tot if test_tot else None,
        "test_mean_distance": test_mean,
        "separation": test_mean - held_mean,
        "ceiling_intra_overfit": best_overfit_intra,
        "ceiling_inter_overfit": best_overfit_inter,
    }
    out_path = ROOT / "analytics/public/leanmill/results/gp235_section_4_5_weight_grid_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
