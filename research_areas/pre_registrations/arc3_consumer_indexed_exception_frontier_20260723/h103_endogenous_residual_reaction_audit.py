#!/usr/bin/env python3
"""Run H103's pre-registered offline proposal-to-assay discriminator."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.endogenous_residual_discovery import (
    ControllerResidualQuestion,
    EndogenousResidualAuthority,
    EndogenousResidualProposal,
    canonical_controller_output_sha256,
    compile_endogenous_residual_discovery,
    measurement_axis_catalog_sha256,
)
from ztare.common.epistemic_autocatalysis import (
    MeasurementAxis,
    stable_sha256,
)
from ztare.common.wake_sleep_credit_router import MemoryScope


BASE = Path(__file__).resolve().parent
H97_RUNTIME = (
    BASE
    / "h97_causal_response_derivative/live_attempt_03_runtime_receipt.json"
)


def axes() -> tuple[MeasurementAxis, ...]:
    return (
        MeasurementAxis("failure-mode-discrimination", 1.0),
        MeasurementAxis("controller-plan-change", 1.0),
        MeasurementAxis("external-task-delta", 2.0),
    )


def draft_questions() -> tuple[ControllerResidualQuestion, ...]:
    evidence = (
        "h95-response-family",
        "h97-source-derivative",
        "h96-settled-failure",
        "h97-source-history-prefix",
    )
    rows = (
        (
            "residual-contract-consumption",
            "payload-contract-consumption",
            (1, 0, 0),
            Fraction(3, 4),
        ),
        (
            "residual-plan-revision",
            "payload-plan-revision",
            (0, 1, 0),
            Fraction(2, 3),
        ),
        (
            "residual-external-effect",
            "payload-external-effect",
            (0, 0, 1),
            Fraction(1, 2),
        ),
        (
            "residual-contract-copy",
            "payload-contract-copy",
            (2, 0, 0),
            Fraction(1, 4),
        ),
    )
    return tuple(
        ControllerResidualQuestion(
            authority_sha256="unbound-controller-output",
            question_ref=question_ref,
            question_payload_sha256=payload_sha256,
            response_signature=tuple(Fraction(value) for value in signature),
            predicted_information_yield=predicted,
            offline_replay_cost=Fraction(1, 10),
            input_evidence_sha256s=evidence,
        )
        for question_ref, payload_sha256, signature, predicted in rows
    )


def proposal(
    *,
    raw_output_sha256: str = "fixture-controller-raw-output",
    interactions: tuple[tuple[str, ...], ...] = (),
) -> EndogenousResidualProposal:
    draft = draft_questions()
    canonical_output = canonical_controller_output_sha256(
        draft,
        modeled_interactions=interactions,
    )
    owner = EndogenousResidualAuthority(
        scope=MemoryScope(
            task_sha256="h97-frozen-task",
            controller_sha256="gpt-5.6-sol:xhigh:all-turns",
            context_sha256="h97-descendant-context",
            choice_set_sha256="arc3-four-action-choice-set",
            action_vocabulary_sha256="arc3-four-action-vocabulary",
        ),
        measurement_catalog_sha256=measurement_axis_catalog_sha256(axes()),
        source_response_family_sha256="h95-response-family",
        source_program_sha256="h95-common-response-program",
        source_derivative_sha256="h97-source-derivative",
        settled_failure_sha256="h96-settled-failure",
        intervention_revision_sha256="h97-causal-intervention-revision",
        primitive_cost_unit="charged-environment-action",
        parent_child_sha256s=("h95-settled-parent",),
        generation_index=2,
        controller_instance_sha256="fixture-controller-instance",
        stored_parent_response_id="fixture-stored-parent-response",
        controller_response_id="fixture-descendant-controller-response",
        source_history_prefix_sha256="h97-source-history-prefix",
        source_environment_step=7,
        controller_prompt_sha256="fixture-controller-prompt",
        raw_controller_output_sha256=raw_output_sha256,
        canonical_controller_output_sha256=canonical_output,
        allowed_input_evidence_sha256s=(
            "h95-response-family",
            "h97-source-derivative",
            "h96-settled-failure",
            "h97-source-history-prefix",
        ),
    )
    questions = tuple(
        replace(row, authority_sha256=owner.sha256) for row in draft
    )
    return EndogenousResidualProposal(
        authority=owner,
        proposal_ref="h103-fixture-controller-proposal",
        questions=questions,
        frozen_environment_step=7,
        modeled_interactions=interactions,
    )


def caught(label, fn) -> dict:
    try:
        fn()
    except (TypeError, ValueError) as exc:
        return {"label": label, "rejected": True, "reason": str(exc)}
    return {"label": label, "rejected": False, "reason": "accepted"}


def main() -> int:
    runtime = json.loads(H97_RUNTIME.read_text(encoding="utf-8"))
    if runtime["evidence_effect"] != "none" or runtime["environment_contact"]:
        raise RuntimeError("H97 runtime boundary changed")

    frozen = proposal()
    discovery = compile_endogenous_residual_discovery(frozen, axes=axes())

    crossed_question = replace(
        frozen.questions[0], authority_sha256="crossed-authority"
    )
    edited_question = replace(
        frozen.questions[0],
        question_payload_sha256="post-hoc-question-payload",
    )
    leaked_question = replace(
        frozen.questions[0],
        input_evidence_sha256s=(
            *frozen.questions[0].input_evidence_sha256s,
            "descendant-outcome",
        ),
    )
    detached_question = replace(
        frozen.questions[0],
        input_evidence_sha256s=(
            "h95-response-family",
            "h97-source-derivative",
            "h97-source-history-prefix",
        ),
    )
    other_axes = (
        MeasurementAxis("failure-mode-discrimination", 1.0),
        MeasurementAxis("controller-plan-change", 1.0),
        MeasurementAxis("external-task-delta", 3.0),
    )
    unknown_interaction = proposal(
        interactions=((
            "residual-contract-consumption",
            "unknown-question",
        ),)
    )
    negatives = (
        caught(
            "cross_question_authority",
            lambda: replace(
                frozen,
                questions=(crossed_question, *frozen.questions[1:]),
            ),
        ),
        caught(
            "post_hoc_question_edit",
            lambda: replace(
                frozen,
                questions=(edited_question, *frozen.questions[1:]),
            ),
        ),
        caught(
            "descendant_outcome_evidence",
            lambda: replace(
                frozen,
                questions=(leaked_question, *frozen.questions[1:]),
            ),
        ),
        caught(
            "missing_settled_failure",
            lambda: replace(
                frozen,
                questions=(detached_question, *frozen.questions[1:]),
            ),
        ),
        caught(
            "post_outcome_environment_step",
            lambda: replace(frozen, frozen_environment_step=8),
        ),
        caught(
            "measurement_catalog_drift",
            lambda: compile_endogenous_residual_discovery(
                frozen, axes=other_axes
            ),
        ),
        caught(
            "unknown_interaction_question",
            lambda: compile_endogenous_residual_discovery(
                unknown_interaction, axes=axes()
            ),
        ),
        caught(
            "float_information_yield",
            lambda: replace(
                frozen.questions[0],
                predicted_information_yield=0.5,
            ),
        ),
    )

    raw_changed = compile_endogenous_residual_discovery(
        proposal(raw_output_sha256="changed-raw-controller-output"),
        axes=axes(),
    )
    identity_change = {
        "proposal_authority_changed": (
            discovery.proposal.authority.sha256
            != raw_changed.proposal.authority.sha256
        ),
        "fission_authority_changed": (
            discovery.fission.authority.sha256
            != raw_changed.fission.authority.sha256
        ),
        "fission_changed": discovery.fission.sha256 != raw_changed.fission.sha256,
        "schedule_changed": discovery.schedule.sha256 != raw_changed.schedule.sha256,
    }

    checks = {
        "raw_question_count": len(frozen.questions) == 4,
        "direction_quotient_count": (
            len(discovery.fission.direction_quotient_classes) == 3
        ),
        "independent_residual_rank": (
            discovery.fission.independent_offspring_capacity == 3
        ),
        "sparse_trajectory_count": discovery.schedule.trajectory_count == 4,
        "factorial_trajectory_count": (
            discovery.schedule.full_factorial_trajectory_count == 8
        ),
        "model_rank": discovery.schedule.model_rank == 4,
        "strict_trajectory_savings": (
            discovery.schedule.trajectory_count
            < discovery.schedule.full_factorial_trajectory_count
        ),
        "all_negatives_rejected": all(row["rejected"] for row in negatives),
        "raw_output_rebinds_downstream_identity": all(identity_change.values()),
        "no_capability_claim": (
            discovery.to_receipt()["live_settlement_required"]
            and not discovery.to_receipt()["compounding_supported"]
            and not discovery.to_receipt()["takeoff_supported"]
        ),
    }
    verdict = (
        "supported_offline_mechanism"
        if all(checks.values())
        else "rejected_offline_mechanism"
    )
    result = {
        "schema": "ztare-h103-endogenous-residual-reaction-audit-v1",
        "status": "offline_complete",
        "verdict": verdict,
        "preregistration": (
            "h103_endogenous_residual_reaction_hypothesis.md"
        ),
        "fixture_provenance": "fixture_authored_controller_output",
        "controller_contact": False,
        "environment_contact": False,
        "h97_runtime_boundary": {
            "attempt": 3,
            "status": runtime["status"],
            "error_code": runtime["error_code"],
            "model_response_created": runtime["model_response_created"],
            "evidence_effect": runtime["evidence_effect"],
        },
        "checks": checks,
        "identity_change_on_raw_output_replacement": identity_change,
        "negative_fixtures": list(negatives),
        "discovery": discovery.to_receipt(),
        "next_discriminator": (
            "after H97 settles a child, obtain causal and placebo controller "
            "proposals from one stored parent before descendant contact, then "
            "settle the frozen sparse assay against external outcomes"
        ),
        "claim_boundary": [
            "The offline controller output is fixture-authored.",
            "The compiler binds one settled failure to rank quotienting and a pre-outcome sparse assay.",
            "No controller generated questions during this audit.",
            "No descendant environment action or outcome was observed.",
            "Compounding, ARC improvement, capability takeoff, and literature novelty remain unsupported.",
        ],
    }
    result["result_sha256"] = stable_sha256(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if verdict == "supported_offline_mechanism" else 1


if __name__ == "__main__":
    raise SystemExit(main())
