from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from ztare.common.endogenous_residual_discovery import (
    ControllerResidualQuestion,
    EndogenousResidualAuthority,
    EndogenousResidualProposal,
    canonical_controller_output_sha256,
    compile_endogenous_residual_discovery,
    measurement_axis_catalog_sha256,
)
from ztare.common.epistemic_autocatalysis import MeasurementAxis
from ztare.common.wake_sleep_credit_router import MemoryScope


def _axes() -> tuple[MeasurementAxis, ...]:
    return (
        MeasurementAxis("axis-a", 1.0),
        MeasurementAxis("axis-b", 1.0),
        MeasurementAxis("axis-c", 2.0),
    )


def _draft_questions() -> tuple[ControllerResidualQuestion, ...]:
    common_evidence = (
        "settled-failure",
        "source-derivative",
        "source-history",
    )
    rows = (
        ("question-a", "payload-a", (1, 0, 0), Fraction(3, 4)),
        ("question-b", "payload-b", (0, 1, 0), Fraction(2, 3)),
        ("question-c", "payload-c", (0, 0, 1), Fraction(1, 2)),
        ("question-a-copy", "payload-copy", (2, 0, 0), Fraction(1, 4)),
    )
    return tuple(
        ControllerResidualQuestion(
            authority_sha256="draft-authority",
            question_ref=question_ref,
            question_payload_sha256=payload_sha256,
            response_signature=tuple(Fraction(value) for value in signature),
            predicted_information_yield=predicted,
            offline_replay_cost=Fraction(1, 10),
            input_evidence_sha256s=common_evidence,
        )
        for question_ref, payload_sha256, signature, predicted in rows
    )


def _proposal(
    *,
    questions: tuple[ControllerResidualQuestion, ...] | None = None,
    interactions: tuple[tuple[str, ...], ...] = (),
    raw_output_sha256: str = "raw-controller-output",
) -> EndogenousResidualProposal:
    draft = questions or _draft_questions()
    canonical_output = canonical_controller_output_sha256(
        draft,
        modeled_interactions=interactions,
    )
    authority = EndogenousResidualAuthority(
        scope=MemoryScope(
            task_sha256="task",
            controller_sha256="controller-class",
            context_sha256="context",
            choice_set_sha256="choice-set",
            action_vocabulary_sha256="action-vocabulary",
        ),
        measurement_catalog_sha256=measurement_axis_catalog_sha256(_axes()),
        source_response_family_sha256="source-family",
        source_program_sha256="source-program",
        source_derivative_sha256="source-derivative",
        settled_failure_sha256="settled-failure",
        intervention_revision_sha256="intervention-revision",
        primitive_cost_unit="charged-environment-action",
        parent_child_sha256s=("settled-parent-child",),
        generation_index=2,
        controller_instance_sha256="controller-instance",
        stored_parent_response_id="response-parent",
        controller_response_id="response-child",
        source_history_prefix_sha256="source-history",
        source_environment_step=7,
        controller_prompt_sha256="controller-prompt",
        raw_controller_output_sha256=raw_output_sha256,
        canonical_controller_output_sha256=canonical_output,
        allowed_input_evidence_sha256s=(
            "source-family",
            "source-derivative",
            "settled-failure",
            "source-history",
        ),
    )
    bound = tuple(
        replace(row, authority_sha256=authority.sha256) for row in draft
    )
    return EndogenousResidualProposal(
        authority=authority,
        proposal_ref="proposal",
        questions=bound,
        frozen_environment_step=7,
        modeled_interactions=interactions,
    )


def test_controller_output_compiles_rank_three_four_row_assay() -> None:
    receipt = compile_endogenous_residual_discovery(
        _proposal(),
        axes=_axes(),
    )
    payload = receipt.to_receipt()

    assert payload["status"] == "preoutcome_branching_assay_candidate"
    assert payload["raw_question_count"] == 4
    assert payload["direction_quotient_count"] == 3
    assert payload["independent_residual_rank"] == 3
    assert payload["sparse_trajectory_count"] == 4
    assert payload["factorial_trajectory_count"] == 8
    assert payload["strict_trajectory_savings"] is True
    assert payload["live_settlement_required"] is True
    assert payload["compounding_supported"] is False
    assert payload["takeoff_supported"] is False
    assert {row.niche_ref for row in receipt.fission.basis_niches} == {
        "question-a",
        "question-b",
        "question-c",
    }


def test_scalar_copy_does_not_increase_independent_rank() -> None:
    receipt = compile_endogenous_residual_discovery(
        _proposal(),
        axes=_axes(),
    )

    assert len(receipt.proposal.questions) == 4
    assert receipt.fission.independent_offspring_capacity == 3
    assert len(receipt.fission.direction_quotient_classes) == 3


def test_question_cannot_cross_proposal_authority() -> None:
    proposal = _proposal()
    crossed = replace(
        proposal.questions[0],
        authority_sha256="another-proposal-authority",
    )
    with pytest.raises(ValueError, match="crossed proposal authority"):
        replace(proposal, questions=(crossed, *proposal.questions[1:]))


def test_parsed_question_content_must_match_frozen_controller_output() -> None:
    proposal = _proposal()
    changed = replace(
        proposal.questions[0],
        question_payload_sha256="post-hoc-payload",
    )
    with pytest.raises(ValueError, match="canonical controller output"):
        replace(proposal, questions=(changed, *proposal.questions[1:]))


def test_question_cannot_use_descendant_outcome_evidence() -> None:
    proposal = _proposal()
    leaked = replace(
        proposal.questions[0],
        input_evidence_sha256s=(
            *proposal.questions[0].input_evidence_sha256s,
            "descendant-outcome",
        ),
    )
    with pytest.raises(ValueError, match="outside proposal input"):
        replace(proposal, questions=(leaked, *proposal.questions[1:]))


def test_every_question_must_consume_the_settled_failure() -> None:
    proposal = _proposal()
    detached = replace(
        proposal.questions[0],
        input_evidence_sha256s=("source-derivative", "source-history"),
    )
    with pytest.raises(ValueError, match="omitted settled-failure"):
        replace(proposal, questions=(detached, *proposal.questions[1:]))


def test_proposal_cannot_cross_environment_frontier() -> None:
    proposal = _proposal()
    with pytest.raises(ValueError, match="pre-outcome environment frontier"):
        replace(proposal, frozen_environment_step=8)


def test_measurement_catalog_identity_is_exact() -> None:
    proposal = _proposal()
    changed_axes = (
        MeasurementAxis("axis-a", 1.0),
        MeasurementAxis("axis-b", 1.0),
        MeasurementAxis("axis-c", 3.0),
    )
    with pytest.raises(ValueError, match="catalog crossed proposal authority"):
        compile_endogenous_residual_discovery(
            proposal,
            axes=changed_axes,
        )


def test_unknown_predeclared_interaction_is_rejected() -> None:
    proposal = _proposal(interactions=(("question-a", "unknown-question"),))
    with pytest.raises(ValueError, match="crossed residual basis"):
        compile_endogenous_residual_discovery(proposal, axes=_axes())


def test_raw_output_change_changes_downstream_fission_and_schedule_identity() -> None:
    first = compile_endogenous_residual_discovery(
        _proposal(raw_output_sha256="raw-output-one"),
        axes=_axes(),
    )
    second = compile_endogenous_residual_discovery(
        _proposal(raw_output_sha256="raw-output-two"),
        axes=_axes(),
    )

    assert first.proposal.authority.sha256 != second.proposal.authority.sha256
    assert first.fission.authority.sha256 != second.fission.authority.sha256
    assert first.fission.sha256 != second.fission.sha256
    assert first.schedule.sha256 != second.schedule.sha256


def test_float_predictions_are_rejected_before_fission() -> None:
    with pytest.raises(TypeError, match="exact rational"):
        ControllerResidualQuestion(
            authority_sha256="authority",
            question_ref="question",
            question_payload_sha256="payload",
            response_signature=(Fraction(1),),
            predicted_information_yield=0.5,
            offline_replay_cost=Fraction(1),
            input_evidence_sha256s=("evidence",),
        )
