#!/usr/bin/env python3
"""Climb trigger analysis -- GP-148 Stage 2, Ticket E.

PURPOSE
Isolates consecutive iteration pairs (iter_t, iter_t+1) with score delta >= +20
and cross-references with the weakest-link cluster label at iter_t. Surfaces
"which failure class, when fixed, produces the biggest jumps" -- informing
where to invest Stage 3 LLM attention.

METHODOLOGY
1. Load the enriched archive, group records by (project, run_session_id).
2. Within each group, sort by iter_timestamp and find consecutive pairs where
   both records have non-null scores and score_t+1 - score_t >= 20.
3. Tag each pair with the cluster_id of iter_t (from Ticket A).
4. Report per-cluster: count of big-jump pairs, mean and median jump size,
   exemplars with (project, iter_ts, score_before, score_after, weakest_point).

KNOWN LIMITATIONS
1. Only considers consecutive pairs within the same project and session.
   Cross-session jumps (e.g., after a rubric change) are excluded because
   they reflect structural changes, not iterative improvement.
2. The cluster label reflects the weakness BEFORE the jump. The mutator may
   have fixed that weakness (direct fix) or introduced something orthogonal
   that scored better despite the weakness remaining (indirect fix).
3. Large jumps from score=0 or very low scores may reflect harness recovery
   rather than genuine epistemic improvement. These are flagged but included.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
# Canonical path (was stranded at pre-reorg analytics/ root — 2026-05-16
# G-class fix; see scripts/public/mining/_canonical_paths.py).
ARCHIVE = REPO / "analytics" / "public" / "ledgers" / "trajectory" / "trajectory_archive_enriched.jsonl"
CLUSTER_JSON = REPO / "analytics" / "public" / "queries" / "weakest_link_clusters_2026-04-24.json"
OUTPUT = REPO / "analytics" / "public" / "queries" / "trajectory" / "climb_triggers_2026-04-24.json"

JUMP_THRESHOLD = 20


def main() -> int:
    if not ARCHIVE.is_file():
        print(f"ERROR: {ARCHIVE} not found.", file=sys.stderr)
        return 1
    if not CLUSTER_JSON.is_file():
        print(f"ERROR: {CLUSTER_JSON} not found.", file=sys.stderr)
        return 1

    # Load cluster labels
    with CLUSTER_JSON.open() as f:
        cdata = json.load(f)
    labels = {(r["project"], r["iter_timestamp"]): r["cluster_id"] for r in cdata["_labels"]}

    # Load and group records by (project, run_session_id)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with ARCHIVE.open() as f:
        for line in f:
            rec = json.loads(line.strip())
            key = (rec["project"], rec.get("run_session_id", ""))
            groups[key].append(rec)

    # Sort within each group by iter_timestamp
    for recs in groups.values():
        recs.sort(key=lambda r: r.get("iter_timestamp") or 0)

    # Find big jumps
    jumps: list[dict[str, Any]] = []
    per_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (project, session), recs in groups.items():
        for i in range(len(recs) - 1):
            r0 = recs[i]
            r1 = recs[i + 1]
            s0 = r0.get("score")
            s1 = r1.get("score")
            if s0 is None or s1 is None:
                continue
            delta = s1 - s0
            if delta >= JUMP_THRESHOLD:
                ts0 = r0.get("iter_timestamp")
                cluster_id = labels.get((project, ts0), "unknown")
                jump = {
                    "project": project,
                    "run_session_id": session,
                    "iter_timestamp_before": ts0,
                    "iter_timestamp_after": r1.get("iter_timestamp"),
                    "score_before": s0,
                    "score_after": s1,
                    "delta": delta,
                    "cluster_id_before": cluster_id,
                    "weakest_point_before": (r0.get("weakest_point") or "")[:200],
                    "weakest_point_after": (r1.get("weakest_point") or "")[:200],
                    "from_zero": s0 == 0,
                }
                jumps.append(jump)
                per_cluster[cluster_id].append(jump)

    print(f"Total jump pairs (delta >= {JUMP_THRESHOLD}): {len(jumps)}")

    # Aggregate per cluster
    cluster_summaries = []
    for cluster_id in sorted(per_cluster.keys(), key=lambda c: -len(per_cluster[c])):
        js = per_cluster[cluster_id]
        n = len(js)
        deltas = [j["delta"] for j in js]
        from_zero_count = sum(1 for j in js if j["from_zero"])
        projects = set(j["project"] for j in js)

        mean_delta = sum(deltas) / n
        sorted_deltas = sorted(deltas)
        median_delta = sorted_deltas[n // 2]

        # Pick up to 3 exemplars from different projects
        seen = set()
        exemplars = []
        for j in sorted(js, key=lambda x: -x["delta"]):
            if j["project"] not in seen:
                exemplars.append({
                    "project": j["project"],
                    "score_before": j["score_before"],
                    "score_after": j["score_after"],
                    "delta": j["delta"],
                    "weakest_point_before": j["weakest_point_before"],
                })
                seen.add(j["project"])
            if len(exemplars) >= 3:
                break

        insufficient = n < 10
        summary = {
            "cluster_id": cluster_id,
            "N": n,
            "project_count": len(projects),
            "mean_delta": round(mean_delta, 1),
            "median_delta": median_delta,
            "max_delta": max(deltas),
            "from_zero_count": from_zero_count,
            "from_zero_fraction": round(from_zero_count / n, 2),
            "insufficient_evidence": insufficient,
            "exemplars": exemplars,
        }
        cluster_summaries.append(summary)

    print("\n=== Climb Triggers by Pre-Jump Cluster ===")
    for s in cluster_summaries:
        note = " [INSUFFICIENT]" if s["insufficient_evidence"] else ""
        zero_note = f" (from_zero: {s['from_zero_fraction']:.0%})" if s["from_zero_count"] > 0 else ""
        print(f"  {s['cluster_id']:30s}  N={s['N']:4d}  mean_delta={s['mean_delta']:+.1f}  "
              f"median={s['median_delta']:+d}  max={s['max_delta']:+d}  "
              f"projects={s['project_count']}{zero_note}{note}")

    output = {
        "generated": "2026-04-24",
        "source_archive": str(ARCHIVE),
        "source_clusters": str(CLUSTER_JSON),
        "jump_threshold": JUMP_THRESHOLD,
        "total_jumps": len(jumps),
        "cluster_summaries": cluster_summaries,
        "anti_overfitting_notes": [
            "Clusters with N < 10 are flagged as insufficient evidence.",
            "from_zero jumps may reflect harness recovery, not epistemic improvement.",
            "Cluster label reflects weakness before the jump, not necessarily what was fixed.",
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
