from src.ztare.gates.finite_prefix_selection_gate import run_gate


def test_finite_prefix_selection_passes_with_paid_source_contract():
    result = run_gate(
        boundary=["1/4", "3/4"],
        interface=["1/2", "1/2"],
        same_source_family=True,
        prefix_fixed_before_payoff=True,
        boundary_interface_units_aligned=True,
        no_post_payoff_selection=True,
        interface_floor="1/2",
    )

    assert result["passed"] is True
    assert result["boundary_prefix_sum"] == "1"
    assert result["interface_prefix_sum"] == "1"
    assert result["witness_indices"] == [1]
    assert result["payment_floor_witness_indices"] == [1]
    assert result["conclusion_strength"] == "boundary_pays_interface_floor"


def test_finite_prefix_selection_rejects_post_payoff_bias():
    result = run_gate(
        boundary=["1/4", "3/4"],
        interface=["1/2", "1/2"],
        same_source_family=True,
        prefix_fixed_before_payoff=False,
        boundary_interface_units_aligned=True,
        no_post_payoff_selection=False,
    )

    assert result["passed"] is False
    assert "prefix_fixed_before_payoff" in result["missing_receipts"]
    assert "no_post_payoff_selection" in result["missing_receipts"]


def test_finite_prefix_selection_rejects_wrong_prefix_inequality_direction():
    result = run_gate(
        boundary=["1/4", "1/4"],
        interface=["1/2", "1/2"],
        same_source_family=True,
        prefix_fixed_before_payoff=True,
        boundary_interface_units_aligned=True,
        no_post_payoff_selection=True,
    )

    assert result["passed"] is False
    assert result["prefix_comparison_holds"] is False
    assert result["witness_indices"] == []
    assert "interface sum exceeds" in result["reason"]


def test_finite_prefix_selection_rejects_zero_interface_payment_witness():
    result = run_gate(
        boundary=["1/10", "2"],
        interface=["1", "0"],
        same_source_family=True,
        prefix_fixed_before_payoff=True,
        boundary_interface_units_aligned=True,
        no_post_payoff_selection=True,
        interface_floor="1/2",
    )

    assert result["passed"] is False
    assert result["witness_indices"] == [1]
    assert result["payment_floor_witness_indices"] == []
    assert "interface floor" in result["reason"]
