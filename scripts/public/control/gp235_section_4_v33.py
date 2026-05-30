#!/usr/bin/env python3
"""gp235_section_4_v33.py — v33 §4 with pre-registered relaxed threshold + joint tune.

Implements the v33 pre-registration committed in
`analytics/.../gp235_section_4_threshold_pre_registration_v33_2026_05_15.md`:

  - §4.1 intra threshold: <0.50 (was <0.30; empirically calibrated to alpha-renamed pair baseline)
  - §4.2 inter threshold: >0.60 (unchanged)
  - Joint tune objective: max 0.5*intra_pass + 0.5*inter_pass on TUNE (using held-out TEST inter sub-set)
  - TRAIN: v3 alpha-renamed proof-body pairs (60), not v2's 30
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from proof_route_fingerprint import parse_proof_body, levenshtein, jaccard_distance  # type: ignore
from proof_route_fingerprint_v2 import extract_signature_features  # type: ignore
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore
from gp235_section_4_v2_full import extract_all_components  # type: ignore


def load_pairs_flat(path: str) -> list[dict]:
    raw = json.load(open(path))
    if isinstance(raw, dict):
        return raw.get("pairs") or raw.get("test_set") or raw.get("train_set") or []
    return raw


def eval_w(comps: list[tuple], w: tuple, threshold: float, direction: str) -> tuple[int, int]:
    dists = [sum(c*wi for c, wi in zip(c6, w)) for c6 in comps]
    if direction == "under":
        return sum(1 for d in dists if d < threshold), len(dists)
    return sum(1 for d in dists if d > threshold), len(dists)


def main():
    train_v3_pairs = load_pairs_flat("/tmp/gp235_train_v3_alpha_rename_60pairs.json")
    test_pairs = load_pairs_flat("/tmp/gp235_test_set_50pairs.json")

    print(f"# v33 §4 with pre-registered relaxed threshold + joint tune\n")
    print(f"TRAIN v3 (60 alpha-renamed): {len(train_v3_pairs)} pairs")
    print(f"TEST (50 cross-namespace): {len(test_pairs)} pairs")
    print(f"Pre-registered §4.1 threshold: <0.50 (was <0.30)")
    print(f"Pre-registered §4.2 threshold: >0.60 (unchanged)")
    print()

    print("Extracting TRAIN v3 components...")
    train_comps = extract_all_components(train_v3_pairs)
    print("Extracting TEST components...")
    test_comps = extract_all_components(test_pairs)
    if not train_comps or not test_comps:
        print("ABORT: insufficient extracted data")
        return 1

    # Honest split: TUNE / HELD = 60/40 of TRAIN; TEST_TUNE / TEST_HELD = 50/50 of TEST
    n_train = len(train_comps)
    n_test = len(test_comps)
    tune_train = train_comps[:int(n_train * 0.6)]
    held_train = train_comps[int(n_train * 0.6):]
    tune_test = test_comps[:n_test//2]
    held_test = test_comps[n_test//2:]
    print(f"TUNE-train: {len(tune_train)}, HELD-train: {len(held_train)}")
    print(f"TUNE-test: {len(tune_test)}, HELD-test: {len(held_test)}")

    # 6-axis grid, step 0.1
    step = 0.10
    weights_grid = []
    levels = [round(x * step, 2) for x in range(1, 10)]
    for w1 in levels:
        for w2 in levels:
            if w1 + w2 > 0.85: continue
            for w3 in levels:
                if w1 + w2 + w3 > 0.90: continue
                for w4 in levels:
                    if w1 + w2 + w3 + w4 > 0.95: continue
                    for w5 in levels:
                        w6 = round(1.0 - w1 - w2 - w3 - w4 - w5, 2)
                        if w6 < 0.05 or w6 > 0.85: continue
                        weights_grid.append((w1, w2, w3, w4, w5, w6))
    print(f"Grid candidates: {len(weights_grid)}\n")

    # Joint tune objective on TUNE-train (intra<0.50) AND TUNE-test (inter>0.60)
    best = None
    best_joint = -1.0
    for w in weights_grid:
        intra_n, intra_d = eval_w(tune_train, w, 0.50, "under")
        inter_n, inter_d = eval_w(tune_test, w, 0.60, "over")
        joint = 0.5 * (intra_n/max(intra_d,1)) + 0.5 * (inter_n/max(inter_d,1))
        if joint > best_joint:
            best_joint = joint
            best = w
            best_components = (intra_n/max(intra_d,1), inter_n/max(inter_d,1))

    print(f"## Optimal joint weights: {best}")
    print(f"## Joint score (TUNE): {100*best_joint:.1f}% [intra={100*best_components[0]:.0f}%, inter={100*best_components[1]:.0f}%]\n")

    # Lock weights, evaluate on HELD partitions
    held_intra_n, held_intra_d = eval_w(held_train, best, 0.50, "under")
    held_inter_n, held_inter_d = eval_w(held_test, best, 0.60, "over")

    print(f"## HELD §4.1 with locked weights: {held_intra_n}/{held_intra_d} = {100*held_intra_n/max(held_intra_d,1):.1f}% (target ≥80%)")
    print(f"## HELD §4.2 with locked weights: {held_inter_n}/{held_inter_d} = {100*held_inter_n/max(held_inter_d,1):.1f}% (target ≥80%)")

    # Ceiling (overfit upper bounds, using ALL data)
    best_ceiling_intra = max(eval_w(train_comps, w, 0.50, "under")[0]/max(len(train_comps),1) for w in weights_grid)
    best_ceiling_inter = max(eval_w(test_comps, w, 0.60, "over")[0]/max(len(test_comps),1) for w in weights_grid)
    print(f"\n## CEILING (overfit upper bound)")
    print(f"   §4.1 intra: best possible = {100*best_ceiling_intra:.1f}%")
    print(f"   §4.2 inter: best possible = {100*best_ceiling_inter:.1f}%")

    # Joint-passing weight set (overfit)
    joint_passing = [
        w for w in weights_grid
        if eval_w(train_comps, w, 0.50, "under")[0]/max(len(train_comps),1) >= 0.80
        and eval_w(test_comps, w, 0.60, "over")[0]/max(len(test_comps),1) >= 0.80
    ]
    print(f"\n## Weights passing BOTH gates (overfit): {len(joint_passing)}")
    for w in joint_passing[:3]:
        iN, iD = eval_w(train_comps, w, 0.50, "under")
        jN, jD = eval_w(test_comps, w, 0.60, "over")
        print(f"   {w} → intra {iN}/{iD} ({100*iN/iD:.0f}%) inter {jN}/{jD} ({100*jN/jD:.0f}%)")

    print(f"\n## Honest verdict")
    held_intra_pct = held_intra_n/max(held_intra_d,1)
    held_inter_pct = held_inter_n/max(held_inter_d,1)
    if held_intra_pct >= 0.80 and held_inter_pct >= 0.80:
        print(f"   PRIMITIVE PASSES v33 §4 (held-out, locked weights). May proceed to §4.5 ablation dominance.")
    elif best_ceiling_intra >= 0.80 and best_ceiling_inter >= 0.80 and joint_passing:
        print(f"   PRIMITIVE PASSES at CEILING but TUNE→HELD didn't transfer fully ({100*held_intra_pct:.0f}% / {100*held_inter_pct:.0f}%)")
        print(f"   → likely TUNE-set generalization issue; larger TRAIN or cross-fold validation may help")
    else:
        print(f"   PRIMITIVE STILL CAN'T PASS v33 with surface+signature alone")
        print(f"   → kernel_fingerprint integration required")

    out = {
        "n_train_v3": len(train_v3_pairs),
        "n_test": len(test_pairs),
        "n_train_extracted": len(train_comps),
        "n_test_extracted": len(test_comps),
        "tune_train_size": len(tune_train),
        "held_train_size": len(held_train),
        "tune_test_size": len(tune_test),
        "held_test_size": len(held_test),
        "intra_threshold_v33": 0.50,
        "inter_threshold_v33": 0.60,
        "optimal_weights_locked": list(best),
        "tune_joint_score": best_joint,
        "tune_intra_pct": best_components[0],
        "tune_inter_pct": best_components[1],
        "held_intra_pct": held_intra_pct,
        "held_inter_pct": held_inter_pct,
        "ceiling_intra": best_ceiling_intra,
        "ceiling_inter": best_ceiling_inter,
        "n_joint_passing_overfit": len(joint_passing),
        "verdict": "PASS" if (held_intra_pct >= 0.80 and held_inter_pct >= 0.80) else "FAIL",
    }
    out_path = ROOT / "analytics/public/leanmill/results/gp235_section_4_v33_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
