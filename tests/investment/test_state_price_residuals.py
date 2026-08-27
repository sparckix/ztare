from ztare.common.equivariance import stable_sha256
from ztare.investment.state_price_residuals import compile_state_price_evidence_requests


def _grid(entity_id, status, bounds):
    candidate_sha = entity_id.lower().ljust(64, "c")[:64]
    result_body = {
        "schema": "jaggedthoughts-state-price-result-v1",
        "status": status,
        "residuals": {"closest_positive_asset_residuals": {entity_id: 1.0}},
    }
    result = {**result_body, "result_sha256": stable_sha256(result_body)}
    declaration = {
        "candidate_sha256": candidate_sha,
        "states": [
            {"state_id": "low", "equity_payoff_at_horizon": 50.0},
            {"state_id": "high", "equity_payoff_at_horizon": 150.0},
        ],
    }
    body = {
        "schema": "jaggedthoughts-modeled-payoff-grid-v1",
        "entity_id": entity_id,
        "declaration": declaration,
        "compiled_proposal": {
            "entity_id": entity_id, "candidate_sha256": candidate_sha,
            "state_price_result": result,
        },
        "diagnostics": {"state_probability_bounds": bounds},
    }
    return {**body, "modeled_grid_sha256": stable_sha256(body)}


def test_routes_near_zero_and_infeasible_grids_to_bound_rival_residuals() -> None:
    near_zero = compile_state_price_evidence_requests(_grid(
        "G", "positive_state_prices_feasible", {"low": [0.2, 0.9], "high": [1e-9, 0.8]},
    ))
    infeasible = compile_state_price_evidence_requests(_grid(
        "LEVI", "infeasible_positive_state_prices", None,
    ))

    expected = {
        "missing_state", "overly_narrow_payoff_support",
        "numeraire_mismatch", "model_misspecification",
    }
    assert near_zero["trigger"] == "near_zero_state_probability_bounds"
    assert near_zero["requests"][0]["affected_state_ids"] == ["high"]
    assert {row["residual_kind"] for row in infeasible["requests"]} == expected
    assert all(row["candidate_sha256"] == infeasible["candidate_sha256"] for row in infeasible["requests"])
    assert infeasible["agent_calls_made"] == 0
    assert infeasible["physical_probability_claim"] is False
