"""Trace recorder for boundary-card repair loops.

H52 showed that rejected boundary cards can be repaired safely on the H26/H48
packet when the repair worker sees only source facts, the rejected card, and
non-oracle gate results. This module validates/appends those repair-loop traces
for live measurement. It does not approve execution by itself.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
DEFAULT_LOG = REPO / "analytics" / "public" / "queries" / "rd" / "boundary_card_repair_trace.jsonl"

CORE_REQUIRED_FIELDS = {
    "trace_id",
    "created_at_utc",
    "substrate",
    "source_ref",
    "source_observation",
    "rejected_card",
    "pre_repair_gate_result",
    "rejection_basis",
    "repair_prompt",
    "raw_repair_output",
    "repaired_card",
    "post_repair_gate_result",
    "downstream_status",
}

RESOLVED_DOWNSTREAM_FIELDS = {
    "executed_action",
    "terminal_action",
    "false_proceed",
    "false_stop",
    "paid_boundary_overwork",
    "episode_cost",
    "downstream_score_ref",
}

VALID_DOWNSTREAM_STATUS = {"pending", "scored", "unavailable"}
VALID_REJECTION_BASIS = {"non_oracle_gate_rejection", "scoring_rejection", "operator_rejection", "mixed"}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def new_repair_trace(**fields: Any) -> dict[str, Any]:
    trace = dict(fields)
    trace.setdefault("created_at_utc", datetime.now(UTC).isoformat())
    trace.setdefault("schema_version", "boundary_card_repair_trace_v1")
    trace.setdefault("downstream_status", "pending")
    return trace


def _is_object(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def validate_repair_trace(trace: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for field in sorted(CORE_REQUIRED_FIELDS):
        value = trace.get(field)
        if field in {"rejected_card", "pre_repair_gate_result", "repaired_card", "post_repair_gate_result"}:
            if not _is_object(value):
                violations.append({"type": "missing_or_invalid_required_object", "field": field})
        elif not _norm(value):
            violations.append({"type": "missing_required_field", "field": field})

    pre_gate = trace.get("pre_repair_gate_result") if isinstance(trace.get("pre_repair_gate_result"), dict) else {}
    post_gate = trace.get("post_repair_gate_result") if isinstance(trace.get("post_repair_gate_result"), dict) else {}
    rejection_basis = _norm(trace.get("rejection_basis")).lower()
    if rejection_basis and rejection_basis not in VALID_REJECTION_BASIS:
        violations.append({"type": "invalid_rejection_basis", "value": rejection_basis})
    if rejection_basis == "non_oracle_gate_rejection" and pre_gate.get("passed") is True:
        violations.append({"type": "non_oracle_rejection_basis_but_pre_gate_passed"})
    if post_gate.get("passed") is not True:
        violations.append({"type": "post_repair_gate_did_not_pass"})

    status = _norm(trace.get("downstream_status")).lower()
    if status and status not in VALID_DOWNSTREAM_STATUS:
        violations.append({"type": "invalid_downstream_status", "value": status})
    if status == "scored":
        for field in sorted(RESOLVED_DOWNSTREAM_FIELDS):
            if field not in trace or trace.get(field) in (None, ""):
                violations.append({"type": "scored_trace_missing_downstream_field", "field": field})

    return {
        "passed": not violations,
        "schema_version": trace.get("schema_version", "boundary_card_repair_trace_v1"),
        "violations": violations,
    }


def append_repair_trace(trace: dict[str, Any], path: Path = DEFAULT_LOG) -> dict[str, Any]:
    result = validate_repair_trace(trace)
    if not result["passed"]:
        return result
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, sort_keys=True) + "\n")
    return {**result, "path": str(path)}


def _read_json(path: str) -> dict[str, Any]:
    import sys
    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Validate or append a boundary-card repair trace JSON.")
    parser.add_argument("trace_json", help="Path to trace JSON, or - for stdin")
    parser.add_argument("--append", action="store_true", help="Append to JSONL after validation")
    parser.add_argument("--out", default=str(DEFAULT_LOG), help="JSONL output path for --append")
    args = parser.parse_args(argv)
    trace = _read_json(args.trace_json)
    result = append_repair_trace(trace, Path(args.out)) if args.append else validate_repair_trace(trace)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
