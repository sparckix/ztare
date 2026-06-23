from ztare.gates.moment_ratio_surplus_gate import run_gate


def test_moment_ratio_surplus_passes_when_ratio_overfills():
    result = run_gate(
        first_moment_sq="1",
        second_moment_cap="4",
        cheap_boundary_lower_bound="4/5",
        threshold_space_measure="1",
    )

    assert result["passed"] is True
    assert result["ratio_lower_bound"] == "1/4"
    assert result["overfill_margin"] == "1/20"


def test_moment_ratio_surplus_rejects_sparse_threshold_ghost():
    result = run_gate(
        first_moment_sq="1",
        second_moment_cap="100",
        cheap_boundary_lower_bound="9/10",
        threshold_space_measure="1",
    )

    assert result["passed"] is False
    assert result["ratio_lower_bound"] == "1/100"
    assert result["overfill_margin"] == "-9/100"
    assert "finite second moment cap is insufficient" in result["reason"]


def test_moment_ratio_surplus_requires_positive_cap():
    result = run_gate(
        first_moment_sq="1",
        second_moment_cap="0",
        cheap_boundary_lower_bound="0",
        threshold_space_measure="1",
    )

    assert result["passed"] is False
    assert result["hard_fail"] is True
    assert "positive" in result["reason"]
