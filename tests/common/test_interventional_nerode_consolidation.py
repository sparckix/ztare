from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from ztare.common.interventional_nerode_consolidation import (
    InterventionalNerodeAuthority,
    canonical_projection_library,
    compile_exact_interventional_fiber,
    compile_interventional_nerode_epoch,
    interventional_nerode_epoch_from_receipt,
    settle_interventional_nerode_holdout,
    stable_sha256,
)


FEATURES = ("control_relation", "pending_waypoint_order_satisfied")


def _authority() -> InterventionalNerodeAuthority:
    return InterventionalNerodeAuthority(
        scope_sha256="scope",
        response_program_sha256="program",
        derivative_sha256="derivative",
        eligibility_rule_sha256="eligibility",
        intervention_set_sha256="interventions",
        utility_measure_sha256="utility",
        restored_prefix_sha256="prefix",
        feature_catalog=FEATURES,
        candidate_projections=canonical_projection_library(FEATURES),
        training_set_sha256="training-set",
        primitive_action_cost=Fraction(20),
        epoch=1,
    )


def _fiber(
    authority: InterventionalNerodeAuthority,
    index: int,
    *,
    phase: str,
    waypoint_satisfied: bool,
    value_delta: Fraction,
    task_delta: int = 0,
    offer_supported: bool = True,
    withhold_supported: bool = False,
):
    return compile_exact_interventional_fiber(
        authority_sha256=authority.sha256,
        parent_state_sha256=f"parent-{phase}-{index}",
        pre_proposal_sha256=f"proposal-{phase}-{index}",
        pre_observation_content_sha256="shared-observation-content",
        exact_micro_basin_sha256=f"basin-{waypoint_satisfied}",
        feature_values=(
            ("control_relation", "other"),
            (
                "pending_waypoint_order_satisfied",
                "true" if waypoint_satisfied else "false",
            ),
        ),
        fork_authority_sha256=f"fork-{phase}-{index}",
        offer_transition_sha256=f"offer-transition-{phase}-{index}",
        withhold_transition_sha256=f"withhold-transition-{phase}-{index}",
        offer_evidence_sha256=f"offer-evidence-{phase}-{index}",
        withhold_evidence_sha256=f"withhold-evidence-{phase}-{index}",
        offer_supported=offer_supported,
        withhold_supported=withhold_supported,
        task_delta=task_delta,
        value_delta=value_delta,
        offer_primitive_action_cost=20,
        withhold_primitive_action_cost=20,
        evidence_refs=(f"evidence:{phase}:{index}",),
        phase=phase,
    )


def test_epoch_keeps_exact_fibers_and_selects_coarsest_predictive_state() -> None:
    authority = _authority()
    training = (
        _fiber(
            authority,
            1,
            phase="training",
            waypoint_satisfied=False,
            value_delta=Fraction(0),
        ),
        _fiber(
            authority,
            2,
            phase="training",
            waypoint_satisfied=True,
            value_delta=Fraction(89, 100),
            task_delta=1,
        ),
    )

    epoch = compile_interventional_nerode_epoch(authority, training)

    assert epoch.selected_projection == ()
    assert len(epoch.states) == 1
    assert epoch.states[0].predicted_value_delta == Fraction(89, 200)
    assert epoch.states[0].predicted_sign == "positive"
    assert len(epoch.states[0].exact_micro_basin_sha256s) == 2
    assert len({row.pre_observation_content_sha256 for row in training}) == 1
    assert len({row.pre_observation_occurrence_sha256 for row in training}) == 2
    receipt = epoch.to_receipt()
    assert receipt["promotion_authorized"] is False
    assert receipt["compounding_supported"] is False
    assert [
        row["fiber_sha256"] for row in receipt["training_fibers"]
    ] == sorted(row.fiber_sha256 for row in training)


def test_fresh_fibers_promote_only_after_sealed_prediction_passes() -> None:
    authority = _authority()
    epoch = compile_interventional_nerode_epoch(authority, (
        _fiber(
            authority,
            1,
            phase="training",
            waypoint_satisfied=False,
            value_delta=Fraction(0),
        ),
        _fiber(
            authority,
            2,
            phase="training",
            waypoint_satisfied=True,
            value_delta=Fraction(89, 100),
            task_delta=1,
        ),
    ))
    holdout = (
        _fiber(
            authority,
            3,
            phase="holdout",
            waypoint_satisfied=False,
            value_delta=Fraction(0),
        ),
        _fiber(
            authority,
            4,
            phase="holdout",
            waypoint_satisfied=True,
            value_delta=Fraction(1, 2),
            task_delta=1,
        ),
    )

    settlement = settle_interventional_nerode_holdout(epoch, holdout)

    assert settlement.promoted
    assert settlement.to_receipt()["promoted_child_count"] == 1
    assert settlement.to_receipt()["supercriticality_supported"] is False
    assert settlement.counterexamples == ()


def test_negative_fresh_effect_refuses_and_emits_new_epoch_counterexample() -> None:
    authority = _authority()
    epoch = compile_interventional_nerode_epoch(authority, (
        _fiber(
            authority,
            1,
            phase="training",
            waypoint_satisfied=False,
            value_delta=Fraction(0),
        ),
        _fiber(
            authority,
            2,
            phase="training",
            waypoint_satisfied=True,
            value_delta=Fraction(1, 2),
        ),
    ))
    holdout = (
        _fiber(
            authority,
            3,
            phase="holdout",
            waypoint_satisfied=False,
            value_delta=Fraction(-1, 4),
        ),
        _fiber(
            authority,
            4,
            phase="holdout",
            waypoint_satisfied=True,
            value_delta=Fraction(1, 2),
        ),
    )

    settlement = settle_interventional_nerode_holdout(epoch, holdout)

    assert not settlement.promoted
    assert not settlement.checks["no_negative_pair_delta"]
    assert settlement.counterexamples[0]["next_epoch_required"] is True
    assert epoch.to_receipt()["promotion_authorized"] is False


def test_training_sign_contradiction_has_no_admissible_projection() -> None:
    authority = _authority()
    with pytest.raises(ValueError, match="no candidate projection"):
        compile_interventional_nerode_epoch(authority, (
            _fiber(
                authority,
                1,
                phase="training",
                waypoint_satisfied=False,
                value_delta=Fraction(-1, 4),
            ),
            _fiber(
                authority,
                2,
                phase="training",
                waypoint_satisfied=True,
                value_delta=Fraction(1, 2),
            ),
        ))


def test_authority_feature_cost_and_content_identity_drift_refuse() -> None:
    authority = _authority()
    fiber = _fiber(
        authority,
        1,
        phase="training",
        waypoint_satisfied=False,
        value_delta=Fraction(0),
    )
    crossed = compile_exact_interventional_fiber(
        authority_sha256="other",
        parent_state_sha256="parent-crossed",
        pre_proposal_sha256="proposal-crossed",
        pre_observation_content_sha256="shared-observation-content",
        exact_micro_basin_sha256="basin-crossed",
        feature_values=fiber.feature_values,
        fork_authority_sha256="fork-crossed",
        offer_transition_sha256="offer-crossed",
        withhold_transition_sha256="withhold-crossed",
        offer_evidence_sha256="offer-evidence-crossed",
        withhold_evidence_sha256="withhold-evidence-crossed",
        offer_supported=True,
        withhold_supported=False,
        task_delta=0,
        value_delta=0,
        offer_primitive_action_cost=20,
        withhold_primitive_action_cost=20,
        evidence_refs=("crossed",),
        phase="training",
    )
    with pytest.raises(ValueError, match="crossed consolidation authority"):
        compile_interventional_nerode_epoch(
            authority,
            (crossed,),
        )
    with pytest.raises(ValueError, match="feature catalog drifted"):
        compile_interventional_nerode_epoch(
            authority,
            (compile_exact_interventional_fiber(
                authority_sha256=authority.sha256,
                parent_state_sha256="parent-drift",
                pre_proposal_sha256="proposal-drift",
                pre_observation_content_sha256="shared-observation-content",
                exact_micro_basin_sha256="basin-drift",
                feature_values=(
                    ("control_relation", "other"),
                    ("post_outcome_feature", "win"),
                ),
                fork_authority_sha256="fork-drift",
                offer_transition_sha256="offer-drift",
                withhold_transition_sha256="withhold-drift",
                offer_evidence_sha256="offer-evidence-drift",
                withhold_evidence_sha256="withhold-evidence-drift",
                offer_supported=True,
                withhold_supported=False,
                task_delta=0,
                value_delta=0,
                offer_primitive_action_cost=20,
                withhold_primitive_action_cost=20,
                evidence_refs=("drift",),
                phase="training",
            ),),
        )
    with pytest.raises(ValueError, match="canonical content identity"):
        replace(fiber, task_delta=1)
    with pytest.raises(ValueError, match="projection library"):
        replace(authority, candidate_projections=((),))


def test_holdout_cannot_reuse_training_evidence() -> None:
    authority = _authority()
    training = (
        _fiber(
            authority,
            1,
            phase="training",
            waypoint_satisfied=False,
            value_delta=Fraction(0),
        ),
        _fiber(
            authority,
            2,
            phase="training",
            waypoint_satisfied=True,
            value_delta=Fraction(1, 2),
        ),
    )
    epoch = compile_interventional_nerode_epoch(authority, training)
    reused = compile_exact_interventional_fiber(
        authority_sha256=authority.sha256,
        parent_state_sha256="fresh-parent",
        pre_proposal_sha256="fresh-proposal",
        pre_observation_content_sha256="shared-observation-content",
        exact_micro_basin_sha256="fresh-basin",
        feature_values=training[0].feature_values,
        fork_authority_sha256="fresh-fork",
        offer_transition_sha256="fresh-offer-transition",
        withhold_transition_sha256="fresh-withhold-transition",
        offer_evidence_sha256=training[0].offer_evidence_sha256,
        withhold_evidence_sha256="fresh-withhold-evidence",
        offer_supported=True,
        withhold_supported=False,
        task_delta=0,
        value_delta=Fraction(1, 2),
        offer_primitive_action_cost=20,
        withhold_primitive_action_cost=20,
        evidence_refs=("fresh",),
        phase="holdout",
    )
    other = _fiber(
        authority,
        4,
        phase="holdout",
        waypoint_satisfied=True,
        value_delta=Fraction(1, 2),
    )

    with pytest.raises(ValueError, match="reused training evidence"):
        settle_interventional_nerode_holdout(epoch, (reused, other))


def test_authority_identity_changes_with_candidate_library() -> None:
    authority = _authority()
    receipt = authority.to_receipt()
    assert receipt["sha256"] == stable_sha256({
        key: value for key, value in receipt.items() if key != "sha256"
    })


def test_sealed_epoch_round_trip_recompiles_and_refuses_drift() -> None:
    authority = _authority()
    epoch = compile_interventional_nerode_epoch(authority, (
        _fiber(
            authority,
            1,
            phase="training",
            waypoint_satisfied=False,
            value_delta=Fraction(0),
        ),
        _fiber(
            authority,
            2,
            phase="training",
            waypoint_satisfied=True,
            value_delta=Fraction(1, 2),
        ),
    ))
    receipt = epoch.to_receipt()

    assert interventional_nerode_epoch_from_receipt(receipt) == epoch

    drifted = dict(receipt)
    drifted["selected_projection"] = ["control_relation"]
    with pytest.raises(ValueError, match="epoch receipt drifted"):
        interventional_nerode_epoch_from_receipt(drifted)
