#!/usr/bin/env python3
"""Score ceiling analysis -- GP-148 Stage 2, Ticket D.

PURPOSE
Identifies the maximum score achieved per configuration group (project,
rubric_hash, mutator_model_id, judge_model_id, run_session_id) and surfaces
which active_constraints correlate with score ceilings in the 70-85 range --
potential "wall constraints" that prevent further progress.

METHODOLOGY
1. Group all records by the 5-tuple (project, rubric_hash, mutator_model_id,
   judge_model_id, run_session_id).
2. For each group, compute max_score and the iter_timestamp at which it was
   achieved.
3. Sort groups by max_score descending; report the top 20 ceilings.
4. For the "wall hypothesis": compare constraint prevalence in groups whose
   ceiling falls in the 70-85 range vs groups whose ceiling is 86+. A
   constraint that appears disproportionately in the 70-85 range (relative
   frequency > 2x its frequency in the 86+ range) is flagged as a potential
   wall constraint.

rubric_hash + run_session_id distinguish stochastic re-runs of the same setup
from structural-change runs per the seam specification.

KNOWN LIMITATIONS
1. active_constraints reflects the CURRENT rubric/charter state, not the
   historical state at the time of each iteration. Constraints may have been
   added or removed between runs.
2. Groups with only 1-2 iterations may report misleading ceilings (the run
   was too short to converge).
3. The wall-constraint analysis uses simple frequency comparison, not
   statistical testing. Constraints flagged as "potential walls" are
   hypotheses for operator review, not confirmed findings.
4. Some records have null rubric_hash or null model IDs, which reduces
   group granularity (multiple configurations may be merged under nulls).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path("/Users/daalami/figs_activist_loop")
ARCHIVE = REPO / "analytics" / "trajectory_archive_enriched.jsonl"
OUTPUT = REPO / "analytics" / "queries" / "score_ceilings_2026-04-24.json"


def main() -> int:
    if not ARCHIVE.is_file():
        print(f"ERROR: {ARCHIVE} not found.", file=sys.stderr)
        return 1

    # Load and group
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    with ARCHIVE.open() as f:
        for line in f:
            rec = json.loads(line.strip())
            key = (
                rec.get("project"),
                rec.get("rubric_hash"),
                rec.get("mutator_model_id"),
                rec.get("judge_model_id"),
                rec.get("run_session_id"),
            )
            groups[key].append(rec)

    print(f"Total groups: {len(groups)}")

    # Compute ceilings
    ceilings = []
    for key, recs in groups.items():
        scored = [r for r in recs if r.get("score") is not None]
        if not scored:
            continue
        best = max(scored, key=lambda r: r["score"])
        ceilings.append({
            "project": key[0],
            "rubric_hash": key[1],
            "mutator_model_id": key[2],
            "judge_model_id": key[3],
            "run_session_id": key[4],
            "max_score": best["score"],
            "max_score_iter_timestamp": best.get("iter_timestamp"),
            "max_score_iteration_index": best.get("iteration_index"),
            "active_constraints": best.get("active_constraints", []),
            "weakest_point_at_ceiling": best.get("weakest_point"),
            "group_iter_count": len(recs),
            "group_scored_count": len(scored),
        })

    ceilings.sort(key=lambda c: c["max_score"], reverse=True)

    # Top 20
    top20 = ceilings[:20]
    print("\n=== Top 20 Score Ceilings ===")
    for i, c in enumerate(top20):
        print(f"  {i+1:2d}. score={c['max_score']:4d}  project={c['project']:<40s} "
              f"mutator={c['mutator_model_id']}  judge={c['judge_model_id']}  "
              f"iters={c['group_scored_count']}")

    # Wall constraint analysis: 70-85 range vs 86+
    wall_range = [c for c in ceilings if 70 <= c["max_score"] <= 85]
    high_range = [c for c in ceilings if c["max_score"] >= 86]

    print(f"\nWall-range groups (70-85 ceiling): {len(wall_range)}")
    print(f"High-range groups (86+ ceiling): {len(high_range)}")

    # Count constraint frequencies in each range
    wall_constraints: dict[str, int] = defaultdict(int)
    high_constraints: dict[str, int] = defaultdict(int)

    for c in wall_range:
        for ac in c["active_constraints"]:
            wall_constraints[ac] += 1
    for c in high_range:
        for ac in c["active_constraints"]:
            high_constraints[ac] += 1

    # Identify potential wall constraints
    all_constraints = set(wall_constraints.keys()) | set(high_constraints.keys())
    wall_candidates = []

    for ac in sorted(all_constraints):
        wall_count = wall_constraints.get(ac, 0)
        high_count = high_constraints.get(ac, 0)
        wall_freq = wall_count / max(len(wall_range), 1)
        high_freq = high_count / max(len(high_range), 1)

        if wall_freq > 0 and (high_freq == 0 or wall_freq / max(high_freq, 0.001) > 2.0):
            wall_candidates.append({
                "constraint": ac,
                "wall_range_count": wall_count,
                "wall_range_freq": round(wall_freq, 3),
                "high_range_count": high_count,
                "high_range_freq": round(high_freq, 3),
                "freq_ratio": round(wall_freq / max(high_freq, 0.001), 2),
            })

    wall_candidates.sort(key=lambda x: -x["freq_ratio"])

    if wall_candidates:
        print("\n=== Potential Wall Constraints (70-85 range > 2x prevalence vs 86+) ===")
        for wc in wall_candidates[:10]:
            print(f"  {wc['constraint']:50s}  wall_freq={wc['wall_range_freq']:.3f}  "
                  f"high_freq={wc['high_range_freq']:.3f}  ratio={wc['freq_ratio']:.1f}x")

    # Output
    output = {
        "generated": "2026-04-24",
        "source": str(ARCHIVE),
        "total_groups": len(groups),
        "total_with_scores": len(ceilings),
        "top_20_ceilings": top20,
        "wall_analysis": {
            "wall_range": "70 <= max_score <= 85",
            "high_range": "max_score >= 86",
            "wall_range_group_count": len(wall_range),
            "high_range_group_count": len(high_range),
            "potential_wall_constraints": wall_candidates,
        },
        "anti_overfitting_notes": [
            "active_constraints reflects current rubric state, not historical.",
            "Wall-constraint analysis uses frequency comparison, not statistical testing.",
            f"Wall range has {len(wall_range)} groups; results are exploratory.",
            "Groups with null rubric_hash or model IDs may merge distinct configurations.",
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
