from src.ztare.gates.quotient_minimal_carrier_payment_gate import (
    run_quotient_minimal_carrier_payment_gate,
)


def test_quotient_minimal_carrier_payment_complete_passes():
    result = run_quotient_minimal_carrier_payment_gate({
        "label": "selected_representative_preserves_payment",
        "quotient_source_law": "same net PDE source class",
        "minimal_carrier_definition": "inf PV over same-source representatives",
        "selected_production_functional": "selected high-high cone production",
        "pre_payoff_representative_selector": "canonical selector fixed before payoff",
        "selector_independent_of_target_deficit": "selector uses only source facts",
        "production_preserved_by_selector": "HH(actual) <= C HH(selector(source))",
        "kernel_cycles_zero_selected_production": "ker source cycles have zero selected HH",
        "minimal_carrier_bounds_selected_production": "HH <= C MPV(source)",
    })
    assert result["passed"] is True
    assert result["complete"] is True


def test_quotient_minimal_carrier_payment_rejects_net_bound_only():
    result = run_quotient_minimal_carrier_payment_gate({
        "quotient_source_law": "same source quotient",
        "minimal_carrier_definition": "inf PV over representatives",
        "selected_production_functional": "selected HH",
        "net_budget_bound_only": "MPV <= net budget",
        "wash_eliminated_only": "inf removes wash cycles",
    })
    assert result["passed"] is False
    assert "production_preserved_by_selector" in result["missing_fields"]
    assert "net_budget_bound_only" in result["weak_substitutes"]


def test_quotient_minimal_carrier_payment_rejects_underpayment_confuser():
    result = run_quotient_minimal_carrier_payment_gate({
        "quotient_source_law": "same net PDE source class",
        "minimal_carrier_definition": "inf PV over same-source representatives",
        "selected_production_functional": "selected high-high cone production",
        "pre_payoff_representative_selector": "claimed selector",
        "selector_independent_of_target_deficit": "claimed source-only selector",
        "production_preserved_by_selector": "claimed preservation",
        "kernel_cycles_zero_selected_production": "claimed zero kernel HH",
        "minimal_carrier_bounds_selected_production": "claimed HH <= C MPV",
        "kernel_cycle_carries_selected_production": "admissible k has S k = 0 and HH(k) > 0",
    })
    assert result["passed"] is False
    assert any(
        v["type"] == "quotient_minimal_underpayment_confuser_present"
        for v in result["violations"]
    )
