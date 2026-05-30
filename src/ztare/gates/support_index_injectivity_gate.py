"""G-SUPPORT-INDEX-INJECTIVITY - collision exclusion for support maps.

Validates that a finite support-index map is injective on its declared domain
because an order, separation, or collision-exclusion law has been supplied.
This catches the shortcut where cardinality, packing, or selected-event labels
are spent as injectivity without an equality-reflection proof.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-SUPPORT-INDEX-INJECTIVITY"

REQUIRED_FIELDS = (
    "support_index_map",
    "support_domain",
    "order_or_separation_law",
    "collision_exclusion_derivation",
    "equality_reflection_law",
    "injectivity_scope",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_reindexing",
    "no_cardinality_label_as_injectivity",
    "no_packing_label_as_injectivity",
)

WEAK_SUBSTITUTES = (
    "injective_prop_label",
    "cardinality_label",
    "packing_label",
    "carleson_label",
    "size_sum_overfill",
    "selected_event_witness",
    "finite_image_label",
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


def run_support_index_injectivity_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "support_index_injectivity_receipt_malformed",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
        }

    violations: list[dict[str, Any]] = []
    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "support_index_injectivity_receipt_incomplete",
            "missing_fields": missing,
            "reason": (
                "support-index injectivity needs a declared domain, an order "
                "or separation law, a collision-exclusion derivation, equality "
                "reflection, scope, timing, and anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "support_index_injectivity_replaced_by_weak_substitutes",
            "weak_substitutes": weak_present,
            "reason": (
                "cardinality, packing, selected-event, or label evidence does "
                "not prove collision exclusion for a support-index map"
            ),
        })
    if _present(receipt.get("post_payoff_reindexing")):
        violations.append({
            "type": "post_payoff_reindexing",
            "reason": "support-index collision exclusion must be fixed before payoff",
        })
    if _present(receipt.get("target_deficit_index_map")):
        violations.append({
            "type": "target_deficit_index_map",
            "reason": "support index cannot be defined from the target deficit",
        })

    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "support_index_injectivity"),
        "passed": not violations,
        "complete": not missing,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "support-index injectivity receipt"
            if not violations else
            f"support-index injectivity rejected with {len(violations)} violation(s)"
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
    weak = run_support_index_injectivity_gate({
        "support_index_map": "supportIndex",
        "cardinality_label": "same number of support atoms",
        "packing_label": "bounded overlap",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False
    assert any(v["type"] == "support_index_injectivity_receipt_incomplete"
               for v in weak["violations"])

    strong = run_support_index_injectivity_gate({
        "support_index_map": "supportIndex",
        "support_domain": "i < supportLength",
        "order_or_separation_law": (
            "i < j on the prefix implies supportIndex i < supportIndex j"
        ),
        "collision_exclusion_derivation": (
            "if supportIndex i = supportIndex j, trichotomy plus strict order "
            "rules out i < j and j < i"
        ),
        "equality_reflection_law": "supportIndex i = supportIndex j -> i = j",
        "injectivity_scope": "Finset.range supportLength",
        "fixed_before_payoff": "strict support order fixed before payoff",
        "not_target_defined": "order not defined from target deficit",
        "no_post_payoff_reindexing": "no reindexing after payoff",
        "no_cardinality_label_as_injectivity": "cardinality is a consequence",
        "no_packing_label_as_injectivity": "packing is not collision exclusion",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a support-index injectivity receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("support_index_injectivity_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_support_index_injectivity_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
