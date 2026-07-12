from ztare.gates.pde_operator_admissibility_gate import (
    run_pde_operator_admissibility_gate,
)


def _paid_receipt() -> dict:
    return {
        "operator_family": "annular Riesz transform / Calderon-Zygmund projection",
        "kernel_or_multiplier_model": "odd kernel with annular bandlimited multiplier",
        "input_output_norms": "same-carrier trace variation to projected trace variation",
        "scale_or_bandlimit": "dyadic annular band fixed before payoff",
        "localization_or_cutoff": "cutoff support inside the selected annular carrier",
        "carrier_identity": "input and output packets share the selected carrier",
        "endpoint_handling": "uniform annular kernel L1 endpoint payment",
        "commutator_or_tail_payment": "cutoff commutator tails paid by same stream",
        "currency_target": "projected tracefree variation payment",
        "hostile_packet_or_counterexample": "low-high leakage packet tested",
        "same_stream_binding": "operator input and output are the same selected stream",
    }


def test_operator_admissibility_gate_accepts_paid_annular_riesz_receipt() -> None:
    result = run_pde_operator_admissibility_gate(_paid_receipt())

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["classification"] == "operator_admissibility_paid"
    assert "riesz" in result["operator_markers"]


def test_operator_admissibility_gate_rejects_raw_cz_substitute() -> None:
    receipt = _paid_receipt()
    receipt["raw_global_CZ_bound"] = "standard global CZ bound"
    receipt["cutoff_commutator_tail_unpaid"] = "tail omitted"

    result = run_pde_operator_admissibility_gate(receipt)

    assert result["passed"] is False
    assert result["complete"] is True
    assert result["rejected_substitutes"] == [
        "raw_global_CZ_bound",
        "cutoff_commutator_tail_unpaid",
    ]


def test_operator_admissibility_gate_reports_missing_fields() -> None:
    result = run_pde_operator_admissibility_gate({
        "operator_family": "Riesz transform",
        "raw_unlocalized_Riesz_measure_target": "unlocalized target",
    })

    assert result["passed"] is False
    assert "kernel_or_multiplier_model" in result["missing_fields"]
    assert "raw_unlocalized_Riesz_measure_target" in result["rejected_substitutes"]
    assert result["next_required_work_units"]


def test_operator_admissibility_gate_emits_tick669_canary_leaf_queue() -> None:
    result = run_pde_operator_admissibility_gate({
        "operator_family": "annular Riesz / Leray projection",
        "kernel_or_multiplier_model": "Calderon-Zygmund kernel",
        "raw_global_CZ_bound": "global CZ bound used as annular payment",
    })

    targets = {
        unit["target"]
        for unit in result["next_required_work_units"]
    }

    assert result["passed"] is False
    assert "uniform_annular_riesz_l1_on_fixed_bandlimited_annular_carrier" in targets
    assert "psd_trace_to_projected_tracefree_payment" in targets
    assert "cutoff_commutator_tail_payment_on_same_stream" in targets
    assert "selected_psd_owner_prefix_no_reuse_budget" in targets
    assert "nonadaptive_annular_event_stream_identity" in targets
