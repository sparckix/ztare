"""Shadow logging contract for orchestration-menu decisions.

H47 showed that outside-specific class expansion is not safe to enforce until
we can measure pre-decision drift/refusal and later outcomes. This module is a
small schema validator and JSONL appender for those non-blocking shadow events.
It records what the orchestration compiler would have done; it does not change
RD decisions.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
DEFAULT_LOG = REPO / "analytics" / "public" / "queries" / "rd" / "orchestration_shadow_log.jsonl"

CORE_REQUIRED_FIELDS = {
    "shadow_event_id",
    "created_at_utc",
    "substrate",
    "source_trace_ref",
    "decision_context_id",
    "pre_decision_state_ref",
    "candidate_action",
    "proposed_known_residual_class",
    "selected_residual_edge",
    "rejected_nearest_confuser_edge",
    "source_cue_check_status",
    "accepted_residual_class",
    "outside_menu_flag",
    "specific_outside_residual_class",
    "action_program",
    "required_next_action",
    "program_counter_rule",
    "program_invariant_passed",
    "later_outcome_status",
}

RESOLVED_OUTCOME_FIELDS = {
    "executed_action",
    "final_disposition",
    "later_outcome_ref",
    "later_outcome_label",
    "outcome_observed_at",
    "cost_or_regret_signal",
}

VALID_CHECK_RESULTS = {"pass", "fail", "not_run", "unknown"}
VALID_BOOLISH = {"true", "false", "pass", "fail", "not_run", "unknown"}
VALID_OUTCOME_STATUS = {"pending", "resolved", "unavailable"}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def new_shadow_event(**fields: Any) -> dict[str, Any]:
    """Create a minimally-populated shadow event dictionary.

    Callers may pass additional fields; this helper only fills stable defaults.
    """
    event = dict(fields)
    event.setdefault("created_at_utc", datetime.now(UTC).isoformat())
    event.setdefault("later_outcome_status", "pending")
    event.setdefault("schema_version", "orchestration_shadow_v1")
    return event


def validate_shadow_event(event: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    for field in sorted(CORE_REQUIRED_FIELDS):
        if not _norm(event.get(field)):
            violations.append({"type": "missing_required_field", "field": field})

    source_cue = _norm(event.get("source_cue_check_status")).lower()
    invariant = _norm(event.get("program_invariant_passed")).lower()
    outcome_status = _norm(event.get("later_outcome_status")).lower()
    if source_cue and source_cue not in VALID_CHECK_RESULTS:
        violations.append({"type": "invalid_source_cue_check_result", "value": source_cue})
    if invariant and invariant not in VALID_BOOLISH:
        violations.append({"type": "invalid_program_invariant_passed", "value": invariant})
    if outcome_status and outcome_status not in VALID_OUTCOME_STATUS:
        violations.append({"type": "invalid_later_outcome_status", "value": outcome_status})
    if outcome_status == "resolved":
        for field in sorted(RESOLVED_OUTCOME_FIELDS):
            if not _norm(event.get(field)):
                violations.append({"type": "resolved_event_missing_outcome_field", "field": field})

    outside_flag = _norm(event.get("outside_menu_flag")).lower()
    if outside_flag in {"true", "yes", "1", "outside_menu"} and not _norm(event.get("specific_outside_residual_class")):
        violations.append({"type": "outside_menu_missing_specific_outside_residual_class"})

    return {
        "passed": not violations,
        "schema_version": event.get("schema_version", "orchestration_shadow_v1"),
        "violations": violations,
    }


def append_shadow_event(event: dict[str, Any], path: Path = DEFAULT_LOG) -> dict[str, Any]:
    result = validate_shadow_event(event)
    if not result["passed"]:
        return result
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
    return {**result, "path": str(path)}


def _read_json(path: str) -> dict[str, Any]:
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate or append orchestration shadow-log event JSON.")
    parser.add_argument("event_json", help="Path to event JSON, or - for stdin")
    parser.add_argument("--append", action="store_true", help="Append to JSONL after validation")
    parser.add_argument("--out", default=str(DEFAULT_LOG), help="JSONL output path for --append")
    args = parser.parse_args(argv)

    event = _read_json(args.event_json)
    result = append_shadow_event(event, Path(args.out)) if args.append else validate_shadow_event(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
