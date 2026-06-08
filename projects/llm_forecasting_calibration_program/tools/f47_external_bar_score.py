#!/usr/bin/env python3
"""Score F47 translated probabilities against the acquired external bars.

No model calls. No DB mutation.

This intentionally reports a tiny joined slice. It answers whether the current
external-bar evidence is enough to promote F47. It does not try to turn a
small partly-acquired slice into a broad market/human claim.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test

from f47_cross_packet_transfer_audit import (
    DEFAULT_SOURCE_CALLS,
    DEFAULT_SOURCE_KEY,
    DEFAULT_TOURNAMENT_CALLS,
    DEFAULT_TOURNAMENT_KEY,
    brier,
    confident_no,
    contract_rows,
    load_edges,
)
from f47_translation_tournament_score import fit_logistic, sigmoid


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_MANIFOLD_1D = (
    WORKSPACE
    / "f47_external_bar_manifold_acquisition_1d_2026_06_03/cutoff_stage_c_manifold_probability_acquisition.jsonl"
)
DEFAULT_POLYMARKET = (
    WORKSPACE
    / "f47_external_bar_polymarket_acquisition_2026_06_03/f47_polymarket_external_bar_acquisition_rows.jsonl"
)
DEFAULT_OUT_JSON = WORKSPACE / "f47_external_bar_score_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_external_bar_score_2026_06_03.md"
MARKET_PILOT = "market_baseline_stage_c_v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def load_existing_market(db: Path) -> dict[str, dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT pc.contract_id, pc.p_success, pc.brier, pc.raw_json, c.y_known
        FROM pilot_calls pc
        JOIN contracts c USING(contract_id)
        WHERE pc.pilot_id = ?
          AND pc.schema_ok = 1
        """,
        (MARKET_PILOT,),
    ).fetchall()
    con.close()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw: dict[str, Any] = {}
        try:
            raw = json.loads(row["raw_json"] or "{}")
        except json.JSONDecodeError:
            raw = {}
        out[str(row["contract_id"])] = {
            "contract_id": str(row["contract_id"]),
            "market_p": float(row["p_success"]),
            "y": int(row["y_known"]),
            "market_source": MARKET_PILOT,
            "market_timing": raw.get("target_days_before_resolution", "stage_c_default"),
            "market_provenance": raw.get("base_rate_provenance"),
        }
    return out


def load_acquired_market(path: Path, db: Path) -> dict[str, dict[str, Any]]:
    joined = [row for row in read_jsonl(path) if row.get("fetch_status") == "joined"]
    if not joined:
        return {}
    con = sqlite3.connect(db)
    placeholders = ",".join("?" for _ in joined)
    outcomes = {
        str(cid): int(y)
        for cid, y in con.execute(
            f"SELECT contract_id, y_known FROM contracts WHERE contract_id IN ({placeholders})",
            tuple(str(row["contract_id"]) for row in joined),
        )
        if y in (0, 1)
    }
    con.close()
    out: dict[str, dict[str, Any]] = {}
    for row in joined:
        cid = str(row["contract_id"])
        if cid not in outcomes:
            continue
        out[cid] = {
            "contract_id": cid,
            "market_p": float(row["base_rate_value"]),
            "y": outcomes[cid],
            "market_source": "f47_external_bar_manifold_acquisition",
            "market_timing": int(row.get("target_days_before_resolution") or 0),
            "market_provenance": row.get("base_rate_provenance"),
        }
    return out


def load_acquired_polymarket(path: Path) -> dict[str, dict[str, Any]]:
    joined = [
        row
        for row in read_jsonl(path)
        if row.get("join_status") == "joined" and row.get("market_p") is not None
    ]
    out: dict[str, dict[str, Any]] = {}
    for row in joined:
        y = row.get("y_known")
        if y not in (0, 1):
            continue
        out[str(row["contract_id"])] = {
            "contract_id": str(row["contract_id"]),
            "market_p": float(row["market_p"]),
            "y": int(y),
            "market_source": "f47_polymarket_external_bar_acquisition",
            "market_timing": row.get("freeze_datetime"),
            "market_provenance": row.get("bar_source"),
        }
    return out


def f47_panel_predictions(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    source_edges, _ = load_edges("source_balanced", args.source_calls, args.source_key)
    tournament_edges, _ = load_edges("translation_tournament", args.tournament_calls, args.tournament_key)
    train = contract_rows(source_edges)
    test = contract_rows(tournament_edges)
    intercept, slope = fit_logistic(
        [float(row["pairwise_score"]) for row in train],
        [int(row["y"]) for row in train],
    )
    by_contract: dict[str, list[dict[str, Any]]] = {}
    for row in test:
        translated = sigmoid(intercept + slope * float(row["pairwise_score"]))
        raw = float(row["raw_context_p"])
        item = {
            **row,
            "raw_context_p": raw,
            "f100_family_p": confident_no(raw),
            "translated_p": translated,
        }
        by_contract.setdefault(str(row["contract_id"]), []).append(item)
    out: dict[str, dict[str, Any]] = {}
    for cid, rows in by_contract.items():
        y_values = {int(row["y"]) for row in rows}
        sources = {str(row["source"]) for row in rows}
        if len(y_values) != 1 or len(sources) != 1:
            continue
        raw_panel = mean([float(row["raw_context_p"]) for row in rows])
        out[cid] = {
            "contract_id": cid,
            "source": next(iter(sources)),
            "y": next(iter(y_values)),
            "family_count": len({str(row["family"]) for row in rows}),
            "raw_panel_p": raw_panel,
            "f100_mean_family_p": mean([float(row["f100_family_p"]) for row in rows]),
            "translated_panel_p": mean([float(row["translated_p"]) for row in rows]),
        }
    return out


def compare(rows: list[dict[str, Any]], candidate: str, baseline: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    candidate_losses = [brier(float(row[candidate]), int(row["y"])) for row in rows]
    baseline_losses = [brier(float(row[baseline]), int(row["y"])) for row in rows]
    return {
        "n": len(rows),
        "candidate": candidate,
        "baseline": baseline,
        "candidate_brier": round(mean(candidate_losses), 6),
        "baseline_brier": round(mean(baseline_losses), 6),
        "delta_candidate_minus_baseline": round(mean([c - b for c, b in zip(candidate_losses, baseline_losses)]), 6),
        "paired_permutation": paired_permutation_test(candidate_losses, baseline_losses, seed=47),
    }


def summarize(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    return {
        "n": len(rows),
        "brier": round(mean([brier(float(row[policy]), int(row["y"])) for row in rows]), 6),
        "mean_p": round(mean([float(row[policy]) for row in rows]), 6),
        "yes_rate": round(mean([float(row["y"]) for row in rows]), 6),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    predictions = f47_panel_predictions(args)
    market_rows = load_existing_market(args.db)
    market_rows.update(load_acquired_market(args.manifold_1d, args.db))
    market_rows.update(load_acquired_polymarket(args.polymarket_bars))
    rows: list[dict[str, Any]] = []
    for cid, market in sorted(market_rows.items()):
        pred = predictions.get(cid)
        if pred is None:
            continue
        if int(pred["y"]) != int(market["y"]):
            raise SystemExit(f"outcome mismatch for {cid}")
        item = {
            **pred,
            "market_p": float(market["market_p"]),
            "market_source": market["market_source"],
            "market_timing": market["market_timing"],
            "market_provenance": market["market_provenance"],
        }
        item["half_market_half_translated_p"] = 0.5 * item["market_p"] + 0.5 * item["translated_panel_p"]
        rows.append(item)
    comparisons = {
        "translated_vs_market": compare(rows, "translated_panel_p", "market_p"),
        "f100_vs_market": compare(rows, "f100_mean_family_p", "market_p"),
        "raw_vs_market": compare(rows, "raw_panel_p", "market_p"),
        "half_blend_vs_market": compare(rows, "half_market_half_translated_p", "market_p"),
        "translated_vs_f100": compare(rows, "translated_panel_p", "f100_mean_family_p"),
        "translated_vs_raw": compare(rows, "translated_panel_p", "raw_panel_p"),
    }
    market_comp = comparisons["translated_vs_market"]
    market_p_value = (market_comp.get("paired_permutation") or {}).get("p_value")
    verdict = "f47_external_bar_slice_too_small"
    if (
        len(rows) >= 20
        and market_comp.get("delta_candidate_minus_baseline", 1.0) < -0.01
        and market_p_value is not None
        and market_p_value <= 0.05
    ):
        verdict = "f47_external_bar_candidate_positive"
    elif len(rows) >= 20 and market_comp.get("delta_candidate_minus_baseline", 1.0) < -0.01:
        verdict = "f47_external_bar_directional_underpowered"
    elif len(rows) and market_comp.get("delta_candidate_minus_baseline", 0.0) > 0:
        verdict = "f47_external_bar_market_beats_translated_on_tiny_slice"
    return {
        "schema": "f47-external-bar-score-v1",
        "date": "2026-06-03",
        "n_joined": len(rows),
        "source_counts": {
            key: sum(1 for row in rows if row["source"] == key)
            for key in sorted({row["source"] for row in rows})
        },
        "market_source_counts": {
            key: sum(1 for row in rows if row["market_source"] == key)
            for key in sorted({row["market_source"] for row in rows})
        },
        "policy_summary": {
            key: summarize(rows, key)
            for key in ("market_p", "raw_panel_p", "f100_mean_family_p", "translated_panel_p", "half_market_half_translated_p")
        },
        "comparisons": comparisons,
        "verdict": verdict,
        "interpretation": (
            "This is a tiny joined external-bar slice. It is useful as a kill/control "
            "signal for overclaiming F47, not as broad evidence about LLM+market additivity."
        ),
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# F47 External-Bar Score",
        "",
        report["interpretation"],
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Joined rows: `{report['n_joined']}`",
        f"- Market source counts: `{report['market_source_counts']}`",
        "",
        "## Policy Brier",
        "",
        "| policy | n | Brier | mean p | yes rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, row in report["policy_summary"].items():
        lines.append(f"| `{key}` | {row.get('n')} | {row.get('brier')} | {row.get('mean_p')} | {row.get('yes_rate')} |")
    lines.extend(["", "## Comparisons", "", "| comparison | delta candidate-minus-baseline | p |", "|---|---:|---:|"])
    for key, row in report["comparisons"].items():
        p = (row.get("paired_permutation") or {}).get("p_value") if isinstance(row.get("paired_permutation"), dict) else None
        lines.append(f"| `{key}` | {row.get('delta_candidate_minus_baseline')} | {p} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source-calls", type=Path, default=DEFAULT_SOURCE_CALLS)
    parser.add_argument("--source-key", type=Path, default=DEFAULT_SOURCE_KEY)
    parser.add_argument("--tournament-calls", type=Path, default=DEFAULT_TOURNAMENT_CALLS)
    parser.add_argument("--tournament-key", type=Path, default=DEFAULT_TOURNAMENT_KEY)
    parser.add_argument("--manifold-1d", type=Path, default=DEFAULT_MANIFOLD_1D)
    parser.add_argument("--polymarket-bars", type=Path, default=DEFAULT_POLYMARKET)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()
    report = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("verdict", "n_joined", "policy_summary", "comparisons")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
