#!/usr/bin/env python3
"""Stage-C horizon sensitivity repair for Law 3.

The strict Stage-C repair uses a seven-day-before-resolution market probability.
Some rows have Manifold bet histories, but no bet before that seven-day target.
This script tries closer pre-outcome horizons on those missing rows and reports
whether the source-currency effect survives in a mixed-horizon sensitivity
analysis. It does not mutate the DB and does not overwrite the strict join.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
STRICT_JOIN = WORKSPACE / "cutoff_stage_c_base_rate_join_report.json"
MISSING_ROWS = WORKSPACE / "cutoff_stage_c_base_rate_join_missing_contracts.jsonl"
DEFAULT_OUT = WORKSPACE
ACQUIRE_HELPER = REPO / "projects/llm_forecasting_calibration_program/tools/cutoff_stage_c_manifold_probability_acquire.py"
JOIN_HELPER = REPO / "projects/llm_forecasting_calibration_program/tools/cutoff_stage_c_base_rate_join.py"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def choose_horizon_repair(
    row: dict[str, Any],
    *,
    acquire: Any,
    horizons: list[int],
    max_pages: int,
    sleep_ms: int,
) -> dict[str, Any]:
    attempts = []
    chosen: dict[str, Any] | None = None
    for horizon in horizons:
        result = acquire.acquire_one(
            row,
            days_before_resolution=horizon,
            max_pages=max_pages,
            sleep_ms=sleep_ms,
        )
        attempts.append(
            {
                "days_before_resolution": horizon,
                "fetch_status": result.get("fetch_status"),
                "base_rate_value": result.get("base_rate_value"),
                "base_rate_band": result.get("base_rate_band"),
                "selection_method": result.get("selection_method"),
                "bets_fetched": result.get("bets_fetched"),
            }
        )
        if result.get("fetch_status") == "joined":
            chosen = result
            break
    if chosen is None:
        chosen = result if attempts else {**row, "fetch_status": "not_attempted"}
    return {
        **chosen,
        "horizon_repair_attempts": attempts,
        "horizon_repair_status": "joined" if chosen.get("fetch_status") == "joined" else "unrepaired",
        "horizon_repair_days_before_resolution": chosen.get("target_days_before_resolution"),
        "horizon_repair_note": (
            "sensitivity_only_closer_pre_outcome_probability"
            if chosen.get("fetch_status") == "joined"
            else "no_join_at_requested_horizons"
        ),
    }


def merged_contract_rows(strict: dict[str, Any], repairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repair_by_id = {
        str(row.get("contract_id")): row
        for row in repairs
        if row.get("fetch_status") == "joined"
    }
    out = []
    for row in strict.get("contract_base_rates", []):
        cid = str(row.get("contract_id"))
        repair = repair_by_id.get(cid)
        if row.get("fetch_status") == "joined":
            out.append({**row, "repair_tier": "strict_7d_or_forecastbench"})
        elif repair:
            out.append(
                {
                    **row,
                    "fetch_status": "joined",
                    "base_rate_value": repair.get("base_rate_value"),
                    "base_rate_band": repair.get("base_rate_band"),
                    "base_rate_provenance": (
                        f"{repair.get('base_rate_provenance')}:"
                        f"horizon_{repair.get('target_days_before_resolution')}d"
                    ),
                    "prior_timestamp": repair.get("prior_timestamp"),
                    "source_question_id": repair.get("market_id"),
                    "selection_method": repair.get("selection_method"),
                    "repair_tier": f"horizon_{repair.get('target_days_before_resolution')}d",
                }
            )
        else:
            out.append({**row, "repair_tier": "missing"})
    return out


def build_report(
    *,
    db: Path,
    strict_join: Path,
    missing_path: Path,
    horizons: list[int],
    max_pages: int,
    sleep_ms: int,
) -> dict[str, Any]:
    acquire = load_module(ACQUIRE_HELPER, "stage_c_acquire_helper")
    join = load_module(JOIN_HELPER, "stage_c_join_helper")
    strict = read_json(strict_join)
    missing = read_jsonl(missing_path)
    repairs = [
        choose_horizon_repair(
            row,
            acquire=acquire,
            horizons=horizons,
            max_pages=max_pages,
            sleep_ms=sleep_ms,
        )
        for row in missing
    ]
    merged = merged_contract_rows(strict, repairs)
    merged_effect = join.repaired_effect(merged, db)
    repaired = [row for row in repairs if row.get("fetch_status") == "joined"]
    merged_joined = [row for row in merged if row.get("fetch_status") == "joined"]
    base_rate_effect = (merged_effect.get("base_rate_matched") or {})
    return {
        "schema": "gp245-cutoff-stage-c-horizon-repair-v1",
        "strict_join_report": str(strict_join.relative_to(REPO)),
        "missing_rows_input": str(missing_path.relative_to(REPO)),
        "horizons_days_before_resolution": horizons,
        "missing_rows_attempted": len(missing),
        "horizon_repaired_rows": len(repaired),
        "still_missing_rows": len(missing) - len(repaired),
        "horizon_repaired_relation_counts": dict(Counter(row.get("cutoff_relation") for row in repaired)),
        "horizon_repaired_tier_counts": dict(Counter(row.get("repair_tier") for row in merged_joined)),
        "horizon_repaired_base_rate_bands": dict(Counter(row.get("base_rate_band") for row in repaired)),
        "strict_effect": strict.get("repaired_effect") or {},
        "merged_effect": merged_effect,
        "verdict": (
            "sensitivity_survives_horizon_repair"
            if base_rate_effect.get("post_minus_pre_brier") is not None
            and float(base_rate_effect["post_minus_pre_brier"]) > 0.02
            else "sensitivity_scopes_or_kills_after_horizon_repair"
        ),
        "repairs": repairs,
        "merged_contract_base_rates": merged,
    }


def render_md(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Cutoff Stage-C Horizon Repair",
            "",
            f"- Schema: `{report['schema']}`",
            f"- Verdict: `{report['verdict']}`",
            f"- Missing rows attempted: {report['missing_rows_attempted']}",
            f"- Horizon-repaired rows: {report['horizon_repaired_rows']}",
            f"- Still missing rows: {report['still_missing_rows']}",
            f"- Horizons tried: `{report['horizons_days_before_resolution']}`",
            f"- Repaired relation counts: `{report['horizon_repaired_relation_counts']}`",
            f"- Repaired base-rate bands: `{report['horizon_repaired_base_rate_bands']}`",
            f"- Strict effect: `{report['strict_effect']}`",
            f"- Merged effect: `{report['merged_effect']}`",
            "",
            "## Interpretation",
            "",
            "This is a sensitivity analysis, not a replacement for the strict seven-day repair.",
            "Rows repaired here use closer pre-outcome Manifold probabilities and should be described as mixed-horizon evidence.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--strict-join", type=Path, default=STRICT_JOIN)
    parser.add_argument("--missing", type=Path, default=MISSING_ROWS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--horizons", default="3,1")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--sleep-ms", type=int, default=50)
    args = parser.parse_args()
    horizons = [int(part.strip()) for part in args.horizons.split(",") if part.strip()]
    report = build_report(
        db=args.db,
        strict_join=args.strict_join,
        missing_path=args.missing,
        horizons=horizons,
        max_pages=args.max_pages,
        sleep_ms=args.sleep_ms,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "cutoff_stage_c_horizon_repair_report.json").write_text(
        json.dumps({k: v for k, v in report.items() if k not in {"repairs", "merged_contract_base_rates"}}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "cutoff_stage_c_horizon_repair_report.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    write_jsonl(args.out_dir / "cutoff_stage_c_horizon_repair_acquisition.jsonl", report["repairs"])
    write_jsonl(args.out_dir / "cutoff_stage_c_horizon_repair_merged_contracts.jsonl", report["merged_contract_base_rates"])
    print(f"wrote {args.out_dir / 'cutoff_stage_c_horizon_repair_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
