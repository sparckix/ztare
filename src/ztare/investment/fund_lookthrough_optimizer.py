"""Isolated mixed-integer leaf for minimum-call fund look-through closure."""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any, Mapping


# ponytail: one entry covers repeated read-model builds; use an LRU only if
# interleaved workspaces make misses measurable.
_LAST_SUCCESS: tuple[str, str] | None = None


def solve_minimum_call_cover(payload: Mapping[str, Any]) -> dict[str, Any]:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix

    issuers = sorted(payload["issuers"], key=lambda row: row["entity_id"])
    funds = dict(payload["funds"])
    sleeves = {
        key: sorted(value) for key, value in dict(payload["sleeves"]).items()
    }
    issuer_index = {row["entity_id"]: index for index, row in enumerate(issuers)}
    completable_funds = sorted(
        fund_id for fund_id, row in funds.items() if float(row["disclosed_weight"]) > 0
    )
    fund_index = {
        value: len(issuer_index) + index
        for index, value in enumerate(completable_funds)
    }
    completable_sleeves = sorted(
        sleeve_id for sleeve_id, members in sleeves.items()
        if len(set(members) & set(completable_funds)) >= 2
    )
    if not completable_sleeves:
        return {
            "optimal": False, "selected_entity_ids": [],
            "message": "no sleeve has two funds with disclosed holdings",
            "admissible_sleeve_count": 0,
        }
    sleeve_index = {
        value: len(issuer_index) + len(fund_index) + index
        for index, value in enumerate(completable_sleeves)
    }
    variable_count = len(issuer_index) + len(fund_index) + len(sleeve_index)
    coordinates: list[tuple[int, int, float]] = []
    lower_bounds: list[float] = []
    upper_bounds: list[float] = []

    def add(coefficients: Mapping[int, float], lower: float, upper: float) -> None:
        row = len(lower_bounds)
        coordinates.extend(
            (row, column, float(value))
            for column, value in coefficients.items() if value
        )
        lower_bounds.append(lower)
        upper_bounds.append(upper)

    for fund_id in completable_funds:
        fund = funds[fund_id]
        deficit = max(
            0.0,
            0.5 * float(fund["disclosed_weight"])
            - float(fund["before_company_quality_weight"]),
        )
        coefficients = {
            issuer_index[row["entity_id"]]: float(
                dict(row["fund_memberships"]).get(fund_id, 0.0)
            )
            for row in issuers
            if dict(row["fund_memberships"]).get(fund_id)
        }
        coefficients[fund_index[fund_id]] = -deficit
        add(coefficients, 0.0, np.inf)
    for sleeve_id in completable_sleeves:
        coefficients = {
            fund_index[fund_id]: 1.0
            for fund_id in sleeves[sleeve_id] if fund_id in fund_index
        }
        coefficients[sleeve_index[sleeve_id]] = -2.0
        add(coefficients, 0.0, np.inf)
    add({index: 1.0 for index in sleeve_index.values()}, 1.0, np.inf)

    def constraints() -> LinearConstraint:
        rows, columns, values = zip(*coordinates, strict=True)
        return LinearConstraint(
            coo_matrix(
                (values, (rows, columns)),
                shape=(len(lower_bounds), variable_count),
            ).tocsr(),
            np.asarray(lower_bounds), np.asarray(upper_bounds),
        )

    bounds = Bounds(np.zeros(variable_count), np.ones(variable_count))
    integrality = np.ones(variable_count)
    primary_objective = np.zeros(variable_count)
    primary_objective[:len(issuers)] = 1.0
    primary = milp(
        primary_objective, integrality=integrality, bounds=bounds,
        constraints=constraints(), options={"time_limit": 30.0},
    )
    if not primary.success:
        return {
            "optimal": False, "selected_entity_ids": [],
            "status": int(primary.status), "message": str(primary.message),
        }
    optimum = round(float(primary.fun))
    add({index: 1.0 for index in issuer_index.values()}, 0.0, float(optimum))
    secondary_objective = np.zeros(variable_count)
    for row in issuers:
        secondary_objective[issuer_index[row["entity_id"]]] = -(
            float(row["aggregate_marginal_covered_weight"])
            + 1e-6 * int(row["cross_fund_reuse_memberships"])
        )
    secondary = milp(
        secondary_objective, integrality=integrality, bounds=bounds,
        constraints=constraints(), options={"time_limit": 30.0},
    )
    selected = [
        row["entity_id"] for row in issuers
        if secondary.success and secondary.x[issuer_index[row["entity_id"]]] > 0.5
    ]
    return {
        "optimal": bool(secondary.success),
        "selected_entity_ids": selected,
        "minimum_issuer_calls": optimum,
        "mip_gap": float(primary.mip_gap),
        "status": int(secondary.status),
        "message": str(secondary.message),
        "admissible_sleeve_count": len(completable_sleeves),
    }


def run_minimum_call_cover(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Run the numerical optimizer outside the memory-heavy workspace compiler."""
    global _LAST_SUCCESS
    serialized = json.dumps(payload, sort_keys=True)
    if _LAST_SUCCESS and _LAST_SUCCESS[0] == serialized:
        return json.loads(_LAST_SUCCESS[1])
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ztare.investment.fund_lookthrough_optimizer"],
            input=serialized, text=True,
            capture_output=True, timeout=45, check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {"optimal": False, "selected_entity_ids": [], "message": str(error)}
    if result.returncode:
        return {
            "optimal": False, "selected_entity_ids": [],
            "message": (result.stderr or result.stdout).strip()[:1_000],
        }
    parsed = json.loads(result.stdout)
    _LAST_SUCCESS = (serialized, result.stdout)
    return parsed


def main() -> int:
    print(json.dumps(solve_minimum_call_cover(json.load(sys.stdin)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
