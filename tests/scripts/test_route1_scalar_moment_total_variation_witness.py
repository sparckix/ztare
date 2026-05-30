from projects.ns_millennium_hunt.scripts.route1_scalar_moment_total_variation_witness import (
    build_witness,
)


def test_scalar_projected_moment_can_cancel_while_total_variation_survives() -> None:
    witness = build_witness(max_prefix=4, comparison_constant=100.0)

    first = witness["samples"][0]
    assert first["signed_projected_moment"] == 0.0
    assert first["tracefree_total_variation"] == 2.0
    assert first["prefix_violates_scalar_moment_payment"] is True


def test_scalar_moment_prefix_bound_cannot_pay_harmonic_total_variation() -> None:
    witness = build_witness(max_prefix=64, comparison_constant=8.0)

    assert witness["first_prefix_failure"] is not None
    assert witness["final_signed_projected_moment_prefix"] == 0.0
    assert witness["final_tracefree_total_variation_prefix"] > 8.0
    assert "coercivity/no-sheath" in witness["interpretation"]
    assert "eventRadiusPayment_eq_projectedTracefreeAnnularOutputVariation" in witness["required_repair_field"]
