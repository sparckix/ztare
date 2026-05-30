"""Gate for signed-to-positive-variation currency bridges.

This is substrate-neutral. It checks that a caller has a numeric domination
receipt on the same carrier before spending a signed lower bound as positive
variation currency.
"""
from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = {
    "signed_source",
    "positive_variation_source",
    "same_carrier",
    "numeric_domination",
    "event_scope",
    "fixed_before_payoff",
    "no_post_payoff_positive_part",
    "no_target_deficit_definition",
}

WEAK_SUBSTITUTES = {
    "positive_variation_label",
    "same_name",
    "same_symbol",
    "signed_to_positive_intuition",
    "posthoc_positive_part",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "none", "null"}
    return bool(value)


def run_positive_variation_bridge_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(field for field in REQUIRED_FIELDS if not _truthy(receipt.get(field)))
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
            "message": "labels or same-symbol cues do not pay signed-to-positive currency exchange",
        })
    if _truthy(receipt.get("posthoc_positive_part")):
        violations.append({
            "type": "posthoc_positive_part_selection",
            "message": "positive variation bridge must be fixed before payoff",
        })
    return {
        "gate": "G-POSITIVE-VARIATION-BRIDGE",
        "label": receipt.get("label", "positive_variation_bridge"),
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

    parser = argparse.ArgumentParser(description="Validate a positive-variation bridge receipt.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_positive_variation_bridge_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
