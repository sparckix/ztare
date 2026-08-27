import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.underwriting_ablation import compile_underwriting_ablation_status
from ztare.investment.learning_credit import compile_learning_credit_assignment
from ztare.investment.underwriting_method_policy import (
    compile_underwriting_method_policy,
    select_underwriting_method_route,
)


def _status(block_count: int, values=None):
    process_body = {
        "schema": "jaggedthoughts-forecast-process-bundle-v1",
        "model_identity_complete": True,
        "resolved_model": "gpt-5.6-sol",
    }
    process = {**process_body, "process_bundle_sha256": stable_sha256(process_body)}
    availability_body = {
        "schema": "jaggedthoughts-field-availability-certificate-v1",
        "complete": True,
        "unverified_field_paths": [],
    }
    availability = {
        **availability_body, "certificate_sha256": stable_sha256(availability_body),
    }
    roles = ("typed_quantitative", "typed_plus_fingerprint", "typed_plus_full_research")
    runs = tuple({
        "run_id": f"run-{index}", "sealed_at": "2026-08-01T00:00:00Z",
        "provider": {"process_bundle": process},
        "evidence_packet": {"field_availability": availability},
        "underwriting_information_ablation": {
            "schema": "jaggedthoughts-underwriting-information-ablation-action-v1",
            "status": "sealed_three_arm_forecast",
            "same_model_process_sha256": process["process_bundle_sha256"],
            "arms": [{
                "role": role, "forecast_candidate_id": f"underwriting_{role}",
            } for role in roles],
        },
    } for index in range(block_count))
    values = values or {
        "typed_quantitative": (0.12, 0.24, 0.00),
        "typed_plus_fingerprint": (0.08, 0.16, 0.02),
        "typed_plus_full_research": (0.08, 0.16, 0.02),
    }
    settlements = tuple({
        "run_id": f"run-{index}",
        "evaluated_at": "2026-08-13T00:00:00Z",
        "candidate_scores": [{
            "candidate_id": f"underwriting_{role}",
            "active_return_absolute_error": score[0],
            "underperformance_brier": score[1],
            "active_return_contribution_after_cost": score[2],
        } for role, score in values.items()],
    } for index in range(block_count))
    return compile_underwriting_ablation_status(
        runs, settlements,
        inference_block_ids={f"run-{index}": f"block-{index}" for index in range(block_count)},
    )


def test_underwriting_method_policy_prefers_fingerprint_only_for_future_runs() -> None:
    status = _status(12)
    policy = compile_underwriting_method_policy(
        status, compiled_at="2026-08-14T20:00:00Z",
    )

    assert policy["routing_decision"] == "prefer_fingerprint"
    assert policy["future_arm_allocation"] == {
        "typed_quantitative": 0.1,
        "typed_plus_fingerprint": 0.8,
        "typed_plus_full_research": 0.1,
    }
    assert policy["effective_for_runs_opened_at_or_after"] == "2026-08-14T20:00:00Z"
    assert policy["historical_relabeling_forbidden"] is True
    assert policy["weights_authority"] is policy["capital_authority"] is False

    blocked = select_underwriting_method_route(
        policy, episode_identity="without-credit",
        opened_at="2026-08-15T00:00:00Z",
        current_ablation_status=status,
    )
    assert blocked["route_mode"] == "balanced_ablation"

    credit = compile_learning_credit_assignment(
        research_learning={}, closed_book={"underwriting_ablation": status},
        institutional_learning={}, fund_sleeve_comparison={}, portfolio_policy={},
        underwriting_method_policy=policy,
    )
    earned = [
        row["component_id"] for row in credit["components"] if row["credit_earned"]
    ]
    assert earned == ["underwriting_information_method"]
    routes = [
        select_underwriting_method_route(
            policy, episode_identity=f"episode-{index}",
            opened_at="2026-08-15T00:00:00Z",
            learning_credit_assignment=credit,
            current_ablation_status=status,
        )
        for index in range(64)
    ]
    assert any(row["route_mode"] == "exploration_ablation" for row in routes)
    assert any(row["selected_arms"] == ["typed_plus_fingerprint"] for row in routes)
    assert all(row["capital_authority"] is False for row in routes)

    later_policy = compile_underwriting_method_policy(
        status, compiled_at="2026-08-15T12:00:00Z",
    )
    later_route = select_underwriting_method_route(
        later_policy, episode_identity="later-same-evidence",
        opened_at="2026-08-16T00:00:00Z",
        learning_credit_assignment=credit,
        current_ablation_status=status,
    )
    assert later_route["learning_credit_admitted"] is True

    stale_route = select_underwriting_method_route(
        later_policy, episode_identity="later-new-evidence",
        opened_at="2026-08-16T00:00:00Z",
        learning_credit_assignment=credit,
        current_ablation_status=_status(13),
    )
    assert stale_route["route_mode"] == "balanced_ablation"
    assert stale_route["learning_credit_admitted"] is False

    neutral = _status(12, values={
        role: (0.08, 0.16, 0.02)
        for role in ("typed_quantitative", "typed_plus_fingerprint", "typed_plus_full_research")
    })
    neutral_policy = compile_underwriting_method_policy(
        neutral, compiled_at="2026-08-14T20:00:00Z",
    )
    neutral_credit = compile_learning_credit_assignment(
        research_learning={}, closed_book={"underwriting_ablation": neutral},
        institutional_learning={}, fund_sleeve_comparison={}, portfolio_policy={},
        underwriting_method_policy=neutral_policy,
    )
    neutral_route = select_underwriting_method_route(
        neutral_policy, episode_identity="same-next-episode",
        opened_at="2026-08-15T00:00:00Z",
        learning_credit_assignment=neutral_credit,
        current_ablation_status=neutral,
    )
    assert neutral_policy["routing_decision"] == "continue_balanced"
    assert neutral_credit["earned_component_count"] == 0
    assert neutral_route["selected_arms"] == [
        "typed_quantitative", "typed_plus_fingerprint", "typed_plus_full_research",
    ]


def test_underwriting_method_policy_stays_balanced_without_eight_blocks() -> None:
    status = _status(7)
    policy = compile_underwriting_method_policy(
        status, compiled_at="2026-08-14T20:00:00Z",
    )

    assert policy["routing_decision"] == "continue_balanced"
    assert "minimum_independent_blocks_not_met" in policy["promotion_blockers"]
    with pytest.raises(ValueError, match="valid ablation status"):
        compile_underwriting_method_policy(
            {**status, "inference_block_count": 99},
            compiled_at="2026-08-14T20:00:00Z",
        )
