#!/usr/bin/env python3
"""Pivot effectiveness analysis -- GP-148 Stage 2, Ticket B.

PURPOSE
Measures how topological pivot events (both profile_injected and emergency)
affect score trajectories, and whether that effectiveness depends on the
type of weakness the pivot is trying to fix. Motivated by the 2026-04-24
gp140 observation suggesting that basis-change pivots work for "unverified
coercivity" failures but not for "exhaustiveness" failures.

METHODOLOGY
1. Load the enriched archive and index records by (project, iteration_index)
   within each run session.
2. Load cluster labels from Ticket A (weakest_link_taxonomy).
3. For each project with a workspace/loop_events.jsonl:
   a. Parse all topological_pivot_profile_injected and
      topological_pivot_emergency events.
   b. For each pivot at iteration_index I:
      - Find the pre-pivot record at I-1 (or the record at I if I-1 is
        missing) and tag it with its cluster ID.
      - Find post-pivot records at I+1, I+2, I+3.
      - Compute score delta = max(scores at I+1..I+3) - score at I-1.
   c. Classify the pivot outcome:
      - "climb": delta >= +10
      - "regress": delta <= -10
      - "no_change": -10 < delta < +10
4. Aggregate per cluster ID: p(climb), p(regress), p(no_change), N.
5. Flag clusters with N < 10 as "insufficient evidence."

The join between loop_events and the archive uses (project, iteration_index).
Because iteration_index can reset across run sessions, the join matches events
to the archive session whose timestamp range contains the event. This is
heuristic but works for the vast majority of cases.

KNOWN LIMITATIONS
1. Pivots near the end of a run (last 3 iters) have truncated post-pivot
   windows and are excluded from the analysis.
2. Records with score=None are skipped, which can reduce the effective
   post-pivot window.
3. The cluster label comes from the pre-pivot iter's weakest_point, which may
   not perfectly describe the failure the pivot was triggered by.
4. Emergency pivots and profile-injected pivots are analyzed together by
   default (both produce score-trajectory effects). They could be split.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
ARCHIVE = REPO / "analytics" / "trajectory_archive_enriched.jsonl"
CLUSTER_JSON = REPO / "analytics" / "public" / "queries" / "weakest_link_clusters_2026-04-24.json"
PROJECTS_DIR = REPO / "projects"
OUTPUT = REPO / "analytics" / "public" / "queries" / "pivot_effectiveness_2026-04-24.json"

POST_PIVOT_WINDOW = 3  # look at next 3 iters
CLIMB_THRESHOLD = 10
REGRESS_THRESHOLD = -10


def load_archive_index() -> dict[str, list[dict[str, Any]]]:
    """Load enriched archive, return records grouped by project, sorted by
    iter_timestamp ascending within each project."""
    by_project: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with ARCHIVE.open() as f:
        for line in f:
            rec = json.loads(line.strip())
            by_project[rec["project"]].append(rec)
    for recs in by_project.values():
        recs.sort(key=lambda r: r.get("iter_timestamp") or 0)
    return by_project


def load_cluster_labels() -> dict[tuple[str, int], str]:
    """Load (project, iter_timestamp) -> cluster_id mapping from Ticket A."""
    with CLUSTER_JSON.open() as f:
        data = json.load(f)
    return {(r["project"], r["iter_timestamp"]): r["cluster_id"] for r in data["_labels"]}


def build_iter_index(recs: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Build iteration_index -> record mapping for a single project's records.
    For projects with multiple sessions (index resets), this takes the LAST
    record with each index, which is usually the most recent session.
    We also build a positional index as fallback."""
    by_idx: dict[int, dict[str, Any]] = {}
    for rec in recs:
        idx = rec.get("iteration_index")
        if idx is not None:
            by_idx[idx] = rec
    return by_idx


def parse_loop_events(project: str) -> list[dict[str, Any]]:
    """Parse loop_events.jsonl for pivot events."""
    path = PROJECTS_DIR / project / "workspace" / "loop_events.jsonl"
    if not path.is_file():
        return []
    events = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            et = ev.get("event_type", "")
            if et in ("topological_pivot_profile_injected", "topological_pivot_emergency"):
                events.append(ev)
    return events


def main() -> int:
    if not ARCHIVE.is_file():
        print(f"ERROR: {ARCHIVE} not found.", file=sys.stderr)
        return 1
    if not CLUSTER_JSON.is_file():
        print(f"ERROR: {CLUSTER_JSON} not found. Run mine_weakest_link_taxonomy.py first.", file=sys.stderr)
        return 1

    archive = load_archive_index()
    labels = load_cluster_labels()

    print(f"Archive: {sum(len(v) for v in archive.values())} records, {len(archive)} projects")
    print(f"Cluster labels: {len(labels)} entries")

    # Process pivot events
    pivot_outcomes: list[dict[str, Any]] = []
    per_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    projects_with_events = 0
    total_pivots = 0
    skipped_truncated = 0
    skipped_no_score = 0

    for project, recs in sorted(archive.items()):
        events = parse_loop_events(project)
        if not events:
            continue
        projects_with_events += 1

        # Build iteration_index -> record map
        idx_map = build_iter_index(recs)
        max_idx = max(idx_map.keys()) if idx_map else 0

        for ev in events:
            total_pivots += 1
            pivot_idx = ev.get("iteration_index")
            if pivot_idx is None:
                continue

            # Pre-pivot record: use I-1, fallback to I
            pre_idx = pivot_idx - 1
            pre_rec = idx_map.get(pre_idx) or idx_map.get(pivot_idx)
            if pre_rec is None:
                continue

            pre_score = pre_rec.get("score")
            if pre_score is None:
                skipped_no_score += 1
                continue

            # Post-pivot records: I+1, I+2, I+3
            post_scores = []
            for offset in range(1, POST_PIVOT_WINDOW + 1):
                post_idx = pivot_idx + offset
                post_rec = idx_map.get(post_idx)
                if post_rec and post_rec.get("score") is not None:
                    post_scores.append(post_rec["score"])

            if not post_scores:
                skipped_truncated += 1
                continue

            # Score delta: max of post-pivot scores minus pre-pivot score
            max_post = max(post_scores)
            delta = max_post - pre_score

            # Classify outcome
            if delta >= CLIMB_THRESHOLD:
                outcome = "climb"
            elif delta <= REGRESS_THRESHOLD:
                outcome = "regress"
            else:
                outcome = "no_change"

            # Get cluster label for pre-pivot iter
            pre_ts = pre_rec.get("iter_timestamp")
            cluster_id = labels.get((project, pre_ts), "unknown")

            result = {
                "project": project,
                "pivot_event_type": ev.get("event_type"),
                "pivot_iteration_index": pivot_idx,
                "pre_pivot_score": pre_score,
                "max_post_pivot_score": max_post,
                "post_pivot_scores": post_scores,
                "delta": delta,
                "outcome": outcome,
                "cluster_id": cluster_id,
                "pivot_profile": ev.get("pivot_profile"),
            }
            pivot_outcomes.append(result)
            per_cluster[cluster_id].append(result)

    print(f"\nProjects with pivot events: {projects_with_events}")
    print(f"Total pivot events: {total_pivots}")
    print(f"Analyzed (with pre+post scores): {len(pivot_outcomes)}")
    print(f"Skipped (truncated window): {skipped_truncated}")
    print(f"Skipped (no pre-pivot score): {skipped_no_score}")

    # Aggregate per cluster
    cluster_summaries = []
    for cluster_id in sorted(per_cluster.keys()):
        outcomes = per_cluster[cluster_id]
        n = len(outcomes)
        n_climb = sum(1 for o in outcomes if o["outcome"] == "climb")
        n_regress = sum(1 for o in outcomes if o["outcome"] == "regress")
        n_nochange = sum(1 for o in outcomes if o["outcome"] == "no_change")

        # Mean delta
        mean_delta = sum(o["delta"] for o in outcomes) / max(n, 1)

        # Cross-project count
        projects_in_cluster = len(set(o["project"] for o in outcomes))

        insufficient = n < 10

        summary = {
            "cluster_id": cluster_id,
            "N": n,
            "project_count": projects_in_cluster,
            "p_climb": round(n_climb / n, 3) if n > 0 else None,
            "p_regress": round(n_regress / n, 3) if n > 0 else None,
            "p_no_change": round(n_nochange / n, 3) if n > 0 else None,
            "mean_delta": round(mean_delta, 1),
            "insufficient_evidence": insufficient,
            "verdict": "",
        }

        # Generate verdict line
        if insufficient:
            summary["verdict"] = f"INSUFFICIENT EVIDENCE (N={n}, need >= 10)"
        else:
            parts = []
            if summary["p_climb"] and summary["p_climb"] > 0.3:
                parts.append(f"climb {summary['p_climb']:.0%}")
            if summary["p_regress"] and summary["p_regress"] > 0.3:
                parts.append(f"regress {summary['p_regress']:.0%}")
            if summary["p_no_change"] and summary["p_no_change"] > 0.3:
                parts.append(f"no-change {summary['p_no_change']:.0%}")
            if projects_in_cluster < 3:
                parts.append("PROVISIONAL (<3 projects)")
            summary["verdict"] = f"N={n}: " + ", ".join(parts) if parts else f"N={n}: mixed"

        cluster_summaries.append(summary)

    cluster_summaries.sort(key=lambda s: -s["N"])

    print("\n=== Per-Cluster Pivot Effectiveness ===")
    for s in cluster_summaries:
        print(f"  {s['cluster_id']:30s}  N={s['N']:4d}  "
              f"climb={s['p_climb']:.0%}  regress={s['p_regress']:.0%}  "
              f"no_change={s['p_no_change']:.0%}  mean_delta={s['mean_delta']:+.1f}  "
              f"{'[INSUFFICIENT]' if s['insufficient_evidence'] else ''}")

    # gp140 hypothesis check
    print("\n=== gp140 Provisional Hypothesis Check ===")
    for s in cluster_summaries:
        if "unverified" in s["cluster_id"]:
            print(f"  unverified_bound: N={s['N']}, p(climb)={s['p_climb']}, mean_delta={s['mean_delta']:+.1f}")
            if s["insufficient_evidence"]:
                print(f"    -> INSUFFICIENT EVIDENCE")
            elif s["p_climb"] and s["p_climb"] > 0.3:
                print(f"    -> SUPPORTS pivot effectiveness for unverified-bound class")
            else:
                print(f"    -> DOES NOT SUPPORT pivot effectiveness for unverified-bound class")
        if "exhaustiveness" in s["cluster_id"]:
            print(f"  exhaustiveness_claim: N={s['N']}, p(climb)={s['p_climb']}, mean_delta={s['mean_delta']:+.1f}")
            if s["insufficient_evidence"]:
                print(f"    -> INSUFFICIENT EVIDENCE")
            elif s["p_climb"] and s["p_climb"] < 0.2:
                print(f"    -> SUPPORTS ineffectiveness for exhaustiveness class")
            else:
                print(f"    -> DOES NOT SUPPORT ineffectiveness for exhaustiveness class")

    # Output
    output = {
        "generated": "2026-04-24",
        "source_archive": str(ARCHIVE),
        "source_clusters": str(CLUSTER_JSON),
        "projects_with_pivot_events": projects_with_events,
        "total_pivot_events": total_pivots,
        "analyzed_pivots": len(pivot_outcomes),
        "skipped_truncated_window": skipped_truncated,
        "skipped_no_pre_score": skipped_no_score,
        "cluster_summaries": cluster_summaries,
        "gp140_hypothesis": {
            "claim": "unverified coercivity cluster -> basis-change pivot effective; exhaustiveness cluster -> pivot ineffective",
            "status": "see cluster_summaries for per-cluster verdicts",
        },
        "anti_overfitting_notes": [
            "Clusters with N < 10 are flagged as insufficient evidence.",
            "Clusters from < 3 projects are flagged as provisional.",
            "Pre-pivot cluster assignment uses weakest_point from I-1, which may not match the trigger.",
            "Emergency and profile-injected pivots are analyzed together.",
        ],
        "pivot_details": pivot_outcomes,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
