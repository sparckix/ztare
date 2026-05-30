"""G-FINITE-PREFIX-SUPPORT -- support-scope leak gate.

General-purpose gate for repairs that replace an impossible all-index claim
with a finite-prefix or support-bounded claim.  It does not prove the estimate.
It rejects the common shortcut where finite-prefix syntax is introduced while
the caller still exports all-index lower bounds, all-prefix budget theorems, or
post-payoff support selection.
"""
from __future__ import annotations

import json
from typing import Any


GATE_ID = "G-FINITE-PREFIX-SUPPORT"

FINITE_SCOPES = {"finite_prefix", "finite_support", "bounded_support", "prefix"}
ALL_INDEX_MARKERS = {
    "all_nat",
    "all_index",
    "all_prefix",
    "forall_nat",
    "unbounded_prefix",
    "global_stream",
}

REQUIRED_FIELDS = (
    "scope_kind",
    "support_or_prefix_witness",
    "lower_bound_scope",
    "budget_scope",
    "prefix_fixed_before_payoff",
    "no_post_payoff_selection",
    "no_all_index_export",
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


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def run_finite_prefix_support_gate(receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate that a finite-prefix repair stays finite-prefix scoped."""
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
            "type": "finite_prefix_support_receipt_incomplete",
            "missing_fields": missing,
            "reason": "finite-prefix repair needs explicit scope, witness, timing, and no-all-index-export receipts",
        })

    scope_kind = _norm(receipt.get("scope_kind"))
    lower_scope = _norm(receipt.get("lower_bound_scope"))
    budget_scope = _norm(receipt.get("budget_scope"))

    if scope_kind and scope_kind not in FINITE_SCOPES:
        violations.append({
            "type": "scope_not_finite_prefix",
            "scope_kind": scope_kind,
            "reason": "scope_kind must be finite_prefix, finite_support, bounded_support, or prefix",
        })

    for field, scope in (
        ("lower_bound_scope", lower_scope),
        ("budget_scope", budget_scope),
    ):
        if scope in ALL_INDEX_MARKERS:
            violations.append({
                "type": "all_index_scope_leak",
                "field": field,
                "scope": scope,
                "reason": "finite-prefix repair cannot retain all-index lower-bound or budget scope",
            })

    exported = [_norm(item) for item in _as_list(receipt.get("exported_theorems"))]
    leaked_exports = [
        item for item in exported
        if any(marker in item for marker in ALL_INDEX_MARKERS)
        or ("selected_depth_bounded" in item and "prefix" not in item and "finite" not in item)
    ]
    if leaked_exports:
        violations.append({
            "type": "all_index_export_declared",
            "exports": leaked_exports,
            "reason": "exported theorem names indicate all-index or unscoped selected-depth leakage",
        })

    explicit_claims = [_norm(item) for item in _as_list(receipt.get("all_index_claims"))]
    explicit_claims = [item for item in explicit_claims if _present(item)]
    if explicit_claims:
        violations.append({
            "type": "all_index_claims_present",
            "claims": explicit_claims,
            "reason": "finite-prefix repair declared all-index claims",
        })

    timing_fields = ("prefix_fixed_before_payoff", "no_post_payoff_selection", "no_all_index_export")
    missing_timing = [field for field in timing_fields if not bool(receipt.get(field))]
    if missing_timing:
        violations.append({
            "type": "finite_prefix_timing_or_export_guard_missing",
            "missing_fields": missing_timing,
            "reason": "prefix/support and exported theorem set must be fixed before payoff and block all-index export",
        })

    return {
        "gate_id": GATE_ID,
        "passed": not violations,
        "complete": not missing,
        "scope_kind": scope_kind,
        "lower_bound_scope": lower_scope,
        "budget_scope": budget_scope,
        "required_fields": list(REQUIRED_FIELDS),
        "missing_fields": missing,
        "violations": violations,
        "summary": (
            "finite-prefix/support repair stays scoped"
            if not violations else
            f"finite-prefix/support repair has {len(violations)} violation(s)"
        ),
    }


def _read_json(path: str) -> dict[str, Any]:
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _self_test() -> None:
    bad = run_finite_prefix_support_gate({
        "scope_kind": "finite_prefix",
        "support_or_prefix_witness": "K",
        "lower_bound_scope": "all_nat",
        "budget_scope": "finite_prefix",
        "prefix_fixed_before_payoff": True,
        "no_post_payoff_selection": True,
        "no_all_index_export": False,
        "exported_theorems": ["selected_depth_bounded"],
    })
    assert bad["passed"] is False
    assert any(v["type"] == "all_index_scope_leak" for v in bad["violations"])
    assert any(v["type"] == "all_index_export_declared" for v in bad["violations"])

    good = run_finite_prefix_support_gate({
        "scope_kind": "finite_prefix",
        "support_or_prefix_witness": "prefixLength = K > 0",
        "lower_bound_scope": "finite_prefix",
        "budget_scope": "finite_prefix",
        "prefix_fixed_before_payoff": True,
        "no_post_payoff_selection": True,
        "no_all_index_export": True,
        "exported_theorems": ["prefix_depth_bounded"],
        "all_index_claims": [],
    })
    assert good["passed"] is True
    assert good["complete"] is True


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate finite-prefix/support scope receipts.")
    parser.add_argument("receipt_json", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"gate_id": GATE_ID, "self_test": "passed"}, indent=2))
        return 0
    result = run_finite_prefix_support_gate(_read_json(args.receipt_json))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
