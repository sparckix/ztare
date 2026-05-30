"""G-METRIC-COVERING-SELECTION — covering theorem receipt gate.

Substrate-neutral gate for arguments that turn a metric family into a finite
overlap packing/selection theorem.  It is stricter than a same-carrier packing
receipt: the caller must provide the metric/scale hypotheses that make the
packing theorem true, plus the omission/error and pre-payoff selection receipts
needed before downstream budget accounting can consume it.
"""
from __future__ import annotations

from typing import Any

GATE_ID = "G-METRIC-COVERING-SELECTION"

REQUIRED_FIELDS = (
    "ambient_metric_or_quasi_metric",
    "source_family",
    "scale_or_radius_function",
    "doubling_or_besicovitch_constant",
    "bounded_eccentricity_or_engulfing",
    "selection_rule",
    "selection_totality_or_paid_omission",
    "pre_payoff_selection_timing",
    "same_carrier_binding",
    "bounded_overlap_conclusion",
    "nested_children_policy",
    "discarded_or_nested_error_budget",
)

WEAK_SUBSTITUTES = (
    "metric_label",
    "vitali_label",
    "besicovitch_label",
    "whitney_label",
    "localized_label",
    "finite_overlap_label",
    "topology_label",
    "reconnection_label",
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


def run_metric_covering_selection_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate metric covering/selection receipts."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "metric_covering_selection_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "weak_substitutes_present": [],
            "summary": "malformed metric covering/selection receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "metric_covering_selection_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": (
                "covering selection needs metric scale, doubling/Besicovitch "
                "constant, engulfing/eccentricity control, pre-payoff rule, "
                "coverage or paid omissions, same-carrier binding, overlap "
                "conclusion, and nested-child/error policy"
            ),
        })

    weak_present = [field for field in WEAK_SUBSTITUTES if _present(receipt.get(field))]
    if weak_present and missing:
        violations.append({
            "type": "metric_covering_selection_replaced_by_weak_substitutes",
            "severity": "blocking" if enforce_block else "advisory",
            "weak_substitutes": weak_present,
            "reason": (
                "metric/Besicovitch/Whitney/topology labels do not supply the "
                "covering hypotheses or paid omission receipts"
            ),
        })

    if _present(receipt.get("known_non_doubling_or_nested_cascade_confuser")):
        violations.append({
            "type": "metric_covering_selection_confuser_declared",
            "severity": "blocking" if enforce_block else "advisory",
            "confuser": receipt.get("known_non_doubling_or_nested_cascade_confuser"),
            "reason": (
                "caller declared non-doubling geometry, nested cascade reuse, "
                "or unpaid discarded children"
            ),
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    confuser = any(
        v["type"] == "metric_covering_selection_confuser_declared"
        for v in violations
    )
    complete = not missing and not confuser
    passed = not blocking if enforce_block else True
    return {
        "gate_id": GATE_ID,
        "passed": passed,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "weak_substitutes_present": weak_present,
        "required_fields": list(REQUIRED_FIELDS),
        "summary": (
            "complete metric covering/selection receipt"
            if complete else
            f"incomplete metric covering/selection receipt; missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    weak = run_metric_covering_selection_gate({
        "source_family": "reconnection tents",
        "besicovitch_label": "Besicovitch subcover",
        "topology_label": "vortex reconnection",
    })
    assert weak["complete"] is False
    assert any(v["type"] == "metric_covering_selection_receipt_incomplete" for v in weak["violations"])

    strong = run_metric_covering_selection_gate({
        "ambient_metric_or_quasi_metric": "parabolic metric",
        "source_family": "reconnection tents",
        "scale_or_radius_function": "r(Q)",
        "doubling_or_besicovitch_constant": "B",
        "bounded_eccentricity_or_engulfing": "5Q engulfing",
        "selection_rule": "maximal disjoint subfamily",
        "selection_totality_or_paid_omission": "unselected children paid by error E",
        "pre_payoff_selection_timing": "selected before target payoff",
        "same_carrier_binding": "same pressure/Duhamel carrier",
        "bounded_overlap_conclusion": "overlap <= B",
        "nested_children_policy": "parent pays children once",
        "discarded_or_nested_error_budget": "sum omitted <= E",
    })
    assert strong["complete"] is True
    assert strong["passed"] is True


if __name__ == "__main__":
    _self_test()
