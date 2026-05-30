"""G-FINITE-SUPPORT-EXTRACTION — concrete finite support receipt.

Checks that a support predicate is tied to an explicit finite extracted support
object before it is used as an indexed finite-support source.  This catches the
shortcut where size/measure evidence, a selected event, or a packing label is
renamed as a finite support set.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-FINITE-SUPPORT-EXTRACTION"

REQUIRED_FIELDS = (
    "finite_support_object",
    "support_predicate",
    "membership_equivalence",
    "cardinality_length_alignment",
    "enumeration_map",
    "enumeration_totality",
    "selected_membership_law",
    "restricted_prefix_membership",
    "fixed_before_payoff",
    "not_target_defined",
    "no_measure_only_extraction",
    "no_label_only_packing",
)

WEAK_SUBSTITUTES = (
    "support_label",
    "size_sum_overfill",
    "selected_event_witness",
    "packing_label",
    "carleson_label",
    "finite_by_intuition",
    "measure_positive",
    "same_name",
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
            "no",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def run_finite_support_extraction_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = True,
) -> dict[str, Any]:
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "finite_support_extraction_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "finite_support_extraction_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "finite support extraction needs a concrete finite support object, "
                "membership equivalence, cardinality alignment, enumeration, "
                "restricted-prefix membership, and anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "finite_support_extraction_replaced_by_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "size sums, selected events, or packing labels do not provide a "
                "finite extracted support object"
            ),
        })
    if _present(receipt.get("post_payoff_extraction")):
        violations.append({
            "type": "post_payoff_extraction",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "finite support must be extracted before payoff",
        })
    if _present(receipt.get("target_deficit_extraction")):
        violations.append({
            "type": "target_deficit_extraction",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "finite support cannot be extracted from the target deficit",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing
    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "finite_support_extraction"),
        "passed": not blocking if enforce_block else True,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "weak_substitute_policy": (
            "advisory when concrete finite support fields are present; missing "
            "support fields and post-payoff or target-deficit extraction block "
            "under enforce_block"
        ),
        "summary": (
            "finite extracted support receipt"
            if complete and not blocking else
            f"finite support extraction rejected with {len(blocking)} blocking violation(s)"
        ),
    }


def _read_json(path: str) -> dict[str, Any]:
    import json
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _self_test() -> None:
    weak = run_finite_support_extraction_gate({
        "support_label": "finite paid support",
        "size_sum_overfill": "strict overfill",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong_receipt = {
        "finite_support_object": "extractedBoundaryPaidSupport : Finset Nat",
        "support_predicate": "boundaryPaidSupportIndex",
        "membership_equivalence": "boundaryPaidSupportIndex n iff n in support",
        "cardinality_length_alignment": "support.card = supportLength",
        "enumeration_map": "supportIndex",
        "enumeration_totality": "every support member is hit",
        "selected_membership_law": "supportIndex k is in support",
        "restricted_prefix_membership": "support members lie in restricted prefix",
        "fixed_before_payoff": "support extracted before payoff",
        "not_target_defined": "not defined from target deficit",
        "no_measure_only_extraction": "size-sum overfill not used as extraction",
        "no_label_only_packing": "packing label not used as extraction",
    }
    strong = run_finite_support_extraction_gate(strong_receipt)
    assert strong["complete"] is True
    assert strong["passed"] is True

    weak_with_strong = run_finite_support_extraction_gate({
        **strong_receipt,
        "support_label": "confuser label retained for audit",
    })
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["weak_substitutes_present"] == ["support_label"]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a finite support extraction receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--advisory", action="store_true", help="report violations without blocking")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("finite_support_extraction_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_finite_support_extraction_gate(
        _read_json(args.receipt_json),
        enforce_block=not args.advisory,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
