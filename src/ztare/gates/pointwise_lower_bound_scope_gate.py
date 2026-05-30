"""G-POINTWISE-LOWER-BOUND-SCOPE -- lower-bound quantifier gate.

This gate validates that a claimed lower-bound receipt is actually pointwise on
the required support/prefix.  It rejects the recurring shortcut where a selected
witness, prefix average, moment bound, or upper bound is spent as
``forall n < prefixLength, delta <= payment n``.
"""
from __future__ import annotations

import json
from typing import Any


GATE_ID = "G-POINTWISE-LOWER-BOUND-SCOPE"

POINTWISE_SCOPES = {
    "pointwise_prefix",
    "pointwise_finite_prefix",
    "pointwise_support",
    "forall_prefix",
    "forall_support",
}

BAD_SCOPES = {
    "selected_index",
    "exists_selected",
    "single_witness",
    "average_prefix",
    "mean_prefix",
    "moment_bound",
    "second_moment",
    "support_measure",
    "size_sum",
    "measure_lower_bound",
    "upper_bound",
    "aggregate_budget",
}

BAD_SOURCE_MARKERS = (
    "selected_only",
    "selected-witness",
    "single_witness",
    "average_only",
    "moment_only",
    "upper_only",
    "cap_only",
)

REQUIRED_FIELDS = (
    "claim_label",
    "target_inequality",
    "target_carrier",
    "lower_bound_claim_scope",
    "quantifier",
    "lower_bound_direction",
    "carrier_matches_target",
    "no_selected_witness_promotion",
    "no_average_to_pointwise_promotion",
    "no_upper_bound_reversal",
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _present(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return False
        return text.lower() not in {"missing", "absent", "todo", "none", "null"}
    return value not in (None, "", [], {}, False)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def run_pointwise_lower_bound_scope_gate(
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate pointwise lower-bound quantifier and direction receipts."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": False,
            "complete": False,
            "violations": [{
                "type": "malformed_receipt",
                "reason": "receipt must be a JSON object",
            }],
            "required_fields": list(REQUIRED_FIELDS),
            "missing_fields": list(REQUIRED_FIELDS),
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "pointwise_lower_bound_receipt_incomplete",
            "missing_fields": missing,
            "reason": "pointwise lower-bound receipts need carrier, quantifier, direction, and anti-laundering guards",
        })

    scope = _norm(receipt.get("lower_bound_claim_scope"))
    quantifier = _norm(receipt.get("quantifier"))
    direction = _norm(receipt.get("lower_bound_direction"))

    if scope and scope not in POINTWISE_SCOPES:
        violations.append({
            "type": "lower_bound_scope_not_pointwise",
            "scope": scope,
            "reason": "the lower-bound claim must be pointwise on the requested finite prefix/support",
        })

    if scope in BAD_SCOPES:
        violations.append({
            "type": "selected_average_moment_or_upper_laundering",
            "scope": scope,
            "reason": "selected, average, moment, upper, or aggregate evidence is not a pointwise lower bound",
        })

    if quantifier and quantifier not in {"forall_prefix", "forall_support", "pointwise"}:
        violations.append({
            "type": "lower_bound_quantifier_not_forall_prefix",
            "quantifier": quantifier,
            "reason": "a pointwise lower bound must quantify over every index in the support",
        })

    if direction and direction not in {"lower", "lower_bound", "ge"}:
        violations.append({
            "type": "lower_bound_direction_wrong",
            "direction": direction,
            "reason": "upper/cap/control estimates cannot be reversed into lower bounds",
        })

    boolean_guards = (
        "carrier_matches_target",
        "no_selected_witness_promotion",
        "no_average_to_pointwise_promotion",
        "no_upper_bound_reversal",
    )
    missing_guards = [field for field in boolean_guards if not bool(receipt.get(field))]
    if missing_guards:
        violations.append({
            "type": "anti_laundering_guard_missing",
            "missing_fields": missing_guards,
            "reason": "the receipt must explicitly block selected/average/upper-bound promotion",
        })

    source_kinds = [_norm(item) for item in _as_list(receipt.get("source_kinds"))]
    bad_sources = [
        item for item in source_kinds
        if any(marker.replace("-", "_") in item for marker in BAD_SOURCE_MARKERS)
    ]
    if bad_sources:
        violations.append({
            "type": "source_kind_declares_non_pointwise_evidence",
            "source_kinds": bad_sources,
            "reason": "declared source kinds are not pointwise lower-bound evidence",
        })

    return {
        "gate_id": GATE_ID,
        "passed": not violations,
        "complete": not missing,
        "scope": scope,
        "quantifier": quantifier,
        "direction": direction,
        "required_fields": list(REQUIRED_FIELDS),
        "missing_fields": missing,
        "violations": violations,
        "summary": (
            "lower-bound receipt is pointwise on the requested support"
            if not violations else
            f"lower-bound receipt has {len(violations)} violation(s)"
        ),
    }


def _read_json(path: str) -> dict[str, Any]:
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _self_test() -> None:
    bad = run_pointwise_lower_bound_scope_gate({
        "claim_label": "selected witness",
        "target_inequality": "delta <= payment n",
        "target_carrier": "payment",
        "lower_bound_claim_scope": "selected_index",
        "quantifier": "exists_selected",
        "lower_bound_direction": "lower",
        "carrier_matches_target": True,
        "no_selected_witness_promotion": False,
        "no_average_to_pointwise_promotion": True,
        "no_upper_bound_reversal": True,
        "source_kinds": ["selected_only"],
    })
    assert bad["passed"] is False
    assert any(v["type"] == "selected_average_moment_or_upper_laundering"
               for v in bad["violations"])

    good = run_pointwise_lower_bound_scope_gate({
        "claim_label": "prefix lower payment",
        "target_inequality": "delta <= payment n for n < K",
        "target_carrier": "payment",
        "lower_bound_claim_scope": "pointwise_prefix",
        "quantifier": "forall_prefix",
        "lower_bound_direction": "lower",
        "carrier_matches_target": True,
        "no_selected_witness_promotion": True,
        "no_average_to_pointwise_promotion": True,
        "no_upper_bound_reversal": True,
        "source_kinds": ["pointwise_prefix_source"],
    })
    assert good["passed"] is True
    assert good["complete"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate pointwise finite-support lower-bound receipts.",
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or -")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--expect-fail",
        action="store_true",
        help="Exit 0 only when the receipt is rejected by the gate.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        _self_test()
        print(json.dumps({"gate_id": GATE_ID, "self_test": "passed"}, indent=2))
        return 0

    if not args.receipt_json:
        parser.error("receipt_json is required unless --self-test is used")

    result = run_pointwise_lower_bound_scope_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.expect_fail:
        return 0 if not result["passed"] else 1
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
