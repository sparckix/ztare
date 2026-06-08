#!/usr/bin/env python3
"""Attempt a local base-rate join for the GP-245 Law 3 Stage-B panel.

This is the executable version of the Stage-C packet: it searches local
ForecastBench/raw Manifold artifacts for pre-outcome probabilities, emits
per-contract join status, and only reports a repaired effect if enough matched
base-rate coverage exists. No model calls and no DB mutation.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
FSC_WORKSPACE = PROGRAM / "forecaster_skill_calibration_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PANEL = WORKSPACE / "cutoff_stage_b_minimum_panel_contracts.jsonl"
DEFAULT_OUT = WORKSPACE
FORECASTBENCH_RAW_FILES = (
    FSC_WORKSPACE / "fb_2026_04_12_questions.json",
    FSC_WORKSPACE / "forecastbench_2026_05_24_raw.json",
)
CUTOFF_MANIFOLD_CANDIDATES = WORKSPACE / "cutoff_manifold_acquisition_candidates.jsonl"
STAGE_C_MANIFOLD_PROBABILITIES = WORKSPACE / "cutoff_stage_c_manifold_probability_acquisition.jsonl"


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def as_probability(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        p = float(value)
    except Exception:
        return None
    if p > 1.0 and p <= 100.0:
        p = p / 100.0
    if p < 0.0 or p > 1.0:
        return None
    return p


def probability_band(p: float | None) -> str:
    if p is None:
        return "missing"
    lo = int(p / 0.2) * 20
    if lo >= 100:
        lo = 80
    return f"{lo / 100:.2f}_{(lo + 20) / 100:.2f}"


def path_label(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def normalized_url(url: str | None) -> str:
    if not url:
        return ""
    return str(url).strip().rstrip(".").rstrip("/")


def forecastbench_index() -> dict[str, dict[str, Any]]:
    by_url: dict[str, dict[str, Any]] = {}
    by_question: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for path in FORECASTBENCH_RAW_FILES:
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        for row in data.get("questions", []):
            if not isinstance(row, dict):
                continue
            p = as_probability(row.get("freeze_datetime_value"))
            if p is None:
                continue
            payload = {
                "base_rate_value": p,
                "base_rate_band": probability_band(p),
                "base_rate_provenance": f"{path.relative_to(REPO)}:freeze_datetime_value",
                "prior_timestamp": row.get("freeze_datetime"),
                "source_url": row.get("url"),
                "source": row.get("source"),
                "source_question_id": row.get("id"),
            }
            if row.get("url"):
                by_url[normalized_url(row.get("url"))] = payload
            if row.get("question"):
                by_question[str(row.get("question"))] = payload
            if row.get("id"):
                by_id[str(row.get("id"))] = payload
    return {"url": by_url, "question": by_question, "id": by_id}


def manifold_candidate_index() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(CUTOFF_MANIFOLD_CANDIDATES):
        raw = row.get("raw_manifold") or {}
        p = as_probability(raw.get("probability"))
        if p is None:
            continue
        contract_id = str(row.get("contract_id") or "")
        out[contract_id] = {
            "base_rate_value": p,
            "base_rate_band": probability_band(p),
            "base_rate_provenance": f"{CUTOFF_MANIFOLD_CANDIDATES.relative_to(REPO)}:raw_manifold.probability",
            "prior_timestamp": raw.get("createdTime"),
            "source_url": raw.get("url"),
            "source": "manifold",
            "source_question_id": raw.get("id"),
        }
    return out


def stage_c_manifold_probability_index() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(STAGE_C_MANIFOLD_PROBABILITIES):
        if row.get("fetch_status") != "joined":
            continue
        p = as_probability(row.get("base_rate_value"))
        if p is None:
            continue
        contract_id = str(row.get("contract_id") or "")
        out[contract_id] = {
            "base_rate_value": p,
            "base_rate_band": row.get("base_rate_band") or probability_band(p),
            "base_rate_provenance": row.get("base_rate_provenance")
            or f"{STAGE_C_MANIFOLD_PROBABILITIES.relative_to(REPO)}:base_rate_value",
            "prior_timestamp": row.get("prior_timestamp"),
            "source_url": row.get("source_url"),
            "source": "manifold",
            "source_question_id": row.get("market_id"),
            "selection_method": row.get("selection_method"),
        }
    return out


def db_probability_index(db: Path, contract_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not contract_ids:
        return {}
    con = sqlite3.connect(db)
    cur = con.cursor()
    placeholders = ",".join("?" for _ in contract_ids)
    rows = cur.execute(
        f"SELECT contract_id, raw_json FROM contracts WHERE contract_id IN ({placeholders})",
        contract_ids,
    ).fetchall()
    con.close()
    out = {}
    for contract_id, raw_text in rows:
        raw = parse_json(raw_text)
        for field in ("probability", "market_price", "market_price_at_forecast", "freeze_datetime_value"):
            p = as_probability(raw.get(field))
            if p is not None:
                out[str(contract_id)] = {
                    "base_rate_value": p,
                    "base_rate_band": probability_band(p),
                    "base_rate_provenance": f"contracts.raw_json.{field}",
                    "prior_timestamp": raw.get("freeze_datetime") or raw.get("createdTime"),
                    "source_url": raw.get("url") or raw.get("resolution_source_url"),
                    "source": raw.get("source") or raw.get("external_source"),
                    "source_question_id": raw.get("id"),
                }
                break
    return out


def contract_id_aliases(contract_id: str) -> list[str]:
    aliases = [contract_id]
    for prefix in ("fb_manifold_bulk_", "fb_manifold_", "manifold_"):
        if contract_id.startswith(prefix):
            aliases.append(contract_id[len(prefix):])
    return aliases


def join_one(row: dict[str, Any], indexes: dict[str, Any]) -> dict[str, Any]:
    cid = str(row["contract_id"])
    candidates = [
        indexes["db"].get(cid),
        indexes["stage_c_manifold"].get(cid),
        indexes["manifold"].get(cid),
        indexes["forecastbench"]["url"].get(normalized_url(row.get("resolution_source_url"))),
        indexes["forecastbench"]["question"].get(str(row.get("question"))),
    ]
    for alias in contract_id_aliases(cid):
        candidates.append(indexes["forecastbench"]["id"].get(alias))
    for candidate in candidates:
        if candidate:
            return {**candidate, "fetch_status": "joined"}
    return {
        "base_rate_value": None,
        "base_rate_band": "missing",
        "base_rate_provenance": None,
        "prior_timestamp": None,
        "source_url": row.get("resolution_source_url"),
        "source": row.get("source"),
        "source_question_id": None,
        "fetch_status": "missing_local_probability",
    }


def load_stage_b_calls(db: Path, contract_ids: list[str]) -> list[dict[str, Any]]:
    if not contract_ids:
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in contract_ids)
    rows = [
        dict(row)
        for row in con.execute(
            f"""
            SELECT contract_id, family, brier, schema_ok
            FROM pilot_calls
            WHERE pilot_id = 'cutoff_stage_b_panel_v1'
              AND contract_id IN ({placeholders})
              AND brier IS NOT NULL
              AND schema_ok = 1
            """,
            contract_ids,
        )
    ]
    con.close()
    return rows


def repaired_effect(joined: list[dict[str, Any]], db: Path) -> dict[str, Any]:
    covered = [row for row in joined if row["fetch_status"] == "joined"]
    if not covered:
        return {"status": "no_coverage"}
    covered_ids = [row["contract_id"] for row in covered]
    calls = load_stage_b_calls(db, covered_ids)
    meta = {row["contract_id"]: row for row in covered}
    stratum_cells: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    base_rate_cells: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for call in calls:
        row = meta.get(str(call["contract_id"]))
        if not row:
            continue
        stratum_key = (str(call["family"]), str(row["stratum_key"]), str(row["cutoff_relation"]))
        base_rate_key = (
            str(call["family"]),
            str(row["stratum_key"]),
            str(row["base_rate_band"]),
            str(row["cutoff_relation"]),
        )
        stratum_cells[stratum_key].append(float(call["brier"]))
        base_rate_cells[base_rate_key].append(float(call["brier"]))

    def paired_delta(cells: dict[tuple[Any, ...], list[float]]) -> dict[str, Any]:
        paired_pre: list[float] = []
        paired_post: list[float] = []
        cell_prefixes = sorted({key[:-1] for key in cells})
        for prefix in cell_prefixes:
            pre = cells.get((*prefix, "pre_cutoff"), [])
            post = cells.get((*prefix, "post_cutoff"), [])
            if pre and post:
                paired_pre.append(statistics.mean(pre))
                paired_post.append(statistics.mean(post))
        if not paired_pre:
            return {"paired_cells": 0, "post_minus_pre_brier": None}
        return {
            "paired_cells": len(paired_pre),
            "post_minus_pre_brier": round(statistics.mean(paired_post) - statistics.mean(paired_pre), 6),
        }

    stratum_effect = paired_delta(stratum_cells)
    base_rate_effect = paired_delta(base_rate_cells)
    if not stratum_effect["paired_cells"]:
        return {
            "status": "insufficient_paired_coverage",
            "covered_contracts": len(covered),
            "covered_relation_counts": dict(Counter(row["cutoff_relation"] for row in covered)),
        }
    if not base_rate_effect["paired_cells"]:
        return {
            "status": "scored_stratum_only_base_rate_unpaired",
            "covered_contracts": len(covered),
            "covered_relation_counts": dict(Counter(row["cutoff_relation"] for row in covered)),
            "stratum_matched": stratum_effect,
            "base_rate_matched": base_rate_effect,
        }
    return {
        "status": "scored_partial_repair",
        "covered_contracts": len(covered),
        "covered_relation_counts": dict(Counter(row["cutoff_relation"] for row in covered)),
        "stratum_matched": stratum_effect,
        "base_rate_matched": base_rate_effect,
    }


def build(db: Path, panel_path: Path) -> dict[str, Any]:
    panel_path = panel_path.resolve()
    panel = load_jsonl(panel_path)
    contract_ids = [str(row["contract_id"]) for row in panel]
    indexes = {
        "forecastbench": forecastbench_index(),
        "manifold": manifold_candidate_index(),
        "stage_c_manifold": stage_c_manifold_probability_index(),
        "db": db_probability_index(db, contract_ids),
    }
    joined = []
    for row in panel:
        hit = join_one(row, indexes)
        joined.append(
            {
                "contract_id": row["contract_id"],
                "source": row.get("source"),
                "topic": row.get("topic"),
                "question_length_bucket": row.get("question_length_bucket"),
                "stratum_key": row.get("stratum_key"),
                "cutoff_relation": row.get("cutoff_relation"),
                "resolve_date": row.get("resolve_date"),
                "y_known": row.get("y_known"),
                **hit,
            }
        )
    relation_counts = Counter(row["cutoff_relation"] for row in joined)
    joined_relation_counts = Counter(
        row["cutoff_relation"] for row in joined if row["fetch_status"] == "joined"
    )
    missing = [row for row in joined if row["fetch_status"] != "joined"]
    effect = repaired_effect(joined, db)
    return {
        "schema": "gp245-cutoff-stage-c-base-rate-join-v1",
        "panel_path": path_label(panel_path),
        "db": str(db),
        "panel_contracts": len(joined),
        "coverage": {
            "joined_contracts": len(joined) - len(missing),
            "missing_contracts": len(missing),
            "relation_counts": dict(sorted(relation_counts.items())),
            "joined_relation_counts": dict(sorted(joined_relation_counts.items())),
            "base_rate_band_counts": dict(Counter(row["base_rate_band"] for row in joined if row["fetch_status"] == "joined")),
            "provenance_counts": dict(Counter(row["base_rate_provenance"] for row in joined if row["fetch_status"] == "joined")),
        },
        "repaired_effect": effect,
        "verdict": (
            "base_rate_join_sufficient"
            if effect.get("status") == "scored_partial_repair"
            else "base_rate_join_insufficient_external_required"
        ),
        "contract_base_rates": joined,
        "missing_contracts": missing,
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_stage_c_base_rate_join_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "cutoff_stage_c_base_rate_join_missing_contracts.jsonl").open("w", encoding="utf-8") as f:
        for row in report["missing_contracts"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Cutoff Stage-C Base-Rate Join Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Verdict: `{report['verdict']}`",
        f"- Panel contracts: {report['panel_contracts']}",
        f"- Joined contracts: {report['coverage']['joined_contracts']}",
        f"- Missing contracts: {report['coverage']['missing_contracts']}",
        f"- Joined relation counts: `{report['coverage']['joined_relation_counts']}`",
        f"- Provenance counts: `{report['coverage']['provenance_counts']}`",
        f"- Repaired effect status: `{report['repaired_effect']['status']}`",
        f"- Stratum-matched effect: `{report['repaired_effect'].get('stratum_matched')}`",
        f"- Base-rate-matched effect: `{report['repaired_effect'].get('base_rate_matched')}`",
        "",
        "## Interpretation",
        "",
        (
            "The joined panel now has enough paired coverage for a partial Law 3 repair."
            if report["verdict"] == "base_rate_join_sufficient"
            else "Local artifacts do not yet provide enough pre-outcome base-rate coverage to repair Law 3."
        ),
        (
            "Remaining missing contracts stay in `cutoff_stage_c_base_rate_join_missing_contracts.jsonl`."
            if report["coverage"]["missing_contracts"]
            else "No missing contracts remain in the Stage-C base-rate join."
        ),
        "",
    ]
    (out_dir / "cutoff_stage_c_base_rate_join_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build(args.db, args.panel)
    write_outputs(report, args.out_dir)
    print(f"wrote {args.out_dir / 'cutoff_stage_c_base_rate_join_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
