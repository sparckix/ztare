"""G-TARGET-INDEXED-EVENT-ASSIGNMENT-PROVENANCE.

General-purpose receipt gate for assigning a target prefix into a fixed indexed
event stream, such as target support jumps into the first final-slot entries of
`sameTreeLock.eventData`.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


GATE_ID = "G-TARGET-INDEXED-EVENT-ASSIGNMENT-PROVENANCE"

MODES = {
    "construct",
    "reduce_to_numeric_bound",
    "refute",
}

BASE_REQUIRED_FIELDS = (
    "target_prefix_family",
    "target_prefix_definition",
    "target_count",
    "indexed_event_stream",
    "indexed_event_prefix_definition",
    "event_prefix_index",
    "event_count",
    "incidence_geometry",
    "same_tree_or_carrier_binding",
    "fixed_before_payoff",
    "not_target_defined",
    "no_post_payoff_assignment_pruning",
    "no_endpoint_capacity_restatement",
    "nearest_confuser",
    "confuser_distinction",
)

CONSTRUCT_REQUIRED_FIELDS = (
    "incidence_relation",
    "assignment_construction_rule",
    "assignment_total_on_target_prefix",
    "assignment_codomain_is_indexed_event_prefix",
    "event_data_binding",
    "prefix_domination_source",
    "injectivity_source",
    "collision_exclusion_derivation",
    "equality_reflection_law",
    "no_rebilling_same_event_atom",
    "finite_injection_cardinality_derivation",
    "handoff_to_prefix_count_bridge",
)

FINITE_INJECTION_CARDINALITY_REQUIRED_FIELDS = (
    "domain",
    "codomain",
    "map",
    "injectivity_certificate",
    "cardinality_theorem",
    "derived_bound",
    "no_prior_bound_dependency",
)

REDUCE_REQUIRED_FIELDS = (
    "target_count_le_event_count",
    "numeric_bound_source",
    "assignment_construction_rule",
    "assignment_total_on_target_prefix",
    "assignment_codomain_is_indexed_event_prefix",
    "event_data_binding",
    "canonical_cast_assignment",
    "cast_assignment_injective",
    "no_rebilling_same_event_atom",
    "handoff_to_prefix_count_bridge",
    "remaining_provenance_obligation",
)

REFUTE_REQUIRED_FIELDS = (
    "refutation_witness_if_mode_refute",
    "collision_or_oversubscription_witness",
    "why_no_injection_to_indexed_prefix",
    "remaining_escape_hatch",
)

WEAK_SUBSTITUTES = (
    "provided_assignment_without_provenance",
    "abstract_source_prefix_assignment",
    "event_label_only",
    "source_budget_only",
    "prefix_domination_label_only",
    "incidence_label_only",
    "bounded_fanout_label_only",
)

HARD_VIOLATIONS = (
    "post_payoff_assignment",
    "target_deficit_selection",
    "carrier_drift",
    "collision_not_excluded",
    "endpoint_capacity_restatement",
    "same_event_atom_reused",
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


def _fraction_or_none(value: Any) -> Fraction | None:
    if value in (None, ""):
        return None
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(str(value).strip())


def _mode_required_fields(mode: str) -> tuple[str, ...]:
    if mode == "construct":
        return CONSTRUCT_REQUIRED_FIELDS
    if mode == "reduce_to_numeric_bound":
        return REDUCE_REQUIRED_FIELDS
    if mode == "refute":
        return REFUTE_REQUIRED_FIELDS
    return ()


def _validate_finite_injection_cardinality_derivation(
    value: Any,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Validate the construct-mode dependency from injection to cardinality."""
    if not _present(value):
        return None, []
    if not isinstance(value, dict):
        return None, [{
            "type": "target_indexed_event_assignment_bad_injection_cardinality_derivation",
            "severity": "blocking",
            "reason": (
                "finite_injection_cardinality_derivation must be an object "
                "with domain/codomain/map/injectivity/theorem/bound/no-prior "
                "dependency fields"
            ),
        }]

    missing = [
        field for field in FINITE_INJECTION_CARDINALITY_REQUIRED_FIELDS
        if not _present(value.get(field))
    ]
    check = {
        "required_fields": list(FINITE_INJECTION_CARDINALITY_REQUIRED_FIELDS),
        "missing_fields": missing,
        "no_prior_bound_dependency": value.get("no_prior_bound_dependency"),
    }
    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({
            "type": "target_indexed_event_assignment_incomplete_injection_cardinality_derivation",
            "severity": "blocking",
            "missing_fields": missing,
            "reason": (
                "construct mode must certify that the target-count bound is "
                "derived from a finite injective map, not assumed as an "
                "endpoint capacity premise"
            ),
        })
    no_prior = value.get("no_prior_bound_dependency")
    if no_prior is not True and not (
        isinstance(no_prior, str)
        and _present(no_prior)
        and "not" in no_prior.lower()
        and "bound" in no_prior.lower()
    ):
        violations.append({
            "type": "target_indexed_event_assignment_prior_bound_dependency_not_excluded",
            "severity": "blocking",
            "reason": (
                "finite injection cardinality derivation must explicitly "
                "exclude using the target-count bound as a premise"
            ),
        })
    return check, violations


def run_target_indexed_event_assignment_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate a target-prefix to indexed-event assignment receipt."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "mode": None,
            "violations": [{
                "type": "target_indexed_event_assignment_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(BASE_REQUIRED_FIELDS),
            "required_fields": list(BASE_REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "hard_violations_present": [],
            "numeric_check": None,
            "summary": "malformed target-indexed event assignment receipt",
        }

    mode = str(receipt.get("mode") or "").strip()
    if mode not in MODES:
        violations.append({
            "type": "target_indexed_event_assignment_unknown_mode",
            "severity": "blocking" if enforce_block else "advisory",
            "mode": mode,
            "allowed_modes": sorted(MODES),
        })

    required_fields = BASE_REQUIRED_FIELDS + _mode_required_fields(mode)
    missing = [field for field in required_fields if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "target_indexed_event_assignment_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "target-indexed event assignments need target prefix, indexed "
                "event stream, same-tree carrier, timing, anti-target-selection, "
                "anti-endpoint, construction/refutation fields, and nearest "
                "confuser separation"
            ),
        })

    weak_present = [
        field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))
    ]
    if weak_present:
        violations.append({
            "type": "target_indexed_event_assignment_weak_substitute",
            "severity": "blocking" if enforce_block else "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "an event label, source-budget proof, prefix-domination label, "
                "or supplied opaque assignment does not certify the target "
                "prefix assignment into the indexed event stream"
            ),
        })

    hard_present = [
        field for field in HARD_VIOLATIONS if _present(receipt.get(field))
    ]
    if hard_present:
        violations.append({
            "type": "target_indexed_event_assignment_hard_violation",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": hard_present,
            "reason": (
                "the assignment is posthoc, target-defined, carrier-drifting, "
                "collision-prone, endpoint-restated, or rebills an event atom"
            ),
        })

    finite_injection_cardinality_check = None
    finite_injection_cardinality_violations: list[dict[str, Any]] = []
    if mode == "construct":
        (
            finite_injection_cardinality_check,
            finite_injection_cardinality_violations,
        ) = _validate_finite_injection_cardinality_derivation(
            receipt.get("finite_injection_cardinality_derivation")
        )
        if finite_injection_cardinality_violations:
            severity = "blocking" if enforce_block else "advisory"
            for violation in finite_injection_cardinality_violations:
                violation["severity"] = severity
            violations.extend(finite_injection_cardinality_violations)

    numeric_check = None
    try:
        target_value = _fraction_or_none(receipt.get("target_count_value"))
        event_value = _fraction_or_none(receipt.get("event_count_value"))
    except Exception as exc:
        violations.append({
            "type": "target_indexed_event_assignment_numeric_parse_error",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": str(exc),
        })
        target_value = event_value = None
    if target_value is not None and event_value is not None:
        target_le_event = target_value <= event_value
        numeric_check = {
            "target_count_value": str(target_value),
            "event_count_value": str(event_value),
            "target_le_event": target_le_event,
            "oversubscribed": target_value > event_value,
        }
        if not target_le_event and mode != "refute":
            violations.append({
                "type": "target_indexed_event_assignment_numeric_check_failed",
                "severity": "blocking" if enforce_block else "advisory",
                "numeric_check": numeric_check,
            })
        if mode == "refute" and target_le_event:
            violations.append({
                "type": "target_indexed_event_assignment_refute_numeric_not_oversubscribed",
                "severity": "blocking" if enforce_block else "advisory",
                "numeric_check": numeric_check,
                "reason": (
                    "refute mode needs either an oversubscription witness or "
                    "a separate collision witness; the numeric fields supplied "
                    "do not oversubscribe the indexed event prefix"
                ),
            })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    numeric_ok = (
        numeric_check is None
        or numeric_check["target_le_event"]
        or (mode == "refute" and numeric_check["oversubscribed"])
    )
    complete = (
        mode in MODES
        and not missing
        and not hard_present
        and not finite_injection_cardinality_violations
        and numeric_ok
    )
    passed = not blocking if enforce_block else True
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "mode": mode,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "hard_violations_present": hard_present,
        "numeric_check": numeric_check,
        "finite_injection_cardinality_check": finite_injection_cardinality_check,
        "required_fields": list(required_fields),
        "summary": (
            f"complete target-indexed event assignment receipt ({mode})"
            if complete else
            "incomplete target-indexed event assignment receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_target_indexed_event_assignment_gate({
        "mode": "construct",
        "target_prefix_family": "target jumps",
        "event_label_only": "eventData",
    })
    assert weak["passed"] is True
    assert weak["complete"] is False
    assert any(
        v["type"] == "target_indexed_event_assignment_receipt_incomplete"
        for v in weak["violations"]
    )

    reduced = run_target_indexed_event_assignment_gate({
        "mode": "reduce_to_numeric_bound",
        "target_prefix_family": "supportIndex target jumps",
        "target_prefix_definition": "Fin (targetPrefixCount finalSlot)",
        "target_count": "targetPrefixCount finalSlot",
        "indexed_event_stream": "FreshFrequencyEventSameTreeLock.eventData",
        "indexed_event_prefix_definition": "first finalSlot eventData atoms",
        "event_prefix_index": "finalSlot",
        "event_count": "finalSlot",
        "incidence_geometry": "BadCenterEventIncidenceGeometry",
        "same_tree_or_carrier_binding": "same sameTreeLock",
        "fixed_before_payoff": "target and event prefix fixed before payoff",
        "not_target_defined": "event prefix is not chosen from target deficit",
        "no_post_payoff_assignment_pruning": "no posthoc pruning",
        "no_endpoint_capacity_restatement": "constructs Fin.castLE assignment",
        "nearest_confuser": "source-budget-only Level493 receipt",
        "confuser_distinction": "targets map into eventData prefix",
        "target_count_le_event_count": "numeric bound supplied",
        "numeric_bound_source": "targetPrefixCount_finalSlot_le_finalSlot",
        "assignment_construction_rule": "Fin.castLE",
        "assignment_total_on_target_prefix": "domain is full target prefix",
        "assignment_codomain_is_indexed_event_prefix": "codomain is Fin finalSlot",
        "event_data_binding": "sourceEventAt j = sameTreeLock.eventData j.val",
        "canonical_cast_assignment": "fun i => Fin.castLE hbound i",
        "cast_assignment_injective": "Fin.val equality reflects equality",
        "no_rebilling_same_event_atom": "injective cast assignment",
        "handoff_to_prefix_count_bridge": "TargetPrefixToSourceEventInjectionSource",
        "remaining_provenance_obligation": "derive numeric bound from incidence",
        "target_count_value": 2,
        "event_count_value": 3,
    })
    assert reduced["complete"] is True
    assert reduced["passed"] is True

    constructed = run_target_indexed_event_assignment_gate({
        **{
            field: "ok" for field in BASE_REQUIRED_FIELDS + CONSTRUCT_REQUIRED_FIELDS
        },
        "mode": "construct",
        "finite_injection_cardinality_derivation": {
            "domain": "Fin targetCount",
            "codomain": "Fin eventCount",
            "map": "targetSlot",
            "injectivity_certificate": "Function.Injective targetSlot",
            "cardinality_theorem": "Fintype.card_le_of_injective",
            "derived_bound": "targetCount <= eventCount",
            "no_prior_bound_dependency": True,
        },
    })
    assert constructed["complete"] is True
    assert constructed["passed"] is True

    bad_numeric = run_target_indexed_event_assignment_gate({
        **{
            field: "ok" for field in BASE_REQUIRED_FIELDS + REDUCE_REQUIRED_FIELDS
        },
        "mode": "reduce_to_numeric_bound",
        "target_count_value": 4,
        "event_count_value": 3,
    })
    assert bad_numeric["passed"] is True
    assert bad_numeric["complete"] is False
    assert any(
        v["type"] == "target_indexed_event_assignment_numeric_check_failed"
        for v in bad_numeric["violations"]
    )

    refute = run_target_indexed_event_assignment_gate({
        **{
            field: "ok" for field in BASE_REQUIRED_FIELDS + REFUTE_REQUIRED_FIELDS
        },
        "mode": "refute",
        "target_count_value": 2,
        "event_count_value": 1,
    }, enforce_block=True)
    assert refute["complete"] is True
    assert refute["passed"] is True
    assert refute["numeric_check"]["oversubscribed"] is True


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
        description="Validate a target-indexed event assignment receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    result = run_target_indexed_event_assignment_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
