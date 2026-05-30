"""G-NONADAPTIVE-SOURCE-SELECTION — pre-payoff source/extractor receipt.

Substrate-neutral gate for routes that introduce a source object, extractor,
section, topology, or selected carrier and then try to spend it downstream. The
gate rejects after-the-fact selection from the target deficit and label-only
source declarations.
"""
from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = {
    "source_object",
    "extractor_or_selection_rule",
    "source_family",
    "owner_or_carrier_binding",
    "index_or_selection_map",
    "fixed_before_payoff",
    "selection_rule_declared_before_target",
    "target_not_used_to_define_source",
    "timing_receipt",
    "no_post_payoff_selection",
}

WEAK_SUBSTITUTES = {
    "source_label",
    "natural_candidate",
    "same_name",
    "after_the_fact_filter",
    "target_deficit_selection",
    "posthoc_extractor",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "none", "null"}
    return bool(value)


def run_nonadaptive_source_selection_gate(receipt: dict[str, Any]) -> dict[str, Any]:
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
            "message": "source labels or after-the-fact filters do not pay nonadaptive source selection",
        })
    if _truthy(receipt.get("after_the_fact_filter")) or _truthy(receipt.get("target_deficit_selection")):
        violations.append({
            "type": "adaptive_target_selection",
            "message": "source/extractor must be fixed before payoff and independent of the target deficit",
        })
    return {
        "gate": "G-NONADAPTIVE-SOURCE-SELECTION",
        "label": receipt.get("label", "nonadaptive_source_selection"),
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

    parser = argparse.ArgumentParser(description="Validate a nonadaptive source-selection receipt.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_nonadaptive_source_selection_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
