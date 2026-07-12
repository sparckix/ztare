"""Bounded interactive agent loop over the anonymous AxiomPack workbench."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Callable, Mapping

from ztare.common.leaf_workbench_contract import render_leaf_workbench_contract_prompt
from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.common.science_output_policy import INVESTIGATED_STAGNATION_K
from ztare.leanmill import prompts
from ztare.leanmill.axiompack_leaf_workbench import (
    decode_frontier_formula_proposal,
    decode_theory_language_expansion_request,
)
from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    cold_navigator_manifest,
    navigator_selection_mode,
    presentation_size_bounds,
    topology_presentation_size,
    frontier_objective_contract,
)
from ztare.leanmill.exploration_budget import BudgetExceeded
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_campaign_journal import TheoryCampaignEvent, TheoryCampaignJournal
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_program import TheoryProgram, derive_lineage_id
from ztare.validator.core.information_yield import (
    IterationSignal,
    evaluate_information_yield,
)

if TYPE_CHECKING:
    from ztare.leanmill.exploration_budget import ExplorationBudgetLedger


NavigatorAgent = Callable[[str], Mapping[str, Any] | str]

def prompt_trace_max_bytes() -> int:
    """Resolve the navigator trace projection cap from the factory policy."""

    from ztare.leanmill.policy import prompt_transport_policy

    return int(prompt_transport_policy()["navigator_trace_max_bytes"])


def _compact_prompt_value(
    value: Any,
    *,
    depth: int = 0,
    string_limit: int = 640,
    sequence_limit: int = 32,
    mapping_limit: int = 48,
) -> Any:
    """Keep durable receipts useful to the leaf without replaying their bulk.

    The full trace remains on disk and is used for host replay.  This is only
    the prompt projection; it prevents a large formula-profile receipt from
    becoming an ever-growing argv/context payload.
    """

    if isinstance(value, str):
        return value if len(value) <= string_limit else value[:string_limit] + "…"
    # Typed formula IR is nested (profile → formula → body → term → args).
    # Keep that structure available; the byte cap, sequence caps, and oldest
    # trace eviction are the size controls.
    if isinstance(value, Mapping):
        items = list(value.items())
        priority = (
            "decision", "capability_id", "receipt_id", "output_summary",
            "formula_ids", "prediction_formula_ids", "boundary_target_ids",
            "residual_yield", "program_yield", "prediction_profile",
            "rationale", "reason", "claim_boundary",
        )
        rank = {key: index for index, key in enumerate(priority)}
        items.sort(key=lambda pair: (rank.get(str(pair[0]), len(priority)), str(pair[0])))
        kept = items[:mapping_limit]
        result = {
            str(key): _compact_prompt_value(
                item,
                depth=depth + 1,
                string_limit=string_limit,
                sequence_limit=sequence_limit,
                mapping_limit=mapping_limit,
            )
            for key, item in kept
        }
        if len(items) > mapping_limit:
            result["_truncated_fields"] = len(items) - mapping_limit
        return result
    if isinstance(value, (list, tuple)):
        kept = list(value[:sequence_limit])
        result = [
            _compact_prompt_value(
                item,
                depth=depth + 1,
                string_limit=string_limit,
                sequence_limit=sequence_limit,
                mapping_limit=mapping_limit,
            )
            for item in kept
        ]
        if len(value) > sequence_limit:
            result.append({"_truncated_items": len(value) - sequence_limit})
        return result
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:string_limit]


def _prompt_trace_projection(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Project recent trace rows under a fixed byte budget for the leaf prompt."""

    for string_limit, sequence_limit, mapping_limit in (
        (640, 32, 48),
        (360, 20, 32),
        (220, 12, 24),
    ):
        projected = [
            _compact_prompt_value(
                row,
                string_limit=string_limit,
                sequence_limit=sequence_limit,
                mapping_limit=mapping_limit,
            )
            for row in rows
        ]
        while len(projected) > 1 and len(
            json.dumps(projected, sort_keys=True, separators=(",", ":"))
        ) > prompt_trace_max_bytes():
            projected.pop(0)
        if len(json.dumps(projected, sort_keys=True, separators=(",", ":"))) <= prompt_trace_max_bytes():
            return projected
    return projected[-1:] if projected else []


def _parse_decision(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    text = str(value).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("navigator decision must be a JSON object")
    return parsed


def _receipted_reject_all(
    context: TheoryLandscapeContext,
    rejected_candidates: list[dict[str, Any]],
    *,
    reason: str,
) -> dict[str, Any]:
    if not rejected_candidates:
        raise ValueError("reject_all requires a host-receipted candidate rejection")
    for row in rejected_candidates:
        selection_mode = str(row.get("selection_mode") or "compact_axiom_pack")
        residual = row.get("residual_yield")
        if not isinstance(residual, Mapping):
            raise ValueError("reject_all candidate is missing residual-yield coordinates")
        if not str(row.get("selection_receipt_id") or ""):
            raise ValueError("reject_all candidate is missing its selection receipt")
        if not str(residual.get("baseline_ref") or ""):
            raise ValueError("reject_all candidate is missing its named baseline")
        if selection_mode == "compact_axiom_pack":
            if float(residual.get("identification_bits", -1.0)) != 0.0:
                raise ValueError("compact reject_all candidate retains residual information")
            if (
                residual.get("residual_ids")
                or row.get("residual_synergy_formula_ids")
                or row.get("residual_prediction_formula_ids")
            ):
                raise ValueError("compact reject_all candidate retains a residual consequence")
        elif selection_mode == "theory_program":
            profile = row.get("prediction_profile")
            rejection_authority = row.get("rejection_authority")
            agent_refusal = (
                rejection_authority == "anonymous_theory_navigator"
                and bool(str(row.get("refusal_rationale") or "").strip())
            )
            host_counterexample = (
                rejection_authority == "deterministic_host_counterexample"
                and row.get("reason")
                == "theory_program_prediction_refuted_in_context"
            )
            if (
                not (agent_refusal or host_counterexample)
                or not row.get("prediction_formula_ids")
                or not isinstance(profile, Mapping)
                or profile.get("authority") != "host_semantic_diagnostic_only"
            ):
                raise ValueError(
                    "theory-program reject_all requires a receipted refusal or counterexample"
                )
            profile_core = {
                key: value for key, value in profile.items() if key != "receipt_sha256"
            }
            if profile.get("receipt_sha256") != content_hash(profile_core):
                raise ValueError("theory-program rejection profile digest mismatch")
        else:
            raise ValueError("reject_all candidate has an unknown selection mode")
    core = {
        "schema": "leanmill.receipted_reject_all.v2",
        "context_hash": context.context_hash,
        "reason": reason,
        "rejected_candidates": rejected_candidates,
        "rejected_candidate_count": len(rejected_candidates),
        "stagnation_k": INVESTIGATED_STAGNATION_K,
        "authority": "deterministic_host",
    }
    return {**core, "receipt_id": "reject-all:" + content_hash(core)}


def _invalid_capability_action_receipt(
    context: TheoryLandscapeContext,
    capability_id: str,
    inputs: Mapping[str, Any],
    error: Exception,
) -> dict[str, Any]:
    """Turn a malformed model action into a replayable host receipt.

    Capability handlers are deterministic host code, but their inputs are model
    authored.  Input-shaped ``KeyError``/``TypeError``/``ValueError`` failures
    therefore belong at the receipt boundary, not at the campaign process
    boundary.  Unexpected exceptions are deliberately not routed here.
    """

    core = {
        "schema": "leanmill.axiompack_invalid_action_receipt.v1",
        "capability_id": capability_id,
        "context_hash": context.context_hash,
        "input_hashes": {
            key: "sha256:" + content_hash(value)
            for key, value in sorted(inputs.items())
        },
        "output_summary": {
            "status": "rejected_invalid_action",
            "error_code": "host_input_validation_failed",
            "error": str(error),
            "claim_boundary": (
                "malformed model action rejected by the host; the context is "
                "unchanged and no semantic or promotion claim is made"
            ),
        },
        "claim_bindings": [capability_id],
        "authority": "deterministic_host",
    }
    return {**core, "receipt_id": "sha256:" + content_hash(core)}


def reject_all_sequence_receipt(
    receipts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind consecutive receipted no-candidate campaign outcomes."""

    if not receipts:
        count = 0
        context_hash = ""
        receipt_ids: list[str] = []
    else:
        context_hash = str(receipts[0].get("context_hash") or "")
        receipt_ids = []
        for receipt in receipts:
            if receipt.get("schema") not in {
                "leanmill.receipted_reject_all.v1",
                "leanmill.receipted_reject_all.v2",
            }:
                raise ValueError("reject-all sequence contains an invalid receipt schema")
            if str(receipt.get("context_hash") or "") != context_hash:
                raise ValueError("reject-all sequence crosses frozen contexts")
            receipt_id = str(receipt.get("receipt_id") or "")
            if not receipt_id:
                raise ValueError("reject-all sequence contains an unreceipted outcome")
            receipt_ids.append(receipt_id)
        count = len(receipt_ids)
    core = {
        "schema": "leanmill.reject_all_sequence.v1",
        "context_hash": context_hash,
        "reject_all_receipt_ids": receipt_ids,
        "consecutive_reject_all_count": count,
        "stagnation_k": INVESTIGATED_STAGNATION_K,
        "stagnation_pressure": count >= INVESTIGATED_STAGNATION_K,
        "authority": "deterministic_host",
    }
    return {**core, "receipt_id": "reject-all-sequence:" + content_hash(core)}


def run_interactive_theory_navigator(
    context: TheoryLandscapeContext,
    blueprint: FrontierTheoryBlueprint,
    journal: TheoryCampaignJournal,
    *,
    agent_fn: NavigatorAgent,
    attempt_id: str,
    campaign_id: str,
    max_rounds: int = 24,
    max_finalists: int = 8,
    budget_ledger: "ExplorationBudgetLedger | None" = None,
    initial_trace: tuple[Mapping[str, Any], ...] = (),
    prior_agent_turns: int = 0,
    round_offset: int = 0,
    epoch: int = 0,
    lineage_id: str = "",
    prior_conflict_rows: tuple[Mapping[str, Any], ...] = (),
    replay_decisions: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    if max_rounds < 1 or max_finalists < 1:
        raise ValueError("navigator budgets must be positive")
    selection_mode = navigator_selection_mode(blueprint)
    active_lineage_id = (
        str(lineage_id).strip()
        or derive_lineage_id(campaign_id=campaign_id, attempt_id=attempt_id)
    )
    environment = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        context_epoch=epoch,
        selection_mode=selection_mode,
        max_presentation_size=blueprint.pack_arity,
        topology_presentation_size=topology_presentation_size(blueprint),
    )
    handlers = environment["action_handlers"]
    if prior_agent_turns < 0 or round_offset < 0:
        raise ValueError("navigator recovery counters must be nonnegative")
    if round_offset + len(replay_decisions) > max_rounds:
        raise ValueError("durable replay exceeds the navigator horizon")
    trace: list[dict[str, Any]] = [dict(row) for row in initial_trace]
    allowed_conflict_fields = {
        "candidate_signature",
        "context_hash",
        "witness_ref",
        "witness_summary",
        "conflict_kind",
    }
    conflict_rows: list[dict[str, Any]] = []
    for row in prior_conflict_rows:
        if (
            not isinstance(row, Mapping)
            or not set(row) <= allowed_conflict_fields
            or row.get("context_hash") != context.context_hash
        ):
            raise ValueError("navigator conflict memory is malformed or belongs to another context")
        conflict_rows.append(dict(row))
    finalists: list[dict[str, Any]] = []
    frozen_candidate_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    considered_candidate_keys: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    candidate_rejections: list[dict[str, Any]] = []
    seen_output_digests: set[str] = set()
    yield_history: list[IterationSignal] = []
    expansion_proposal: dict[str, Any] | None = None
    language_expansion_request: dict[str, Any] | None = None
    agent_turns_used = prior_agent_turns
    low_yield_threshold_ppm = (
        budget_ledger.budget.stop_rule.min_marginal_information_per_cost_ppm
        if budget_ledger is not None
        else 0
    )
    cold = cold_navigator_manifest(blueprint)
    minimum_presentation_size, maximum_presentation_size = presentation_size_bounds(
        blueprint
    )
    contract_text = render_leaf_workbench_contract_prompt(environment["contract"])

    for round_index in range(round_offset, max_rounds):
        replay_index = round_index - round_offset
        replaying = replay_index < len(replay_decisions)
        if budget_ledger is not None and not replaying:
            soft_stop = budget_ledger.soft_stop_reason(
                allow_coverage_target=frontier_objective_contract(blueprint) is None
            )
            if soft_stop is not None:
                if finalists or candidate_rejections:
                    trace.append(
                        {"round": round_index, "decision": "budget_stop", "reason": soft_stop}
                    )
                    break
                if trace and trace[-1].get("decision") == "request":
                    break
                raise BudgetExceeded(soft_stop)
        visible_trace_rows = list(trace[-12:])
        if conflict_rows:
            visible_trace_rows = visible_trace_rows[-11:] + [
                {
                    "decision": "prior_witnessed_conflict_memory",
                    "conflicts": conflict_rows,
                    "authority": "host_witness_replay",
                    "instruction": "avoid exact repeats; the host will replay every claimed block",
                }
            ]
        visible_trace = _prompt_trace_projection(visible_trace_rows)
        prompt_values = {
            "cold_manifest_json": json.dumps(cold, sort_keys=True, separators=(",", ":")),
            "workbench_contract": contract_text,
            "trace_json": json.dumps(visible_trace, sort_keys=True, separators=(",", ":")),
            "budget_state_json": json.dumps(
                {
                    "navigation_provider_calls_remaining": (
                        budget_ledger.remaining_capacity("navigation", "provider_calls")
                        if budget_ledger is not None
                        else max(0, max_rounds - round_index)
                    ),
                    "navigation_agent_turns_remaining": (
                        budget_ledger.remaining_capacity("navigation", "agent_turns")
                        if budget_ledger is not None
                        else max(0, max_rounds - round_index)
                    ),
                    "rounds_remaining": max(0, max_rounds - round_index),
                    "context_epoch": epoch,
                    "context_hash": context.context_hash,
                    "preview_is_not_freeze": True,
                    "low_yield_information_per_cost_threshold": (
                        low_yield_threshold_ppm / 1_000_000
                    ),
                    "low_yield_patience": (
                        budget_ledger.budget.stop_rule.low_yield_patience
                        if budget_ledger is not None
                        else 0
                    ),
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
        prompt = prompts.AXIOMPACK_THEORY_NAVIGATOR_PROMPT.format(**prompt_values)
        legacy_prompt = prompts.AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V1.format(
            **prompt_values
        )
        residual_prompt = prompts.AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V2.format(
            **prompt_values
        )
        profile_refinement_prompt = (
            prompts.AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V3.format(**prompt_values)
        )
        contrast_prompt = prompts.AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V4.format(
            **prompt_values
        )
        successor_prompt = prompts.AXIOMPACK_THEORY_NAVIGATOR_PROMPT_V5.format(
            **prompt_values
        )
        turn_reservation = None
        role = getattr(agent_fn, "call_role", None)
        if role is None and hasattr(agent_fn, "call_count"):
            role = agent_fn
        before_calls = getattr(
            role, "provider_call_count", getattr(role, "call_count", None)
        )
        if budget_ledger is not None and not replaying:
            try:
                turn_reservation = budget_ledger.reserve(
                    f"navigator:{round_index}:agent_turn",
                    "navigation",
                    {"provider_calls": 1, "agent_turns": 1},
                )
            except BudgetExceeded as exc:
                if not finalists and not candidate_rejections:
                    if trace and trace[-1].get("decision") == "request":
                        break
                    raise
                trace.append(
                    {
                        "round": round_index,
                        "decision": "budget_stop",
                        "reason": exc.reason,
                    }
                )
                break
        try:
            if replaying:
                raw_decision = replay_decisions[replay_index]
            else:
                compatible_call = getattr(
                    agent_fn, "call_with_compatible_prompts", None
                )
                raw_decision = (
                    compatible_call(
                        prompt,
                        (
                            successor_prompt,
                            contrast_prompt,
                            profile_refinement_prompt,
                            residual_prompt,
                            legacy_prompt,
                        ),
                    )
                    if callable(compatible_call)
                    else agent_fn(prompt)
                )
            decision = _parse_decision(raw_decision)
            agent_turns_used += 1
        finally:
            if turn_reservation is not None:
                after_calls = getattr(
                    role, "provider_call_count", getattr(role, "call_count", None)
                )
                used = (
                    1
                    if before_calls is None or after_calls is None
                    else max(0, min(1, int(after_calls) - int(before_calls)))
                )
                budget_ledger.commit(
                    turn_reservation,
                    {"provider_calls": used, "agent_turns": used},
                )
        kind = str(decision.get("decision") or "")
        rationale = str(decision.get("rationale") or "").strip()
        if not rationale:
            raise ValueError("navigator decision requires rationale")
        if kind == "request":
            capability_ref = str(decision.get("capability_id") or "")
            capability_id = environment["contract"].resolve_capability_ref(
                capability_ref
            )
            if capability_id not in handlers:
                raise ValueError(
                    f"navigator requested unavailable capability: {capability_ref!r}"
                )
            inputs = decision.get("input_refs")
            if not isinstance(inputs, dict):
                raise ValueError("navigator action input_refs must be an object")
            action_reservation = None
            if budget_ledger is not None:
                action_reservation = budget_ledger.reserve(
                    f"navigator:{round_index}:{capability_id}",
                    "navigation",
                    {"workbench_actions": 1},
                )
            try:
                try:
                    receipt = handlers[capability_id](
                        ".", {"input_refs": inputs}, None, environment["contract"]
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    receipt = _invalid_capability_action_receipt(
                        context, capability_id, inputs, exc
                    )
            finally:
                if action_reservation is not None:
                    budget_ledger.commit(action_reservation)
            output_digest = content_hash(receipt.get("output_summary"))
            is_new = output_digest not in seen_output_digests
            seen_output_digests.add(output_digest)
            yield_history.append(
                IterationSignal(
                    iteration_index=round_index,
                    score=len(seen_output_digests),
                    score_improved=is_new,
                    weakest_point=capability_id,
                    novel_hinge_ids=(output_digest,) if is_new else (),
                )
            )
            patience = (
                budget_ledger.budget.stop_rule.low_yield_patience
                if budget_ledger is not None else 3
            )
            loop_control = evaluate_information_yield(
                yield_history,
                refresh_after=max(1, patience - 1),
                pivot_after=patience,
                underidentified_after=patience,
            )
            trace.append(
                {
                    "round": round_index,
                    "decision": "request",
                    "capability_id": capability_id,
                    "rationale": rationale,
                    "loop_control": {
                        "action": loop_control.action.value,
                        "stagnant_window": loop_control.stagnant_window,
                        "rationale": loop_control.rationale,
                    },
                    "receipt": receipt,
                }
            )
            journal.append(
                TheoryCampaignEvent(
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=epoch,
                    context_hash=context.context_hash,
                    event_type="navigator_action_executed",
                    subject_ids=(str(receipt["receipt_id"]),),
                    input_refs=(capability_id,),
                    evidence_status="witnessed",
                    authority="deterministic_workbench_executor",
                )
            )
            if capability_id == "propose_frontier_formula":
                summary = receipt.get("output_summary") or {}
                if summary.get("status") == "proposed_new_formula":
                    proposal = decode_frontier_formula_proposal(context, inputs)
                    epoch_request = {
                        "schema": "leanmill.frontier_formula_epoch_request.v1",
                        "source_context_hash": context.context_hash,
                        "source_epoch": epoch,
                        "workbench_receipt_id": str(receipt["receipt_id"]),
                        "typed_axiom_proposal": proposal.to_json(),
                        "typed_proposal_sha256": proposal.content_hash,
                        "formula_id": str(summary["formula_id"]),
                        "contrast_refinement": summary.get(
                            "semantic_profile_new_witness"
                        ),
                        "navigator_rationale": rationale,
                    }
                    expansion_proposal = epoch_request
                    break
            if capability_id == "propose_theory_language_expansion":
                summary = receipt.get("output_summary") or {}
                if summary.get("status") != "outbound_blueprint_request":
                    continue
                request = decode_theory_language_expansion_request(
                    context, inputs, source_epoch=epoch
                )
                if summary.get("request_id") != request.request_id:
                    raise ValueError("theory-language request changed after host receipt")
                language_expansion_request = request.to_json()
                break
            continue
        if kind in {"freeze", "reject_candidate"}:
            formulas_raw = decision.get("formula_ids")
            if not isinstance(formulas_raw, list):
                raise ValueError(f"{kind} requires formula_ids")
            formulas = tuple(sorted(str(row) for row in formulas_raw))
            if len(set(formulas)) != len(formulas):
                raise ValueError("candidate presentation formula IDs must be unique")
            if not minimum_presentation_size <= len(formulas) <= maximum_presentation_size:
                raise ValueError("frozen presentation violates campaign presentation size")
            boundary_targets_raw = decision.get("boundary_target_ids")
            if selection_mode == "theory_program":
                if not isinstance(boundary_targets_raw, list) or not boundary_targets_raw:
                    raise ValueError(
                        "theory-program candidates require explicit prediction formula IDs"
                    )
                boundary_target_ids = tuple(str(row) for row in boundary_targets_raw)
                if len(set(boundary_target_ids)) != len(boundary_target_ids):
                    raise ValueError("theory-program prediction IDs must be unique")
                if set(boundary_target_ids) & set(formulas):
                    raise ValueError(
                        "theory-program predictions must be outside its presentation"
                    )
                unknown_predictions = set(boundary_target_ids) - set(context.formula_ids)
                if unknown_predictions:
                    raise ValueError(
                        "theory-program predictions contain unknown formula IDs"
                    )
                selection_inputs = {
                    "formula_ids": list(formulas),
                    "prediction_formula_ids": list(boundary_target_ids),
                }
                boundary_selection_authority = "anonymous_theory_navigator"
            else:
                if kind == "reject_candidate":
                    raise ValueError(
                        "reject_candidate is reserved for open theory-program judgments"
                    )
                boundary_target_ids = ()
                selection_inputs = {"formula_ids": list(formulas)}
                boundary_selection_authority = ""
            candidate_key = (
                formulas,
                boundary_target_ids if selection_mode == "theory_program" else (),
            )
            if candidate_key in frozen_candidate_keys:
                raise ValueError("navigator repeated a frozen candidate")
            if candidate_key in considered_candidate_keys:
                raise ValueError("navigator repeated a previously considered candidate")
            considered_candidate_keys.add(candidate_key)
            selection_reservation = None
            if budget_ledger is not None:
                selection_reservation = budget_ledger.reserve(
                    f"navigator:{round_index}:select_theory_presentation",
                    "navigation",
                    {"workbench_actions": 1},
                )
            try:
                selection = handlers["select_theory_presentation"](
                    ".", {"input_refs": selection_inputs}, None, environment["contract"]
                )
            finally:
                if selection_reservation is not None:
                    budget_ledger.commit(selection_reservation)
            summary = selection["output_summary"]
            synergy = tuple(str(row) for row in summary.get("synergy_formula_ids") or ())
            pack_residual_ids = tuple(
                str(row) for row in summary.get("residual_synergy_formula_ids") or ()
            )
            program_yield = dict(summary.get("program_yield") or {})
            if selection_mode == "theory_program":
                residual_ids = tuple(
                    str(row)
                    for row in summary.get("residual_prediction_formula_ids") or ()
                )
                baseline_inconclusive_ids = tuple(
                    str(row)
                    for row in program_yield.get("cheap_baseline_inconclusive_ids") or ()
                )
                residual_yield = dict(program_yield.get("coordinates") or {})
            else:
                residual_ids = pack_residual_ids
                baseline_inconclusive_ids = tuple(
                    str(row)
                    for row in summary.get("cheap_baseline_inconclusive_ids") or ()
                )
                residual_yield = dict(summary.get("residual_yield") or {})
            prediction_profile = summary.get("prediction_profile")
            if selection_mode == "theory_program":
                if not isinstance(prediction_profile, Mapping):
                    raise ValueError("theory-program selection lacks a prediction profile")
            elif boundary_targets_raw is None:
                boundary_target_ids = residual_ids
                boundary_selection_authority = "compatibility_default_all_residuals"
            else:
                if not isinstance(boundary_targets_raw, list) or not boundary_targets_raw:
                    raise ValueError("freeze boundary_target_ids must be a nonempty list")
                boundary_target_ids = tuple(str(row) for row in boundary_targets_raw)
                if len(set(boundary_target_ids)) != len(boundary_target_ids):
                    raise ValueError("freeze boundary_target_ids must not contain duplicates")
                if any(row not in residual_ids for row in boundary_target_ids):
                    raise ValueError(
                        "compact-pack boundary targets must be residual consequences"
                    )
                boundary_selection_authority = "anonymous_theory_navigator"
            information_per_cost_ppm = max(
                0,
                min(
                    1_000_000,
                    round(
                        float(residual_yield.get("information_per_cost", 0.0))
                        * 1_000_000
                    ),
                ),
            )
            rejection_reason = None
            if selection_mode == "compact_axiom_pack":
                if summary.get("independent") is not True:
                    rejection_reason = "presentation_not_independent"
                elif int(summary.get("extent_size", 0)) < 2:
                    rejection_reason = "extent_not_robust"
                elif len(formulas) > 1 and not synergy:
                    rejection_reason = "no_joint_only_consequence"
                elif not residual_ids and baseline_inconclusive_ids:
                    rejection_reason = "cheap_baseline_inconclusive"
                elif not residual_ids:
                    rejection_reason = "cheap_baseline_exhausts_joint_consequences"
                elif float(residual_yield.get("identification_bits", 0.0)) <= 0:
                    rejection_reason = "zero_residual_information"
            elif kind == "freeze" and isinstance(prediction_profile, Mapping) and any(
                row.get("chart_status")
                in {"refuted_in_context", "vacuous_on_empty_extent"}
                for row in prediction_profile.get("predictions") or ()
                if isinstance(row, Mapping)
            ):
                rejection_reason = "theory_program_prediction_refuted_in_context"
            if rejection_reason is not None:
                rejected = {
                    "formula_ids": list(formulas),
                    "selection_mode": selection_mode,
                    "node_id": summary["node_id"],
                    "reason": rejection_reason,
                    "selection_receipt_id": selection["receipt_id"],
                    "residual_yield": residual_yield,
                    "cheap_baseline_formula_ids": list(
                        summary.get("cheap_baseline_formula_ids") or ()
                    ),
                    "cheap_baseline_inconclusive_ids": list(
                        baseline_inconclusive_ids
                    ),
                    "cheap_baseline_inconclusive_receipts": dict(
                        summary.get("cheap_baseline_inconclusive_receipts") or {}
                    ),
                    "structural_baseline": summary.get("structural_baseline"),
                    "prediction_profile": (
                        dict(prediction_profile)
                        if isinstance(prediction_profile, Mapping)
                        else None
                    ),
                    "prediction_formula_ids": list(boundary_target_ids),
                    "rejection_authority": "deterministic_host_counterexample",
                    "residual_synergy_formula_ids": list(residual_ids),
                    "residual_prediction_formula_ids": list(residual_ids),
                }
                trace.append(
                    {
                        "round": round_index,
                        "decision": "candidate_rejected",
                        "rationale": rationale,
                        "rejection": rejected,
                        "stagnation_pressure": (
                            rejection_reason
                            in {
                                "cheap_baseline_exhausts_joint_consequences",
                                "cheap_baseline_exhausts_predictions",
                                "zero_residual_information",
                                "theory_program_prediction_refuted_in_context",
                            }
                            and len(candidate_rejections) + 1
                            >= INVESTIGATED_STAGNATION_K
                        ),
                    }
                )
                journal.append(
                    TheoryCampaignEvent(
                        attempt_id=attempt_id,
                        campaign_id=campaign_id,
                        epoch=epoch,
                        context_hash=context.context_hash,
                        event_type="theory_presentation_rejected",
                        subject_ids=(str(summary["node_id"]),),
                        input_refs=formulas,
                        output_refs=(str(selection["receipt_id"]),),
                        evidence_status="witnessed",
                        authority="deterministic_workbench_executor",
                    )
                )
                if rejection_reason in {
                    "cheap_baseline_exhausts_joint_consequences",
                    "cheap_baseline_exhausts_predictions",
                    "zero_residual_information",
                    "theory_program_prediction_refuted_in_context",
                }:
                    candidate_rejections.append(rejected)
                if budget_ledger is not None:
                    budget_ledger.observe_information(
                        action_id=f"navigator:{round_index}:candidate_rejected",
                        marginal_information_per_cost_ppm=information_per_cost_ppm,
                        coverage_ppm=0,
                        evidence_refs=(
                            str(selection["receipt_id"]),
                            str(summary["node_id"]),
                        ),
                    )
                continue
            if kind == "reject_candidate":
                rejected = {
                    "formula_ids": list(formulas),
                    "prediction_formula_ids": list(boundary_target_ids),
                    "selection_mode": selection_mode,
                    "node_id": summary["node_id"],
                    "reason": "agent_refused_theory_program",
                    "refusal_rationale": rationale,
                    "rejection_authority": "anonymous_theory_navigator",
                    "selection_receipt_id": selection["receipt_id"],
                    "prediction_profile": dict(prediction_profile),
                    "residual_yield": residual_yield,
                    "cheap_baseline_formula_ids": list(
                        summary.get("cheap_baseline_formula_ids") or ()
                    ),
                    "cheap_baseline_inconclusive_ids": list(
                        baseline_inconclusive_ids
                    ),
                    "cheap_baseline_inconclusive_receipts": dict(
                        summary.get("cheap_baseline_inconclusive_receipts") or {}
                    ),
                    "structural_baseline": summary.get("structural_baseline"),
                    "residual_synergy_formula_ids": list(pack_residual_ids),
                    "residual_prediction_formula_ids": list(residual_ids),
                }
                candidate_rejections.append(rejected)
                trace.append(
                    {
                        "round": round_index,
                        "decision": "candidate_rejected",
                        "rationale": rationale,
                        "rejection": rejected,
                        "stagnation_pressure": (
                            len(candidate_rejections) >= INVESTIGATED_STAGNATION_K
                        ),
                    }
                )
                journal.append(
                    TheoryCampaignEvent(
                        attempt_id=attempt_id,
                        campaign_id=campaign_id,
                        epoch=epoch,
                        context_hash=context.context_hash,
                        event_type="theory_program_refused",
                        subject_ids=(str(summary["node_id"]), *boundary_target_ids),
                        input_refs=formulas,
                        output_refs=(str(selection["receipt_id"]),),
                        evidence_status="witnessed",
                        authority="anonymous_theory_navigator",
                    )
                )
                if budget_ledger is not None:
                    budget_ledger.observe_information(
                        action_id=f"navigator:{round_index}:candidate_refused",
                        marginal_information_per_cost_ppm=information_per_cost_ppm,
                        coverage_ppm=0,
                        evidence_refs=(
                            str(selection["receipt_id"]),
                            str(summary["node_id"]),
                        ),
                    )
                continue
            finalist = {
                "node_id": summary["node_id"],
                "candidate_kind": selection_mode,
                "context_hash": context.context_hash,
                "context_epoch": epoch,
                "formula_ids": list(formulas),
                "joint_only_consequence_ids": list(synergy),
                "cheap_baseline_consequence_ids": list(
                    summary.get("cheap_baseline_formula_ids") or ()
                ),
                "residual_joint_only_consequence_ids": list(pack_residual_ids),
                "consequence_formula_ids": list(
                    summary.get("consequence_formula_ids") or ()
                ),
                "residual_prediction_formula_ids": list(
                    summary.get("residual_prediction_formula_ids") or ()
                ),
                "boundary_target_ids": list(boundary_target_ids),
                "boundary_selection_authority": boundary_selection_authority,
                "prediction_profile": (
                    dict(prediction_profile)
                    if isinstance(prediction_profile, Mapping)
                    else None
                ),
                "residual_information_yield": residual_yield,
                "cheap_baseline_inconclusive_ids": list(
                    baseline_inconclusive_ids
                ),
                "cheap_baseline_inconclusive_receipts": dict(
                    summary.get("cheap_baseline_inconclusive_receipts") or {}
                ),
                "structural_baseline": summary.get("structural_baseline"),
                "extent_size": summary["extent_size"],
                "closure_size": summary["closure_size"],
                "navigator_rationale": rationale,
                "selection_receipt_id": selection["receipt_id"],
            }
            if selection_mode == "theory_program":
                program = TheoryProgram(
                    campaign_id=campaign_id,
                    lineage_id=active_lineage_id,
                    context_hash=context.context_hash,
                    context_epoch=epoch,
                    presentation_formula_ids=formulas,
                    prediction_formula_ids=boundary_target_ids,
                    selection_receipt_id=str(selection["receipt_id"]),
                )
                finalist["theory_program"] = program.to_json()
                finalist["theory_program_id"] = program.program_id
            finalists.append(finalist)
            if budget_ledger is not None:
                budget_ledger.observe_information(
                    action_id=f"navigator:{round_index}:freeze",
                    marginal_information_per_cost_ppm=information_per_cost_ppm,
                    coverage_ppm=min(1_000_000, len(finalists) * 1_000_000 // max_finalists),
                    evidence_refs=(str(selection["receipt_id"]), str(summary["node_id"])),
                )
            frozen_candidate_keys.add(candidate_key)
            trace.append({"round": round_index, "decision": "freeze", "finalist": finalist})
            journal.append(
                TheoryCampaignEvent(
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=epoch,
                    context_hash=context.context_hash,
                    event_type="finalist_frozen",
                    subject_ids=(str(summary["node_id"]),)
                    + (
                        (str(finalist["theory_program_id"]),)
                        if finalist.get("theory_program_id")
                        else ()
                    ),
                    input_refs=formulas,
                    output_refs=(str(selection["receipt_id"]),),
                    evidence_status="frozen",
                    authority="anonymous_theory_navigator",
                )
            )
            if len(finalists) >= max_finalists:
                break
            continue
        if kind == "finish":
            if not finalists:
                trace.append(
                    {
                        "round": round_index,
                        "decision": "finish_rejected",
                        "rationale": rationale,
                        "reason": (
                            "no finalist is frozen; a presentation preview is not a "
                            "freeze—return decision=freeze or a receipted reject_all"
                        ),
                    }
                )
                continue
            trace.append({"round": round_index, "decision": "finish", "rationale": rationale})
            break
        if kind == "reject_all":
            if finalists:
                raise ValueError("reject_all is only valid when no finalist was frozen")
            if not candidate_rejections:
                trace.append(
                    {
                        "round": round_index,
                        "decision": "reject_all_rejected",
                        "rationale": rationale,
                        "reason": (
                            "reject_all requires at least one host-receipted candidate "
                            "rejection or theory-program refusal"
                        ),
                    }
                )
                continue
            receipt = _receipted_reject_all(
                context,
                candidate_rejections,
                reason="navigator_rejected_all_host_visible_candidates",
            )
            trace.append(
                {
                    "round": round_index,
                    "decision": "reject_all",
                    "rationale": rationale,
                    "receipt": receipt,
                }
            )
            journal.append(
                TheoryCampaignEvent(
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=epoch,
                    context_hash=context.context_hash,
                    event_type="navigator_reject_all",
                    subject_ids=tuple(
                        str(row["node_id"]) for row in candidate_rejections
                    ),
                    input_refs=tuple(
                        str(row["selection_receipt_id"])
                        for row in candidate_rejections
                    ),
                    output_refs=(str(receipt["receipt_id"]),),
                    evidence_status="witnessed",
                    authority="deterministic_workbench_executor",
                )
            )
            break
        raise ValueError(f"unknown navigator decision: {kind!r}")
    if expansion_proposal is not None and not finalists:
        return {
            "schema": "leanmill.interactive_theory_navigator.v1",
            "context_hash": context.context_hash,
            "context_epoch": epoch,
            "finalist_node_ids": [],
            "finalists": [],
            "trace": trace,
            "expansion_proposal": expansion_proposal,
            "provider_calls": agent_turns_used,
            "prior_conflict_count": len(conflict_rows),
            "cold_view": True,
        }
    if language_expansion_request is not None and not finalists:
        return {
            "schema": "leanmill.interactive_theory_navigator.v1",
            "context_hash": context.context_hash,
            "context_epoch": epoch,
            "finalist_node_ids": [],
            "finalists": [],
            "trace": trace,
            "language_expansion_request": language_expansion_request,
            "provider_calls": agent_turns_used,
            "prior_conflict_count": len(conflict_rows),
            "cold_view": True,
        }
    if not finalists:
        last_decision = trace[-1] if trace else {}
        if last_decision.get("decision") == "request":
            receipt = last_decision.get("receipt") or {}
            pending_core = {
                "schema": "leanmill.pending_leaf_decision.v1",
                "context_hash": context.context_hash,
                "context_epoch": epoch,
                "lineage_id": active_lineage_id,
                "capability_id": str(
                    last_decision.get("capability_id")
                    or receipt.get("capability_id")
                    or ""
                ),
                "receipt_id": str(receipt.get("receipt_id") or ""),
                "reason": "host_action_completed_after_leaf_turn",
                "claim_boundary": (
                    "the host receipt still requires the requesting leaf's "
                    "accept, reject, or next-move decision"
                ),
                "authority": "host_lifecycle_receipt",
            }
            pending = {
                **pending_core,
                "receipt_sha256": content_hash(pending_core),
            }
            trace.append(
                {
                    "decision": "pending_leaf_decision",
                    "receipt": pending,
                    "host_finalized": True,
                }
            )
            return {
                "schema": "leanmill.interactive_theory_navigator.v1",
                "context_hash": context.context_hash,
                "context_epoch": epoch,
                "finalist_node_ids": [],
                "finalists": [],
                "trace": trace,
                "pending_leaf_decision": pending,
                "provider_calls": agent_turns_used,
                "prior_conflict_count": len(conflict_rows),
                "cold_view": True,
            }
        explicit = next(
            (row["receipt"] for row in reversed(trace) if row["decision"] == "reject_all"),
            None,
        )
        if explicit is None and candidate_rejections:
            explicit = _receipted_reject_all(
                context,
                candidate_rejections,
                reason="navigator_budget_or_round_limit_after_receipted_rejections",
            )
            trace.append({"decision": "reject_all", "receipt": explicit, "host_finalized": True})
        if explicit is None:
            exhaustion_core = {
                "schema": "leanmill.navigation_exhausted.v1",
                "context_hash": context.context_hash,
                "context_epoch": epoch,
                "agent_turns_used": agent_turns_used,
                "reason": "round_or_soft_horizon_without_frozen_or_refused_candidate",
                "claim_boundary": (
                    "budget exhaustion records no scientific rejection and no candidate authority"
                ),
                "authority": "host_lifecycle_receipt",
            }
            exhaustion = {
                **exhaustion_core,
                "receipt_sha256": content_hash(exhaustion_core),
            }
            trace.append(
                {
                    "decision": "navigation_exhausted",
                    "receipt": exhaustion,
                    "host_finalized": True,
                }
            )
            return {
                "schema": "leanmill.interactive_theory_navigator.v1",
                "context_hash": context.context_hash,
                "context_epoch": epoch,
                "finalist_node_ids": [],
                "finalists": [],
                "trace": trace,
                "navigation_exhausted_receipt": exhaustion,
                "provider_calls": agent_turns_used,
                "prior_conflict_count": len(conflict_rows),
                "cold_view": True,
            }
        sequence = reject_all_sequence_receipt([explicit])
        return {
            "schema": "leanmill.interactive_theory_navigator.v1",
            "context_hash": context.context_hash,
            "context_epoch": epoch,
            "finalist_node_ids": [],
            "finalists": [],
            "trace": trace,
            "reject_all_receipt": explicit,
            "reject_all_sequence_receipt": sequence,
            "stagnation_pressure": bool(sequence["stagnation_pressure"]),
            "provider_calls": agent_turns_used,
            "prior_conflict_count": len(conflict_rows),
            "cold_view": True,
        }
    result = {
        "schema": "leanmill.interactive_theory_navigator.v1",
        "context_hash": context.context_hash,
        "context_epoch": epoch,
        "finalist_node_ids": [row["node_id"] for row in finalists],
        "finalists": finalists,
        "trace": trace,
        "provider_calls": agent_turns_used,
        "prior_conflict_count": len(conflict_rows),
        "cold_view": True,
    }
    if expansion_proposal is not None:
        result["expansion_proposal"] = expansion_proposal
    if language_expansion_request is not None:
        result["language_expansion_request"] = language_expansion_request
    if selection_mode == "theory_program":
        result["lineage_id"] = active_lineage_id
    return result


__all__ = ["reject_all_sequence_receipt", "run_interactive_theory_navigator"]
