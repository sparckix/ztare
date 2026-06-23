from ztare.gates.positive_variation_bridge_gate import run_positive_variation_bridge_gate


def test_positive_variation_bridge_complete_passes():
    result = run_positive_variation_bridge_gate({
        "label": "alpha_to_mu",
        "signed_source": "alphaA",
        "positive_variation_source": "muA",
        "same_carrier": "same event carrier",
        "numeric_domination": "alphaA(E) <= muA(E)",
        "event_scope": "all selected events",
        "fixed_before_payoff": "pre-payoff",
        "no_post_payoff_positive_part": "no posthoc positive part",
        "no_target_deficit_definition": "not defined from target deficit",
    })
    assert result["passed"] is True
    assert result["complete"] is True


def test_positive_variation_bridge_rejects_label_only():
    result = run_positive_variation_bridge_gate({
        "signed_source": "alphaA",
        "positive_variation_source": "muA",
        "positive_variation_label": "muA is positive variation",
        "same_name": "active",
    })
    assert result["passed"] is False
    assert "numeric_domination" in result["missing_fields"]
    assert "positive_variation_label" in result["weak_substitutes"]


def test_positive_variation_bridge_rejects_posthoc_positive_part():
    result = run_positive_variation_bridge_gate({
        "signed_source": "alphaA",
        "positive_variation_source": "muA",
        "same_carrier": "same event carrier",
        "numeric_domination": "alphaA(E) <= muA(E)",
        "event_scope": "selected event",
        "fixed_before_payoff": "pre-payoff",
        "no_post_payoff_positive_part": "no",
        "no_target_deficit_definition": "not from target",
        "posthoc_positive_part": "max(alpha,0) after payoff",
    })
    assert result["passed"] is False
    assert any(v["type"] == "posthoc_positive_part_selection" for v in result["violations"])
