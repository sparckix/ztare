from src.ztare.gates.nonadaptive_source_selection_gate import (
    run_nonadaptive_source_selection_gate,
)


def complete_receipt():
    return {
        "label": "topology_extractor_fixed_before_payoff",
        "source_object": "vortex topology event extractor",
        "extractor_or_selection_rule": "tau(level)=event fixed from source trace",
        "source_family": "selected LEI stream",
        "owner_or_carrier_binding": "same owner root",
        "index_or_selection_map": "total on selected prefix",
        "fixed_before_payoff": True,
        "selection_rule_declared_before_target": True,
        "target_not_used_to_define_source": True,
        "timing_receipt": "pre-payoff timestamp",
        "no_post_payoff_selection": True,
    }


def test_complete_nonadaptive_source_selection_receipt_passes():
    result = run_nonadaptive_source_selection_gate(complete_receipt())
    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_label_only_source_selection_rejected():
    result = run_nonadaptive_source_selection_gate({
        "label": "weak",
        "source_label": "topology",
        "natural_candidate": "vortex lines",
    })
    assert result["passed"] is False
    assert "source_object" in result["missing_fields"]
    assert "source_label" in result["weak_substitutes"]


def test_after_the_fact_filter_rejected_even_with_fields():
    receipt = complete_receipt()
    receipt["after_the_fact_filter"] = True
    result = run_nonadaptive_source_selection_gate(receipt)
    assert result["passed"] is False
    assert any(v["type"] == "adaptive_target_selection" for v in result["violations"])
