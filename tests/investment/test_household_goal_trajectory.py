import pytest

from ztare.investment.household_goal_trajectory import (
    HOUSEHOLD_GOAL_TRAJECTORY_INPUT_SCHEMA,
    compile_household_goal_trajectory,
)


def test_household_goal_trajectory_compounds_then_contributes_and_validates_horizon() -> None:
    inputs = {
        "schema": HOUSEHOLD_GOAL_TRAJECTORY_INPUT_SCHEMA,
        "starting_investable_wealth": 100.0,
        "annual_contribution": 10.0,
        "horizon_years": 2,
        "target_wealth": 140.0,
        "nominal_return": 0.10,
    }

    result = compile_household_goal_trajectory(inputs)

    assert result["annual_wealth_path"] == [
        {"year": 0, "wealth": 100.0},
        {"year": 1, "wealth": 120.00000000000001},
        {"year": 2, "wealth": 142.00000000000003},
    ]
    assert result["terminal_gap"] == pytest.approx(2.0)
    assert result["achieved"] is True
    assert result["forecast_claim"] is result["capital_authority"] is False

    inputs["horizon_years"] = 2.5
    with pytest.raises(ValueError, match="integer"):
        compile_household_goal_trajectory(inputs)
