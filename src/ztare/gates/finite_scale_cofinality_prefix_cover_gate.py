"""G-FINITE-SCALE-COFINALITY-PREFIX-COVER.

Receipt gate for deriving a target/index prefix-cover relation from finite
scale-prefix comparison plus event-prefix cofinality.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-FINITE-SCALE-COFINALITY-PREFIX-COVER"

REQUIRED_FIELDS = (
    "target_family",
    "finite_scale_prefix_comparison",
    "event_prefix_cofinality",
    "selected_eventdata_index",
    "selected_index_codomain",
    "cover_relation_definition",
    "cover_relation_is_guarded_graph",
    "selected_index_cover_membership",
    "selected_index_incidence_law",
    "cover_to_incidence_transport",
    "same_tree_binding",
    "prefix_domination_primitive_binding",
    "incidence_geometry_binding",
    "selected_index_fixed_before_payoff",
    "not_arbitrary_cover_relation",
    "not_endpoint_capacity_only",
    "not_label_only_prefix_domination",
    "not_post_payoff_selection",
    "downstream_prefix_cover_source",
    "nearest_confuser",
)

WEAK_SUBSTITUTES = (
    "prefix_domination_label_only",
    "finite_scale_label_only",
    "cofinality_label_only",
    "cover_label_only",
    "endpoint_capacity_label_only",
    "opaque_cover_relation",
    "classical_choice_from_bare_cofinality",
)

HARD_VIOLATIONS = (
    "post_payoff_index_choice",
    "target_deficit_choice",
    "carrier_drift",
    "cover_relation_not_guarded_by_primitive_fields",
    "selected_index_outside_final_slot",
    "selected_index_not_incident",
    "endpoint_capacity_as_cover",
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


def run_finite_scale_cofinality_prefix_cover_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a finite-scale/cofinality prefix-cover receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "finite_scale_cofinality_prefix_cover_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed finite-scale/cofinality prefix-cover receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "finite_scale_cofinality_prefix_cover_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "prefix-cover construction needs finite scale-prefix "
                "comparison, event-prefix cofinality, selected Fin index, "
                "guarded graph definition, membership, incidence transport, "
                "provenance, timing, and anti-label checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "finite_scale_cofinality_prefix_cover_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "labels for prefix domination, finite comparison, cofinality, "
                "or endpoint capacity do not construct a guarded cover graph"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "finite_scale_cofinality_prefix_cover_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the cover is posthoc, target-defined, carrier-drifting, not "
                "guarded by the prefix primitive fields, outside the final "
                "slot, nonincident, or endpoint-capacity-only"
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
            "complete finite-scale/cofinality prefix-cover receipt"
            if complete else
            "incomplete finite-scale/cofinality prefix-cover receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    advisory = run_finite_scale_cofinality_prefix_cover_gate({
        "target_family": "L3A target prefix",
        "cover_label_only": "cover exists",
    })
    assert advisory["passed"] is True
    assert advisory["complete"] is False
    assert advisory["weak_substitutes_present"] == ["cover_label_only"]

    weak_with_strong = run_finite_scale_cofinality_prefix_cover_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "cofinality_label_only": "named nearest confuser, not used as proof",
    }, enforce_block=True)
    assert weak_with_strong["passed"] is True
    assert weak_with_strong["complete"] is True
    assert weak_with_strong["weak_substitutes_present"] == ["cofinality_label_only"]

    hard = run_finite_scale_cofinality_prefix_cover_gate({
        **{field: "ok" for field in REQUIRED_FIELDS},
        "cover_relation_not_guarded_by_primitive_fields": "bare relation",
    }, enforce_block=True)
    assert hard["passed"] is False
    assert hard["hard_violations_present"] == [
        "cover_relation_not_guarded_by_primitive_fields"
    ]

    exact_false = run_finite_scale_cofinality_prefix_cover_gate({
        "target_family": "missing because target-family proof is pending",
    }, enforce_block=True)
    assert exact_false["missing_fields"][0] == "finite_scale_prefix_comparison"

    strong = run_finite_scale_cofinality_prefix_cover_gate({
        field: "ok" for field in REQUIRED_FIELDS
    }, enforce_block=True)
    assert strong["complete"] is True
    assert strong["passed"] is True


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
        description="Validate a finite-scale/cofinality prefix-cover receipt."
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
    result = run_finite_scale_cofinality_prefix_cover_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
