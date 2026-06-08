#!/usr/bin/env python3
"""Build or apply a DB ingest plan for reviewed Law 3 cutoff candidates."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_ACQUISITION = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_manifold_acquisition_report.json"
DEFAULT_REVIEW = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_candidate_review_report.json"
DEFAULT_OUT = PROGRAM_ROOT / "cutoff_validity_v1/workspace"

CRITICAL_FLAGS = {
    "platform_self_reference",
    "general_bucket_contains_political_cue",
    "general_bucket_contains_finance_cue",
    "trivial_calendar",
    "invalid_bettor_count",
    "invalid_volume",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def existing_contract_ids(db: Path) -> set[str]:
    con = sqlite3.connect(db)
    try:
        return {str(row[0]) for row in con.execute("SELECT contract_id FROM contracts")}
    finally:
        con.close()


def contract_row(candidate: dict[str, Any]) -> dict[str, Any]:
    raw = {
        "contract_id": candidate.get("contract_id"),
        "question": candidate.get("question"),
        "source": candidate.get("source"),
        "source_corpus": candidate.get("source_corpus"),
        "task_type": candidate.get("task_type"),
        "resolution_date": candidate.get("strict_resolve_date"),
        "strict_resolve_date": candidate.get("strict_resolve_date"),
        "computed_cutoff_relation": candidate.get("computed_cutoff_relation"),
        "panel_cutoff_date": candidate.get("panel_cutoff_date"),
        "post_training_cutoff": 0,
        "cutoff_relation": "pre_cutoff",
        "y_known": candidate.get("y_known"),
        "y_known_provenance": "manifold_dump_20240706_resolution",
        "acquisition_id": candidate.get("acquisition_id"),
        "target_key": candidate.get("target_key"),
        "event_core_id": candidate.get("event_core_id"),
        "raw_manifold": candidate.get("raw_manifold") or {},
    }
    return {
        "contract_id": candidate.get("contract_id"),
        "question": candidate.get("question"),
        "source": candidate.get("source"),
        "source_corpus": candidate.get("source_corpus"),
        "horizon": f"resolved-by-{candidate.get('strict_resolve_date')}",
        "y_known": candidate.get("y_known"),
        "post_training_cutoff": 0,
        "task_type": candidate.get("task_type"),
        "external_market_open": None,
        "resolution_source_url": (candidate.get("raw_manifold") or {}).get("url"),
        "y_known_provenance": "manifold_dump_20240706_resolution",
        "raw_json": raw,
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


def build_plan(acquisition_path: Path, review_path: Path, db: Path) -> dict[str, Any]:
    acquisition = read_json(acquisition_path)
    review = read_json(review_path)
    selected = {row.get("acquisition_id"): row for row in acquisition.get("selected_candidates") or []}
    reviewed = review.get("reviewed_candidates") or []
    existing = existing_contract_ids(db)
    decisions: list[dict[str, Any]] = []
    accepted_contract_rows: list[dict[str, Any]] = []
    by_target: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    for row in reviewed:
        acq_id = row.get("acquisition_id")
        candidate = selected.get(acq_id)
        flags = list(row.get("flags") or [])
        critical = sorted(set(flags) & CRITICAL_FLAGS)
        if not candidate:
            decision = "reject_missing_candidate"
            reason = "review row has no selected candidate payload"
        elif critical:
            decision = "reject_critical_flags"
            reason = "critical review flags: " + ",".join(critical)
        elif candidate.get("contract_id") in existing:
            decision = "skip_existing_contract"
            reason = "contract_id already exists in DB"
        elif flags:
            decision = "accept_with_advisory_flags"
            reason = "advisory flags only: " + ",".join(flags)
        else:
            decision = "accept"
            reason = "no review flags"
        decision_counts[decision] += 1
        if decision.startswith("accept") and candidate:
            by_target[str(candidate.get("target_key"))] += 1
            accepted_contract_rows.append(contract_row(candidate))
        decisions.append(
            {
                "acquisition_id": acq_id,
                "contract_id": row.get("contract_id"),
                "target_key": row.get("target_key"),
                "decision": decision,
                "reason": reason,
                "flags": flags,
                "question": row.get("question"),
            }
        )
    return {
        "schema": "gp245-cutoff-candidate-ingest-preview-v1",
        "db": str(db),
        "acquisition_report": str(acquisition_path),
        "review_report": str(review_path),
        "selected_rows": len(selected),
        "reviewed_rows": len(reviewed),
        "accepted_rows": len(accepted_contract_rows),
        "rejected_rows": sum(1 for row in decisions if row["decision"].startswith("reject")),
        "skipped_existing_rows": decision_counts.get("skip_existing_contract", 0),
        "ready_for_db_ingest": (
            len(accepted_contract_rows) == len(selected)
            and len(selected) > 0
            and not any(row["decision"].startswith("reject") for row in decisions)
        ),
        "decision_counts": dict(sorted(decision_counts.items())),
        "accepted_by_target_key": dict(sorted(by_target.items())),
        "decisions": decisions,
        "contract_rows": accepted_contract_rows,
        "interpretation": (
            "This preview accepts advisory-only flags but refuses critical flags. "
            "It writes no DB rows unless --write-db is provided."
        ),
    }


def write_outputs(plan: dict[str, Any], out_dir: Path, *, write_result: dict[str, int] | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if write_result is not None:
        plan = {**plan, "write_db_result": write_result}
    (out_dir / "cutoff_candidate_ingest_preview.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "cutoff_candidate_ingest_contract_rows.jsonl").open("w", encoding="utf-8") as f:
        for row in plan.get("contract_rows") or []:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Cutoff Candidate Ingest Preview",
        "",
        f"- Schema: `{plan['schema']}`",
        f"- Selected rows: {plan['selected_rows']}",
        f"- Reviewed rows: {plan['reviewed_rows']}",
        f"- Accepted rows: {plan['accepted_rows']}",
        f"- Rejected rows: {plan['rejected_rows']}",
        f"- Skipped existing rows: {plan['skipped_existing_rows']}",
        f"- Ready for DB ingest: `{plan['ready_for_db_ingest']}`",
    ]
    if write_result is not None:
        lines.append(f"- DB inserted: `{write_result['inserted']}`")
        lines.append(f"- DB skipped existing: `{write_result['skipped_existing']}`")
    lines.extend(["", "## Decision Counts", ""])
    for decision, n in plan["decision_counts"].items():
        lines.append(f"- `{decision}`: {n}")
    lines.extend(["", "## Decisions", ""])
    for row in plan["decisions"]:
        lines.append(
            f"- `{row['acquisition_id']}` `{row['target_key']}` "
            f"`{row['decision']}`: {row['reason']}"
        )
    lines.extend(["", "## Interpretation", "", plan["interpretation"], ""])
    (out_dir / "cutoff_candidate_ingest_preview.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition", type=Path, default=DEFAULT_ACQUISITION)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--write-db", action="store_true")
    args = parser.parse_args()
    plan = build_plan(args.acquisition, args.review, args.db)
    write_result = None
    if args.write_db:
        if not plan["ready_for_db_ingest"]:
            raise SystemExit("refusing DB write: preview is not ready_for_db_ingest")
        write_result = insert_contracts(args.db, plan["contract_rows"])
    print(json.dumps({k: v for k, v in plan.items() if k != "contract_rows"}, indent=2, sort_keys=True))
    write_outputs(plan, args.out_dir, write_result=write_result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
