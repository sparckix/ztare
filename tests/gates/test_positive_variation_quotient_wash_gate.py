from ztare.gates.positive_variation_quotient_wash_gate import (
    run_positive_variation_quotient_wash_gate,
)


def test_positive_variation_quotient_wash_complete_passes():
    result = run_positive_variation_quotient_wash_gate({
        "label": "selected_transaction_no_wash",
        "net_or_quotient_source_law": "same PDE source quotient fixed before payoff",
        "positive_variation_or_turnover_currency": "gross selected transaction variation",
        "same_source_or_owner_binding": "same selected owner/window",
        "pre_payoff_representative_fixed": "canonical representative fixed before payoff",
        "no_wash_cycle_law": "kernel wash cycles have zero selected positive variation",
        "no_null_cycle_growth": "null cycles cannot grow gross turnover",
        "bounded_positive_variation_from_net_budget": "PV <= C * NetBudget",
        "no_post_payoff_grossing": "grossing rule declared before target deficit",
    })
    assert result["passed"] is True
    assert result["complete"] is True


def test_positive_variation_quotient_wash_rejects_visibility_only():
    result = run_positive_variation_quotient_wash_gate({
        "net_or_quotient_source_law": "same pressure source",
        "positive_variation_or_turnover_currency": "gross selected variation",
        "same_source_or_owner_binding": "same selected window",
        "pressure_visibility_only": "pressure l2 samples visible",
        "rank_reconstruction_only": "rank five reconstruction",
    })
    assert result["passed"] is False
    assert "no_wash_cycle_law" in result["missing_fields"]
    assert "pressure_visibility_only" in result["weak_substitutes"]


def test_positive_variation_quotient_wash_rejects_wash_confuser():
    result = run_positive_variation_quotient_wash_gate({
        "net_or_quotient_source_law": "same PDE source quotient fixed before payoff",
        "positive_variation_or_turnover_currency": "gross selected transaction variation",
        "same_source_or_owner_binding": "same selected owner/window",
        "pre_payoff_representative_fixed": "canonical representative fixed before payoff",
        "no_wash_cycle_law": "claimed no wash law",
        "no_null_cycle_growth": "claimed no null growth",
        "bounded_positive_variation_from_net_budget": "PV <= C * NetBudget",
        "no_post_payoff_grossing": "predeclared grossing",
        "core_sheath_wash_cycle": "N A plus -N A + G keeps net fixed",
    })
    assert result["passed"] is False
    assert any(v["type"] == "wash_cycle_confuser_present" for v in result["violations"])
