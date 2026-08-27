"""Bound the next acquisitions that can distinguish strategy transfer."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .strategy_control_eligibility import STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA
from .strategy_event_refinement import STRATEGY_EVENT_REFINEMENT_JOB_KIND
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA,
    STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
    compile_strategy_program_adoption_result,
)
from .strategy_transfer import STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA


STRATEGY_TRANSFER_ACQUISITION_SCHEMA = "jaggedthoughts-strategy-transfer-acquisition-policy-v1"
STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA = (
    "jaggedthoughts-strategy-program-control-acquisition-v1"
)
_ACTIVE = {"queued", "claimed", "running", "retry_queued"}


def _next_utc_day(value: str) -> str:
    return (timestamp_key(value).replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=1)).isoformat(timespec="seconds").replace("+00:00", "Z")


def _family_index(library: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("mechanism_signature_sha256") or ""): row
        for row in library.get("move_families") or ()
        if isinstance(row, Mapping) and row.get("mechanism_signature_sha256")
    }


def _event_contract_frontier(library: Mapping[str, Any]) -> list[dict[str, Any]]:
    families = _family_index(library)
    rows = []
    for move in library.get("moves") or ():
        if not isinstance(move, Mapping) or move.get("claim_status") != "supported":
            continue
        status = str(move.get("causal_panel_status") or "")
        contracts = list(move.get("outcome_contracts") or ())
        if status == "treatment_event_ready" and contracts:
            continue
        family = families.get(str(move.get("mechanism_signature_sha256") or ""), {})
        if status == "treatment_timing_interval_censored" and contracts:
            acquisition = "sharpen_focal_implementation_interval"
            readiness = 3
        elif move.get("implementation_event") and not contracts:
            acquisition = "declare_source_bound_operating_outcome_contract"
            readiness = 2
        elif not move.get("implementation_event"):
            acquisition = "acquire_exact_implementation_event_then_outcome_contract"
            readiness = 1
        else:
            continue
        row = {
            "entity_id": move.get("entity_id"), "move_sha256": move.get("move_sha256"),
            "option_id": move.get("option_id"), "description": move.get("description"),
            "mechanism_signature": move.get("mechanism_signature"),
            "mechanism_signature_sha256": move.get("mechanism_signature_sha256"),
            "mechanism_phenotype_sha256": move.get("mechanism_phenotype_sha256"),
            "acquisition": acquisition,
            "current_timing_status": status,
            "contract_sha256s": sorted(
                str(contract.get("contract_sha256") or "") for contract in contracts
            ),
            "family_entity_count": len(family.get("entity_ids") or ()),
            "family_environment_count": int(family.get("environment_count") or 0),
            "frontier_bundle_count": int(move.get("frontier_bundle_count") or 0),
            "local_peak_bundle_count": int(move.get("local_peak_bundle_count") or 0),
            "source_refs": sorted(str(ref) for ref in move.get("evidence_refs") or ()),
            "issue_now": False,
            "blocker": "requires_current_public_evidence_and_strategy_frontier_recompilation",
            "capital_authority": False,
        }
        row["priority_vector"] = [
            readiness, row["family_entity_count"], row["family_environment_count"],
            row["frontier_bundle_count"], row["local_peak_bundle_count"],
        ]
        rows.append(row)
    return sorted(rows, key=lambda row: (
        tuple(-int(value) for value in row["priority_vector"]),
        str(row["entity_id"]), str(row["move_sha256"]),
    ))


def compile_strategy_transfer_acquisition_policy(
    *, library: Mapping[str, Any], cohort_plan: Mapping[str, Any],
    control_frontier: Mapping[str, Any], panel_readiness: Mapping[str, Any],
    queue_jobs: Sequence[Mapping[str, Any]], subscription_research: Mapping[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Choose a small control batch, then expose later outcome/event frontiers."""

    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("strategy acquisition requires a strategy move library")
    if cohort_plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        raise ValueError("strategy acquisition requires a cohort plan")
    if control_frontier.get("schema") != STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA:
        raise ValueError("strategy acquisition requires a control frontier")
    plan_sha = str(cohort_plan.get("plan_sha256") or "")
    if control_frontier.get("plan_sha256") != plan_sha or panel_readiness.get("plan_sha256") != plan_sha:
        raise ValueError("strategy acquisition inputs cross cohort-plan identities")
    compiled_at = canonical_timestamp(generated_at, "strategy acquisition generated_at")
    requests = {
        str(row.get("request_sha256") or ""): row
        for row in cohort_plan.get("requests") or () if isinstance(row, Mapping)
    }
    histories = {
        str(row.get("entity_id") or "").upper(): row
        for row in panel_readiness.get("history_status") or ()
        if isinstance(row, Mapping) and row.get("entity_id")
    }
    transfer_anchors = {
        (
            str(row.get("mechanism_phenotype_sha256") or ""),
            str(row.get("target_industry_id") or ""),
        ): {str(entity).upper() for entity in row.get("anchor_entity_ids") or ()}
        for row in cohort_plan.get("transfer_environment_searches") or ()
        if isinstance(row, Mapping)
    }
    jobs = {}
    event_jobs = {}
    for row in queue_jobs:
        if not isinstance(row, Mapping):
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        if row.get("kind") == STRATEGY_EVENT_REFINEMENT_JOB_KIND:
            move_sha = str(payload.get("move_sha256") or "")
            if move_sha and row.get("status") in _ACTIVE:
                event_jobs[move_sha] = row
            continue
        if row.get("kind") != "jaggedthoughts_strategy_cohort_research":
            continue
        request_sha = str(payload.get("request_sha256") or "")
        if request_sha in requests and row.get("status") in _ACTIVE:
            jobs[request_sha] = row

    candidates = []
    for source_request in control_frontier.get("next_source_requests") or ():
        if not isinstance(source_request, Mapping):
            continue
        request_sha = str(source_request.get("request_sha256") or "")
        request, job = requests.get(request_sha), jobs.get(request_sha)
        if request is None or job is None:
            continue
        entity = str(request.get("peer_entity_id") or "").upper()
        history = histories.get(entity, {})
        required = list(source_request.get("required_evidence") or ())
        periods = int(history.get("period_count") or 0)
        immediate = "pre_period_earnings_durability_history" not in required
        candidates.append({
            "work_id": job.get("work_id"), "request_sha256": request_sha,
            "peer_entity_id": entity,
            "mechanism_signature_sha256": request.get("mechanism_signature_sha256"),
            "mechanism_phenotype_sha256": request.get("mechanism_phenotype_sha256"),
            "industry_id": request.get("industry_id"),
            "search_role": request.get("search_role") or "within_environment_control_discovery",
            "law_blind_environment_probe": (
                request.get("search_role") == "law_blind_environment_probe"
            ),
            "law_blind_selection_receipt": request.get(
                "law_blind_selection_receipt"
            ),
            "transfer_anchor": entity in transfer_anchors.get((
                str(request.get("mechanism_phenotype_sha256") or ""),
                str(request.get("industry_id") or ""),
            ), set()),
            "period_count": periods,
            "immediate_control_admission_if_no_family_adoption": immediate,
            "required_evidence": required,
            "search_end_at": request.get("search_end_at"),
            "queue_status": job.get("status"),
        })
    candidates.sort(key=lambda row: (
        not row["immediate_control_admission_if_no_family_adoption"],
        -row["period_count"], len(row["required_evidence"]), row["peer_entity_id"],
    ))
    target = int(cohort_plan.get("target_control_unit_count") or 4)
    admitted = int((control_frontier.get("audit") or {}).get("admissible_control_count") or 0)
    batch_size = max(0, target - admitted)
    transfer_groups: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        if row["search_role"] == "cross_environment_transfer_discovery":
            transfer_groups.setdefault(str(row["industry_id"]), []).append(row)
    for rows in transfer_groups.values():
        rows.sort(key=lambda row: (
            not row["transfer_anchor"],
            not row["immediate_control_admission_if_no_family_adoption"],
            -row["period_count"], len(row["required_evidence"]), row["peer_entity_id"],
        ))
    transfer_first = []
    while any(transfer_groups.values()):
        for industry in sorted(transfer_groups):
            if transfer_groups[industry]:
                transfer_first.append(transfer_groups[industry].pop(0))
    law_blind = sorted(
        (row for row in candidates if row["law_blind_environment_probe"]),
        key=lambda row: (
            str((row.get("law_blind_selection_receipt") or {}).get(
                "sampling_frame_sha256"
            )),
            row["peer_entity_id"],
        ),
    )
    reserved = law_blind[:1]
    directed = [
        row for row in transfer_first if not row["law_blind_environment_probe"]
    ] + [
        row for row in candidates
        if row not in transfer_first and not row["law_blind_environment_probe"]
    ]
    total_slots = max(batch_size, 1 if reserved else 0)
    selected = reserved + directed[:max(0, total_slots - len(reserved))]
    selected_work_ids = {str(row["work_id"]) for row in selected}
    for rank, row in enumerate(selected, start=1):
        row["selection_rank"] = rank
        if row["law_blind_environment_probe"]:
            row["reserved_exploration_position"] = 1
            row["scheduler_priority_override"] = 900_000
            row["scheduler_priority_bonus"] = 0.0
        else:
            row["scheduler_priority_bonus"] = round(0.6 - (rank - 1) * 0.01, 8)

    unsettled = []
    for move in library.get("moves") or ():
        if not isinstance(move, Mapping):
            continue
        settled = {str(row.get("contract_sha256") or "") for row in move.get("outcome_episodes") or ()}
        for contract in move.get("outcome_contracts") or ():
            if str(contract.get("contract_sha256") or "") in settled:
                continue
            unsettled.append({
                "move_sha256": move.get("move_sha256"), "entity_id": move.get("entity_id"),
                "contract_sha256": contract.get("contract_sha256"),
                "metric_id": contract.get("metric_id"), "due_at": contract.get("due_at"),
                "timing_status": move.get("causal_panel_status"),
                "evidence_use": (
                    "causal_panel_candidate" if move.get("causal_panel_status") == "treatment_event_ready"
                    else "descriptive_operating_outcome_only"
                ),
            })
    unsettled.sort(key=lambda row: (str(row["due_at"]), str(row["contract_sha256"])))
    event_frontier = _event_contract_frontier(library)
    budget = dict(subscription_research.get("daily_dispatch_budget") or {})
    not_before = _next_utc_day(compiled_at) if budget.get("exhausted") else None
    for row in event_frontier:
        job = event_jobs.get(str(row["move_sha256"]))
        if not job:
            continue
        row.update({
            "issue_now": True, "work_id": job.get("work_id"),
            "queue_status": job.get("status"), "queue_priority": job.get("priority"),
            "scheduler_priority_bonus": 0.75,
            "not_before": not_before,
            "blocker": "subscription_dispatch_budget_exhausted" if not_before else None,
        })
    if selected:
        next_transition = {
            "transition": "classify_exact_peer_for_control_admission",
            "work_id": selected[0]["work_id"],
            "peer_entity_id": selected[0]["peer_entity_id"],
            "request_sha256": selected[0]["request_sha256"],
            "not_before": not_before,
            "blocker": "subscription_dispatch_budget_exhausted" if not_before else None,
        }
    elif unsettled:
        next_transition = {
            "transition": "settle_next_declared_operating_outcome",
            "work_id": None, "contract_sha256": unsettled[0]["contract_sha256"],
            "not_before": unsettled[0]["due_at"], "blocker": "outcome_horizon_not_matured",
        }
    else:
        next_transition = None
    body = {
        "schema": STRATEGY_TRANSFER_ACQUISITION_SCHEMA,
        "compiled_at": compiled_at,
        "library_sha256": library.get("library_sha256"), "cohort_plan_sha256": plan_sha,
        "control_frontier_sha256": control_frontier.get("control_frontier_sha256"),
        "census": {
            "move_count": int(library.get("move_count") or 0),
            "move_family_count": int(library.get("move_family_count") or 0),
            "exact_focal_move_count": int(cohort_plan.get("exact_focal_move_count") or 0),
            "admissible_control_count": admitted,
            "pending_control_candidate_count": len(candidates),
            "unsettled_outcome_contract_count": len(unsettled),
            "active_event_refinement_count": len(event_jobs),
        },
        "control_batch": {
            "target_new_control_count": batch_size,
            "selection_method": (
                "reserve one law-blind environment probe, then source-bound transfer "
                "environments round-robin, anchors before peers, and immediate control yield"
            ),
            "law_blind_reserved_share": 0.2,
            "law_blind_selected_count": len(reserved),
            "selected": selected,
            "deferred": [
                row for row in candidates
                if str(row["work_id"]) not in selected_work_ids
            ],
            "refill_after_each_classification": True,
        },
        "outcome_watch": unsettled,
        "event_contract_frontier": event_frontier,
        "next_cross_family_acquisition": next(
            (row for row in event_frontier if row.get("issue_now")),
            event_frontier[0] if event_frontier else None,
        ),
        "next_transition": next_transition,
        "boundary": (
            "The policy changes acquisition order only. It does not infer non-adoption, author an "
            "implementation date or outcome contract, settle an outcome, promote a law, or allocate capital."
        ),
        "authority": "strategy_research_acquisition_order_only",
        "capital_authority": False,
    }
    return {**body, "policy_sha256": stable_sha256(body)}


def compile_strategy_program_control_acquisition(
    *, program_transfer: Mapping[str, Any], library: Mapping[str, Any],
    program_requests: Sequence[Mapping[str, Any]],
    program_results: Sequence[Mapping[str, Any]] = (),
    queue_jobs: Sequence[Mapping[str, Any]] = (), generated_at: str,
) -> dict[str, Any]:
    """Point integrated-program cards at source-bound composition controls."""

    if program_transfer.get("schema") != STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA:
        raise ValueError("program control acquisition requires a program-transfer index")
    if program_transfer.get("index_sha256") != stable_sha256({
        key: value for key, value in program_transfer.items() if key != "index_sha256"
    }):
        raise ValueError("program control acquisition transfer-index hash mismatch")
    if library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError("program control acquisition requires a strategy move library")
    epoch = canonical_timestamp(generated_at, "program control acquisition generated_at")
    moves = {
        str(row.get("move_sha256") or ""): row
        for row in library.get("moves") or ()
        if isinstance(row, Mapping) and row.get("move_sha256")
    }
    requests = {
        str(row.get("request_sha256")): dict(row)
        for row in program_requests
        if isinstance(row, Mapping)
        and row.get("schema") == STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA
        and row.get("request_sha256") == stable_sha256({
            key: value for key, value in row.items() if key != "request_sha256"
        })
        and timestamp_key(str(row.get("search_end_at"))) <= timestamp_key(epoch)
    }
    results = {}
    for raw in program_results:
        if not isinstance(raw, Mapping) or raw.get("schema") != STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA:
            continue
        request = requests.get(str(raw.get("request_sha256") or ""))
        if request is None or timestamp_key(str(raw.get("assessed_at"))) > timestamp_key(epoch):
            continue
        try:
            verified = compile_strategy_program_adoption_result(raw, request)
        except (KeyError, TypeError, ValueError):
            continue
        if verified.get("result_sha256") == raw.get("result_sha256"):
            results[str(request["request_sha256"])] = verified
    jobs = {
        str((row.get("payload") or {}).get("request_sha256") or ""): row
        for row in queue_jobs
        if isinstance(row, Mapping)
        and row.get("kind") == "jaggedthoughts_strategy_program_adoption_research"
        and isinstance(row.get("payload"), Mapping)
        and row.get("status") in _ACTIVE
    }

    cards = []
    for card in program_transfer.get("cards") or ():
        if not isinstance(card, Mapping):
            continue
        phenotype = dict(card.get("program_phenotype") or {})
        wanted = Counter(map(str, phenotype.get("constituent_mechanism_phenotype_sha256s") or ()))
        if not wanted or sum(wanted.values()) != int(phenotype.get("constituent_count") or 0):
            continue
        treated = set(map(str, card.get("entity_ids") or ()))
        treated_environments = set(map(str, card.get("environment_boundaries") or ()))
        readout_signature = (
            str(card.get("metric_id") or ""), str(card.get("unit") or ""),
            str(card.get("direction") or ""), float(card.get("minimum_effect") or 0.0),
            int(card.get("horizon_days") or 0),
            str(card.get("outcome_role") or "terminal_operating"),
            str(card.get("acquisition_mode") or "subscription_primary_document"),
            str(card.get("source_definition_sha256") or ""),
        )
        targets = []
        for request_sha, request in requests.items():
            entity_id = str(request.get("entity_id") or "")
            if entity_id in treated:
                continue
            result, job = results.get(request_sha), jobs.get(request_sha)
            selected_ids = set(map(str, (result or {}).get("selected_program_ids") or ()))
            event_ids = set(
                str(row.get("option_id")) for row in (result or {}).get("option_events") or ()
            )
            full_coverage = bool(
                ((result or {}).get("coverage") or {}).get("sec_filings_searched")
                and ((result or {}).get("coverage") or {}).get("issuer_materials_searched")
            )
            result_events = {
                str(row.get("option_id")): row
                for row in (result or {}).get("option_events") or ()
                if isinstance(row, Mapping) and row.get("option_id")
            }
            for program in request.get("candidate_programs") or ():
                if not isinstance(program, Mapping):
                    continue
                option_ids = {str(row.get("option_id")) for row in program.get("options") or ()}
                program_moves = [moves.get(str(row.get("move_sha256") or "")) for row in program.get("options") or ()]
                if not program_moves or any(not isinstance(row, Mapping) for row in program_moves):
                    continue
                search_end = str(request.get("search_end_at"))
                program_events = []
                for option, move in zip(program.get("options") or (), program_moves, strict=True):
                    option_id = str(option.get("option_id") or "")
                    event = result_events.get(option_id)
                    if event is None and move.get("causal_panel_status") == "treatment_event_ready":
                        event = move.get("implementation_event")
                    if not isinstance(event, Mapping) or timestamp_key(str(event.get("available_at"))) > timestamp_key(search_end):
                        program_events = []
                        break
                    program_events.append(event)
                if len(program_events) != len(program_moves):
                    continue
                candidate_environments = sorted({
                    str((row.get("environment") or {}).get("industry_boundary") or "")
                    for row in program_moves
                } - {""})
                if treated_environments and not treated_environments.intersection(candidate_environments):
                    continue
                matched_contracts = [
                    (str(row.get("move_sha256")), str(contract.get("contract_sha256")))
                    for row in program_moves for contract in row.get("outcome_contracts") or ()
                    if (
                        str(contract.get("metric_id") or ""), str(contract.get("unit") or ""),
                        str(contract.get("direction") or ""),
                        float(contract.get("minimum_effect") or 0.0),
                        int(contract.get("horizon_days") or 0),
                        str(contract.get("outcome_role") or "terminal_operating"),
                        str(contract.get("acquisition_mode") or "subscription_primary_document"),
                        stable_sha256({
                            "metric_locator": contract.get("metric_locator"),
                            "measurement_source_catalog": contract.get("measurement_source_catalog"),
                        }),
                    ) == readout_signature and contract.get("evidence_refs")
                ]
                if len({move_sha for move_sha, _ in matched_contracts}) < 2:
                    continue
                observed = Counter(
                    str(row.get("mechanism_phenotype_sha256") or "") for row in program_moves
                )
                same_constituents = observed == wanted
                one_choice_base = bool(
                    sum(observed.values()) + 1 == sum(wanted.values())
                    and all(observed[key] <= wanted[key] for key in observed)
                )
                missing_constituents = sorted((wanted - observed).elements())
                program_roles = set(map(str, program.get("roles") or ()))
                same_size_local_peak = (
                    len(program_moves) == sum(wanted.values())
                    and "local_peak" in program_roles
                    and "global_frontier" not in program_roles
                )
                if not (same_constituents or one_choice_base or same_size_local_peak):
                    continue
                program_id = str(program.get("program_id") or "")
                selected_program = program_id in selected_ids
                fragmented = bool(
                    same_constituents and result
                    and result.get("classification") in {
                        "partial_option_adoption", "no_integrated_program_adoption_found",
                    }
                    and full_coverage and event_ids == option_ids
                    and not result.get("joint_execution_source_urls")
                )
                local_peak = bool(
                    same_size_local_peak and selected_program and result
                    and result.get("classification") == "exact_integrated_program_adoption"
                )
                base_program = bool(
                    one_choice_base and selected_program and result
                    and result.get("classification") == "exact_integrated_program_adoption"
                )
                roles = [
                    label for label, enabled in (
                        ("same_constituents_fragmented", fragmented),
                        ("one_choice_base_program", base_program),
                        ("same_size_local_peak", local_peak),
                    ) if enabled
                ]
                control_readout = None
                if roles and result:
                    measurement_start_at = canonical_timestamp(
                        result["assessed_at"], "program control assessed_at",
                    )
                    due_at = (
                        timestamp_key(measurement_start_at)
                        + timedelta(days=readout_signature[4])
                    ).isoformat(timespec="seconds").replace("+00:00", "Z")
                    readout_body = {
                        "schema": "jaggedthoughts-strategy-program-control-outcome-plan-v1",
                        "request_sha256": request_sha,
                        "result_sha256": result["result_sha256"],
                        "entity_id": entity_id,
                        "program_id": program_id,
                        "control_identity": {
                            "same_constituents_fragmented": "same_constituents_without_joint_evidence",
                            "one_choice_base_program": "one_choice_base_program",
                            "same_size_local_peak": "same_size_local_peak",
                        }[roles[0]],
                        "metric_id": readout_signature[0],
                        "unit": readout_signature[1],
                        "direction": readout_signature[2],
                        "minimum_effect": readout_signature[3],
                        "horizon_days": readout_signature[4],
                        "outcome_role": readout_signature[5],
                        "acquisition_mode": readout_signature[6],
                        "source_definition_sha256": readout_signature[7],
                        "comparator": "assessment_time_baseline",
                        "measurement_start_at": measurement_start_at,
                        "due_at": due_at,
                        "environment_boundaries": candidate_environments,
                        "basis_contract_sha256s": sorted({
                            contract_sha for _, contract_sha in matched_contracts
                        }),
                        "selection_rule": (
                            "latest admitted observation at or before source classification; "
                            "earliest admitted observation at or after the frozen horizon"
                        ),
                    }
                    control_readout = {
                        **readout_body,
                        "control_plan_sha256": stable_sha256(readout_body),
                    }
                targets.append({
                    "entity_id": entity_id, "request_sha256": request_sha,
                    "program_id": program_id, "program_expression": program.get("expression"),
                    "constituent_mechanism_phenotype_sha256s": sorted(observed.elements()),
                    "missing_target_constituent_mechanism_phenotype_sha256s": missing_constituents,
                    "candidate_control_classes": [
                        label for label, enabled in (
                            ("same_constituents_fragmented", same_constituents),
                            ("one_choice_base_program", one_choice_base),
                            ("same_size_local_peak", same_size_local_peak),
                        ) if enabled
                    ],
                    "admitted_control_classes": roles,
                    "source_classification_status": (
                        "classified" if result else str((job or {}).get("status") or "awaiting_queue")
                    ),
                    "classification": (result or {}).get("classification"),
                    "result_sha256": (result or {}).get("result_sha256"),
                    "work_id": (job or {}).get("work_id"),
                    "search_end_at": request.get("search_end_at"),
                    "environment_boundaries": candidate_environments,
                    "matched_outcome_contract_sha256s": sorted({
                        contract_sha for _, contract_sha in matched_contracts
                    }),
                    "control_readout": control_readout,
                    "available_at": max(
                        str(row["available_at"]) for row in program_events
                    ),
                    "program_outcome_credit_eligible": False,
                    "security_return_credit_eligible": False,
                    "portfolio_weight": 0.0, "capital_authority": False,
                })
        targets.sort(key=lambda row: (
            not bool(row["admitted_control_classes"]),
            "same_constituents_fragmented" not in row["candidate_control_classes"],
            row["entity_id"], row["program_id"],
        ))
        queued = next((row for row in targets if row.get("work_id") and not row["admitted_control_classes"]), None)
        admitted = [row for row in targets if row["admitted_control_classes"]]
        body = {
            "transfer_card_sha256": card.get("card_sha256"),
            "program_phenotype_sha256": card.get("program_phenotype_sha256"),
            "matched_readout": {
                key: card.get(key) for key in (
                    "metric_id", "unit", "direction", "minimum_effect", "horizon_days",
                    "outcome_role", "acquisition_mode", "source_definition_sha256",
                )
            },
            "candidate_count": len(targets), "admitted_source_control_count": len(admitted),
            "targets": targets, "admitted_source_controls": admitted,
            "permutation_null": {
                "unit": "matched_entity_program_outcome_episode",
                "shuffle": "integrated_vs_control_label_within_environment_and_readout_identity",
                "held_constant": [
                    "control_identity", "metric_id", "unit", "direction",
                    "minimum_effect", "horizon_days", "environment_boundary",
                    "outcome_role", "acquisition_mode", "source_definition_sha256",
                    "same_constituents_or_exact_one_constituent_deletion",
                ],
                "syntax_permutations_excluded": (
                    "combine is associative/commutative and already quotiented by the frontier compiler"
                ),
                "ready": False,
                "blocker": "matched_source_bound_outcomes_not_settled",
            },
            "next_transition": ({
                "transition": "classify_program_control",
                "work_id": queued["work_id"], "request_sha256": queued["request_sha256"],
                "entity_id": queued["entity_id"], "program_id": queued["program_id"],
                "search_end_at": queued["search_end_at"],
            } if queued else None),
            "composition_outcome_comparison_ready": False,
            "one_choice_outcome_comparison_ready": False,
            "causal_program_credit_eligible": False,
            "security_return_credit_eligible": False,
            "portfolio_weight": 0.0, "capital_authority": False,
        }
        cards.append({**body, "acquisition_card_sha256": stable_sha256(body)})
    next_transition = next(
        (row["next_transition"] for row in cards if row.get("next_transition")), None,
    )
    targets = [target for card in cards for target in card["targets"]]
    admitted = [
        target for target in targets if target.get("admitted_control_classes")
    ]
    body = {
        "schema": STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA,
        "generated_at": epoch, "program_transfer_sha256": program_transfer.get("index_sha256"),
        "library_sha256": library.get("library_sha256"),
        "card_count": len(cards),
        "candidate_control_count": len(targets),
        "admitted_source_control_count": len(admitted),
        "admitted_fragmented_control_count": sum(
            "same_constituents_fragmented" in target["admitted_control_classes"]
            for target in admitted
        ),
        "admitted_local_peak_control_count": sum(
            "same_size_local_peak" in target["admitted_control_classes"]
            for target in admitted
        ),
        "admitted_one_choice_base_control_count": sum(
            "one_choice_base_program" in target["admitted_control_classes"]
            for target in admitted
        ),
        "pending_classification_count": sum(
            bool(target.get("work_id")) and not target.get("admitted_control_classes")
            for target in targets
        ),
        "cards": cards, "next_transition": next_transition,
        "boundary": (
            "Source classifications select paper-only comparison units. Operating outcomes must "
            "settle before composition credit; security returns and capital authority remain separate."
        ),
        "causal_program_credit": False, "security_return_credit": False,
        "portfolio_weight": 0.0, "capital_authority": False,
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_PROGRAM_CONTROL_ACQUISITION_SCHEMA", "STRATEGY_TRANSFER_ACQUISITION_SCHEMA",
    "compile_strategy_program_control_acquisition",
    "compile_strategy_transfer_acquisition_policy",
]
