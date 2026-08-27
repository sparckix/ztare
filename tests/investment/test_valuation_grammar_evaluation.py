from ztare.common.equivariance import stable_sha256
from ztare.investment.valuation_grammar_evaluation import (
    REVISION_MANIFEST_SCHEMA,
    schedule_valuation_grammar_evaluations,
)
from ztare.investment.valuation_grammar_residual_learning import (
    compile_valuation_grammar_residual_learning,
)


def _hashed(body, field):
    return {**body, field: stable_sha256(body)}


def _candidate(entity_id, as_of):
    return _hashed({
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "entity_id": entity_id,
        "entity_kind": "public_equity",
        "as_of": as_of,
        "valuation": {"envelope_sha256": stable_sha256([entity_id, as_of])},
    }, "candidate_sha256")


def _discovery(run_id, as_of, source_sha, candidates):
    return _hashed({
        "schema": "jaggedthoughts-discovery-run-v1",
        "run_id": run_id,
        "as_of": as_of,
        "source_run_sha256": source_sha,
        "candidates": candidates,
    }, "run_sha256")


def _residual(candidate):
    kinds = [
        "missing_state", "overly_narrow_payoff_support",
        "numeraire_mismatch", "model_misspecification",
    ]
    return _hashed({
        "schema": "jaggedthoughts-state-price-residual-set-v1",
        "entity_id": candidate["entity_id"],
        "candidate_sha256": candidate["candidate_sha256"],
        "modeled_grid_sha256": stable_sha256([candidate["entity_id"], "grid"]),
        "state_price_result_sha256": stable_sha256([candidate["entity_id"], "result"]),
        "near_zero_probability_threshold": 1e-6,
        "trigger": "infeasible_positive_state_prices",
        "request_count": len(kinds),
        "requests": [{"residual_kind": kind} for kind in kinds],
        "agent_calls_made": 0,
        "physical_probability_claim": False,
        "expected_return_claim": False,
        "capital_authority": False,
    }, "residual_set_sha256")


def test_schedules_then_activates_four_isolated_future_paired_evaluations() -> None:
    selected = _candidate("OLD", "2026-08-12T00:00:00Z")
    selection = _discovery("selection", "2026-08-12T00:00:00Z", "s" * 64, [selected])
    learning = compile_valuation_grammar_residual_learning(
        [_residual(selected)], compiled_at="2026-08-13T00:00:00Z",
    )

    pending = schedule_valuation_grammar_evaluations(
        learning, selection, scheduled_at="2026-08-13T00:00:00Z",
    )
    assert pending["evaluation_count"] == 4
    assert pending["ready_count"] == 0
    assert all(row["activation_requirements"] == [
        "strictly_new_discovery_and_source_epoch", "one_versioned_revision_manifest",
    ] for row in pending["evaluations"])

    future = _discovery(
        "future", "2026-08-14T00:00:00Z", "f" * 64,
        [_candidate(f"NEW-{index}", "2026-08-14T00:00:00Z") for index in range(4)],
    )
    manifests = []
    for conjecture in learning["conjectures"]:
        manifests.append(_hashed({
            "schema": REVISION_MANIFEST_SCHEMA,
            "conjecture_id": conjecture["conjecture_id"],
            "conjecture_sha256": conjecture["conjecture_sha256"],
            "revision_kind": conjecture["revision_kind"],
            "base_grammar_contract_sha256": learning["valuation_grammar_contract_sha256"],
            "affected_ast_operators": conjecture["affected_ast_operators"],
            "affected_ast_terminals": conjecture["affected_ast_terminals"],
            "revision_count": 1,
            "implementation_ref": f"revision-executor:{conjecture['revision_kind']}@1",
            "implementation_sha256": stable_sha256([conjecture["revision_kind"], "implementation"]),
            "revision_delta_sha256": stable_sha256([conjecture["revision_kind"], "delta"]),
            "automatic_revision_activation": False,
            "security_ranking_use": False,
            "capital_authority": False,
        }, "revision_manifest_sha256"))

    active = schedule_valuation_grammar_evaluations(
        learning, selection, future_discovery=future, revision_manifests=manifests,
        scheduled_at="2026-08-13T00:00:00Z",
    )
    assert active["ready_count"] == 4
    cohort_ids = {row["common_candidate_cohort_sha256"] for row in active["evaluations"]}
    assert len(cohort_ids) == 1
    assert all(row["revision_arm"]["exactly_one_revision"] for row in active["evaluations"])
    assert active["paired_result_contract"]["out_of_sample_settlement"]["nullable_until_due"]
    assert all(row["paired_result_contract_sha256"] == active["paired_result_contract"]["result_contract_sha256"] for row in active["evaluations"])
    assert all(row["historical_retrofit_allowed"] is False for row in active["evaluations"])
    assert active["security_ranking_use"] is False
