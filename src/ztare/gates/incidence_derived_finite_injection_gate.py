"""G-INCIDENCE-DERIVED-FINITE-INJECTION.

Receipt gate for extracting a finite injective map from an incidence relation.
This catches the common confuser where an incidence or prefix-domination label
is named as if it were already a concrete finite assignment.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-INCIDENCE-DERIVED-FINITE-INJECTION"

REQUIRED_FIELDS = (
    "incidence_source",
    "domain_predicate",
    "codomain_event_family",
    "map_extraction_rule",
    "totality_derivation",
    "uniqueness_or_collision_exclusion",
    "injectivity_derivation",
    "same_event_family_binding",
    "finite_domain",
    "finite_codomain",
    "no_post_payoff_choice",
    "not_cardinality_as_injectivity",
    "not_label_only_incidence",
    "nearest_confuser",
    "downstream_cardinality_bridge",
)

WEAK_SUBSTITUTES = (
    "incidence_label_only",
    "prefix_domination_label_only",
    "bounded_fanout_label_only",
    "same_tree_label_only",
    "cardinality_bound_assumed",
    "opaque_injection_prop",
)

HARD_VIOLATIONS = (
    "post_payoff_map_choice",
    "target_deficit_map_choice",
    "event_family_drift",
    "collision_allowed",
    "injectivity_from_cardinality_bound",
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


def run_incidence_derived_finite_injection_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a receipt for incidence-derived finite injection."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "incidence_derived_finite_injection_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "summary": "malformed incidence-derived finite injection receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "incidence_derived_finite_injection_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "incidence-derived finite injection needs an incidence source, "
                "map extraction rule, totality, uniqueness/collision exclusion, "
                "injectivity derivation, same-event-family binding, and "
                "anti-label-only / anti-cardinality-restatement checks"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "incidence_derived_finite_injection_weak_substitute",
            "severity": "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "incidence, prefix-domination, fanout, or same-tree labels do "
                "not construct a finite map or prove equality reflection"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "incidence_derived_finite_injection_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the proposed map is posthoc, target-defined, carrier-drifting, "
                "collision-prone, or derives injectivity from the cardinality "
                "bound it was supposed to prove"
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
        "required_fields": list(REQUIRED_FIELDS),
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "summary": (
            "complete incidence-derived finite injection receipt"
            if complete else
            f"incomplete incidence-derived finite injection receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_incidence_derived_finite_injection_gate({
        "incidence_source": "BadCenterEventIncidenceGeometry",
        "incidence_label_only": "incidence exists",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False
    assert any(
        v["type"] == "incidence_derived_finite_injection_receipt_incomplete"
        for v in weak["violations"]
    )
    assert any(
        v["type"] == "incidence_derived_finite_injection_weak_substitute"
        for v in weak["violations"]
    )

    strong = run_incidence_derived_finite_injection_gate({
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
        description="Validate an incidence-derived finite injection receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_incidence_derived_finite_injection_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
