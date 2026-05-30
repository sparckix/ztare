#!/usr/bin/env python3
"""gp235_section_4_v34_kernel_kfold.py — v34 with kernel embedding axis + 5-fold CV.

Adds 7th axis (kernel_embedding_distance) using pre-computed v28B node2vec
embeddings. Anti-amnesia: reuses prior infrastructure instead of rebuilding.

Same thresholds as v33 (§4.1 <0.50, §4.2 >0.60) + joint tune + 5-fold CV.
"""
from __future__ import annotations
import json, sys, random
from pathlib import Path
from statistics import mean

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
sys.path.insert(0, str(ROOT / "venv/lib/python3.13/site-packages"))

from proof_route_fingerprint import parse_proof_body, levenshtein, jaccard_distance  # type: ignore
from proof_route_fingerprint_v2 import extract_signature_features  # type: ignore
from proof_route_fingerprint_v3_kernel import kernel_embedding_distance  # type: ignore
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore


def compute_components_7axis(file_text_l: str, name_l: str, body_l: str,
                             file_text_r: str, name_r: str, body_r: str) -> tuple:
    fp_l = parse_proof_body(body_l)
    fp_r = parse_proof_body(body_r)
    sig_l = extract_signature_features(file_text_l, name_l)
    sig_r = extract_signature_features(file_text_r, name_r)
    seq_a = fp_l["tactic_family_sequence"]
    seq_b = fp_r["tactic_family_sequence"]
    lev_seq = levenshtein(seq_a, seq_b) / max(max(len(seq_a), len(seq_b)), 1)
    jac_consts = jaccard_distance(fp_l["cited_constants"], fp_r["cited_constants"])
    skel_diff = 0.0 if fp_l["skeleton_kind"] == fp_r["skeleton_kind"] else 1.0
    norm_a = fp_l["normalization_path"]
    norm_b = fp_r["normalization_path"]
    lev_norm = (levenshtein(norm_a, norm_b) / max(max(len(norm_a), len(norm_b)), 1)) if (norm_a or norm_b) else 0.0
    type_diff = 0.0 if sig_l["target_type_head"] == sig_r["target_type_head"] else 1.0
    jac_ids = jaccard_distance(sig_l["signature_identifier_set"], sig_r["signature_identifier_set"])
    # 7th axis: kernel embedding distance over cited constants
    kernel_dist = kernel_embedding_distance(fp_l["cited_constants"], fp_r["cited_constants"])
    return (lev_seq, jac_consts, skel_diff, lev_norm, type_diff, jac_ids, kernel_dist)


def load_pairs_flat(path: str) -> list[dict]:
    raw = json.load(open(path))
    if isinstance(raw, dict):
        return raw.get("pairs") or raw.get("test_set") or raw.get("train_set") or []
    return raw


def extract_all_components_7axis(pairs: list[dict]) -> list[tuple]:
    out = []
    file_text_cache = {}
    for pair in pairs:
        left = pair.get("left", {})
        right = pair.get("right", {})
        fl = left.get("file_path", "")
        fr = right.get("file_path", "")
        if not fl or not fr or not Path(fl).exists() or not Path(fr).exists():
            continue
        if fl not in file_text_cache:
            file_text_cache[fl] = Path(fl).read_text()
        if fr not in file_text_cache:
            file_text_cache[fr] = Path(fr).read_text()
        body_l = extract_proof_body(fl, left.get("name", ""))
        body_r = extract_proof_body(fr, right.get("name", ""))
        if body_l is None or body_r is None:
            continue
        try:
            comps = compute_components_7axis(
                file_text_cache[fl], left["name"], body_l,
                file_text_cache[fr], right["name"], body_r,
            )
            out.append(comps)
        except Exception as e:
            print(f"  skip {pair.get('pair_id')}: {e}")
            continue
    return out


def eval_w(comps: list[tuple], w: tuple, threshold: float, direction: str) -> tuple[int, int]:
    dists = [sum(c*wi for c, wi in zip(c7, w)) for c7 in comps]
    if direction == "under":
        return sum(1 for d in dists if d < threshold), len(dists)
    return sum(1 for d in dists if d > threshold), len(dists)


def main():
    print(f"# v34 §4 with 7-axis fingerprint (surface + signature + KERNEL) + 5-fold CV\n")
    train_pairs = load_pairs_flat("/tmp/gp235_train_v3_alpha_rename_60pairs.json")
    test_pairs = load_pairs_flat("/tmp/gp235_test_set_50pairs.json")
    print(f"TRAIN v3: {len(train_pairs)} pairs")
    print(f"TEST: {len(test_pairs)} pairs")
    print("Extracting 7-axis components...")
    train_comps = extract_all_components_7axis(train_pairs)
    test_comps = extract_all_components_7axis(test_pairs)
    print(f"TRAIN extracted: {len(train_comps)}")
    print(f"TEST extracted: {len(test_comps)}\n")

    if len(train_comps) < 10 or len(test_comps) < 10:
        print("ABORT: insufficient extracted data")
        return 1

    # 7-axis grid — step 0.10 still tractable
    step = 0.10
    levels = [round(x * step, 2) for x in range(1, 9)]  # 0.10..0.80
    grid = []
    for w1 in levels:
        for w2 in levels:
            if w1+w2 > 0.80: continue
            for w3 in levels:
                if w1+w2+w3 > 0.85: continue
                for w4 in levels:
                    if w1+w2+w3+w4 > 0.90: continue
                    for w5 in levels:
                        if w1+w2+w3+w4+w5 > 0.92: continue
                        for w6 in levels:
                            w7 = round(1.0 - w1-w2-w3-w4-w5-w6, 2)
                            if w7 < 0.05 or w7 > 0.80: continue
                            grid.append((w1,w2,w3,w4,w5,w6,w7))
    print(f"Grid: {len(grid)} 7-axis weight tuples\n")

    random.seed(42)
    rt = train_comps.copy(); random.shuffle(rt)
    re = test_comps.copy(); random.shuffle(re)
    K = 5
    train_folds = [rt[i::K] for i in range(K)]
    test_folds = [re[i::K] for i in range(K)]

    fold_results = []
    for k in range(K):
        train_tune = [c for i, f in enumerate(train_folds) if i != k for c in f]
        test_tune = [c for i, f in enumerate(test_folds) if i != k for c in f]
        train_held = train_folds[k]
        test_held = test_folds[k]
        best = None
        best_score = -1.0
        for w in grid:
            iN, iD = eval_w(train_tune, w, 0.50, "under")
            jN, jD = eval_w(test_tune, w, 0.60, "over")
            score = 0.5*(iN/max(iD,1)) + 0.5*(jN/max(jD,1))
            if score > best_score:
                best_score = score
                best = w
        hiN, hiD = eval_w(train_held, best, 0.50, "under")
        joN, joD = eval_w(test_held, best, 0.60, "over")
        intra_pct = hiN/max(hiD,1)
        inter_pct = joN/max(joD,1)
        fold_results.append({
            "fold": k, "weights": best,
            "intra_pct": intra_pct, "inter_pct": inter_pct,
            "n_held_train": len(train_held), "n_held_test": len(test_held),
        })
        print(f"Fold {k}: w={best} | intra {hiN}/{hiD} ({100*intra_pct:.0f}%) inter {joN}/{joD} ({100*inter_pct:.0f}%)")

    mean_intra = mean(r["intra_pct"] for r in fold_results)
    mean_inter = mean(r["inter_pct"] for r in fold_results)
    joint_passes = sum(1 for r in fold_results if r["intra_pct"] >= 0.80 and r["inter_pct"] >= 0.80)

    print(f"\n## Aggregated across {K} folds (KERNEL augmented)")
    print(f"   mean intra: {100*mean_intra:.1f}% (v33 CV was 94.6%)")
    print(f"   mean inter: {100*mean_inter:.1f}% (v33 CV was 68.7% — target ≥80%)")
    print(f"   joint passing: {joint_passes}/{K} (v33 was 1/5)")

    print(f"\n## Honest verdict")
    if mean_intra >= 0.80 and mean_inter >= 0.80 and joint_passes >= 3:
        print(f"   PRIMITIVE PASSES under 5-fold CV with kernel augmentation")
        print(f"   → ready to write GP-236 architecture seam ON TOP of this validated primitive")
    elif mean_inter < 0.80:
        print(f"   Inter generalization still weak ({100*mean_inter:.0f}%); needs larger data or more signal")
    else:
        print(f"   Marginal — improvements over v33 but not yet strict pass")

    out = {
        "version": "v34",
        "kernel_axis_added": True,
        "n_train_extracted": len(train_comps),
        "n_test_extracted": len(test_comps),
        "mean_intra": mean_intra,
        "mean_inter": mean_inter,
        "joint_passing": joint_passes,
        "per_fold": fold_results,
        "improvement_over_v33": {
            "intra_delta": mean_intra - 0.946,
            "inter_delta": mean_inter - 0.687,
        },
        "verdict": "PASS" if (mean_intra >= 0.80 and mean_inter >= 0.80 and joint_passes >= 3) else "FAIL",
    }
    out_path = ROOT / "analytics/public/leanmill/results/gp235_section_4_v34_kernel_results.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
