#!/usr/bin/env python3
"""Reproduce every quantitative claim in Chapter 2.5 from the frozen dataset.

Reads ``chapter25_classified_iterations.jsonl`` (built by
build_classified_dataset.py from public, git-tracked ZTARE sources) and
recomputes, with deterministic arithmetic and no LLM calls:

  1. score-bucket counts (high >= 85, mid 60-84, low < 60);
  2. the per-failure-class lift table (high-bucket frequency divided by
     low-bucket frequency) and the structural-blocker / ceiling-breaker split;
  3. the persistence profile (groups by project + rubric_hash, bucketed by the
     max score the group reached, with mean iterations and mean distinct
     failure classes per band).

Run:  python verify_chapter25_claims.py
Anyone with the packet can re-run this and obtain the figures the paper cites.
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "chapter25_classified_iterations.jsonl"
HIGH, LOW = 85, 60          # high >= 85 ; low < 60 ; mid is the remainder
MIN_CLASS_N = 20            # ignore classes too rare to rate


def load():
    return [json.loads(l) for l in DATA.open()]


def buckets(rows):
    hi = [r for r in rows if r["score"] >= HIGH]
    lo = [r for r in rows if r["score"] < LOW]
    mid = [r for r in rows if LOW <= r["score"] < HIGH]
    return hi, mid, lo


def lift_table(rows, hi, lo):
    n_hi, n_lo = len(hi), len(lo)
    ch = Counter(r["failure_class"] for r in hi)
    cl = Counter(r["failure_class"] for r in lo)
    total = Counter(r["failure_class"] for r in rows)
    out = []
    for cls, n in total.items():
        if n < MIN_CLASS_N:
            continue
        fh = ch[cls] / n_hi if n_hi else 0.0
        fl = cl[cls] / n_lo if n_lo else 0.0
        lift = (fh / fl) if fl else float("inf")
        out.append((cls, n, fh, fl, lift))
    out.sort(key=lambda x: x[4])
    return out


def persistence(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["project"], r["rubric_hash"])].append(r)
    bands = {">=90": [], "75-89": [], "<50": []}
    for g in groups.values():
        m = max(r["score"] for r in g)
        rec = (len(g), len({r["failure_class"] for r in g}))
        if m >= 90:
            bands[">=90"].append(rec)
        elif 75 <= m <= 89:
            bands["75-89"].append(rec)
        elif m < 50:
            bands["<50"].append(rec)
    return bands


def main() -> int:
    rows = load()
    hi, mid, lo = buckets(rows)
    print(f"corpus: {len(rows)} classified scored iterations")
    print(f"buckets: high>={HIGH} {len(hi)} | mid {len(mid)} | low<{LOW} {len(lo)}\n")

    print(f"{'failure_class':32} {'n':>5} {'hi%':>6} {'lo%':>6} {'lift':>6}")
    for cls, n, fh, fl, lift in lift_table(rows, hi, lo):
        lv = "inf" if lift == float("inf") else f"{lift:.2f}"
        print(f"{cls:32} {n:>5} {fh*100:>5.1f} {fl*100:>5.1f} {lv:>6}")

    print("\npersistence profile (groups by project+rubric_hash):")
    for band, recs in persistence(rows).items():
        if not recs:
            print(f"  peak {band}: 0 groups")
            continue
        iters = [r[0] for r in recs]
        klass = [r[1] for r in recs]
        print(f"  peak {band}: {len(recs)} groups | mean_iter {st.mean(iters):.1f} "
              f"| mean_distinct_classes {st.mean(klass):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
