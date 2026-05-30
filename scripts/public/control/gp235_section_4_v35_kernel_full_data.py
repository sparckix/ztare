#!/usr/bin/env python3
"""gp235_section_4_v35_kernel_full_data.py — v35 with kernel + proof_body_snippet fallback.

Anti-amnesia fix: TEST set provides proof_body_snippet directly (agent already
extracted it). Use that when file-based extraction fails, increasing effective
TEST size from 29 → ~50. Also finer 7-axis grid with kernel-axis-emphasized
slice (w7 ∈ {0.10, 0.20, 0.30, 0.40, 0.50}).
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


def get_proof_body(file_path: str, name: str, fallback_snippet: str | None = None) -> str | None:
    """Try file extraction first; fall back to provided proof_body_snippet."""
    body = extract_proof_body(file_path, name)
    if body:
        return body
    if fallback_snippet:
        return fallback_snippet.strip()
    return None


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
    kernel_dist = kernel_embedding_distance(fp_l["cited_constants"], fp_r["cited_constants"])
    return (lev_seq, jac_consts, skel_diff, lev_norm, type_diff, jac_ids, kernel_dist)


def load_pairs_flat(path: str) -> list[dict]:
    raw = json.load(open(path))
    if isinstance(raw, dict):
        return raw.get("pairs") or raw.get("test_set") or raw.get("train_set") or []
    return raw


def extract_components_v35(pairs: list[dict], label: str) -> list[tuple]:
    out = []
    file_text_cache = {}
    n_file = 0
    n_snippet = 0
    n_fail = 0
    for pair in pairs:
        left = pair.get("left", {})
        right = pair.get("right", {})
        fl = left.get("file_path", "")
        fr = right.get("file_path", "")
        if not fl or not fr or not Path(fl).exists() or not Path(fr).exists():
            n_fail += 1; continue
        if fl not in file_text_cache:
            file_text_cache[fl] = Path(fl).read_text()
        if fr not in file_text_cache:
            file_text_cache[fr] = Path(fr).read_text()
        body_l = get_proof_body(fl, left.get("name", ""), left.get("proof_body_snippet") or left.get("proof_body"))
        body_r = get_proof_body(fr, right.get("name", ""), right.get("proof_body_snippet") or right.get("proof_body"))
        if body_l is None or body_r is None:
            n_fail += 1; continue
        # Track source
        body_l_file = extract_proof_body(fl, left.get("name", ""))
        body_r_file = extract_proof_body(fr, right.get("name", ""))
        if body_l_file and body_r_file:
            n_file += 1
        else:
            n_snippet += 1
        try:
            out.append(compute_components_7axis(
                file_text_cache[fl], left["name"], body_l,
                file_text_cache[fr], right["name"], body_r,
            ))
        except Exception:
            n_fail += 1
    print(f"  {label}: extracted {len(out)} (file-based {n_file}, snippet-fallback {n_snippet}, failed {n_fail})")
    return out


def eval_w(comps: list[tuple], w: tuple, threshold: float, direction: str) -> tuple[int, int]:
    dists = [sum(c*wi for c, wi in zip(c7, w)) for c7 in comps]
    if direction == "under":
        return sum(1 for d in dists if d < threshold), len(dists)
    return sum(1 for d in dists if d > threshold), len(dists)


def main():
    print("# v35 §4 with kernel + proof_body_snippet fallback + finer grid\n")
    train_pairs = load_pairs_flat("/tmp/gp235_train_v3_alpha_rename_60pairs.json")
    test_pairs = load_pairs_flat("/tmp/gp235_test_set_50pairs.json")
    print(f"TRAIN v3: {len(train_pairs)} | TEST: {len(test_pairs)}\n")
    train_comps = extract_components_v35(train_pairs, "TRAIN")
    test_comps = extract_components_v35(test_pairs, "TEST")
    print()

    if len(train_comps) < 10 or len(test_comps) < 10:
        print("ABORT: insufficient data")
        return 1

    # Finer grid: w7 (kernel) explored at 0.05/0.10/0.20/0.30/0.40/0.50
    step = 0.10
    levels = [round(x * step, 2) for x in range(1, 9)]
    kernel_levels = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
    grid = []
    for w7 in kernel_levels:
        remaining = round(1.0 - w7, 2)
        for w1 in levels:
            if w1 > remaining: continue
            for w2 in levels:
                if w1+w2 > remaining-0.20: continue
                for w3 in levels:
                    if w1+w2+w3 > remaining-0.15: continue
                    for w4 in levels:
                        if w1+w2+w3+w4 > remaining-0.10: continue
                        for w5 in levels:
                            w6 = round(remaining - w1-w2-w3-w4-w5, 2)
                            if w6 < 0.05 or w6 > 0.80: continue
                            grid.append((w1,w2,w3,w4,w5,w6,w7))
    print(f"Grid: {len(grid)} 7-axis tuples (kernel-emphasized)\n")

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
        best = None; best_score = -1
        for w in grid:
            iN, iD = eval_w(train_tune, w, 0.50, "under")
            jN, jD = eval_w(test_tune, w, 0.60, "over")
            score = 0.5*(iN/max(iD,1)) + 0.5*(jN/max(jD,1))
            if score > best_score:
                best_score = score; best = w
        hiN, hiD = eval_w(train_held, best, 0.50, "under")
        joN, joD = eval_w(test_held, best, 0.60, "over")
        intra_pct = hiN/max(hiD,1)
        inter_pct = joN/max(joD,1)
        fold_results.append({"fold": k, "weights": best, "intra_pct": intra_pct, "inter_pct": inter_pct,
                             "n_held_train": len(train_held), "n_held_test": len(test_held)})
        print(f"Fold {k}: w={best} | intra {hiN}/{hiD} ({100*intra_pct:.0f}%) inter {joN}/{joD} ({100*inter_pct:.0f}%)")

    mean_intra = mean(r["intra_pct"] for r in fold_results)
    mean_inter = mean(r["inter_pct"] for r in fold_results)
    joint_passes = sum(1 for r in fold_results if r["intra_pct"] >= 0.80 and r["inter_pct"] >= 0.80)

    print(f"\n## Aggregated across {K} folds (v35: kernel + full data)")
    print(f"   mean intra: {100*mean_intra:.1f}%  (v33: 94.6%, v34: 94.6%)")
    print(f"   mean inter: {100*mean_inter:.1f}%  (v33: 68.7%, v34: 72.0%, target ≥80%)")
    print(f"   joint passing: {joint_passes}/{K}  (v33: 1, v34: 2)")

    print(f"\n## Verdict")
    if mean_intra >= 0.80 and mean_inter >= 0.80 and joint_passes >= 3:
        print("   PRIMITIVE PASSES v35 fair CV — generalization confirmed")
        print("   → may write GP-236 architecture seam citing this primitive")
    elif mean_inter >= 0.80:
        print(f"   inter mean passes ({100*mean_inter:.0f}%) but per-fold joint not yet ≥3/5")
    else:
        print(f"   inter mean still {100*mean_inter:.0f}% — closer but not yet")

    out_path = ROOT / "analytics/public/leanmill/results/gp235_section_4_v35_results.json"
    out_path.write_text(json.dumps({
        "version": "v35",
        "n_train_extracted": len(train_comps),
        "n_test_extracted": len(test_comps),
        "mean_intra": mean_intra,
        "mean_inter": mean_inter,
        "joint_passes": joint_passes,
        "per_fold": fold_results,
        "grid_size": len(grid),
        "verdict": "PASS" if (mean_intra >= 0.80 and mean_inter >= 0.80 and joint_passes >= 3) else "FAIL",
    }, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
