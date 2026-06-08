#!/usr/bin/env python3
"""Materialize computed source-currency receipts for forecast calls.

No model calls. DB ingestion is opt-in via ``--ingest-db``.

This is the reusable DB-facing companion to the F100 source-currency audit:
it computes resolution-date-vs-model-cutoff relation with the shared
``classify_forecast_source_currency`` primitive and stores the resulting
receipt separately from the stale-prone ``contracts.post_training_cutoff``
flag.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.research_director.source_currency_discriminator import (
    classify_forecast_source_currency,
)


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = WORKSPACE / "source_currency_gate_2026_06_05"
DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")

STRICT_RESOLVE_DATE_KEYS = (
    "resolve_date",
    "resolve_time",
    "resolution_date",
    "resolution_date_filled",
    "close_time",
    "close_date",
    "resolved_at",
    "resolution_fetched_at",
    "horizon",
)
MODEL_CUTOFF_KEYS = (
    "panel_cutoff_date",
    "model_cutoff_date",
    "training_cutoff_date",
    "knowledge_cutoff_date",
)


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO))
    except ValueError:
        return str(path)


def parse_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def parse_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    match = DATE_RE.search(str(value))
    if not match:
        return None
    y, m, d = map(int, match.groups())
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def first_date_with_source(*items: tuple[str, Any]) -> tuple[str | None, str | None]:
    for source, value in items:
        parsed = parse_iso_date(value)
        if parsed:
            return parsed, source
    return None, None


def load_call_rows(db: Path, pilot_id: str | None) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    where = "WHERE pc.pilot_id = ?" if pilot_id else ""
    params: tuple[Any, ...] = (pilot_id,) if pilot_id else ()
    try:
        rows = [
            dict(row)
            for row in con.execute(
                f"""
                SELECT pc.call_id, pc.pilot_id, pc.contract_id, pc.agent_id,
                       pc.family, pc.condition, pc.primitive, pc.primitive_base,
                       pc.phase, pc.role, pc.p_success, pc.brier, pc.schema_ok,
                       pc.parsed_json AS call_parsed_json,
                       pc.raw_json AS call_raw_json,
                       c.question, c.source, c.source_corpus, c.horizon,
                       c.y_known, c.post_training_cutoff, c.task_type,
                       c.raw_json AS contract_raw_json
                FROM pilot_calls pc
                JOIN contracts c ON c.contract_id = pc.contract_id
                {where}
                ORDER BY pc.pilot_id, pc.call_id
                """,
                params,
            )
        ]
    finally:
        con.close()
    return rows


def receipt_for_row(row: dict[str, Any], *, default_model_cutoff_date: str | None) -> dict[str, Any]:
    call_raw = parse_json(row.get("call_raw_json"))
    call_parsed = parse_json(row.get("call_parsed_json"))
    contract_raw = parse_json(row.get("contract_raw_json"))

    resolve_items: list[tuple[str, Any]] = []
    for key in STRICT_RESOLVE_DATE_KEYS:
        resolve_items.extend(
            [
                (f"pilot_calls.raw_json.{key}", call_raw.get(key)),
                (f"pilot_calls.parsed_json.{key}", call_parsed.get(key)),
                (f"contracts.raw_json.{key}", contract_raw.get(key)),
            ]
        )
    resolve_items.append(("contracts.horizon", row.get("horizon")))

    cutoff_items: list[tuple[str, Any]] = []
    for key in MODEL_CUTOFF_KEYS:
        cutoff_items.extend(
            [
                (f"pilot_calls.raw_json.{key}", call_raw.get(key)),
                (f"pilot_calls.parsed_json.{key}", call_parsed.get(key)),
                (f"contracts.raw_json.{key}", contract_raw.get(key)),
            ]
        )
    cutoff_items.append(("--default-model-cutoff-date", default_model_cutoff_date))

    resolve_date, resolve_date_provenance = first_date_with_source(*resolve_items)
    model_cutoff_date, model_cutoff_date_provenance = first_date_with_source(*cutoff_items)
    receipt = classify_forecast_source_currency(
        resolve_date=resolve_date,
        model_cutoff_date=model_cutoff_date,
        stored_post_training_cutoff=row.get("post_training_cutoff"),
        prefer_computed_cutoff=bool(resolve_date and model_cutoff_date),
    )
    receipt["resolve_date"] = resolve_date
    receipt["resolve_date_provenance"] = resolve_date_provenance
    receipt["model_cutoff_date"] = model_cutoff_date
    receipt["model_cutoff_date_provenance"] = model_cutoff_date_provenance
    return receipt


def materialize_row(row: dict[str, Any], *, default_model_cutoff_date: str | None) -> dict[str, Any]:
    receipt = receipt_for_row(row, default_model_cutoff_date=default_model_cutoff_date)
    return {
        "call_id": int(row["call_id"]),
        "pilot_id": row.get("pilot_id"),
        "contract_id": row.get("contract_id"),
        "agent_id": row.get("agent_id"),
        "family": row.get("family"),
        "source": row.get("source"),
        "source_corpus": row.get("source_corpus"),
        "task_type": row.get("task_type"),
        "schema_ok": row.get("schema_ok"),
        "p_success": row.get("p_success"),
        "brier": row.get("brier"),
        "y_known": row.get("y_known"),
        "post_training_cutoff": row.get("post_training_cutoff"),
        "cutoff_relation": receipt["cutoff_relation"],
        "cutoff_relation_provenance": receipt["provenance"],
        "stored_cutoff_relation": receipt.get("stored_cutoff_relation"),
        "computed_cutoff_relation": receipt.get("computed_cutoff_relation"),
        "cutoff_relation_conflict": bool(receipt["cutoff_relation_conflict"]),
        "resolve_date": receipt.get("resolve_date"),
        "resolve_date_provenance": receipt.get("resolve_date_provenance"),
        "model_cutoff_date": receipt.get("model_cutoff_date"),
        "model_cutoff_date_provenance": receipt.get("model_cutoff_date_provenance"),
        "source_currency_receipt": receipt,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    computed = [row for row in rows if row.get("computed_cutoff_relation")]
    conflicts = [row for row in rows if row.get("cutoff_relation_conflict")]
    policy_scoreable = [
        row for row in rows if row.get("schema_ok") == 1 and row.get("p_success") is not None and row.get("y_known") in (0, 1)
    ]
    return {
        "call_rows": len(rows),
        "computed_relation_rows": len(computed),
        "missing_computed_relation_rows": len(rows) - len(computed),
        "cutoff_relation_conflicts": len(conflicts),
        "policy_scoreable_call_rows": len(policy_scoreable),
        "policy_scoreable_conflicts": sum(1 for row in policy_scoreable if row.get("cutoff_relation_conflict")),
        "cutoff_relation_counts": dict(sorted(Counter(str(row.get("cutoff_relation")) for row in rows).items())),
        "cutoff_relation_provenance_counts": dict(
            sorted(Counter(str(row.get("cutoff_relation_provenance")) for row in rows).items())
        ),
        "stored_cutoff_relation_counts": dict(
            sorted(Counter(str(row.get("stored_cutoff_relation") or "missing") for row in rows).items())
        ),
        "computed_cutoff_relation_counts": dict(
            sorted(Counter(str(row.get("computed_cutoff_relation") or "missing") for row in rows).items())
        ),
        "verdict": (
            "stored_cutoff_flags_conflict_with_computed_source_currency"
            if conflicts
            else "no_stored_computed_cutoff_conflicts_detected"
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


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ingest_db(db: Path, report: dict[str, Any]) -> int:
    generated_at = str(report["generated_at"])
    rows = report["rows"]
    con = sqlite3.connect(db)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS source_currency_gate_rows (
                call_id INTEGER PRIMARY KEY,
                pilot_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                agent_id TEXT,
                family TEXT,
                source TEXT,
                source_corpus TEXT,
                task_type TEXT,
                schema_ok INTEGER,
                p_success REAL,
                brier REAL,
                y_known INTEGER,
                post_training_cutoff INTEGER,
                cutoff_relation TEXT NOT NULL,
                cutoff_relation_provenance TEXT NOT NULL,
                stored_cutoff_relation TEXT,
                computed_cutoff_relation TEXT,
                cutoff_relation_conflict INTEGER NOT NULL,
                resolve_date TEXT,
                resolve_date_provenance TEXT,
                model_cutoff_date TEXT,
                model_cutoff_date_provenance TEXT,
                generated_at TEXT NOT NULL,
                source_currency_receipt TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                FOREIGN KEY (call_id) REFERENCES pilot_calls(call_id),
                FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
            )
            """
        )
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_currency_gate_pilot
            ON source_currency_gate_rows(pilot_id, cutoff_relation)
            """
        )
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_currency_gate_conflict
            ON source_currency_gate_rows(cutoff_relation_conflict, pilot_id)
            """
        )
        con.execute("DELETE FROM source_currency_gate_rows")
        con.executemany(
            """
            INSERT INTO source_currency_gate_rows (
                call_id, pilot_id, contract_id, agent_id, family, source,
                source_corpus, task_type, schema_ok, p_success, brier, y_known,
                post_training_cutoff, cutoff_relation, cutoff_relation_provenance,
                stored_cutoff_relation, computed_cutoff_relation,
                cutoff_relation_conflict, resolve_date, resolve_date_provenance,
                model_cutoff_date, model_cutoff_date_provenance, generated_at,
                source_currency_receipt, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    int(row["call_id"]),
                    str(row["pilot_id"]),
                    str(row["contract_id"]),
                    row.get("agent_id"),
                    row.get("family"),
                    row.get("source"),
                    row.get("source_corpus"),
                    row.get("task_type"),
                    optional_int(row.get("schema_ok")),
                    optional_float(row.get("p_success")),
                    optional_float(row.get("brier")),
                    optional_int(row.get("y_known")),
                    optional_int(row.get("post_training_cutoff")),
                    str(row["cutoff_relation"]),
                    str(row["cutoff_relation_provenance"]),
                    row.get("stored_cutoff_relation"),
                    row.get("computed_cutoff_relation"),
                    int(bool(row.get("cutoff_relation_conflict"))),
                    row.get("resolve_date"),
                    row.get("resolve_date_provenance"),
                    row.get("model_cutoff_date"),
                    row.get("model_cutoff_date_provenance"),
                    generated_at,
                    json.dumps(row["source_currency_receipt"], sort_keys=True),
                    json.dumps(row, sort_keys=True),
                )
                for row in rows
            ],
        )
        con.execute("DROP VIEW IF EXISTS v_source_currency_gate_conflicts")
        con.execute(
            """
            CREATE VIEW v_source_currency_gate_conflicts AS
            SELECT *
            FROM source_currency_gate_rows
            WHERE cutoff_relation_conflict = 1
            """
        )
        con.execute("DROP VIEW IF EXISTS v_policy_scoreable_calls_source_currency")
        con.execute(
            """
            CREATE VIEW v_policy_scoreable_calls_source_currency AS
            SELECT
                pc.*,
                g.cutoff_relation,
                g.cutoff_relation_provenance,
                g.stored_cutoff_relation,
                g.computed_cutoff_relation,
                g.cutoff_relation_conflict,
                g.resolve_date,
                g.resolve_date_provenance,
                g.model_cutoff_date,
                g.model_cutoff_date_provenance,
                g.source_currency_receipt
            FROM v_policy_scoreable_calls pc
            LEFT JOIN source_currency_gate_rows g
              ON g.call_id = pc.call_id
            """
        )
        con.commit()
    finally:
        con.close()
    return len(rows)


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = [
        materialize_row(row, default_model_cutoff_date=args.default_model_cutoff_date)
        for row in load_call_rows(args.db, args.pilot_id)
    ]
    return {
        "schema": "gp245-source-currency-gate-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": repo_relative(args.db),
        "pilot_id": args.pilot_id,
        "default_model_cutoff_date": args.default_model_cutoff_date,
        "summary": summarize(rows),
        "policy": {
            "law_policy_gate": (
                "When computed resolution-date-vs-model-cutoff relation is present, "
                "policy/science audits should consume it with its receipt instead of "
                "contracts.post_training_cutoff."
            ),
            "non_claims": [
                "not a model-call result",
                "DB mutation only when explicitly run with --ingest-db",
                "not a label-time/as-of receipt",
                "not a correction to contracts.post_training_cutoff",
            ],
        },
        "rows": rows,
    }


def render_md(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Source-Currency Gate",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- DB: `{report['db']}`",
        f"- Pilot filter: `{report['pilot_id'] or 'all'}`",
        f"- Default model cutoff date: `{report['default_model_cutoff_date'] or 'none'}`",
        f"- Verdict: `{s['verdict']}`",
        "",
        "## Summary",
        "",
        f"- Call rows: `{s['call_rows']}`",
        f"- Computed relation rows: `{s['computed_relation_rows']}`",
        f"- Missing computed relation rows: `{s['missing_computed_relation_rows']}`",
        f"- Stored/computed cutoff conflicts: `{s['cutoff_relation_conflicts']}`",
        f"- Policy-scoreable call rows: `{s['policy_scoreable_call_rows']}`",
        f"- Policy-scoreable conflicts: `{s['policy_scoreable_conflicts']}`",
        f"- Cutoff relation counts: `{s['cutoff_relation_counts']}`",
        f"- Cutoff relation provenance counts: `{s['cutoff_relation_provenance_counts']}`",
        f"- Stored relation counts: `{s['stored_cutoff_relation_counts']}`",
        f"- Computed relation counts: `{s['computed_cutoff_relation_counts']}`",
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
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pilot-id", default=None, help="Optional pilot_calls.pilot_id filter.")
    parser.add_argument(
        "--default-model-cutoff-date",
        default=None,
        help="Optional fallback cutoff date when rows lack a panel/model cutoff receipt.",
    )
    parser.add_argument(
        "--ingest-db",
        action="store_true",
        help="Refresh analytics/public/calibration/forecaster_calibration.db source_currency_gate_rows.",
    )
    args = parser.parse_args()
    report = build(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "source_currency_gate.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "source_currency_gate.md").write_text(render_md(report), encoding="utf-8")
    with (args.out_dir / "source_currency_gate_rows.jsonl").open("w", encoding="utf-8") as fh:
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
