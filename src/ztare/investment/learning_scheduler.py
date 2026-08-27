"""Rank admissible research jobs by their leverage on the learning system."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.common.information_yield_pricing import price_experiment

from .contracts import canonical_timestamp, timestamp_key
from .mandate_research_relevance import compile_mandate_research_relevance


LEARNING_SCHEDULE_SCHEMA = "jaggedthoughts-institutional-learning-schedule-v2"

_STRATEGY_KINDS = {
    "jaggedthoughts_strategy_measurement_research": "freeze_strategy_measurement_contract",
    "jaggedthoughts_strategy_outcome_research": "settle_strategy_consequence",
    "jaggedthoughts_strategy_cohort_research": "classify_strategy_control",
    "jaggedthoughts_strategy_frontier_research": "compile_strategy_options",
    "jaggedthoughts_strategy_constraint_evidence_research": "falsify_strategy_constraints",
    "jaggedthoughts_strategy_event_refinement_research": "sharpen_strategy_treatment_event",
    "jaggedthoughts_strategy_program_adoption_research": "classify_integrated_strategy_program",
    "jaggedthoughts_hypothesis_set_epoch_research": "expand_refuted_hypothesis_committee",
    "jaggedthoughts_hypothesis_set_evidence_research": "test_successor_hypothesis_committee",
}
_DECISION_VALUE = {
    "jaggedthoughts_strategy_measurement_research": 0.95,
    "jaggedthoughts_strategy_outcome_research": 1.0,
    "jaggedthoughts_subscription_activation_research": 1.0,
    "jaggedthoughts_subscription_reassessment": 0.9,
    "jaggedthoughts_subscription_research": 0.8,
    "jaggedthoughts_candidate_payoff_forecast": 0.9,
    "jaggedthoughts_strategy_cohort_research": 0.7,
    "jaggedthoughts_strategy_program_adoption_research": 0.85,
    "jaggedthoughts_strategy_frontier_research": 0.6,
    "jaggedthoughts_strategy_constraint_evidence_research": 0.75,
    "jaggedthoughts_strategy_event_refinement_research": 0.9,
    "jaggedthoughts_autoresearch_project": 0.4,
    "jaggedthoughts_hypothesis_set_epoch_research": 0.9,
    "jaggedthoughts_hypothesis_set_evidence_research": 0.9,
}
_WEIGHTS = {
    "law_scope_separation_upper_bound": 0.35,
    "law_scope_compression_upper_bound": 0.20,
    "unseen_entity_context": 0.15,
    "cohort_sampling_gap_upper_bound": 0.20,
    "decision_proximity_prior": 0.10,
}
_REPEATED_ENTITY_ACTION_PENALTY = 0.15
_SERVICE_BONUS_MAX = 0.10
FROZEN_CHAIN_SUCCESSOR_JOB_KINDS = {
    "jaggedthoughts_strategy_cohort_research",
    "jaggedthoughts_strategy_measurement_research",
    "jaggedthoughts_strategy_outcome_research",
    "jaggedthoughts_strategy_constraint_evidence_research",
    "jaggedthoughts_strategy_event_refinement_research",
    "jaggedthoughts_strategy_program_adoption_research",
}
_ADMINISTRATIVE_STAGES = {
    "superseded", "covered_by_prior_classification", "covered_by_prior_dossier",
    "awaiting_source_reassessment",
}


def _law_size(law: Mapping[str, Any]) -> int:
    mechanism = law.get("mechanism") if isinstance(law.get("mechanism"), Mapping) else {}
    predictor = law.get("predictor_program") if isinstance(law.get("predictor_program"), Mapping) else {}
    return max(
        1,
        len(mechanism.get("antecedent_concepts") or ()) + len(predictor.get("nodes") or ()),
    )


def _supports(job: Mapping[str, Any], law: Mapping[str, Any], entity_kind: str) -> bool:
    kind = str(job.get("kind") or "")
    mechanism = law.get("mechanism") if isinstance(law.get("mechanism"), Mapping) else {}
    if kind in _STRATEGY_KINDS:
        return (
            str((law.get("estimator") or {}).get("kind") or "") == "difference_in_differences"
            or "strategic_choice_adoption" in set(mechanism.get("antecedent_concepts") or ())
        )
    return entity_kind in set((law.get("cohort") or {}).get("entity_kinds") or ())


def _cohort_gap(
    applicable: Sequence[Mapping[str, Any]], cohorts: Mapping[str, Mapping[str, Any]],
) -> float:
    gaps = []
    for law in applicable:
        minimum = int((law.get("validation") or {}).get("minimum_inference_blocks") or 1)
        observed = int((cohorts.get(str(law.get("law_sha256"))) or {}).get("inference_block_count") or 0)
        gaps.append(max(0.0, min(1.0, (minimum - observed) / minimum)))
    return sum(gaps) / len(gaps) if gaps else 0.0


def _action_class(kind: str) -> str:
    return _STRATEGY_KINDS.get(kind, kind.removeprefix("jaggedthoughts_"))


def _market_flow_residual_components(payload: Mapping[str, Any]) -> dict[str, float] | None:
    trigger = payload.get("research_trigger")
    if not isinstance(trigger, Mapping):
        return None
    residual = trigger.get("research_residual")
    if not isinstance(residual, Mapping):
        return None
    body = dict(residual)
    declared = str(body.pop("research_residual_sha256", ""))
    if not (
        residual.get("schema") == "jaggedthoughts-market-flow-research-residual-v1"
        and declared == stable_sha256(body)
        and trigger.get("research_residual_sha256") == declared
        and residual.get("next_permitted_action") == "successor_research_due"
        and residual.get("capital_authority") is False
    ):
        return None
    comparisons = [
        row for row in residual.get("candidate_pairwise_comparisons") or ()
        if isinstance(row, Mapping) and row.get("observed_delta") is not None
    ]
    discrimination = (
        sum(abs(float(row["observed_delta"])) > 1e-12 for row in comparisons)
        / len(comparisons) if comparisons else 0.0
    )
    improvements = residual.get("candidate_improvement_over_baseline")
    improvements = improvements if isinstance(improvements, Mapping) else {}
    cross_dimension = sum(
        value is not None and abs(float(value)) > 1e-12
        for value in improvements.values()
    ) / 3.0
    blocks = int(residual.get("inference_block_count") or 0)
    minimum = int(residual.get("min_inference_blocks") or 0)
    evidence_strength = min(1.0, blocks / minimum) if minimum > 0 else 0.0
    return {
        "world_model_control_disagreement_upper_bound": discrimination,
        "world_model_cross_dimension_upper_bound": cross_dimension,
        "prospective_evidence_strength": evidence_strength,
    }


def _constraint_evidence_components(
    kind: str, payload: Mapping[str, Any],
) -> dict[str, float] | None:
    if kind != "jaggedthoughts_strategy_constraint_evidence_research":
        return None
    candidates = int(payload.get("candidate_effect_count") or 0)
    feasible = int(payload.get("parent_feasible_bundle_count") or 0)
    rejected = [
        max(0, int(value))
        for value in payload.get("candidate_rejected_parent_bundle_counts") or ()
    ]
    return {
        "constraint_discrimination_upper_bound": 1.0 if candidates >= 2 else 0.0,
        "constraint_falsification_surface_upper_bound": (
            min(1.0, max(rejected, default=0) / feasible) if feasible > 0 else 0.0
        ),
        "source_disjoint_replay_readiness": float(bool(
            payload.get("candidate_freeze_sha256")
            and payload.get("holdout_predicates_hidden") is True
            and int(payload.get("candidate_source_family_count") or 0) > 0
        )),
    }


def _known_by(row: Mapping[str, Any], epoch: str, field: str) -> bool:
    value = row.get(field)
    return not value or timestamp_key(canonical_timestamp(value, field)) <= timestamp_key(epoch)


def _research_was_served(row: Mapping[str, Any]) -> bool:
    payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
    return row.get("status") == "done" and payload.get("stage") not in _ADMINISTRATIVE_STAGES


def compile_learning_schedule(
    queue_rows: Sequence[Mapping[str, Any]],
    learning_state: Mapping[str, Any],
    *,
    generated_at: str,
    strategy_acquisition_policy: Mapping[str, Any] | None = None,
    household_mandate_frontier: Mapping[str, Any] | None = None,
    sleeve_implementation_frontier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Order queued actions with point-in-time law-scope and backlog proxies.

    This changes research order only. It does not score securities, infer expected
    return, or grant paper/capital authority.
    """

    epoch = canonical_timestamp(generated_at, "learning schedule generated_at")
    laws = sorted([
        dict(row) for row in learning_state.get("candidates") or ()
        if isinstance(row, Mapping) and row.get("law_sha256")
        and _known_by(row, epoch, "created_at")
    ], key=lambda row: str(row["law_sha256"]))
    visible_episodes = [
        row for row in learning_state.get("phenotype_episodes") or ()
        if isinstance(row, Mapping) and _known_by(row, epoch, "opened_at")
    ]
    visible_blocks = {
        str(row.get("episode_id")): str(row.get("inference_block_id"))
        for row in visible_episodes if row.get("episode_id") and row.get("inference_block_id")
    }
    cohorts = {
        str(row.get("law_sha256")): {
            **row,
            "inference_block_count": len({
                visible_blocks[episode_id]
                for episode_id in map(str, row.get("member_episode_ids") or ())
                if episode_id in visible_blocks
            }) if row.get("member_episode_ids") is not None else row.get("inference_block_count", 0),
        }
        for row in learning_state.get("cohorts") or ()
        if isinstance(row, Mapping) and row.get("law_sha256")
        and _known_by(row, epoch, "generated_at")
    }
    seen_entities = {
        str(row.get("entity_id") or "").upper()
        for row in visible_episodes if row.get("entity_id")
    }
    historical_kinds: dict[str, set[str]] = {}
    for row in visible_episodes:
        if not row.get("entity_id") or not row.get("entity_kind"):
            continue
        historical_kinds.setdefault(str(row["entity_id"]).upper(), set()).add(str(row["entity_kind"]))
    epoch_seconds = int(timestamp_key(epoch).timestamp())
    visible_queue = [
        row for row in queue_rows
        if str(row.get("kind") or "") in _DECISION_VALUE
        and (not int(row.get("created_at") or 0) or int(row.get("created_at") or 0) <= epoch_seconds)
    ]
    if (household_mandate_frontier is None) != (sleeve_implementation_frontier is None):
        raise ValueError("mandate relevance requires both mandate and implementation frontiers")
    mandate_relevance = (
        compile_mandate_research_relevance(
            [row for row in visible_queue if row.get("status") == "queued"],
            household_mandate_frontier=household_mandate_frontier,
            sleeve_implementation_frontier=sleeve_implementation_frontier,
        )
        if household_mandate_frontier is not None else None
    )
    relevance_by_work = {
        str(row["work_id"]): row for row in (mandate_relevance or {}).get("rows") or ()
    }
    class_totals = Counter(_action_class(str(row.get("kind") or "")) for row in visible_queue)
    class_served = Counter(
        _action_class(str(row.get("kind") or ""))
        for row in visible_queue if _research_was_served(row)
    )
    prior_entity_actions = Counter()
    for row in visible_queue:
        if not _research_was_served(row):
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        prior_entity_actions[(
            str(payload.get("entity_id") or "").upper(),
            _action_class(str(row.get("kind") or "")),
        )] += 1
    acquisition_rows = [
        *(((strategy_acquisition_policy or {}).get("control_batch") or {}).get("selected") or ()),
        *((strategy_acquisition_policy or {}).get("event_contract_frontier") or ()),
    ]
    acquisition_bonus = {
        str(row.get("work_id") or ""): float(row.get("scheduler_priority_bonus") or 0.0)
        for row in acquisition_rows
        if isinstance(row, Mapping) and row.get("work_id")
    }
    law_blind_priority = {
        str(row.get("work_id") or ""): int(row["scheduler_priority_override"])
        for row in ((strategy_acquisition_policy or {}).get("control_batch") or {}).get("selected") or ()
        if isinstance(row, Mapping)
        and row.get("law_blind_environment_probe")
        and row.get("work_id") and row.get("scheduler_priority_override") is not None
    }
    actions = []
    repeated: Counter[tuple[str, str]] = Counter(prior_entity_actions)
    ordered_rows = sorted(
        visible_queue,
        key=lambda row: (int(row.get("created_at") or 0), str(row.get("work_id") or "")),
    )
    for raw in ordered_rows:
        if raw.get("status") != "queued" or str(raw.get("kind") or "") not in _DECISION_VALUE:
            continue
        job = dict(raw)
        kind = str(job["kind"])
        payload = job.get("payload") if isinstance(job.get("payload"), Mapping) else {}
        world_model_components = (
            _market_flow_residual_components(payload)
            if kind == "jaggedthoughts_autoresearch_project" else None
        )
        constraint_components = _constraint_evidence_components(kind, payload)
        if kind == "jaggedthoughts_autoresearch_project" and world_model_components is None:
            continue
        entity_id = str(payload.get("entity_id") or "").upper()
        entity_kind = str(payload.get("entity_kind") or "")
        if not entity_kind and len(historical_kinds.get(entity_id, ())) == 1:
            entity_kind = next(iter(historical_kinds[entity_id]))
        if not entity_kind and kind == "jaggedthoughts_subscription_activation_research":
            entity_kind = "public_equity"
        law_blind = str(job.get("work_id") or "") in law_blind_priority
        applicable = [] if law_blind else [
            law for law in laws if _supports(job, law, entity_kind)
        ]
        applicable_ids = {str(law["law_sha256"]) for law in applicable}
        if laws and not law_blind:
            priced = price_experiment(
                laws,
                lambda law: "direct" if str(law["law_sha256"]) in applicable_ids else "indirect",
                _law_size,
                novel_context=bool(entity_id and entity_id not in seen_entities),
            )
            identification, compression, novelty = (
                priced.identification, priced.compression_gain, priced.novelty,
            )
        else:
            identification = compression = novelty = 0.0
        gap = 0.0 if law_blind else _cohort_gap(applicable, cohorts)
        components = {
            "law_scope_separation_upper_bound": identification,
            "law_scope_compression_upper_bound": compression,
            "unseen_entity_context": novelty,
            "cohort_sampling_gap_upper_bound": gap,
            "decision_proximity_prior": _DECISION_VALUE[kind],
            **(world_model_components or {
                "world_model_control_disagreement_upper_bound": 0.0,
                "world_model_cross_dimension_upper_bound": 0.0,
                "prospective_evidence_strength": 0.0,
            }),
            **(constraint_components or {
                "constraint_discrimination_upper_bound": 0.0,
                "constraint_falsification_surface_upper_bound": 0.0,
                "source_disjoint_replay_readiness": 0.0,
            }),
        }
        base_score = (
            0.40 * components["world_model_control_disagreement_upper_bound"]
            + 0.25 * components["world_model_cross_dimension_upper_bound"]
            + 0.25 * components["prospective_evidence_strength"]
            + 0.10 * components["decision_proximity_prior"]
            if world_model_components is not None else
            (
                components["constraint_discrimination_upper_bound"]
                + components["constraint_falsification_surface_upper_bound"]
                + components["source_disjoint_replay_readiness"]
                + components["decision_proximity_prior"]
            ) / 4.0
            if constraint_components is not None else
            sum(_WEIGHTS[key] * components[key] for key in _WEIGHTS)
        )
        action_class = _action_class(kind)
        repetition_key = (entity_id, action_class)
        repetition_ordinal = repeated.get(repetition_key, 0)
        repeated[repetition_key] = repetition_ordinal + 1
        redundancy_penalty = min(0.30, repetition_ordinal * _REPEATED_ENTITY_ACTION_PENALTY)
        score = max(0.0, base_score - redundancy_penalty)
        service_ratio = class_served[action_class] / class_totals[action_class]
        created_at = int(job.get("created_at") or 0)
        waiting_days = max(0.0, (epoch_seconds - created_at) / 86_400) if created_at else 0.0
        service_debt = 1.0 - service_ratio
        service_bonus = _SERVICE_BONUS_MAX * service_debt
        age_bonus = min(0.05, waiting_days * (0.05 / 7.0))
        starvation_guard = waiting_days >= 7.0
        strategy_bonus = (
            0.0 if law_blind
            else acquisition_bonus.get(str(job.get("work_id") or ""), 0.0)
        )
        ranking_score = score + service_bonus + age_bonus + strategy_bonus
        potential_ordered = kind in {
            "jaggedthoughts_subscription_research",
            "jaggedthoughts_subscription_activation_research",
            "jaggedthoughts_subscription_reassessment",
            "jaggedthoughts_candidate_payoff_forecast",
        } or (
            kind == "jaggedthoughts_strategy_frontier_research"
            and isinstance(payload.get("potential_rank"), Mapping)
            and int((payload.get("potential_rank") or {}).get("rank") or 0) > 0
        )
        frozen_chain_priority = int(payload.get("frozen_chain_priority") or 0)
        frozen_chain_successor = (
            kind in FROZEN_CHAIN_SUCCESSOR_JOB_KINDS and frozen_chain_priority > 0
        )
        residual_ordered = world_model_components is not None
        priority = (
            law_blind_priority[str(job.get("work_id") or "")]
            if law_blind else
            frozen_chain_priority
            if frozen_chain_successor else
            int(job.get("priority") or 0)
            if potential_ordered or frozen_chain_successor
            else (
                int(starvation_guard) * 10**15
                + (int(round(waiting_days * 1_000_000)) if starvation_guard else 0) * 1_000_001
                + int(round(ranking_score * 1_000_000))
            )
        )
        action = {
            "work_id": str(job.get("work_id") or ""),
            "kind": kind,
            "action_class": action_class,
            "entity_id": entity_id or None,
            "entity_kind": entity_kind or None,
            "applicable_law_ids": sorted(str(law.get("law_id")) for law in applicable),
            "applicable_law_count": len(applicable),
            "components": {key: round(value, 8) for key, value in components.items()},
            "base_learning_score": round(base_score, 8),
            "same_entity_action_ordinal": repetition_ordinal + 1,
            "redundancy_penalty": round(redundancy_penalty, 8),
            "learning_score": round(score, 8),
            "action_class_service_ratio": round(service_ratio, 8),
            "waiting_age_days": round(waiting_days, 8),
            "service_debt": round(service_debt, 8),
            "service_bonus": round(service_bonus, 8),
            "age_bonus": round(age_bonus, 8),
            "strategy_acquisition_bonus": round(strategy_bonus, 8),
            "frozen_chain_priority": frozen_chain_priority or None,
            "law_blind_environment_probe": law_blind,
            "starvation_guard": starvation_guard,
            "ranking_score": round(ranking_score, 8),
            "ordering_basis": (
                "law_blind_environment_probe" if law_blind else
                "prospective_chain_successor" if frozen_chain_successor else
                "prospective_world_model_residual_yield" if residual_ordered else
                "blind_constraint_information_yield"
                if constraint_components is not None else
                "candidate_potential_rank" if potential_ordered
                else "institutional_learning_information_yield"
            ),
            "queue_priority": priority,
            "queue_created_at_epoch": int(job.get("created_at") or 0),
        }
        if str(job.get("work_id") or "") in relevance_by_work:
            action["mandate_decision_relevance"] = relevance_by_work[str(job["work_id"])]
        actions.append(action)
    actions.sort(key=lambda row: (
        -row["queue_priority"], row["queue_created_at_epoch"], row["work_id"],
    ))
    for position, row in enumerate(actions, start=1):
        row["rank"] = position
        row["scheduler_position"] = position
    for basis in {str(row["ordering_basis"]) for row in actions}:
        lane = [row for row in actions if row["ordering_basis"] == basis]
        for lane_rank, row in enumerate(lane, start=1):
            row["lane_rank"] = lane_rank
            row["lane_size"] = len(lane)
    body = {
        "schema": LEARNING_SCHEDULE_SCHEMA,
        "generated_at": epoch,
        "committee": {
            "law_count": len(laws),
            "law_sha256s": sorted(str(row["law_sha256"]) for row in laws),
        },
        "policy": {
            "weights": dict(_WEIGHTS),
            "method": "typed_lane_proxy_plus_sampling_gap_and_service_debt",
            "yield_interpretation": "upper_bound_research_leverage_proxy",
            "observed_information_gain": False,
            "service_policy": "learning_proxy_plus_bounded_service_bonus_with_seven_day_starvation_guard",
            "outer_arbiter": "runtime_candidate_reservation_cadence_then_lane_priority",
            "repeated_entity_action_penalty": _REPEATED_ENTITY_ACTION_PENALTY,
            "maximum_service_bonus": _SERVICE_BONUS_MAX,
            "strategy_acquisition_policy_sha256": (
                (strategy_acquisition_policy or {}).get("policy_sha256")
            ),
            "law_blind_exploration_firewall": {
                "reserved_share": 0.2,
                "forbidden_inputs": [
                    "law_applicability", "law_support", "cohort_gap",
                    "strategy_acquisition_bonus",
                ],
                "authority": "research_queue_priority_only",
            },
            "world_model_residual_policy": {
                "weights": {
                    "control_disagreement": 0.40,
                    "cross_dimension": 0.25,
                    "prospective_evidence_strength": 0.25,
                    "decision_proximity": 0.10,
                },
                "eligibility": (
                    "hash_bound_successor_research_due_residual_only"
                ),
            },
        },
        "queued_action_count": len(actions),
        **({"mandate_research_relevance": mandate_relevance} if mandate_relevance else {}),
        "actions": actions,
        "next_action": actions[0] if actions else None,
        "boundary": (
            "This schedule orders already-admissible research. Law-scope, cohort-gap, and "
            "prospective world-model residual components are upper-bound leverage proxies, "
            "not measured information gain, expected returns, security ranks, or portfolio weights."
        ),
        "authority": "research_queue_priority_only",
        "capital_authority": False,
    }
    return {**body, "schedule_sha256": stable_sha256(body)}


__all__ = [
    "FROZEN_CHAIN_SUCCESSOR_JOB_KINDS",
    "LEARNING_SCHEDULE_SCHEMA",
    "compile_learning_schedule",
]
