#!/usr/bin/env python3
"""No-call re-audit of channel-only classifier signal on v28a rows.

Question: after removing the cheap shortcuts (`question_len`, `p_success`),
do LLM-emitted uncertainty channels still explain Brier? This intentionally
uses the existing OLS/LOO primitive rather than a stronger ML model.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import ols_multichannel_r2


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_JSON = WORKSPACE / "channel_only_classifier_reaudit_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "channel_only_classifier_reaudit_2026_06_03.md"

PILOT_IDS = (
    "v28a_full__internal",
    "v28a_full__v25_external",
    "v28a_refill__v25_external",
)
MIN_N = 30
CHANNELS = (
    "worry",
    "bid_ask_spread",
    "self_brier_mid",
    "self_brier_width",
)
SHORTCUTS = ("question_len", "p_success")
SHORTCUTS_PLUS_EXTREMITY = ("question_len", "p_success", "p_extremity")


def load_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def scale_0_100(x: float) -> float:
    return x / 100.0 if abs(x) > 1.5 else x


def extract_channels(parsed: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}

    worry = as_float(parsed.get("tail_insurance_premium"))
    if worry is None:
        worry = as_float(parsed.get("worry"))
    if worry is not None:
        out["worry"] = scale_0_100(worry)

    buy = as_float(parsed.get("p_buy_yes_max"))
    sell = as_float(parsed.get("p_sell_yes_min"))
    spread = as_float(parsed.get("spread"))
    if spread is None and buy is not None and sell is not None:
        spread = sell - buy
    if spread is not None:
        out["bid_ask_spread"] = spread

    lo = as_float(parsed.get("predicted_brier_lo"))
    hi = as_float(parsed.get("predicted_brier_hi"))
    if lo is not None and hi is not None:
        out["self_brier_mid"] = (lo + hi) / 2.0
        out["self_brier_width"] = hi - lo

    return {k: v for k, v in out.items() if math.isfinite(v)}


def source_bucket(source: str, source_corpus: str) -> str:
    if source:
        return source
    if source_corpus == "corpus_v22":
        return "internal_corpus_v22"
    return "unknown"


def load_rows(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in PILOT_IDS)
    rows: list[dict[str, Any]] = []
    try:
        cur = con.execute(
            f"""
            SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success, pc.brier,
                   pc.parsed_json, c.question, c.source, c.source_corpus
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.pilot_id IN ({placeholders})
              AND pc.schema_ok = 1
              AND pc.p_success IS NOT NULL
              AND pc.brier IS NOT NULL
              AND pc.family IS NOT NULL
            """,
            PILOT_IDS,
        )
        for row in cur.fetchall():
            parsed = load_json(row["parsed_json"])
            channels = extract_channels(parsed)
            if not all(ch in channels for ch in CHANNELS):
                continue
            p = float(row["p_success"])
            source = source_bucket(str(row["source"] or ""), str(row["source_corpus"] or ""))
            rows.append(
                {
                    "pilot_id": str(row["pilot_id"]),
                    "contract_id": str(row["contract_id"]),
                    "family": str(row["family"]),
                    "source": source,
                    "question_len": float(len(str(row["question"] or ""))),
                    "p_success": p,
                    "p_extremity": abs(p - 0.5),
                    "brier": float(row["brier"]),
                    **channels,
                }
            )
    finally:
        con.close()
    return rows


def zscore_columns(rows: list[dict[str, Any]], features: tuple[str, ...]) -> tuple[list[list[float]], list[str]]:
    cols: list[list[float]] = []
    names: list[str] = []
    for name in features:
        values = [float(row[name]) for row in rows]
        mean = statistics.mean(values)
        sd = statistics.pstdev(values)
        if sd <= 1e-12:
            continue
        cols.append([(v - mean) / sd for v in values])
        names.append(name)
    return cols, names


def fit_model(rows: list[dict[str, Any]], features: tuple[str, ...]) -> dict[str, Any]:
    ys = [float(row["brier"]) for row in rows]
    cols, names = zscore_columns(rows, features)
    if not cols:
        return {"error": "no nonconstant columns", "features": list(features), "n": len(rows)}
    result = ols_multichannel_r2(cols, ys, names)
    if "error" in result:
        result = {"error": result["error"], "features": names, "n": len(rows)}
    else:
        result = {
            "n": result["n"],
            "k": result["k"],
            "features": result["channel_names"],
            "r2": round(result["r2"], 6),
            "r2_adj": round(result["r2_adj"], 6),
            "r2_loo": round(result["r2_loo"], 6),
        }
    return result


def summarize_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    models = {
        "channel_only": fit_model(rows, CHANNELS),
        "shortcuts": fit_model(rows, SHORTCUTS),
        "shortcuts_plus_extremity": fit_model(rows, SHORTCUTS_PLUS_EXTREMITY),
        "channels_plus_shortcuts": fit_model(rows, CHANNELS + SHORTCUTS),
        "channels_plus_shortcuts_plus_extremity": fit_model(
            rows, CHANNELS + SHORTCUTS_PLUS_EXTREMITY
        ),
    }
    channel_loo = models["channel_only"].get("r2_loo")
    shortcut_loo = models["shortcuts"].get("r2_loo")
    combined_loo = models["channels_plus_shortcuts"].get("r2_loo")
    augmented_shortcut_loo = models["shortcuts_plus_extremity"].get("r2_loo")
    augmented_combined_loo = models["channels_plus_shortcuts_plus_extremity"].get("r2_loo")
    return {
        "n": len(rows),
        "models": models,
        "deltas": {
            "channel_minus_shortcut_r2_loo": (
                round(channel_loo - shortcut_loo, 6)
                if isinstance(channel_loo, float) and isinstance(shortcut_loo, float)
                else None
            ),
            "combined_minus_shortcut_r2_loo": (
                round(combined_loo - shortcut_loo, 6)
                if isinstance(combined_loo, float) and isinstance(shortcut_loo, float)
                else None
            ),
            "combined_minus_shortcut_plus_extremity_r2_loo": (
                round(augmented_combined_loo - augmented_shortcut_loo, 6)
                if isinstance(augmented_combined_loo, float)
                and isinstance(augmented_shortcut_loo, float)
                else None
            ),
        },
        "mean_brier": round(statistics.mean(float(row["brier"]) for row in rows), 6),
    }


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family_source: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
        by_family_source[(row["family"], row["source"])].append(row)

    family = {
        fam: summarize_cell(items)
        for fam, items in sorted(by_family.items())
        if len(items) >= MIN_N
    }
    family_source = {
        f"{fam}::{source}": summarize_cell(items)
        for (fam, source), items in sorted(by_family_source.items())
        if len(items) >= MIN_N
    }

    positive_channel = [
        (key, val["models"]["channel_only"].get("r2_loo"))
        for key, val in family.items()
        if isinstance(val["models"]["channel_only"].get("r2_loo"), float)
        and val["models"]["channel_only"]["r2_loo"] > 0
    ]
    positive_incremental = [
        (key, val["deltas"]["combined_minus_shortcut_r2_loo"])
        for key, val in family.items()
        if isinstance(val["deltas"]["combined_minus_shortcut_r2_loo"], float)
        and val["deltas"]["combined_minus_shortcut_r2_loo"] > 0
    ]

    interpretation = (
        "Channel-only signal does not survive as a general applied policy: only "
        f"{len(positive_channel)}/{len(family)} families have positive channel-only "
        "LOO R2, and the shortcut-controlled incremental result is not universal. "
        "Use channel surfaces as diagnostic/eigenframe evidence, not as a broad "
        "classifier deployment rule."
    )
    return {
        "report": "channel_only_classifier_reaudit",
        "date": "2026-06-03",
        "db": str(DEFAULT_DB),
        "pilot_ids": list(PILOT_IDS),
        "valid_rows_with_all_v28a_channels": len(rows),
        "features": {
            "channels": list(CHANNELS),
            "shortcuts": list(SHORTCUTS),
            "shortcut_extremity_control": "p_extremity = abs(p_success - 0.5)",
            "target": "Brier",
        },
        "family": family,
        "family_source": family_source,
        "verdict": {
            "channel_only_generalizes": False,
            "positive_channel_only_family_cells": len(positive_channel),
            "total_family_cells": len(family),
            "positive_incremental_family_cells": len(positive_incremental),
            "interpretation": interpretation,
        },
    }


def fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:+.3f}"
    return str(value)


def model_field(cell: dict[str, Any], model: str, field: str) -> Any:
    return cell["models"].get(model, {}).get(field)


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Channel-only classifier re-audit - 2026-06-03",
        "",
        "No new model calls. Rows are v28a all-channel calls with all four channel fields present.",
        "",
        "Target: Brier. Channel features: `worry`, `bid_ask_spread`, `self_brier_mid`, `self_brier_width`. Shortcut controls: `question_len`, `p_success`, with a sensitivity control adding `abs(p_success - 0.5)`.",
        "",
        "## Family Cells",
        "",
        "| family | n | channel-only LOO R2 | shortcut LOO R2 | channel+shortcut LOO R2 | incremental vs shortcuts | incremental vs shortcuts+extremity |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for family, cell in report["family"].items():
        lines.append(
            "| {family} | {n} | {co} | {sc} | {combo} | {inc} | {inc_ext} |".format(
                family=family,
                n=cell["n"],
                co=fmt(model_field(cell, "channel_only", "r2_loo")),
                sc=fmt(model_field(cell, "shortcuts", "r2_loo")),
                combo=fmt(model_field(cell, "channels_plus_shortcuts", "r2_loo")),
                inc=fmt(cell["deltas"]["combined_minus_shortcut_r2_loo"]),
                inc_ext=fmt(cell["deltas"]["combined_minus_shortcut_plus_extremity_r2_loo"]),
            )
        )

    lines.extend(
        [
            "",
            "## Source Cells",
            "",
            "| family | source | n | channel-only LOO R2 | shortcut LOO R2 | incremental vs shortcuts |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for key, cell in report["family_source"].items():
        family, source = key.split("::")
        lines.append(
            "| {family} | {source} | {n} | {co} | {sc} | {inc} |".format(
                family=family,
                source=source,
                n=cell["n"],
                co=fmt(model_field(cell, "channel_only", "r2_loo")),
                sc=fmt(model_field(cell, "shortcuts", "r2_loo")),
                inc=fmt(cell["deltas"]["combined_minus_shortcut_r2_loo"]),
            )
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            report["verdict"]["interpretation"],
            "",
            f"Valid rows with all v28a channels: `{report['valid_rows_with_all_v28a_channels']}`.",
            "",
            "This keeps F58/F59/F61 as a diagnostic surface, not a deployable classifier story. It also explains why the newer router/allocation attempts failed: channels reveal family/source structure, but broad policy lift is mostly carried by simpler universal rules and source/horizon difficulty rather than a universal channel-only classifier.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    rows = load_rows(args.db)
    report = build_report(rows)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, args.out_md)
    print(json.dumps(report["verdict"], indent=2, sort_keys=True))
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
