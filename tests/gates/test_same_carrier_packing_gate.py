from ztare.gates.same_carrier_packing_gate import (
    run_same_carrier_packing_gate,
)


def test_same_carrier_packing_flags_label_only_packings() -> None:
    result = run_same_carrier_packing_gate({
        "source_carrier": "metric reconnection tents",
        "target_payment_family": "fresh-frequency tent atoms",
        "packing_label": "Besicovitch packing",
        "finite_budget_label": "finite fresh budget",
    })

    assert result["passed"] is True
    assert result["complete"] is False
    assert "assignment_or_injection_map" in result["missing_fields"]
    assert any(
        v["type"] == "same_carrier_packing_replaced_by_weak_substitutes"
        for v in result["violations"]
    )


def test_same_carrier_packing_accepts_complete_receipt() -> None:
    result = run_same_carrier_packing_gate({
        "source_carrier": "metric reconnection tents",
        "target_payment_family": "fresh-frequency tent atoms",
        "assignment_or_injection_map": "selected event n maps to packed tent atom j(n)",
        "assignment_total_on_prefix": "all selected n<K are assigned",
        "same_carrier_binding": "same pressure/Duhamel carrier",
        "overlap_or_multiplicity_bound": "overlap <= M",
        "finite_prefix_budget": "M * tentAtomBudget <= freshFrequencyPriceBudget",
        "pre_payoff_timing": "packing fixed before payoff",
        "no_nested_reuse": "nested chains are charged once under the packing",
        "no_rebilling_same_atom": "no atom is reused beyond multiplicity M",
    })

    assert result["passed"] is True
    assert result["complete"] is True
    assert result["violations"] == []


def test_same_carrier_packing_blocks_declared_nested_reuse_confuser() -> None:
    result = run_same_carrier_packing_gate(
        {
            "source_carrier": "metric reconnection tents",
            "target_payment_family": "fresh-frequency tent atoms",
            "assignment_or_injection_map": "selected event n maps to packed tent atom j(n)",
            "assignment_total_on_prefix": "all selected n<K are assigned",
            "same_carrier_binding": "same pressure/Duhamel carrier",
            "overlap_or_multiplicity_bound": "overlap <= M",
            "finite_prefix_budget": "M * tentAtomBudget <= freshFrequencyPriceBudget",
            "pre_payoff_timing": "packing fixed before payoff",
            "no_nested_reuse": "nested chains are charged once under the packing",
            "no_rebilling_same_atom": "no atom is reused beyond multiplicity M",
            "known_nested_reuse_confuser": "selected tents are nested across prefixes",
        },
        enforce_block=True,
    )

    assert result["passed"] is False
    assert any(
        v["type"] == "same_carrier_packing_nested_reuse_confuser_declared"
        for v in result["violations"]
    )
