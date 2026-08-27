"""Deterministic, ephemeral household goal trajectory."""

from __future__ import annotations

import math
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import require_finite


HOUSEHOLD_GOAL_TRAJECTORY_INPUT_SCHEMA = "jaggedthoughts-household-goal-trajectory-input-v1"
HOUSEHOLD_GOAL_TRAJECTORY_SCHEMA = "jaggedthoughts-household-goal-trajectory-v1"


def compile_household_goal_trajectory(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one declared annual return; this does not estimate or forecast it."""
    expected_fields = {
        "schema", "starting_investable_wealth", "annual_contribution",
        "horizon_years", "target_wealth", "nominal_return",
    }
    if set(raw) != expected_fields:
        raise ValueError("household goal trajectory requires its exact six input fields")
    if raw.get("schema") != HOUSEHOLD_GOAL_TRAJECTORY_INPUT_SCHEMA:
        raise ValueError(
            f"household goal trajectory schema must be {HOUSEHOLD_GOAL_TRAJECTORY_INPUT_SCHEMA}"
        )
    for field in expected_fields - {"schema"}:
        if isinstance(raw.get(field), bool):
            raise ValueError(f"{field} must be numeric, not boolean")
    start = require_finite(raw.get("starting_investable_wealth"), "starting_investable_wealth")
    contribution = require_finite(raw.get("annual_contribution"), "annual_contribution")
    target = require_finite(raw.get("target_wealth"), "target_wealth")
    rate = require_finite(raw.get("nominal_return"), "nominal_return")
    raw_horizon = require_finite(raw.get("horizon_years"), "horizon_years")
    horizon = int(raw_horizon)
    if start < 0 or contribution < 0 or target <= 0:
        raise ValueError("wealth and contribution must be nonnegative; target must be positive")
    if isinstance(raw.get("horizon_years"), bool) or raw_horizon != horizon or not 1 <= horizon <= 100:
        raise ValueError("horizon_years must be an integer in [1, 100]")
    if not -1 < rate <= 10:
        raise ValueError("nominal_return must be greater than -1 and no more than 10")

    wealth = start
    path = [{"year": 0, "wealth": wealth}]
    for year in range(1, horizon + 1):
        wealth = wealth * (1.0 + rate) + contribution
        if not math.isfinite(wealth):
            raise ValueError("household goal trajectory overflowed")
        path.append({"year": year, "wealth": wealth})
    gap = wealth - target
    body = {
        "schema": HOUSEHOLD_GOAL_TRAJECTORY_SCHEMA,
        "inputs": {
            "starting_investable_wealth": start,
            "annual_contribution": contribution,
            "horizon_years": horizon,
            "target_wealth": target,
            "nominal_return": rate,
        },
        "recurrence": {
            "operator": "annual_compound_then_contribute",
            "contribution_timing": "year_end",
        },
        "annual_wealth_path": path,
        "terminal_wealth": wealth,
        "terminal_gap": gap,
        "achieved": wealth >= target,
        "forecast_claim": False,
        "recommendation_claim": False,
        "capital_authority": False,
        "persistence": "none",
        "boundary": (
            "The after-tax nominal return is a user-declared scenario input, not an estimate "
            "or forecast. The path models investable portfolio wealth only."
        ),
    }
    return {**body, "trajectory_sha256": stable_sha256(body)}


__all__ = [
    "HOUSEHOLD_GOAL_TRAJECTORY_INPUT_SCHEMA",
    "HOUSEHOLD_GOAL_TRAJECTORY_SCHEMA",
    "compile_household_goal_trajectory",
]
