from projects.ns_millennium_hunt.scripts.total_cone_visibility_reuse_witness import (
    build_witness,
)


def test_visibility_reuse_witness_overflows_fixed_comparison_constant() -> None:
    witness = build_witness(max_prefix=8, comparison_constant=4.0)

    assert witness["first_failure"]["prefix"] == 5
    assert witness["first_failure"]["advertised_bound"] == 4.0
    assert witness["first_failure"]["selected_total_cone_variation"] == 5.0
    assert witness["first_failure"]["violates_visibility_payment"] is True


def test_visibility_reuse_witness_records_no_reuse_missing_field() -> None:
    witness = build_witness(max_prefix=2, comparison_constant=10.0)

    assert "no-reuse same-selected-stream theorem" in witness["interpretation"]
    assert witness["claim_blocked"].startswith("projected stress total variation")
