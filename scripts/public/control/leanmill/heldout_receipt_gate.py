#!/usr/bin/env python3
"""Validate LeanMill heldout-independence receipts.

This gate is intentionally narrow. It does not ratify proof value; it only
checks that a proposed validated-family heldout receipt carries the minimum
independence and governance evidence needed before registry promotion logic can
consider it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VALID_OUTCOMES = {"closure", "exact_gap", "valid_falsifier"}
ALLOWED_GOVERNANCE_WORKER_CLASSES = {"governance", "governance_gate"}
ALLOWED_GOVERNANCE_WORKER_IDS = {
    "leanmill-governance",
    "leanmill-24x7-local-governance",
    "governance",
}
REQUIRED_BOOL_TRUE = {
    "not_same_row",
    "not_same_target_alias",
    "not_same_source_file",
    "not_used_in_template_design",
    "matched_negative_control_failed",
    "governance_ratified",
}


def _read_report_records(path: str) -> list[dict[str, Any]]:
    p = Path(path).expanduser()
    if not p.exists() or not p.is_file():
        return []
    text = p.read_text(errors="ignore")
    if not text.strip():
        return []
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return rows
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        for key in ("events", "records", "rows", "results"):
            vals = raw.get(key)
            if isinstance(vals, list):
                return [x for x in vals if isinstance(x, dict)]
        return [raw]
    return []


def _record_matches_governance(
    rec: dict[str, Any],
    *,
    family: str,
    heldout_row: str,
    proof_hash: str,
    artifact_hash: str,
) -> bool:
    rec_family = str(rec.get("family") or rec.get("repair_family") or rec.get("lane") or "")
    rec_row = str(rec.get("heldout_row") or rec.get("row_id") or rec.get("row") or "")
    if rec_family and rec_family != family:
        return False
    if rec_row and rec_row != heldout_row:
        return False
    status = str(rec.get("status") or rec.get("decision") or rec.get("event") or rec.get("event_type") or "")
    ratified = status in {"governance_ratified", "ratified_closure", "ratified", "pass"} or rec.get("governance_ratified") is True
    if not ratified:
        return False
    # Defense in depth: validate_receipt already requires a non-empty proof or
    # artifact hash for proof-value outcomes (lines 148-151 below), but this
    # helper is also reachable from other call sites in the future, so refuse
    # the match if no hash was provided to compare against.
    expected_hash = proof_hash or artifact_hash
    rec_hashes = {
        str(rec.get("proof_replay_hash") or ""),
        str(rec.get("artifact_hash") or ""),
        str(rec.get("outcome_hash") or ""),
        str(rec.get("sha256") or ""),
    }
    if not expected_hash:
        # Cannot match without a hash to compare. Refuse rather than accept-by-default.
        return False
    if expected_hash not in rec_hashes:
        return False
    return True


def _read_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {"_malformed_json": True}


def validate_receipt(obj: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if obj.get("_malformed_json"):
        return [{"failure": "malformed_json"}]
    if obj.get("schema") != "leanmill-heldout-receipt-v1":
        failures.append({"failure": "wrong_schema", "expected": "leanmill-heldout-receipt-v1"})
    family = str(obj.get("family") or "")
    heldout_row = str(obj.get("heldout_row") or "")
    if not family:
        failures.append({"failure": "missing_family"})
    if not heldout_row:
        failures.append({"failure": "missing_heldout_row"})

    design_rows = obj.get("template_design_rows")
    if not isinstance(design_rows, list) or not all(isinstance(x, str) and x for x in design_rows):
        failures.append({"failure": "template_design_rows_must_be_nonempty_string_list"})
    elif heldout_row in set(design_rows):
        failures.append({"failure": "heldout_row_in_template_design_rows", "heldout_row": heldout_row})

    evidence = obj.get("evidence")
    if not isinstance(evidence, dict):
        failures.append({"failure": "missing_evidence"})
        evidence = {}
    for key in sorted(REQUIRED_BOOL_TRUE):
        if evidence.get(key) is not True:
            failures.append({"failure": "required_evidence_not_true", "field": f"evidence.{key}"})

    if "outcome" in obj and "expected_outcome" not in obj:
        failures.append({"failure": "outcome_without_expected_outcome"})
    if "outcome" in obj and "expected_outcome" in obj and obj.get("outcome") != obj.get("expected_outcome"):
        failures.append({"failure": "inconsistent_outcome_keys"})
    outcome = str(obj.get("expected_outcome") or "")
    if outcome not in VALID_OUTCOMES:
        failures.append({"failure": "invalid_expected_outcome", "expected": sorted(VALID_OUTCOMES)})

    artifacts = obj.get("artifacts")
    if not isinstance(artifacts, dict):
        failures.append({"failure": "missing_artifacts"})
        artifacts = {}
    proof_hash = str(artifacts.get("proof_replay_hash") or "")
    outcome_hash = str(artifacts.get("artifact_hash") or "")
    governance_report = str(artifacts.get("governance_report") or "")
    if outcome == "closure" and not proof_hash:
        failures.append({"failure": "closure_requires_proof_replay_hash"})
    if not proof_hash and not outcome_hash:
        failures.append({"failure": "missing_artifact_hash"})
    if not governance_report:
        failures.append({"failure": "missing_governance_report"})
    else:
        report_records = _read_report_records(governance_report)
        if not report_records:
            failures.append({"failure": "governance_report_missing_or_unreadable", "path": governance_report})
        elif not any(_record_matches_governance(
            rec,
            family=family,
            heldout_row=heldout_row,
            proof_hash=proof_hash,
            artifact_hash=outcome_hash,
        ) for rec in report_records):
            failures.append({"failure": "governance_report_missing_matching_ratification", "path": governance_report})

    credit = obj.get("credit")
    if not isinstance(credit, dict):
        failures.append({"failure": "missing_credit_boundary"})
        credit = {}
    for key in ("source_credit_eligible", "clean_solver_credit_eligible", "repair_canary_credit_eligible"):
        if key not in credit or not isinstance(credit.get(key), bool):
            failures.append({"failure": "credit_boundary_not_explicit_bool", "field": f"credit.{key}"})
    if isinstance(credit, dict):
        true_credit = [key for key in ("source_credit_eligible", "clean_solver_credit_eligible", "repair_canary_credit_eligible") if credit.get(key) is True]
        if len(true_credit) != 1:
            failures.append({"failure": "credit_boundary_must_have_exactly_one_true", "true_fields": true_credit})

    worker_class = str(obj.get("produced_by_worker_class") or "")
    worker_id = str(obj.get("produced_by_worker_id") or "")
    if worker_class not in ALLOWED_GOVERNANCE_WORKER_CLASSES and worker_id not in ALLOWED_GOVERNANCE_WORKER_IDS:
        failures.append({
            "failure": "receipt_not_produced_by_allowed_governance_worker",
            "produced_by_worker_class": worker_class,
            "produced_by_worker_id": worker_id,
        })

    return failures


def build(args: argparse.Namespace) -> dict[str, Any]:
    obj = _read_json(args.receipt)
    failures = validate_receipt(obj)
    payload = {
        "schema": "leanmill-heldout-receipt-gate-v1",
        "receipt": args.receipt,
        "family": obj.get("family"),
        "heldout_row": obj.get("heldout_row"),
        "failure_count": len(failures),
        "failures": failures,
        "status": "pass" if not failures else "fail",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    import tempfile

    good = {
        "schema": "leanmill-heldout-receipt-v1",
        "family": "fam",
        "heldout_row": "r3",
        "template_design_rows": ["r1", "r2"],
        "expected_outcome": "closure",
        "evidence": {
            "not_same_row": True,
            "not_same_target_alias": True,
            "not_same_source_file": True,
            "not_used_in_template_design": True,
            "matched_negative_control_failed": True,
            "governance_ratified": True,
        },
        "artifacts": {
            "proof_replay_hash": "abc123",
            "governance_report": "/tmp/report.json",
        },
        "credit": {
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "repair_canary_credit_eligible": True,
        },
    }
    bad = {**good, "heldout_row": "r1"}
    with tempfile.TemporaryDirectory() as td:
        report = Path(td) / "governance_report.json"
        report.write_text(json.dumps({
            "event_type": "governance_ratified",
            "family": "fam",
            "heldout_row": "r3",
            "proof_replay_hash": "abc123",
        }) + "\n")
        gp = Path(td) / "good.json"
        bp = Path(td) / "bad.json"
        good["artifacts"]["governance_report"] = str(report)
        good["produced_by_worker_class"] = "governance"
        good["produced_by_worker_id"] = "leanmill-governance"
        gp.write_text(json.dumps(good) + "\n")
        bp.write_text(json.dumps(bad) + "\n")
        assert build(argparse.Namespace(receipt=str(gp), out=None))["status"] == "pass"
        assert build(argparse.Namespace(receipt=str(bp), out=None))["status"] == "fail"
    print("leanmill_heldout_receipt_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", default="")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.receipt:
        raise SystemExit("--receipt is required unless --self-test is used")
    payload = build(args)
    print(json.dumps({
        "status": payload["status"],
        "failure_count": payload["failure_count"],
        "family": payload.get("family"),
        "heldout_row": payload.get("heldout_row"),
        "out": args.out,
    }, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
