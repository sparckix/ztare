#!/usr/bin/env python3
"""Render a CEC packet for Law 3 alternate general-source acquisition.

This does not acquire rows and does not write the DB. It applies the
Capability Evidence Contract discipline to the tempting move after Metaculus
API access is insufficient: substituting FRED/yfinance-style dataset rows for
the remaining Metaculus target cells.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_TARGETS = WORKSPACE / "cutoff_second_source_pre_cutoff_acquisition_targets.jsonl"
DEFAULT_METACULUS_PROBE = WORKSPACE / "metaculus_api_access_probe_2026_06_03.md"
DEFAULT_METACULUS_REPROBE = WORKSPACE / "metaculus_api_access_reprobe_2026_06_03.json"
DEFAULT_FRED_PROBE = WORKSPACE / "fred_source_lane_probe_2026_06_04/fred_source_lane_probe.json"
DEFAULT_FRED_MANIFEST = WORKSPACE / "fred_forecastbench_manifest_2026_06_04/fred_forecastbench_manifest_audit.json"
DEFAULT_FRED_PRE_COMPANION = (
    WORKSPACE / "fred_pre_cutoff_companion_2026_06_04/fred_pre_cutoff_companion_manifest.json"
)
DEFAULT_OUT = WORKSPACE


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def bootstrap_dotenv() -> None:
    if os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY"):
        return
    if load_dotenv is None:
        return
    candidate = REPO / ".env"
    if candidate.exists():
        load_dotenv(candidate, override=False)


def db_source_counts(db: Path) -> dict[str, dict[str, int]]:
    con = sqlite3.connect(db)
    try:
        out: dict[str, dict[str, int]] = {}
        for source, n, y, pre, post in con.execute(
            """
            SELECT source, COUNT(*), SUM(y_known IS NOT NULL),
                   SUM(CASE WHEN post_training_cutoff = 0 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN post_training_cutoff = 1 THEN 1 ELSE 0 END)
            FROM contracts
            WHERE source IN ('fred', 'yfinance', 'dbnomics', 'acled', 'wikipedia', 'metaculus', 'polymarket')
            GROUP BY source
            ORDER BY source
            """
        ):
            out[str(source)] = {
                "contracts": int(n or 0),
                "y_known": int(y or 0),
                "pre_cutoff_flagged": int(pre or 0),
                "post_cutoff_flagged": int(post or 0),
            }
        return out
    finally:
        con.close()


def target_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, int] = {}
    by_cell: dict[str, int] = {}
    for row in rows:
        source = str(row.get("source"))
        n = int(row.get("target_pre_cutoff_rows") or 0)
        by_source[source] = by_source.get(source, 0) + n
        key = " | ".join(
            [
                source,
                str(row.get("freeze_value_band")),
                str(row.get("question_length_band")),
            ]
        )
        by_cell[key] = by_cell.get(key, 0) + n
    return {"total": sum(by_source.values()), "by_source": by_source, "by_cell": by_cell}


def build(args: argparse.Namespace) -> dict[str, Any]:
    bootstrap_dotenv()
    targets = read_jsonl(args.targets)
    target = target_summary(targets)
    db = db_source_counts(args.db)
    metaculus_probe_exists = args.metaculus_probe.exists()
    metaculus_reprobe = read_json(args.metaculus_reprobe)
    fred_env_set = bool(os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY"))
    return {
        "schema": "gp245-law3-general-source-cec-v1",
        "inputs": {
            "target_manifest": str(args.targets.relative_to(REPO)),
            "target_manifest_sha256": sha256_file(args.targets),
            "metaculus_api_probe": str(args.metaculus_probe.relative_to(REPO)) if metaculus_probe_exists else None,
            "metaculus_api_probe_sha256": sha256_file(args.metaculus_probe),
            "metaculus_api_reprobe": (
                str(args.metaculus_reprobe.relative_to(REPO))
                if args.metaculus_reprobe.exists()
                else None
            ),
            "metaculus_api_reprobe_sha256": sha256_file(args.metaculus_reprobe),
            "fred_source_lane_probe": (
                str(args.fred_probe.relative_to(REPO)) if args.fred_probe.exists() else None
            ),
            "fred_source_lane_probe_sha256": sha256_file(args.fred_probe),
            "fred_forecastbench_manifest": (
                str(args.fred_manifest.relative_to(REPO)) if args.fred_manifest.exists() else None
            ),
            "fred_forecastbench_manifest_sha256": sha256_file(args.fred_manifest),
            "fred_pre_cutoff_companion": (
                str(args.fred_pre_companion.relative_to(REPO)) if args.fred_pre_companion.exists() else None
            ),
            "fred_pre_cutoff_companion_sha256": sha256_file(args.fred_pre_companion),
            "db": str(args.db.relative_to(REPO)),
        },
        "current_state": {
            "target_summary": target,
            "db_source_counts": db,
            "fred_api_env_available_in_this_shell": fred_env_set,
            "metaculus_probe_verdict": (
                "correct_endpoint_and_auth_insufficient_access_tier"
                if metaculus_probe_exists
                else "missing_probe"
            ),
            "metaculus_reprobe_verdict": metaculus_reprobe.get("verdict") or "missing_reprobe",
            "metaculus_reprobe_field_availability": metaculus_reprobe.get("field_availability") or {},
            "fred_source_lane_probe": read_json(args.fred_probe),
            "fred_forecastbench_manifest": read_json(args.fred_manifest),
            "fred_pre_cutoff_companion": read_json(args.fred_pre_companion),
        },
        "capability_evidence_contracts": [
            {
                "capability_id": "metaculus_export_access_for_existing_target",
                "bottleneck_stage_targeted": {
                    "decomposition_ref": str(args.targets.relative_to(REPO)),
                    "snapshot_hash": sha256_file(args.targets),
                    "declared_causal_path": (
                        "exposes resolved Yes/No values and pre-resolution community "
                        "prediction history for the 17 remaining Metaculus target rows"
                    ),
                },
                "exogenous_carrier": {
                    "kind": "downstream_decision",
                    "where": "Metaculus bot-benchmarking/data-download access or licensed export",
                    "why_unfakeable": (
                        "Metaculus controls the export/access tier; the researcher cannot "
                        "choose the hidden resolution or aggregate-history distribution"
                    ),
                },
                "kill_criterion": (
                    "Abandon this path if the granted export cannot provide both "
                    "resolved Yes/No outcome and a dated aggregate/history value at "
                    "or before the seven-day pre-resolution freeze time."
                ),
                "downstream_decision_changed": (
                    "Whether the existing 17-row Metaculus target can be DB-ingested "
                    "and used in the second-source pre/post packet."
                ),
                "cost_ceiling": {
                    "wall_time": "one access/export request plus one bounded ingest pass",
                    "usd": "0 unless Metaculus requires paid data access",
                    "agent_attention": "low after export is available",
                },
                "reuse_surface": "metaculus_export_to_law3_contract_rows",
                "rankability": "rankable_existing_target_path",
            },
            {
                "capability_id": "dataset_source_law3_replication_fred_yfinance",
                "bottleneck_stage_targeted": {
                    "decomposition_ref": str(args.targets.relative_to(REPO)),
                    "snapshot_hash": sha256_file(args.targets),
                    "declared_causal_path": (
                        "constructs a new source-currency replication from official "
                        "time-series outcomes, matched on source/topic/length/horizon; "
                        "does not fill Metaculus freeze-probability cells"
                    ),
                },
                "exogenous_carrier": {
                    "kind": "matched_negative_control",
                    "where": (
                        "official FRED/yfinance observed values plus a frozen threshold "
                        "manifest; scored only after pre/post rows are matched and y_known "
                        "comes from external time-series data"
                    ),
                    "why_unfakeable": (
                        "the observed time-series values are external; however, threshold "
                        "selection is researcher-constructed and therefore needs frozen "
                        "manifest controls before any model calls"
                    ),
                },
                "kill_criterion": (
                    "Do not use as a substitute for the Metaculus target. Kill or keep "
                    "separate if it cannot produce at least 40 pre and 40 post rows with "
                    "strict resolution dates, external y_known receipts, no latest-date "
                    "confusion, and matched source/topic/length/horizon cells."
                ),
                "downstream_decision_changed": (
                    "Whether to open a new dataset-source Law 3 replication lane, not "
                    "whether the current Metaculus target is complete."
                ),
                "cost_ceiling": {
                    "wall_time": "one packet-construction pass plus one no-call audit",
                    "usd": "0 if public CSV/API access suffices",
                    "agent_attention": "medium because threshold construction needs controls",
                },
                "reuse_surface": "dataset_timeseries_to_law3_contract_rows",
                "rankability": "rankable_new_design_only_not_current_target",
            },
        ],
        "verdict": {
            "existing_target_next_step": "get_metaculus_export_or_access_tier",
            "dataset_source_substitution": "invalid_as_drop_in_substitute",
            "dataset_source_new_lane": "allowed_only_with_frozen_manifest_and_controls",
        },
        "interpretation": (
            "The remaining Metaculus rows are defined by source plus freeze-probability "
            "and question-length cells. Dataset-source rows can be useful for a broader "
            "source-currency replication, but they cannot honestly satisfy those cells "
            "unless the target design is explicitly changed before model calls."
        ),
    }


def render_md(packet: dict[str, Any]) -> str:
    lines = [
        "# Law 3 General-Source Capability Evidence Packet",
        "",
        f"- Schema: `{packet['schema']}`",
        f"- Existing-target next step: `{packet['verdict']['existing_target_next_step']}`",
        f"- Dataset-source substitution: `{packet['verdict']['dataset_source_substitution']}`",
        f"- Dataset-source new lane: `{packet['verdict']['dataset_source_new_lane']}`",
        "",
        "## Current State",
        "",
        "```json",
        json.dumps(packet["current_state"], indent=2, sort_keys=True),
        "```",
        "",
        "## Capability Evidence Contracts",
        "",
    ]
    for cec in packet["capability_evidence_contracts"]:
        lines.extend(
            [
                f"### {cec['capability_id']}",
                f"- Rankability: `{cec['rankability']}`",
                f"- Declared causal path: {cec['bottleneck_stage_targeted']['declared_causal_path']}",
                f"- Exogenous carrier: `{cec['exogenous_carrier']['kind']}` at {cec['exogenous_carrier']['where']}",
                f"- Why unfakeable: {cec['exogenous_carrier']['why_unfakeable']}",
                f"- Kill criterion: {cec['kill_criterion']}",
                f"- Decision changed: {cec['downstream_decision_changed']}",
                f"- Reuse surface: `{cec['reuse_surface']}`",
                "",
            ]
        )
    lines.extend(["## Interpretation", "", packet["interpretation"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--metaculus-probe", type=Path, default=DEFAULT_METACULUS_PROBE)
    parser.add_argument("--metaculus-reprobe", type=Path, default=DEFAULT_METACULUS_REPROBE)
    parser.add_argument("--fred-probe", type=Path, default=DEFAULT_FRED_PROBE)
    parser.add_argument("--fred-manifest", type=Path, default=DEFAULT_FRED_MANIFEST)
    parser.add_argument("--fred-pre-companion", type=Path, default=DEFAULT_FRED_PRE_COMPANION)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    packet = build(args)
    json_path = args.out_dir / "cutoff_general_source_cec_packet.json"
    md_path = args.out_dir / "cutoff_general_source_cec_packet.md"
    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(packet), encoding="utf-8")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
