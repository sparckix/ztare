"""Gate for quadratic-function descent through a quotient/source map.

For a quadratic selected-production functional Q, a quotient/minimal source
carrier controls actual representatives only if Q descends to the quotient (or
is bounded there). It is not enough for the selector to be energy-orthogonal or
source-minimal: every source-kernel direction must have controlled square term
and controlled cross term with the selected representative before payoff.
"""
from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "source_map_or_equivalence",
    "quadratic_functional",
    "polarized_bilinear_form",
    "source_kernel_definition",
    "representative_selector",
    "selector_fixed_before_payoff",
    "kernel_square_zero_or_nonpositive",
    "kernel_cross_zero_or_nonpositive",
    "quotient_descent_or_bound",
    "not_defined_by_target_deficit",
}

WEAK_SUBSTITUTES = {
    "linear_orthogonality_only",
    "energy_minimality_only",
    "net_source_identity_only",
    "quotient_label_only",
    "same_source_label_only",
    "rank_reconstruction_only",
    "pressure_visibility_only",
    "sterility_defined_by_conclusion",
}

QUADRATIC_CONFUSER_FIELDS = {
    "kernel_square_positive",
    "kernel_cross_positive",
    "zero_source_positive_quadratic_packet",
    "selector_metric_not_quadratic_metric",
    "actual_representative_differs_by_positive_kernel",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "none", "null"}
    return bool(value)


def run_quadratic_quotient_descent_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(field for field in REQUIRED_FIELDS if not _truthy(receipt.get(field)))
    weak_hits = sorted(field for field in WEAK_SUBSTITUTES if _truthy(receipt.get(field)))
    confuser_hits = sorted(field for field in QUADRATIC_CONFUSER_FIELDS if _truthy(receipt.get(field)))
    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({"type": "missing_required_fields", "missing_fields": missing})
    if weak_hits:
        violations.append({
            "type": "weak_substitute_fields_present",
            "fields": weak_hits,
            "message": (
                "linear/energy/source labels do not prove a quadratic selected "
                "functional descends to the quotient"
            ),
        })
    if confuser_hits:
        violations.append({
            "type": "quadratic_quotient_confuser_present",
            "fields": confuser_hits,
            "message": (
                "a source-kernel direction has positive square or cross term, "
                "so the quadratic functional is not paid by the quotient carrier"
            ),
        })
    return {
        "gate": "G-QUADRATIC-QUOTIENT-DESCENT",
        "label": receipt.get("label", "quadratic_quotient_descent"),
        "passed": not violations,
        "complete": not missing,
        "missing_fields": missing,
        "weak_substitutes": weak_hits,
        "quadratic_confusers": confuser_hits,
        "violations": violations,
        "required_fields": sorted(REQUIRED_FIELDS),
    }


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

    parser = argparse.ArgumentParser(description="Validate quadratic quotient-descent receipts.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_quadratic_quotient_descent_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
