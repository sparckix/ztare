"""Gate for quotient-minimal carrier claims.

Taking an infimum over representatives of a net/quotient source removes
same-net wash cycles, but it may also remove the representative-level payment
the proof wants to spend. This gate checks that a quotient-minimal currency is
not used to pay a selected representative-level production term unless the
caller supplies a pre-payoff representative law and a preservation receipt.
"""
from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = {
    "quotient_source_law",
    "minimal_carrier_definition",
    "selected_production_functional",
    "pre_payoff_representative_selector",
    "selector_independent_of_target_deficit",
    "production_preserved_by_selector",
    "kernel_cycles_zero_selected_production",
    "minimal_carrier_bounds_selected_production",
}

WEAK_SUBSTITUTES = {
    "infimum_exists_only",
    "net_budget_bound_only",
    "same_source_label_only",
    "canonical_representative_label_only",
    "wash_eliminated_only",
    "pressure_visibility_only",
    "rank_reconstruction_only",
}

UNDERPAYMENT_CONFUSER_FIELDS = {
    "selected_production_not_quotient_invariant",
    "kernel_cycle_carries_selected_production",
    "minimizer_erases_selected_cone",
    "actual_packet_not_minimizer",
    "post_payoff_minimizer_selection",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "none", "null"}
    return bool(value)


def run_quotient_minimal_carrier_payment_gate(
    receipt: dict[str, Any],
) -> dict[str, Any]:
    missing = sorted(field for field in REQUIRED_FIELDS if not _truthy(receipt.get(field)))
    weak_hits = sorted(field for field in WEAK_SUBSTITUTES if _truthy(receipt.get(field)))
    confuser_hits = sorted(
        field for field in UNDERPAYMENT_CONFUSER_FIELDS if _truthy(receipt.get(field))
    )
    violations: list[dict[str, Any]] = []
    if missing:
        violations.append({
            "type": "missing_required_fields",
            "missing_fields": missing,
        })
    if weak_hits:
        violations.append({
            "type": "weak_substitute_fields_present",
            "fields": weak_hits,
            "message": (
                "a quotient/minimal norm can bound the quotient while failing "
                "to pay the selected representative-level production"
            ),
        })
    if confuser_hits:
        violations.append({
            "type": "quotient_minimal_underpayment_confuser_present",
            "fields": confuser_hits,
            "message": (
                "the selected production is not controlled by the quotient "
                "minimal carrier without a representative-preservation law"
            ),
        })
    return {
        "gate": "G-QUOTIENT-MINIMAL-CARRIER-PAYMENT",
        "label": receipt.get("label", "quotient_minimal_carrier_payment"),
        "passed": not violations,
        "complete": not missing,
        "missing_fields": missing,
        "weak_substitutes": weak_hits,
        "underpayment_confusers": confuser_hits,
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

    parser = argparse.ArgumentParser(
        description="Validate a quotient-minimal carrier payment receipt."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_quotient_minimal_carrier_payment_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
