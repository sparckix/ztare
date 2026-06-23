"""G-NO-REBILLING-FRESHNESS — distinct-payment/no-reuse receipt gate.

Substrate-neutral gate for arguments that turn a sequence of selected levels,
events, or obligations into a summable budget. It checks that each level uses a
fresh payment atom and that one physical packet cannot be rebilled as many
costs.
"""
from __future__ import annotations

from typing import Any

try:  # pragma: no cover - fallback keeps direct script execution usable
    from ztare.gates.required_field_semantics import is_semantically_present
except ModuleNotFoundError:  # pragma: no cover
    from required_field_semantics import is_semantically_present

REQUIRED_FIELDS = {
    "selected_units",
    "payment_atoms",
    "assignment_map",
    "assignment_total_on_prefix",
    "distinctness_or_disjointness",
    "no_rebilling_same_atom",
    "prefix_budget_bound",
    "fixed_before_payoff",
    "same_owner_or_source",
    "overlap_or_multiplicity_bound",
}

WEAK_SUBSTITUTES = {
    "finite_budget_label",
    "same_carrier_label",
    "freshness_label",
    "pointwise_payment_only",
    "bounded_fanout_label",
    "disjoint_by_intuition",
}


def _truthy(value: Any) -> bool:
    return is_semantically_present(value)


def run_no_rebilling_freshness_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(
        field for field in REQUIRED_FIELDS
        if not is_semantically_present(receipt.get(field), field=field)
    )
    weak_hits = sorted(field for field in WEAK_SUBSTITUTES if _truthy(receipt.get(field)))
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
            "message": "budget/freshness labels do not prove distinct payment atoms or no-rebilling",
        })
    if _truthy(receipt.get("same_atom_reused_across_levels")):
        violations.append({
            "type": "same_atom_reused_across_levels",
            "message": "one payment atom cannot be counted as many selected-level costs",
        })
    return {
        "gate": "G-NO-REBILLING-FRESHNESS",
        "label": receipt.get("label", "no_rebilling_freshness"),
        "passed": not violations,
        "complete": not missing,
        "missing_fields": missing,
        "weak_substitutes": weak_hits,
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

    parser = argparse.ArgumentParser(description="Validate a no-rebilling freshness receipt.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_no_rebilling_freshness_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
