#!/usr/bin/env python3
"""gp235_section_4_v33_kfold.py — 5-fold CV for honest §4 generalization.

After v33 single-split showed CEILING passes but TUNE→HELD generalization
fragile, 5-fold CV gives a more honest estimate.

For each fold:
  - Train weights on (4 folds TRAIN + 4 folds TEST) joint objective
  - Evaluate on (1 fold TRAIN intra + 1 fold TEST inter)
  - Record per-fold pass rates

Aggregate: mean intra-pass, mean inter-pass, and joint pass rate.
"""
from __future__ import annotations
import json, sys, random
from pathlib import Path
from statistics import mean

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from gp235_section_4_v2_full import extract_all_components  # type: ignore
from gp235_section_4_v33 import load_pairs_flat, eval_w  # type: ignore


def main():
    train_v3 = load_pairs_flat("/tmp/gp235_train_v3_alpha_rename_60pairs.json")
    test = load_pairs_flat("/tmp/gp235_test_set_50pairs.json")
    print(f"# v33 §4 5-fold CV — honest generalization estimate\n")

    print("Extracting...")
    train_comps = extract_all_components(train_v3)
    test_comps = extract_all_components(test)

    if len(train_comps) < 10 or len(test_comps) < 10:
        print(f"ABORT: too few extracted components")
        return 1

    # Shuffle deterministically and split into 5 folds
    random.seed(42)
    rt = train_comps.copy()
    re = test_comps.copy()
    random.shuffle(rt)
    random.shuffle(re)
    K = 5
    train_folds = [rt[i::K] for i in range(K)]
    test_folds = [re[i::K] for i in range(K)]

    # 6-axis grid
    step = 0.10
    grid = []
    levels = [round(x * step, 2) for x in range(1, 10)]
    for w1 in levels:
        for w2 in levels:
            if w1+w2 > 0.85: continue
            for w3 in levels:
                if w1+w2+w3 > 0.90: continue
                for w4 in levels:
                    if w1+w2+w3+w4 > 0.95: continue
                    for w5 in levels:
                        w6 = round(1.0-w1-w2-w3-w4-w5, 2)
                        if w6 < 0.05 or w6 > 0.85: continue
                        grid.append((w1,w2,w3,w4,w5,w6))

    fold_results = []
    print(f"\nGrid: {len(grid)} weight tuples, K={K} folds\n")

    for k in range(K):
        train_tune = [c for i, fold in enumerate(train_folds) if i != k for c in fold]
        test_tune = [c for i, fold in enumerate(test_folds) if i != k for c in fold]
        train_held = train_folds[k]
        test_held = test_folds[k]

        # Pick best weights on (train_tune intra<0.50) + (test_tune inter>0.60)
        best = None
        best_score = -1.0
        for w in grid:
            iN, iD = eval_w(train_tune, w, 0.50, "under")
            jN, jD = eval_w(test_tune, w, 0.60, "over")
            score = 0.5 * (iN/max(iD,1)) + 0.5 * (jN/max(jD,1))
            if score > best_score:
                best_score = score
                best = w

        held_intra_n, held_intra_d = eval_w(train_held, best, 0.50, "under")
        held_inter_n, held_inter_d = eval_w(test_held, best, 0.60, "over")
        intra_pct = held_intra_n/max(held_intra_d,1)
        inter_pct = held_inter_n/max(held_inter_d,1)
        fold_results.append({
            "fold": k,
            "weights": best,
            "tune_joint_score": best_score,
            "held_intra_pct": intra_pct,
            "held_inter_pct": inter_pct,
            "n_held_train": len(train_held),
            "n_held_test": len(test_held),
        })
        print(f"Fold {k}: weights={best} | HELD intra {held_intra_n}/{held_intra_d} ({100*intra_pct:.0f}%) inter {held_inter_n}/{held_inter_d} ({100*inter_pct:.0f}%)")

    mean_intra = mean(r["held_intra_pct"] for r in fold_results)
    mean_inter = mean(r["held_inter_pct"] for r in fold_results)
    joint_passes = sum(1 for r in fold_results if r["held_intra_pct"] >= 0.80 and r["held_inter_pct"] >= 0.80)

    print(f"\n## Aggregated across {K} folds")
    print(f"   mean HELD intra: {100*mean_intra:.1f}%")
    print(f"   mean HELD inter: {100*mean_inter:.1f}%")
    print(f"   folds passing BOTH gates: {joint_passes}/{K}")

    print(f"\n## Honest verdict")
    if mean_intra >= 0.80 and mean_inter >= 0.80 and joint_passes >= 3:
        print(f"   PRIMITIVE PASSES under 5-fold CV — generalization is real")
    elif mean_intra >= 0.80 and mean_inter >= 0.80:
        print(f"   PRIMITIVE marginal — means pass but per-fold joint-pass count is low ({joint_passes}/{K})")
    elif mean_inter < 0.80:
        print(f"   PRIMITIVE WEAK on inter-cluster generalization (mean {100*mean_inter:.0f}% < 80%)")
        print(f"   → kernel_fingerprint integration probably required for production use")
    else:
        print(f"   PRIMITIVE FAILS under 5-fold CV")

    out = {
        "n_folds": K,
        "mean_intra": mean_intra,
        "mean_inter": mean_inter,
        "folds_passing_both": joint_passes,
        "per_fold": fold_results,
    }
    out_path = ROOT / "analytics/public/leanmill/results/gp235_section_4_v33_kfold_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
