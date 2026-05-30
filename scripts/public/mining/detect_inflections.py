#!/usr/bin/env python3
"""Inflection detection on apparatus trajectory curves.

Implements GP-227 Phase 1, step 2. Reads
``analytics/public/queries/trajectory/trajectory_curves.json`` and runs change-point
detection on every metric. Outputs ranked inflection candidates by
multi-metric convergence score.

The discipline (per GP-227): a date counts as a "real" inflection only
when ≥3 of the 9 trajectory metrics show a coincident step-change at
that date. Single-metric inflections are dismissed as metric noise.

Detection method:
  Robust per-curve outlier on first differences:
    - For each curve, compute first differences (week N → week N+1).
    - Mark a week as inflected if its first-difference value is
      > median + 2*MAD (median absolute deviation) of the curve's
      diff distribution.
  This is robust to single high-baseline weeks (which would be
  inflected by a z-score test).

Inflection score = number of metrics in which the week is inflected.
A week with score ≥ 3 (out of 6 quantitative metrics) is a "real"
inflection.

Outputs:
  ``analytics/public/queries/inflection_candidates.{json,md}``

Usage:
    python scripts/public/mining/detect_inflections.py
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[3]
CURVES_PATH = REPO / "analytics" / "public" / "queries" / "trajectory" / "trajectory_curves.json"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "trajectory" / "inflection_candidates.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "trajectory" / "inflection_candidates.md"


def _mad(xs: list[float]) -> float:
    if not xs:
        return 0.0
    m = median(xs)
    return median([abs(x - m) for x in xs])


def _detect_inflected_weeks(
    curve: dict[str, int],
    weeks_sorted: list[str],
    *,
    is_cumulative: bool = False,
    z_threshold: float = 1.0,
) -> set[str]:
    """Return set of weeks where the curve shows an outlier step-change.

    For cumulative curves (Sophistication-A), use first differences.
    For per-week curves, use raw values.

    Detection: top half of the values that ALSO exceed
    ``median + z_threshold * MAD``. With small N (≤6 weeks), the MAD-only
    test was too conservative — all weeks were "accelerating" so no
    single one stood out. Lowering z to 1.0 + requiring above-median
    surfaces the bigger jumps without flagging every flat-ish week.
    """
    if not curve or len(weeks_sorted) < 3:
        return set()
    if is_cumulative:
        diffs: list[float] = []
        weekly_diffs: dict[str, float] = {}
        prev = 0
        for wk in weeks_sorted:
            v = curve.get(wk, prev)
            diffs.append(float(v - prev))
            weekly_diffs[wk] = float(v - prev)
            prev = v
    else:
        weekly_diffs = {wk: float(curve.get(wk, 0)) for wk in weeks_sorted}
        diffs = list(weekly_diffs.values())

    m = median(diffs)
    mad_val = _mad(diffs)
    if mad_val == 0:
        return set()
    threshold = m + z_threshold * mad_val
    # Require above-median AND above the MAD-threshold AND positive
    return {
        wk for wk, d in weekly_diffs.items()
        if d > threshold and d > m and d > 0
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curves", type=Path, default=CURVES_PATH)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--z-threshold", type=float, default=2.0,
                    help="MAD multiplier for inflection detection (default 2.0)")
    ap.add_argument("--convergence-floor", type=int, default=2,
                    help="Min metrics in which a week must inflect (default 2 — GP-227 says 3 once data is denser)")
    args = ap.parse_args()

    print("=== inflection detector ===")
    if not args.curves.exists():
        print(f"  ERROR: missing {args.curves}; run mine_trajectory_curves.py first")
        return 2

    data = json.loads(args.curves.read_text(encoding="utf-8"))
    curves = data.get("curves") or {}
    weeks = data.get("weeks") or []
    print(f"  weeks: {len(weeks)}")
    print(f"  curves: {list(curves.keys())}")

    # Run detection per curve
    inflections_per_curve: dict[str, set[str]] = {}
    for name, curve in curves.items():
        is_cum = "cumulative" in name
        inflected = _detect_inflected_weeks(
            curve, weeks,
            is_cumulative=is_cum,
            z_threshold=args.z_threshold,
        )
        inflections_per_curve[name] = inflected
        print(f"  {name}: {len(inflected)} inflected weeks {sorted(inflected)}")

    # Convergence: for each week, count how many metrics inflect there
    convergence_score: dict[str, int] = defaultdict(int)
    convergence_metrics: dict[str, list[str]] = defaultdict(list)
    for name, weeks_set in inflections_per_curve.items():
        for wk in weeks_set:
            convergence_score[wk] += 1
            convergence_metrics[wk].append(name)

    # Rank candidates
    ranked = []
    for wk, score in sorted(convergence_score.items(), key=lambda kv: (-kv[1], kv[0])):
        ranked.append({
            "week": wk,
            "convergence_score": score,
            "metrics": convergence_metrics[wk],
            "verdict": (
                "real_inflection"
                if score >= args.convergence_floor + 1
                else (
                    "candidate_inflection"
                    if score >= args.convergence_floor
                    else "single_metric_noise"
                )
            ),
        })

    # Cross-reference with external_events
    events = data.get("external_events") or []
    events_by_week: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        ds = str(e.get("date", "")).strip()
        if not ds:
            continue
        try:
            dt = datetime.fromisoformat(ds).replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            continue
        from datetime import timedelta as _td
        monday = dt - _td(days=dt.weekday())
        wk = monday.strftime("%Y-%m-%d")
        events_by_week[wk].append(e)

    for entry in ranked:
        ev = events_by_week.get(entry["week"], [])
        if ev:
            entry["coincident_external_events"] = [
                {"date": e.get("date"), "kind": e.get("kind"), "label": e.get("label")}
                for e in ev
            ]

    real_count = sum(1 for r in ranked if r["verdict"] == "real_inflection")
    candidate_count = sum(1 for r in ranked if r["verdict"] == "candidate_inflection")

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "z_threshold": args.z_threshold,
        "convergence_floor": args.convergence_floor,
        "n_real_inflections": real_count,
        "n_candidate_inflections": candidate_count,
        "ranked_inflections": ranked,
        "inflections_per_curve": {
            k: sorted(v) for k, v in inflections_per_curve.items()
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Inflection Candidates — Multi-Metric Convergence\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Convergence floor:_ {args.convergence_floor}  "
        f"_Real inflections:_ {real_count}  "
        f"_Candidate inflections:_ {candidate_count}\n"
    )
    md.append(
        "**Discipline:** dates surfaced here come from the trajectory record, not "
        "operator memory. A week counts as a real inflection only if ≥{0} "
        "of the 6 trajectory metrics show coincident step-changes.\n".format(args.convergence_floor + 1)
    )
    md.append("## Ranked weeks (highest convergence first)\n")
    md.append(
        "| Week | Score | Verdict | Metrics with step-change | External events |\n"
        "|---|---:|---|---|---|"
    )
    for r in ranked[:30]:
        ev = r.get("coincident_external_events") or []
        ev_str = "; ".join(
            f"{e.get('date')} {e.get('label', '')[:40]}" for e in ev
        )[:120] or "—"
        metrics_str = ", ".join(m.replace("_", " ")[:30] for m in r["metrics"])
        md.append(
            f"| {r['week']} | {r['convergence_score']} | "
            f"`{r['verdict']}` | {metrics_str} | {ev_str} |"
        )
    md.append("")

    md.append("## Per-curve inflection lists (raw)\n")
    for k, v in payload["inflections_per_curve"].items():
        if v:
            md.append(f"- **{k}**: {', '.join(v)}")
        else:
            md.append(f"- **{k}**: (none)")
    md.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
