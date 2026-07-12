from ztare.pde.gate_runner import run_pde_gate
from ztare.pde.work_order import build_pde_leaf_work_order


def _paid_payload() -> dict:
    return {
        "label": "valuation_budget_constructor_defines_streams",
        "equality_target": "eventRadiusPayment = targetCharge",
        "left_stream": "hSource.eventRadiusPayment",
        "right_stream": "budget.targetCharge",
        "provenance_kind": "constructor_definitional_assignment",
        "constructor_or_theorem": (
            "TraceFreeL2ValuationC7CofinalOwnerBudget."
            "ofC7PackingOwnerPreimageAndFiveFrameSource"
        ),
        "generated_fields": [
            "budget.angularEventPay",
            "budget.targetCharge",
            "source.tracefreeValuationPay",
        ],
        "constructor_body_assignments": {
            "angularEventPay": "hSource.tracefreeValuationPay",
            "targetCharge": "hSource.tracefreeValuationPay",
        },
        "source_binding": "hSameRoute binds eventRadiusPayment to routeActiveTail",
        "anti_proxy_or_anti_laundering_fields": [
            "C7PackingOwnerPreimageReceipt",
            "notBesovBVProductL2OrCFImport",
            "sourceSigmaAlgebraMatchesSelectedAnnularOwnerFibers",
        ],
        "hostile_packet_or_confuser": "diagonalDiniReplayOverflow",
        "proof_boundary": (
            "passes only for the C7 owner-preimage constructor; arbitrary "
            "TraceFreeL2ValuationC7CofinalOwnerBudget field projection is not credit"
        ),
    }


def test_equality_provenance_gate_accepts_constructor_defined_streams() -> None:
    result = run_pde_gate("G-PDE-EQUALITY-PROVENANCE", _paid_payload())

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["result"]["classification"] == "equality_provenance_paid"
    assert result["result"]["constructor_body_assignments_present"] is True


def test_equality_provenance_gate_rejects_record_field_projection() -> None:
    payload = _paid_payload()
    payload["provenance_kind"] = "record_field_projection"
    payload.pop("constructor_body_assignments")
    payload["field_projection_only"] = True
    payload["assumed_record_field_only"] = True

    result = run_pde_gate("G-PDE-EQUALITY-PROVENANCE", payload)

    assert result["passed"] is False
    assert result["result"]["classification"] == "equality_provenance_unpaid"
    assert "field_projection_only" in result["rejected_substitutes"]
    assert any(
        violation["type"] == "equality_provenance_kind_rejected"
        for violation in result["violations"]
    )
    assert result["next_required_work_units"]


def test_pec_l_work_order_includes_equality_provenance_gate() -> None:
    work_order = build_pde_leaf_work_order(
        target="event-radius target-charge identity",
        op_id="pec_l",
    )
    gate_ids = {gate["gate_id"] for gate in work_order["gate_requirements"]}

    assert "G-PDE-EQUALITY-PROVENANCE" in gate_ids
