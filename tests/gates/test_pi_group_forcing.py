from src.ztare.gates.pi_group_forcing import run_pi_group_forcing


def test_dimensionless_target_with_dimensionless_subset_is_ambiguous_not_crash() -> None:
    result = run_pi_group_forcing(
        quantity_dim={},
        subset_dims={"angular_collar_width": {}, "angular_derivative_scale": {}},
    )

    assert result["forced"] is False
    assert result["ambiguous"] is True
    assert result["needs_independent_constant"] is False
    assert "dimensionless" in result["reason"]


def test_heat_length_is_dimensionally_forced() -> None:
    result = run_pi_group_forcing(
        quantity_dim={"L": 1},
        subset_dims={"nu": {"L": 2, "T": -1}, "t": {"T": 1}},
    )

    assert result["forced"] is True
    assert result["exponents"] == {"nu": "1/2", "t": "1/2"}


def test_subset_dims_accepts_sequence_shape() -> None:
    result = run_pi_group_forcing(
        quantity_dim={"L": 1},
        subset_dims=[{"L": 2, "T": -1}, {"T": 1}],
    )

    assert result["forced"] is True
    assert result["exponents"] == {"x0": "1/2", "x1": "1/2"}

