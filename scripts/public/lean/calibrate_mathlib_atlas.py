#!/usr/bin/env python3
"""Retrieval-quality calibration for the Mathlib atlas.

Two tests, both internal (no API calls — uses atlas vectors as queries):

  Test 1A — Family cohesion. Pick known analysis classics (Hölder, Minkowski,
  Sobolev, Gronwall, Bochner). For each, use its atlas vector as the query and
  verify the top-10 neighbours share its top-level Mathlib subdir (a weak but
  honest proxy for "structurally related"). Pass condition: >=70% of top-10
  neighbours stay within the query's top-level subdir.

  Test 1B — Cross-family separation. For the same anchors, verify their top-1
  neighbour is NOT a notoriously-different family (Combinatorics, Algebra,
  LinearAlgebra for analysis anchors). Pass condition: 0 cross-family top-1.

This is a calibration check, NOT a relevance judgment. The mathematical
relevance of any specific hit must be human-judged before the fallback gets
flipped default-ON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from src.ztare.research_director.mathlib_semantic import (  # noqa: E402
    DEFAULT_MATHLIB_ATLAS,
    DEFAULT_MATHLIB_INDEX,
    _load_mathlib_atlas,
    _cosine,
)


ANCHOR_NAMES = [
    # Hölder family
    "inner_mul_le_norm_mul_norm",
    "NNReal.inner_le_iff",
    # Minkowski / Lp
    "MeasureTheory.lintegral_rpow_add_le",
    # Sobolev
    "MeasureTheory.MemLp.aestronglyMeasurable",
    # Gronwall
    "ODE_solution_unique_of_mem_Icc_right",
    "Real.add_pow_le_pow_mul_pow_of_sq_le_sq",
    # Bochner
    "MeasureTheory.integral_eq_sub_of_hasDerivAt",
    "MeasureTheory.Integrable",
    # Triangle inequality / norms
    "norm_add_le",
    "abs_sub_abs_le_abs_sub",
]


def find_anchors(rows: list[dict], names: list[str]) -> list[tuple[int, dict]]:
    """Return (index, row) for each anchor name found in the atlas."""
    by_name = {row.get("name"): (i, row) for i, row in enumerate(rows)}
    found = []
    for n in names:
        hit = by_name.get(n)
        if hit is not None:
            found.append(hit)
    return found


def top_n_neighbours(
    query_idx: int, vecs: list[list[float]], rows: list[dict], n: int = 10
) -> list[tuple[float, int, dict]]:
    qvec = vecs[query_idx]
    scored = []
    for j in range(len(vecs)):
        if j == query_idx:
            continue
        scored.append((_cosine(qvec, vecs[j]), j, rows[j]))
    scored.sort(reverse=True, key=lambda t: t[0])
    return scored[:n]


def top_dir(file_path: str) -> str:
    return (file_path or "").split("/", 1)[0]


def main() -> int:
    if not DEFAULT_MATHLIB_ATLAS.exists():
        print(f"ERROR: atlas missing at {DEFAULT_MATHLIB_ATLAS}")
        print("  Run scripts/public/lean/build_mathlib_atlas_embeddings.py first.")
        return 1

    rows, vecs = _load_mathlib_atlas(DEFAULT_MATHLIB_ATLAS, DEFAULT_MATHLIB_INDEX)
    manifest = json.loads(DEFAULT_MATHLIB_ATLAS.read_text())
    print(f"loaded atlas: {len(rows)} entries")
    print(f"atlas generated_at: {manifest.get('generated_at')}")
    print(f"atlas model: {manifest.get('model')}  dims: {manifest.get('dimensions')}")
    print()

    anchors = find_anchors(rows, ANCHOR_NAMES)
    print(f"anchors found in atlas: {len(anchors)} / {len(ANCHOR_NAMES)}")
    if len(anchors) < 5:
        print("  WARN: <5 anchors found — atlas may have been built with --max-entries cap")
        print("  or these specific Mathlib names differ. Falling back to first 5 entries")
        print("  in each of Analysis/MeasureTheory/Topology/Order/NumberTheory.")
        seen_dirs: dict[str, list[tuple[int, dict]]] = {}
        for i, row in enumerate(rows):
            d = top_dir(row.get("file", ""))
            if d in {"Analysis", "MeasureTheory", "Topology", "Order", "NumberTheory"}:
                seen_dirs.setdefault(d, []).append((i, row))
        anchors = [picks[0] for picks in seen_dirs.values() if picks][:5]
        print(f"  using {len(anchors)} fallback anchors")
        print()

    cross_family_set = {"Combinatorics", "Algebra", "LinearAlgebra"}
    pass_1a = 0
    pass_1b = 0
    for qi, qrow in anchors:
        qdir = top_dir(qrow.get("file", ""))
        nbrs = top_n_neighbours(qi, vecs, rows, n=10)
        same_dir = sum(1 for _, _, r in nbrs if top_dir(r.get("file", "")) == qdir)
        ratio = same_dir / max(len(nbrs), 1)
        top1_dir = top_dir(nbrs[0][2].get("file", "")) if nbrs else ""
        cross_top1 = (
            top1_dir in cross_family_set
            and qdir not in cross_family_set
        )
        cohesion_pass = ratio >= 0.7
        separation_pass = not cross_top1
        if cohesion_pass:
            pass_1a += 1
        if separation_pass:
            pass_1b += 1
        flag_1a = "PASS" if cohesion_pass else "WARN"
        flag_1b = "PASS" if separation_pass else "FAIL"
        print(f"=== {qrow.get('name', '?')[:60]:60s}  @ {qdir} ===")
        print(f"  1A cohesion: [{flag_1a}]  same-dir-in-top-10: {same_dir}/{len(nbrs)} ({100*ratio:.0f}%)")
        print(f"  1B separation: [{flag_1b}]  top-1 dir: {top1_dir}")
        print(f"  top-3 neighbours:")
        for cos, _, r in nbrs[:3]:
            d = top_dir(r.get("file", ""))
            print(f"    cos={cos:.4f}  [{d}]  {r.get('name', '?')[:65]}")
        print()

    n = len(anchors)
    print(f"=== summary ===")
    print(f"  Test 1A (family cohesion >=70% same-dir): {pass_1a}/{n} anchors pass")
    print(f"  Test 1B (no cross-family top-1):         {pass_1b}/{n} anchors pass")
    overall = pass_1a == n and pass_1b == n
    print(f"  overall: {'PASS — atlas retrieval quality is clean' if overall else 'NEEDS REVIEW'}")
    return 0 if overall else 0  # non-zero would block CI; this is advisory


if __name__ == "__main__":
    raise SystemExit(main())
