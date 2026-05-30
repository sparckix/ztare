#!/usr/bin/env python3
"""Aggregate taste ratings into weekly insight-quality curves.

Joins:
  - ``analytics/public/queries/taste/_taste_metadata.json`` (week + source mapping)
  - ``analytics/public/queries/taste/_taste_ratings.json`` (rater-produced scores)

Produces:
  - Per-week mean taste score
  - Per-week max taste score (catches paradigm-shifters)
  - Per-week count of high-quality (≥4) artifacts
  - Volume × taste product = total insight density estimate

Outputs:
  ``analytics/public/queries/taste/taste_weighted_insight.json``
  ``analytics/public/queries/taste/taste_weighted_insight.md``

These curves are added back into the trajectory dashboard for the
operator review.

Usage:
    python scripts/public/mining/aggregate_taste.py
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import hashlib

REPO = Path(__file__).resolve().parents[3]
METADATA_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_metadata.json"
RATINGS_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_ratings.json"
LEDGER_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "taste_ledger.json"
PRIMER_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_context_primer.md"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "taste" / "taste_weighted_insight.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "taste" / "taste_weighted_insight.md"

# These constants are mirrored from sample_artifacts_for_taste.py.
# When you bump them there, bump them here. Mismatch = ledger entries
# that don't carry the new values get treated as stale on next read.
LEDGER_SCHEMA_VERSION = 1
CODE_VERSION = "2026-05-06.r1"


def _file_sha(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", type=Path, default=METADATA_PATH)
    ap.add_argument("--ratings", type=Path, default=RATINGS_PATH)
    ap.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    ap.add_argument("--rater-id", default="cold_subagent",
                    help="Identifier for the rater used this run; written into ledger")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    if not args.metadata.exists() or not args.ratings.exists():
        print(f"ERROR: need both {args.metadata} and {args.ratings}")
        return 2

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    ratings = json.loads(args.ratings.read_text(encoding="utf-8")).get("ratings", {})

    # Load existing ledger (may be empty on first run)
    ledger: dict[str, dict] = {}
    if args.ledger.exists():
        try:
            ledger = json.loads(args.ledger.read_text(encoding="utf-8")) or {}
            if not isinstance(ledger, dict):
                ledger = {}
        except Exception:  # noqa: BLE001
            ledger = {}
    print(f"=== taste aggregation ===")
    print(f"  ledger entries before run: {len(ledger)}")

    # Build per-week score lists. Source of score per sample:
    #   1. cached_score from metadata (came from ledger)
    #   2. ratings.json[sample_id] (fresh from rater this run)
    by_week: dict[str, list[dict]] = defaultdict(list)
    by_week_kind: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    n_from_cache = 0
    n_from_fresh = 0
    n_unrated = 0
    new_ledger_entries: list[dict] = []
    for s in metadata.get("samples", []):
        sid = s["sample_id"]
        wk = s["week"]
        kind = s["kind"]
        sha = s.get("content_sha")
        cached = bool(s.get("cached"))
        rationale = ""
        if cached:
            # G8 rater-segregation: a cached score is only valid for THIS
            # series if the ledger entry that produced it was rated by the
            # same rater_id. Otherwise the weekly curve silently pools
            # cold + contextualized methodologies (the 2026-05-16 incident;
            # see docs/concepts/reflexive_mining_methodology.md §3).
            led_entry = ledger.get(sha or "", {})
            if led_entry and led_entry.get("rater") and led_entry.get("rater") != args.rater_id:
                n_unrated += 1
                continue
            score = s.get("cached_score")
            rationale = s.get("cached_rationale", "")
            if score is None:
                continue
            n_from_cache += 1
        else:
            rating = ratings.get(sid)
            if not rating:
                n_unrated += 1
                continue
            score = rating["score"]
            rationale = rating.get("rationale", "")
            n_from_fresh += 1
            # Stage for ledger insertion. Carry schema_version,
            # code_version, primer_sha so a future run can decide
            # whether this entry is still trustworthy after a bug
            # fix / primer change. See delta-method robustness in
            # sample_artifacts_for_taste.py.
            if sha:
                new_ledger_entries.append({
                    "sha": sha,
                    "entry": {
                        "schema_version": LEDGER_SCHEMA_VERSION,
                        "code_version": CODE_VERSION,
                        "primer_sha": _file_sha(PRIMER_PATH),
                        "path_at_first_sight": s.get("source_path", ""),
                        "kind": kind,
                        "first_seen_week": wk,
                        "score": int(score),
                        "rationale": rationale,
                        "rater": args.rater_id,
                        "rated_at_utc": datetime.now(timezone.utc).isoformat(),
                    },
                })
        by_week[wk].append({
            "sample_id": sid,
            "kind": kind,
            "score": int(score),
            "rationale": rationale,
            "source_path": s.get("source_path", ""),
            "from_cache": cached,
        })
        by_week_kind[wk][kind].append(int(score))

    print(f"  scores from ledger cache: {n_from_cache}")
    print(f"  scores from fresh rater:  {n_from_fresh}")
    if n_unrated:
        print(f"  WARN unrated (rater missed sample_id): {n_unrated}")

    # Write back new entries to ledger
    for ne in new_ledger_entries:
        ledger[ne["sha"]] = ne["entry"]
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(json.dumps(ledger, indent=2))
    print(f"  ledger entries after run:  {len(ledger)} (+{len(new_ledger_entries)})")

    # Compute per-week stats
    weekly_stats: dict[str, dict] = {}
    for wk, items in by_week.items():
        scores = [it["score"] for it in items]
        if not scores:
            continue
        weekly_stats[wk] = {
            "n_rated": len(scores),
            "mean_score": round(mean(scores), 2),
            "max_score": max(scores),
            "n_high_quality_ge4": sum(1 for s in scores if s >= 4),
            "n_paradigm_shift_ge5": sum(1 for s in scores if s >= 5),
            "score_distribution": {str(s): scores.count(s) for s in range(6)},
            "by_kind_mean": {
                k: round(mean(v), 2) for k, v in by_week_kind[wk].items() if v
            },
            "top_3_artifacts": sorted(
                items, key=lambda it: -it["score"]
            )[:3],
        }

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_samples_with_ratings": sum(s["n_rated"] for s in weekly_stats.values()),
        "weeks_observed": sorted(weekly_stats.keys()),
        "weekly_stats": weekly_stats,
        "rater_caveat": (
            "Ratings are from an LLM rater (or a stubbed Claude in conversation). "
            "Treat as a noisy estimate of insight density, not ground truth. "
            "The same sample rated by 5 raters typically shows ±1 point spread."
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  weeks rated: {len(weekly_stats)}")
    print(f"  wrote {args.out_json}")

    md = ["# Taste-Weighted Insight Curves\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Samples rated:_ {payload['n_samples_with_ratings']}  ")
    md.append(f"_Weeks observed:_ {len(weekly_stats)}\n")

    md.append("## Weekly insight quality\n")
    md.append(
        "| Week | N | Mean | Max | High-quality (≥4) | Paradigm-shift (≥5) |\n"
        "|---|---:|---:|---:|---:|---:|"
    )
    for wk in sorted(weekly_stats.keys()):
        s = weekly_stats[wk]
        md.append(
            f"| {wk} | {s['n_rated']} | {s['mean_score']} | "
            f"{s['max_score']} | {s['n_high_quality_ge4']} | "
            f"{s['n_paradigm_shift_ge5']} |"
        )
    md.append("")

    md.append("## Top-rated artifact per week\n")
    md.append("| Week | Score | Kind | Path | Rationale |\n|---|---:|---|---|---|")
    for wk in sorted(weekly_stats.keys()):
        top = weekly_stats[wk].get("top_3_artifacts", [])
        if not top:
            continue
        a = top[0]
        md.append(
            f"| {wk} | {a['score']} | `{a['kind']}` | "
            f"`{a['source_path']}` | {a['rationale'][:100]} |"
        )
    md.append("")

    md.append("## Rater caveat\n")
    md.append(payload["rater_caveat"])

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
