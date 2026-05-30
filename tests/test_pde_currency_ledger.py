from src.ztare.research_director.pde_currency_ledger import currency_ledger_template


def test_dynamic_admissibility_currencies_are_surfaced() -> None:
    ledger = currency_ledger_template("dynamic_reset")

    assert ledger["target_currency"] == "dynamic_reset"
    obligations = ledger["exchange_rate_obligations"]
    produced = ledger["produced_currency"]

    assert "static_packet_to_dynamic_reset_obstruction" in obligations
    assert "sample_transversality_to_uniform_exposure_bound" in obligations
    assert "near_stealth_to_signed_growth_sterility" in obligations
    assert "dynamic_reset_dwell_certificate" in produced
    assert "uniform_transversality_exposure_bound" in produced
    assert "signed_growth_sterility_budget" in produced


def test_angular_cutoff_boundary_invoice_currency_is_surfaced() -> None:
    ledger = currency_ledger_template("angular_boundary_invoice")

    obligations = ledger["exchange_rate_obligations"]
    produced = ledger["produced_currency"]

    assert "angular_cutoff_boundary_to_same_owner_invoice" in obligations
    assert "same_owner_angular_boundary_invoice" in produced
    assert "same owner prefix" in obligations["angular_cutoff_boundary_to_same_owner_invoice"]

def test_coarea_low_slice_lower_payment_exchange_is_surfaced() -> None:
    ledger = currency_ledger_template("coarea_lower_payment")

    obligations = ledger["exchange_rate_obligations"]
    produced = ledger["produced_currency"]

    assert "coarea_low_slice_to_lower_payment" in obligations
    assert "correlated_coarea_slice_payment" in produced
    assert "high-low correlation" in obligations["coarea_low_slice_to_lower_payment"]

def test_linear_moment_budget_to_quadratic_cap_exchange_is_surfaced() -> None:
    ledger = currency_ledger_template("same_prefix_second_moment_cap")

    obligations = ledger["exchange_rate_obligations"]
    produced = ledger["produced_currency"]

    assert "linear_moment_budget_to_quadratic_cap" in obligations
    assert "same_carrier_quadratic_moment_cap" in produced
    assert "first-moment" in obligations["linear_moment_budget_to_quadratic_cap"]
    assert "arbitrarily concentrated spikes" in obligations["linear_moment_budget_to_quadratic_cap"]




def test_boundary_invoice_to_selected_no_reuse_budget_exchange_is_surfaced() -> None:
    ledger = currency_ledger_template("selected_boundary_no_reuse_budget")

    obligations = ledger["exchange_rate_obligations"]
    produced = ledger["produced_currency"]

    assert "boundary_invoice_to_selected_no_reuse_budget" in obligations
    assert "same_stream_boundary_no_reuse_budget" in produced
    assert "finite all-prefix budget" in obligations["boundary_invoice_to_selected_no_reuse_budget"]
    assert "no nested rebilling" in obligations["boundary_invoice_to_selected_no_reuse_budget"]
