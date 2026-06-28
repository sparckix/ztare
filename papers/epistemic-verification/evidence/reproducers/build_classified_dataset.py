#!/usr/bin/env python3
"""Build the frozen, classified iteration dataset behind Chapter 2.5.

Provenance step (run once). Joins three public, git-tracked sources in the
ZTARE repository into one self-contained file that ``verify_chapter25_claims.py``
then reads. The join is deterministic: every label is read from a cached file,
so re-running this script on the same sources reproduces the same dataset.

Sources (paths relative to the ZTARE repo root, set ZTARE_REPO_ROOT):
  analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl
      one record per scored iteration: project, iter_timestamp, score,
      judge/mutator model ids, rubric/charter hashes, weakest_point text.
  analytics/public/queries/classification/weakest_link_clusters_2026-04-24.json
      regex/cluster fast-path: (project, iter_timestamp) -> cluster_id.
  analytics/public/queries/classification/weakest_link_llm_subclasses_2026-04-24.json
      finer LLM labels for the records the fast-path left as
      ``other_unclustered``: categories[].members = [[project, iter_ts], ...].

Final class per record = the LLM sub-label when present (more specific),
otherwise the fast-path cluster_id. Records with no score or no label are
dropped (they cannot enter the score-bucketed analysis).

Output: chapter25_classified_iterations.jsonl next to this script's packet root.

Note on snapshot drift: the live archive keeps growing. The classification
caches were frozen 2026-04-24. This join therefore covers the records present
in BOTH the current archive and the 2026-04-24 caches; that intersection is
the corpus Chapter 2.5 reports. The figures in the paper are whatever
verify_chapter25_claims.py prints for this file, not a historical snapshot.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO = Path(os.environ.get("ZTARE_REPO_ROOT", ".")).resolve()
ARCHIVE = REPO / "analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl"
CLUSTERS = REPO / "analytics/public/queries/classification/weakest_link_clusters_2026-04-24.json"
LLMSUB = REPO / "analytics/public/queries/classification/weakest_link_llm_subclasses_2026-04-24.json"
OUT = Path(__file__).resolve().parent.parent / "chapter25_classified_iterations.jsonl"

KEEP = ("project", "iter_timestamp", "score", "judge_model_id",
        "mutator_model_id", "rubric_hash", "charter_hash", "weakest_point")


def _key(project, ts):
    return (project, int(ts)) if ts is not None else None


def main() -> int:
    clusters = json.loads(CLUSTERS.read_text())
    fastpath = {}
    for lab in clusters["_labels"]:
        k = _key(lab["project"], lab.get("iter_timestamp"))
        if k:
            fastpath[k] = lab["cluster_id"]

    llm = json.loads(LLMSUB.read_text())
    fine = {}
    for cat in llm["categories"]:
        for project, ts in cat["members"]:
            k = _key(project, ts)
            if k:
                fine[k] = cat["category"]

    rows = []
    with ARCHIVE.open() as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("score") is None:
                continue
            k = _key(rec.get("project"), rec.get("iter_timestamp"))
            if not k:
                continue
            cls = fine.get(k) or fastpath.get(k)
            if cls is None:
                continue
            row = {kk: rec.get(kk) for kk in KEEP}
            row["failure_class"] = cls
            rows.append(row)

    rows.sort(key=lambda r: (r["project"], r["iter_timestamp"]))
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} classified scored iterations -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
