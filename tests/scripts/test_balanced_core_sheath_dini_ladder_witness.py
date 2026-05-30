from projects.ns_millennium_hunt.scripts.balanced_core_sheath_dini_ladder_witness import (
    build_witness,
)


def test_balanced_ladder_pointwise_overflow_payment_fails() -> None:
    witness = build_witness(max_prefix=4, epsilon=0.5, comparison_constant=1.0)

    first = witness["first_pointwise_failure"]
    assert first["n"] == 0
    assert first["overflow_excess"] == 0.5
    assert first["total_cone_variation"] == 2.0
    assert first["pointwise_violates_overflow_payment"] is True


def test_balanced_ladder_prefix_diverges_past_summable_overflow() -> None:
    witness = build_witness(max_prefix=64, epsilon=0.5, comparison_constant=8.0)

    assert witness["first_prefix_failure"] is not None
    assert witness["final_total_cone_variation_prefix"] > witness["final_overflow_prefix"] * 8.0
    assert "one fresh output-scale owner" in witness["owner_model"]
    assert "harmonic" in witness["interpretation"]
