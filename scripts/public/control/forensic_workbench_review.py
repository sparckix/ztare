#!/usr/bin/env python3
"""Apply a file-backed forensic-workbench review file."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
SCHEMA = "ztare-forensic-workbench-review-v1"
ACTION_SCHEMA = "ztare-forensic-workbench-row-action-v1"
ACTION_CHOICES = {"next_step", "needs_source", "ready_to_run", "export_blocker"}


def row_slug(label: str) -> str:
    return re.sub(r"(^_+|_+$)", "", re.sub(r"[^a-z0-9]+", "_", label.lower())) or "row"


def read_review_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"review file is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("review file must be a JSON object")
    return payload


def case_key(project: str, intake: str) -> str:
    intake_value = str(intake or "").strip()
    return f"{project}::{intake_value}" if intake_value else project


def validate_payload_case(payload: dict[str, Any], *, project: str, intake: str | None) -> list[str]:
    if not intake:
        return []
    errors: list[str] = []
    payload_case_key = str(payload.get("case_key") or "").strip()
    if payload_case_key and payload_case_key != case_key(project, intake):
        errors.append(f"case_key mismatch: expected {case_key(project, intake)!r}, got {payload_case_key!r}")
    payload_intake = str(payload.get("intake") or "").strip()
    if payload_intake and payload_intake != intake:
        errors.append(f"intake mismatch: expected {intake!r}, got {payload_intake!r}")
    return errors


def validate_review_file(payload: dict[str, Any], *, project: str, row: str, intake: str | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if payload.get("project") != project:
        errors.append(f"project mismatch: expected {project!r}, got {payload.get('project')!r}")
    errors.extend(validate_payload_case(payload, project=project, intake=intake))
    review_row = str(payload.get("row") or "")
    if row_slug(review_row) != row:
        errors.append(f"row mismatch: expected slug {row!r}, got row {review_row!r}")
    decision = payload.get("decision")
    if decision not in {"reviewed", "deferred", "blocked"}:
        errors.append("decision must be reviewed, deferred, or blocked")
    evidence_refs = payload.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        errors.append("evidence_refs must be a non-empty list")
    return errors


def validate_action_file(payload: dict[str, Any], *, project: str, row: str, intake: str | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != ACTION_SCHEMA:
        errors.append(f"schema must be {ACTION_SCHEMA}")
    if payload.get("project") != project:
        errors.append(f"project mismatch: expected {project!r}, got {payload.get('project')!r}")
    errors.extend(validate_payload_case(payload, project=project, intake=intake))
    action_row = str(payload.get("row") or "")
    if row_slug(action_row) != row:
        errors.append(f"row mismatch: expected slug {row!r}, got row {action_row!r}")
    if payload.get("action") not in ACTION_CHOICES:
        errors.append("action must be next_step, needs_source, ready_to_run, or export_blocker")
    note = str(payload.get("note") or "").strip()
    if not note:
        errors.append("note must be non-empty")
    evidence_refs = payload.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        errors.append("evidence_refs must be a non-empty list")
    return errors


def validate_project_slug(project: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
        raise ValueError(f"invalid project slug: {project!r}")
    return project


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def add_case_context(receipt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("rubric", "intake", "case_key"):
        value = str(payload.get(key) or "").strip()
        if value:
            receipt[key] = value
    return receipt


def receipt_for_payload(
    payload: dict[str, Any],
    *,
    project: str,
    row: str,
    review_file_bytes: bytes,
    review_file_path: str,
) -> dict[str, Any]:
    errors = validate_review_file(payload, project=project, row=row)
    if errors:
        raise SystemExit("invalid forensic-workbench review file:\n- " + "\n- ".join(errors))
    receipt = {
        "schema": "ztare-forensic-workbench-review-receipt-v1",
        "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project": project,
        "row": payload["row"],
        "row_slug": row,
        "decision": payload["decision"],
        "note": str(payload.get("note") or ""),
        "review_file_path": review_file_path,
        "review_file_sha256": hashlib.sha256(review_file_bytes).hexdigest(),
        "evidence_ref_count": len(payload.get("evidence_refs") or []),
    }
    return add_case_context(receipt, payload)


def write_review_receipt(
    receipt: dict[str, Any],
    *,
    project: str,
    ledger: str | None = None,
    latest: str | None = None,
) -> dict[str, Any]:
    validate_project_slug(project)
    workspace = REPO / "projects" / project / "workspace"
    ledger_path = Path(ledger) if ledger else workspace / "forensic_workbench_reviews.jsonl"
    latest_path = Path(latest) if latest else workspace / "forensic_workbench_latest_review.json"
    if not ledger_path.is_absolute():
        ledger_path = (REPO / ledger_path).resolve()
    if not latest_path.is_absolute():
        latest_path = (REPO / latest_path).resolve()
    append_jsonl(ledger_path, receipt)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "ledger": display_path(ledger_path), "latest": display_path(latest_path), "receipt": receipt}


def receipt_for_action_payload(
    payload: dict[str, Any],
    *,
    project: str,
    row: str,
    action_file_bytes: bytes,
    action_file_path: str,
) -> dict[str, Any]:
    errors = validate_action_file(payload, project=project, row=row)
    if errors:
        raise SystemExit("invalid forensic-workbench row action file:\n- " + "\n- ".join(errors))
    receipt = {
        "schema": "ztare-forensic-workbench-row-action-receipt-v1",
        "applied_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project": project,
        "row": payload["row"],
        "row_slug": row,
        "action": payload["action"],
        "note": str(payload.get("note") or ""),
        "action_file_path": action_file_path,
        "action_file_sha256": hashlib.sha256(action_file_bytes).hexdigest(),
        "evidence_ref_count": len(payload.get("evidence_refs") or []),
    }
    return add_case_context(receipt, payload)


def write_action_receipt(
    receipt: dict[str, Any],
    *,
    project: str,
    ledger: str | None = None,
    latest: str | None = None,
) -> dict[str, Any]:
    validate_project_slug(project)
    workspace = REPO / "projects" / project / "workspace"
    ledger_path = Path(ledger) if ledger else workspace / "forensic_workbench_row_actions.jsonl"
    latest_path = Path(latest) if latest else workspace / "forensic_workbench_latest_row_action.json"
    if not ledger_path.is_absolute():
        ledger_path = (REPO / ledger_path).resolve()
    if not latest_path.is_absolute():
        latest_path = (REPO / latest_path).resolve()
    append_jsonl(ledger_path, receipt)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "ledger": display_path(ledger_path), "latest": display_path(latest_path), "receipt": receipt}


def apply_review_payload(
    payload: dict[str, Any],
    *,
    project: str,
    row: str,
    review_file_path: str,
    ledger: str | None = None,
    latest: str | None = None,
) -> dict[str, Any]:
    validate_project_slug(project)
    review_file_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    receipt = receipt_for_payload(
        payload,
        project=project,
        row=row,
        review_file_bytes=review_file_text.encode("utf-8"),
        review_file_path=review_file_path,
    )
    return write_review_receipt(receipt, project=project, ledger=ledger, latest=latest)


def apply_action_payload(
    payload: dict[str, Any],
    *,
    project: str,
    row: str,
    action_file_path: str,
    ledger: str | None = None,
    latest: str | None = None,
) -> dict[str, Any]:
    validate_project_slug(project)
    action_file_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    receipt = receipt_for_action_payload(
        payload,
        project=project,
        row=row,
        action_file_bytes=action_file_text.encode("utf-8"),
        action_file_path=action_file_path,
    )
    return write_action_receipt(receipt, project=project, ledger=ledger, latest=latest)


def apply_review(args: argparse.Namespace) -> dict[str, Any]:
    validate_project_slug(args.project)
    review_file_path = Path(args.review_file_path)
    if not review_file_path.is_absolute():
        review_file_path = (Path.cwd() / review_file_path).resolve()
    payload = read_review_file(review_file_path)
    receipt = receipt_for_payload(
        payload,
        project=args.project,
        row=args.row,
        review_file_bytes=review_file_path.read_bytes(),
        review_file_path=str(review_file_path),
    )
    return write_review_receipt(receipt, project=args.project, ledger=args.ledger, latest=args.latest)


def save_action(args: argparse.Namespace) -> dict[str, Any]:
    validate_project_slug(args.project)
    action_file_path = Path(args.action_file_path)
    if not action_file_path.is_absolute():
        action_file_path = (Path.cwd() / action_file_path).resolve()
    payload = read_review_file(action_file_path)
    receipt = receipt_for_action_payload(
        payload,
        project=args.project,
        row=args.row,
        action_file_bytes=action_file_path.read_bytes(),
        action_file_path=str(action_file_path),
    )
    return write_action_receipt(receipt, project=args.project, ledger=args.ledger, latest=args.latest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project slug under projects/.")
    parser.add_argument("--row", required=True, help="Slug for the reviewed row, e.g. report_export.")
    parser.add_argument("--from", dest="review_file_path", required=True, help="Review file JSON saved from the workbench.")
    parser.add_argument("--ledger", help="Optional JSONL ledger override, mainly for tests.")
    parser.add_argument("--latest", help="Optional latest-receipt JSON override, mainly for tests.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Output is JSON by default.")
    return parser


def build_action_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply a file-backed forensic-workbench row action file.")
    parser.add_argument("--project", required=True, help="Project slug under projects/.")
    parser.add_argument("--row", required=True, help="Slug for the acted-on row, e.g. report_export.")
    parser.add_argument("--from", dest="action_file_path", required=True, help="Row action JSON saved from the workbench.")
    parser.add_argument("--ledger", help="Optional JSONL ledger override, mainly for tests.")
    parser.add_argument("--latest", help="Optional latest-action JSON override, mainly for tests.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Output is JSON by default.")
    return parser


def action_main(argv: list[str] | None = None) -> int:
    parser = build_action_parser()
    args = parser.parse_args(argv)
    try:
        result = save_action(args)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"forensic workbench row action failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = apply_review(args)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"forensic workbench review failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
