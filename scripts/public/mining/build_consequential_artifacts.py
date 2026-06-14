#!/usr/bin/env python3
"""Per-week consequential-artifacts digest.

Joins:
  - analytics/public/queries/taste/_taste_metadata.json     (sample → week mapping)
  - analytics/public/queries/taste/taste_ledger.json        (sha → score + rationale)
  - analytics/public/queries/graphs/reference_graph.json     (node → in_degree)

Per week, surfaces:
  - Top-N rated artifacts (score ≥ 3) with content snippet, rationale, kind, path
  - Top-N most-cited artifacts (in_degree ≥ 3) — decision-critical infrastructure
  - Synthesized "what happened this week" — stitched from the rationales

Output:
  analytics/public/queries/trajectory/consequential_artifacts_by_week.json

The dashboard's Week Digests view reads this JSON.

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/build_consequential_artifacts.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "analytics" / "public" / "queries"
METADATA_PATH = QUERIES / "taste" / "_taste_metadata.json"
LEDGER_PATH = QUERIES / "taste" / "taste_ledger.json"
GRAPH_PATH = QUERIES / "reference_graph.json"
OUT_JSON = QUERIES / "trajectory" / "consequential_artifacts_by_week.json"


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-rated-per-week", type=int, default=8)
    ap.add_argument("--top-cited-per-week", type=int, default=5)
    ap.add_argument("--score-floor", type=int, default=3,
                    help="Minimum taste score to qualify as consequential")
    ap.add_argument("--out", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    print("=== consequential-artifacts digest ===")
    metadata = _load(METADATA_PATH) or {}
    ledger = _load(LEDGER_PATH) or {}
    ref_graph = _load(GRAPH_PATH) or {}

    samples = metadata.get("samples", [])
    print(f"  samples in metadata: {len(samples)}")

    # Index ledger by sha
    ledger_active = {k: v for k, v in ledger.items() if not k.startswith("_") and isinstance(v, dict)}
    print(f"  ledger active entries: {len(ledger_active)}")

    # Index graph nodes by id
    nodes_by_id: dict[str, dict] = {}
    for n in ref_graph.get("nodes", []) or []:
        nodes_by_id[n["id"]] = n

    # Per week: rated artifacts
    by_week_rated: dict[str, list[dict]] = defaultdict(list)
    for s in samples:
        sha = s.get("content_sha")
        wk = s.get("week")
        if not sha or not wk:
            continue
        # Score either from metadata cache or ledger
        score = s.get("cached_score")
        rationale = s.get("cached_rationale", "")
        if score is None:
            entry = ledger_active.get(sha)
            if entry:
                score = entry.get("score")
                rationale = entry.get("rationale", "")
        if score is None:
            continue
        if score < args.score_floor:
            continue
        by_week_rated[wk].append({
            "sample_id": s.get("sample_id"),
            "kind": s.get("kind"),
            "path": s.get("source_path", ""),
            "score": int(score),
            "rationale": rationale,
            "content_sha": sha,
        })

    # Per week: top-cited artifacts
    by_week_cited: dict[str, list[dict]] = defaultdict(list)
    for nid, n in nodes_by_id.items():
        in_deg = n.get("in_degree", 0)
        if in_deg < 3:
            continue
        wk = n.get("week", "")
        by_week_cited[wk].append({
            "path": nid,
            "kind": n.get("kind"),
            "in_degree": in_deg,
            "out_degree": n.get("out_degree", 0),
            "week": wk,
        })

    # Build per-week digest
    all_weeks = sorted(set(by_week_rated.keys()) | set(by_week_cited.keys()))
    digests = {}
    for wk in all_weeks:
        rated = sorted(
            by_week_rated.get(wk, []),
            key=lambda r: -r["score"],
        )[: args.top_rated_per_week]
        cited = sorted(
            by_week_cited.get(wk, []),
            key=lambda r: -r["in_degree"],
        )[: args.top_cited_per_week]

        # Synthesize a one-line "what happened" — concatenate top-3 rationales
        narrative_seeds = [r["rationale"] for r in rated[:3] if r["rationale"]]

        # Group rated artifacts by kind for at-a-glance distribution
        by_kind: dict[str, int] = defaultdict(int)
        for r in rated:
            by_kind[r["kind"]] += 1

        digests[wk] = {
            "week": wk,
            "n_rated_above_floor": len(by_week_rated.get(wk, [])),
            "n_cited_above_floor": len(by_week_cited.get(wk, [])),
            "top_rated": rated,
            "top_cited": cited,
            "rated_by_kind": dict(by_kind),
            "narrative_seeds": narrative_seeds,
        }

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "score_floor": args.score_floor,
        "weeks": digests,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"  weeks with digest: {len(digests)}")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
