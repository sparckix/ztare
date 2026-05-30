from projects.ns_millennium_hunt.scripts.five_shadow_valuation_budget_reinterpretation_witness import (
    build_witness,
)


def _verdict(witness, name):
    return next(row for row in witness.verdicts if row.budget_reading == name)


def test_final_scalar_visibility_does_not_pay_presummed_valuation() -> None:
    witness = build_witness([10, 100])
    row = _verdict(witness, "final_scalar_visibility_or_signed_shadow_sum")
    assert row.finite_on_harmonic_diagonal_packet is True
    assert row.pays_required_linear_valuation_currency is False
    assert row.killed_by_packet is True


def test_beta_square_budget_stays_finite_but_does_not_pay_linear_valuation() -> None:
    witness = build_witness([10, 100, 1000])
    row = _verdict(witness, "beta_square_or_overflow_currency")
    assert row.finite_on_harmonic_diagonal_packet is True
    assert row.pays_required_linear_valuation_currency is False
    assert witness.rows[-1].beta_square_prefix <= witness.rows[-1].beta_square_upper_bound
    assert witness.rows[-1].carrier_local_absolute_valuation_prefix > witness.rows[0].carrier_local_absolute_valuation_prefix


def test_replay_invariant_budget_identifies_correct_currency_but_not_finite_payer() -> None:
    witness = build_witness([10, 100, 1000])
    row = _verdict(witness, "replay_invariant_shadow_tv_budget")
    assert row.pays_required_linear_valuation_currency is True
    assert row.killed_by_packet is True
    assert "same-carrier fresh no-reuse" in witness.remaining_pde_obligation
