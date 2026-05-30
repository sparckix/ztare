"""Deterministic checks for compact orchestration contracts.

The orchestration menu is an action-program compiler surface. This gate checks
that a compact contract does not ask the RD agent to execute a class/action
sequence that contradicts the accepted class, program counter, outside handoff,
or scoped stop condition. It does not decide whether the underlying research
claim is true.
"""
from __future__ import annotations

from typing import Any


KNOWN_CLASS_FIRST_ACTIONS = {
    "paid_narrow_boundary": "proceed",
    "claim_boundary_split": "build_boundary_artifact",
    "missing_source_holdout": "collect_source_evidence",
    "production_shadow_missing": "open_shadow_log",
    "external_audit_missing": "request_external_audit",
    "tool_depth_missing": "run_tool_depth_loop",
    "outside_menu": "defer_to_new_residual_class",
}

ALLOWED_ACTIONS = {
    "proceed",
    "build_boundary_artifact",
    "collect_source_evidence",
    "open_shadow_log",
    "request_external_audit",
    "run_tool_depth_loop",
    "require_preventive_receipt",
    "defer_to_new_residual_class",
    "stop_or_repair",
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _words(value: Any) -> set[str]:
    return {
        word
        for word in str(value or "").lower().replace("_", " ").replace("-", " ").split()
        if len(word) > 3
    }


def _action_program(contract: dict[str, Any]) -> list[str]:
    program = contract.get("action_program") or contract.get("orchestration_action_program") or []
    if isinstance(program, str):
        return [_norm(part) for part in program.split(",") if part.strip()]
    if not isinstance(program, list):
        return []
    return [_norm(item) for item in program]


def validate_orchestration_contract(
    contract: dict[str, Any],
    *,
    source_facts: str | None = None,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate program-order and stop-condition invariants.

    ``expected`` is optional and should be supplied by replay tests, shadow logs,
    or deterministic source-cue compilers when a gold/accepted target is known.
    Runtime RD use can still catch internal contradictions without it.
    """
    expected = expected or {}
    accepted_class = _norm(
        contract.get("accepted_residual_class")
        or contract.get("orchestration_accepted_residual_class")
    )
    requested_class = _norm(
        contract.get("requested_residual_class")
        or contract.get("orchestration_requested_residual_class")
    )
    required_action = _norm(
        contract.get("required_next_action")
        or contract.get("orchestration_required_next_action")
    )
    program = _action_program(contract)
    first_action = program[0] if program else ""
    expected_first = KNOWN_CLASS_FIRST_ACTIONS.get(accepted_class)

    violations: list[dict[str, Any]] = []

    if accepted_class not in KNOWN_CLASS_FIRST_ACTIONS:
        violations.append({"type": "unknown_accepted_residual_class", "value": accepted_class})
    if requested_class and accepted_class and requested_class != accepted_class:
        # This is not always fatal; accepted class may repair requested class.
        if not contract.get("wrong_contract_repair_or_refusal"):
            violations.append({
                "type": "requested_accepted_class_mismatch_without_repair_receipt",
                "requested": requested_class,
                "accepted": accepted_class,
            })
    if required_action not in ALLOWED_ACTIONS:
        violations.append({"type": "unknown_required_next_action", "value": required_action})
    if program and first_action != required_action:
        violations.append({
            "type": "program_order_required_action_mismatch",
            "program_first_action": first_action,
            "required_next_action": required_action,
        })
    if expected_first and required_action and expected_first != required_action:
        violations.append({
            "type": "deterministic_lowering_action_mismatch",
            "accepted_residual_class": accepted_class,
            "expected_first_action": expected_first,
            "required_next_action": required_action,
        })

    lowering = str(
        contract.get("deterministic_lowering_result")
        or contract.get("orchestration_deterministic_lowering_result")
        or ""
    )
    lowering_words = _words(lowering)
    if lowering and accepted_class:
        accepted_words = _words(accepted_class)
        required_words = _words(required_action)
        if not accepted_words <= lowering_words or not required_words <= lowering_words:
            violations.append({
                "type": "deterministic_lowering_receipt_mismatch",
                "deterministic_lowering_result": lowering,
            })

    if accepted_class == "outside_menu":
        outside = str(
            contract.get("specific_outside_residual_class")
            or contract.get("orchestration_specific_outside_residual_class")
            or contract.get("new_residual_class_candidate")
            or ""
        ).strip()
        if not outside:
            violations.append({"type": "missing_specific_outside_residual_class"})

    stop_condition = str(
        contract.get("stop_condition")
        or contract.get("orchestration_stop_condition_check")
        or ""
    )
    if accepted_class == "paid_narrow_boundary":
        stop_l = stop_condition.lower()
        if "all" in stop_l and "only" not in stop_l:
            violations.append({
                "type": "stop_condition_overblocks_paid_scope",
                "stop_condition": stop_condition,
            })

    if source_facts:
        source_words = _words(source_facts)
        source_text = str(source_facts or "").lower().replace("-", " ")
        cues = contract.get("source_cue_receipts") or contract.get("orchestration_source_cue_receipts") or []
        if isinstance(cues, str):
            cues = [cues]
        for cue in cues:
            cue_text = str(cue or "").lower().replace("-", " ")
            cue_words = _words(cue)
            negated_anchor = any(
                (f"no {word}" in source_text or f"not {word}" in source_text)
                and f"no {word}" not in cue_text
                and f"not {word}" not in cue_text
                for word in cue_words
            )
            if cue_words and (not cue_words.intersection(source_words) or negated_anchor):
                violations.append({
                    "type": "source_cue_not_anchored",
                    "cue": cue,
                })

    expected_class = _norm(expected.get("accepted_residual_class") or expected.get("residual_class"))
    expected_action = _norm(expected.get("required_next_action") or expected.get("action"))
    expected_outside = _norm(expected.get("specific_outside_residual_class") or expected.get("handoff"))
    expected_stop = str(expected.get("stop_condition") or "")
    if expected_class and accepted_class != expected_class:
        violations.append({
            "type": "accepted_class_mismatch",
            "expected": expected_class,
            "actual": accepted_class,
        })
    if expected_action and required_action != expected_action:
        violations.append({
            "type": "expected_required_action_mismatch",
            "expected": expected_action,
            "actual": required_action,
        })
    if expected_outside and accepted_class == "outside_menu":
        actual_outside = _norm(
            contract.get("specific_outside_residual_class")
            or contract.get("orchestration_specific_outside_residual_class")
            or contract.get("new_residual_class_candidate")
        )
        if actual_outside != expected_outside:
            violations.append({
                "type": "outside_handoff_mismatch",
                "expected": expected_outside,
                "actual": actual_outside,
            })
    if expected_stop:
        stop_words = _words(stop_condition)
        expected_stop_words = _words(expected_stop)
        if expected_stop_words and not expected_stop_words.intersection(stop_words):
            violations.append({
                "type": "stop_condition_scope_mismatch",
                "expected": expected_stop,
                "actual": stop_condition,
            })

    return {
        "passed": not violations,
        "accepted_residual_class": accepted_class,
        "required_next_action": required_action,
        "action_program": program,
        "violations": violations,
    }


def _read_json(path: str) -> dict[str, Any]:
    import json
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate compact orchestration contract invariants."
    )
    parser.add_argument("contract_json", help="Path to contract JSON, or - for stdin")
    parser.add_argument("--source-facts", default="", help="Optional source facts text")
    parser.add_argument("--source-facts-file", help="Optional file containing source facts")
    parser.add_argument("--expected-json", help="Optional expected fields JSON path")
    args = parser.parse_args(argv)

    source_facts = args.source_facts
    if args.source_facts_file:
        with open(args.source_facts_file, encoding="utf-8") as f:
            source_facts = f.read()
    expected = _read_json(args.expected_json) if args.expected_json else None
    result = validate_orchestration_contract(
        _read_json(args.contract_json),
        source_facts=source_facts or None,
        expected=expected,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
