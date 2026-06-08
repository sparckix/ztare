#!/usr/bin/env python3
"""Review Polymarket Law 3 cutoff candidates before DB ingest.

No DB mutation. This consumes the public-CLOB acquisition manifest and emits a
quality review plus an ingest-preview contract-row packet. Rows are candidates
until manual resolution-source review clears them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_MANIFEST = WORKSPACE / "cutoff_polymarket_pre_cutoff_candidate_manifest.jsonl"
DEFAULT_OUT = WORKSPACE


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def normalize_question(question: str | None) -> str:
    text = " ".join((question or "").lower().strip().split())
    keep = [ch for ch in text if ch.isalnum() or ch.isspace()]
    return " ".join("".join(keep).split())


def event_core_id(question: str | None) -> str:
    return hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()[:16]


def existing_db_surface(db: Path) -> dict[str, set[str]]:
    con = sqlite3.connect(db)
    try:
        rows = list(con.execute("SELECT contract_id, question FROM contracts"))
    finally:
        con.close()
    return {
        "contract_ids": {str(row[0]) for row in rows if row[0]},
        "event_cores": {event_core_id(str(row[1] or "")) for row in rows if row[1]},
    }


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def review_flags(row: dict[str, Any], event_counts: Counter[str], db_surface: dict[str, set[str]]) -> list[str]:
    flags: list[str] = []
    contract_id = str(row.get("contract_id") or "")
    event_slug = str(row.get("event_slug") or row.get("slug") or "")
    history_status = str(row.get("history_status") or "")
    freeze_value = as_float(row.get("freeze_datetime_value"))
    y_known = row.get("y_known")
    history_ts = row.get("freeze_history_timestamp")

    if contract_id in db_surface["contract_ids"]:
        flags.append("contract_id_already_in_db")
    if event_core_id(str(row.get("question") or "")) in db_surface["event_cores"]:
        flags.append("normalized_question_already_in_db")
    if event_slug and event_counts[event_slug] > 1:
        flags.append("sibling_event_family_duplicate")
    if not row.get("resolution_source_url"):
        flags.append("missing_resolution_source_url")
    if history_status != "history_nearest_at_or_before_target":
        flags.append("unexpected_history_status")
    if freeze_value is None or not (0.0 <= freeze_value <= 1.0):
        flags.append("invalid_freeze_probability")
    if y_known not in (0, 1):
        flags.append("invalid_y_known")
    if history_ts in (None, ""):
        flags.append("missing_history_timestamp")
    if row.get("cutoff_relation") != "pre_cutoff":
        flags.append("not_pre_cutoff")
    if row.get("source") != "polymarket":
        flags.append("not_polymarket")
    if not row.get("yes_token_id"):
        flags.append("missing_yes_token_id")
    return flags


def manual_required(flags: list[str]) -> bool:
    return any(
        flag
        in {
            "missing_resolution_source_url",
            "sibling_event_family_duplicate",
            "contract_id_already_in_db",
            "normalized_question_already_in_db",
            "unexpected_history_status",
            "invalid_freeze_probability",
            "invalid_y_known",
            "not_pre_cutoff",
            "not_polymarket",
        }
        for flag in flags
    )


def contract_row(row: dict[str, Any], flags: list[str]) -> dict[str, Any]:
    raw_payload = {
        "schema": "gp245-polymarket-pre-cutoff-contract-row-preview-v1",
        "source_currency_receipt": row.get("source_currency_receipt"),
        "freeze_datetime": row.get("freeze_datetime"),
        "freeze_datetime_value": row.get("freeze_datetime_value"),
        "freeze_history_timestamp": row.get("freeze_history_timestamp"),
        "freeze_days_before_resolution": row.get("freeze_days_before_resolution"),
        "yes_token_id": row.get("yes_token_id"),
        "history_status": row.get("history_status"),
        "event_slug": row.get("event_slug"),
        "event_title": row.get("event_title"),
        "review_flags": flags,
        "raw_market": row.get("raw_market"),
    }
    return {
        "contract_id": row.get("contract_id"),
        "question": row.get("question"),
        "source": "polymarket",
        "source_corpus": "law3_cutoff_acquisition_polymarket_public_clob_2026_06_02",
        "horizon": f"resolved-by-{row.get('resolution_date')}",
        "y_known": row.get("y_known"),
        "post_training_cutoff": 0,
        "task_type": "polymarket_binary",
        "external_market_open": None,
        "resolution_source_url": row.get("resolution_source_url") or row.get("url"),
        "y_known_provenance": "polymarket_final_outcome_prices_public_gamma",
        "raw_json": raw_payload,
    }


def build_report(manifest: Path, db: Path) -> dict[str, Any]:
    rows = read_jsonl(manifest)
    db_surface = existing_db_surface(db)
    event_counts = Counter(str(row.get("event_slug") or row.get("slug") or "") for row in rows)
    reviewed: list[dict[str, Any]] = []
    contract_rows: list[dict[str, Any]] = []
    flag_counts: Counter[str] = Counter()
    by_cell: Counter[str] = Counter()
    by_event: Counter[str] = Counter()
    for row in rows:
        flags = review_flags(row, event_counts, db_surface)
        flag_counts.update(flags)
        cell = f"{row.get('source')} | {row.get('freeze_value_band')} | {row.get('question_length_band')}"
        by_cell[cell] += 1
        event_slug = str(row.get("event_slug") or row.get("slug") or "")
        by_event[event_slug] += 1
        status = "manual_review_required" if manual_required(flags) else "auto_clear"
        reviewed.append(
            {
                "contract_id": row.get("contract_id"),
                "question": row.get("question"),
                "url": row.get("url"),
                "event_slug": event_slug,
                "freeze_datetime": row.get("freeze_datetime"),
                "freeze_datetime_value": row.get("freeze_datetime_value"),
                "freeze_value_band": row.get("freeze_value_band"),
                "resolution_date": row.get("resolution_date"),
                "y_known": row.get("y_known"),
                "flags": flags,
                "review_status": status,
            }
        )
        contract_rows.append(contract_row(row, flags))

    manual_rows = [row for row in reviewed if row["review_status"] == "manual_review_required"]
    auto_clear_rows = [row for row in reviewed if row["review_status"] == "auto_clear"]
    return {
        "schema": "gp245-polymarket-candidate-review-v1",
        "manifest": repo_rel(manifest),
        "db": repo_rel(db),
        "candidate_rows": len(rows),
        "auto_clear_rows": len(auto_clear_rows),
        "manual_review_rows": len(manual_rows),
        "ready_for_db_ingest": len(rows) > 0 and not manual_rows,
        "selected_by_cell": dict(sorted(by_cell.items())),
        "unique_event_families": len(by_event),
        "event_family_counts": dict(by_event.most_common()),
        "flag_counts": dict(sorted(flag_counts.items())),
        "reviewed_candidates": reviewed,
        "contract_rows": contract_rows,
        "interpretation": (
            "This is an ingest preview, not a DB write. Rows with "
            "missing_resolution_source_url need manual resolution-source review; "
            "sibling_event_family_duplicate rows need dependence annotation or capping "
            "before they are used as a broad second-source replication."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Polymarket Candidate Review / Ingest Preview",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Candidate rows: {report['candidate_rows']}",
        f"- Auto-clear rows: {report['auto_clear_rows']}",
        f"- Manual-review rows: {report['manual_review_rows']}",
        f"- Ready for DB ingest: `{report['ready_for_db_ingest']}`",
        f"- Unique event families: {report['unique_event_families']}",
        "",
        "## Selected By Cell",
        "",
        "```json",
        json.dumps(report["selected_by_cell"], indent=2, sort_keys=True),
        "```",
        "",
        "## Flag Counts",
        "",
        "```json",
        json.dumps(report["flag_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Event Families",
        "",
        "```json",
        json.dumps(report["event_family_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Manual Review Rows",
        "",
    ]
    for row in report["reviewed_candidates"]:
        if row["review_status"] != "manual_review_required":
            continue
        lines.append(
            f"- `{row['contract_id']}` `{row['freeze_value_band']}` "
            f"`{row['event_slug']}` flags={','.join(row['flags'])}: {row['question']}"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_polymarket_candidate_review_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "cutoff_polymarket_candidate_review_report.md").write_text(
        render_md(report),
        encoding="utf-8",
    )
    with (out_dir / "cutoff_polymarket_candidate_ingest_contract_rows.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in report["contract_rows"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = build_report(args.manifest, args.db)
    write_outputs(report, args.out_dir)
    print(json.dumps({k: report[k] for k in (
        "candidate_rows",
        "auto_clear_rows",
        "manual_review_rows",
        "ready_for_db_ingest",
        "flag_counts",
        "unique_event_families",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
