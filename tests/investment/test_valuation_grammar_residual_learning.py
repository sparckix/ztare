from ztare.common.equivariance import stable_sha256
from ztare.investment.valuation_grammar_residual_learning import (
    compile_valuation_grammar_residual_learning,
)


def _residual(entity_id, residual_kinds, trigger):
    body = {
        "schema": "jaggedthoughts-state-price-residual-set-v1",
        "entity_id": entity_id,
        "candidate_sha256": entity_id.lower().ljust(64, "c")[:64],
        "modeled_grid_sha256": entity_id.lower().ljust(64, "g")[:64],
        "state_price_result_sha256": entity_id.lower().ljust(64, "r")[:64],
        "near_zero_probability_threshold": 1e-6,
        "trigger": trigger,
        "request_count": len(residual_kinds),
        "requests": [{"residual_kind": kind} for kind in residual_kinds],
        "agent_calls_made": 0,
        "physical_probability_claim": False,
        "expected_return_claim": False,
        "capital_authority": False,
    }
    return {**body, "residual_set_sha256": stable_sha256(body)}


def test_aggregates_support_and_counterexamples_into_future_only_conjectures() -> None:
    learning = compile_valuation_grammar_residual_learning([
        _residual("A", ["missing_state", "model_misspecification"], "infeasible_positive_state_prices"),
        _residual("B", ["missing_state"], "near_zero_state_probability_bounds"),
        _residual("C", [], None),
    ], compiled_at="2026-08-13T00:00:00Z")

    conjecture = next(row for row in learning["conjectures"] if row["residual_kind"] == "missing_state")
    assert conjecture["revision_kind"] == "add_state_axis"
    assert conjecture["support_count"] == 2
    assert conjecture["counterexample_count"] == 1
    assert conjecture["counterexamples"][0]["entity_id"] == "C"
    assert "present_value" in conjecture["affected_ast_operators"]
    assert conjecture["future_evaluation_contract"]["historical_retrofit_allowed"] is False
    assert learning["auto_modifies_grammar"] is False
    assert learning["security_ranking_use"] is False
