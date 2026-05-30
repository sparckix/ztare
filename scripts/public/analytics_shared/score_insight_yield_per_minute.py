#!/usr/bin/env python3
"""
score_insight_yield_per_minute.py

Operator-requested metric (2026-05-09): insight yield per agent-minute.

Definition:
- For each RESOLVED prediction-ledger row with a known realized bucket:
  - `info_bits = -log2(p_realized)` (Shannon self-information of the realized outcome).
    This is high when the predictor was surprised; low when they expected it.
  - `wall_clock_min = harness_duration_ms / 60000` (from agent_telemetry.jsonl,
    NOT from the agent's self-reported effort, which is inflated 4-12×).
  - `insight_per_min = info_bits / wall_clock_min`.

This metric rewards predictions that:
  (a) resolved a low-probability event (information gain) AND
  (b) ran fast in wall-clock terms (low denominator).

It does NOT reward:
  (a) predictions resolving high-probability events ("we said event_1 at 0.95
      and event_1 fired" gives 0.07 bits — confirmation, not insight)
  (b) slow-running agents regardless of insight content.

The metric is unweighted by value (no external valuation function). High-value
information doesn't necessarily score higher than trivia. Operator can apply
post-hoc value-multiplier per row if desired; this script reports the raw
self-info per minute.

Schema:
- `analytics/public/ledgers/prediction/prediction_ledger.jsonl` — predictor side
- `analytics/public/telemetry/agent_telemetry.jsonl` — wall-clock side
- Join by description-substring or task_id (when wired)

Output:
- stdout: per-row insight_per_min table sorted descending
- `analytics/public/telemetry/insight_yield_summary.json` — aggregate + per-substrate rollup

Usage: python scripts/public/analytics_shared/score_insight_yield_per_minute.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def find_realized_p(row: dict) -> float | None:
    """Extract p_realized for the resolved bucket from a PL row."""
    bucket = row.get("actual_outcome_bucket")
    odds = row.get("conditional_odds", [])
    if not bucket or not odds:
        return None
    bucket_lower = bucket.lower()
    for entry in odds:
        event = (entry.get("event") or "").lower()
        bucket_token = bucket_lower.split("_")[1] if "_" in bucket_lower else bucket_lower
        if bucket_token in event or event in bucket_lower:
            return entry.get("p")
    return None


def match_telemetry(pl_row: dict, telemetry: list[dict]) -> dict | None:
    """Best-effort match by description token."""
    desc_pl = (pl_row.get("question") or "").lower()
    substrate = (pl_row.get("substrate") or "").lower()
    pred_id = pl_row.get("prediction_id", "")
    desc_tokens = set(filter(None, [
        substrate.split("/")[-1].strip() if substrate else "",
        desc_pl[:50].lower() if desc_pl else "",
    ]))
    best = None
    best_score = 0
    for t in telemetry:
        td = (t.get("description") or "").lower()
        score = sum(1 for tok in desc_tokens if tok and tok[:20] in td)
        if "MLG" in pred_id and "MLG" in (t.get("description") or "").upper():
            mlg_pl = pred_id.replace("PL-0", "MLG-")
            if mlg_pl[:5].lower() in td:
                score += 5
        if score > best_score:
            best_score = score
            best = t
    return best if best_score >= 1 else None


def main() -> int:
    repo = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
    pl_rows = load_jsonl(repo / "analytics/public/ledgers/prediction/prediction_ledger.jsonl")
    telemetry = load_jsonl(repo / "analytics/public/telemetry/agent_telemetry.jsonl")

    resolved = [r for r in pl_rows if r.get("resolved_at") and r.get("actual_outcome_bucket")]
    print(f"Resolved PL rows: {len(resolved)}")
    print(f"Telemetry rows: {len(telemetry)}")
    print()

    scored: list[dict] = []
    for r in resolved:
        p = find_realized_p(r)
        if p is None or p <= 0 or p >= 1:
            continue
        info_bits = -math.log2(p)
        t = match_telemetry(r, telemetry)
        if t is None:
            wall_min_source = "agent_self_report (TELEMETRY MISS)"
            wall_min = r.get("actual_effort_minutes") or r.get("effort_estimate_agent_minutes") or 0
            wall_min_inflated_warning = True
        else:
            wall_min = t.get("harness_wall_clock_min") or 0
            wall_min_source = "harness_duration_ms"
            wall_min_inflated_warning = False
        if wall_min <= 0:
            continue
        scored.append({
            "prediction_id": r.get("prediction_id"),
            "question_short": (r.get("question") or "")[:80],
            "p_realized": p,
            "info_bits": round(info_bits, 3),
            "wall_clock_min": round(wall_min, 2),
            "wall_min_source": wall_min_source,
            "insight_per_min": round(info_bits / wall_min, 4),
            "telemetry_inflated_warning": wall_min_inflated_warning,
            "predictor": r.get("predictor"),
            "substrate": r.get("substrate"),
        })

    scored.sort(key=lambda x: x["insight_per_min"], reverse=True)
    print(f"{'PL':<8} {'p_real':<7} {'bits':<6} {'min':<6} {'bits/min':<10} {'source':<28} {'question'}")
    print("-" * 130)
    for s in scored:
        warn = "⚠" if s["telemetry_inflated_warning"] else " "
        print(
            f"{s['prediction_id']:<8} "
            f"{s['p_realized']:<7.3f} "
            f"{s['info_bits']:<6.2f} "
            f"{s['wall_clock_min']:<6.2f} "
            f"{s['insight_per_min']:<10.4f} "
            f"{warn} {s['wall_min_source']:<26} "
            f"{s['question_short']}"
        )

    if scored:
        bits_total = sum(s["info_bits"] for s in scored)
        min_total = sum(s["wall_clock_min"] for s in scored)
        weighted_yield = bits_total / min_total if min_total else 0
        per_min_mean = sum(s["insight_per_min"] for s in scored) / len(scored)
        print()
        print(f"Aggregate: {bits_total:.2f} bits over {min_total:.1f} wall-clock-min → {weighted_yield:.4f} bits/min (weighted by wall-clock)")
        print(f"Per-row mean insight/min: {per_min_mean:.4f}")
        print(f"Best row: {scored[0]['prediction_id']} at {scored[0]['insight_per_min']:.4f} bits/min")
        print(f"Worst row: {scored[-1]['prediction_id']} at {scored[-1]['insight_per_min']:.4f} bits/min")

        summary = {
            "computed_at": "2026-05-09",
            "n_resolved": len(scored),
            "n_telemetry_inflated_warnings": sum(1 for s in scored if s["telemetry_inflated_warning"]),
            "bits_total": round(bits_total, 3),
            "wall_clock_min_total": round(min_total, 2),
            "weighted_yield_bits_per_min": round(weighted_yield, 4),
            "per_row_mean_yield": round(per_min_mean, 4),
            "rows": scored,
        }
        (repo / "analytics/public/telemetry/insight_yield_summary.json").write_text(json.dumps(summary, indent=2))
        print(f"\nSummary written: analytics/public/telemetry/insight_yield_summary.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
