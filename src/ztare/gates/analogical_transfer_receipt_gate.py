"""G-ANALOGICAL-TRANSFER-RECEIPT.

General-purpose gate for using analogies as research operators.  The gate does
not judge whether the analogy is mathematically true.  It forces the analogy to
be converted into a concrete target receipt/check and rejects vocabulary-only
pattern transfer.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-ANALOGICAL-TRANSFER-RECEIPT"

REQUIRED_FIELDS = (
    "donor_domain",
    "donor_pattern",
    "donor_invariant",
    "target_domain",
    "target_obligation",
    "mapping",
    "preserved_structure",
    "loss_budget",
    "target_receipt_or_gate",
    "nearest_confuser",
    "confuser_distinction",
    "falsifier_or_kill_condition",
    "concrete_next_check",
)

WEAK_SUBSTITUTES = (
    "same_name",
    "metaphor_only",
    "donor_success_label",
    "structural_rhyme",
    "field_analogy_only",
    "target_desired_conclusion",
)

HARD_VIOLATIONS = (
    "hidden_target_assumption",
    "target_result_assumed",
    "post_hoc_mapping",
    "no_target_falsifier",
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


def run_analogical_transfer_receipt_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate that an analogy has been compiled into a checkable receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "analogical_transfer_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "summary": "malformed analogical-transfer receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "analogical_transfer_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "analogy transfer needs donor invariant, target obligation, "
                "explicit mapping, loss budget, target receipt/check, nearest "
                "confuser distinction, falsifier, and concrete next check"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "analogical_transfer_replaced_by_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "shared names, metaphors, donor success, or desired target "
                "conclusions do not substitute for a target receipt"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "analogical_transfer_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the analogy assumes the target result, maps after payoff, or "
                "has no target falsifier"
            ),
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present
    passed = not blocking if enforce_block else True
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "complete analogical-transfer receipt"
            if complete else
            f"incomplete analogical-transfer receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_analogical_transfer_receipt_gate({
        "donor_domain": "max-flow/min-cut",
        "donor_pattern": "cut pays all paths",
        "target_domain": "PDE",
        "same_name": "capacity",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False
    assert any(
        v["type"] == "analogical_transfer_receipt_incomplete"
        for v in weak["violations"]
    )

    strong = run_analogical_transfer_receipt_gate({
        "donor_domain": "max-flow/min-cut",
        "donor_pattern": "finite cut capacity bounds routed paths",
        "donor_invariant": "each path crossing is assigned to one cut edge",
        "target_domain": "finite PDE prefix source",
        "target_obligation": "supportIndex finalSlot <= baseIndex + finalSlot",
        "mapping": "supportIndex jump -> fresh source atom",
        "preserved_structure": "one crossing uses one atom before payoff",
        "loss_budget": "bounded fanout M paid in prefix budget",
        "target_receipt_or_gate": "G-NO-REBILLING-FRESHNESS",
        "nearest_confuser": "packing label without assignment map",
        "confuser_distinction": "requires explicit no-rebilling map",
        "falsifier_or_kill_condition": "one atom reused for two jumps",
        "concrete_next_check": "run no-rebilling and same-carrier gates",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True

    weak_with_strong = run_analogical_transfer_receipt_gate({
        **{
            field: "paid by concrete target receipt"
            for field in REQUIRED_FIELDS
        },
        "structural_rhyme": "recorded as nearest confuser, not proof",
    }, enforce_block=True)
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["weak_substitutes_present"] == ["structural_rhyme"]


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
        description="Validate an analogical-transfer receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    args = parser.parse_args(argv)
    result = run_analogical_transfer_receipt_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
