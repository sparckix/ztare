from pathlib import Path

from ztare.investment.max_caliber_recovery import (
    compile_max_caliber_readiness,
    run_recovery_tournament,
)


def test_contextual_tilt_recovers_injection_without_promoting_the_null():
    root = Path(__file__).parents[2] / "projects/jaggedthoughts_company_state_path_newton"
    result = run_recovery_tournament(
        root / "evidence.txt",
        root / "evidence_holdout.txt",
        root / "evidence_farther_tail.txt",
        trials=16,
    )

    assert result["partition_row_counts"] == {
        "visible": 226, "holdout": 94, "farther_tail": 99,
    }
    assert result["same_feature_offset_logit"]["numerically_equivalent"]
    assert result["injected"]["fitted_theta_sign_recovery_rate"] >= 0.9
    assert result["injected"]["power"] >= 0.75
    assert result["null"]["false_promotion_rate"] <= 0.25
    assert result["recovery_gate"]["status"] == "recovery_gate_failed"
    assert result["signal_authority"] is result["capital_authority"] is False

    readiness = compile_max_caliber_readiness(result, {
        "schema": "jaggedthoughts-strategy-state-transition-join-v1",
        "join_sha256": "join", "fit_qualified_issuer_ids": [],
        "fit_support_floor": {"independent_issuers": 8},
        "overlap_entity_ids": ["RRC"], "event_bundles": [],
    }, {
        "schema": "jaggedthoughts-institutional-learning-schedule-v2",
        "schedule_sha256": "schedule", "actions": [{
            "work_id": "rrc-event", "entity_id": "RRC", "rank": 1,
            "kind": "jaggedthoughts_strategy_event_refinement_research",
        }],
    })
    assert readiness["measurement_recovery_lane"]["selected_existing_job"] is None
    assert readiness["strategy_conditioning_lane"]["selected_existing_job"]["work_id"] == "rrc-event"
    assert readiness["independence_contract"]["event_refinement_changes"] == "strategy_state_transition_join_only"
