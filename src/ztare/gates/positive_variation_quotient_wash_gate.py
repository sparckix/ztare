"""Gate for positive-variation claims over quotient/net transaction channels.

A net or quotient source law can identify many representations of the same
source. Positive variation/turnover is not automatically well-defined on that
quotient: wash cycles may keep the net source fixed while making gross positive
turnover arbitrarily large. This gate requires a no-wash/no-null-cycle law or
an injective representative receipt before a bounded net budget can be spent as
bounded positive variation.
"""
from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = {
    "net_or_quotient_source_law",
    "positive_variation_or_turnover_currency",
    "same_source_or_owner_binding",
    "pre_payoff_representative_fixed",
    "no_wash_cycle_law",
    "no_null_cycle_growth",
    "bounded_positive_variation_from_net_budget",
    "no_post_payoff_grossing",
}

WEAK_SUBSTITUTES = {
    "net_identity_only",
    "same_window_label",
    "positive_turnover_label",
    "pressure_visibility_only",
    "rank_reconstruction_only",
    "pre_summed_label_only",
}

WASH_CONFUSER_FIELDS = {
    "wash_cycle_confuser_present",
    "core_sheath_wash_cycle",
    "unbounded_turnover_same_net",
    "null_cycle_growth_witness",
}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "none", "null"}
    return bool(value)


def run_positive_variation_quotient_wash_gate(receipt: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(field for field in REQUIRED_FIELDS if not _truthy(receipt.get(field)))
    weak_hits = sorted(field for field in WEAK_SUBSTITUTES if _truthy(receipt.get(field)))
    confuser_hits = sorted(field for field in WASH_CONFUSER_FIELDS if _truthy(receipt.get(field)))
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
                "net labels, visibility, rank, or pre-summed names do not prove "
                "positive variation is bounded on the quotient"
            ),
        })
    if confuser_hits:
        violations.append({
            "type": "wash_cycle_confuser_present",
            "fields": confuser_hits,
            "message": (
                "a same-net wash/null cycle is visible; prove no_wash_cycle_law "
                "or stop before spending net budget as positive turnover"
            ),
        })
    return {
        "gate": "G-POSITIVE-VARIATION-QUOTIENT-WASH",
        "label": receipt.get("label", "positive_variation_quotient_wash"),
        "passed": not violations,
        "complete": not missing,
        "missing_fields": missing,
        "weak_substitutes": weak_hits,
        "wash_confusers": confuser_hits,
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
        description="Validate a quotient/no-wash receipt for positive-variation currency."
    )
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    args = parser.parse_args(argv)
    result = run_positive_variation_quotient_wash_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
