#!/usr/bin/env python3
"""gp235_section_4_1_intra_cluster.py — §4.1 intra-cluster distance test.

Reads /tmp/gp235_train_set_30pairs.json. For each pair (X, X') extracts the
proof body of each and computes surface_distance with default weights
(w1=0.4, w2=0.3, w3=0.2, w4=0.1). Reports:
  - Per-pair distance + skeleton match
  - Distribution (mean, median, p25/p75, max)
  - Pass-gate check: ≥80% of pairs with distance < 0.30

Note: this uses DEFAULT weights (no tuning yet). Per §4.1 the weights should
be tuned on TRAIN, then validated on TEST. This script reports the
default-weight baseline; weight-tuning is the next step if pass-gate FAILS.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from proof_route_fingerprint import parse_proof_body, surface_distance  # type: ignore


def extract_proof_body(file_path: str, theorem_name: str) -> str | None:
    """Find the proof body of `theorem_name`. Line-based: find the line
    containing `theorem|lemma|def|instance <name>`, then capture everything
    after the first `:=` (or `:= by`) up to next top-level decl."""
    import re
    p = Path(file_path)
    if not p.exists():
        return None
    text = p.read_text()
    lines = text.splitlines()
    # Find decl line — start with `^` optional whitespace then keyword then name
    decl_re = re.compile(
        rf"^\s*(?:theorem|lemma|example|def|instance|noncomputable\s+def)\s+(?:@\[[^\]]+\]\s+)?{re.escape(theorem_name)}(?=\s|\(|\{{|:|$)"
    )
    decl_idx = None
    for i, line in enumerate(lines):
        if decl_re.search(line):
            decl_idx = i
            break
    if decl_idx is None:
        return None
    # Walk forward to find `:=` (might be on a later line for multi-line sigs)
    body_lines = []
    body_started = False
    end_re = re.compile(
        r"^\s*(?:theorem|lemma|example|def|instance|end|namespace|@\[|noncomputable\s+def|abbrev|structure|class|inductive|opaque|axiom)\b"
    )
    for i in range(decl_idx, min(len(lines), decl_idx + 200)):
        line = lines[i]
        if not body_started:
            # Look for `:=` on this line
            if ":=" in line:
                idx = line.index(":=")
                rest = line[idx+2:]
                body_lines.append(rest)
                body_started = True
                continue
        else:
            # Stop at next top-level decl (but allow blank lines / indented content)
            if end_re.search(line) and i > decl_idx:
                break
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return body if body else None


def main():
    train = json.load(open("/tmp/gp235_train_set_30pairs.json"))
    print(f"# §4.1 Intra-cluster distance test — {len(train)} pairs\n")

    results = []
    extraction_failures = 0
    for pair in train:
        pair_id = pair.get("pair_id", "?")
        left = pair.get("left", {})
        right = pair.get("right", {})
        body_l = extract_proof_body(left.get("file_path", ""), left.get("name", ""))
        body_r = extract_proof_body(right.get("file_path", ""), right.get("name", ""))
        if body_l is None or body_r is None:
            extraction_failures += 1
            results.append({
                "pair_id": pair_id,
                "error": f"extraction_failed: left={body_l is not None} right={body_r is not None}",
            })
            continue
        fp_l = parse_proof_body(body_l)
        fp_r = parse_proof_body(body_r)
        dist = surface_distance(fp_l, fp_r)
        results.append({
            "pair_id": pair_id,
            "left_name": left.get("name"),
            "right_name": right.get("name"),
            "skeleton_match": fp_l["skeleton_kind"] == fp_r["skeleton_kind"],
            "left_skeleton": fp_l["skeleton_kind"],
            "right_skeleton": fp_r["skeleton_kind"],
            "distance": dist["total_distance"],
            "components": dist["components"],
        })

    successes = [r for r in results if "error" not in r]
    n_ok = len(successes)
    n_under_0_30 = sum(1 for r in successes if r["distance"] < 0.30)
    n_under_0_50 = sum(1 for r in successes if r["distance"] < 0.50)

    print(f"## Extraction\n- Pairs: {len(train)}\n- Successful extractions: {n_ok}\n- Failed extractions: {extraction_failures}\n")
    if n_ok == 0:
        print("ABORT: zero successful extractions; cannot run distance test")
        for r in results[:5]:
            print(f"  {r}")
        return 1
    dists = [r["distance"] for r in successes]
    print(f"## Distance distribution (default weights w=(0.4,0.3,0.2,0.1))")
    print(f"- mean:   {mean(dists):.3f}")
    print(f"- median: {median(dists):.3f}")
    print(f"- min:    {min(dists):.3f}")
    print(f"- max:    {max(dists):.3f}\n")
    print(f"## Pass-gate (§4.1 pre-registered: ≥80% pairs distance < 0.30)")
    print(f"- {n_under_0_30}/{n_ok} pairs under 0.30 = {100*n_under_0_30/n_ok:.1f}%")
    print(f"- {n_under_0_50}/{n_ok} pairs under 0.50 = {100*n_under_0_50/n_ok:.1f}%")
    print(f"- **Pass-gate verdict (default weights):** {'PASS' if n_under_0_30/n_ok >= 0.80 else 'FAIL'}")
    print()
    print(f"## Per-pair detail (first 10)")
    for r in successes[:10]:
        ok = "✓" if r["distance"] < 0.30 else "✗"
        print(f"  {ok} {r['pair_id'][:50]:<50} dist={r['distance']:.3f} [{r['left_skeleton']}/{r['right_skeleton']}]")
    if extraction_failures:
        print()
        print(f"## Extraction-failed pairs (first 5)")
        failed = [r for r in results if "error" in r][:5]
        for r in failed:
            print(f"  {r['pair_id']}: {r['error']}")

    out_path = Path(ROOT / "analytics/public/leanmill/results/gp235_section_4_1_results.json")
    out_path.write_text(json.dumps({
        "n_pairs": len(train),
        "n_successful_extractions": n_ok,
        "n_extraction_failures": extraction_failures,
        "mean_distance": mean(dists) if dists else None,
        "median_distance": median(dists) if dists else None,
        "n_under_0_30": n_under_0_30,
        "n_under_0_50": n_under_0_50,
        "pass_gate_threshold": 0.30,
        "pass_gate_pct_threshold": 0.80,
        "pass_gate_verdict": "PASS" if n_ok and n_under_0_30/n_ok >= 0.80 else "FAIL",
        "per_pair_results": results,
    }, indent=2, default=str))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
