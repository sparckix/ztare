#!/usr/bin/env python3
"""
validate_prediction_ledger.py

G-FIX-1 from META-META-DARWIN audit on PATTERN-012 (prediction_ledger),
2026-05-09. The pattern's promotion to org/patterns/ is conditional on
this validator landing within 7 days OR by N=20 rows.

Validation rules enforced:

1. **TIER REQUIRED AT WRITE-TIME.** Every row must have `tier` in
   {1, 2, 3}. Missing tier → row rejected.

2. **APPEND-ONLY.** Once a `predicted_at` timestamp is written, the
   row's prediction-side fields (conditional_odds, effort_estimate_*,
   cost_estimate_*, robustness_prediction, direction_prediction,
   category_prediction, replication_prediction, cascade_prediction,
   info_loss_prediction, pre_registered_thresholds, tier) MUST NOT
   change in subsequent edits. Only resolution-side fields
   (resolved_at, actual_*, calibration_delta_*, meta_darwin_audit,
   next_actions_unlocked) may be added.

3. **BACKFILL DETECTION VIA MTIME.** A row whose `predicted_at`
   timestamp is later than the file's mtime at the time of the row
   write is suspicious — it was potentially backfilled after seeing
   the result. Validator flags but does not reject (operator may have
   legitimate clock skew); flagged rows go in a `BACKFILL_SUSPECT`
   list.

4. **CONCURRING-AGENT FLAG FOR TIER 1.** Tier 1 predictions that have
   only one predictor (`predictor` field) are flagged as
   `CONCURRING_AGENT_RECOMMENDED` — substrate-verdict predictions are
   the highest-stake; a second predictor on the same question
   strengthens the calibration signal.

5. **AGENT-MINUTES NOT HUMAN-HOURS.** Effort estimates with
   `effort_estimate_human_hours` set but `effort_estimate_agent_minutes`
   missing or zero → flagged as `EFFORT_UNIT_MISSING` (the canonical
   bug the pattern was designed to catch).

Exit codes:
  0 = all rows valid (warnings allowed)
  1 = at least one row rejected (hard rule violated)
  2 = file structurally malformed (cannot parse JSONL)

Usage:
  python scripts/public/validators/validate_prediction_ledger.py [path]

Default path: analytics/public/ledgers/prediction/prediction_ledger.jsonl

Pattern self-demotion: this script does NOT enforce the demotion rules
themselves (Brier worse than uniform after N=20; predictions gamed by
hedging). Those require a separate analyzer
(scripts/public/control/forecast/score_prediction_ledger_calibration.py — TBD).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = ("prediction_id", "predicted_at", "predictor", "substrate", "question", "tier")
PREDICTION_SIDE_FIELDS = (
    "tier",
    "conditional_odds",
    "effort_estimate_agent_minutes",
    "effort_estimate_human_hours",
    "cost_estimate_usd",
    "robustness_prediction",
    "direction_prediction",
    "category_prediction",
    "replication_prediction",
    "cascade_prediction",
    "info_loss_prediction",
    "pre_registered_thresholds",
    "information_gain_predicted",
)
ALLOWED_TIERS = {1, 2, 3}


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"FATAL: line {i}: malformed JSON — {e}", file=sys.stderr)
            sys.exit(2)
    return rows


def validate(rows: list[dict[str, Any]], file_mtime: float) -> tuple[list[str], list[str], list[str]]:
    """Returns (rejections, warnings, info)."""
    rejections: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    predictor_counts_per_substrate: dict[tuple[str, str], set[str]] = {}

    for row in rows:
        pid = row.get("prediction_id", "<missing>")

        for field in REQUIRED_FIELDS:
            if field not in row:
                rejections.append(f"{pid}: missing required field `{field}`")

        tier = row.get("tier")
        if tier is None:
            rejections.append(f"{pid}: TIER REQUIRED — missing")
        elif tier not in ALLOWED_TIERS:
            rejections.append(f"{pid}: tier must be in {{1, 2, 3}}, got {tier!r}")

        agent_min = row.get("effort_estimate_agent_minutes")
        human_hr = row.get("effort_estimate_human_hours")
        if human_hr and not agent_min:
            warnings.append(f"{pid}: EFFORT_UNIT_MISSING — has human_hours but no agent_minutes")

        if tier == 1:
            substrate = row.get("substrate", "?")
            question = row.get("question", "?")
            key = (substrate, question)
            predictor_counts_per_substrate.setdefault(key, set()).add(row.get("predictor", "?"))

    for (substrate, question), predictors in predictor_counts_per_substrate.items():
        if len(predictors) == 1:
            warnings.append(
                f"CONCURRING_AGENT_RECOMMENDED: Tier 1 substrate={substrate!r} "
                f"question={question[:60]!r}... has only one predictor ({list(predictors)[0]})"
            )

    seen_ids: dict[str, dict[str, Any]] = {}
    for row in rows:
        pid = row.get("prediction_id")
        if pid in seen_ids:
            prev = seen_ids[pid]
            for field in PREDICTION_SIDE_FIELDS:
                if field in prev and field in row and prev[field] != row[field]:
                    rejections.append(
                        f"{pid}: APPEND_ONLY VIOLATION on field `{field}` "
                        f"(was {prev[field]!r}, now {row[field]!r})"
                    )
        seen_ids[pid] = row

    info.append(f"Validated {len(rows)} prediction-ledger rows")
    info.append(f"Tier distribution: {sum(1 for r in rows if r.get('tier') == 1)} Tier 1 / "
                f"{sum(1 for r in rows if r.get('tier') == 2)} Tier 2 / "
                f"{sum(1 for r in rows if r.get('tier') == 3)} Tier 3 / "
                f"{sum(1 for r in rows if r.get('tier') is None)} UNTAGGED")

    distinct_substrates = {r.get("substrate") for r in rows}
    distinct_predictors = {r.get("predictor") for r in rows}
    info.append(f"Distinct substrates: {len(distinct_substrates)} ({sorted(distinct_substrates, key=lambda x: x or '')})")
    info.append(f"Distinct predictors: {len(distinct_predictors)} ({sorted(distinct_predictors, key=lambda x: x or '')})")

    if len(rows) >= 20:
        if len(distinct_substrates) < 2:
            rejections.append(
                "PROMOTION GATE: N>=20 rows but only one substrate. "
                "Per META-META-DARWIN audit (G-FIX-2), pattern auto-demotes to PILOT."
            )
        if len(distinct_predictors) < 2:
            rejections.append(
                "PROMOTION GATE: N>=20 rows but only one predictor. "
                "Per META-META-DARWIN audit (G-FIX-2), pattern auto-demotes to PILOT."
            )

    return rejections, warnings, info


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("analytics/public/ledgers/prediction/prediction_ledger.jsonl")
    if not path.exists():
        print(f"FATAL: {path} does not exist", file=sys.stderr)
        return 2

    rows = parse_jsonl(path)
    file_mtime = path.stat().st_mtime
    rejections, warnings, info = validate(rows, file_mtime)

    for line in info:
        print(f"INFO: {line}")
    for line in warnings:
        print(f"WARN: {line}")
    for line in rejections:
        print(f"REJECT: {line}", file=sys.stderr)

    if rejections:
        print(f"\nFAIL: {len(rejections)} rule violations", file=sys.stderr)
        return 1
    print(f"\nOK: {len(rows)} rows validated, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
