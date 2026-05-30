"""Bounded LeanMill learning-feedback contracts.

Probe and governance outcomes are useful only when they change downstream
behavior without becoming proof credit. This module is the narrow contract
surface for that loop: normalize probe exits, distinguish malformed negative
controls from matched negative evidence, and build capped feedback entries for
worker prompts and factory intelligence.
"""
from __future__ import annotations

from typing import Any


SCHEMA = "leanmill-learning-feedback-v1"
FAILURE_EVIDENCE_KEYS = (
    "row_id",
    "candidate",
    "action_family",
    "driver_path",
    "body_tail",
    "stdout_tail",
    "stderr_tail",
    "repl_error_tail",
    "error_class",
)

NONUSEFUL_PROBE_EXITS = {
    "tested_no_positive_signal",
    "negative_control_unexpected_pass",
    "invalid_negative_control",
    "canary_probe_no_positive_signal",
    "stale_family_spec_probe_packet",
}

NEGATIVE_CONTROL_INVALID_FAILURE_MARKERS = (
    "Invalid `",
    "unexpected token",
    "unknown identifier",
    "invalid field notation",
    "application type mismatch",
    "failed to synthesize",
)

PROOF_VALUE_EXIT_KINDS = {
    "ratified_closure",
    "exact_gap_candidate",
    "valid_falsifier",
}

TESTED_LEARNING_EXIT_KINDS = {
    "compile_candidate_needs_governance",
    "tested_no_positive_signal",
    "tested_probe_no_signal",
}

TERMINAL_DECISION_EXIT_KINDS = {
    "failed_negative_control",
    "invalid_negative_control",
    "probe_failed",
    "probe_finished_no_tests",
    "retired",
    "tested_hold",
    "stale_family_spec_probe_packet",
}


def int_count(obj: dict[str, Any], key: str) -> int:
    try:
        return int(obj.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def learning_exit_from_counts(payload: dict[str, Any], *, returncode: int = 0) -> str:
    """Return the canonical LeanMill learning-unit exit for a probe payload."""
    if returncode != 0:
        return "probe_failed"
    if int_count(payload, "negative_control_unexpected_pass_count") > 0:
        return "failed_negative_control"
    if int_count(payload, "negative_control_invalid_fail_count") > 0:
        return "invalid_negative_control"
    if int_count(payload, "ratified_closure_count") > 0:
        return "ratified_closure"
    if int_count(payload, "exact_gap_candidate_count") > 0:
        return "exact_gap_candidate"
    if int_count(payload, "valid_falsifier_count") > 0:
        return "valid_falsifier"
    if int_count(payload, "compile_candidate_count") > 0:
        return "compile_candidate_needs_governance"
    if int_count(payload, "negative_control_fail_count") > 0:
        return "tested_no_positive_signal"
    if int_count(payload, "completed") > 0:
        return "tested_probe_no_signal"
    if str(payload.get("learning_unit_exit") or ""):
        return str(payload["learning_unit_exit"])
    if str(payload.get("learning_exit") or ""):
        return str(payload["learning_exit"])
    if str(payload.get("exit_kind") or ""):
        return str(payload["exit_kind"])
    return "unknown"


def negative_control_invalid_failure(obj: dict[str, Any]) -> bool:
    """True when a negative control failed for parser/elaborator shape reasons."""
    if int_count(obj, "n_closed") or int_count(obj, "n_ratified"):
        return False
    for result in obj.get("results") or []:
        if not isinstance(result, dict):
            continue
        text = "\n".join(str(result.get(k) or "") for k in ("stdout_tail", "stderr_tail"))
        for err in result.get("repl_errors") or []:
            if isinstance(err, dict):
                text += "\n" + str(err.get("data") or "")
        if any(marker in text for marker in NEGATIVE_CONTROL_INVALID_FAILURE_MARKERS):
            return True
    return False


def _tail(value: Any, limit: int) -> str:
    text = str(value or "")
    return text[-limit:] if len(text) > limit else text


def compact_failure_evidence(
    evidence: list[dict[str, Any]] | None,
    *,
    limit: int = 4,
    tail_limit: int = 900,
) -> list[dict[str, Any]]:
    """Keep bounded, non-credit-bearing Lean failure evidence for repair loops."""
    out: list[dict[str, Any]] = []
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        rec: dict[str, Any] = {}
        for key in FAILURE_EVIDENCE_KEYS:
            value = item.get(key)
            if value is None or value == "":
                continue
            rec[key] = _tail(value, tail_limit) if key.endswith("_tail") else str(value)
        if rec:
            out.append(rec)
        if len(out) >= max(0, int(limit)):
            break
    return out


def feedback_entry(
    *,
    source_probe_work_id: str,
    row_id: str,
    exit_kind: str,
    negative_control_invalid_fail_count: int = 0,
    negative_control_fail_count: int = 0,
    negative_control_unexpected_pass_count: int = 0,
    scoreboard: str = "",
    feedback_action: str = "",
    failure_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a compact, non-credit-bearing learning-feedback entry."""
    entry = {
        "schema": SCHEMA,
        "source_probe_work_id": str(source_probe_work_id or ""),
        "row_id": str(row_id or ""),
        "exit_kind": str(exit_kind or ""),
        "negative_control_invalid_fail_count": int(negative_control_invalid_fail_count or 0),
        "negative_control_fail_count": int(negative_control_fail_count or 0),
        "negative_control_unexpected_pass_count": int(negative_control_unexpected_pass_count or 0),
        "scoreboard": str(scoreboard or ""),
        "feedback_action": str(feedback_action or "use as causal feedback only; do not count as proof value"),
        "proof_credit_eligible": False,
    }
    compact = compact_failure_evidence(failure_evidence)
    if compact:
        entry["failure_evidence"] = compact
    return entry


def compact_feedback_entries(entries: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    """Return schema-normalized feedback entries capped for prompt hygiene."""
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        out.append(feedback_entry(
            source_probe_work_id=str(entry.get("source_probe_work_id") or ""),
            row_id=str(entry.get("row_id") or ""),
            exit_kind=str(entry.get("exit_kind") or ""),
            negative_control_invalid_fail_count=int_count(entry, "negative_control_invalid_fail_count"),
            negative_control_fail_count=int_count(entry, "negative_control_fail_count"),
            negative_control_unexpected_pass_count=int_count(entry, "negative_control_unexpected_pass_count"),
            scoreboard=str(entry.get("scoreboard") or ""),
            feedback_action=str(entry.get("feedback_action") or ""),
            failure_evidence=entry.get("failure_evidence") if isinstance(entry.get("failure_evidence"), list) else None,
        ))
        if len(out) >= max(0, int(limit)):
            break
    return out


def _self_test() -> int:
    assert learning_exit_from_counts({"negative_control_invalid_fail_count": 1, "ratified_closure_count": 1}) == "invalid_negative_control"
    assert learning_exit_from_counts({"ratified_closure_count": 1}) == "ratified_closure"
    assert learning_exit_from_counts({"negative_control_fail_count": 1}) == "tested_no_positive_signal"
    assert learning_exit_from_counts({"exit_kind": "stale_family_spec_probe_packet"}) == "stale_family_spec_probe_packet"
    assert negative_control_invalid_failure({"results": [{"stderr_tail": "Invalid `x` notation"}]})
    assert not negative_control_invalid_failure({"n_ratified": 1, "results": [{"stderr_tail": "Invalid `x`"}]})
    entries = compact_feedback_entries([
        {"source_probe_work_id": "p", "row_id": "r", "exit_kind": "invalid_negative_control", "negative_control_invalid_fail_count": "1"},
        {"source_probe_work_id": "q", "row_id": "s", "exit_kind": "tested_no_positive_signal"},
    ], limit=1)
    assert len(entries) == 1
    assert entries[0]["schema"] == SCHEMA
    assert entries[0]["proof_credit_eligible"] is False
    evidenced = compact_feedback_entries([{
        "source_probe_work_id": "p",
        "row_id": "r",
        "exit_kind": "tested_no_positive_signal",
        "failure_evidence": [{"row_id": "r", "stderr_tail": "x" * 1200, "ignored": "drop"}],
    }])
    assert evidenced[0]["failure_evidence"][0]["row_id"] == "r"
    assert len(evidenced[0]["failure_evidence"][0]["stderr_tail"]) == 900
    assert "ignored" not in evidenced[0]["failure_evidence"][0]
    print("ztare.leanmill.contracts.learning_feedback self-test PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
