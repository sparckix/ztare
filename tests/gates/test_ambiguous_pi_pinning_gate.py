from src.ztare.gates.ambiguous_pi_pinning_gate import run_gate


def test_nonambiguous_pi_needs_no_pinning_receipt():
    result = run_gate(ambiguous=False, receipts={})
    assert result["passed"] is True
    assert result["ambiguous"] is False


def test_ambiguous_pi_requires_physical_pinning_receipt():
    result = run_gate(ambiguous=True, receipts={"physical_pinning_law": "R <= 1 + C"})
    assert result["passed"] is False
    kinds = [v["type"] for v in result["violations"]]
    assert "missing_pi_pinning_receipts" in kinds


def test_ambiguous_pi_accepts_complete_pinning_receipt():
    result = run_gate(
        ambiguous=True,
        receipts={
            "physical_pinning_law": "active-scale Reynolds ratio controls surplus fraction",
            "pinning_identity_type": "active_scale_reynolds",
            "source_bound_statement": "eta <= R - 1 <= C",
            "fixed_before_payoff": True,
            "same_carrier_or_scope": True,
            "not_dimensional_analysis_only": True,
            "consumed_by": "Level412 eta*A owner-root payment",
        },
    )
    assert result["passed"] is True


def test_ambiguous_pi_accepts_active_scale_channel_estimate_receipt():
    result = run_gate(
        ambiguous=True,
        receipts={
            "physical_pinning_law": "active-scale Reynolds excess paid by pre-payoff channel coefficient",
            "pinning_identity_type": "active_scale_reynolds_channel_estimate",
            "source_bound_statement": "eta*A <= c_eff*A <= I <= B",
            "fixed_before_payoff": True,
            "same_carrier_or_scope": True,
            "not_dimensional_analysis_only": True,
            "consumed_by": "SameOwnerEffectiveInvoiceBudgetBridge",
        },
    )
    assert result["passed"] is True
