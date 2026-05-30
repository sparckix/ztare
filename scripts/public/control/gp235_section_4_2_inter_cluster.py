#!/usr/bin/env python3
"""gp235_section_4_2_inter_cluster.py — §4.2 inter-cluster distance test.

Reads /tmp/gp235_test_set_50pairs.json (structurally-distinct pairs).
For each pair, extracts proof body and computes surface_distance.
Pass-gate: ≥80% of pairs with distance > 0.60.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from proof_route_fingerprint import parse_proof_body, surface_distance  # type: ignore
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore


def main():
    raw = json.load(open("/tmp/gp235_test_set_50pairs.json"))
    # Agent wrapped pairs in a dict with summary keys
    if isinstance(raw, dict):
        test = raw.get("test_set") or raw.get("pairs") or []
    else:
        test = raw
    print(f"# §4.2 Inter-cluster distance test — {len(test)} pairs\n")

    results = []
    extraction_failures = 0
    for pair in test:
        pair_id = pair.get("pair_id", "?")
        left = pair.get("left", {})
        right = pair.get("right", {})
        body_l = extract_proof_body(left.get("file_path", ""), left.get("name", ""))
        body_r = extract_proof_body(right.get("file_path", ""), right.get("name", ""))
        if body_l is None or body_r is None:
            extraction_failures += 1
            results.append({"pair_id": pair_id, "error": f"l={body_l is not None} r={body_r is not None}"})
            continue
        fp_l = parse_proof_body(body_l)
        fp_r = parse_proof_body(body_r)
        dist = surface_distance(fp_l, fp_r)
        results.append({
            "pair_id": pair_id,
            "left_skeleton": fp_l["skeleton_kind"],
            "right_skeleton": fp_r["skeleton_kind"],
            "distance": dist["total_distance"],
            "components": dist["components"],
        })

    successes = [r for r in results if "error" not in r]
    n_ok = len(successes)
    n_over_0_60 = sum(1 for r in successes if r["distance"] > 0.60)
    n_over_0_40 = sum(1 for r in successes if r["distance"] > 0.40)

    print(f"## Extraction\n- Pairs: {len(test)}\n- Successful: {n_ok}\n- Failed: {extraction_failures}\n")
    if n_ok == 0:
        return 1
    dists = [r["distance"] for r in successes]
    print(f"## Distance distribution (default weights)")
    print(f"- mean:   {mean(dists):.3f}")
    print(f"- median: {median(dists):.3f}")
    print(f"- min:    {min(dists):.3f}")
    print(f"- max:    {max(dists):.3f}\n")
    print(f"## Pass-gate (§4.2 pre-registered: ≥80% pairs distance > 0.60)")
    print(f"- {n_over_0_60}/{n_ok} pairs over 0.60 = {100*n_over_0_60/n_ok:.1f}%")
    print(f"- {n_over_0_40}/{n_ok} pairs over 0.40 = {100*n_over_0_40/n_ok:.1f}%")
    print(f"- **Pass-gate verdict (default weights):** {'PASS' if n_over_0_60/n_ok >= 0.80 else 'FAIL'}")

    print()
    print(f"## Per-pair (first 10)")
    for r in successes[:10]:
        ok = "✓" if r["distance"] > 0.60 else "✗"
        print(f"  {ok} {r['pair_id'][:55]:<55} dist={r['distance']:.3f} [{r['left_skeleton']}/{r['right_skeleton']}]")

    out_path = Path(ROOT / "analytics/public/leanmill/results/gp235_section_4_2_results.json")
    out_path.write_text(json.dumps({
        "n_pairs": len(test),
        "n_successful": n_ok,
        "n_extraction_failures": extraction_failures,
        "mean_distance": mean(dists),
        "median_distance": median(dists),
        "n_over_0_60": n_over_0_60,
        "n_over_0_40": n_over_0_40,
        "pass_gate_threshold": 0.60,
        "pass_gate_pct_threshold": 0.80,
        "pass_gate_verdict": "PASS" if n_over_0_60/n_ok >= 0.80 else "FAIL",
        "per_pair_results": results,
    }, indent=2, default=str))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
