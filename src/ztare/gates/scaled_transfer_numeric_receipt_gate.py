"""G-SCALED-TRANSFER-NUMERIC-RECEIPT.

Advisory gate for numeric receipts upstream of scaled carrier transfer.

This catches a general laundering mode: a Prop-level positivity or membership
label is not the pointwise numerical inequality consumed by a transfer theorem.
Substrates supply edge-specific expected quantities, consumers, and confusers
through ``profile``.
"""
from __future__ import annotations

from typing import Any


REQUIRED_RECEIPT_FIELDS = (
    "source_quantity",
    "event_index_map",
    "pointwise_numeric_statement",
    "prop_to_numeric_bridge",
    "consumed_by",
    "downstream_receipt",
)

DEFAULT_PROFILE = {
    "expected_source_quantity": "",
    "expected_event_index_map": "",
    "expected_consumers": [],
    "prop_only_fields": ("prop_membership_input",),
    "wrong_edge_reason": (
        "numeric receipt is not bound to the selected pointwise numeric "
        "transfer edge"
    ),
}


def _present(value: Any) -> bool:
    return value not in (None, "", [], {}, False)


def _matches_expected(value: Any, expected: str) -> bool:
    if not _present(value):
        return False
    text = str(value)
    return text == expected or expected in text


def run_scaled_transfer_numeric_receipt_gate(
    rubric_data: dict[str, Any] | None = None,
    *,
    profile: dict[str, Any] | None = None,
    enforce_block: bool = False,
    expect_receipt: bool = False,
) -> dict[str, Any]:
    """Verify pointwise numeric receipts consumed by scaled-transfer edges."""

    rubric_data = rubric_data or {}
    profile = {**DEFAULT_PROFILE, **(profile or {})}
    expected_source_quantity = str(profile.get("expected_source_quantity") or "")
    expected_event_index_map = str(profile.get("expected_event_index_map") or "")
    expected_consumers = [
        str(x) for x in (profile.get("expected_consumers") or [])
        if str(x).strip()
    ]
    prop_only_fields = tuple(str(x) for x in (
        profile.get("prop_only_fields") or ()
    ))
    receipts = rubric_data.get("scaled_transfer_numeric_receipts") or []
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not isinstance(receipts, list):
        violations.append({
            "type": "scaled_transfer_numeric_receipts_malformed",
            "severity": "blocking" if enforce_block else "advisory",
            "reason": (
                "scaled_transfer_numeric_receipts must be a list of receipt dicts"
            ),
        })
        receipts = []

    if expect_receipt and not receipts:
        violations.append({
            "type": "scaled_transfer_numeric_receipt_missing",
            "severity": "advisory",
            "reason": (
                "a scaled-transfer numeric edge was selected, but no "
                "scaled_transfer_numeric_receipts were declared"
            ),
        })
        warnings.append("scaled-transfer numeric edge selected with no receipt")

    n_complete = 0
    for i, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            violations.append({
                "type": "scaled_transfer_numeric_receipt_malformed",
                "receipt_index": i,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "scaled_transfer_numeric_receipts entries must be dicts",
            })
            continue

        missing = [
            field for field in REQUIRED_RECEIPT_FIELDS
            if not _present(receipt.get(field))
        ]
        if missing:
            violations.append({
                "type": "scaled_transfer_numeric_receipt_incomplete",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "missing_fields": missing,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": (
                    "scaled-transfer numeric receipts require the pointwise "
                    "numeric inequality and the Prop-to-numeric bridge, not "
                    "only selected-node or beta positivity labels"
                ),
            })
            warnings.append(
                "scaled_transfer_numeric_receipts["
                f"{i}] missing: {', '.join(missing)}"
            )
            continue

        prop_only = [
            field for field in prop_only_fields
            if _present(receipt.get(field))
        ]
        if prop_only and not _present(receipt.get("pointwise_numeric_statement")):
            violations.append({
                "type": "prop_only_nonnegativity_laundering",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "prop_only_fields": prop_only,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": (
                    "Prop-level positivity fields do not supply the pointwise "
                    "numeric inequality required by scaled transfer"
                ),
            })
            continue

        wrong_edge: list[str] = []
        if expected_source_quantity and not _matches_expected(
            receipt.get("source_quantity"), expected_source_quantity
        ):
            wrong_edge.append("source_quantity")
        if expected_event_index_map and not _matches_expected(
            receipt.get("event_index_map"), expected_event_index_map
        ):
            wrong_edge.append("event_index_map")
        if expected_consumers and not any(
            _matches_expected(receipt.get("consumed_by"), consumer)
            for consumer in expected_consumers
        ):
            wrong_edge.append("consumed_by")
        if wrong_edge:
            violations.append({
                "type": "wrong_numeric_carrier_or_transfer_edge",
                "receipt_index": i,
                "receipt_name": receipt.get("name", "<unnamed>"),
                "fields": wrong_edge,
                "severity": "blocking" if enforce_block else "advisory",
                "reason": str(profile.get("wrong_edge_reason") or ""),
            })
            continue

        n_complete += 1

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = not blocking if enforce_block else True
    summary_parts = [
        f"{len(receipts)} scaled-transfer numeric receipt(s) declared",
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
        "required_fields": list(REQUIRED_RECEIPT_FIELDS),
        "expected_source_quantity": expected_source_quantity,
        "expected_event_index_map": expected_event_index_map,
        "expected_consumers": expected_consumers,
        "prop_only_fields": list(prop_only_fields),
        "summary": "; ".join(summary_parts),
    }


def _self_test() -> None:
    weak = run_scaled_transfer_numeric_receipt_gate({
        "scaled_transfer_numeric_receipts": [{
            "name": "prop_only",
            "nodeRadiusPositiveOnSelected": "Prop",
            "prop_membership_input": "eventToBadNode lands in selected nodes",
        }],
    })
    assert weak["passed"] is True
    assert any(
        v["type"] == "scaled_transfer_numeric_receipt_incomplete"
        for v in weak["violations"]
    )

    strong = run_scaled_transfer_numeric_receipt_gate({
        "scaled_transfer_numeric_receipts": [{
            "name": "event_node_radius",
            "source_quantity": "carrier.radius",
            "event_index_map": "events.to_node",
            "pointwise_numeric_statement": (
                "forall n, 0 <= carrier.radius (events.to_node n)"
            ),
            "prop_to_numeric_bridge": (
                "selected-node radius theorem plus cofinal incidence"
            ),
            "consumed_by": "RouteTailNonnegative.ofPointwiseRadius",
            "downstream_receipt": "RouteTailNonnegative.nonnegative",
        }],
    }, profile={
        "expected_source_quantity": "carrier.radius",
        "expected_event_index_map": "events.to_node",
        "expected_consumers": ["RouteTailNonnegative.ofPointwiseRadius"],
    })
    assert strong["n_complete_receipts"] == 1
    assert not strong["violations"]


if __name__ == "__main__":
    _self_test()
