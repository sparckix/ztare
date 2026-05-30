from projects.ns_millennium_hunt.scripts.tracefree_rank_one_scalar_functional_defect import (
    build_witness,
)


def test_rank_one_scalar_functional_has_tracefree_kernel_witness() -> None:
    witness = build_witness(max_prefix=4)

    first = witness["samples"][0]
    assert first["tensor_diag"] == [0.0, 1.0, -1.0]
    assert first["e1_scalar_sample"] == 0.0
    assert first["trace"] == 0.0
    assert first["tracefree_total_variation_proxy"] == 2.0
    assert first["scalar_prefix_misses_variation"] is True


def test_rank_one_scalar_prefix_misses_harmonic_tracefree_variation() -> None:
    witness = build_witness(max_prefix=64)

    assert witness["single_scalar_rank"] == 1
    assert witness["tracefree_dimension"] == 5
    assert witness["kernel_dimension_lower_bound"] == 4
    assert witness["final_scalar_prefix"] == 0.0
    assert witness["final_tracefree_variation_prefix"] > 8.0
    assert "full tensor-output identity" in witness["interpretation"]
