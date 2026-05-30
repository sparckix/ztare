"""G-CLASSICAL-CHOOSE-BOUND.

General gate for receipts that prove a bound on the exact witness selected by
`Classical.choose` from an existential.  A bounded witness for the same target
is not enough unless the bound is applied to the chosen witness via the
existential's own `choose_spec` equality or an equivalent universal preimage
bound.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-CLASSICAL-CHOOSE-BOUND"

REQUIRED_FIELDS = (
    "target_family",
    "existential_receipt_field",
    "chosen_witness_expression",
    "choose_spec_equality",
    "bound_source",
    "bound_applies_to_chosen_witness",
    "same_target_membership",
    "bounded_existential_not_enough",
    "nearest_confuser",
    "confuser_distinction",
)

WEAK_SUBSTITUTES = (
    "some_bounded_witness_exists",
    "bounded_projection_exists",
    "endpoint_capacity_only",
    "same_target_label_only",
)

HARD_VIOLATIONS = (
    "bound_on_different_witness",
    "choose_spec_not_used",
    "projected_exists_choice_assumed_bounded",
    "bare_existential_bound",
    "post_payoff_choice",
    "target_membership_drift",
)


def _present(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if not text:
            return False
        false_exact_matches = {
            "missing",
            "absent",
            "unknown",
            "todo",
            "owed",
            "unpaid",
            "not supplied",
            "not provided",
            "none",
            "null",
            "false",
            "0",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_classical_choose_bound_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate an exact `Classical.choose` bound receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "classical_choose_bound_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": ["malformed_receipt"],
            "summary": "malformed classical choose-bound receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "classical_choose_bound_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "a choose-bound receipt must identify the existential, the "
                "chosen witness expression, the choose_spec equality, and the "
                "bound source that applies to that exact witness"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "classical_choose_bound_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "existence of a bounded alternate witness or endpoint capacity "
                "does not bound the witness selected by Classical.choose"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "classical_choose_bound_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the receipt bounds a different witness, omits choose_spec, "
                "assumes projected existential choice is bounded, or drifts "
                "target/timing"
            ),
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present
    return {
        "gate_id": GATE_ID,
        "passed": not blocking if enforce_block else True,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "summary": (
            "complete classical choose-bound receipt"
            if complete else
            "incomplete classical choose-bound receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_classical_choose_bound_gate({
        "target_family": "Level536",
        "some_bounded_witness_exists": "there exists an in-prefix event",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["some_bounded_witness_exists"]

    weak_with_strong = run_classical_choose_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "some_bounded_witness_exists": "confuser only",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == [
        "some_bounded_witness_exists"
    ]

    hard = run_classical_choose_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "bound_on_different_witness": "bounded alternate witness",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["complete"] is False
    assert hard["hard_violations_present"] == ["bound_on_different_witness"]

    exact_false = run_classical_choose_bound_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "choose_spec_equality": "missing would be bad, but here documented",
    }, enforce_block=True)
    assert exact_false["passed"] is True
    assert exact_false["missing_fields"] == []


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
        description="Validate an exact Classical.choose bound receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_classical_choose_bound_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
