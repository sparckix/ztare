#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""build_dashboard_bundle.py — fold the dashboard's per-dataset JSONs
into one bundle file.

The dashboard previously copied nine separate JSONs into ``src/data/``
and ``public/data/``; the React app statically imported each one. Each
file was a drift surface (path mismatches stranded several at pre-reorg
locations — see ``docs/concepts/reflexive_mining_methodology.md`` §4 G1–G4).

One bundle file collapses the contract surface: one path to verify, one
sanitizer pass, one shape for the React consumer to index. The bundle
schema is intentionally small:

    {
      "schema_version": 1,
      "bundle_generated_utc": "...",
      "sources": { "<datasetKey>": "<repo-relative path>", ... },
      "datasets": { "<datasetKey>": <parsed json or null>, ... }
    }

Outputs:
    analytics/public/queries/dashboard_bundle.json

Pure read-only over the source datasets. A missing source is recorded
as ``null`` in ``datasets`` with the path still listed in ``sources`` —
the React consumer treats null as "not yet produced" without crashing
the build (matches the prior placeholder behavior).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

# Dataset key → repo-relative source path. The KEY is the React
# DashboardData field name; do not rename without changing the consumer
# in ``analytics/public/dashboard/src/lib/data.ts``.
DATASETS: dict[str, str] = {
    "trajectoryCurves":        "analytics/public/queries/trajectory/trajectory_curves.json",
    "inflections":             "analytics/public/queries/trajectory/inflection_candidates.json",
    "taste":                   "analytics/public/queries/taste/taste_weighted_insight.json",
    "referenceGraph":          "analytics/public/queries/reference_graph.json",
    "consequentialArtifacts":  "analytics/public/queries/trajectory/consequential_artifacts_by_week.json",
    "recursiveGainCandidates": "analytics/public/queries/trajectory/recursive_gain_candidates.json",
    "bifurcation":             "analytics/public/ledgers/reflexive/bifurcation_report.json",
    "graphSowhat":             "analytics/public/queries/graph_sowhat.json",
    "p0Metrics":               "analytics/public/ledgers/reflexive/p0_metrics.json",
}

# JSONL datasets (parsed into a list of rows). Append-only history files
# whose week-over-week shape drives sparklines and trend reads.
JSONL_DATASETS: dict[str, str] = {
    "p0MetricsHistory":        "analytics/public/ledgers/reflexive/p0_metrics_history.jsonl",
}

DEFAULT_OUT = REPO / "analytics" / "public" / "queries" / "dashboard_bundle.json"


def _load(rel: str) -> tuple[object | None, str]:
    p = REPO / rel
    if not p.is_file():
        return None, "missing"
    try:
        return json.loads(p.read_text(encoding="utf-8")), "ok"
    except json.JSONDecodeError as exc:
        return None, f"parse-error: {exc.msg} (line {exc.lineno})"


def _load_jsonl(rel: str) -> tuple[list | None, str]:
    p = REPO / rel
    if not p.is_file():
        return None, "missing"
    rows: list = []
    try:
        for n, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError as exc:
                return None, f"parse-error line {n}: {exc.msg}"
    except OSError as exc:
        return None, f"read-error: {exc}"
    return rows, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    datasets: dict[str, object | None] = {}
    statuses: dict[str, str] = {}
    print("=== dashboard bundle ===")
    for key, rel in DATASETS.items():
        data, status = _load(rel)
        datasets[key] = data
        statuses[key] = status
        marker = "ok " if status == "ok" else "MISS" if status == "missing" else "FAIL"
        print(f"  [{marker}] {key:<26} ← {rel}")
    for key, rel in JSONL_DATASETS.items():
        rows, status = _load_jsonl(rel)
        datasets[key] = rows
        statuses[key] = status
        marker = "ok " if status == "ok" else "MISS" if status == "missing" else "FAIL"
        n = f" ({len(rows)} rows)" if rows is not None else ""
        print(f"  [{marker}] {key:<26} ← {rel}{n}")

    payload = {
        "schema_version": 1,
        "bundle_generated_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {**DATASETS, **JSONL_DATASETS},
        "statuses": statuses,
        "datasets": datasets,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    n_ok = sum(1 for s in statuses.values() if s == "ok")
    total = len(DATASETS) + len(JSONL_DATASETS)
    print(f"  wrote {args.out.relative_to(REPO)}  ({n_ok}/{total} datasets present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
