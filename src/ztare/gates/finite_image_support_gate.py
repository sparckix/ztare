"""G-FINITE-IMAGE-SUPPORT - finite support from a fixed finite image.

Validates that a finite support object is produced as the image of a fixed
finite domain under an enumeration map, with cardinality paid by injectivity.
This catches the shortcut where a support set is asserted as finite without the
image/range construction that justifies totality and card alignment.
"""
from __future__ import annotations

from typing import Any

try:
    from src.ztare.gates.required_field_semantics import is_semantically_present
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from required_field_semantics import is_semantically_present


GATE_ID = "G-FINITE-IMAGE-SUPPORT"

REQUIRED_FIELDS = (
    "domain_finset",
    "image_map",
    "image_support_object",
    "support_object_is_image",
    "membership_iff_exists_domain",
    "selected_membership_from_domain",
    "totality_from_image_membership",
    "injective_on_domain",
    "card_image_eq_domain_card",
    "domain_card_eq_length",
    "restricted_prefix_on_image",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_domain_pruning",
)

WEAK_SUBSTITUTES = (
    "support_label",
    "packing_label",
    "carleson_label",
    "size_sum_overfill",
    "selected_event_witness",
    "measure_positive",
    "finite_by_assertion",
    "cardinality_by_label",
    "same_name",
)


def _present(value: Any, *, field: str = "") -> bool:
    return is_semantically_present(value, field=field)


def run_finite_image_support_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = True,
) -> dict[str, Any]:
    receipt = receipt or {}
    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "finite_image_support_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
        }

    violations: list[dict[str, Any]] = []
    missing = [
        field for field in REQUIRED_FIELDS
        if not _present(receipt.get(field), field=field)
    ]
    weak_present = [
        field for field in WEAK_SUBSTITUTES
        if _present(receipt.get(field), field=field)
    ]
    if missing:
        violations.append({
            "type": "finite_image_support_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "finite image support needs a domain Finset, image map, "
                "image identity, membership/totality from image membership, "
                "injectivity, card equality, restricted-prefix membership, "
                "and timing/anti-laundering receipts"
            ),
        })
    if weak_present:
        violations.append({
            "type": "finite_image_support_replaced_by_weak_substitutes",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "packing, size-sum, selected-event, or label evidence does "
                "not prove a finite image support construction"
            ),
        })
    if _present(receipt.get("post_payoff_image_domain")):
        violations.append({
            "type": "post_payoff_image_domain",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "the image domain must be fixed before payoff",
        })
    if _present(receipt.get("target_deficit_image_map")):
        violations.append({
            "type": "target_deficit_image_map",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": "the image map cannot be defined from the target deficit",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing
    return {
        "gate_id": GATE_ID,
        "label": receipt.get("label", "finite_image_support"),
        "passed": not blocking if enforce_block else True,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "weak_substitute_policy": (
            "advisory when concrete finite image support fields are present; "
            "missing image fields and post-payoff or target-deficit image "
            "construction block under enforce_block"
        ),
        "summary": (
            "finite image support receipt"
            if complete and not blocking else
            f"finite image support rejected with {len(blocking)} blocking violation(s)"
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
    weak = run_finite_image_support_gate({
        "support_label": "finite support",
        "cardinality_by_label": "same size",
    })
    assert weak["passed"] is False
    assert weak["complete"] is False

    strong_receipt = {
        "domain_finset": "Finset.range supportLength",
        "image_map": "supportIndex",
        "image_support_object": "Finset.image supportIndex (Finset.range supportLength)",
        "support_object_is_image": "rfl",
        "membership_iff_exists_domain": "mem_image",
        "selected_membership_from_domain": "mem_image_of_mem",
        "totality_from_image_membership": "mem_image gives a preimage",
        "injective_on_domain": "supportIndex injective for k < supportLength",
        "card_image_eq_domain_card": "Finset.card_image_of_injective",
        "domain_card_eq_length": "Finset.card_range",
        "restricted_prefix_on_image": "preimage index satisfies supportIndex_lt_restricted",
        "fixed_before_payoff": "domain and map fixed before payoff",
        "not_target_defined": "map not target-defined",
        "no_post_payoff_domain_pruning": "range domain not pruned after payoff",
    }
    strong = run_finite_image_support_gate(strong_receipt)
    assert strong["complete"] is True
    assert strong["passed"] is True

    weak_with_strong = run_finite_image_support_gate({
        **strong_receipt,
        "support_label": "confuser label retained for audit",
    })
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["weak_substitutes_present"] == ["support_label"]

    non_claim = {
        **strong_receipt,
        "injective_on_domain": (
            "no injectivity is claimed; multiplicity is preserved explicitly"
        ),
        "card_image_eq_domain_card": "not used; no card equality is claimed",
    }
    weak_semantic = run_finite_image_support_gate(non_claim)
    assert weak_semantic["complete"] is False
    assert weak_semantic["passed"] is False
    assert "injective_on_domain" in weak_semantic["missing_fields"]
    assert "card_image_eq_domain_card" in weak_semantic["missing_fields"]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate a finite image support receipt."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--advisory", action="store_true", help="report violations without blocking")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print("finite_image_support_gate self-test PASS")
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_finite_image_support_gate(
        _read_json(args.receipt_json),
        enforce_block=not args.advisory,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
