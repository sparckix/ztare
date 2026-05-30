#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""build_taste_canonical_series.py — the canonical week-over-week taste
curve, computed read-only from the full rater-segregated ledger.

Why this exists. ``aggregate_taste.py`` builds the weekly curve from the
*current sample's* cached/fresh scores. That is sample-scoped, not the
full historical series, so its week-over-week numbers depend on which
artifacts happen to be in this week's stratified sample. The canonical
recursive-gain read needs the full history of every artifact ever
rated by the canonical rater. See
``docs/concepts/reflexive_mining_methodology.md`` §5c.

What this does. Reads ``taste_ledger.json`` (every rating the apparatus
has ever produced), filters to a single rater (default:
``cold_subagent_contextualized`` — the canonical contextualized rater),
groups by ``first_seen_week``, and emits per-week stats with the same
shape as ``taste_weighted_insight.json`` so downstream consumers
(``build_p0_metrics.py``, the dashboard) can swap source files without
schema churn.

Pure read-only. Never writes to the ledger, never calls a model, never
mutates the sample-scoped artifact.

Outputs:
    analytics/public/queries/taste/taste_canonical_series.json
    analytics/public/queries/taste/taste_canonical_series.md

Usage:
    python scripts/public/mining/build_taste_canonical_series.py
    python scripts/public/mining/build_taste_canonical_series.py --rater cold_subagent_contextualized
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO = Path(__file__).resolve().parents[3]
LEDGER_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "taste_ledger.json"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "taste" / "taste_canonical_series.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "taste" / "taste_canonical_series.md"
CANONICAL_RATER = "cold_subagent_contextualized"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    ap.add_argument("--rater", default=CANONICAL_RATER,
                    help="Rater id to compute the canonical curve for "
                         f"(default: {CANONICAL_RATER!r}).")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    if not args.ledger.exists():
        print(f"ERROR: ledger not found: {args.ledger}")
        return 2

    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    if not isinstance(ledger, dict):
        print(f"ERROR: ledger has unexpected shape ({type(ledger).__name__})")
        return 2

    entries = [e for e in ledger.values()
               if isinstance(e, dict) and e.get("rater") == args.rater]
    print(f"=== canonical taste series (rater={args.rater!r}) ===")
    print(f"  ledger entries total:                  {len(ledger)}")
    print(f"  filtered to canonical rater:           {len(entries)}")

    by_week: dict[str, list[dict]] = defaultdict(list)
    by_week_kind: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        wk = e.get("first_seen_week")
        if not wk:
            continue
        try:
            score = int(e["score"])
        except (KeyError, TypeError, ValueError):
            continue
        kind = e.get("kind", "")
        by_week[wk].append({
            "kind": kind,
            "score": score,
            "rationale": e.get("rationale", ""),
            "source_path": e.get("path_at_first_sight", ""),
        })
        by_week_kind[wk][kind].append(score)

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
            "top_3_artifacts": sorted(items, key=lambda it: -it["score"])[:3],
        }

    weeks_sorted = sorted(weekly_stats.keys())
    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(args.ledger.relative_to(REPO)),
        "rater": args.rater,
        "scope": "full historical ledger, rater-segregated — NOT sample-scoped",
        "n_entries_in_ledger": len(ledger),
        "n_entries_for_rater": len(entries),
        "n_samples_with_ratings": sum(s["n_rated"] for s in weekly_stats.values()),
        "weeks_observed": weeks_sorted,
        "weekly_stats": weekly_stats,
        "rater_caveat": (
            "Canonical series from the full ledger, filtered to one rater. "
            "The recursive-gain read is the week-over-week shape of this "
            "series (not the sample-scoped aggregate). See "
            "docs/concepts/reflexive_mining_methodology.md §5c for the "
            "discipline rule and §3 for the RCA the rule was added for."
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  weeks observed:                        {len(weeks_sorted)}")
    print(f"  wrote {args.out_json.relative_to(REPO)}")

    md = ["# Taste — Canonical Series (Ledger-Derived)\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Rater:_ `{args.rater}`  ")
    md.append(f"_Source:_ `{payload['source']}` (full ledger, read-only)  ")
    md.append(f"_Scope:_ {payload['scope']}  ")
    md.append(f"_Entries (rater-filtered / total):_ {len(entries)} / {len(ledger)}  ")
    md.append(f"_Weeks observed:_ {len(weeks_sorted)}\n")

    md.append("## Weekly insight quality\n")
    md.append(
        "| Week | N | Mean | Max | High-quality (≥4) | Paradigm-shift (≥5) |\n"
        "|---|---:|---:|---:|---:|---:|"
    )
    for wk in weeks_sorted:
        s = weekly_stats[wk]
        md.append(
            f"| {wk} | {s['n_rated']} | {s['mean_score']} | "
            f"{s['max_score']} | {s['n_high_quality_ge4']} | "
            f"{s['n_paradigm_shift_ge5']} |"
        )
    md.append("")

    md.append("## Top artifact per week\n")
    md.append("| Week | Score | Kind | Path | Rationale |\n|---|---:|---|---|---|")
    for wk in weeks_sorted:
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
    print(f"  wrote {args.out_md.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
