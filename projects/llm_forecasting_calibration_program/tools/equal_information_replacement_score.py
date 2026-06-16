#!/usr/bin/env python3
"""Score the replacement equal-information model-vs-market packet."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.experiment_stats import bootstrap_ci, paired_permutation_test  # noqa: E402


DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_OUT = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15"
)
DEFAULT_MODEL_PILOT = "equal_information_replacement_model_forecast_v1"
DEFAULT_MARKET_PILOT = "equal_information_replacement_polymarket_baseline_v1"


def brier(p: float, y: int) -> float:
    return (float(p) - int(y)) ** 2


def load_rows(db: Path, model_pilot: str, market_pilot: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT
              c.contract_id,
              c.question,
              c.y_known,
              pc.family,
              pc.p_success AS model_p,
              pc.brier AS model_brier,
              pc.parsed_json AS model_parsed_json,
              ebo.p_success AS market_p,
              ebo.brier AS market_brier,
              ebo.raw_json AS market_raw_json,
              ebo.observed_at AS market_observed_at
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            JOIN external_baseline_observations ebo ON ebo.contract_id = pc.contract_id
            WHERE pc.pilot_id = ?
              AND pc.schema_ok = 1
              AND ebo.pilot_id = ?
              AND ebo.schema_ok = 1
              AND ebo.equal_information_flag = 1
              AND c.y_known IN (0, 1)
            ORDER BY c.contract_id, pc.family
            """,
            (model_pilot, market_pilot),
        )
    ]
    con.close()
    return rows


def parse_json(text: Any) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(str(text))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    model_scores = [float(row["model_brier"]) for row in rows]
    market_scores = [float(row["market_brier"]) for row in rows]
    diffs = [m - k for m, k in zip(model_scores, market_scores)]
    ys = [int(row["y_known"]) for row in rows]
    model_ps = [float(row["model_p"]) for row in rows]
    market_ps = [float(row["market_p"]) for row in rows]
    recognition = []
    by_freeze_band: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_contract: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        parsed = parse_json(row.get("model_parsed_json"))
        rec = parsed.get("recognition_self_report")
        if isinstance(rec, (int, float)):
            recognition.append(float(rec))
        market_raw = parse_json(row.get("market_raw_json"))
        request = market_raw.get("request") if isinstance(market_raw.get("request"), dict) else {}
        by_freeze_band[str(request.get("freeze_value_band") or "unknown")].append(row)
        by_family[str(row["family"])].append(row)
        by_contract[str(row["contract_id"])].append(row)
    _, model_lo, model_hi = bootstrap_ci(model_scores, seed=42)
    _, market_lo, market_hi = bootstrap_ci(market_scores, seed=42)
    _, diff_lo, diff_hi = bootstrap_ci(diffs, seed=42)
    family_summary = {}
    for family, group in sorted(by_family.items()):
        family_model = [float(row["model_brier"]) for row in group]
        family_market = [float(row["market_brier"]) for row in group]
        family_summary[family] = {
            "n": len(group),
            "mean_model_brier": mean(family_model),
            "mean_market_brier": mean(family_market),
            "mean_model_minus_market_brier": mean(
                m - k for m, k in zip(family_model, family_market)
            ),
        }
    complete_family_counts = sorted(Counter(len(group) for group in by_contract.values()).items())
    panel_rows = []
    for cid, group in sorted(by_contract.items()):
        y = int(group[0]["y_known"])
        market_p = float(group[0]["market_p"])
        model_p = mean(float(row["model_p"]) for row in group)
        panel_rows.append(
            {
                "contract_id": cid,
                "families": sorted(str(row["family"]) for row in group),
                "y_known": y,
                "model_panel_p": model_p,
                "model_panel_brier": brier(model_p, y),
                "market_p": market_p,
                "market_brier": brier(market_p, y),
            }
        )
    panel_model_scores = [float(row["model_panel_brier"]) for row in panel_rows]
    panel_market_scores = [float(row["market_brier"]) for row in panel_rows]
    contract_ys = [int(row["y_known"]) for row in panel_rows]
    return {
        "n": len(rows),
        "row_n": len(rows),
        "contract_n": len(by_contract),
        "family_n": len(by_family),
        "families": dict(Counter(str(row["family"]) for row in rows)),
        "contract_family_count_distribution": dict(complete_family_counts),
        "outcome_counts": dict(sorted(Counter(str(y) for y in contract_ys).items())),
        "row_outcome_counts": dict(sorted(Counter(str(y) for y in ys).items())),
        "mean_model_brier": mean(model_scores),
        "mean_market_brier": mean(market_scores),
        "mean_constant_0_5_brier": mean(brier(0.5, y) for y in ys),
        "mean_model_minus_market_brier": mean(diffs),
        "bootstrap_ci": {
            "model_brier": {"lo": model_lo, "hi": model_hi},
            "market_brier": {"lo": market_lo, "hi": market_hi},
            "model_minus_market": {"lo": diff_lo, "hi": diff_hi},
        },
        "paired_permutation_model_vs_market": paired_permutation_test(
            model_scores, market_scores, n_perm=10000, seed=42
        ),
        "mean_model_p": mean(model_ps),
        "mean_market_p": mean(market_ps),
        "mean_recognition_self_report": mean(recognition) if recognition else None,
        "family_summary": family_summary,
        "model_panel_mean_p_brier": mean(panel_model_scores) if panel_model_scores else None,
        "model_panel_mean_p_minus_market_brier": (
            mean(m - k for m, k in zip(panel_model_scores, panel_market_scores))
            if panel_model_scores
            else None
        ),
        "paired_permutation_model_panel_vs_market": (
            paired_permutation_test(panel_model_scores, panel_market_scores, n_perm=10000, seed=42)
            if panel_model_scores
            else None
        ),
        "market_brier_lt_0_05": sum(1 for score in panel_market_scores if score < 0.05),
        "model_brier_lt_0_05": sum(1 for score in model_scores if score < 0.05),
        "model_panel_brier_lt_0_05": sum(1 for score in panel_model_scores if score < 0.05),
        "by_freeze_band": {
            band: {
                "n": len(group),
                "model_brier": mean(float(row["model_brier"]) for row in group),
                "market_brier": mean(float(row["market_brier"]) for row in group),
            }
            for band, group in sorted(by_freeze_band.items())
        },
        "panel_rows": panel_rows,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = load_rows(args.db, args.model_pilot, args.market_pilot)
    summary = summarize(rows)
    state = "no_rows"
    if summary.get("contract_n") == 24 and summary.get("family_n", 0) >= 2:
        if (summary.get("model_panel_mean_p_minus_market_brier") or 0) < 0:
            state = "model_panel_beats_market_on_replacement_multifamily_slice"
        else:
            state = "market_beats_model_panel_on_replacement_multifamily_slice"
    elif summary.get("n") == 24:
        family = next(iter(summary.get("families", {"model": 24})), "model")
        if summary["mean_model_minus_market_brier"] < 0:
            state = f"model_beats_market_on_replacement_{family}_slice"
        else:
            state = f"market_beats_model_on_replacement_{family}_slice"
    elif summary.get("n", 0) > 0:
        state = "partial_model_market_join"
    return {
        "schema": "gp245-equal-information-replacement-score-v1",
        "db": str(args.db),
        "model_pilot": args.model_pilot,
        "market_pilot": args.market_pilot,
        "state": state,
        "summary": summary,
        "rows": rows,
        "interpretation": (
            "This is a same-contract model-vs-Polymarket comparison on the replacement "
            "equal-information packet. It is a Polymarket-only market control and does not "
            "establish a broad human/market claim."
        ),
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "equal_information_replacement_score.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = report["summary"]
    lines = [
        "# Equal-Information Replacement Score",
        "",
        f"- State: `{report['state']}`",
        f"- Model pilot: `{report['model_pilot']}`",
        f"- Market pilot: `{report['market_pilot']}`",
        f"- Paired rows: `{summary.get('n')}`",
        f"- Outcome counts: `{summary.get('outcome_counts')}`",
        f"- Model Brier: `{fmt(summary.get('mean_model_brier'))}`",
        f"- Market Brier: `{fmt(summary.get('mean_market_brier'))}`",
        f"- Model minus market Brier: `{fmt(summary.get('mean_model_minus_market_brier'))}`",
        f"- Paired permutation: `{summary.get('paired_permutation_model_vs_market')}`",
        f"- Family summary: `{summary.get('family_summary')}`",
        f"- Model-panel mean-p Brier: `{fmt(summary.get('model_panel_mean_p_brier'))}`",
        f"- Model-panel minus market Brier: `{fmt(summary.get('model_panel_mean_p_minus_market_brier'))}`",
        f"- Model-panel paired permutation: `{summary.get('paired_permutation_model_panel_vs_market')}`",
        f"- Mean recognition self-report: `{fmt(summary.get('mean_recognition_self_report'))}`",
        "",
        report["interpretation"],
    ]
    (out_dir / "equal_information_replacement_score.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--model-pilot", default=DEFAULT_MODEL_PILOT)
    parser.add_argument("--market-pilot", default=DEFAULT_MARKET_PILOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args)
    write_report(report, args.out_dir)
    print(json.dumps({"state": report["state"], "summary": report["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
