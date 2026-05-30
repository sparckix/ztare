#!/usr/bin/env python3
"""gp235_section_4_v2_full.py — §4 with v2 fingerprint + v2 TRAIN.

Combines two v32 improvements:
  - v2 fingerprint (proof_route_fingerprint_v2): 6-axis with signature features
  - v2 TRAIN (alpha-renamed proof-body pairs, not `'`-suffix statement pairs)

Honest TUNE/HELD split + locked-weight evaluation + overfit ceiling.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from statistics import mean
from itertools import product

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from proof_route_fingerprint import parse_proof_body, levenshtein, jaccard_distance  # type: ignore
from proof_route_fingerprint_v2 import extract_signature_features  # type: ignore
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore


def load_pairs(path: str, key: str = None) -> list[dict]:
    raw = json.load(open(path))
    if isinstance(raw, dict):
        if key and key in raw:
            return raw[key]
        for k in ["test_set", "pairs", "train_set"]:
            if k in raw:
                return raw[k]
        return []
    return raw


def compute_components_v2(file_text_l: str, name_l: str, file_text_r: str, name_r: str, body_l: str, body_r: str) -> tuple:
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
    return (lev_seq, jac_consts, skel_diff, lev_norm, type_diff, jac_ids)


def extract_all_components(pairs: list[dict]) -> list[tuple]:
    """For each pair, extract proof body for both sides + signature features.
    Return list of 6-tuple components for pairs where extraction succeeded."""
    out = []
    fail_count = 0
    file_text_cache = {}
    for pair in pairs:
        left = pair.get("left", {})
        right = pair.get("right", {})
        fl = left.get("file_path", "")
        fr = right.get("file_path", "")
        if not fl or not fr or not Path(fl).exists() or not Path(fr).exists():
            fail_count += 1
            continue
        if fl not in file_text_cache:
            file_text_cache[fl] = Path(fl).read_text()
        if fr not in file_text_cache:
            file_text_cache[fr] = Path(fr).read_text()
        body_l = extract_proof_body(fl, left.get("name", ""))
        body_r = extract_proof_body(fr, right.get("name", ""))
        if body_l is None or body_r is None:
            fail_count += 1
            continue
        try:
            comps = compute_components_v2(
                file_text_cache[fl], left["name"],
                file_text_cache[fr], right["name"],
                body_l, body_r,
            )
            out.append(comps)
        except Exception:
            fail_count += 1
    print(f"  extracted: {len(out)} / {len(pairs)} ({fail_count} failures)")
    return out


def eval_w(comps_list: list[tuple], w: tuple, threshold: float, direction: str) -> tuple[int, int]:
    dists = [sum(c*wi for c, wi in zip(c6, w)) for c6 in comps_list]
    if direction == "under":
        n_pass = sum(1 for d in dists if d < threshold)
    else:
        n_pass = sum(1 for d in dists if d > threshold)
    return n_pass, len(dists)


def main():
    train_v2 = load_pairs("/tmp/gp235_train_v2_alpha_rename_30pairs.json")
    test = load_pairs("/tmp/gp235_test_set_50pairs.json", key="test_set")

    print(f"# v2 §4 evaluation (v2 fingerprint + v2 TRAIN)\n")
    print(f"TRAIN v2 (alpha-renamed): {len(train_v2)} pairs")
    print(f"TEST (cross-namespace): {len(test)} pairs")

    print(f"\nExtracting TRAIN v2 components...")
    train_comps = extract_all_components(train_v2)
    print(f"Extracting TEST components...")
    test_comps = extract_all_components(test)

    if len(train_comps) < 4:
        print(f"\nABORT: too few TRAIN components ({len(train_comps)}). Cannot grid search.")
        return 1

    # 50/50 split TRAIN into TUNE / HELD
    n = len(train_comps)
    tune = train_comps[:n//2]
    held = train_comps[n//2:]
    print(f"\nTUNE: {len(tune)}, HELD: {len(held)}")

    # Grid search 6-axis weights w1..w6 with sum=1.0, each ≥ 0.05
    # To keep grid tractable: coarser step
    step = 0.10
    weights_grid = []
    levels = [round(x * step, 2) for x in range(1, 10)]  # 0.10..0.90
    for w1 in levels:
        for w2 in levels:
            if w1 + w2 > 0.85:
                continue
            for w3 in levels:
                if w1 + w2 + w3 > 0.90:
                    continue
                for w4 in levels:
                    if w1 + w2 + w3 + w4 > 0.95:
                        continue
                    for w5 in levels:
                        w6 = round(1.0 - w1 - w2 - w3 - w4 - w5, 2)
                        if w6 < 0.05 or w6 > 0.85:
                            continue
                        weights_grid.append((w1, w2, w3, w4, w5, w6))

    print(f"Grid candidates: {len(weights_grid)}")

    # Tune on TUNE intra (max pairs under 0.30) — but penalize degenerate solutions
    # by ALSO requiring TUNE-inter-proxy (use the same comps but evaluate as inter at 0.60).
    # No — that's leakage. Tune only on TUNE intra.
    best = None
    best_score = -1.0
    for w in weights_grid:
        n_under, n_tot = eval_w(tune, w, 0.30, "under")
        score = n_under / max(n_tot, 1)
        if score > best_score:
            best_score = score
            best = w

    print(f"\n## Optimal weights on TUNE intra: {best}")
    print(f"## TUNE intra-pass at optimal: {100*best_score:.1f}%")

    held_n, held_tot = eval_w(held, best, 0.30, "under")
    test_n, test_tot = eval_w(test_comps, best, 0.60, "over")

    print(f"\n## HELD §4.1 (intra) with locked weights: {held_n}/{held_tot} = {100*held_n/held_tot:.1f}% (target ≥80%)")
    print(f"## TEST §4.2 (inter) with locked weights: {test_n}/{test_tot} = {100*test_n/test_tot:.1f}% (target ≥80%)")

    # Ceiling: best possible §4.1 and best possible §4.2 (overfit upper bounds)
    all_train = tune + held
    best_intra_ceiling = max(eval_w(all_train, w, 0.30, "under")[0]/max(len(all_train),1) for w in weights_grid)
    best_inter_ceiling = max(eval_w(test_comps, w, 0.60, "over")[0]/max(len(test_comps),1) for w in weights_grid)

    print(f"\n## CEILING (overfit upper bound)")
    print(f"   §4.1 intra: best possible = {100*best_intra_ceiling:.1f}%")
    print(f"   §4.2 inter: best possible = {100*best_inter_ceiling:.1f}%")

    # Joint pass: are there weights that hit BOTH ≥80%?
    joint_passing = [
        w for w in weights_grid
        if eval_w(all_train, w, 0.30, "under")[0]/max(len(all_train),1) >= 0.80
        and eval_w(test_comps, w, 0.60, "over")[0]/max(len(test_comps),1) >= 0.80
    ]
    print(f"\n## Weights passing BOTH §4.1 ≥80% AND §4.2 ≥80% (overfit, not held-out): {len(joint_passing)}")
    if joint_passing[:3]:
        for w in joint_passing[:3]:
            iN, iD = eval_w(all_train, w, 0.30, "under")
            jN, jD = eval_w(test_comps, w, 0.60, "over")
            print(f"   {w} → intra={iN}/{iD} ({100*iN/iD:.0f}%) inter={jN}/{jD} ({100*jN/jD:.0f}%)")

    print(f"\n## Honest verdict")
    if held_n/held_tot >= 0.80 and test_n/test_tot >= 0.80:
        print(f"   PRIMITIVE PASSES §4 with locked optimal weights (v2 + alpha-rename TRAIN)")
        print(f"   → proceed to §4.5 ablation dominance check")
    elif best_intra_ceiling >= 0.80 and best_inter_ceiling >= 0.80 and joint_passing:
        print(f"   PRIMITIVE PASSES CEILING but TUNE→HELD didn't transfer at TUNE-best.")
        print(f"   → Either tune objective needs to be JOINT (intra + inter), or larger TUNE set, or fold for generalization.")
    elif best_inter_ceiling < 0.80:
        print(f"   PRIMITIVE STRUCTURALLY CANNOT PASS §4.2 (ceiling = {100*best_inter_ceiling:.1f}% < 80%)")
        print(f"   → Even with v2 augmentation, surface+signature is insufficient. KERNEL FINGERPRINT required.")
    else:
        print(f"   PRIMITIVE CAN'T PASS at locked weights but ceiling allows.")
        print(f"   → tune objective improvement OR more TRAIN data.")

    out_path = ROOT / "analytics/public/leanmill/results/gp235_section_4_v2_full_results.json"
    out_path.write_text(json.dumps({
        "n_train_v2": len(train_v2),
        "n_test": len(test),
        "n_train_extracted": len(train_comps),
        "n_test_extracted": len(test_comps),
        "n_tune": len(tune),
        "n_held": len(held),
        "optimal_weights_locked": list(best) if best else None,
        "tune_intra_at_optimal": best_score,
        "held_intra_locked": held_n/held_tot if held_tot else None,
        "test_inter_locked": test_n/test_tot if test_tot else None,
        "ceiling_intra_overfit": best_intra_ceiling,
        "ceiling_inter_overfit": best_inter_ceiling,
        "n_weights_passing_both_overfit": len(joint_passing),
        "verdict": "PASS" if (held_n/held_tot >= 0.80 and test_n/test_tot >= 0.80) else "FAIL",
    }, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
