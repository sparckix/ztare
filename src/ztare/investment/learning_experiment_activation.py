"""Compile issued, scheduled, and settleable learning experiments."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key


LEARNING_EXPERIMENT_ACTIVATION_SCHEMA = "jaggedthoughts-learning-experiment-activation-v1"
_RESEARCH_FAMILY = "coverage-vs-disagreement-itt-v2"
_RESEARCH_ARMS = {"coverage_first", "disagreement_first"}
_ACTIVE_JOB_STATES = {"queued", "claimed", "running", "retry_queued"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hashed(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    payload = dict(body)
    return {**payload, field: stable_sha256(payload)}


def _valid_hash(value: Mapping[str, Any], field: str) -> bool:
    claimed = str(value.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: child for key, child in value.items() if key != field
    })


def _design_for(
    design: Mapping[str, Any], component_id: str,
) -> Mapping[str, Any] | None:
    for collection in ("proposals", "active_experiments"):
        for row in design.get(collection) or ():
            if isinstance(row, Mapping) and row.get("component_id") == component_id:
                return row
    return None


def _research_activation(
    *, design: Mapping[str, Any], research_learning: Mapping[str, Any],
    research_requests: Sequence[Mapping[str, Any]],
    subscription_research: Mapping[str, Any], discovery: Mapping[str, Any],
) -> dict[str, Any] | None:
    experiment = _design_for(design, "research_question_policy")
    if experiment is None:
        return None
    family_id = str(experiment.get("family_id") or _RESEARCH_FAMILY)
    issued: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for request in research_requests:
        if not isinstance(request, Mapping):
            continue
        assignment = request.get("research_policy_assignment")
        if not isinstance(assignment, Mapping) or not assignment.get("eligible"):
            continue
        if assignment.get("experiment_id") != family_id or not _valid_hash(
            assignment, "assignment_sha256"
        ):
            continue
        public_refs = sorted(str(ref) for ref in request.get("source_refs") or () if ref)
        frozen = all((
            request.get("request_sha256"), request.get("candidate_leaf"), public_refs,
            assignment.get("arm_id") in _RESEARCH_ARMS,
            assignment.get("assignment_unit_id"), assignment.get("outcome_due_at"),
            assignment.get("randomization_sha256"),
        ))
        row = {
            "request_id": request.get("request_id"),
            "request_sha256": request.get("request_sha256"),
            "candidate_leaf": request.get("candidate_leaf"),
            "entity_id": request.get("entity_id"),
            "arm_id": assignment.get("arm_id"),
            "assignment_sha256": assignment.get("assignment_sha256"),
            "assignment_unit_id": assignment.get("assignment_unit_id"),
            "randomization_sha256": assignment.get("randomization_sha256"),
            "outcome_due_at": assignment.get("outcome_due_at"),
            "frozen_identity_and_public_evidence": bool(frozen),
            "lifecycle_stage": request.get("lifecycle_stage"),
        }
        issued.append(row)
        groups.setdefault(str(assignment.get("assignment_unit_id") or ""), []).append(row)

    valid_units = {
        unit_id: members for unit_id, members in groups.items()
        if unit_id
        and len({str(row.get("arm_id") or "") for row in members}) == 1
        and len({str(row.get("randomization_sha256") or "") for row in members}) == 1
        and all(row["frozen_identity_and_public_evidence"] for row in members)
    }
    valid_request_shas = {
        str(row["request_sha256"])
        for members in valid_units.values() for row in members
    }
    jobs = []
    for job in ((subscription_research.get("queue") or {}).get("jobs") or ()):
        if not isinstance(job, Mapping) or job.get("kind") != "jaggedthoughts_subscription_research":
            continue
        payload = job.get("payload") if isinstance(job.get("payload"), Mapping) else {}
        if str(payload.get("request_sha256") or "") not in valid_request_shas:
            continue
        jobs.append({
            "work_id": job.get("work_id"), "status": job.get("status"),
            "request_sha256": payload.get("request_sha256"),
            "candidate_leaf": payload.get("candidate_leaf"),
            "entity_id": payload.get("entity_id"),
        })
    jobs.sort(key=lambda row: (str(row["status"]), str(row["work_id"])))
    active_jobs = [row for row in jobs if row["status"] in _ACTIVE_JOB_STATES]
    question = dict(research_learning.get("research_question_policy_experiment") or {})
    next_due = (discovery.get("schedule") or {}).get("next_due_at")
    if active_jobs:
        next_activation = {
            "transition": "continue_exact_subscription_research_job",
            "work_id": active_jobs[0]["work_id"],
            "request_sha256": active_jobs[0]["request_sha256"],
            "not_before": None, "blocker": None,
        }
    else:
        next_activation = {
            "transition": "assign_next_candidate_level_randomized_unit",
            "work_id": None, "request_sha256": None,
            "not_before": next_due,
            "blocker": (
                "awaiting_current_qualified_candidate_with_frozen_candidate_leaf_and_"
                "public_source_refs"
            ),
        }
    request_keys = [str(row.get("request_sha256") or "") for row in issued]
    candidate_keys = [str(row.get("candidate_leaf") or "") for row in issued]
    body = {
        "experiment_id": experiment.get("experiment_id"),
        "family_id": family_id,
        "component_id": "research_question_policy",
        "state": "issued_waiting_outcome" if valid_units else "awaiting_assignment_unit",
        "issued": {
            "request_count": len(issued),
            "valid_assignment_unit_count": len(valid_units),
            "valid_assignment_unit_ids": sorted(valid_units),
            "duplicate_issue_count": sum(max(0, len(rows) - 1) for rows in valid_units.values()),
            "invalid_assignment_unit_count": len(groups) - len(valid_units),
        },
        "scheduled": {"job_count": len(jobs), "active_job_count": len(active_jobs), "jobs": jobs},
        "deduplication": {
            "keys": ["request_sha256", "candidate_leaf"],
            "duplicate_request_count": len(request_keys) - len(set(request_keys)),
            "duplicate_candidate_leaf_count": len(candidate_keys) - len(set(candidate_keys)),
            "valid": len(request_keys) == len(set(request_keys))
            and len(valid_units) == len(groups),
        },
        "settlement": {
            "settled_independent_block_count": int(
                question.get("settled_itt_unit_count") or 0
            ),
            "minimum_independent_blocks_per_arm": int(
                question.get("minimum_settled_units_per_arm") or 20
            ),
            "due_censored_block_count": int(
                question.get("censored_due_unit_count") or 0
            ),
            "authority": "complete_due_intent_to_treat_cohorts_only",
        },
        "next_activation": next_activation,
        "historical_repair_forbidden": True,
        "capital_authority": False,
    }
    return _hashed(body, "activation_sha256")


def _strategy_activation(
    *, design: Mapping[str, Any], strategy_alpha_tournament: Mapping[str, Any],
    capital_cycle: Mapping[str, Any],
) -> dict[str, Any] | None:
    experiment = _design_for(design, "underwriting_forecast_bundle")
    if experiment is None:
        return None
    binding_status = dict(strategy_alpha_tournament.get("binding_activation") or {})
    activations = [
        dict(row) for row in binding_status.get("activation_statuses") or ()
        if isinstance(row, Mapping) and row.get("status") in {"activated", "bound"}
    ]
    activations.sort(key=lambda row: str(row.get("run_id") or ""))
    actions = [{
        key: row.get(key) for key in (
            "run_id", "action_id", "action_sha256", "binding_sha256", "evaluated_at",
        )
    } for row in activations]
    bound_ids = {str(row.get("run_id") or "") for row in activations}
    settlement_gaps = [
        row for row in (strategy_alpha_tournament.get("evidence") or {}).get("gaps") or ()
        if isinstance(row, Mapping) and row.get("code") == "settlement_missing"
        and str(row.get("run_id") or "") in bound_ids and row.get("end_at")
    ]
    not_before = max(
        (canonical_timestamp(row["end_at"], "strategy settlement end_at") for row in settlement_gaps),
        key=timestamp_key, default=None,
    )
    latest = capital_cycle.get("latest_run") if isinstance(capital_cycle.get("latest_run"), Mapping) else {}
    schedule = latest.get("strategy_alpha_schedule") if isinstance(latest.get("strategy_alpha_schedule"), Mapping) else {}
    scheduled = [
        dict(row) for row in schedule.get("scheduled_windows") or () if isinstance(row, Mapping)
    ]
    eligible = [
        dict(row) for row in schedule.get("eligibility") or ()
        if isinstance(row, Mapping) and row.get("eligible")
    ]
    if scheduled:
        nomination = scheduled[0]
        next_activation = {
            "transition": "issue_preopen_subscription_strategy_alpha_action",
            "subject_id": nomination.get("candidate_id"),
            "nomination_sha256": nomination.get("nomination_sha256"),
            "not_before": nomination.get("start_at"), "blocker": None,
        }
        state = "ready_for_exact_preopen_action"
    else:
        next_activation = {
            "transition": "schedule_next_nonoverlapping_strategy_alpha_window",
            "subject_id": eligible[0].get("candidate_id") if eligible else None,
            "nomination_sha256": None, "not_before": not_before,
            "blocker": (
                "awaiting_nonoverlapping_due_forecast_window" if eligible
                else "awaiting_current_candidate_with_quality_and_exact_strategy_phenotype"
            ),
        }
        state = "issued_waiting_outcome" if actions else "awaiting_eligible_episode"
    action_keys = [str(row.get("action_sha256") or "") for row in actions]
    binding_keys = [str(row.get("binding_sha256") or "") for row in actions]
    historical_closed = sum(
        "issuance_window_closed" in set(row.get("gap_codes") or ())
        for row in binding_status.get("runs") or () if isinstance(row, Mapping)
    )
    evidence = dict(strategy_alpha_tournament.get("evidence") or {})
    body = {
        "experiment_id": experiment.get("experiment_id"),
        "family_id": experiment.get("family_id"),
        "component_id": "underwriting_forecast_bundle",
        "state": state,
        "issued": {
            "binding_count": len(actions), "actions": actions,
            "non_recoverable_historical_count": historical_closed,
        },
        "scheduled": {
            "window_count": len(scheduled),
            "windows": scheduled,
            "eligible_subject_ids": sorted(str(row.get("candidate_id") or "") for row in eligible),
        },
        "deduplication": {
            "scheduler_key": "dual_outcome_episode_key_sha256",
            "duplicate_action_count": len(action_keys) - len(set(action_keys)),
            "duplicate_binding_count": len(binding_keys) - len(set(binding_keys)),
            "valid": len(action_keys) == len(set(action_keys))
            and len(binding_keys) == len(set(binding_keys)),
        },
        "settlement": {
            "settlement_count": int(evidence.get("settlement_count") or 0),
            "settled_independent_block_count": int(strategy_alpha_tournament.get("eligible_episode_count") or 0),
            "minimum_independent_blocks": 8,
            "authority": "closed_book_benchmark_relative_return_only",
        },
        "next_activation": next_activation,
        "issue_only_if": [
            "current_discovery_candidate_and_golden_candidate_leaf",
            "current_quality_report",
            "admitted_exact_phenotype_move_and_implementation_event",
            "public_source_supported_three_arm_preopen_forecast",
            "nonoverlapping_due_forecast_window",
        ],
        "historical_repair_forbidden": True,
        "capital_authority": False,
    }
    return _hashed(body, "activation_sha256")


def _household_activation(
    *, design: Mapping[str, Any], household_policy_tournament: Mapping[str, Any],
) -> dict[str, Any] | None:
    experiment = _design_for(design, "household_implementation_rule")
    if experiment is None:
        return None
    household = dict(household_policy_tournament)
    latest = dict(household.get("latest_run") or {})
    reviews = [row for row in household.get("reviews") or () if isinstance(row, Mapping)]
    blocks = max((
        int((row.get("survivor_set") or {}).get("inference_block_count") or 0)
        for row in reviews
    ), default=0)
    pending = int(household.get("pending_count") or 0)
    if pending and latest:
        next_activation = {
            "transition": "settle_frozen_household_policy_when_due",
            "subject_id": latest.get("run_id"), "not_before": latest.get("end_at"),
            "blocker": "prospective_return_window_not_mature",
        }
        state = "issued_waiting_outcome"
    else:
        next_activation = {
            "transition": "freeze_displayed_household_policy_rivals",
            "subject_id": None, "not_before": None,
            "blocker": "operator_must_review_and_activate_current_household_scenario",
        }
        state = "awaiting_operator_scenario_freeze"
    body = {
        "experiment_id": experiment.get("experiment_id"),
        "family_id": experiment.get("family_id"),
        "component_id": "household_implementation_rule", "state": state,
        "issued": {
            "run_count": int(household.get("run_count") or 0),
            "latest_run_id": latest.get("run_id"),
            "latest_scenario_sha256": latest.get("scenario_sha256"),
        },
        "scheduled": {
            "owner": "periodic_capital_cycle_after_explicit_freeze",
            "entry_or_due_exit_entity_refresh": True,
        },
        "settlement": {
            "settlement_count": int(household.get("settled_count") or 0),
            "settled_independent_block_count": blocks,
            "minimum_independent_blocks": 8,
            "authority": "later_complete_policy_return_vs_broad_sleeve_control_only",
        },
        "next_activation": next_activation,
        "historical_repair_forbidden": True,
        "policy_authority": False, "capital_authority": False,
    }
    return _hashed(body, "activation_sha256")


def compile_learning_experiment_activation(
    *, learning_experiment_design: Mapping[str, Any],
    research_learning: Mapping[str, Any],
    research_requests: Sequence[Mapping[str, Any]],
    subscription_research: Mapping[str, Any], discovery: Mapping[str, Any],
    strategy_alpha_tournament: Mapping[str, Any], capital_cycle: Mapping[str, Any],
    household_policy_tournament: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Expose the next lawful transition; existing owners perform the mutation."""

    transitions = [row for row in (
        _research_activation(
            design=learning_experiment_design, research_learning=research_learning,
            research_requests=research_requests, subscription_research=subscription_research,
            discovery=discovery,
        ),
        _strategy_activation(
            design=learning_experiment_design,
            strategy_alpha_tournament=strategy_alpha_tournament,
            capital_cycle=capital_cycle,
        ),
        _household_activation(
            design=learning_experiment_design,
            household_policy_tournament=household_policy_tournament or {},
        ),
    ) if row is not None]
    next_rows = [
        {"component_id": row["component_id"], **row["next_activation"]}
        for row in transitions
    ]
    immediate = [row for row in next_rows if row.get("blocker") is None]
    dated = [row for row in next_rows if row.get("not_before")]
    next_transition = (
        sorted(immediate, key=lambda row: str(row.get("component_id")))[0]
        if immediate else
        min(dated, key=lambda row: timestamp_key(str(row["not_before"]))) if dated else None
    )
    body = {
        "schema": LEARNING_EXPERIMENT_ACTIVATION_SCHEMA,
        "identity": "prospective_learning_experiment_activation_policy",
        "compiled_at": canonical_timestamp(generated_at or _now(), "activation compiled_at"),
        "source_design_sha256": learning_experiment_design.get("design_sha256"),
        "transitions": transitions,
        "next_transition": next_transition,
        "counts": {
            "tracked": len(transitions),
            "issued": sum(int(
                row["issued"].get("binding_count")
                or row["issued"].get("valid_assignment_unit_count")
                or row["issued"].get("valid_pair_count")
                or row["issued"].get("run_count") or 0
            ) for row in transitions),
            "settled_independent_blocks": sum(int(row["settlement"].get("settled_independent_block_count") or 0) for row in transitions),
        },
        "boundary": (
            "This compiler reports lawful transitions owned by the existing discovery, subscription-"
            "research, closed-book, household-policy, and settlement state machines. It creates no synthetic experiment, "
            "rewrites no historical issuance, and grants no capital authority."
        ),
        "authority": "paper_learning_activation_policy_only",
        "capital_authority": False,
    }
    return _hashed(body, "policy_sha256")


__all__ = [
    "LEARNING_EXPERIMENT_ACTIVATION_SCHEMA", "compile_learning_experiment_activation",
]
