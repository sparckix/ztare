#!/usr/bin/env python3
"""Trace headline GP-245 numbers to their current score sources.

No network, no model calls, no database mutation. The output is a compact
reader-facing check that the manuscript's main quantitative statements still
match the SQLite evidence database and the stored score reports.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
PAPER_DIR = REPO / "papers/llm-forecast-calibration-cross-corpus"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/numeric_claim_trace_2026_06_16"

MAIN_TEX = PAPER_DIR / "main.tex"
STAGE_B_SCORE = PROGRAM / "cutoff_validity_v1/workspace/cutoff_stage_b_score_report.json"
POLYMARKET_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/equal_information_replacement_score_2026_06_15"
    / "equal_information_replacement_score.json"
)
MANIFOLD_SCORE = (
    PROGRAM
    / "cutoff_validity_v1/workspace/non_polymarket_equal_information_export_packet_2026_06_15"
    / "manifold_history_score_2026_06_15/non_polymarket_equal_information_score.json"
)
MANIFOLD_FREEZE0_SCORE = (
    PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze0_2026_06_20"
    / "non_polymarket_equal_information_score.json"
)
MANIFOLD_FREEZE1_SCORE = (
    PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze1_2026_06_20"
    / "non_polymarket_equal_information_score.json"
)
MANIFOLD_FREEZE2_SCORE = (
    PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze2_2026_06_20"
    / "non_polymarket_equal_information_score.json"
)
MANIFOLD_FREEZE7_SCORE = (
    PROGRAM
    / "paper_alignment_v1/workspace/non_polymarket_equal_information_score_freeze7_2026_06_20"
    / "non_polymarket_equal_information_score.json"
)
CALIBRATION_SCORE = (
    PROGRAM
    / "forecaster_skill_calibration_v1/workspace/f100_calibrator_audit_2026_06_04_policy_scoreable.json"
)
CALIBRATION_STRESS = (
    PROGRAM / "forecaster_skill_calibration_v1/workspace/f100_source_currency_audit_2026_06_03.json"
)
PAIRWISE_SCORE = (
    PROGRAM / "forecaster_skill_calibration_v1/workspace/f47_source_balanced_consumer_score_2026_06_03.json"
)
FRED_VINTAGE_SCORE = (
    PROGRAM / "cutoff_validity_v1/workspace/fred_vintage_bulk_rescore_2026_06_04/fred_vintage_rescore.json"
)
STRUCTURED_PROMPT_SCORE = (
    PROGRAM / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_score_report.json"
)
STRUCTURED_PROMPT_EXTERNAL_CONTROL = (
    PROGRAM / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_external_control_report.json"
)
STRUCTURED_PROMPT_CLAUDE_SCORE = (
    PROGRAM
    / "structured_metacognition_v1/workspace/structured_metacognition_public_v1_claude_replication_score_report.json"
)


@dataclass
class NumericCheck:
    name: str
    paper_label: str
    source_label: str
    observed: float | int | str | None
    expected: float | int | str
    tolerance: float
    source_path: str
    manuscript_pattern: str
    status: str
    detail: str


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def scalar(cur: sqlite3.Cursor, sql: str) -> Any:
    row = cur.execute(sql).fetchone()
    return row[0] if row else None


def db_counts(db: Path) -> dict[str, int]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    try:
        return {
            "source_currency_rows": int(scalar(cur, "SELECT COUNT(*) FROM source_currency_gate_rows") or 0),
            "source_currency_conflicts": int(
                scalar(cur, "SELECT COUNT(*) FROM v_source_currency_gate_conflicts") or 0
            ),
            "label_time_rows": int(scalar(cur, "SELECT COUNT(*) FROM dataset_label_time_gate_rows") or 0),
            "external_market_rows": int(scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines") or 0),
            "equal_information_rows": int(
                scalar(cur, "SELECT COUNT(*) FROM v_external_market_baselines WHERE equal_information_flag = 1")
                or 0
            ),
        }
    finally:
        con.close()


def fmt(value: float | int | str | None) -> str:
    if value is None:
        return "missing"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def status_for(observed: float | int | str | None, expected: float | int | str, tolerance: float) -> tuple[str, str]:
    if observed is None:
        return "fail", "source value missing"
    if isinstance(expected, (float, int)) and isinstance(observed, (float, int)):
        delta = abs(float(observed) - float(expected))
        if delta <= tolerance:
            return "pass", f"delta {delta:.8g} within tolerance {tolerance:g}"
        return "fail", f"delta {delta:.8g} exceeds tolerance {tolerance:g}"
    if str(observed) == str(expected):
        return "pass", "exact match"
    return "fail", "string mismatch"


def make_check(
    *,
    name: str,
    paper_label: str,
    source_label: str,
    observed: float | int | str | None,
    expected: float | int | str,
    tolerance: float,
    source_path: Path,
    manuscript_pattern: str,
    main_tex: str,
) -> NumericCheck:
    source_status, source_detail = status_for(observed, expected, tolerance)
    manuscript_ok = bool(re.search(manuscript_pattern, main_tex))
    if source_status == "pass" and manuscript_ok:
        status = "pass"
        detail = source_detail
    elif source_status != "pass":
        status = "fail"
        detail = source_detail
    else:
        status = "fail"
        detail = f"source matches, but manuscript pattern not found: {manuscript_pattern}"
    return NumericCheck(
        name=name,
        paper_label=paper_label,
        source_label=source_label,
        observed=observed,
        expected=expected,
        tolerance=tolerance,
        source_path=rel(source_path),
        manuscript_pattern=manuscript_pattern,
        status=status,
        detail=detail,
    )


def build_report(db: Path) -> dict[str, Any]:
    main_tex = MAIN_TEX.read_text(encoding="utf-8")
    counts = db_counts(db)
    stage_b = read_json(STAGE_B_SCORE)
    polymarket = read_json(POLYMARKET_SCORE)
    manifold = read_json(MANIFOLD_SCORE)
    manifold_freeze0 = read_json(MANIFOLD_FREEZE0_SCORE)
    manifold_freeze1 = read_json(MANIFOLD_FREEZE1_SCORE)
    manifold_freeze2 = read_json(MANIFOLD_FREEZE2_SCORE)
    manifold_freeze7 = read_json(MANIFOLD_FREEZE7_SCORE)
    calibration = read_json(CALIBRATION_SCORE)
    stress = read_json(CALIBRATION_STRESS)
    pairwise = read_json(PAIRWISE_SCORE)
    fred_vintage = read_json(FRED_VINTAGE_SCORE)
    structured_prompt = read_json(STRUCTURED_PROMPT_SCORE)
    structured_prompt_external = read_json(STRUCTURED_PROMPT_EXTERNAL_CONTROL)
    structured_prompt_claude = read_json(STRUCTURED_PROMPT_CLAUDE_SCORE)

    checks: list[NumericCheck] = []
    add = checks.append
    add(
        make_check(
            name="source_currency_contracts",
            paper_label="Manifold source-currency panel contracts",
            source_label="Source-currency score report",
            observed=nested(stage_b, "panel_contracts"),
            expected=80,
            tolerance=0.0,
            source_path=STAGE_B_SCORE,
            manuscript_pattern=r"80 contracts",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="source_currency_calls",
            paper_label="Manifold source-currency panel calls",
            source_label="Source-currency score report",
            observed=nested(stage_b, "call_coverage", "calls_in_db"),
            expected=240,
            tolerance=0.0,
            source_path=STAGE_B_SCORE,
            manuscript_pattern=r"240 tool-free model calls|240 tool-free calls",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="source_currency_aggregate_delta",
            paper_label="Post-minus-pre Brier, aggregate",
            source_label="Source-currency score report",
            observed=nested(stage_b, "aggregate_delta", "post_minus_pre"),
            expected=0.191098,
            tolerance=0.0000005,
            source_path=STAGE_B_SCORE,
            manuscript_pattern=r"0\.191098",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="source_currency_paired_delta",
            paper_label="Post-minus-pre Brier, paired strata",
            source_label="Source-currency score report",
            observed=nested(stage_b, "paired_stratum_delta", "paired_permutation", "observed_delta"),
            expected=0.2155,
            tolerance=0.00005,
            source_path=STAGE_B_SCORE,
            manuscript_pattern=r"0\.2155",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="source_currency_p_value",
            paper_label="Source-currency paired permutation p-value",
            source_label="Source-currency score report",
            observed=nested(stage_b, "paired_stratum_delta", "paired_permutation", "p_value"),
            expected=0.0004,
            tolerance=0.0000005,
            source_path=STAGE_B_SCORE,
            manuscript_pattern=r"0\.0004",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="external_market_rows",
            paper_label="External market baseline rows",
            source_label="SQLite evidence database",
            observed=counts["external_market_rows"],
            expected=170,
            tolerance=0.0,
            source_path=db,
            manuscript_pattern=r"170 external market baseline rows|170 typed external market baseline rows",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="equal_information_rows",
            paper_label="Same-information market rows",
            source_label="SQLite evidence database",
            observed=counts["equal_information_rows"],
            expected=119,
            tolerance=0.0,
            source_path=db,
            manuscript_pattern=r"119 equal-information market rows|119 ingested equal-information market rows",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="label_time_rows",
            paper_label="Label-time screen rows",
            source_label="SQLite evidence database",
            observed=counts["label_time_rows"],
            expected=165,
            tolerance=0.0,
            source_path=db,
            manuscript_pattern=r"165 dataset-source rows|165 label-time rows",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="source_currency_conflicts",
            paper_label="Stored/computed source-currency conflicts",
            source_label="SQLite evidence database",
            observed=counts["source_currency_conflicts"],
            expected=39,
            tolerance=0.0,
            source_path=db,
            manuscript_pattern=r"39/240|39 / 240",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="polymarket_contracts",
            paper_label="Polymarket same-information contracts",
            source_label="Polymarket equal-information score report",
            observed=nested(polymarket, "summary", "contract_n"),
            expected=24,
            tolerance=0.0,
            source_path=POLYMARKET_SCORE,
            manuscript_pattern=r"24 Polymarket contracts|24-contract Polymarket|Polymarket, 24 contracts",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="polymarket_panel_brier",
            paper_label="Polymarket slice model-panel Brier",
            source_label="Polymarket equal-information score report",
            observed=nested(polymarket, "summary", "model_panel_mean_p_brier"),
            expected=0.267758,
            tolerance=0.0000005,
            source_path=POLYMARKET_SCORE,
            manuscript_pattern=r"0\.267758",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="polymarket_market_brier",
            paper_label="Polymarket market Brier",
            source_label="Polymarket equal-information score report",
            observed=nested(polymarket, "summary", "mean_market_brier"),
            expected=0.072964,
            tolerance=0.0000005,
            source_path=POLYMARKET_SCORE,
            manuscript_pattern=r"0\.072964",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="polymarket_panel_p_value",
            paper_label="Polymarket panel-vs-market p-value",
            source_label="Polymarket equal-information score report",
            observed=nested(polymarket, "summary", "paired_permutation_model_panel_vs_market", "p_value"),
            expected=0.0068,
            tolerance=0.0000005,
            source_path=POLYMARKET_SCORE,
            manuscript_pattern=r"0\.0068",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_contracts",
            paper_label="Manifold same-information contracts",
            source_label="Manifold equal-information score report",
            observed=nested(manifold, "selected_candidate", "contracts"),
            expected=24,
            tolerance=0.0,
            source_path=MANIFOLD_SCORE,
            manuscript_pattern=r"24-contract Manifold|Manifold, 24 contracts",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_panel_brier",
            paper_label="Manifold slice model-panel Brier",
            source_label="Manifold equal-information score report",
            observed=nested(manifold, "selected_candidate", "model_panel_mean_p_brier"),
            expected=0.198723,
            tolerance=0.0000005,
            source_path=MANIFOLD_SCORE,
            manuscript_pattern=r"0\.198723",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_market_brier",
            paper_label="Manifold market Brier",
            source_label="Manifold equal-information score report",
            observed=nested(manifold, "selected_candidate", "mean_market_brier_on_common_contracts"),
            expected=0.160977,
            tolerance=0.0000005,
            source_path=MANIFOLD_SCORE,
            manuscript_pattern=r"0\.160977",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_panel_p_value",
            paper_label="Manifold panel-vs-market p-value",
            source_label="Manifold equal-information score report",
            observed=nested(manifold, "selected_candidate", "paired_permutation_model_panel_vs_market", "p_value"),
            expected=0.5431,
            tolerance=0.0000005,
            source_path=MANIFOLD_SCORE,
            manuscript_pattern=r"0\.5431",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze0_contracts",
            paper_label="Manifold same-day freeze expansion contracts",
            source_label="Manifold same-day freeze expansion score report",
            observed=nested(manifold_freeze0, "selected_candidate", "contracts"),
            expected=32,
            tolerance=0.0,
            source_path=MANIFOLD_FREEZE0_SCORE,
            manuscript_pattern=r"32-contract Manifold|Manifold same-day freeze expansion",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze0_panel_brier",
            paper_label="Manifold same-day freeze expansion model-panel Brier",
            source_label="Manifold same-day freeze expansion score report",
            observed=nested(manifold_freeze0, "selected_candidate", "model_panel_mean_p_brier"),
            expected=0.214665,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE0_SCORE,
            manuscript_pattern=r"0\.214665",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze0_market_brier",
            paper_label="Manifold same-day freeze expansion market Brier",
            source_label="Manifold same-day freeze expansion score report",
            observed=nested(manifold_freeze0, "selected_candidate", "mean_market_brier_on_common_contracts"),
            expected=0.135951,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE0_SCORE,
            manuscript_pattern=r"0\.135951",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze0_panel_minus_market",
            paper_label="Manifold same-day freeze expansion panel-minus-market Brier",
            source_label="Manifold same-day freeze expansion score report",
            observed=nested(manifold_freeze0, "selected_candidate", "model_panel_minus_market_brier"),
            expected=0.078714,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE0_SCORE,
            manuscript_pattern=r"0\.078714",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze0_panel_p_value",
            paper_label="Manifold same-day freeze expansion panel-vs-market p-value",
            source_label="Manifold same-day freeze expansion score report",
            observed=nested(
                manifold_freeze0,
                "selected_candidate",
                "paired_permutation_model_panel_vs_market",
                "p_value",
            ),
            expected=0.0048,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE0_SCORE,
            manuscript_pattern=r"0\.0048",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze1_contracts",
            paper_label="Manifold one-day horizon sensitivity contracts",
            source_label="Manifold one-day horizon sensitivity score report",
            observed=nested(manifold_freeze1, "selected_candidate", "contracts"),
            expected=18,
            tolerance=0.0,
            source_path=MANIFOLD_FREEZE1_SCORE,
            manuscript_pattern=r"18/18 one-day|18 one-day",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze1_panel_brier",
            paper_label="Manifold one-day horizon sensitivity model-panel Brier",
            source_label="Manifold one-day horizon sensitivity score report",
            observed=nested(manifold_freeze1, "selected_candidate", "model_panel_mean_p_brier"),
            expected=0.202270,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE1_SCORE,
            manuscript_pattern=r"0\.202270",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze1_market_brier",
            paper_label="Manifold one-day horizon sensitivity market Brier",
            source_label="Manifold one-day horizon sensitivity score report",
            observed=nested(manifold_freeze1, "selected_candidate", "mean_market_brier_on_common_contracts"),
            expected=0.099699,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE1_SCORE,
            manuscript_pattern=r"0\.099699",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze1_panel_p_value",
            paper_label="Manifold one-day horizon sensitivity panel-vs-market p-value",
            source_label="Manifold one-day horizon sensitivity score report",
            observed=nested(
                manifold_freeze1,
                "selected_candidate",
                "paired_permutation_model_panel_vs_market",
                "p_value",
            ),
            expected=0.0122,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE1_SCORE,
            manuscript_pattern=r"0\.0122",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze2_contracts",
            paper_label="Manifold two-day horizon sensitivity contracts",
            source_label="Manifold two-day horizon sensitivity score report",
            observed=nested(manifold_freeze2, "selected_candidate", "contracts"),
            expected=10,
            tolerance=0.0,
            source_path=MANIFOLD_FREEZE2_SCORE,
            manuscript_pattern=r"10/10 two-day|10 two-day",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze2_panel_brier",
            paper_label="Manifold two-day horizon sensitivity model-panel Brier",
            source_label="Manifold two-day horizon sensitivity score report",
            observed=nested(manifold_freeze2, "selected_candidate", "model_panel_mean_p_brier"),
            expected=0.231846,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE2_SCORE,
            manuscript_pattern=r"0\.231846",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze2_market_brier",
            paper_label="Manifold two-day horizon sensitivity market Brier",
            source_label="Manifold two-day horizon sensitivity score report",
            observed=nested(manifold_freeze2, "selected_candidate", "mean_market_brier_on_common_contracts"),
            expected=0.109365,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE2_SCORE,
            manuscript_pattern=r"0\.109365",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze2_panel_p_value",
            paper_label="Manifold two-day horizon sensitivity panel-vs-market p-value",
            source_label="Manifold two-day horizon sensitivity score report",
            observed=nested(
                manifold_freeze2,
                "selected_candidate",
                "paired_permutation_model_panel_vs_market",
                "p_value",
            ),
            expected=0.0152,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE2_SCORE,
            manuscript_pattern=r"0\.0152",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze7_contracts",
            paper_label="Manifold seven-day horizon sensitivity contracts",
            source_label="Manifold seven-day horizon sensitivity score report",
            observed=nested(manifold_freeze7, "selected_candidate", "contracts"),
            expected=7,
            tolerance=0.0,
            source_path=MANIFOLD_FREEZE7_SCORE,
            manuscript_pattern=r"7/7 seven-day|7 seven-day",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze7_panel_brier",
            paper_label="Manifold seven-day horizon sensitivity model-panel Brier",
            source_label="Manifold seven-day horizon sensitivity score report",
            observed=nested(manifold_freeze7, "selected_candidate", "model_panel_mean_p_brier"),
            expected=0.228263,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE7_SCORE,
            manuscript_pattern=r"0\.228263",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze7_market_brier",
            paper_label="Manifold seven-day horizon sensitivity market Brier",
            source_label="Manifold seven-day horizon sensitivity score report",
            observed=nested(manifold_freeze7, "selected_candidate", "mean_market_brier_on_common_contracts"),
            expected=0.193649,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE7_SCORE,
            manuscript_pattern=r"0\.193649",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="manifold_freeze7_panel_p_value",
            paper_label="Manifold seven-day horizon sensitivity panel-vs-market p-value",
            source_label="Manifold seven-day horizon sensitivity score report",
            observed=nested(
                manifold_freeze7,
                "selected_candidate",
                "paired_permutation_model_panel_vs_market",
                "p_value",
            ),
            expected=0.5045,
            tolerance=0.0000005,
            source_path=MANIFOLD_FREEZE7_SCORE,
            manuscript_pattern=r"0\.5045",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="calibration_panel_count",
            paper_label="Source-documented calibration panels",
            source_label="Source-documented calibration score report",
            observed=nested(calibration, "n_panels"),
            expected=132,
            tolerance=0.0,
            source_path=CALIBRATION_SCORE,
            manuscript_pattern=r"132 panels",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="calibration_raw_minus_adjusted",
            paper_label="Raw mean-panel Brier disadvantage",
            source_label="Source-documented calibration score report",
            observed=nested(calibration, "policies", "raw_mean_panel", "delta_vs_confident_no"),
            expected=0.029598,
            tolerance=0.0000005,
            source_path=CALIBRATION_SCORE,
            manuscript_pattern=r"0\.029598",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="calibration_p_value",
            paper_label="Low-probability calibration p-value",
            source_label="Source-documented calibration score report",
            observed=nested(calibration, "policies", "raw_mean_panel", "paired_vs_confident_no", "p_value"),
            expected=0.0062,
            tolerance=0.0000005,
            source_path=CALIBRATION_SCORE,
            manuscript_pattern=r"0\.0062",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="calibration_forward_delta",
            paper_label="Forward-looking source-currency calibration delta",
            source_label="Source-currency calibration stress score report",
            observed=nested(stress, "by_cutoff_relation", "post_cutoff", "delta_f100_minus_raw"),
            expected=-0.025326,
            tolerance=0.0000005,
            source_path=CALIBRATION_STRESS,
            manuscript_pattern=r"-0\.025326",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="calibration_source_visible_delta",
            paper_label="Source-visible source-currency calibration delta",
            source_label="Source-currency calibration stress score report",
            observed=nested(stress, "by_cutoff_relation", "pre_cutoff", "delta_f100_minus_raw"),
            expected=0.035016,
            tolerance=0.0000005,
            source_path=CALIBRATION_STRESS,
            manuscript_pattern=r"0\.035016",
            main_tex=main_tex,
        )
    )
    collapsed = nested(pairwise, "summaries", "collapsed_by_unique_pair") or {}
    add(
        make_check(
            name="pairwise_unique_pairs",
            paper_label="Pairwise ranking unique non-tie pairs",
            source_label="Pairwise ranking score report",
            observed=collapsed.get("non_tie_n"),
            expected=24,
            tolerance=0.0,
            source_path=PAIRWISE_SCORE,
            manuscript_pattern=r"24 unique non-tie pairs",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="pairwise_accuracy",
            paper_label="Pairwise ranking accuracy",
            source_label="Pairwise ranking score report",
            observed=collapsed.get("contrastive_accuracy"),
            expected=0.75,
            tolerance=0.0000005,
            source_path=PAIRWISE_SCORE,
            manuscript_pattern=r"0\.750",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="pairwise_utility",
            paper_label="Pairwise ranking utility",
            source_label="Pairwise ranking score report",
            observed=collapsed.get("contrastive_mean_utility"),
            expected=0.583333,
            tolerance=0.0000005,
            source_path=PAIRWISE_SCORE,
            manuscript_pattern=r"0\.583",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="pairwise_random_p_value",
            paper_label="Pairwise ranking p-value versus random",
            source_label="Pairwise ranking score report",
            observed=nested(collapsed, "paired_vs_random", "p_value"),
            expected=0.0044,
            tolerance=0.0000005,
            source_path=PAIRWISE_SCORE,
            manuscript_pattern=r"0\.0044",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="fred_vintage_rows",
            paper_label="FRED vintage-scoreable official-data rows",
            source_label="FRED vintage rescore",
            observed=nested(fred_vintage, "audit_summary", "vintage_scoreable_rows"),
            expected=98,
            tolerance=0.0,
            source_path=FRED_VINTAGE_SCORE,
            manuscript_pattern=r"98 vintage-scoreable official-data rows|15 of 98",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="fred_binary_label_changes",
            paper_label="FRED binary labels changed under vintage repair",
            source_label="FRED vintage rescore",
            observed=nested(fred_vintage, "audit_summary", "y_two_point_changed"),
            expected=15,
            tolerance=0.0,
            source_path=FRED_VINTAGE_SCORE,
            manuscript_pattern=r"15 of 98 binary labels changed",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="fred_blinded_control_calls",
            paper_label="FRED blinded-control scored calls",
            source_label="FRED vintage rescore",
            observed=nested(fred_vintage, "control", "scored_rows"),
            expected=192,
            tolerance=0.0,
            source_path=FRED_VINTAGE_SCORE,
            manuscript_pattern=r"192 blinded-control calls",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="fred_current_label_delta",
            paper_label="FRED current-label apparent post-minus-pre penalty",
            source_label="FRED vintage rescore",
            observed=nested(fred_vintage, "control", "paired_current", "mean_post_minus_pre_brier"),
            expected=0.02471901041666667,
            tolerance=0.0000005,
            source_path=FRED_VINTAGE_SCORE,
            manuscript_pattern=r"0\.024719",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="fred_vintage_label_delta",
            paper_label="FRED vintage-label post-minus-pre delta",
            source_label="FRED vintage rescore",
            observed=nested(fred_vintage, "control", "paired_vintage", "mean_post_minus_pre_brier"),
            expected=-0.0029893229166666735,
            tolerance=0.0000005,
            source_path=FRED_VINTAGE_SCORE,
            manuscript_pattern=r"-0\.002989",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_gemini_scored_rows",
            paper_label="Gemini structured-prompt scored calls",
            source_label="Gemini structured-prompt score report",
            observed=nested(structured_prompt, "input_rows"),
            expected=600,
            tolerance=0.0,
            source_path=STRUCTURED_PROMPT_SCORE,
            manuscript_pattern=r"600-call Gemini|600/600 scored Gemini calls",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_gemini_contract_blocks",
            paper_label="Gemini structured-prompt contract blocks",
            source_label="Gemini structured-prompt score report",
            observed=nested(structured_prompt, "coverage", "complete_contract_family_blocks"),
            expected=120,
            tolerance=0.0,
            source_path=STRUCTURED_PROMPT_SCORE,
            manuscript_pattern=r"120 contracts",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_bare_delta",
            paper_label="Expert-training minus bare prompt Brier delta",
            source_label="Gemini structured-prompt score report",
            observed=nested(structured_prompt, "overall", "expert_training_prompt_vs_bare_forecast", "mean_delta_brier"),
            expected=-0.06056856883333333,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_SCORE,
            manuscript_pattern=r"-0\.060569",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_bare_sign_p",
            paper_label="Expert-training minus bare prompt sign p-value",
            source_label="Gemini structured-prompt score report",
            observed=nested(structured_prompt, "overall", "expert_training_prompt_vs_bare_forecast", "sign_p"),
            expected=0.0005090902243497337,
            tolerance=0.00005,
            source_path=STRUCTURED_PROMPT_SCORE,
            manuscript_pattern=r"0\.0005",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_placebo_delta",
            paper_label="Expert-training minus length-matched placebo Brier delta",
            source_label="Gemini structured-prompt score report",
            observed=nested(
                structured_prompt,
                "overall",
                "expert_training_prompt_vs_length_matched_placebo",
                "mean_delta_brier",
            ),
            expected=-0.024286527166675002,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_SCORE,
            manuscript_pattern=r"-0\.024287",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_placebo_sign_p",
            paper_label="Expert-training minus length-matched placebo sign p-value",
            source_label="Gemini structured-prompt score report",
            observed=nested(structured_prompt, "overall", "expert_training_prompt_vs_length_matched_placebo", "sign_p"),
            expected=0.006695018134217244,
            tolerance=0.00005,
            source_path=STRUCTURED_PROMPT_SCORE,
            manuscript_pattern=r"0\.0067",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_adjusted_bare_delta",
            paper_label="Expert-training minus same-row calibrated-bare Brier delta",
            source_label="Structured-prompt external-control audit",
            observed=nested(
                structured_prompt_external,
                "low_probability_adjustment",
                "expert_minus_adjusted_bare",
                "mean_delta_brier",
            ),
            expected=-0.05250321261395833,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_EXTERNAL_CONTROL,
            manuscript_pattern=r"-0\.052503",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_adjusted_bare_sign_p",
            paper_label="Expert-training minus same-row calibrated-bare sign p-value",
            source_label="Structured-prompt external-control audit",
            observed=nested(
                structured_prompt_external,
                "low_probability_adjustment",
                "expert_minus_adjusted_bare",
                "sign_p",
            ),
            expected=0.002151553087925025,
            tolerance=0.00005,
            source_path=STRUCTURED_PROMPT_EXTERNAL_CONTROL,
            manuscript_pattern=r"0\.0022",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_all_market_delta",
            paper_label="Expert-training minus all matched market rows Brier delta",
            source_label="Structured-prompt external-control audit",
            observed=nested(
                structured_prompt_external,
                "market_controls",
                "all_market_rows",
                "expert_minus_market",
                "mean_delta_brier",
            ),
            expected=0.15094979905723982,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_EXTERNAL_CONTROL,
            manuscript_pattern=r"0\.150950",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_expert_vs_equal_information_market_delta",
            paper_label="Expert-training minus same-information market rows Brier delta",
            source_label="Structured-prompt external-control audit",
            observed=nested(
                structured_prompt_external,
                "market_controls",
                "equal_information_rows",
                "expert_minus_market",
                "mean_delta_brier",
            ),
            expected=0.09313004109801755,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_EXTERNAL_CONTROL,
            manuscript_pattern=r"0\.093130",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_claude_scored_rows",
            paper_label="Claude partial structured-prompt scored calls",
            source_label="Claude structured-prompt partial score report",
            observed=nested(structured_prompt_claude, "input_rows"),
            expected=591,
            tolerance=0.0,
            source_path=STRUCTURED_PROMPT_CLAUDE_SCORE,
            manuscript_pattern=r"591/600 calls|591/600-call|591-call",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_claude_expert_vs_bare_delta",
            paper_label="Claude expert-training minus bare prompt Brier delta",
            source_label="Claude structured-prompt partial score report",
            observed=nested(structured_prompt_claude, "overall", "expert_training_prompt_vs_bare_forecast", "mean_delta_brier"),
            expected=-0.0036384866086956492,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_CLAUDE_SCORE,
            manuscript_pattern=r"0\.003638",
            main_tex=main_tex,
        )
    )
    add(
        make_check(
            name="structured_prompt_claude_expert_vs_placebo_delta",
            paper_label="Claude expert-training minus length-matched placebo Brier delta",
            source_label="Claude structured-prompt partial score report",
            observed=nested(
                structured_prompt_claude,
                "overall",
                "expert_training_prompt_vs_length_matched_placebo",
                "mean_delta_brier",
            ),
            expected=-0.004175008571428565,
            tolerance=0.0000005,
            source_path=STRUCTURED_PROMPT_CLAUDE_SCORE,
            manuscript_pattern=r"0\.004175",
            main_tex=main_tex,
        )
    )

    failed = [item for item in checks if item.status != "pass"]
    return {
        "schema": "gp245-numeric-claim-trace-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "pass" if not failed else "fail",
        "checks": [item.__dict__ for item in checks],
    }


def write_csv(path: Path, checks: list[dict[str, Any]]) -> None:
    columns = [
        "name",
        "status",
        "paper_label",
        "expected",
        "observed",
        "tolerance",
        "source_label",
        "source_path",
        "detail",
        "manuscript_pattern",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(checks)


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GP-245 Numeric Claim Trace",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
        "| Paper number | Expected | Observed | Status | Source |",
        "|---|---:|---:|---|---|",
    ]
    for item in report["checks"]:
        lines.append(
            "| {label} | `{expected}` | `{observed}` | {status} | {source} |".format(
                label=item["paper_label"],
                expected=fmt(item["expected"]),
                observed=fmt(item["observed"]),
                status=item["status"],
                source=item["source_label"],
            )
        )
    lines.extend(
        [
            "",
            "This report checks the manuscript's headline quantitative statements against the current database and stored score reports. It does not add new model calls or change any scores.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.db)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "numeric_claim_trace.json"
    csv_path = args.out_dir / "numeric_claim_trace.csv"
    md_path = args.out_dir / "numeric_claim_trace.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(csv_path, report["checks"])
    md_path.write_text(build_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "out_dir": str(args.out_dir),
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
