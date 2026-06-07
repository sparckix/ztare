"""Generic residual-core receipt gate.

This is substrate-neutral plumbing for fine receipt handles.  A caller supplies
a profile with required fields, expected consumers, and confuser field sets.
Substrates such as NS provide the profile in their workbench layer.
"""
from __future__ import annotations

from typing import Any


_PLACEHOLDER_STRINGS = {
    "missing",
    "missing_receipt",
    "not_present",
    "not supplied",
    "not_supplied",
    "not yet derived",
    "not_yet_derived",
    "not yet proven",
    "not_yet_proven",
    "pending",
    "placeholder",
    "todo",
    "tbd",
    "unknown",
    "label_only",
    "label-only",
    "same_source_label_only",
}


def _present(value: Any) -> bool:
    if value in (None, "", [], {}, False):
        return False
    if isinstance(value, str):
        normalized = " ".join(value.strip().lower().split())
        if normalized in _PLACEHOLDER_STRINGS:
            return False
        if normalized.startswith(("missing ", "todo:", "tbd:", "placeholder:")):
            return False
        if normalized.endswith((" missing", " pending", " label only")):
            return False
    if isinstance(value, list):
        return any(_present(item) for item in value)
    if isinstance(value, dict):
        return any(_present(item) for item in value.values())
    return True


def _consumer_matches(value: Any, expected_consumers: list[str]) -> bool:
    if not _present(value):
        return False
    text = str(value)
    return any(expected in text for expected in expected_consumers)


def run_residual_core_receipt_gate(
    rubric_data: dict[str, Any] | None = None,
    *,
    profile: dict[str, Any],
    enforce_block: bool = False,
    expect_receipt: bool = False,
) -> dict[str, Any]:
    """Verify receipts for a configured residual-core edge."""

    rubric_data = rubric_data or {}
    receipt_key = str(profile["receipt_key"])
    receipt_label = str(profile["receipt_label"])
    required_fields = list(profile.get("required_fields") or [])
    expected_consumers = list(profile.get("expected_consumers") or [])
    confuser_sets = list(profile.get("confuser_sets") or [])

    receipts = rubric_data.get(receipt_key) or []
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not isinstance(receipts, list):
        violations.append({
            "type": f"{receipt_label}_receipts_malformed",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": f"{receipt_key} must be a list of dicts",
        })
        receipts = []

    if expect_receipt and not receipts:
        violations.append({
            "type": f"{receipt_label}_receipt_missing",
            "severity": "advisory",
            "reason": (
                f"the {receipt_label} edge was selected, but no "
                f"{receipt_key} were declared"
            ),
        })
        warnings.append(f"{receipt_label} edge selected with no receipt")

    n_complete = 0
    for i, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            violations.append({
                "type": f"{receipt_label}_receipt_malformed",
                "receipt_index": i,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": f"{receipt_key} entries must be dicts",
            })
            continue

        missing = [
            field for field in required_fields
            if not _present(receipt.get(field))
        ]
        if missing:
            violations.append({
                "type": f"{receipt_label}_receipt_incomplete",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "missing_fields": missing,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": str(profile.get("incomplete_reason") or ""),
            })
            warnings.append(
                f"{receipt_key}[{i}] missing: " + ", ".join(missing)
            )
            continue

        confuser_hit = False
        for confuser in confuser_sets:
            fields = list(confuser.get("fields") or [])
            required_absent = list(confuser.get("unless_present") or [])
            present_fields = [
                field for field in fields if _present(receipt.get(field))
            ]
            absent_required = [
                field for field in required_absent
                if not _present(receipt.get(field))
            ]
            if present_fields and absent_required:
                violations.append({
                    "type": str(confuser["type"]),
                    "receipt_index": i,
                    "receipt_name": receipt.get("name", "<unnamed>"),
                    "confuser_fields": present_fields,
                    "unless_present_missing": absent_required,
                    "severity": "blocking" if enforce_block else "advisory",
                    "reason": str(confuser.get("reason") or ""),
                })
                confuser_hit = True
                break
        if confuser_hit:
            continue

        if expected_consumers and not _consumer_matches(
            receipt.get("consumed_by"), expected_consumers
        ):
            violations.append({
                "type": f"wrong_{receipt_label}_consumer",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "severity": "blocking" if enforce_block else "advisory",
                "reason": str(profile.get("wrong_consumer_reason") or ""),
            })
            continue

        n_complete += 1

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = not blocking if enforce_block else True
    summary_parts = [
        f"{len(receipts)} {receipt_label} receipt(s) declared",
        f"{n_complete} complete",
    ]
    if violations:
        summary_parts.append(f"{len(violations)} violation(s)")
    if not enforce_block:
        summary_parts.append("ADVISORY mode")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "n_receipts_declared": len(receipts),
        "n_complete_receipts": n_complete,
        "required_fields": required_fields,
        "expected_consumers": expected_consumers,
        "summary": "; ".join(summary_parts),
    }
