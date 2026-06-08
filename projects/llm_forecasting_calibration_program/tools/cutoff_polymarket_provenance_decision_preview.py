#!/usr/bin/env python3
"""Apply manual Polymarket provenance decisions without mutating the DB.

This consumes the manual provenance packet and an optional reviewer-decision
JSONL file. It emits a blank decision template plus an ingest preview containing
only accepted rows. A later DB write should consume the accepted-row JSONL, not
the raw acquisition manifest.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
WORKSPACE = PROGRAM / "cutoff_validity_v1/workspace"
DEFAULT_PACKET = WORKSPACE / "cutoff_polymarket_manual_provenance_packet.json"
DEFAULT_DECISIONS = WORKSPACE / "cutoff_polymarket_manual_provenance_decisions.jsonl"
DEFAULT_OUT = WORKSPACE
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
ACCEPTED_FLAG_ALLOWLIST = {"gamma_resolution_source_field_blank"}


def resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (REPO / path).resolve()


def repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def valid_review_time(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def decision_template(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "gp245-polymarket-manual-provenance-decision-v1",
        "contract_id": row.get("contract_id"),
        "accept_for_db_ingest": None,
        "reviewer": "",
        "reviewed_at": "",
        "resolution_source_url": "",
        "resolution_source_note": "",
        "y_known_confirmed": None,
        "reject_reason": "",
    }


def index_decisions(decisions: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    indexed: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []
    for decision in decisions:
        contract_id = str(decision.get("contract_id") or "")
        if not contract_id:
            continue
        if contract_id in indexed:
            duplicates.append(contract_id)
        indexed[contract_id] = decision
    return indexed, sorted(set(duplicates))


def validate_decision(
    row: dict[str, Any],
    decision: dict[str, Any] | None,
    *,
    duplicate_decisions: set[str],
) -> tuple[str, list[str]]:
    contract_id = str(row.get("contract_id") or "")
    if decision is None:
        return "missing_decision", ["missing_decision"]
    errors: list[str] = []
    if contract_id in duplicate_decisions:
        errors.append("duplicate_decision")
    accept = decision.get("accept_for_db_ingest")
    if accept is True:
        if not str(decision.get("reviewer") or "").strip():
            errors.append("missing_reviewer")
        if not valid_review_time(decision.get("reviewed_at")):
            errors.append("invalid_or_missing_reviewed_at")
        if not (
            str(decision.get("resolution_source_url") or "").strip()
            or str(decision.get("resolution_source_note") or "").strip()
        ):
            errors.append("missing_resolution_source_url_or_note")
        if decision.get("y_known_confirmed") != row.get("y_known"):
            errors.append("y_known_confirmation_mismatch")
        unallowed_flags = sorted(set(row.get("flags") or []) - ACCEPTED_FLAG_ALLOWLIST)
        if unallowed_flags:
            errors.append("unresolved_flags:" + ",".join(unallowed_flags))
        return ("invalid_accept" if errors else "accept", errors)
    if accept is False:
        if not str(decision.get("reject_reason") or "").strip():
            errors.append("missing_reject_reason")
        return ("invalid_reject" if errors else "reject", errors)
    return "invalid_decision", ["accept_for_db_ingest_must_be_true_or_false"]


def contract_row(row: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    raw_payload = {
        "schema": "gp245-polymarket-reviewed-contract-row-preview-v1",
        "source_currency_receipt": row.get("source_currency_receipt"),
        "freeze_datetime": row.get("freeze_datetime"),
        "freeze_datetime_value": row.get("freeze_datetime_value"),
        "freeze_history_timestamp": row.get("freeze_history_timestamp"),
        "history_status": row.get("history_status"),
        "event_slug": row.get("event_slug"),
        "event_title": row.get("event_title"),
        "final_yes_probability": row.get("final_yes_probability"),
        "uma_resolution_status": row.get("uma_resolution_status"),
        "uma_end_date": row.get("uma_end_date"),
        "polymarket_url": row.get("polymarket_url"),
        "provenance_decision": decision,
        "original_flags": row.get("flags") or [],
    }
    source_url = (
        str(decision.get("resolution_source_url") or "").strip()
        or str(row.get("polymarket_url") or "")
    )
    return {
        "contract_id": row.get("contract_id"),
        "question": row.get("question"),
        "source": "polymarket",
        "source_corpus": "law3_cutoff_acquisition_polymarket_public_clob_reviewed_2026_06_02",
        "horizon": f"resolved-by-{row.get('resolution_date')}",
        "y_known": row.get("y_known"),
        "post_training_cutoff": 0,
        "task_type": "polymarket_binary",
        "external_market_open": None,
        "resolution_source_url": source_url,
        "y_known_provenance": "polymarket_final_outcome_prices_public_gamma_reviewed",
        "raw_json": raw_payload,
    }


def insert_contracts(db: Path, rows: list[dict[str, Any]]) -> dict[str, int]:
    con = sqlite3.connect(db)
    inserted = 0
    skipped_existing = 0
    try:
        for row in rows:
            exists = con.execute(
                "SELECT 1 FROM contracts WHERE contract_id = ?",
                (row["contract_id"],),
            ).fetchone()
            if exists:
                skipped_existing += 1
                continue
            con.execute(
                """
                INSERT INTO contracts
                  (contract_id, question, source, source_corpus, horizon, y_known,
                   post_training_cutoff, task_type, external_market_open,
                   resolution_source_url, y_known_provenance, raw_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["contract_id"],
                    row["question"],
                    row["source"],
                    row["source_corpus"],
                    row["horizon"],
                    row["y_known"],
                    row["post_training_cutoff"],
                    row["task_type"],
                    row["external_market_open"],
                    row["resolution_source_url"],
                    row["y_known_provenance"],
                    json.dumps(row["raw_json"], sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            inserted += 1
        con.commit()
    finally:
        con.close()
    return {"inserted": inserted, "skipped_existing": skipped_existing}


def platform_accept_decision(row: dict[str, Any], reviewer: str, reviewed_at: str) -> dict[str, Any]:
    return {
        "schema": "gp245-polymarket-manual-provenance-decision-v1",
        "contract_id": row.get("contract_id"),
        "accept_for_db_ingest": True,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "resolution_source_url": row.get("polymarket_url") or "",
        "resolution_source_note": (
            "platform_resolver_only: public Polymarket Gamma payload has blank "
            "structured resolutionSource, but the market page URL is present, "
            "resolution criteria text is embedded in the payload, UMA status is "
            "resolved, and final Yes/No outcome price matches y_known. This is "
            "not independent external-source verification."
        ),
        "y_known_confirmed": row.get("y_known"),
        "reject_reason": "",
    }


def should_platform_accept(row: dict[str, Any]) -> bool:
    flags = set(row.get("flags") or [])
    if flags - ACCEPTED_FLAG_ALLOWLIST:
        return False
    if not row.get("polymarket_url"):
        return False
    if not str(row.get("resolution_criteria_text") or "").strip():
        return False
    if str(row.get("uma_resolution_status") or "").lower() != "resolved":
        return False
    final_yes = row.get("final_yes_probability")
    if final_yes is None or row.get("y_known") not in (0, 1):
        return False
    return int(row["y_known"]) == int(round(float(final_yes)))


def write_platform_accept_decisions(packet: dict[str, Any], decisions_path: Path, reviewer: str) -> dict[str, Any]:
    rows = packet.get("reviewed_candidates") or []
    reviewed_at = datetime.now(timezone.utc).isoformat()
    accepted = [platform_accept_decision(row, reviewer, reviewed_at) for row in rows if should_platform_accept(row)]
    rejected = [
        {
            "schema": "gp245-polymarket-manual-provenance-decision-v1",
            "contract_id": row.get("contract_id"),
            "accept_for_db_ingest": False,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "resolution_source_url": "",
            "resolution_source_note": "",
            "y_known_confirmed": None,
            "reject_reason": "auto_platform_accept_conditions_failed",
        }
        for row in rows
        if not should_platform_accept(row)
    ]
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    with decisions_path.open("w", encoding="utf-8") as f:
        for decision in [*accepted, *rejected]:
            f.write(json.dumps(decision, sort_keys=True) + "\n")
    return {
        "accepted_decisions_written": len(accepted),
        "rejected_decisions_written": len(rejected),
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "decisions_path": repo_rel(decisions_path),
    }


def build_preview(packet_path: Path, decisions_path: Path) -> dict[str, Any]:
    packet = read_json(packet_path)
    rows = packet.get("reviewed_candidates") or []
    decisions_list = read_jsonl(decisions_path)
    decisions, duplicates = index_decisions(decisions_list)
    duplicate_set = set(duplicates)
    decision_rows: list[dict[str, Any]] = []
    accepted_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    for row in rows:
        contract_id = str(row.get("contract_id") or "")
        decision = decisions.get(contract_id)
        status, errors = validate_decision(row, decision, duplicate_decisions=duplicate_set)
        status_counts[status] += 1
        error_counts.update(errors)
        if status == "accept" and decision:
            accepted_rows.append(contract_row(row, decision))
        decision_rows.append(
            {
                "contract_id": contract_id,
                "question": row.get("question"),
                "status": status,
                "errors": errors,
                "decision": decision,
                "flags": row.get("flags") or [],
            }
        )
    invalid_rows = sum(status_counts[name] for name in ("invalid_accept", "invalid_reject", "invalid_decision"))
    missing_rows = int(status_counts.get("missing_decision", 0))
    rejected_rows = int(status_counts.get("reject", 0))
    accepted_count = int(status_counts.get("accept", 0))
    return {
        "schema": "gp245-polymarket-provenance-decision-preview-v1",
        "packet": repo_rel(packet_path),
        "decisions": repo_rel(decisions_path),
        "candidate_rows": len(rows),
        "decision_rows_supplied": len(decisions_list),
        "accepted_rows": accepted_count,
        "rejected_rows": rejected_rows,
        "missing_decision_rows": missing_rows,
        "invalid_decision_rows": invalid_rows,
        "duplicate_decision_contract_ids": duplicates,
        "status_counts": dict(sorted(status_counts.items())),
        "error_counts": dict(sorted(error_counts.items())),
        "ready_for_partial_db_ingest": accepted_count > 0 and invalid_rows == 0,
        "ready_for_full_slice_db_ingest": (
            len(rows) > 0 and accepted_count == len(rows) and invalid_rows == 0 and missing_rows == 0
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_templates": [decision_template(row) for row in rows],
        "decision_reviews": decision_rows,
        "contract_rows": accepted_rows,
        "interpretation": (
            "This is a no-write preview. Full-slice DB ingest is allowed only "
            "when every candidate has a valid accept decision. Partial ingest "
            "can be used for accepted rows but does not complete the 33-row "
            "Polymarket slice."
        ),
    }


def render_md(preview: dict[str, Any]) -> str:
    lines = [
        "# Polymarket Provenance Decision Preview",
        "",
        f"- Schema: `{preview['schema']}`",
        f"- Candidate rows: {preview['candidate_rows']}",
        f"- Decision rows supplied: {preview['decision_rows_supplied']}",
        f"- Accepted rows: {preview['accepted_rows']}",
        f"- Rejected rows: {preview['rejected_rows']}",
        f"- Missing decisions: {preview['missing_decision_rows']}",
        f"- Invalid decisions: {preview['invalid_decision_rows']}",
        f"- Ready for partial DB ingest: `{preview['ready_for_partial_db_ingest']}`",
        f"- Ready for full-slice DB ingest: `{preview['ready_for_full_slice_db_ingest']}`",
        "",
        "## Status Counts",
        "",
        "```json",
        json.dumps(preview["status_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Error Counts",
        "",
        "```json",
        json.dumps(preview["error_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Rows Needing Attention",
        "",
    ]
    attention = [
        row for row in preview["decision_reviews"]
        if row["status"] not in {"accept", "reject"}
    ]
    if not attention:
        lines.append("- None.")
    for row in attention:
        lines.append(
            f"- `{row['contract_id']}` status=`{row['status']}` "
            f"errors=`{','.join(row['errors'])}`: {row['question']}"
        )
    lines.extend(["", "## Interpretation", "", preview["interpretation"], ""])
    return "\n".join(lines)


def write_outputs(preview: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_polymarket_provenance_decision_preview.json").write_text(
        json.dumps(preview, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "cutoff_polymarket_provenance_decision_preview.md").write_text(
        render_md(preview),
        encoding="utf-8",
    )
    with (out_dir / "cutoff_polymarket_reviewed_contract_rows.jsonl").open("w", encoding="utf-8") as f:
        for row in preview["contract_rows"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    with (out_dir / "cutoff_polymarket_manual_provenance_decision_template.jsonl").open("w", encoding="utf-8") as f:
        for row in preview["decision_templates"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument(
        "--auto-accept-platform-provenance",
        action="store_true",
        help=(
            "Write bounded platform-resolver decisions before previewing. "
            "This accepts only rows whose criteria text, Polymarket URL, UMA "
            "resolved status, and final outcome price are internally consistent."
        ),
    )
    parser.add_argument("--reviewer", default="codex_rd_platform_provenance_review")
    args = parser.parse_args()
    packet_path = resolve_path(args.packet)
    decisions_path = resolve_path(args.decisions)
    auto_result = None
    if args.auto_accept_platform_provenance:
        auto_result = write_platform_accept_decisions(read_json(packet_path), decisions_path, args.reviewer)
    preview = build_preview(packet_path, decisions_path)
    if auto_result is not None:
        preview["auto_platform_accept_result"] = auto_result
    if args.write_db:
        if not preview.get("ready_for_full_slice_db_ingest"):
            raise SystemExit("Refusing --write-db: preview is not ready for full-slice DB ingest")
        preview["write_db_result"] = insert_contracts(resolve_path(args.db), preview["contract_rows"])
    print(json.dumps(preview, indent=2, sort_keys=True))
    write_outputs(preview, resolve_path(args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
