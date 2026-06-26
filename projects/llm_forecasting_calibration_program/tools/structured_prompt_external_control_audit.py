#!/usr/bin/env python3
"""External-control audit for the structured-prompt public-corpus packet.

This report uses existing database rows only. It compares the expert-training
prompt against:

1. the same-row low-probability adjustment applied to the bare prompt, and
2. matched market baselines where the structured-prompt contracts have joins.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = PROGRAM / "structured_metacognition_v1/workspace"
DEFAULT_PILOT_ID = "structured_metacognition_public_v1"


def low_probability_adjustment(p: float) -> float:
    return 0.35 * p + 0.65 * 0.10 if p < 0.20 else p


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def sign_p_value(diffs: list[float]) -> float | None:
    nonzero = [diff for diff in diffs if abs(diff) > 1e-12]
    n = len(nonzero)
    if n == 0:
        return None
    wins = sum(1 for diff in nonzero if diff < 0)
    lower = sum(math.comb(n, k) for k in range(0, wins + 1)) / (2**n)
    upper = sum(math.comb(n, k) for k in range(wins, n + 1)) / (2**n)
    return min(1.0, 2 * min(lower, upper))


def summarize(diffs: list[float]) -> dict[str, Any]:
    if not diffs:
        return {"n": 0}
    return {
        "n": len(diffs),
        "mean_delta_brier": sum(diffs) / len(diffs),
        "wins": sum(1 for diff in diffs if diff < 0),
        "losses": sum(1 for diff in diffs if diff > 0),
        "ties": sum(1 for diff in diffs if abs(diff) <= 1e-12),
        "sign_p": sign_p_value(diffs),
    }


def fnum(value: Any, digits: int = 6) -> str:
    if value is None:
        return "NA"
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def load_structured_rows(db: Path, pilot_id: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in con.execute(
                """
                SELECT pc.contract_id, pc.condition, pc.p_success, pc.brier,
                       c.source, c.y_known
                FROM pilot_calls pc
                JOIN contracts c ON c.contract_id = pc.contract_id
                WHERE pc.pilot_id = ?
                  AND pc.schema_ok = 1
                  AND pc.brier IS NOT NULL
                  AND c.y_known IN (0, 1)
                """,
                (pilot_id,),
            )
        ]
    finally:
        con.close()

    by_contract: dict[str, dict[str, Any]] = defaultdict(dict)
    meta: dict[str, Any] = {}
    for row in rows:
        by_contract[str(row["contract_id"])][str(row["condition"])] = row
        meta[str(row["contract_id"])] = {"source": row["source"], "y_known": int(row["y_known"])}
    return by_contract, meta


def load_market_rows(db: Path, contract_ids: list[str]) -> list[dict[str, Any]]:
    if not contract_ids:
        return []
    placeholders = ",".join("?" for _ in contract_ids)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in con.execute(
                f"""
                SELECT b.contract_id, b.platform, b.p_success, b.brier,
                       b.equal_information_flag, b.observed_at,
                       c.source, c.y_known
                FROM v_external_market_baselines b
                JOIN contracts c ON c.contract_id = b.contract_id
                WHERE b.contract_id IN ({placeholders})
                """,
                contract_ids,
            )
        ]
    finally:
        con.close()


def build_report(db: Path, pilot_id: str) -> dict[str, Any]:
    by_contract, meta = load_structured_rows(db, pilot_id)

    adjusted_diffs: list[float] = []
    adjusted_by_source: dict[str, list[float]] = defaultdict(list)
    for contract_id, conditions in by_contract.items():
        expert = conditions.get("expert_training_prompt")
        bare = conditions.get("bare_forecast")
        if not expert or not bare:
            continue
        y = int(meta[contract_id]["y_known"])
        adjusted_bare_brier = brier(low_probability_adjustment(float(bare["p_success"])), y)
        diff = float(expert["brier"]) - adjusted_bare_brier
        adjusted_diffs.append(diff)
        adjusted_by_source[str(meta[contract_id]["source"])].append(diff)

    market_rows = load_market_rows(db, sorted(by_contract))
    market_blocks: dict[str, dict[str, Any]] = {}
    for label, flag in (("all_market_rows", None), ("equal_information_rows", 1), ("non_equal_information_rows", 0)):
        expert_minus_market: list[float] = []
        bare_minus_market: list[float] = []
        adjusted_bare_minus_market: list[float] = []
        by_source: dict[str, list[float]] = defaultdict(list)
        for market in market_rows:
            if flag is not None and int(market["equal_information_flag"]) != flag:
                continue
            contract_id = str(market["contract_id"])
            conditions = by_contract.get(contract_id) or {}
            expert = conditions.get("expert_training_prompt")
            bare = conditions.get("bare_forecast")
            if not expert or not bare:
                continue
            y = int(market["y_known"])
            market_brier = float(market["brier"])
            expert_diff = float(expert["brier"]) - market_brier
            expert_minus_market.append(expert_diff)
            bare_minus_market.append(float(bare["brier"]) - market_brier)
            adjusted_bare_minus_market.append(
                brier(low_probability_adjustment(float(bare["p_success"])), y) - market_brier
            )
            by_source[str(market["source"])].append(expert_diff)
        market_blocks[label] = {
            "expert_minus_market": summarize(expert_minus_market),
            "bare_minus_market": summarize(bare_minus_market),
            "adjusted_bare_minus_market": summarize(adjusted_bare_minus_market),
            "expert_minus_market_by_source": {source: summarize(vals) for source, vals in sorted(by_source.items())},
        }

    equal_summary = market_blocks["equal_information_rows"]["expert_minus_market"]
    adjusted_summary = summarize(adjusted_diffs)
    verdict = (
        "beats_adjusted_bare_market_not_beaten"
        if (adjusted_summary.get("mean_delta_brier") or 0) < 0
        and (adjusted_summary.get("sign_p") or 1) <= 0.05
        and equal_summary.get("n", 0) > 0
        and (equal_summary.get("mean_delta_brier") or 0) > 0
        else "check_report"
    )

    return {
        "schema": "structured-prompt-external-control-audit-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pilot_id": pilot_id,
        "verdict": verdict,
        "low_probability_adjustment": {
            "definition": "if bare_prompt_p < 0.20 then 0.35*bare_prompt_p + 0.65*0.10 else bare_prompt_p",
            "expert_minus_adjusted_bare": adjusted_summary,
            "by_source": {source: summarize(vals) for source, vals in sorted(adjusted_by_source.items())},
            "interpretation": (
                "The expert-training prompt beats the same-row low-probability-adjusted bare prompt; "
                "this is not the five-family mean-panel rule."
            ),
        },
        "market_controls": market_blocks,
        "claim_boundary": (
            "Expert-training survives the same-row calibrated-bare comparison, but matched market rows remain "
            "stronger on the current overlap. This supports a bounded prompt result, not market superiority."
        ),
    }


def build_markdown(report: dict[str, Any]) -> str:
    adj = report["low_probability_adjustment"]["expert_minus_adjusted_bare"]
    equal = report["market_controls"]["equal_information_rows"]["expert_minus_market"]
    all_market = report["market_controls"]["all_market_rows"]["expert_minus_market"]
    lines = [
        "# Structured-Prompt External-Control Audit",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Pilot: `{report['pilot_id']}`",
        f"Verdict: `{report['verdict']}`",
        "",
        "This audit uses existing database rows only.",
        "",
        "## Main Comparisons",
        "",
        "| Comparison | n | Mean delta Brier | Wins | Losses | Ties | Sign p |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            "| Expert-training minus low-probability-adjusted bare prompt | "
            f"{adj.get('n', 0)} | {fnum(adj.get('mean_delta_brier'))} | "
            f"{adj.get('wins', 0)} | {adj.get('losses', 0)} | {adj.get('ties', 0)} | "
            f"{fnum(adj.get('sign_p'), 4)} |"
        ),
        (
            "| Expert-training minus all matched market rows | "
            f"{all_market.get('n', 0)} | {fnum(all_market.get('mean_delta_brier'))} | "
            f"{all_market.get('wins', 0)} | {all_market.get('losses', 0)} | {all_market.get('ties', 0)} | "
            f"{fnum(all_market.get('sign_p'), 4)} |"
        ),
        (
            "| Expert-training minus equal-information market rows | "
            f"{equal.get('n', 0)} | {fnum(equal.get('mean_delta_brier'))} | "
            f"{equal.get('wins', 0)} | {equal.get('losses', 0)} | {equal.get('ties', 0)} | "
            f"{fnum(equal.get('sign_p'), 4)} |"
        ),
        "",
        "## Interpretation",
        "",
        report["claim_boundary"],
        "",
        "The adjusted-bare comparison applies the same low-probability formula to the matched bare Gemini forecast; "
        "it is not the five-family mean-panel rule.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.db, args.pilot_id)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "structured_metacognition_public_v1_external_control_report.json"
    md_path = args.out_dir / "structured_metacognition_public_v1_external_control_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "verdict": report["verdict"],
                "outputs": [str(json_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
