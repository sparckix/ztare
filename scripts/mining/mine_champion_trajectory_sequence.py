"""GP-149 I-4 — Champion-trajectory sequence miner.

For each (project, rubric_hash) group with max_score >= 90, extract the
SEQUENCE of weakest-link class labels across iterations. Aggregate into:

  1. Per-champion path string (e.g. "harness_defect -> catastrophic -> overclaim -> tail -> counterfactual")
  2. Class-to-class transition matrix (empirical Markov chain)
  3. Common prefixes (the first N classes that appear in K+ champions)
  4. Rare transitions (1-off class pairs) — potential novel insights

Output: analytics/queries/champion_trajectory_sequences_<date>.json

Statistical caveat: only ~30 champion groups in the current corpus. Markov-chain
estimates from small N are unreliable. The script flags n_champions used and
annotates each transition with its observed count. Acceptance criterion for
drawing conclusions: any transition needs >= 3 observations across distinct
project groups.

Reference: research_areas/private/seams/engine/GP-149_mining_findings_and_interventions_seam.md §2.5 + §4 I-4.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "analytics" / "trajectory_archive_enriched.jsonl"
REGEX_CLUSTERS = REPO / "analytics" / "queries" / "weakest_link_clusters_2026-04-24.json"
LLM_CLUSTERS = REPO / "analytics" / "queries" / "weakest_link_llm_subclasses_2026-04-24.json"
OUT_DIR = REPO / "analytics" / "queries"


def load_class_by_key() -> dict[tuple[str, int], str]:
    """Build (project, iter_timestamp) -> class_label map from regex+LLM labels.
    LLM labels override regex on the 842 overlap.
    """
    class_by_key: dict[tuple[str, int], str] = {}
    if REGEX_CLUSTERS.is_file():
        regex = json.loads(REGEX_CLUSTERS.read_text())
        for cl in regex.get("clusters", []):
            name = cl.get("cluster_id") or cl.get("cluster_name") or "?"
            for proj, ts in cl.get("members", []):
                class_by_key[(proj, int(ts))] = name
    if LLM_CLUSTERS.is_file():
        llm = json.loads(LLM_CLUSTERS.read_text())
        for c in llm.get("categories", []):
            cat = c.get("category", "?")
            for proj, ts in c.get("members", []):
                class_by_key[(proj, int(ts))] = cat
    return class_by_key


def load_groups() -> dict[tuple[str, str], list[dict]]:
    """Group iterations by (project, rubric_hash)."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with ARCHIVE.open() as f:
        for line in f:
            r = json.loads(line)
            key = (r.get("project", "?"), r.get("rubric_hash") or "unknown")
            groups[key].append(r)
    for rs in groups.values():
        rs.sort(key=lambda r: r.get("iter_timestamp") or 0)
    return groups


def main() -> None:
    if not ARCHIVE.is_file():
        print(f"ERROR: {ARCHIVE} not found. Run mine_trajectories.py first.", file=sys.stderr)
        sys.exit(1)

    class_by_key = load_class_by_key()
    groups = load_groups()

    # Filter to champion groups (max score >= 90)
    champions = {}
    for key, rs in groups.items():
        scores = [r.get("score") for r in rs if isinstance(r.get("score"), (int, float))]
        if not scores or max(scores) < 90:
            continue
        seq = []
        for r in rs:
            cls = class_by_key.get((r.get("project"), r.get("iter_timestamp")), None)
            seq.append({
                "iter_timestamp": r.get("iter_timestamp"),
                "score": r.get("score"),
                "class": cls,
            })
        champions[key] = {
            "max_score": max(scores),
            "n_iters": len(rs),
            "distinct_classes": len({s["class"] for s in seq if s["class"] is not None}),
            "sequence": seq,
            "class_sequence": [s["class"] for s in seq],
        }

    if not champions:
        print("No champion groups (max_score >= 90) found in corpus.", file=sys.stderr)
        out = {"n_champions": 0, "note": "no champion groups in archive"}
        out_path = OUT_DIR / f"champion_trajectory_sequences_{date.today()}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2))
        return

    # Transition matrix — (prev_class, curr_class) -> count
    transitions: Counter = Counter()
    transitions_by_project: dict[tuple[str, str], set[str]] = defaultdict(set)
    for key, champ in champions.items():
        seq = [c for c in champ["class_sequence"] if c is not None]
        for i in range(len(seq) - 1):
            pair = (seq[i], seq[i + 1])
            transitions[pair] += 1
            transitions_by_project[pair].add(key[0])

    # Common first-class occurrences
    first_classes = Counter()
    for champ in champions.values():
        for c in champ["class_sequence"]:
            if c is not None:
                first_classes[c] += 1
                break

    # Class frequency across all champion iters
    class_freq = Counter()
    for champ in champions.values():
        for c in champ["class_sequence"]:
            if c is not None:
                class_freq[c] += 1

    # Output shape
    out = {
        "generated": str(date.today()),
        "n_champions": len(champions),
        "avg_iters_per_champion": round(sum(c["n_iters"] for c in champions.values()) / len(champions), 1),
        "avg_distinct_classes": round(sum(c["distinct_classes"] for c in champions.values()) / len(champions), 2),
        "statistical_caveat": (
            f"{len(champions)} champion groups is small N for robust Markov-chain "
            "inference. Transitions with count < 3 or project_count < 2 are flagged "
            "insufficient_evidence. Champion trajectory patterns below are "
            "descriptive, not predictive."
        ),
        "first_class_frequency": first_classes.most_common(15),
        "class_frequency_across_champion_iters": class_freq.most_common(20),
        "transitions": [
            {
                "from": prev,
                "to": curr,
                "count": n,
                "project_count": len(transitions_by_project[(prev, curr)]),
                "insufficient_evidence": n < 3 or len(transitions_by_project[(prev, curr)]) < 2,
            }
            for (prev, curr), n in sorted(transitions.items(), key=lambda x: -x[1])[:50]
        ],
        "champions": [
            {
                "project": k[0],
                "rubric_hash": k[1],
                "max_score": v["max_score"],
                "n_iters": v["n_iters"],
                "distinct_classes": v["distinct_classes"],
                "class_sequence_compact": [c for c in v["class_sequence"] if c is not None],
            }
            for k, v in sorted(champions.items(), key=lambda x: -x[1]["max_score"])
        ],
    }

    out_path = OUT_DIR / f"champion_trajectory_sequences_{date.today()}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"wrote {out_path}")
    print(f"  n_champions: {len(champions)}")
    print(f"  avg iters per champion: {out['avg_iters_per_champion']}")
    print(f"  avg distinct classes: {out['avg_distinct_classes']}")
    print(f"  most-common first-class across champions:")
    for cls, n in out["first_class_frequency"][:5]:
        print(f"    {n:>3}  {cls}")
    print(f"  top-3 transitions:")
    for t in out["transitions"][:3]:
        flag = " (insufficient)" if t["insufficient_evidence"] else ""
        print(f"    {t['count']:>3}  {t['from']:<30} -> {t['to']:<30}{flag}")


if __name__ == "__main__":
    main()
