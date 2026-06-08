#!/usr/bin/env python3
"""Audit dataset-source rows for label-time validity before law/policy use.

No model calls. DB ingestion is opt-in via ``--ingest-db``.

The FRED vintage repair exposed a failure mode that source-currency flags alone
cannot catch: an official current answer key can differ from the values
available at forecast/resolution time. This report classifies dataset-source
contracts into eligibility buckets so downstream law and calibration-policy
claims do not silently consume current-label artifacts.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_FRED_REPAIR = WORKSPACE / "fred_vintage_bulk_repair_2026_06_04/fred_vintage_bulk_repair.json"
DEFAULT_OUT = WORKSPACE / "dataset_label_time_gate_2026_06_04"

DATASET_SOURCES = {"fred", "yfinance", "yfinance_etf"}


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def load_contracts(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in con.execute(
            """
            SELECT contract_id, question, source, source_corpus, horizon,
                   y_known, post_training_cutoff, task_type,
                   y_known_provenance, resolution_source_url, raw_json
            FROM contracts
            ORDER BY source, source_corpus, contract_id
            """
        )
    ]
    con.close()
    return rows


def fred_receipts(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    return {
        str(row.get("contract_id")): row
        for row in data.get("rows", [])
        if isinstance(row, dict) and row.get("contract_id")
    }


def is_dataset_source(row: dict[str, Any]) -> bool:
    return inferred_dataset_family(row) is not None


def inferred_dataset_family(row: dict[str, Any]) -> str | None:
    source = str(row.get("source") or "").lower()
    corpus = str(row.get("source_corpus") or "").lower()
    task = str(row.get("task_type") or "").lower()
    if source in DATASET_SOURCES:
        return source
    for src in sorted(DATASET_SOURCES, key=len, reverse=True):
        if src in corpus or src in task:
            return src
    return None


def classify_row(row: dict[str, Any], *, fred_by_contract: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cid = str(row.get("contract_id") or "")
    source = str(row.get("source") or "")
    dataset_family = inferred_dataset_family(row)
    resolved = row.get("y_known") in (0, 1)
    base = {
        "contract_id": cid,
        "source": source,
        "source_corpus": row.get("source_corpus"),
        "task_type": row.get("task_type"),
        "post_training_cutoff": row.get("post_training_cutoff"),
        "resolved": bool(resolved),
        "y_known": row.get("y_known"),
        "y_known_provenance": row.get("y_known_provenance"),
        "dataset_family": dataset_family,
    }
    if dataset_family is None:
        return {
            **base,
            "dataset_source": False,
            "label_time_status": "not_dataset_source",
            "law_policy_current_label_eligible": None,
            "required_next_receipt": None,
        }
    if not resolved:
        return {
            **base,
            "dataset_source": True,
            "label_time_status": "unresolved_no_label_test_yet",
            "law_policy_current_label_eligible": False,
            "required_next_receipt": "outcome plus label-time/as-of receipt before scoring",
        }
    if dataset_family == "fred":
        receipt = fred_by_contract.get(cid)
        if not receipt:
            return {
                **base,
                "dataset_source": True,
                "label_time_status": "fred_resolved_without_vintage_receipt",
                "law_policy_current_label_eligible": False,
                "required_next_receipt": "FRED vintage/as-of row or ALFRED receipt",
            }
        label_changed = receipt.get("y_two_point_differs_from_current") is True
        return {
            **base,
            "dataset_source": True,
            "label_time_status": (
                "fred_vintage_repaired_current_label_changed"
                if label_changed
                else "fred_vintage_repaired_current_label_stable"
            ),
            "law_policy_current_label_eligible": False if label_changed else True,
            "vintage_repair_available": True,
            "vintage_y_two_point": receipt.get("y_two_point_realtime"),
            "y_two_point_differs_from_current": receipt.get("y_two_point_differs_from_current"),
            "due_value_changed_asof_due_vs_current": receipt.get("due_value_changed_asof_due_vs_current"),
            "resolution_value_changed_asof_resolution_vs_current": receipt.get(
                "resolution_value_changed_asof_resolution_vs_current"
            ),
            "required_next_receipt": (
                "use repaired vintage label or ALFRED confirmation; do not use current DB label"
                if label_changed
                else "keep vintage/as-of receipt attached if this row is used"
            ),
        }
    return {
        **base,
        "dataset_source": True,
        "label_time_status": f"{dataset_family}_resolved_without_label_time_receipt",
        "law_policy_current_label_eligible": False,
        "required_next_receipt": "source-specific as-of/vintage/corporate-action-adjusted label receipt",
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dataset = [row for row in rows if row.get("dataset_source")]
    resolved_dataset = [row for row in dataset if row.get("resolved")]
    eligible = [row for row in resolved_dataset if row.get("law_policy_current_label_eligible") is True]
    ineligible = [row for row in resolved_dataset if row.get("law_policy_current_label_eligible") is False]
    by_source: dict[str, dict[str, Any]] = {}
    for source in sorted({str(row.get("dataset_family") or "") for row in dataset}):
        src_rows = [row for row in dataset if str(row.get("dataset_family") or "") == source]
        src_resolved = [row for row in src_rows if row.get("resolved")]
        by_source[source] = {
            "rows": len(src_rows),
            "resolved": len(src_resolved),
            "eligible_current_label_rows": sum(
                1 for row in src_resolved if row.get("law_policy_current_label_eligible") is True
            ),
            "ineligible_current_label_rows": sum(
                1 for row in src_resolved if row.get("law_policy_current_label_eligible") is False
            ),
            "status_counts": dict(sorted(Counter(str(row.get("label_time_status")) for row in src_rows).items())),
        }
    return {
        "contracts": len(rows),
        "dataset_source_rows": len(dataset),
        "resolved_dataset_source_rows": len(resolved_dataset),
        "eligible_current_label_rows": len(eligible),
        "ineligible_current_label_rows": len(ineligible),
        "label_time_status_counts": dict(sorted(Counter(str(row.get("label_time_status")) for row in dataset).items())),
        "by_source": by_source,
        "verdict": (
            "dataset_source_current_labels_not_globally_eligible"
            if ineligible
            else "all_resolved_dataset_source_rows_current_label_eligible"
        ),
    }


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return None


def ingest_db(db: Path, report: dict[str, Any]) -> int:
    generated_at = str(report["generated_at"])
    rows = report["rows"]
    con = sqlite3.connect(db)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS dataset_label_time_gate_rows (
                contract_id TEXT PRIMARY KEY,
                dataset_family TEXT NOT NULL,
                source TEXT,
                source_corpus TEXT,
                task_type TEXT,
                resolved INTEGER NOT NULL,
                y_known INTEGER,
                post_training_cutoff INTEGER,
                label_time_status TEXT NOT NULL,
                law_policy_current_label_eligible INTEGER,
                vintage_repair_available INTEGER,
                vintage_y_two_point INTEGER,
                y_two_point_differs_from_current INTEGER,
                due_value_changed_asof_due_vs_current INTEGER,
                resolution_value_changed_asof_resolution_vs_current INTEGER,
                required_next_receipt TEXT,
                generated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
            )
            """
        )
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dataset_label_time_gate_status
            ON dataset_label_time_gate_rows(dataset_family, label_time_status)
            """
        )
        con.execute("DELETE FROM dataset_label_time_gate_rows")
        con.executemany(
            """
            INSERT INTO dataset_label_time_gate_rows (
                contract_id,
                dataset_family,
                source,
                source_corpus,
                task_type,
                resolved,
                y_known,
                post_training_cutoff,
                label_time_status,
                law_policy_current_label_eligible,
                vintage_repair_available,
                vintage_y_two_point,
                y_two_point_differs_from_current,
                due_value_changed_asof_due_vs_current,
                resolution_value_changed_asof_resolution_vs_current,
                required_next_receipt,
                generated_at,
                raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(row["contract_id"]),
                    str(row["dataset_family"]),
                    row.get("source"),
                    row.get("source_corpus"),
                    row.get("task_type"),
                    int(bool(row.get("resolved"))),
                    optional_int(row.get("y_known")),
                    optional_int(row.get("post_training_cutoff")),
                    str(row["label_time_status"]),
                    optional_int(row.get("law_policy_current_label_eligible")),
                    optional_int(row.get("vintage_repair_available")),
                    optional_int(row.get("vintage_y_two_point")),
                    optional_int(row.get("y_two_point_differs_from_current")),
                    optional_int(row.get("due_value_changed_asof_due_vs_current")),
                    optional_int(row.get("resolution_value_changed_asof_resolution_vs_current")),
                    row.get("required_next_receipt"),
                    generated_at,
                    json.dumps(row, sort_keys=True),
                )
                for row in rows
            ],
        )
        con.execute("DROP VIEW IF EXISTS v_label_time_eligible_contracts")
        con.execute(
            """
            CREATE VIEW v_label_time_eligible_contracts AS
            SELECT
                c.*,
                CASE
                    WHEN g.contract_id IS NULL THEN 0
                    ELSE 1
                END AS is_dataset_source,
                g.dataset_family,
                g.label_time_status,
                CASE
                    WHEN c.y_known NOT IN (0, 1) THEN 0
                    WHEN g.contract_id IS NULL THEN 1
                    WHEN g.law_policy_current_label_eligible = 1 THEN 1
                    ELSE 0
                END AS law_policy_scoreable,
                CASE
                    WHEN c.y_known NOT IN (0, 1) THEN 'unresolved'
                    WHEN g.contract_id IS NULL THEN 'non_dataset_source'
                    WHEN g.law_policy_current_label_eligible = 1 THEN 'label_time_eligible'
                    ELSE g.label_time_status
                END AS law_policy_scoreable_reason,
                g.vintage_repair_available,
                g.vintage_y_two_point,
                g.y_two_point_differs_from_current,
                g.required_next_receipt
            FROM contracts c
            LEFT JOIN dataset_label_time_gate_rows g
              ON g.contract_id = c.contract_id
            """
        )
        con.execute("DROP VIEW IF EXISTS v_policy_scoreable_calls")
        con.execute(
            """
            CREATE VIEW v_policy_scoreable_calls AS
            SELECT
                pc.*,
                c.y_known,
                c.source,
                c.source_corpus,
                c.horizon,
                c.post_training_cutoff,
                c.question,
                c.is_dataset_source,
                c.dataset_family,
                c.label_time_status,
                c.law_policy_scoreable,
                c.law_policy_scoreable_reason,
                c.vintage_y_two_point,
                c.y_two_point_differs_from_current
            FROM pilot_calls pc
            JOIN v_label_time_eligible_contracts c
              ON c.contract_id = pc.contract_id
            WHERE c.law_policy_scoreable = 1
            """
        )
        con.commit()
    finally:
        con.close()
    return len(rows)


def build(args: argparse.Namespace) -> dict[str, Any]:
    contracts = load_contracts(args.db)
    fred_by_contract = fred_receipts(args.fred_vintage_repair)
    rows = [classify_row(row, fred_by_contract=fred_by_contract) for row in contracts]
    dataset_rows = [row for row in rows if row.get("dataset_source")]
    return {
        "schema": "gp245-dataset-label-time-gate-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": repo_relative(args.db),
        "fred_vintage_repair": repo_relative(args.fred_vintage_repair),
        "summary": summarize(rows),
        "policy": {
            "law_policy_gate": (
                "A resolved dataset-source row is eligible for source-currency or "
                "calibration-policy evidence only when a source-specific as-of/vintage "
                "receipt supports the scored label."
            ),
            "non_claims": [
                "not a model-call result",
                "DB mutation only when explicitly run with --ingest-db",
                "not an ALFRED confirmation",
                "not a market/human baseline",
            ],
        },
        "rows": dataset_rows,
    }


def render_md(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Dataset Label-Time Gate",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- DB: `{report['db']}`",
        f"- FRED vintage repair: `{report['fred_vintage_repair']}`",
        f"- Verdict: `{s['verdict']}`",
        "",
        "## Summary",
        "",
        f"- Dataset-source rows: `{s['dataset_source_rows']}`",
        f"- Resolved dataset-source rows: `{s['resolved_dataset_source_rows']}`",
        f"- Eligible current-label rows: `{s['eligible_current_label_rows']}`",
        f"- Ineligible current-label rows: `{s['ineligible_current_label_rows']}`",
        f"- Label-time status counts: `{s['label_time_status_counts']}`",
        "",
        "## By Source",
        "",
        "| dataset family | rows | resolved | eligible current-label | ineligible current-label | statuses |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for source, data in s["by_source"].items():
        lines.append(
            f"| `{source}` | {data['rows']} | {data['resolved']} | "
            f"{data['eligible_current_label_rows']} | {data['ineligible_current_label_rows']} | "
            f"`{data['status_counts']}` |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            report["policy"]["law_policy_gate"],
            "",
            "## Non-Claims",
            "",
            *[f"- {claim}" for claim in report["policy"]["non_claims"]],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--fred-vintage-repair", type=Path, default=DEFAULT_FRED_REPAIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--ingest-db",
        action="store_true",
        help="Refresh analytics/public/calibration/forecaster_calibration.db dataset_label_time_gate_rows.",
    )
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "dataset_label_time_gate.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "dataset_label_time_gate.md").write_text(render_md(report), encoding="utf-8")
    with (args.out_dir / "dataset_label_time_gate_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    ingested_rows = ingest_db(args.db, report) if args.ingest_db else 0
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "summary": report["summary"],
                "db_ingested_rows": ingested_rows,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
