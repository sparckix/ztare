from ztare.gates.bounded_ratio_support_gate import run_gate


def test_bounded_ratio_support_passes_when_overfills():
    result = run_gate(
        mean_surplus="1/2",
        ratio_upper_bound="3",
        companion_lower_bound="4/5",
        threshold_space_measure="1",
    )

    assert result["passed"] is True
    assert result["support_lower_bound"] == "1/4"
    assert result["overfill_margin"] == "1/20"


def test_bounded_ratio_support_rejects_sparse_high_rho():
    result = run_gate(
        mean_surplus="1/2",
        ratio_upper_bound="101",
        companion_lower_bound="9/10",
        threshold_space_measure="1",
    )

    assert result["passed"] is False
    assert result["support_lower_bound"] == "1/200"
    assert result["overfill_margin"] == "-19/200"
    assert "does not overfill" in result["reason"]


def test_bounded_ratio_support_requires_upper_bound_above_one():
    result = run_gate(
        mean_surplus="1/2",
        ratio_upper_bound="1",
        companion_lower_bound="0",
        threshold_space_measure="1",
    )

    assert result["passed"] is False
    assert result["hard_fail"] is True
    assert "greater than 1" in result["reason"]
