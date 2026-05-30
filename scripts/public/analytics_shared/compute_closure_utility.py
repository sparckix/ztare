#!/usr/bin/env python3
"""Compute closure-utility metric from Codex-marked nomination panel.

Reads `analytics/public/queries/novelty/codex_nomination_panel.csv` after Codex has
filled the `codex_verdict` column for each nomination. Computes:

  - Per-source novelty_rate = novel_plausible / (novel + considered + wrong + trivial)
  - Aggregate novelty_rate
  - Per-source already_considered_rate (tells you which apparatus is most descriptive)
  - Per-source wrong_rate (tells you which apparatus most hallucinates)

Verdict: > 30% novelty_rate = apparatus delivers real surprise.
        < 5%  = confirmation theater.

Usage:
    # After Codex fills CSV:
    python scripts/public/analytics_shared/compute_closure_utility.py
    python scripts/public/analytics_shared/compute_closure_utility.py --csv path/to/panel.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VALID_VERDICTS = {"already_considered", "novel_plausible", "wrong",
                   "trivial", "cant_classify"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path,
                    default=REPO / "analytics" / "public" / "queries" /
                              "codex_nomination_panel.csv")
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" /
                              "closure_utility_metric.json")
    args = ap.parse_args()

    if not args.csv.exists():
        print(f"missing {args.csv}; run build_codex_nomination_panel.py first")
        return 1

    rows = []
    with args.csv.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        print("(empty CSV)")
        return 1

    n_total = len(rows)
    n_marked = sum(1 for r in rows if r.get("codex_verdict", "").strip())
    if n_marked == 0:
        print(f"=== Codex hasn't marked any of {n_total} nominations yet ===")
        print(f"Mark the codex_verdict column in {args.csv}")
        print(f"Valid verdicts: {sorted(VALID_VERDICTS)}")
        return 1

    # Per-source stats
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        verdict = r.get("codex_verdict", "").strip()
        if not verdict:
            continue
        if verdict not in VALID_VERDICTS:
            print(f"  WARNING: row {r.get('nomination_id')} has invalid verdict "
                  f"{verdict!r} (valid: {sorted(VALID_VERDICTS)})")
            continue
        # Normalize source: strip "(rank N)" suffix
        source = r.get("source", "?").split(" (")[0]
        by_source[source][verdict] += 1

    print(f"=== closure-utility metric ===")
    print(f"  total nominations: {n_total}")
    print(f"  marked: {n_marked}")
    print(f"  unmarked: {n_total - n_marked}")

    overall = Counter()
    for source, counts in by_source.items():
        total = sum(counts.values())
        novelty = counts["novel_plausible"] / max(total, 1)
        considered = counts["already_considered"] / max(total, 1)
        wrong_rate = counts["wrong"] / max(total, 1)
        trivial_rate = counts["trivial"] / max(total, 1)
        cant_rate = counts["cant_classify"] / max(total, 1)
        verdict_label = ("REAL SURPRISE" if novelty > 0.30
                          else "MIXED" if novelty > 0.05
                          else "CONFIRMATION THEATER")
        print(f"\n  [{source}] (n={total})")
        print(f"    novelty_rate:        {novelty:.0%}  → {verdict_label}")
        print(f"    already_considered:  {considered:.0%}")
        print(f"    wrong:               {wrong_rate:.0%}")
        print(f"    trivial:             {trivial_rate:.0%}")
        print(f"    cant_classify:       {cant_rate:.0%}")
        overall.update(counts)

    total_marked = sum(overall.values())
    overall_novelty = overall["novel_plausible"] / max(total_marked, 1)
    print(f"\n  === aggregate ===")
    print(f"  total marked: {total_marked}")
    print(f"  aggregate novelty_rate: {overall_novelty:.0%}")
    if overall_novelty > 0.30:
        print(f"  → APPARATUS DELIVERS REAL SURPRISE")
    elif overall_novelty > 0.05:
        print(f"  → MIXED: some real signal, some confirmation theater")
    else:
        print(f"  → CONFIRMATION THEATER: apparatus mostly rediscovers known")

    # Best-source rank
    print(f"\n  === best source by novelty_rate ===")
    ranked = sorted(by_source.items(),
                     key=lambda kv: -kv[1]["novel_plausible"] / max(sum(kv[1].values()), 1))
    for source, counts in ranked:
        total = sum(counts.values())
        rate = counts["novel_plausible"] / max(total, 1)
        print(f"    {source}: {counts['novel_plausible']}/{total} = {rate:.0%}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "n_total": n_total,
        "n_marked": n_marked,
        "aggregate_novelty_rate": overall_novelty,
        "verdict": ("real_surprise" if overall_novelty > 0.30
                     else "mixed" if overall_novelty > 0.05
                     else "confirmation_theater"),
        "per_source": {s: dict(c) for s, c in by_source.items()},
    }, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
