"""Freeze rival-model responses before public-market evidence acquisition."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist, stdev
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.finite_structure_belief import (
    compile_finite_structure_belief,
    rank_finite_structure_questions,
    update_finite_structure_belief,
)
from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    select_guarded_protocol,
)
from ztare.experiment_stats import paired_permutation_test

from .contracts import canonical_timestamp, require_text, timestamp_key
from .equity_activation_research import (
    ALL_MATRIX_POLICY_ARMS,
    MATRIX_POLICY_ARMS,
    MATRIX_POLICY_EXPERIMENT,
    MATRIX_POLICY_LEARNING_SCHEMA,
    activation_matrix_policy_assignment,
    validate_equity_activation_request,
)
from .research_questions import RESEARCH_QUESTION_FRONTIER_SCHEMA


SCHEMA = "jaggedthoughts-prospective-protocol-response-matrix-v2"
LEGACY_SCHEMA = "jaggedthoughts-prospective-protocol-response-matrix-v1"
SETTLEMENT_SCHEMA = "jaggedthoughts-prospective-protocol-response-settlement-v2"
LEGACY_SETTLEMENT_SCHEMA = "jaggedthoughts-prospective-protocol-response-settlement-v1"
CONTINUATION_SCHEMA = "jaggedthoughts-prospective-protocol-response-continuation-v1"
POLICY_LEARNING_SCHEMA = MATRIX_POLICY_LEARNING_SCHEMA
RESPONSE_ALPHABET = (
    "supports_thesis", "supports_rival", "mixed", "unresolved",
)
HYPOTHESIS_KINDS = ("thesis", "rival", "null")


def response_matrix_output_schema(
    *, hypothesis_ids: Sequence[str], program_ids: Sequence[str],
) -> dict[str, Any]:
    """Return the strict subscription-agent output shape."""

    text = {"type": "string", "minLength": 1}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "responses": {
                "type": "array",
                "minItems": len(hypothesis_ids) * len(program_ids),
                "maxItems": len(hypothesis_ids) * len(program_ids),
                "items": {
                    "type": "object",
                    "properties": {
                        "hypothesis_id": {
                            "type": "string", "enum": list(hypothesis_ids),
                        },
                        "program_id": {
                            "type": "string", "enum": list(program_ids),
                        },
                        "predicted_response": {
                            "type": "string", "enum": list(RESPONSE_ALPHABET),
                        },
                        "predicted_distribution": {
                            "type": "object",
                            "properties": {
                                outcome: {
                                    "type": "number", "minimum": 0, "maximum": 1,
                                }
                                for outcome in RESPONSE_ALPHABET
                            },
                            "required": list(RESPONSE_ALPHABET),
                            "additionalProperties": False,
                        },
                        "rationale": text,
                        "rationale_source_refs": {
                            "type": "array", "items": text,
                        },
                    },
                    "required": [
                        "hypothesis_id", "program_id", "predicted_response",
                        "predicted_distribution", "rationale", "rationale_source_refs",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["responses"],
        "additionalProperties": False,
    }


def _verified_frontier(value: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    body = dict(value)
    declared = require_text(
        body.pop("question_frontier_sha256", ""), "question frontier hash",
    )
    if body.get("schema") != RESEARCH_QUESTION_FRONTIER_SCHEMA:
        raise ValueError("unsupported research question frontier")
    if stable_sha256(body) != declared:
        raise ValueError("research question frontier identity is invalid")
    return body, declared


def validate_prospective_response_matrix(value: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the immutable matrix envelope without reconstructing its inputs."""

    body = dict(value)
    declared = require_text(body.pop("matrix_sha256", ""), "response matrix hash")
    if body.get("schema") not in {SCHEMA, LEGACY_SCHEMA} or stable_sha256(body) != declared:
        raise ValueError("prospective response matrix identity is invalid")
    return {**body, "matrix_sha256": declared}


def validate_prospective_response_settlement(value: Mapping[str, Any]) -> dict[str, Any]:
    """Verify one source-bound settlement envelope."""

    body = dict(value)
    declared = require_text(body.pop("settlement_sha256", ""), "response settlement hash")
    if (
        body.get("schema") not in {SETTLEMENT_SCHEMA, LEGACY_SETTLEMENT_SCHEMA}
        or stable_sha256(body) != declared
    ):
        raise ValueError("prospective response settlement identity is invalid")
    return {**body, "settlement_sha256": declared}


def _matrix_structure_belief(matrix: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct and verify the compact stochastic belief frozen by a v2 matrix."""

    hypothesis_ids = sorted(str(row["hypothesis_id"]) for row in matrix["hypotheses"])
    response_index = {
        (str(row["hypothesis_id"]), str(row["program_id"])): row
        for row in matrix["responses"]
    }
    belief = compile_finite_structure_belief(
        evidence_epoch=stable_sha256({
            "candidate_leaf_sha256": matrix["candidate_leaf_sha256"],
            "question_frontier_sha256": matrix["question_frontier_sha256"],
            "evidence_cutoff": matrix["evidence_cutoff"],
        }),
        model_ids=hypothesis_ids,
        question_predictives={
            str(program_id): {
                hypothesis_id: response_index[(hypothesis_id, str(program_id))][
                    "predicted_distribution"
                ]
                for hypothesis_id in hypothesis_ids
            }
            for program_id in matrix["protocol_ids"]
        },
    )
    if belief["belief_sha256"] != matrix.get("structure_belief_sha256"):
        raise ValueError("response matrix structure belief identity is invalid")
    return belief


def compile_prospective_response_matrix(
    question_frontier: Mapping[str, Any],
    *,
    candidate_leaf_sha256: str,
    evidence_cutoff: str,
    predicted_at: str,
    hypotheses: Sequence[Mapping[str, Any]],
    responses: Sequence[Mapping[str, Any]],
    allowed_source_refs: Sequence[str],
) -> dict[str, Any]:
    """Validate a complete pre-acquisition matrix and price its protocols.

    Hypothesis construction and response authorship stay outside this compiler.
    V2 freezes uniform design weights plus categorical predictions. Its score is
    posterior-predictive information per declared source-call unit, not calibrated conviction.
    """

    frontier, frontier_sha = _verified_frontier(question_frontier)
    candidate_leaf = require_text(candidate_leaf_sha256, "candidate leaf hash")
    cutoff = canonical_timestamp(evidence_cutoff, "response matrix evidence cutoff")
    forecast_time = canonical_timestamp(predicted_at, "response matrix predicted_at")
    if timestamp_key(forecast_time) < timestamp_key(cutoff):
        raise ValueError("response matrix prediction precedes its evidence cutoff")

    programs = {
        require_text(row.get("program_id"), "frontier program id"): dict(row)
        for row in frontier.get("frontier_programs") or ()
        if isinstance(row, Mapping)
    }
    if not programs:
        raise ValueError("response matrix requires frontier programs")

    normalized_hypotheses: dict[str, dict[str, Any]] = {}
    allowed_refs = {str(value) for value in allowed_source_refs}
    for raw in hypotheses:
        row = dict(raw)
        hypothesis_id = require_text(row.get("hypothesis_id"), "hypothesis id")
        kind = require_text(row.get("kind"), f"{hypothesis_id} hypothesis kind")
        if kind not in HYPOTHESIS_KINDS:
            raise ValueError(f"unsupported hypothesis kind: {kind}")
        if hypothesis_id in normalized_hypotheses:
            raise ValueError(f"duplicate hypothesis id: {hypothesis_id}")
        mechanism = require_text(row.get("mechanism"), f"{hypothesis_id} mechanism")
        refs = tuple(sorted({str(value) for value in row.get("source_refs") or ()}))
        if set(refs) - allowed_refs:
            raise ValueError(f"{hypothesis_id} cites evidence outside the frozen cutoff")
        normalized_hypotheses[hypothesis_id] = {
            "hypothesis_id": hypothesis_id,
            "kind": kind,
            "mechanism": mechanism,
            "mechanism_sha256": stable_sha256(mechanism),
            "source_refs": list(refs),
        }
    if set(row["kind"] for row in normalized_hypotheses.values()) != set(HYPOTHESIS_KINDS):
        raise ValueError("response matrix requires one thesis, rival, and null hypothesis")
    if len(normalized_hypotheses) != len(HYPOTHESIS_KINDS):
        raise ValueError("response matrix v1 permits exactly three hypotheses")

    normalized_responses: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in responses:
        row = dict(raw)
        hypothesis_id = require_text(row.get("hypothesis_id"), "response hypothesis id")
        program_id = require_text(row.get("program_id"), "response program id")
        key = hypothesis_id, program_id
        if hypothesis_id not in normalized_hypotheses or program_id not in programs:
            raise ValueError("response crossed the frozen hypothesis or protocol set")
        if key in normalized_responses:
            raise ValueError(f"duplicate response: {hypothesis_id}/{program_id}")
        predicted = require_text(row.get("predicted_response"), "predicted response")
        if predicted not in RESPONSE_ALPHABET:
            raise ValueError(f"unsupported predicted response: {predicted}")
        raw_distribution = row.get("predicted_distribution")
        if (
            not isinstance(raw_distribution, Mapping)
            or set(raw_distribution) != set(RESPONSE_ALPHABET)
        ):
            raise ValueError("predicted response distribution must cover the exact alphabet")
        distribution = {
            outcome: float(raw_distribution.get(outcome, -1.0))
            for outcome in RESPONSE_ALPHABET
        }
        if any(not math.isfinite(value) or value < 0 for value in distribution.values()):
            raise ValueError("predicted response distribution must cover the response alphabet")
        total = sum(distribution.values())
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError("predicted response probabilities must sum to one")
        distribution = {
            outcome: distribution[outcome] / total for outcome in RESPONSE_ALPHABET
        }
        if distribution[predicted] + 1e-12 < max(distribution.values()):
            raise ValueError("predicted response must be an argmax of its distribution")
        rationale = require_text(row.get("rationale"), "response rationale")
        refs = tuple(sorted({str(value) for value in row.get("rationale_source_refs") or ()}))
        if set(refs) - allowed_refs:
            raise ValueError("response rationale cites evidence outside the frozen cutoff")
        response = {
            "hypothesis_id": hypothesis_id,
            "program_id": program_id,
            "predicted_response": predicted,
            "predicted_distribution": distribution,
            "predicted_at": forecast_time,
            "rationale": rationale,
            "rationale_source_refs": list(refs),
        }
        normalized_responses[key] = {
            **response, "response_sha256": stable_sha256(response),
        }
    expected = {
        (hypothesis_id, program_id)
        for hypothesis_id in normalized_hypotheses for program_id in programs
    }
    if set(normalized_responses) != expected:
        missing = sorted(expected - set(normalized_responses))
        raise ValueError(f"response matrix is not Cartesian-complete: {missing}")

    candidates = []
    for program_id, program in sorted(programs.items()):
        source_plan = tuple(str(value) for value in program.get("source_plan") or ())
        source_calls = max(1, int(program.get("estimated_source_calls") or len(source_plan) or 1))
        protocol = GuardedExperimentProtocol(
            protocol_id=program_id,
            preparation=source_plan,
            probe=tuple(str(value) for value in program.get("atom_ids") or (program_id,)),
            target_key=(candidate_leaf, frontier_sha),
            cost=ProtocolCost(
                preparation_execution_units=float(source_calls),
                probe_execution_units=0.0,
            ),
            novel_context=False,
            evidence_refs=tuple(sorted(allowed_refs)),
        )
        committee = tuple(
            ProtocolResponseHypothesis(
                hypothesis_id=hypothesis_id,
                response=normalized_responses[(hypothesis_id, program_id)][
                    "predicted_response"
                ],
                evidence_refs=tuple(
                    normalized_responses[(hypothesis_id, program_id)][
                        "rationale_source_refs"
                    ]
                ),
            )
            for hypothesis_id in sorted(normalized_hypotheses)
        )
        candidates.append(GuardedProtocolCandidate(protocol=protocol, committee=committee))
    deterministic_selection = select_guarded_protocol(
        candidates,
        weights=ProtocolYieldWeights(
            identification=1.0, compression=0.0, novelty=0.0,
        ),
    )
    evidence_epoch = stable_sha256({
        "candidate_leaf_sha256": candidate_leaf,
        "question_frontier_sha256": frontier_sha,
        "evidence_cutoff": cutoff,
    })
    program_costs = {
        program_id: max(
            1, int(programs[program_id].get("estimated_source_calls") or 1)
        )
        for program_id in programs
    }
    belief = compile_finite_structure_belief(
        evidence_epoch=evidence_epoch,
        model_ids=sorted(normalized_hypotheses),
        question_predictives={
            program_id: {
                hypothesis_id: normalized_responses[(hypothesis_id, program_id)][
                    "predicted_distribution"
                ]
                for hypothesis_id in sorted(normalized_hypotheses)
            }
            for program_id in sorted(programs)
        },
    )
    ranking = rank_finite_structure_questions(
        belief,
        costs=program_costs,
    )
    selected_program_id = str(ranking[0]["question_id"])
    selection = {
        "status": "selected",
        "selected_protocol_id": selected_program_id,
        "ranking": ranking,
        "score_semantics": (
            "posterior_predictive_information_bits_per_declared_source_call_unit"
        ),
        "belief_sha256": belief["belief_sha256"],
    }
    body = {
        "schema": SCHEMA,
        "candidate_leaf_sha256": candidate_leaf,
        "question_frontier_sha256": frontier_sha,
        "evidence_cutoff": cutoff,
        "predicted_at": forecast_time,
        "committee_epoch_id": stable_sha256({
            "candidate_leaf_sha256": candidate_leaf,
            "question_frontier_sha256": frontier_sha,
            "evidence_cutoff": cutoff,
            "hypotheses": normalized_hypotheses,
        }),
        "hypotheses": [normalized_hypotheses[key] for key in sorted(normalized_hypotheses)],
        "protocol_ids": sorted(programs),
        "program_declared_source_call_units": program_costs,
        "responses": [normalized_responses[key] for key in sorted(normalized_responses)],
        "selection": selection,
        "deterministic_control_selection": deterministic_selection.to_receipt(),
        "structure_belief_sha256": belief["belief_sha256"],
        "mass_semantics": "uniform_design_weights",
        "score_semantics": (
            "posterior_predictive_mutual_information_per_declared_source_call_unit"
        ),
        "status": "selected",
        "selected_program_id": selected_program_id,
        "research_queue_authority": False,
        "capital_authority": False,
    }
    return {**body, "matrix_sha256": stable_sha256(body)}


def settle_prospective_response_matrix(
    matrix: Mapping[str, Any],
    *,
    program_id: str,
    observed_response: str,
    observed_at: str,
    evidence_refs: Sequence[str],
    execution_contract: Mapping[str, Any] | None = None,
    prior_settlements: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Settle one researched program against its frozen response cells."""

    frozen = validate_prospective_response_matrix(matrix)
    protocol_id = require_text(program_id, "settled program id")
    if protocol_id not in set(map(str, frozen.get("protocol_ids") or ())):
        raise ValueError("settlement program is outside the frozen matrix")
    response = require_text(observed_response, "observed response")
    if response not in RESPONSE_ALPHABET:
        raise ValueError("settlement response is outside the frozen alphabet")
    settled_at = canonical_timestamp(observed_at, "response settlement observed_at")
    prior_rows = [validate_prospective_response_settlement(row) for row in prior_settlements]
    continuation = None
    minimum_time = str(frozen["predicted_at"])
    if prior_rows:
        continuation = compile_prospective_response_continuation(frozen, prior_rows)
        if continuation["next_program_id"] != protocol_id:
            raise ValueError("settlement program is not the posterior-ranked continuation")
        minimum_time = str(prior_rows[-1]["observed_at"])
    if timestamp_key(settled_at) < timestamp_key(minimum_time):
        raise ValueError("response settlement precedes the frozen prediction")
    refs = sorted({require_text(value, "settlement evidence ref") for value in evidence_refs})
    if not refs:
        raise ValueError("response settlement requires evidence refs")
    execution = dict(execution_contract or {})
    if execution and (
        execution.get("matrix_sha256") != frozen["matrix_sha256"]
        or execution.get("executed_program_id") != protocol_id
        or execution.get("arm_id") not in ALL_MATRIX_POLICY_ARMS
    ):
        raise ValueError("response settlement crossed its execution assignment")
    predicted_rows = [
        row for row in frozen.get("responses") or ()
        if isinstance(row, Mapping) and row.get("program_id") == protocol_id
    ]
    belief_update = None
    predictive_scores = None
    if frozen["schema"] == SCHEMA:
        belief = _matrix_structure_belief(frozen)
        for prior in prior_rows:
            belief = update_finite_structure_belief(
                belief, question_id=str(prior["program_id"]),
                observed_outcome=str(prior["observed_response"]),
                observed_at=str(prior["observed_at"]),
                evidence_refs=list(prior["evidence_refs"]),
            )
        question = next(
            row for row in belief["questions"] if row["question_id"] == protocol_id
        )
        mixture = {
            outcome: sum(
                float(belief["weights"][model_id])
                * float(question["predictive_distributions"][model_id].get(outcome, 0.0))
                for model_id in belief["model_ids"]
            )
            for outcome in question["outcome_alphabet"]
        }
        belief_update = update_finite_structure_belief(
            belief, question_id=protocol_id, observed_outcome=response,
            observed_at=settled_at, evidence_refs=refs,
        )
        posterior_size = sum(
            float(weight) > 0 for weight in belief_update["weights"].values()
        )
        prior_entropy = math.log2(len(belief["model_ids"]))
        if belief_update["status"] == "committee_refuted":
            information_bits = 0.0
            realized = 0.0
        else:
            information_bits = sum(
                float(weight) * math.log2(float(weight) / float(belief["weights"][key]))
                for key, weight in belief_update["weights"].items() if float(weight) > 0
            )
            realized = information_bits / prior_entropy if prior_entropy > 0 else 0.0
        cost_units = float((
            frozen.get("program_declared_source_call_units") or {}
        ).get(protocol_id, 0.0))
        if not math.isfinite(cost_units) or cost_units <= 0:
            raise ValueError("response matrix program cost is missing or invalid")
        observed_probability = float(mixture.get(response, 0.0))
        predictive_scores = {
            "mixture_observed_probability": observed_probability,
            "log_loss_bits": (
                -math.log2(observed_probability) if observed_probability > 0 else None
            ),
            "brier_score": sum(
                (probability - (1.0 if outcome == response else 0.0)) ** 2
                for outcome, probability in mixture.items()
            ),
        }
    else:
        prior_size = len(predicted_rows)
        posterior_size = sum(
            row.get("predicted_response") == response for row in predicted_rows
        )
        realized = (
            0.0 if prior_size <= 1 else
            1.0 if posterior_size == 0 else
            math.log2(prior_size / posterior_size) / math.log2(prior_size)
        )
        information_bits = realized
        cost_units = 1.0
    body = {
        "schema": (
            SETTLEMENT_SCHEMA if frozen["schema"] == SCHEMA else LEGACY_SETTLEMENT_SCHEMA
        ),
        "matrix_sha256": frozen["matrix_sha256"],
        "program_id": protocol_id,
        "observed_response": response,
        "observed_at": settled_at,
        "evidence_refs": refs,
        "posterior_cell_size": posterior_size,
        "realized_information_yield": realized,
        "realized_information_bits": information_bits,
        "executed_declared_source_call_units": cost_units,
        "realized_information_bits_per_declared_source_call_unit": (
            information_bits / cost_units
        ),
        "status": (
            "committee_refuted" if (
                belief_update is not None
                and belief_update["status"] == "committee_refuted"
            ) or posterior_size == 0
            else "witnessed_partition_cell"
        ),
        **(
            {
                "structure_belief_update_receipt": {
                    key: belief_update[key]
                    for key in (
                        "belief_sha256", "parent_belief_sha256", "weights",
                        "weight_semantics", "status", "observation_history",
                    )
                },
                "predictive_scores": predictive_scores,
            }
            if belief_update is not None else {}
        ),
        "matrix_policy_choice_observed": protocol_id == frozen.get("selected_program_id"),
        **({"response_matrix_execution": execution} if execution else {}),
        **(
            {
                "prior_settlement_sha256s": [
                    str(row["settlement_sha256"]) for row in prior_rows
                ],
                "continuation_sha256": continuation["continuation_sha256"],
            }
            if continuation else {}
        ),
        "research_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "settlement_sha256": stable_sha256(body)}


def compile_prospective_response_continuation(
    matrix: Mapping[str, Any], settlements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Replay settled observations and price the remaining program frontier."""

    frozen = validate_prospective_response_matrix(matrix)
    if frozen["schema"] != SCHEMA:
        raise ValueError("prospective continuation requires a v2 response matrix")
    belief = _matrix_structure_belief(frozen)
    settlement_ids = []
    accepted_settlements: list[dict[str, Any]] = []
    previous_observed_at = str(frozen["predicted_at"])
    costs = frozen.get("program_declared_source_call_units") or {}

    for raw in settlements:
        settlement = validate_prospective_response_settlement(raw)
        if (
            settlement["schema"] != SETTLEMENT_SCHEMA
            or settlement.get("matrix_sha256") != frozen["matrix_sha256"]
        ):
            raise ValueError("settlement crossed the v2 response matrix")
        if settlement_ids:
            prior_receipt = compile_prospective_response_continuation(
                frozen, accepted_settlements,
            )
            if (
                settlement.get("prior_settlement_sha256s") != settlement_ids
                or settlement.get("continuation_sha256")
                != prior_receipt["continuation_sha256"]
            ):
                raise ValueError("response settlement crossed its continuation lineage")
        elif (
            settlement.get("prior_settlement_sha256s") is not None
            or settlement.get("continuation_sha256") is not None
        ):
            raise ValueError("initial response settlement declares continuation lineage")
        program_id = require_text(settlement.get("program_id"), "settled program id")
        response = require_text(settlement.get("observed_response"), "observed response")
        observed_at = canonical_timestamp(
            settlement.get("observed_at"), "response settlement observed_at",
        )
        if timestamp_key(observed_at) < timestamp_key(previous_observed_at):
            raise ValueError("response settlements are not in observation order")
        refs = sorted({
            require_text(value, "settlement evidence ref")
            for value in settlement.get("evidence_refs") or ()
        })
        if not refs or refs != settlement.get("evidence_refs"):
            raise ValueError("response settlement evidence refs are not canonical")

        question = next(
            row for row in belief["questions"] if row["question_id"] == program_id
        )
        mixture = {
            outcome: sum(
                float(belief["weights"][model_id])
                * float(question["predictive_distributions"][model_id].get(outcome, 0.0))
                for model_id in belief["model_ids"]
            )
            for outcome in question["outcome_alphabet"]
        }
        updated = update_finite_structure_belief(
            belief, question_id=program_id, observed_outcome=response,
            observed_at=observed_at, evidence_refs=refs,
        )
        expected_receipt = {
            key: updated[key]
            for key in (
                "belief_sha256", "parent_belief_sha256", "weights",
                "weight_semantics", "status", "observation_history",
            )
        }
        cost = float(costs.get(program_id, 0.0))
        expected_status = (
            "committee_refuted"
            if updated["status"] == "committee_refuted"
            else "witnessed_partition_cell"
        )
        expected_size = sum(float(weight) > 0 for weight in updated["weights"].values())
        if updated["status"] == "committee_refuted":
            information_bits = realized_yield = 0.0
        else:
            information_bits = sum(
                float(weight) * math.log2(
                    float(weight) / float(belief["weights"][model_id])
                )
                for model_id, weight in updated["weights"].items()
                if float(weight) > 0
            )
            prior_entropy = math.log2(len(belief["model_ids"]))
            realized_yield = information_bits / prior_entropy if prior_entropy else 0.0
        observed_probability = float(mixture.get(response, 0.0))
        expected_scores = {
            "mixture_observed_probability": observed_probability,
            "log_loss_bits": (
                -math.log2(observed_probability) if observed_probability > 0 else None
            ),
            "brier_score": sum(
                (probability - (1.0 if outcome == response else 0.0)) ** 2
                for outcome, probability in mixture.items()
            ),
        }
        if (
            settlement.get("structure_belief_update_receipt") != expected_receipt
            or settlement.get("status") != expected_status
            or settlement.get("posterior_cell_size") != expected_size
            or not math.isfinite(cost) or cost <= 0
            or float(settlement.get("executed_declared_source_call_units", 0.0)) != cost
            or float(settlement.get("realized_information_bits", math.nan))
            != information_bits
            or float(settlement.get("realized_information_yield", math.nan))
            != realized_yield
            or float(settlement.get(
                "realized_information_bits_per_declared_source_call_unit", math.nan,
            )) != information_bits / cost
            or settlement.get("predictive_scores") != expected_scores
            or settlement.get("matrix_policy_choice_observed")
            is not (program_id == frozen.get("selected_program_id"))
            or settlement.get("research_policy_authority") is not False
            or settlement.get("capital_authority") is not False
        ):
            raise ValueError("response settlement differs from deterministic update semantics")
        execution = settlement.get("response_matrix_execution")
        if execution is not None and (
            not isinstance(execution, Mapping)
            or execution.get("matrix_sha256") != frozen["matrix_sha256"]
            or execution.get("executed_program_id") != program_id
            or execution.get("arm_id") not in ALL_MATRIX_POLICY_ARMS
        ):
            raise ValueError("response settlement crossed its execution assignment")
        belief = updated
        previous_observed_at = observed_at
        settlement_ids.append(str(settlement["settlement_sha256"]))
        accepted_settlements.append(settlement)

    if belief["status"] == "committee_refuted":
        ranking = []
        exhaustion_reason = "committee_refuted"
    else:
        ranking = rank_finite_structure_questions(belief, costs=costs)
        exhaustion_reason = None if ranking else "all_programs_observed"
    body = {
        "schema": CONTINUATION_SCHEMA,
        "matrix_sha256": frozen["matrix_sha256"],
        "settlement_sha256s": settlement_ids,
        "current_structure_belief_sha256": belief["belief_sha256"],
        "current_weights": belief["weights"],
        "observed_program_ids": [
            row["question_id"] for row in belief["observation_history"]
        ],
        "remaining_program_ranking": ranking,
        "next_program_id": ranking[0]["question_id"] if ranking else None,
        "frontier_exhausted": not ranking,
        "frontier_exhaustion_reason": exhaustion_reason,
        "status": "next_program_selected" if ranking else "frontier_exhausted",
        "score_semantics": (
            "posterior_predictive_information_bits_per_declared_source_call_unit"
        ),
        "research_queue_authority": False,
        "capital_authority": False,
    }
    return {**body, "continuation_sha256": stable_sha256(body)}


def _scheduled_review_pairs(
    pairs: Sequence[Mapping[str, Any]], minimum_pairs: int,
) -> tuple[list[dict[str, Any]], int, int | None]:
    """Freeze each doubling look by settlement-completion order."""

    ordered = sorted(
        (dict(row) for row in pairs),
        key=lambda row: (str(row["completed_at"]), str(row["pair_id"])),
    )
    review_count = (
        minimum_pairs * 2 ** int(math.log2(len(ordered) / minimum_pairs))
        if len(ordered) >= minimum_pairs else 0
    )
    review_index = (
        int(math.log2(review_count / minimum_pairs)) if review_count else None
    )
    return ordered[:review_count], review_count, review_index


def compile_activation_matrix_policy_learning(
    episodes: Sequence[Mapping[str, Any]], *, compiled_at: str,
    minimum_pairs: int = 20,
    minimum_useful_information_bits_per_declared_source_call_unit: float = 0.05,
    target_power: float = 0.8,
) -> dict[str, Any]:
    """Compare frozen matrix selection with the incumbent on matched activations."""

    if isinstance(minimum_pairs, bool) or minimum_pairs < 1:
        raise ValueError("activation matrix policy minimum_pairs must be positive")
    minimum_useful_delta = float(
        minimum_useful_information_bits_per_declared_source_call_unit
    )
    if (
        not math.isfinite(minimum_useful_delta) or minimum_useful_delta <= 0
        or not 0 < float(target_power) < 1
    ):
        raise ValueError("activation matrix policy power contract is invalid")
    compiled = canonical_timestamp(compiled_at, "activation matrix policy compiled_at")
    rows = []
    for episode in episodes:
        request = validate_equity_activation_request(episode["activation_request"])
        assignment = activation_matrix_policy_assignment(request)
        if (
            not assignment["eligible"]
            or assignment.get("experiment_id") != MATRIX_POLICY_EXPERIMENT
        ):
            continue
        matrix = validate_prospective_response_matrix(episode["response_matrix"])
        settlement = validate_prospective_response_settlement(episode["settlement"])
        if matrix["schema"] != SCHEMA or settlement["schema"] != SETTLEMENT_SCHEMA:
            continue
        frontier = request.get("research_question_frontier") or {}
        incumbent = frontier.get("selected_program") or {}
        frontier_program_ids = {
            str(row.get("program_id") or "")
            for row in frontier.get("frontier_programs") or () if isinstance(row, Mapping)
        }
        matrix_program_id = str(matrix.get("selected_program_id") or "")
        if (
            matrix.get("candidate_leaf_sha256")
            != (request.get("candidate_identity") or {}).get("candidate_leaf")
            or matrix.get("question_frontier_sha256")
            != frontier.get("question_frontier_sha256")
            or matrix_program_id not in frontier_program_ids
            or settlement.get("matrix_sha256") != matrix.get("matrix_sha256")
        ):
            raise ValueError("activation matrix policy episode crossed a frozen identity")
        expected_program_id = (
            matrix_program_id
            if str(assignment["arm_id"]).endswith("matrix_selected_question")
            else str(incumbent.get("program_id") or "")
        )
        execution = settlement.get("response_matrix_execution")
        expected_cost = float(
            (matrix.get("program_declared_source_call_units") or {}).get(
                expected_program_id, 0.0
            )
        )
        if (
            settlement.get("program_id") != expected_program_id
            or not isinstance(execution, Mapping)
            or execution.get("assignment_sha256") != assignment["assignment_sha256"]
            or execution.get("arm_id") != assignment["arm_id"]
            or execution.get("executed_program_id") != expected_program_id
            or execution.get("assignment_realized") is not True
            or not math.isfinite(expected_cost)
            or expected_cost <= 0
            or not math.isclose(
                float(
                    settlement.get("executed_declared_source_call_units") or 0.0
                ),
                expected_cost,
            )
        ):
            raise ValueError("activation matrix policy settlement did not execute its assigned arm")
        if timestamp_key(str(settlement["observed_at"])) > timestamp_key(compiled):
            raise ValueError("activation matrix policy compilation predates a settlement")
        ranking = list((matrix.get("selection") or {}).get("ranking") or ())
        information_values = [
            float(row.get("information_bits_per_cost") or 0.0)
            for row in ranking if isinstance(row, Mapping)
        ]
        scores = settlement.get("predictive_scores") or {}
        categorical_control_program_id = str(
            (matrix.get("deterministic_control_selection") or {}).get(
                "protocol_id"
            ) or ""
        )
        rows.append({
            "pair_id": assignment["pair_id"],
            "pair_slot": assignment["pair_slot"],
            "arm_id": assignment["arm_id"],
            "assignment_sha256": assignment["assignment_sha256"],
            "request_sha256": request["request_sha256"],
            "assigned_at": request["created_at"],
            "entity_id": (request.get("candidate_identity") or {}).get("entity_id"),
            "program_id": expected_program_id,
            "matrix_selected_program_id": matrix_program_id,
            "incumbent_program_id": incumbent.get("program_id"),
            "matrix_selected_incumbent": matrix_program_id == incumbent.get("program_id"),
            "matrix_selected_categorical_control": (
                matrix_program_id == categorical_control_program_id
            ),
            "question_information_spread": (
                max(information_values) - min(information_values)
                if information_values else 0.0
            ),
            "observed_at": settlement["observed_at"],
            "observed_response": settlement.get("observed_response"),
            "realized_information_yield": float(settlement["realized_information_yield"]),
            "realized_information_bits": float(settlement["realized_information_bits"]),
            "executed_declared_source_call_units": float(
                settlement["executed_declared_source_call_units"]
            ),
            "realized_information_bits_per_declared_source_call_unit": float(
                settlement[
                    "realized_information_bits_per_declared_source_call_unit"
                ]
            ),
            "predictive_log_loss_bits": scores.get("log_loss_bits"),
            "predictive_brier_score": scores.get("brier_score"),
            "committee_refuted": settlement.get("status") == "committee_refuted",
            "settlement_sha256": settlement["settlement_sha256"],
        })

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["pair_id"]), []).append(row)
    pairs = []
    invalid_pair_count = 0
    for pair_id, members in sorted(groups.items()):
        by_arm = {str(row["arm_id"]): row for row in members}
        if (
            len(members) != 2
            or set(by_arm) != set(MATRIX_POLICY_ARMS)
            or len({row["request_sha256"] for row in members}) != 2
            or {int(row["pair_slot"]) for row in members} != {0, 1}
        ):
            invalid_pair_count += 1
            continue
        incumbent, matrix_selected = (by_arm[arm] for arm in MATRIX_POLICY_ARMS)
        log_improvement = (
            float(incumbent["predictive_log_loss_bits"])
            - float(matrix_selected["predictive_log_loss_bits"])
            if incumbent["predictive_log_loss_bits"] is not None
            and matrix_selected["predictive_log_loss_bits"] is not None else None
        )
        brier_improvement = (
            float(incumbent["predictive_brier_score"])
            - float(matrix_selected["predictive_brier_score"])
            if incumbent["predictive_brier_score"] is not None
            and matrix_selected["predictive_brier_score"] is not None else None
        )
        pairs.append({
            "pair_id": pair_id,
            "assigned_at": max(str(row["assigned_at"]) for row in members),
            "completed_at": max(
                str(row["observed_at"]) for row in members
            ),
            "request_sha256_by_arm": {
                arm: by_arm[arm]["request_sha256"] for arm in MATRIX_POLICY_ARMS
            },
            "entity_id_by_arm": {
                arm: by_arm[arm]["entity_id"] for arm in MATRIX_POLICY_ARMS
            },
            "matrix_minus_incumbent": {
                "realized_information_bits_per_declared_source_call_unit": round(
                    matrix_selected[
                        "realized_information_bits_per_declared_source_call_unit"
                    ] - incumbent[
                        "realized_information_bits_per_declared_source_call_unit"
                    ], 12,
                ),
                "committee_refutation": int(matrix_selected["committee_refuted"])
                - int(incumbent["committee_refuted"]),
                "predictive_log_loss_improvement_bits": log_improvement,
                "predictive_brier_improvement": brier_improvement,
            },
        })
    review_pairs, review_pair_count, review_index = _scheduled_review_pairs(
        pairs, minimum_pairs,
    )
    look_alpha = (
        0.05 / 2 ** (int(review_index) + 1)
        if review_index is not None else 0.05
    )
    deltas = [
        row["matrix_minus_incumbent"][
            "realized_information_bits_per_declared_source_call_unit"
        ]
        for row in review_pairs
    ]
    inference = paired_permutation_test(
        deltas, [0.0] * len(deltas),
        seed=int(stable_sha256(deltas)[:8], 16),
        ci_level=1.0 - look_alpha,
    )
    p_value = inference.get("p_value")
    ci_lo, ci_hi = inference.get("ci_lo"), inference.get("ci_hi")
    paired_sd = stdev(deltas) if len(deltas) >= 2 else None
    required_pairs = (
        max(1, math.ceil((
            (NormalDist().inv_cdf(1.0 - look_alpha / 2.0)
             + NormalDist().inv_cdf(float(target_power)))
            * paired_sd / minimum_useful_delta
        ) ** 2))
        if paired_sd is not None else None
    )
    review_boundary_reached = bool(review_pair_count)
    enough = bool(
        review_boundary_reached and required_pairs is not None
        and review_pair_count >= required_pairs
    )
    matrix_wins = bool(
        enough and p_value is not None and float(p_value) <= look_alpha
        and ci_lo is not None and float(ci_lo) > minimum_useful_delta
    )
    incumbent_wins = bool(
        enough and p_value is not None and float(p_value) <= look_alpha
        and ci_hi is not None and float(ci_hi) < -minimum_useful_delta
    )
    preferred = (
        MATRIX_POLICY_ARMS[1] if matrix_wins else
        "incumbent_question" if incumbent_wins else None
    )
    representation_diagnostics = {
        "mixed_or_unresolved_rate": (
            sum(row["observed_response"] in {"mixed", "unresolved"} for row in rows)
            / len(rows) if rows else None
        ),
        "matrix_selected_incumbent_rate": (
            sum(row["matrix_selected_incumbent"] for row in rows) / len(rows)
            if rows else None
        ),
        "stochastic_selected_categorical_control_rate": (
            sum(row["matrix_selected_categorical_control"] for row in rows) / len(rows)
            if rows else None
        ),
        "non_discriminating_question_menu_rate": (
            sum(row["question_information_spread"] <= 1e-6 for row in rows) / len(rows)
            if rows else None
        ),
        "review_boundary_reached": review_boundary_reached,
    }
    representation_diagnostics["repair_recommended"] = bool(
        review_boundary_reached and (
            float(representation_diagnostics["mixed_or_unresolved_rate"] or 0.0) > 0.8
            or float(representation_diagnostics["matrix_selected_incumbent_rate"] or 0.0) > 0.9
            or float(
                representation_diagnostics["non_discriminating_question_menu_rate"] or 0.0
            ) > 0.8
        )
    )
    if representation_diagnostics["repair_recommended"]:
        preferred = None
    other = next((arm for arm in MATRIX_POLICY_ARMS if arm != preferred), None)
    body = {
        "schema": POLICY_LEARNING_SCHEMA,
        "compiled_at": compiled,
        "status": (
            "representation_repair_required"
            if representation_diagnostics["repair_recommended"] else
            "stochastic_matrix_selected_superior" if matrix_wins else
            "incumbent_superior" if incumbent_wins else
            "inconclusive_no_superiority" if enough else
            "collecting_power_for_declared_effect" if review_boundary_reached else
            "collecting_matched_settlements"
        ),
        "observed_episode_count": len(rows),
        "complete_pair_count": len(pairs),
        "eligible_pair_set_sha256": stable_sha256(pairs),
        "invalid_pair_count": invalid_pair_count,
        "minimum_pairs": minimum_pairs,
        "sequential_review_contract": {
            "review_schedule": "minimum_pairs_times_powers_of_two",
            "review_pair_count": review_pair_count,
            "review_index": review_index,
            "look_alpha": look_alpha,
            "familywise_alpha_budget": 0.05,
            "alpha_spending_rule": "0.05 / 2^(review_index + 1)",
            "unreviewed_complete_pair_count": len(pairs) - review_pair_count,
            "review_pair_ids_sha256": stable_sha256([
                row["pair_id"] for row in review_pairs
            ]),
        },
        "power_contract": {
            "alpha_two_sided": look_alpha,
            "target_power": float(target_power),
            "minimum_useful_information_bits_per_declared_source_call_unit": (
                minimum_useful_delta
            ),
            "observed_paired_standard_deviation": paired_sd,
            "estimated_required_pair_count": required_pairs,
            "power_sufficient": enough,
        },
        "pairs": pairs,
        "paired_information_per_declared_source_call_unit_inference": inference,
        "representation_diagnostics": representation_diagnostics,
        "preferred_arm": preferred,
        "routing_change_allowed": preferred is not None,
        "future_routing": (
            {str(preferred): 0.8, str(other): 0.2}
            if preferred else {arm: 0.5 for arm in MATRIX_POLICY_ARMS}
        ),
        "outcome_semantics": (
            "source_bound_realized_information_bits_per_declared_source_call_unit_"
            "not_investment_return_cost_estimate_calibration_absent"
        ),
        "policy_authority": "future_activation_question_routing_only",
        "capital_authority": False,
    }
    return {**body, "policy_learning_sha256": stable_sha256(body)}


def compile_workspace_activation_matrix_policy_learning(
    workspace: str | Path, *, compiled_at: str, minimum_pairs: int = 20,
) -> dict[str, Any]:
    """Project eligible request/matrix/settlement triples from one workspace."""

    root = Path(workspace).expanduser().resolve()
    activation_root = root / "research_jobs" / "activation"
    episodes = []
    for settlement_path in sorted((activation_root / "response_matrix_settlements").glob("*.json")):
        request_path = activation_root / "requests" / settlement_path.name
        matrix_path = activation_root / "response_matrices" / settlement_path.name
        if not request_path.exists() or not matrix_path.exists():
            continue
        episodes.append({
            "activation_request": json.loads(request_path.read_text(encoding="utf-8")),
            "response_matrix": json.loads(matrix_path.read_text(encoding="utf-8")),
            "settlement": json.loads(settlement_path.read_text(encoding="utf-8")),
        })
    return compile_activation_matrix_policy_learning(
        episodes, compiled_at=compiled_at, minimum_pairs=minimum_pairs,
    )


__all__ = [
    "CONTINUATION_SCHEMA",
    "HYPOTHESIS_KINDS",
    "POLICY_LEARNING_SCHEMA",
    "RESPONSE_ALPHABET",
    "SCHEMA",
    "SETTLEMENT_SCHEMA",
    "compile_activation_matrix_policy_learning",
    "compile_prospective_response_continuation",
    "compile_prospective_response_matrix",
    "compile_workspace_activation_matrix_policy_learning",
    "response_matrix_output_schema",
    "settle_prospective_response_matrix",
    "validate_prospective_response_matrix",
    "validate_prospective_response_settlement",
]
