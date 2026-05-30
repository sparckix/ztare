from src.ztare.gates.scaled_transfer_numeric_receipt_gate import (
    run_scaled_transfer_numeric_receipt_gate,
)


def test_scaled_transfer_numeric_gate_flags_prop_only_radius_receipt() -> None:
    result = run_scaled_transfer_numeric_receipt_gate({
        "scaled_transfer_numeric_receipts": [{
            "name": "prop_only_radius",
            "nodeRadiusPositiveOnSelected": "Prop",
            "prop_membership_input": "eventToBadNode lands in selected nodes",
        }],
    })

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 0
    assert any(
        v["type"] == "scaled_transfer_numeric_receipt_incomplete"
        and "pointwise_numeric_statement" in v["missing_fields"]
        for v in result["violations"]
    )


def test_scaled_transfer_numeric_gate_accepts_event_node_radius_receipt() -> None:
    result = run_scaled_transfer_numeric_receipt_gate({
        "scaled_transfer_numeric_receipts": [{
            "name": "event_node_radius",
            "source_quantity": "hCarrier.nodeRadius",
            "event_index_map": "hEvents.eventToBadNode",
            "pointwise_numeric_statement": (
                "forall n, 0 <= hCarrier.nodeRadius (hEvents.eventToBadNode n)"
            ),
            "prop_to_numeric_bridge": (
                "selected-node radius theorem plus cofinal incidence"
            ),
            "consumed_by": (
                "C7RouteActiveTailNonnegativeReceipt."
                "ofPointwiseEventNodeRadiusNonnegative"
            ),
            "downstream_receipt": (
                "C7RouteActiveTailNonnegativeReceipt.routeActiveTail_nonnegative"
            ),
        }],
    })

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 1
    assert result["violations"] == []


def test_scaled_transfer_numeric_gate_blocks_wrong_edge_when_enforced() -> None:
    result = run_scaled_transfer_numeric_receipt_gate(
        {
            "scaled_transfer_numeric_receipts": [{
                "name": "wrong_quantity",
                "source_quantity": "hBeta.betaNumber",
                "event_index_map": "hEvents.eventToBadNode",
                "pointwise_numeric_statement": "forall n, 0 <= beta n",
                "prop_to_numeric_bridge": "beta square is nonnegative",
                "consumed_by": (
                    "C7RouteActiveTailNonnegativeReceipt."
                    "ofPointwiseEventNodeRadiusNonnegative"
                ),
                "downstream_receipt": (
                    "C7RouteActiveTailNonnegativeReceipt."
                    "routeActiveTail_nonnegative"
                ),
            }],
        },
        profile={
            "expected_source_quantity": "hCarrier.nodeRadius",
            "expected_event_index_map": "hEvents.eventToBadNode",
            "expected_consumers": [
                "C7RouteActiveTailNonnegativeReceipt."
                "ofPointwiseEventNodeRadiusNonnegative"
            ],
        },
        enforce_block=True,
    )

    assert result["passed"] is False
    assert any(
        v["type"] == "wrong_numeric_carrier_or_transfer_edge"
        for v in result["violations"]
    )
