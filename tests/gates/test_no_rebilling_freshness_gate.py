from src.ztare.gates.no_rebilling_freshness_gate import (
    run_no_rebilling_freshness_gate,
)


def complete_receipt():
    return {
        "label": "selected_level_distinct_topology_events",
        "selected_units": "selected levels n<N",
        "payment_atoms": "topology events tau(n)",
        "assignment_map": "n -> tau(n)",
        "assignment_total_on_prefix": "all n<N mapped",
        "distinctness_or_disjointness": "tau injective on prefix",
        "no_rebilling_same_atom": "same topology event not reused",
        "prefix_budget_bound": "sum costs <= TopBudget",
        "fixed_before_payoff": "pre-payoff",
        "same_owner_or_source": "same selected LEI owner",
        "overlap_or_multiplicity_bound": "multiplicity <= 1",
    }


def test_complete_no_rebilling_receipt_passes():
    result = run_no_rebilling_freshness_gate(complete_receipt())
    assert result["passed"] is True
    assert result["missing_fields"] == []


def test_budget_label_only_rejected():
    result = run_no_rebilling_freshness_gate({
        "label": "weak",
        "finite_budget_label": "finite budget",
        "freshness_label": "fresh",
    })
    assert result["passed"] is False
    assert "assignment_map" in result["missing_fields"]
    assert "finite_budget_label" in result["weak_substitutes"]


def test_same_atom_reuse_rejected_even_with_fields():
    receipt = complete_receipt()
    receipt["same_atom_reused_across_levels"] = True
    result = run_no_rebilling_freshness_gate(receipt)
    assert result["passed"] is False
    assert any(v["type"] == "same_atom_reused_across_levels" for v in result["violations"])


def test_missing_strings_count_as_absent():
    receipt = complete_receipt()
    receipt["assignment_map"] = "missing: no assignment for tail atom"
    receipt["no_rebilling_same_atom"] = "not supplied: overlap proof owed"
    result = run_no_rebilling_freshness_gate(receipt)
    assert result["passed"] is False
    assert "assignment_map" in result["missing_fields"]
    assert "no_rebilling_same_atom" in result["missing_fields"]
