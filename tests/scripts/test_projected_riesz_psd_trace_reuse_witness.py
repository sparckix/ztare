from projects.ns_millennium_hunt.scripts.projected_riesz_psd_trace_reuse_witness import (
    build_witness,
)


def test_projected_riesz_psd_trace_reuse_overflows_fixed_trace_budget() -> None:
    witness = build_witness(max_prefix=8, comparison_constant=4.0)

    assert witness["first_failure"]["prefix"] == 5
    assert witness["first_failure"]["psd_trace_budget"] == 1.0
    assert witness["first_failure"]["projected_variation_prefix"] == 5.0
    assert witness["first_failure"]["violates_psd_trace_payment"] is True


def test_projected_riesz_psd_trace_reuse_names_missing_prefix_inequality() -> None:
    witness = build_witness(max_prefix=2, comparison_constant=10.0)

    assert "selected-prefix owner-preimage inequality" in witness["interpretation"]
    assert witness["claim_blocked"].startswith("one finite PSD trace packet")
