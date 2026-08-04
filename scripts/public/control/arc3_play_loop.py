#!/usr/bin/env python3
"""GP-250 "beat" engine: governed identification × planner exploitation, live.

The kernel-first self-improvement loop (NO Frankenstein re-identifier — the
governed `experiment-loop` IS the identifier, with its stagnation-pivot
reconception, judge, and hard gates; this driver only alternates it with
live play and grows the evidence):

  cycle:
    1. run the governed loop on the current episode log -> a ratified model
       (or, on stagnation, a structurally-pivoted reconception of it)
    2. load the ratified model, PLAY the live game under it (novelty / goal-cue
       steering), stopping on an adapter-authority task-discharge receipt
    3. LEVEL? report the win. else append the off-basin transitions the live
       game produced (the model was never fit on them) to the episode log,
       re-render evidence, reseal — the next governed cycle re-identifies on the
       richer evidence, and its pivot machinery reconceives if it stalls.

Reuses: experiment-loop (subprocess, sealed subscription workers), the
worldmodel gates/planner, the arc_agi3 adapter. Spends subscription tokens for
the governed cycles. Usage:
    python3 scripts/public/control/arc3_play_loop.py --game ls20 --cycles 4
    python3 scripts/public/control/arc3_play_loop.py --game ls20 --mode competition
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from ztare.common.phase_timing import phase  # noqa: E402
from ztare.common.worldmodel_carrier_purity import (  # noqa: E402
    project_dynamics_assumption,
    validate_worldmodel_carrier_source,
)
from ztare.substrates.arc_agi3 import ArcAgi3Adapter  # noqa: E402
from ztare.worldmodel.adapter import (  # noqa: E402
    admit_observations as _append_observations,
    episode_log_path,
    grow_evidence as _grow_evidence,
    observation_log as _observation_log,
)
from ztare.worldmodel.episode_log import EpisodeLog, Transition  # noqa: E402
from ztare.worldmodel.carrier_loader import load_carrier_from_source  # noqa: E402
from ztare.worldmodel.level_boundary_seed import (  # noqa: E402
    replay_latest_seed as _replay_latest_level_boundary_seed,
    replay_latest_seed_trace as _replay_latest_level_boundary_seed_trace,
)
from ztare.worldmodel.planner import pursue_goal  # noqa: E402
from ztare.worldmodel.residual_repair import (  # noqa: E402
    reject_satisfied_seed_prerequisite_cards,
)


_ADVICE_MODES = {"advice", "competition", "compiled", "advice_consume"}
_FRONTIER_SCOPE_SCHEMA = "ztare-frontier-memory-scope-v1"
_FRONTIER_ABSTRACTION_VERSION = "arc3-component-orbit-frontier-v3"


def _game_prefix(game: str) -> str:
    return str(game or "").split("-", 1)[0]


def _resolve_game_id(game: str) -> str | None:
    game = str(game or "").strip()
    if "-" in game:
        return game
    from ztare.substrates.arc_agi3 import list_games
    return next((g for g in list_games() if g.startswith(game)), None)


def _normalize_play_mode(mode) -> "tuple[str, str]":
    alias = str(mode or "governed").strip().lower().replace("-", "_")
    return ("advice" if alias in _ADVICE_MODES else alias), alias


def _play_config(project: Path) -> dict:
    """Driver scheduling config (NOT research config — the rubric stays sealed):
    mode governed|sprint|hybrid|advice, sprint/checkpoint budgets. Missing file =
    prior behavior (governed).

    `advice` is the competition-time shape: consume the compiled advice string
    (persisted specs/candidates + deterministic abduction) and never launch the
    governed subscription-worker loop. Research happens before this mode, not
    inside it.
    """
    import json as _j
    path = project / "play_config.json"
    cfg = {"mode": "governed", "sprint_steps": 1500, "sprint_rounds": 6,
           "governed_checkpoint_every": 3, "governed_iters": 3,
           "plan_depth": 12, "seed_recovery_steps": 250,
           "seed_recovery_max_carriers": 2,
           "seed_recovery_patch_base_depth": 1}
    if path.exists():
        try:
            cfg.update(_j.loads(path.read_text()))
        except Exception:
            pass
    cfg["mode"], cfg["mode_alias"] = _normalize_play_mode(cfg.get("mode", "governed"))
    return cfg


def _projected_control_edge_identity(
    source,
    intervention,
    *,
    abstract_fn=None,
    coverage_fn=None,
):
    """Return the acquisition consumer's state-action identity when total.

    A projection failure does not erase the exact edge. It merely withholds
    transport to other presentations until the consumer can represent them.
    """
    if abstract_fn is None:
        return None
    try:
        identity = abstract_fn(source)
        if coverage_fn is not None:
            identity = coverage_fn(identity)
        edge = (identity, intervention)
        hash(edge)
        return edge
    except Exception:  # noqa: BLE001 - exact edge remains available
        return None


def _is_env_reset(context_log, round_obs) -> bool:
    """Classify the LAST observed transition as an ENVIRONMENT RESET (episode
    boundary) using the gate's own logic: append the round's observations to the
    evidence context and ask gates.env_frame_indices whether that final row is a
    refill / t-anomaly. No bespoke reset heuristic — the same classifier the
    replay gate excuses on drives the episode-crossing decision."""
    from ztare.worldmodel.gates import env_frame_indices
    tmp = EpisodeLog(list(context_log))
    for observation in round_obs:
        if isinstance(observation, Transition):
            tmp.append_transition(observation)
        else:
            s_, a_, s2_, t_ = observation
            tmp.append(s_, a_, s2_, t=t_)
    return bool(len(tmp)) and (len(tmp) - 1) in env_frame_indices(tmp)


def _first_environment_boundary_in_tail(context_log, round_obs, tail_length):
    """Return the first boundary observation in the newest trajectory tail."""
    from ztare.worldmodel.gates import env_frame_indices

    tmp = EpisodeLog(list(context_log))
    normalized = []
    for observation in round_obs:
        transition = (
            observation
            if isinstance(observation, Transition)
            else Transition(
                t=observation[3],
                s=observation[0],
                a=observation[1],
                s_next=observation[2],
            )
        )
        normalized.append(transition)
        tmp.append_transition(transition)
    tail = max(0, min(int(tail_length), len(normalized)))
    start_in_round = len(normalized) - tail
    start_in_joined = len(tmp) - tail
    candidates = sorted(
        index for index in env_frame_indices(tmp) if index >= start_in_joined
    )
    if not candidates:
        return None
    round_index = start_in_round + candidates[0] - start_in_joined
    return round_index, normalized[round_index]


def _play_round_multilife(
    adapter,
    play_model,
    *,
    budget,
    context_log,
    task_contract=None,
    **kw,
):
    """Cross environment epochs until task discharge or the action budget ends.

    ``pursue_goal`` owns one within-epoch planning leg and returns at an
    adapter-owned boundary.  This wrapper owns the run lifecycle: it replans
    from the adapter's new state without asking the carrier to predict the
    boundary repaint.  With no task contract it preserves the one-level
    stop used by seed-recovery callers.
    """
    from types import SimpleNamespace
    from ztare.common.task_discharge import adjudicate_task_discharge

    obs, trace, steps, levels, saturated, status, lives = [], [], 0, 0, False, "plan_exhausted", 1
    leg_outcomes = []
    detail = ""
    replans = 0
    planning_outcome = {}
    divergence = None
    remaining = int(budget)
    task_discharged = False
    legacy_boundary_stop = False
    discharge_receipt = None
    task_process_tokens = []
    task_decision_windows = []
    task_context_epoch = _adapter_epoch(adapter)
    run_goal_edge = kw.get("goal_edge_fn")
    run_goal_fn = kw.get("goal_fn")
    run_acquisition_obligation = kw.get("acquisition_obligation")
    base_edge_exclusion = kw.get("excluded_edge_fn")
    inherited_boundary_edges = tuple(
        kw.get("control_boundary_edges") or ()
    )
    sealed_boundary_edges = tuple(
        getattr(base_edge_exclusion, "predictive_evidence_edges", ())
        or getattr(base_edge_exclusion, "evidence_edges", ())
        or ()
    )
    sealed_history_trajectories = tuple(
        getattr(base_edge_exclusion, "history_trajectories", ()) or ()
    )
    inherited_history_trajectories = tuple(
        kw.get("control_history_trajectories") or ()
    )
    active_control_history = list(
        kw.get("control_history_prefix") or ()
    )
    active_operation_effect_history = list(
        kw.get("control_operation_effect_history_prefix") or ()
    )
    factored_projection = getattr(
        play_model,
        "_ztare_factored_projection",
        None,
    )

    def advance_control_histories(
        transitions,
        *,
        action_prefix,
        operation_effect_prefix,
    ):
        if factored_projection is None:
            return (
                (
                    *tuple(action_prefix),
                    *(transition.a for transition in transitions),
                ),
                tuple(operation_effect_prefix),
            )
        from ztare.worldmodel.mechanism_effects import (
            predictive_prefixes_from_transitions,
        )

        return predictive_prefixes_from_transitions(
            transitions,
            projection=factored_projection,
            action_prefix=action_prefix,
            operation_effect_prefix=operation_effect_prefix,
        )
    non_discharge_edges: list[tuple[object, object]] = []
    non_discharge_boundary_edges: list[
        tuple[object, object, str, tuple, tuple]
    ] = []
    non_discharge_edge_indices: list[int] = []
    projected_non_discharge_counts: dict[object, int] = {}

    def excluded_control_edge(source, intervention, time_value):
        if base_edge_exclusion is not None and base_edge_exclusion(
            source, intervention, time_value
        ):
            return True
        if any(
            source == prior_source and intervention == prior_intervention
            for prior_source, prior_intervention in non_discharge_edges
        ):
            return True
        projected = _projected_control_edge_identity(
            source,
            intervention,
            abstract_fn=kw.get("abstract_fn"),
            coverage_fn=kw.get("coverage_fn"),
        )
        # One task-open boundary excludes its exact edge. Two distinct
        # presentations with the same consumer identity admit transport of the
        # no-good across that support fiber.
        return (
            projected is not None
            and projected_non_discharge_counts.get(projected, 0) >= 2
        )

    while remaining > 0:
        if task_contract is not None:
            discharge_receipt = adjudicate_task_discharge(adapter, task_contract)
            task_discharged = discharge_receipt.discharged
        if task_discharged:
            status = "task_discharged"
            break
        leg_kw = dict(kw)
        if task_contract is not None:
            leg_kw["control_task_contract_sha256"] = task_contract.sha256
        if getattr(run_goal_fn, "active_count", 1) == 0:
            leg_kw["goal_fn"] = None
        if getattr(run_goal_edge, "active_count", 1) == 0:
            leg_kw["goal_edge_fn"] = None
        active_epoch = _adapter_epoch(adapter)
        active_rows = ()
        if active_epoch is not None:
            evidence_bank = EpisodeLog(
                transition
                for transition in (*tuple(context_log), *tuple(obs))
                if isinstance(transition, Transition)
            )
            active_rows = evidence_bank.within_epoch_view(active_epoch)
        if active_epoch is not None and "evidence_states" not in leg_kw:
            leg_kw["evidence_states"] = tuple(
                state
                for transition in active_rows
                for state in (transition.s, transition.s_next)
            )
        if active_epoch is not None and "evidence_transitions" not in leg_kw:
            from ztare.worldmodel.gates import law_scored_view

            leg_kw["evidence_transitions"] = tuple(
                law_scored_view(evidence_bank, source_epoch=active_epoch)
            )
        if hasattr(run_goal_edge, "for_source_epoch"):
            if active_epoch is not None:
                # A terminal outcome may recur while its concrete source
                # presentation does not.  Re-scope on every lifecycle leg;
                # an absent witness makes directed planning undefined and
                # hands control to acquisition inside pursue_goal.
                leg_kw["goal_edge_fn"] = run_goal_edge.for_source_epoch(
                    active_epoch
                )
                if getattr(
                    leg_kw["goal_edge_fn"],
                    "active_count",
                    1,
                ) == 0:
                    leg_kw["goal_edge_fn"] = None
        if hasattr(run_acquisition_obligation, "for_source_epoch"):
            if active_epoch is not None:
                leg_kw["acquisition_obligation"] = (
                    run_acquisition_obligation.for_source_epoch(active_epoch)
                )
        if base_edge_exclusion is not None or non_discharge_edges:
            leg_kw["excluded_edge_fn"] = excluded_control_edge
        active_boundary_edges = tuple(non_discharge_boundary_edges)
        if (
            inherited_boundary_edges
            or sealed_boundary_edges
            or active_boundary_edges
        ):
            leg_kw["control_boundary_edges"] = tuple((
                *inherited_boundary_edges,
                *sealed_boundary_edges,
                *active_boundary_edges,
            ))
        leg_kw["control_history_prefix"] = tuple(active_control_history)
        leg_kw["control_operation_effect_history_prefix"] = tuple(
            active_operation_effect_history
        )
        if sealed_history_trajectories or inherited_history_trajectories:
            leg_kw["control_history_trajectories"] = tuple((
                *inherited_history_trajectories,
                *sealed_history_trajectories,
            ))
        leg_observation_start = len(obs)
        leg_history_start = tuple(active_control_history)
        leg_operation_effect_history_start = tuple(
            active_operation_effect_history
        )
        pr = pursue_goal(adapter, play_model, max_steps=remaining, **leg_kw)
        leg_trace = list(getattr(pr, "trace", []) or [])
        obs.extend(pr.observed_transitions)
        trace.extend(leg_trace)
        steps += pr.steps_executed
        levels += pr.levels_gained
        saturated = saturated or bool(pr.saturated)
        status = pr.status
        detail = str(getattr(pr, "detail", "") or "")
        # The ARC adapter cannot attest every environment-owned respawn.  A
        # mismatch on such a row arrives as ``unclassified`` and can only be
        # resolved after joining it to the evidence context.  Normalize that
        # disposition before writing the leg receipt: otherwise the same row
        # is reported here as scientific refutation and later excluded by the
        # replay gate's shared boundary classifier.
        inferred_repaint = (
            pr.status == "model_diverged"
            and pr.steps_executed > 0
            and _is_env_reset(context_log, obs)
        )
        inferred_transition = (
            pr.observed_transitions[-1]
            if inferred_repaint
            and pr.observed_transitions
            and isinstance(pr.observed_transitions[-1], Transition)
            else None
        )
        inferred_context_transition = bool(
            inferred_transition is not None
            and any(
                known.s == inferred_transition.s
                and known.a == inferred_transition.a
                and known.s_next == inferred_transition.s_next
                for known in active_rows
            )
        )
        inferred_boundary = bool(
            inferred_repaint and not inferred_context_transition
        )
        boundary_observation = None
        boundary_observation_index = None
        if inferred_boundary and pr.observed_transitions:
            boundary_observation = pr.observed_transitions[-1]
            boundary_observation_index = len(obs) - 1
        elif (
            pr.status == "environment_boundary"
            and pr.observed_transitions
        ):
            located_boundary = _first_environment_boundary_in_tail(
                context_log,
                obs,
                len(pr.observed_transitions),
            )
            if located_boundary is not None:
                boundary_observation_index, boundary_observation = (
                    located_boundary
                )
        if inferred_context_transition:
            status = "environment_context_transition_inferred"
            detail = (
                "evidence-side classifier matched a prior within-epoch "
                "transition; replan from its observed context"
            )
        elif inferred_boundary:
            status = "environment_boundary_inferred"
            detail = (
                "evidence-side boundary classifier resolved an adapter-"
                "unclassified repaint; the within-epoch carrier was not refuted"
            )
        replans += int(getattr(pr, "replans", 0) or 0)
        planning_outcome = dict(
            getattr(pr, "planning_outcome", {}) or {}
        )
        task_process_tokens.extend(
            str(token)
            for token in (
                planning_outcome.get("continual_control_process_tokens")
                or ()
            )
            if str(token)
        )
        refuted_goal_hypotheses: tuple[str, ...] = ()
        candidate_goal_edge = getattr(pr, "candidate_goal_edge", None)
        active_leg_goal_edge = leg_kw.get("goal_edge_fn")
        can_refute_candidate_edge = bool(
            isinstance(candidate_goal_edge, dict)
            and callable(
                getattr(active_leg_goal_edge, "refute_satisfied", None)
            )
        )
        if (
            (
                status in {"plan_exhausted", "candidate_goal_reached"}
                and callable(
                    getattr(run_goal_fn, "refute_satisfied", None)
                )
            )
            or can_refute_candidate_edge
        ) and task_contract is not None:
            discharge_receipt = adjudicate_task_discharge(adapter, task_contract)
            task_discharged = discharge_receipt.discharged
            if task_discharged:
                status = "task_discharged"
                detail = "registered task adjudicator accepted the candidate predicate"
            else:
                if can_refute_candidate_edge:
                    refuted_goal_hypotheses = tuple(
                        active_leg_goal_edge.refute_satisfied(
                            candidate_goal_edge["source"],
                            candidate_goal_edge["operation"],
                            candidate_goal_edge.get("time"),
                        )
                    )
                else:
                    refuted_goal_hypotheses = tuple(
                        run_goal_fn.refute_satisfied(adapter.state)
                    )
                if refuted_goal_hypotheses:
                    if status not in {
                        "environment_boundary",
                        "environment_boundary_inferred",
                        "model_diverged",
                    }:
                        status = "goal_hypothesis_refuted"
                        detail = (
                            "adapter task adjudication remained open after "
                            "reaching "
                            f"{len(refuted_goal_hypotheses)} candidate "
                            "relation(s)"
                        )
                    planning_outcome["goal_hypotheses_refuted"] = list(
                        refuted_goal_hypotheses
                    )
                    planning_outcome["goal_hypotheses_remaining"] = int(
                        getattr(
                            (
                                active_leg_goal_edge
                                if can_refute_candidate_edge
                                else run_goal_fn
                            ),
                            "active_count",
                            0,
                        )
                    )
        decision_window = planning_outcome.get("task_decision_choice")
        if (
            isinstance(decision_window, dict)
            and task_contract is not None
            and pr.steps_executed > 0
        ):
            required_decision_fields = (
                "decision_namespace",
                "choice_context_sha256",
                "continuation_context_sha256",
                "chosen_option_family_sha256",
                "chosen_option_variant_sha256",
                "available_option_family_sha256s",
            )
            if all(
                decision_window.get(field)
                for field in required_decision_fields
            ):
                from ztare.common.equivariance import stable_sha256

                leg_discharge_receipt = adjudicate_task_discharge(
                    adapter,
                    task_contract,
                )
                leg_task_discharged = (
                    leg_discharge_receipt.discharged
                )
                if leg_task_discharged:
                    task_discharged = True
                    status = "task_discharged"
                leg_adjudication_sha256 = stable_sha256(
                    leg_discharge_receipt.to_dict()
                )
                task_decision_windows.append({
                    **{
                        field: decision_window[field]
                        for field in required_decision_fields
                    },
                    "outcome": (
                        "attained"
                        if leg_task_discharged
                        else "open"
                    ),
                    "evidence_ref": (
                        "task_adjudication:"
                        + leg_adjudication_sha256
                    ),
                })
        leg_outcomes.append(
            {
                "status": status,
                "steps_executed": int(pr.steps_executed),
                "detail": detail,
                "planning_outcome": planning_outcome,
                "non_discharge_edges_excluded": len(non_discharge_edges),
            }
        )
        remaining -= max(pr.steps_executed, 0)
        if task_discharged:
            break
        if (
            refuted_goal_hypotheses
            and remaining > 0
            and status not in {
                "environment_boundary",
                "environment_boundary_inferred",
                "model_diverged",
            }
        ):
            (
                next_action_history,
                next_operation_effect_history,
            ) = advance_control_histories(
                pr.observed_transitions,
                action_prefix=leg_history_start,
                operation_effect_prefix=(
                    leg_operation_effect_history_start
                ),
            )
            active_control_history = list(next_action_history)
            active_operation_effect_history = list(
                next_operation_effect_history
            )
            continue
        if pr.levels_gained > 0:
            if task_contract is not None:
                discharge_receipt = adjudicate_task_discharge(adapter, task_contract)
                task_discharged = discharge_receipt.discharged
            else:
                # Compatibility callers such as seed recovery ask for one
                # adapter boundary, but no task contract means no discharge
                # authority.  Preserve the stop without fabricating completion.
                legacy_boundary_stop = True
                status = "environment_boundary"
                break
            if task_discharged:
                status = "task_discharged"
                break
            lives += 1
            active_control_history = []
            active_operation_effect_history = []
            continue
        if (
            status == "environment_context_transition_inferred"
            and pr.steps_executed > 0
        ):
            # The exact source-operation-successor triple already belongs to
            # transition evidence. Task non-discharge cannot turn it into
            # partiality. The repaint begins a fresh finite-history segment,
            # while its observed successor remains the next planning state.
            lives += 1
            active_control_history = []
            active_operation_effect_history = []
            continue
        if status in {"environment_boundary", "environment_boundary_inferred"} \
                and pr.steps_executed > 0:
            # The adapter has now supplied the missing consequence of the
            # simulated edge.  If the active task adjudicator remains open,
            # that concrete source/intervention is a control no-good for this
            # run.  Feed it back through pursue_goal's single prediction door
            # before starting the next life; do not edit the transition law.
            if task_contract is not None:
                discharge_receipt = adjudicate_task_discharge(
                    adapter, task_contract
                )
                task_discharged = discharge_receipt.discharged
            if task_discharged:
                status = "task_discharged"
                break
            last_observation = (
                boundary_observation
                if boundary_observation is not None
                else pr.observed_transitions[-1]
                if pr.observed_transitions else None
            )
            if isinstance(last_observation, Transition):
                edge = (last_observation.s, last_observation.a)
            elif (
                isinstance(last_observation, tuple)
                and len(last_observation) >= 2
            ):
                edge = (last_observation[0], last_observation[1])
            else:
                edge = None
            if edge is not None and not any(
                edge[0] == prior_source and edge[1] == prior_intervention
                for prior_source, prior_intervention in non_discharge_edges
            ):
                non_discharge_edges.append(edge)
                projected = _projected_control_edge_identity(
                    edge[0],
                    edge[1],
                    abstract_fn=kw.get("abstract_fn"),
                    coverage_fn=kw.get("coverage_fn"),
                )
                if projected is not None:
                    projected_non_discharge_counts[projected] = (
                        projected_non_discharge_counts.get(projected, 0) + 1
                    )
                if boundary_observation_index is None:
                    boundary_observation_index = len(obs) - 1
                non_discharge_edge_indices.append(
                    int(boundary_observation_index)
                )
                local_boundary_index = max(
                    0,
                    int(boundary_observation_index)
                    - leg_observation_start,
                )
                non_discharge_boundary_edges.append((
                    edge[0],
                    edge[1],
                    (
                        "arc3_play_loop:active_control_boundary#"
                        f"{len(non_discharge_boundary_edges)}"
                    ),
                    tuple((
                        *leg_history_start,
                        *leg_trace[:local_boundary_index],
                    )),
                    advance_control_histories(
                        pr.observed_transitions[:local_boundary_index],
                        action_prefix=leg_history_start,
                        operation_effect_prefix=(
                            leg_operation_effect_history_start
                        ),
                    )[1],
                ))
            lives += 1
            active_control_history = []
            active_operation_effect_history = []
            continue
        # Preserve only a carrier counterexample.  A legacy/untyped boundary can
        # initially surface from the within-epoch planner as ``model_diverged``;
        # once the shared boundary classifier identifies it as an environment
        # reset above, retaining that payload would relabel an epoch transition
        # as a scientific-law failure in the play report.
        if divergence is None and getattr(pr, "divergence", None) is not None:
            divergence = pr.divergence
        break        # genuine stop: saturation / real divergence / budget spent
    continual_task_experience = {
        "status": "not_recorded",
        "reason": "task contract, process tokens, or persistence path absent",
    }
    if (
        task_contract is not None
        and (task_process_tokens or task_decision_windows)
        and kw.get("receipts_dir") is not None
    ):
        try:
            from ztare.common.continual_skill_memory import (
                load_continual_skill_memory,
                record_task_decision_experience,
                record_task_experience,
                save_continual_skill_memory,
            )
            from ztare.common.equivariance import stable_sha256

            discharge_receipt = adjudicate_task_discharge(
                adapter,
                task_contract,
            )
            task_discharged = discharge_receipt.discharged
            if task_discharged:
                status = "task_discharged"
            adjudication = discharge_receipt.to_dict()
            outcome = "attained" if task_discharged else "open"
            adjudication_sha256 = stable_sha256(adjudication)
            trace_ref = "arc3-control-run:" + stable_sha256({
                "task_contract_sha256": task_contract.sha256,
                "process_tokens": tuple(task_process_tokens),
                "decision_choices": tuple(
                    (
                        choice["decision_namespace"],
                        choice["choice_context_sha256"],
                        choice["chosen_option_variant_sha256"],
                        choice["outcome"],
                    )
                    for choice in task_decision_windows
                ),
                "outcome": outcome,
                "adjudication_sha256": adjudication_sha256,
            })
            memory_path = (
                Path(kw["receipts_dir"])
                / "continual_skill_memory.json"
            )
            memory_before = load_continual_skill_memory(memory_path)
            memory_after = memory_before
            if task_process_tokens:
                memory_after = record_task_experience(
                    memory_after,
                    task_contract_sha256=task_contract.sha256,
                    trace_ref=trace_ref,
                    outcome=outcome,
                    process_tokens=tuple(task_process_tokens),
                    evidence_ref=(
                        "task_adjudication:" + adjudication_sha256
                    ),
                    context_key=(
                        "arc3-task-control-context-v1",
                        task_contract.sha256,
                        (
                            f"{type(adapter).__module__}."
                            f"{type(adapter).__qualname__}"
                        ),
                        task_context_epoch,
                    ),
                )
            for choice_index, choice in enumerate(
                task_decision_windows
            ):
                memory_after = record_task_decision_experience(
                    memory_after,
                    task_contract_sha256=task_contract.sha256,
                    trace_ref=trace_ref,
                    choice_index=choice_index,
                    outcome=str(choice["outcome"]),
                    decision_namespace=str(
                        choice["decision_namespace"]
                    ),
                    choice_context_sha256=str(
                        choice["choice_context_sha256"]
                    ),
                    continuation_context_sha256=str(
                        choice["continuation_context_sha256"]
                    ),
                    chosen_option_family_sha256=str(
                        choice["chosen_option_family_sha256"]
                    ),
                    chosen_option_variant_sha256=str(
                        choice["chosen_option_variant_sha256"]
                    ),
                    available_option_family_sha256s=tuple(map(
                        str,
                        choice["available_option_family_sha256s"],
                    )),
                    evidence_ref=str(choice["evidence_ref"]),
                )
            save_continual_skill_memory(memory_path, memory_after)
            continual_task_experience = {
                "status": "recorded",
                "trace_ref": trace_ref,
                "outcome": outcome,
                "process_token_count": len(task_process_tokens),
                "effect_option_token_count": sum(
                    token.startswith("effect_option:")
                    for token in task_process_tokens
                ),
                "choice_experience_count": 0,
                "decision_experience_count": len(
                    task_decision_windows
                ),
                "adjudication_sha256": adjudication_sha256,
                "memory_before_sha256": memory_before.memory_sha256,
                "memory_after_sha256": memory_after.memory_sha256,
                "credit_witness_count": len(
                    memory_after.credit_witnesses
                ),
            }
        except Exception as task_memory_error:  # noqa: BLE001
            continual_task_experience = {
                "status": "recording_failed",
                "error_type": type(task_memory_error).__name__,
            }
    # ``lives`` is execution history.  Preserve the terminal lifecycle outcome
    # as status so downstream routing can distinguish task discharge, model
    # refutation, environment boundaries, and bounded planning exhaustion.
    return SimpleNamespace(status=status,
                           steps_executed=steps, levels_gained=levels,
                           saturated=saturated, observed_transitions=obs,
                           lives=lives, divergence=divergence, trace=trace,
                           detail=detail, replans=replans,
                           planning_outcome=planning_outcome,
                           leg_outcomes=leg_outcomes,
                           non_discharge_edge_count=len(non_discharge_edges),
                           non_discharge_edge_indices=non_discharge_edge_indices,
                           non_discharge_projection_count=sum(
                               1 for count in projected_non_discharge_counts.values()
                               if count >= 2
                           ),
                           task_discharged=task_discharged,
                           legacy_boundary_stop=legacy_boundary_stop,
                           task_contract=(task_contract.to_dict() if task_contract is not None else None),
                           task_discharge_receipt=(
                               discharge_receipt.to_dict()
                               if discharge_receipt is not None else None
                           ),
                           continual_task_experience=(
                               continual_task_experience
                           ))


def _terminal_witness_sha(pr) -> "str | None":
    div = getattr(pr, "divergence", None)
    if not isinstance(div, dict):
        return None
    witness = div.get("terminal_witness")
    return witness.get("sha256") if isinstance(witness, dict) else None


def _terminal_model_mismatch(pr) -> bool:
    return getattr(pr, "divergence", None) is not None and int(
        getattr(pr, "levels_gained", 0) or 0
    ) > 0


def _transition_model_mismatch(pr) -> bool:
    return getattr(pr, "divergence", None) is not None


def _write_play_report_and_terminal_audit(project: Path, report: dict) -> dict:
    """Persist the play report and its authority-boundary closure audit."""
    ws = project / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "arc3_play_loop_report.json").write_text(json.dumps(report, indent=2))
    try:
        from ztare.worldmodel.search_control_repair import write_terminal_closure_audit
        return write_terminal_closure_audit(project)
    except Exception as exc:  # noqa: BLE001 - report persistence is primary
        audit = {
            "schema": "ztare-worldmodel-terminal-closure-audit-error-v1",
            "status": "audit_write_failed",
            "error": str(exc)[:300],
        }
        (ws / "terminal_closure_audit.json").write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return audit


def _apply_trace_audit_consequence(report: dict, audit: dict) -> tuple[list[str], list[str]]:
    """Fence the existing result field when an operational route is open."""
    active = [
        str(finding["check_id"])
        for finding in audit.get("findings", [])
        if finding.get("verdict") == "anomaly"
        and finding.get("routing_scope") == "active_apparatus"
    ]
    advisory = [
        str(finding["check_id"])
        for finding in audit.get("findings", [])
        if finding.get("verdict") == "anomaly"
        and finding.get("routing_scope") == "catalog_advisory"
    ]
    if any(
        bool((finding.get("witness") or {}).get("halt_required"))
        for finding in audit.get("findings", [])
    ):
        report["result"] = "operational_route_obstruction"
    report["trace_auditor_active_anomalies"] = active
    report["trace_auditor_catalog_advisories"] = advisory
    return active, advisory


def _kernel_role_bindings(pr) -> list:
    div = getattr(pr, "divergence", None)
    if not isinstance(div, dict):
        return []
    bindings = list(div.get("kernel_role_bindings") or [])
    witness = div.get("terminal_witness")
    if isinstance(witness, dict):
        bindings.extend(witness.get("kernel_role_bindings") or [])
    seen = set()
    out = []
    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        key = (binding.get("term"), tuple(binding.get("roles") or ()))
        if key in seen:
            continue
        seen.add(key)
        out.append(binding)
    return out


def _write_level_boundary_seed(
    project: Path,
    *,
    game_id: str,
    cycle: int,
    completed_level: int,
    actions: list[int],
    source: str = "arc3_play_loop",
    execution_segments: list[dict] | None = None,
) -> dict:
    """Persist a replayable seed for the next level boundary.

    The seed is substrate adapter evidence, not a model claim: it lets bounded
    transfer probes replay the exact terminal path from reset instead of relying
    on an external scratch file.
    """
    next_level = max(1, int(completed_level) + 1)
    flat_actions = [int(a) for a in actions]
    raw_segments = execution_segments or [{
        "segment_kind": "active_control",
        "source_ref": source,
        "authority": "live_environment_execution",
        "actions": flat_actions,
    }]
    segments = []
    cursor = 0
    for index, raw_segment in enumerate(raw_segments):
        segment_actions = [int(a) for a in (raw_segment.get("actions") or [])]
        if not segment_actions:
            continue
        segment = {
            "segment_id": str(raw_segment.get("segment_id") or f"segment-{index}"),
            "segment_kind": str(raw_segment.get("segment_kind") or "active_control"),
            "source_ref": str(raw_segment.get("source_ref") or source),
            "authority": str(raw_segment.get("authority") or "live_environment_execution"),
            "start_index": cursor,
            "end_index_exclusive": cursor + len(segment_actions),
            "actions": segment_actions,
        }
        segments.append(segment)
        cursor += len(segment_actions)
    derived_actions = [action for segment in segments for action in segment["actions"]]
    if derived_actions != flat_actions:
        raise ValueError("execution segments must derive the from-reset action projection exactly")
    receipt = {
        "schema": "ztare-level-boundary-seed-v1",
        "game": game_id,
        "cycle": int(cycle),
        "completed_level": int(completed_level),
        "target_level": next_level,
        "execution_segments": segments,
        "full_sequence_from_reset": flat_actions,
        "sequence_len": len(flat_actions),
        "source": source,
        "authority": (
            "replay seed only; transfer, model adoption, and solve claims still "
            "require the normal replay/holdout/live gates"
        ),
    }
    ws = project / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    target = ws / f"level{next_level}_seed.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    (ws / "latest_level_boundary_seed.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def _planner_attention_bindings(pr, *, goal_fn=None, goal_edge_fn=None,
                                progress_fn=None,
                                evidence_grown_by: int | None = None) -> list[dict]:
    """Typed pressure for the Strategy Office: the transition model can be good
    while search control is under-specified. This is advisory routing only; it
    cannot promote a candidate or claim a solve."""
    if goal_fn is not None or goal_edge_fn is not None or progress_fn is not None:
        return []
    if getattr(pr, "levels_gained", 0):
        return []
    if getattr(pr, "status", "") != "plan_exhausted":
        return []
    if evidence_grown_by not in (None, 0):
        return []
    return [{
        "term": "planner_goal_cue_absent",
        "roles": ["search_control", "selection", "model_update"],
        "evidence": (
            "gate-passing transition model exhausted live planning without "
            "a candidate goal/progress cue or new evidence"
        ),
    }]


def _champion_spec_path(project: Path):
    return project / "workspace" / "champion_spec.json"


def _load_prior_spec(project: Path):
    """Disk-persisted champion: a fresh process warm-starts in seconds instead
    of paying a cold abduction (the in-process prior only covers round->round)."""
    import json as _j
    paths = [_champion_spec_path(project)]
    legacy = REPO / "workspace" / "champion_spec.json"
    if not paths[0].exists() and legacy.exists():
        paths.append(legacy)
    log = None
    try:
        log = EpisodeLog.read_jsonl(episode_log_path(project))
    except Exception:
        log = None
    from ztare.worldmodel.gates import replay_consistency_gate
    from ztare.worldmodel.spec_catalog import lower_spec
    for path in paths:
        try:
            spec = _j.loads(path.read_text())
            if log is not None:
                step, _err = lower_spec(spec)
                if step is None or not replay_consistency_gate(step, log).ok:
                    _append_play_receipt(project, {
                        "site": "arc3_play_loop.py:286",
                        "fallback_taken": "corrupt_champion_spec",
                        "cause": "replay_consistency_gate rejected champion spec",
                        "champion_spec_path": str(path),
                    })
                    continue
            if path != paths[0]:
                _save_champion_spec(project, spec)
            return {"verdict": "loaded", "spec": spec, "source_path": str(path)}
        except Exception:
            _append_play_receipt(project, {
                "site": "arc3_play_loop.py:320",
                "fallback_taken": "corrupt_champion_spec",
                "cause": "champion spec read/parse failed",
                "champion_spec_path": str(path),
            })
            continue
    return {"verdict": "missing", "spec": None}


def _load_abduced_core_spec(project: Path):
    """Advisory warm-start only. A partial abduced core may seed the miner, but
    unlike champion_spec it cannot short-circuit replay/holdout gates."""
    import json as _j
    path = project / "workspace" / "abduced_core.json"
    try:
        payload = _j.loads(path.read_text())
        spec = payload.get("spec")
        if not isinstance(spec, dict):
            return None
        from ztare.worldmodel.spec_catalog import lower_spec
        step, _err = lower_spec(spec)
        if step is None:
            return None
        return spec
    except Exception:
        return None


def _load_warm_prior_spec(project: Path):
    prior = _load_prior_spec(project)
    if isinstance(prior, dict) and prior.get("verdict") == "loaded":
        return prior.get("spec")
    return _load_abduced_core_spec(project)


def _save_champion_spec(project: Path, spec) -> None:
    import json as _j
    try:
        path = _champion_spec_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_j.dumps(spec))
    except Exception:
        pass


def _append_play_receipt(project: Path, row: dict[str, Any]) -> None:
    ledger = project / "workspace" / "arc3_play_loop_receipts.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _write_abduced_core_receipt(project: Path, log, ab) -> None:
    import json as _j
    path = project / "workspace" / "abduced_core.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    spec = getattr(ab, "spec", None)
    step_fn = getattr(ab, "step_fn", None)
    rows = list(log)
    if spec is None or step_fn is None:
        path.write_text(_j.dumps({
            "schema": "ztare-abduced-core-v1",
            "spec": None,
            "transitions": len(rows),
            "matched_transitions": 0,
            "residuals": [],
        }))
        return
    residual_classes = {}
    matched = 0
    for tr in rows:
        pred = step_fn(tr.s, tr.a, tr.t)
        if pred == tr.s_next:
            matched += 1
            continue
        cells = []
        for y in range(len(tr.s)):
            for x in range(len(tr.s[0])):
                if pred[y][x] != tr.s_next[y][x]:
                    cells.append(f"({y},{x}) predicted {pred[y][x]} real {tr.s_next[y][x]}")
        signature = (tr.a, len(cells), tuple(cells[:40]))
        row = residual_classes.get(signature)
        if row is None:
            row = {
                "first_t": tr.t,
                "action": tr.a,
                "cell_count": len(cells),
                "count": 0,
                "_t_values": set(),
                "t": tr.t,
                "cells": cells[:40],
            }
            residual_classes[signature] = row
        row["count"] += 1
        row["_t_values"].add(tr.t)
        row["first_t"] = min(int(row["first_t"]), int(tr.t))
    residuals = []
    for row in residual_classes.values():
        out_row = dict(row)
        t_values = sorted(int(t) for t in out_row.pop("_t_values", set()))
        out_row["t_values"] = t_values[:20]
        out_row["t_value_count"] = len(t_values)
        residuals.append(out_row)
    residuals = sorted(
        residuals,
        key=lambda r: (-int(r["count"]), int(r["first_t"]), int(r["action"])),
    )[:3]
    path.write_text(_j.dumps({
        "schema": "ztare-abduced-core-v1",
        "spec": spec,
        "transitions": len(rows),
        "matched_transitions": matched,
        "residual_class_count": len(residual_classes),
        "residuals": residuals,
    }))


def _write_worldmodel_blueprint(project: Path, log, spec) -> "Path | None":
    """Producer edge for the worldmodel <-> LeanMill feedback loop.

    The play loop may prepare proof work from an abduced spec, but it never
    converts conjectures into planner constraints. Only `absorb_ratification`
    can write `invariant_certificates.jsonl` after the kernel accepts a proof.
    """
    if not isinstance(spec, dict):
        return None
    import json as _j
    try:
        from ztare.worldmodel.lean_bridge import (
            WORLDMODEL_INVARIANT_BINDING_SCHEMA,
            write_blueprint,
        )
        from ztare.worldmodel.object_roles import induce_roles
        try:
            roles = induce_roles(log, _log_arity(log)).roles
        except Exception:  # noqa: BLE001 — roles are blueprint context, not authority
            roles = []
        path = write_blueprint(project, spec, log, roles)
        try:
            command_path = path.relative_to(REPO)
        except ValueError:
            command_path = path
        blueprint_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        from ztare.common.equivariance import stable_sha256

        spec_sha256 = stable_sha256(spec)
        from ztare.common.observation_chart import capture_project_evidence_epoch

        evidence_epoch_sha256 = capture_project_evidence_epoch(project).epoch_sha256
        proof_command = (
            f"./venv/bin/python -m ztare.leanmill.cli campaign "
            f"{command_path}"
        )
        async_command = (
            f"./venv/bin/python -m ztare.leanmill.workbench_actions "
            f"autoformalize-notes {command_path} --project {project.name} "
            f"--save --json"
        )
        receipt = {
            "schema": "ztare-worldmodel-lean-feedback-v2",
            "status": "blueprint_emitted",
            "blueprint_ref": str(path.relative_to(project)),
            "blueprint_sha256": blueprint_sha256,
            "spec_sha256": spec_sha256,
            "evidence_epoch_sha256": evidence_epoch_sha256,
            "invariant_binding_schema": WORLDMODEL_INVARIANT_BINDING_SCHEMA,
            "next_command": proof_command,
            "async_command": async_command,
            "absorb_command_template": (
                f"./venv/bin/python -m ztare.worldmodel.lean_bridge absorb "
                f"--project {project} --lean-file <closed.lean> --theorem <theorem_name>"
            ),
            "evidence_hash": log.content_hash(),
            "routes": {
                "prove_current_spec": {
                    "status": "ready",
                    "command": proof_command,
                    "async_command": async_command,
                    "candidate": "theorem consequence of the frozen concrete spec",
                },
                "repair_single_proof_gap": {
                    "status": "inside_leanmill",
                    "operator": "solver.abduction.route_abduction",
                    "candidate": "missing premise that remains a child proof obligation",
                },
                "discover_reusable_theory": {
                    "status": "awaiting_signed_unseen_task_family",
                    "operator": "ztare.leanmill.axiom_pack",
                    "minimum_distinct_eval_tasks": 2,
                    "required": [
                        "typed_base_theory",
                        "typed_axiom_proposals",
                        "signed_pre_candidate_task_manifest",
                        "unseen_eval_tasks_not_embedded_in_this_blueprint",
                    ],
                    "command_template": (
                        "./venv/bin/python -m ztare.leanmill.axiom_pack "
                        "<typed_axiom_pack_blueprint.json> --out <screen.json>"
                    ),
                    "arc_consumption_rule": (
                        "a pack may assist later proof campaigns; only a separately audited theorem "
                        "derived from this concrete spec may enter invariant_certificates.jsonl"
                    ),
                },
            },
            "authority": (
                "proof-work handoff only; conjectures are not enforced until "
                "a byte-matched L1/L2/L3 proof audit writes certificates to "
                "workspace/invariant_certificates.jsonl"
            ),
        }
        out = project / "workspace" / "worldmodel_lean_feedback_receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_j.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return path
    except Exception as exc:  # noqa: BLE001 — proof handoff must not block play
        out = project / "workspace" / "worldmodel_lean_feedback_receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_j.dumps({
            "schema": "ztare-worldmodel-lean-feedback-v1",
            "status": "blueprint_skipped",
            "reason": f"{type(exc).__name__}: {exc}",
            "evidence_hash": log.content_hash(),
            "authority": "proof-work handoff failure; no planner constraint emitted",
        }, indent=2, sort_keys=True) + "\n")
        return None


def _lean_feedback_checkpoint(project: Path, blueprint_path: "Path | None",
                              blueprint_sha256: "str | None") -> None:
    """Close the ARC↔LeanMill return edge at each governed checkpoint.

    Two non-blocking steps (ZTARE_ARC_LEAN_FEEDBACK=0 disables both):

    (a) KICK: if a freshly-emitted blueprint exists and no async campaign job
        has been launched for its sha, launch one in the background now and
        stamp the sha so re-entry is idempotent.
    (b) POLL: scan <project>/leanmill/jobs/ for any COMPLETED proof_audit job;
        for each, call absorb_ratification to append invariant_certificates.jsonl.
        A malformed job receipt raises loudly; an incomplete job is silently skipped.
    """
    import os as _os
    if _os.environ.get("ZTARE_ARC_LEAN_FEEDBACK", "1") == "0":
        return

    # ---- (a) KICK: idempotent campaign launch keyed by blueprint sha ----------
    if blueprint_path is not None and blueprint_sha256:
        stamp = project / "workspace" / "leanmill_campaign_launched.json"
        launched_sha = ""
        try:
            launched_sha = json.loads(stamp.read_text())["blueprint_sha256"]
        except Exception:  # noqa: BLE001 — missing / malformed stamp == not launched
            pass
        if launched_sha != blueprint_sha256:
            try:
                env = _os.environ.copy()
                src = str((REPO / "src").resolve())
                env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else f"{src}{_os.pathsep}{env['PYTHONPATH']}"
                subprocess.Popen(
                    [sys.executable, "-m", "ztare.leanmill.cli", "campaign", str(blueprint_path)],
                    cwd=str(REPO),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                stamp.parent.mkdir(parents=True, exist_ok=True)
                stamp.write_text(json.dumps({
                    "blueprint_sha256": blueprint_sha256,
                    "blueprint_ref": str(blueprint_path),
                }) + "\n")
                print(f"  [lean-feedback] campaign kicked (sha={blueprint_sha256[:12]})", flush=True)
            except Exception as _kick_err:  # noqa: BLE001 — kick must never block play
                print(f"  [lean-feedback] campaign kick failed (non-fatal): {_kick_err}", flush=True)

    # ---- (b) POLL: absorb any completed proof_audit jobs ----------------------
    jobs_dir = project / "leanmill" / "jobs"
    if not jobs_dir.exists():
        return
    try:
        from ztare.worldmodel.lean_bridge import absorb_ratification, extract_theorem_statements
    except Exception as _imp_err:  # noqa: BLE001
        print(f"  [lean-feedback] import error (non-fatal): {_imp_err}", flush=True)
        return

    for job_path in sorted(jobs_dir.glob("lm_*.json"), reverse=True):
        if job_path.name.endswith("_result.json"):
            continue
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(job, dict):
            continue
        if job.get("action") != "proof_audit":
            continue
        if job.get("status") not in ("completed",):
            continue
        # Locate the result file
        result_ref = (job.get("paths") or {}).get("result") or job.get("result_path") or ""
        if not result_ref:
            continue
        result_path = (REPO / result_ref) if not Path(result_ref).is_absolute() else Path(result_ref)
        if not result_path.exists():
            result_path = project / result_ref
        if not result_path.exists():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as _rj_err:
            raise RuntimeError(f"[lean-feedback] malformed result JSON at {result_path}: {_rj_err}") from _rj_err
        if not isinstance(result, dict):
            raise RuntimeError(f"[lean-feedback] result file is not a JSON object: {result_path}")
        if not result.get("ok"):
            continue  # proof_audit failed or timed out — skip quietly
        # Absorb: need the .lean source file and theorem name(s)
        source_ref = job.get("source_file", "")
        if not source_ref:
            continue
        lean_path = (REPO / source_ref) if not Path(source_ref).is_absolute() else Path(source_ref)
        if not lean_path.exists():
            lean_path = project / source_ref
        if not lean_path.exists():
            continue
        target_name = job.get("target_name", "")
        try:
            if target_name:
                source_text = lean_path.read_text(encoding="utf-8")
                stmts = extract_theorem_statements(source_text, [target_name])
            else:
                # absorb_ratification extracts all theorems itself when given a raw source line
                stmts = [f"theorem {n}" for n in _theorem_names_from_lean(lean_path)]
            if stmts:
                certs = absorb_ratification(project, lean_path, stmts)
                if certs:
                    print(f"  [lean-feedback] absorbed {len(certs)} certificate(s) from {lean_path.name}", flush=True)
        except Exception as _abs_err:  # noqa: BLE001 — absorb must not block play
            print(f"  [lean-feedback] absorb_ratification error (non-fatal): {_abs_err}", flush=True)


def _theorem_names_from_lean(lean_path: Path) -> "list[str]":
    """Extract top-level theorem/lemma names from a .lean file (no imports needed)."""
    import re as _re
    pat = _re.compile(r"^(?:private\s+)?(?:theorem|lemma)\s+([A-Za-z0-9_'.]+)\b", _re.MULTILINE)
    try:
        return pat.findall(lean_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []


def _sprint_ident_receipt(project: Path, row: dict) -> None:
    """Append one row to workspace/sprint_identification.jsonl."""
    p = project / "workspace" / "sprint_identification.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _champion_warm_start(project: Path, log: "EpisodeLog") -> "dict | None":
    """Read-only bitmap check: is the current champion correct on all checked rows?

    Returns {"wrong_rows": [...], "rows": N, "carrier_path": str} on success,
    None on any failure (caller treats None as warmstart_unavailable).
    """
    # ponytail: test_model.py is the canonical champion carrier in the project.
    carrier = project / "test_model.py"
    if not carrier.exists():
        return None
    ep_path = episode_log_path(project)
    if not ep_path.exists():
        return None
    try:
        from ztare.worldmodel.evidence_consolidation import build_row_bitmap
        bitmap = build_row_bitmap(carrier, ep_path, project_dir=project)
        return {
            "wrong_rows": bitmap.get("wrong_rows", []),
            "rows": bitmap.get("total_rows", 0),
            "carrier_path": str(carrier),
        }
    except Exception:  # noqa: BLE001 — failure must not block the sprint
        return None


def _sprint(project: Path, adapter, cfg: dict, progress_fn, goal_fn,
            champion_model=None, game_id: str = "", goal_edge_fn=None) -> dict:
    """ZERO-TOKEN hot path (the Rodionov-throughput fix): abduce -> play long
    -> absorb divergence -> re-abduce. Plays only gate-passing abduced models;
    the adapter-authority task adjudicator and raw gates hold everywhere; governance runs at
    checkpoints, not per step."""
    import os as _os
    from ztare.worldmodel.spec_abduction import abduce_spec
    from ztare.worldmodel.gates import rollout_depth as _rd
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    hold = EpisodeLog.read_jsonl(episode_log_path(project, episode=2))
    out = {"rounds": [], "levels": 0, "deepest": 0,
           "task_discharged": False}
    from ztare.worldmodel.gates import replay_consistency_gate as _rcg
    # FIX 3: wall-clock budget for the identification step (default 900s).
    try:
        _ident_budget_s = float(_os.environ.get("ZTARE_SPRINT_IDENT_BUDGET_S", "900"))
    except ValueError:
        _ident_budget_s = 900.0
    # Champion first; if absent, seed from a partial abduced-core receipt. The
    # latter is only a search prior and still pays the normal replay gates.
    prior_spec = _load_warm_prior_spec(project)
    verified_prefix = 0
    for rnd in range(1, int(cfg["sprint_rounds"]) + 1):
        # FIX 2: sub-phase receipt for identification (abduce + warm-start check).
        # FIX 1: warm-start / skip — evaluate the champion bitmap before paying
        # the full abduce cost. If wrong_rows is empty the champion already
        # explains every checked row; skip re-identification for this round.
        ab = None
        with phase("sprint.identification", project / "workspace"):
            import time as _time
            _ident_t0 = _time.monotonic()
            # --- warm-start check (read-only, failure-safe) ---
            _ws = None
            try:
                _ws = _champion_warm_start(project, log)
            except Exception:  # noqa: BLE001
                pass
            if _ws is None:
                # bitmap unavailable — full pipeline as before
                _sprint_ident_receipt(project, {
                    "schema": "ztare.sprint_identification.v1",
                    "round": rnd,
                    "action": "warmstart_unavailable",
                    "rows": len(log),
                })
            elif not _ws["wrong_rows"]:
                # champion explains all checked rows — skip from-scratch abduction
                _sprint_ident_receipt(project, {
                    "schema": "ztare.sprint_identification.v1",
                    "round": rnd,
                    "action": "skipped",
                    "reason": "champion_explains_all_checked_rows",
                    "rows": _ws["rows"],
                })
                print(f"  sprint {rnd}: warm-start SKIP (champion explains all "
                      f"{_ws['rows']} rows)", flush=True)
                # Reconstruct ab from the champion spec so downstream code has a
                # valid AbductionResult (replay_ok=True, step_fn set).
                from ztare.worldmodel.spec_abduction import AbductionResult
                from ztare.worldmodel.spec_catalog import lower_spec as _ls
                _champ = _load_prior_spec(project)
                _cs = _champ.get("spec") if isinstance(_champ, dict) and _champ.get("verdict") == "loaded" else None
                if _cs is not None:
                    _csf, _ = _ls(_cs)
                    ab = AbductionResult(
                        status="spec_identified", spec=_cs, step_fn=_csf,
                        replay_ok=True,
                        detail="warmstart: champion_explains_all_checked_rows",
                    )
                    prior_spec = _cs
            if ab is None:
                # full abduction path: warmstart_unavailable, residual non-empty, OR
                # bitmap said 0 wrong rows but champion spec failed to load
                _elapsed = _time.monotonic() - _ident_t0
                if _elapsed >= _ident_budget_s:
                    # budget already exceeded before we started — emit receipt and skip
                    _sprint_ident_receipt(project, {
                        "schema": "ztare.sprint_identification.v1",
                        "round": rnd,
                        "action": "budget_exit",
                        "reason": "budget_already_exceeded",
                        "budget_s": _ident_budget_s,
                        "elapsed_s": round(_elapsed, 2),
                    })
                else:
                    _residual_count = len(_ws["wrong_rows"]) if _ws else None
                    ab = abduce_spec(log, adapter.action_arity, prior_spec=prior_spec,
                                     verified_prefix=verified_prefix)
                    _elapsed2 = _time.monotonic() - _ident_t0
                    if _elapsed2 >= _ident_budget_s:
                        _sprint_ident_receipt(project, {
                            "schema": "ztare.sprint_identification.v1",
                            "round": rnd,
                            "action": "budget_exit",
                            "reason": "exceeded_during_abduce",
                            "budget_s": _ident_budget_s,
                            "elapsed_s": round(_elapsed2, 2),
                            "residual_count": _residual_count,
                        })
                        # ab may be partial; we still use whatever abduce returned
                    else:
                        # label logic:
                        #   _ws is None       -> warmstart_unavailable (bitmap not computable)
                        #   _ws has residuals -> full_reidentification (champion has wrong rows)
                        #   _ws has 0 residuals but ab is None (champion spec failed to load)
                        #     -> warmstart_failed_spec_load (bitmap said OK, but spec missing)
                        if _ws is None:
                            _ident_action = "warmstart_unavailable"
                        elif _residual_count:
                            _ident_action = "full_reidentification"
                        else:
                            # bitmap says 0 wrong rows but champion spec couldn't be loaded ->
                            # fell through to full abduction; this was the residual_count=0
                            # full_reidentification mislabel (first-round cache-miss path)
                            _ident_action = "warmstart_failed_spec_load"
                        _sprint_ident_receipt(project, {
                            "schema": "ztare.sprint_identification.v1",
                            "round": rnd,
                            "action": _ident_action,
                            "residual_count": _residual_count,
                            "rows": len(log),
                            "elapsed_s": round(_elapsed2, 2),
                        })
        # budget_exit with no ab produced → treat as abduction_partial and checkpoint
        if ab is None:
            partial = {"round": rnd, "status": "abduction_partial"}
            out["rounds"].append(partial)
            _write_sprint_receipt(project, {
                "round": rnd, "status": "abduction_partial",
                "saturated": False, "goal_mode": "none", "n_candidates": 0,
                "transition_model_mismatch": False,
                "terminal_verifier_model_mismatch": False,
                "terminal_witness_sha": None, "kernel_role_bindings": [],
            })
            break
        _write_abduced_core_receipt(project, log, ab)
        _write_worldmodel_blueprint(project, log, getattr(ab, "spec", None))
        if getattr(ab, 'spec', None) and getattr(ab, 'replay_ok', False):
            _save_champion_spec(project, ab.spec)
            verified_prefix = len(list(log))
        if ab.spec is not None:
            prior_spec = ab.spec
        abduced_ok = (ab.replay_ok and ab.step_fn is not None
                      and _rd(ab.step_fn, hold) >= len(hold))
        # play the ABDUCED model if complete, else the loaded gate-passing
        # CHAMPION (mutator's) — so exhaustive coverage runs even when abduction
        # is partial (ls20 timer never abduces). Only skip if NO valid model.
        play_model = ab.step_fn if abduced_ok else champion_model
        if play_model is None or not _rcg(play_model, log).ok:
            # CATALOG CEILING. Triage the residual into counterexample-bound cards,
            # then hand implementation to the ordinary governed executable-carrier
            # worker. This keeps one proposal language and one replay/holdout arbiter;
            # the older grid-only sealed-spec implementer remains a compatibility path.
            reflex = None
            # FIX 1: gate grammar_reflex on non-empty residual — if champion
            # explains all rows the reflex has nothing to mine (propose_operators
            # would scan the full log and produce no actionable cards).
            _has_residual = (_ws is None or bool(_ws.get("wrong_rows")))
            if _has_residual and _os.environ.get("ZTARE_GRAMMAR_REFLEX", "1") != "0":
                with phase("sprint.grammar_reflex", project / "workspace"):
                    from ztare.worldmodel.grammar_reflex import route_operator_proposals
                    reflex = route_operator_proposals(
                        project,
                        log,
                        ab,
                        residual_indices=(
                            list(_ws.get("wrong_rows") or [])
                            if isinstance(_ws, dict)
                            else None
                        ),
                    )
                out.setdefault("grammar_reflex", []).append(
                    {"round": rnd, "status": reflex["status"],
                     "proposal_count": len(reflex["cards"]),
                     "dispositions": [d.get("disposition") for d in reflex["dispositions"]]})
            # Governed carrier synthesis is the single implementation owner.
            # Sprint surfaces the counterexample-bound handoff, then stops; it
            # cannot auto-adopt through the legacy sealed-spec door.
            partial = {"round": rnd, "status": "abduction_partial"}
            out["rounds"].append(partial)
            _write_sprint_receipt(project, {
                "round": rnd,
                "status": "abduction_partial",
                "saturated": False,
                "goal_mode": "none",
                "n_candidates": 0,
                "transition_model_mismatch": False,
                "terminal_verifier_model_mismatch": False,
                "terminal_witness_sha": None,
                "kernel_role_bindings": [],
            })
            break                                    # governed checkpoint owns synthesis
        # goal cascade: candidate goal/progress is steering only; the sealed
        # terminal verifier still decides success. If no candidate cue exists,
        # fall back to abduced structural candidates, then coverage.
        from ztare.worldmodel.goal_abduction import authoritative_goal_edge_predicate
        bank_goal_edge, bank_goal_edge_count = authoritative_goal_edge_predicate(
            log,
            source_epoch=int(getattr(adapter, "levels_completed", 0) or 0),
        )
        active_goal_edge = goal_edge_fn or bank_goal_edge
        from ztare.common.task_discharge import task_discharge_from_profile
        task_contract = task_discharge_from_profile(cfg)
        structural_gf, n_cand = (
            (None, 0)
            if goal_fn is not None or active_goal_edge is not None
            else _structural_goal_fn(
                project,
                log,
                ab,
                source_epoch=int(
                    getattr(adapter, "levels_completed", 0) or 0
                ),
                task_contract_sha256=(task_contract.sha256 if task_contract else ""),
            )
        )
        active_goal = None if active_goal_edge is not None else (goal_fn or structural_gf)
        active_progress = progress_fn if active_goal is None and active_goal_edge is None else None
        # VISITED SEED FROM RAW EVIDENCE (single source of truth): the frontier
        # store is the live cache UNION every abstract state in the log, so
        # coverage never re-walks a state the evidence already witnessed.
        source_epoch = _adapter_epoch(adapter)
        af, visited_path, visited_store = _frontier_memory(
            project,
            log,
            source_epoch=source_epoch,
        )
        with phase("sprint.multilife", project / "workspace"):
            pr = _play_round_multilife(
                adapter, play_model, budget=int(cfg["sprint_steps"]), context_log=log,
                goal_fn=active_goal,
                goal_edge_fn=active_goal_edge,
                progress_fn=active_progress,
                resource_colors=_resource_colors(
                    project,
                    log,
                    source_epoch=source_epoch,
                ),
                invariants=_invariants(project, play_model), abstract_fn=af,
                coverage_fn=_coverage_fn(
                    project,
                    log,
                    source_epoch=source_epoch,
                ),
                visited_store=visited_store, visited_path=visited_path,
                plan_depth=int(cfg["plan_depth"]), max_replans=40,
                task_contract=task_contract)
        log, _admitted = _append_observations(
            project, pr.observed_transitions, log=log
        )
        out["deepest"] = max(out["deepest"], pr.steps_executed)
        out["rounds"].append({"round": rnd, "pursuit": pr.status,
                              "steps": pr.steps_executed, "log": len(log),
                              "saturated": bool(pr.saturated),
                              "transition_model_mismatch": _transition_model_mismatch(pr),
                              "terminal_verifier_model_mismatch": _terminal_model_mismatch(pr),
                              "terminal_witness_sha": _terminal_witness_sha(pr),
                              "kernel_role_bindings": _kernel_role_bindings(pr)})
        _write_sprint_receipt(project, {
            "round": rnd, "saturated": bool(pr.saturated),
            "goal_mode": (
                "environment_goal_edge" if active_goal_edge is not None else
                "candidate_goal" if goal_fn is not None else
                "candidate_progress" if active_progress is not None else
                "structural" if structural_gf else "coverage"
            ),
            "n_candidates": bank_goal_edge_count if active_goal_edge is not None else n_cand,
            "transition_model_mismatch": _transition_model_mismatch(pr),
            "terminal_verifier_model_mismatch": _terminal_model_mismatch(pr),
            "terminal_witness_sha": _terminal_witness_sha(pr),
            "kernel_role_bindings": _kernel_role_bindings(pr)})
        print(f"  sprint {rnd}: {pr.status} depth={pr.steps_executed} log={len(log)}",
              flush=True)
        out["task_discharged"] = bool(getattr(pr, "task_discharged", False))
        if pr.levels_gained > 0:
            out["levels"] += pr.levels_gained
            completed_level = int(getattr(adapter, "levels_completed", 0) or pr.levels_gained)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=rnd,
                completed_level=completed_level,
                actions=list(getattr(pr, "trace", []) or []),
                source="arc3_play_loop_sprint",
            )
            out["level_boundary_seed"] = {
                "target_level": seed["target_level"],
                "sequence_len": seed["sequence_len"],
                "source_ref": f"workspace/level{seed['target_level']}_seed.json",
            }
            if pr.observed_transitions:
                _write_goal_exemplar(
                    project,
                    pr.observed_transitions[-1],
                    cycle=f"sprint{rnd}",
                    game_id=game_id,
                    task_contract=task_contract,
                )
            print(f"  🏆 LEVEL in sprint {rnd}", flush=True)
        if out["task_discharged"]:
            break
    # --- LEVEL-3 machinery contradiction detection (append-only wiring) ---
    try:
        from ztare.worldmodel.machinery_contradictions import detect_and_card as _dc
        # derive divergence_indices from round log-length deltas; first round's
        # pre-sprint rows are unknown here so round-1 divergence may be missed —
        # acceptable: the spiral detector needs >=3 rounds anyway.
        _div_idx: set = set()
        _prev_rlog = None
        for _r in out["rounds"]:
            _cur_rlog = _r.get("log")
            if (_prev_rlog is not None and _cur_rlog is not None
                    and (_r.get("pursuit") or _r.get("status", "")) == "model_diverged"):
                _div_idx.update(range(_prev_rlog, _cur_rlog))
            if _cur_rlog is not None:
                _prev_rlog = _cur_rlog
        _mc = _dc(project, log, out["rounds"], divergence_indices=_div_idx)
        out["machinery_cards"] = _mc
        if _mc:
            latest = out["rounds"][-1] if out["rounds"] else {}
            _write_sprint_receipt(project, {
                **latest,
                "machinery_cards": _mc,
            })
    except Exception:  # noqa: BLE001 — detector failure must never break a sprint
        pass
    return out


def _log_arity(log) -> int:
    return 1 + max((tr.a for tr in log), default=0)


def _adapter_epoch(adapter):
    epoch = getattr(adapter, "current_epoch", None)
    if epoch is None:
        epoch = getattr(adapter, "levels_completed", None)
    if epoch is None:
        epoch = getattr(
            getattr(adapter, "last_transition_identity", None),
            "target_epoch",
            None,
        )
    return epoch


_ROLE_STATE_CACHE: dict[tuple, object] = {}


def _role_state(project: Path, log=None, *, source_epoch=None):
    """Compute evidence-induced roles once per episode/sidecar byte identity.

    ``_abstract_fn``, ``_coverage_fn``, and ``_resource_colors`` previously
    repeated the same full-bank scan in one play turn.  The key contains both
    episode and sidecar stat identities; any evidence append or chart migration
    invalidates it.  This is a process-local projection cache, never authority.
    """
    episode = episode_log_path(project)
    sidecar = episode.with_name(f"{episode.stem}.identity.json")

    def stat_identity(path: Path):
        if not path.is_file():
            return None
        stat = path.stat()
        return (stat.st_mtime_ns, stat.st_size)

    key = (
        str(episode.resolve()),
        stat_identity(episode),
        stat_identity(sidecar),
        source_epoch,
    )
    cached = _ROLE_STATE_CACHE.get(key)
    if cached is not None:
        return cached
    if log is None:
        log = EpisodeLog.read_jsonl(episode)
    from ztare.worldmodel.object_roles import induce_roles
    planning_log = log.within_epoch_view(source_epoch)
    state = induce_roles(planning_log, _log_arity(planning_log))
    _ROLE_STATE_CACHE.clear()
    _ROLE_STATE_CACHE[key] = state
    return state


def _abstract_fn(project: Path, log=None, *, source_epoch=None):
    """Object-state key for FSM memoization and coverage.

    Prefer induced role signatures when the log exposes a controlled mover: they
    separate agent pose, passive resource clocks, and reactive terrain. Fall
    back to volatile-cell signatures for early or non-role evidence.
    """
    from ztare.worldmodel.object_roles import (
        object_signature, sound_signature, volatile_positions)
    if log is None:
        log = EpisodeLog.read_jsonl(episode_log_path(project))

    def bind_identity(fn):
        fn._ztare_receipt_context = {
            "abstraction_version": _FRONTIER_ABSTRACTION_VERSION,
            "evidence_hash": log.content_hash(),
        }
        return fn

    try:
        roles = _role_state(project, log, source_epoch=source_epoch).roles
        if any(r.name == "moves_under_actions" for r in roles):
            return bind_identity(lambda g: object_signature(g, roles))
    except Exception:
        pass
    vp = volatile_positions(log)
    return bind_identity(lambda g: sound_signature(g, vp)) if vp else None


def _coverage_fn(project: Path, log=None, *, source_epoch=None):
    """Frontier projection paired with `_abstract_fn`.

    ARC object roles expose a shorter controllable-state carrier than their full
    transition signature. Substrates without that carrier keep identity
    coverage.
    """
    try:
        from ztare.worldmodel.object_roles import control_signature
        roles = _role_state(project, log, source_epoch=source_epoch).roles
        if any(r.name == "moves_under_actions" for r in roles):
            return control_signature
    except Exception:
        pass
    return None


def _invariants(project: Path, subject=None) -> list:
    """Kernel-ratified invariants only enforce; conjectured ones ride along.
    Ratification receipts live in workspace/invariant_certificates.jsonl."""
    from ztare.worldmodel.lean_bridge import load_current_invariants

    return load_current_invariants(project, subject=subject)


def _structural_goal_fn(
    project: Path,
    log,
    ab,
    *,
    source_epoch=None,
    task_contract_sha256="",
):
    """Pre-exemplar goal source (in-loop wiring, 2026-07-03): dormant-event /
    goal-abduction candidates compiled to ONE OR-predicate — reaching ANY
    candidate state is worth probing; the adapter adjudicator disposes. Returns
    (goal_fn_or_None, n_candidates). Falls back to (None, 0) if the module or
    candidates are absent."""
    try:
        from ztare.worldmodel.goal_abduction import (
            abduce_goal_candidates,
            compile_goal_hypothesis_set,
            predicate_from_spec,
        )
        goal_log = log
        if source_epoch is not None:
            # Lifecycle selection has one authority-bearing door.  Repeating a
            # local identity filter here previously omitted the authority check
            # and allowed candidate-authored epoch labels to scope planning.
            goal_log = log.within_epoch_view(source_epoch)
            if not len(goal_log):
                return None, 0
        roles = _role_state(
            project,
            log,
            source_epoch=source_epoch,
        )
        out = abduce_goal_candidates(
            goal_log,
            getattr(ab, "spec", None),
            roles,
        )
        trs = list(goal_log)
        start = trs[0].s if trs else None
        if start is None or not out:
            return None, 0
        if out.get("mode") == "post_success" and out.get("goal_predicate_spec"):
            predicate = predicate_from_spec(out["goal_predicate_spec"], start)
            setattr(predicate, "_ztare_source_epoch", source_epoch)
            return predicate, 1
        cands = [c for c in out.get("candidates", []) if c.get("predicate_spec")]
        task_open_states = tuple(
            transition.s_next
            for transition in goal_log
            if transition.identity is not None
            and transition.identity.is_authoritative
            and not transition.identity.is_boundary
        )
        predicate = compile_goal_hypothesis_set(
            cands,
            start,
            task_open_states=task_open_states,
            source_epoch=source_epoch,
            task_contract_sha256=task_contract_sha256,
        )
        if predicate is None:
            return None, 0
        setattr(predicate, "_ztare_source_epoch", source_epoch)
        return predicate, len(cands)
    except Exception:
        return None, 0


def _candidate_task_hypotheses(
    project: Path,
    *,
    source_epoch,
    task_contract,
    candidate_paths=(),
):
    """Load current-epoch leaf task hypotheses without adopting their carrier."""

    if task_contract is None or source_epoch is None:
        return None
    try:
        from ztare.worldmodel.goal_abduction import (
            compile_candidate_goal_hypothesis_set,
        )

        active = EpisodeLog.read_jsonl(episode_log_path(project)).within_epoch_view(
            source_epoch
        )
        states = tuple(
            state
            for transition in active
            for state in (transition.s, transition.s_next)
        )
        projected = compile_candidate_goal_hypothesis_set(
            project,
            source_epoch=source_epoch,
            task_contract_sha256=task_contract.sha256,
            witness_states=(*states[:8], *states[-8:]),
            task_open_states=states,
        )
        if projected is not None:
            return projected
        from ztare.common.observation_chart import capture_project_evidence_epoch

        evidence_epoch = capture_project_evidence_epoch(project).epoch_sha256
        records = []
        for path in candidate_paths:
            path = Path(path)
            try:
                ref = str(path.resolve().relative_to(project.resolve()))
            except (OSError, ValueError):
                continue
            if path.is_file():
                records.append({
                    "source_type": "task_hypothesis",
                    "artifact_role": "task_hypothesis",
                    "submission": ref,
                    "evidence_epoch_sha256": evidence_epoch,
                })
        return compile_candidate_goal_hypothesis_set(
            project,
            source_epoch=source_epoch,
            task_contract_sha256=task_contract.sha256,
            witness_states=(*states[:8], *states[-8:]),
            task_open_states=states,
            records=records,
        )
    except Exception:  # noqa: BLE001 - optional steering never blocks identification
        return None


def _seed_visited(
    visited_path,
    log,
    abstract_fn,
    *,
    inherited=None,
    start_row: int = 0,
) -> set:
    """Single source of truth for the exploration frontier: the live-play cache
    (visited_path) UNION every abstract object-state witnessed in the evidence
    log (both endpoints of each transition). The side file is only a live-play
    cache; the evidence log is the master. Pure and testable."""
    from ztare.worldmodel.reachability import load_visited
    store = set(inherited or ())
    store.update(load_visited(visited_path))
    if abstract_fn is not None:
        rows = list(log)
        for tr in rows[max(0, int(start_row)):]:
            store.add(abstract_fn(tr.s))
            store.add(abstract_fn(tr.s_next))
    return store


def _episode_prefix_identity(path: Path, byte_limit: int | None = None) -> dict:
    digest = hashlib.sha256()
    consumed = 0
    with path.open("rb") as handle:
        while byte_limit is None or consumed < byte_limit:
            size = 1024 * 1024
            if byte_limit is not None:
                size = min(size, byte_limit - consumed)
            chunk = handle.read(size)
            if not chunk:
                break
            digest.update(chunk)
            consumed += len(chunk)
    return {"bytes": consumed, "sha256": digest.hexdigest()}


def _sidecar_semantic_sha(episode_path: Path) -> str | None:
    sidecar = episode_path.with_name(f"{episode_path.stem}.identity.json")
    if not sidecar.is_file():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unreadable"
    payload.pop("episode_sha256", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sidecar_binding_prefix_sha(
    episode_path: Path,
    row_limit: int,
) -> str | None:
    """Identity of the sidecar meaning over an existing episode prefix."""
    sidecar = episode_path.with_name(f"{episode_path.stem}.identity.json")
    if not sidecar.is_file():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unreadable"
    bindings: list[dict] = []
    for binding in payload.get("bindings") or []:
        if not isinstance(binding, dict):
            return "unreadable"
        try:
            row_index = int(binding.get("row_index", -1))
        except (TypeError, ValueError):
            return "unreadable"
        if row_index < int(row_limit):
            bindings.append(binding)
    prefix_payload = {
        "schema": payload.get("schema"),
        "episode_chart_sha256": payload.get("episode_chart_sha256"),
        "bindings": bindings,
        # A changed chart or transport contract may change the meaning of an
        # old binding even when the row bytes did not change, so keep both.
        "observation_charts": payload.get("observation_charts") or [],
        "transport_windows": payload.get("transport_windows") or [],
    }
    encoded = json.dumps(
        prefix_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _frontier_scope(
    project: Path,
    log,
    abstract_fn,
    *,
    source_epoch=None,
    frontier_rows: int | None = None,
) -> dict:
    """Validity key for live frontier memory.

    Frontier memory is a quotient cache, not a substrate fact. It is reusable
    only for the evidence content and abstraction version that defined the
    quotient; otherwise stale coverage can make a fresh play round look
    saturated before it has spent actions.
    """
    episode = episode_log_path(project)
    prefix = _episode_prefix_identity(episode)
    return {
        "schema": _FRONTIER_SCOPE_SCHEMA,
        "evidence_hash": log.content_hash(),
        "evidence_rows": len(log),
        "episode_prefix_bytes": prefix["bytes"],
        "episode_prefix_sha256": prefix["sha256"],
        "sidecar_semantic_sha256": _sidecar_semantic_sha(episode),
        "sidecar_binding_prefix_sha256": _sidecar_binding_prefix_sha(
            episode, len(log)
        ),
        "source_epoch": source_epoch,
        "frontier_rows": int(
            len(log) if frontier_rows is None else frontier_rows
        ),
        "abstraction_version": (
            _FRONTIER_ABSTRACTION_VERSION if abstract_fn is not None else "none"
        ),
    }


def _frontier_memory_path(project: Path, scope: dict) -> Path:
    raw = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    return project / "workspace" / "frontier" / f"visited_{sha}.jsonl"


def _write_frontier_scope_receipt(
    project: Path,
    scope: dict,
    visited_path: Path,
    *,
    inherited_rows: int = 0,
) -> None:
    receipt = dict(scope)
    receipt["visited_path"] = str(visited_path.relative_to(project))
    receipt["inherited_rows"] = int(inherited_rows)
    receipt["authority"] = (
        "frontier cache only; ignored automatically when evidence hash or "
        "abstraction version changes"
    )
    p = project / "workspace" / "latest_frontier_scope.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def _frontier_memory(project: Path, log=None, *, source_epoch=None):
    """Shared quotient-frontier memory for sprint and governed play."""
    if log is None:
        log = EpisodeLog.read_jsonl(episode_log_path(project))
    frontier_log = log.within_epoch_view(source_epoch)
    abstract = _abstract_fn(project, log, source_epoch=source_epoch)
    latest_path = project / "workspace" / "latest_frontier_scope.json"
    prior = None
    if latest_path.is_file():
        try:
            prior = json.loads(latest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prior = None
    scope = _frontier_scope(
        project,
        log,
        abstract,
        source_epoch=source_epoch,
        frontier_rows=len(frontier_log),
    )
    visited_path = _frontier_memory_path(project, scope)
    inherited: set = set()
    inherited_rows = 0
    if (
        isinstance(prior, dict)
        and prior.get("abstraction_version") == scope["abstraction_version"]
        and prior.get("source_epoch") == scope["source_epoch"]
    ):
        try:
            prior_rows = int(prior.get("evidence_rows", -1))
            prior_frontier_rows = int(prior.get("frontier_rows", -1))
            prior_bytes = int(prior.get("episode_prefix_bytes", -1))
            prior_ref = str(prior.get("visited_path") or "")
            prior_visited = project / prior_ref
            prefix = _episode_prefix_identity(episode_log_path(project), prior_bytes)
            prefix_matches = (
                0 <= prior_rows <= len(log)
                and 0 <= prior_frontier_rows <= len(frontier_log)
                and prior_bytes >= 0
                and prefix["bytes"] == prior_bytes
                and prefix["sha256"] == prior.get("episode_prefix_sha256")
                and _sidecar_binding_prefix_sha(
                    episode_log_path(project), prior_rows
                ) == prior.get("sidecar_binding_prefix_sha256")
                and prior_visited.is_file()
            )
            if prefix_matches:
                from ztare.worldmodel.reachability import load_visited
                inherited = load_visited(prior_visited)
                inherited_rows = prior_frontier_rows
                # The cache object follows the certified append lineage.  Keep
                # one file and delta-append new quotient keys instead of
                # copying the full image into a new evidence-hash filename.
                visited_path = prior_visited
        except (OSError, TypeError, ValueError):
            inherited = set()
            inherited_rows = 0
    visited_store = _seed_visited(
        visited_path,
        frontier_log,
        abstract,
        inherited=inherited,
        start_row=inherited_rows,
    )
    from ztare.worldmodel.reachability import save_visited
    save_visited(visited_path, visited_store)
    _write_frontier_scope_receipt(
        project,
        scope,
        visited_path,
        inherited_rows=inherited_rows,
    )
    return abstract, visited_path, visited_store


def _write_sprint_receipt(project: Path, receipt: dict) -> None:
    """Minimal latest-sprint receipt the briefing reads (saturation + goal mode)."""
    import json as _j
    p = project / "workspace" / "latest_sprint_receipt.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_j.dumps(receipt))


def _resource_colors(project: Path, log=None, *, source_epoch=None) -> list:
    """Monotone-depleting roles = the resource whose bar bounds the horizon
    as a search coordinate. Proof-enforced pruning is separate and only comes
    from `_invariants(project)` reading kernel-ratified certificates."""
    try:
        for r in _role_state(project, log, source_epoch=source_epoch).roles:
            if r.name == "monotone_depleting":
                return list(r.members)
    except Exception:
        pass
    return []


def _record_spec_receipt(project: Path, spec: dict, cycle: int) -> None:
    """Ratified-spec receipt: the seed data for the calibrated cross-game
    catalog (which operators, which parameter shapes, which game, verdicts)."""
    import json as _json
    path = project / "workspace" / "spec_receipts.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    ops = sorted({r.get("op") for rules in spec.get("actions", {}).values() for r in rules}
                 | {r.get("op") for r in spec.get("always", [])})
    with path.open("a") as f:
        f.write(_json.dumps({"schema": "ztare-spec-receipt-v1", "project": project.name,
                             "cycle": cycle, "ops": ops, "spec": spec,
                             "verdict": "replay_and_holdout_pass",
                             "source": "abduction"}) + chr(10))


def _write_goal_exemplar(
    project: Path,
    transition,
    *,
    cycle,
    game_id: str,
    task_contract,
) -> dict | None:
    """Persist a terminal-edge witness with its lifecycle identity."""

    if not isinstance(transition, Transition):
        return None
    identity = getattr(transition, "identity", None)
    if identity is None or not identity.is_authoritative:
        return None
    row = {
        "schema": "ztare-goal-exemplar-v2",
        "game": game_id,
        "cycle": cycle,
        "t": transition.t,
        "action": transition.a,
        "s": [list(r) for r in transition.s],
        "s_next": [list(r) for r in transition.s_next],
        "source_epoch": identity.source_epoch,
        "target_epoch": identity.target_epoch,
        "transition_identity": identity.to_dict(),
        "task_contract_sha256": (
            task_contract.sha256 if task_contract is not None else ""
        ),
        "authority": "adapter-attested terminal edge; no cross-epoch transport",
    }
    path = project / "workspace" / "goal_exemplars.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _validate_carrier_rubric_aware(source: str, project) -> None:
    validate_worldmodel_carrier_source(
        source,
        dynamics_assumption=project_dynamics_assumption(project),
    )


def _load_ratified_model(project: Path):
    """The champion the governed loop just ratified — the mutator's test_model.py
    (python carrier or grid_dsl PROGRAM), plus an optional PROGRESS heuristic the
    mutator inferred from the observed frames. Returns (model, progress_fn); the
    progress heuristic is STEERING ONLY (the adapter adjudicator judges success, so a
    wrong cue costs efficiency, never correctness — the non-iatrogenic split)."""
    tm = project / "test_model.py"
    if not tm.exists():
        return None, None, None
    source = tm.read_text()
    _validate_carrier_rubric_aware(source, project)
    ns: dict = {"__name__": "candidate"}
    try:
        exec(compile(source, str(tm), "exec"), ns)  # noqa: S102 — our own sealed file
    except Exception as exc:  # noqa: BLE001 — no-model is a valid outcome, silence is not
        print(f"  ratified model failed to load ({tm}): "
              f"{type(exc).__name__}: {exc}", flush=True)
        return None, None, None
    return _model_from_namespace(project, ns)


def _governed_adoption_cursor(project: Path) -> dict[str, Any]:
    telemetry = project / "workspace" / "iteration_telemetry.jsonl"
    model_path = project / "test_model.py"
    try:
        offset = telemetry.stat().st_size
    except OSError:
        offset = 0
    try:
        model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    except OSError:
        model_sha = ""
    return {"telemetry_offset": offset, "model_sha256": model_sha}


def _materialize_governed_baseline(
    project: Path,
    *,
    source: str,
    source_ref: str,
    candidate_sha256: str,
    producer_id: str,
) -> dict[str, Any]:
    """Bind governed search to the selected residual-frontier carrier.

    This is baseline selection, not promotion.  The cursor is captured after
    materialization, so adoption still requires changed bytes plus a current-run
    promotion event.
    """

    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if source_sha != str(candidate_sha256):
        raise ValueError("governed baseline source does not match proposal identity")
    _validate_carrier_rubric_aware(source, project)
    target = project / "test_model.py"
    prior_sha = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else ""
    if prior_sha != source_sha:
        temporary = target.with_suffix(".py.tmp")
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(target)
    repair_frontier_refreshed = False
    if (project / "gate_harness.py").is_file():
        from ztare.common.patch_base_identity import load_current_repair_frontier
        from ztare.validator.core.repair_preflight import (
            patch_base_regression_retry_message,
        )

        patch_base_regression_retry_message(
            enabled=True,
            project_dir=project,
            candidate_source=source,
            python_executable=sys.executable,
        )
        frontier = load_current_repair_frontier(project)
        if str(frontier.get("sha256") or "") != source_sha:
            raise RuntimeError(
                "selected governed baseline did not become the current-epoch "
                "repair frontier"
            )
        repair_frontier_refreshed = True
    receipt = {
        "schema": "ztare-governed-baseline-materialization-v1",
        "candidate_sha256": source_sha,
        "producer_id": str(producer_id),
        "prior_sha256": prior_sha,
        "changed": prior_sha != source_sha,
        "authority": "residual_frontier_selection",
        "promotion_authority": False,
        "source_ref": str(source_ref),
        "repair_frontier_refreshed": repair_frontier_refreshed,
    }
    _append_play_receipt(
        project,
        {"site": "arc3_play_loop.py:governed_baseline", **receipt},
    )
    return receipt


def _governed_adoption_since(project: Path, cursor: dict[str, Any]) -> dict[str, Any]:
    """Adopt a current-run search incumbent as an active discriminator."""
    telemetry = project / "workspace" / "iteration_telemetry.jsonl"
    offset = int(cursor.get("telemetry_offset") or 0)
    rows: list[dict[str, Any]] = []
    try:
        with telemetry.open("rb") as handle:
            handle.seek(offset)
            for raw in handle:
                try:
                    row = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        rows = []
    model_path = project / "test_model.py"
    try:
        current_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    except OSError:
        current_sha = ""
    promoted = any(
        row.get("record_type") == "iteration" and row.get("champion_promoted") is True
        for row in rows
    )
    changed = bool(current_sha and current_sha != str(cursor.get("model_sha256") or ""))
    immutable_ref = ""
    if promoted and changed:
        from ztare.worldmodel.patch_base_carrier import (
            materialize_immutable_patch_base,
        )

        source = model_path.read_text(encoding="utf-8")
        immutable_ref, immutable_sha = materialize_immutable_patch_base(
            project,
            source,
            prefix="governed_frontier",
        )
        if immutable_sha != current_sha:
            raise RuntimeError("governed immutable snapshot changed candidate identity")
    return {
        "schema": "ztare-governed-candidate-adoption-v1",
        "adopted": bool(promoted and changed),
        "champion_promoted_in_run": promoted,
        "adoption_scope": "active_discriminator_frontier",
        "task_discharge_authorized": False,
        "candidate_bytes_changed": changed,
        "prior_sha256": str(cursor.get("model_sha256") or ""),
        "current_sha256": current_sha,
        "immutable_source_ref": immutable_ref,
        "telemetry_rows_observed": len(rows),
    }


def _model_from_namespace(project: Path, ns: dict, *, allow_patch_base: bool = True):
    """Extract carrier plus steering-only progress and goal projections."""

    # optional goal-cue: a `progress(grid)->float` callable, or PROGRESS_SRC to
    # sandbox-compile (defense-in-depth; steering-only so it is not a trust boundary)
    progress = ns.get("progress") if callable(ns.get("progress")) else None
    if progress is None and isinstance(ns.get("PROGRESS_SRC"), str):
        from ztare.worldmodel.planner import compile_progress_heuristic
        fn, _err = compile_progress_heuristic(ns["PROGRESS_SRC"])
        progress = fn
    # GOAL_PREDICATE: the mutator's falsifiable goal HYPOTHESIS (rival: the
    # adapter adjudicator fires elsewhere; discriminator: the level event itself).
    # Steering-only — plan_to_goal targets it, levels_completed judges it.
    goal = ns.get("GOAL_PREDICATE") if callable(ns.get("GOAL_PREDICATE")) else None

    try:
        from ztare.worldmodel.carrier_loader import lower_carrier_namespace

        model = lower_carrier_namespace(
            ns,
            project_dir=project,
            attach_projection=True,
            allow_patch_base=allow_patch_base,
        )
    except Exception as exc:  # noqa: BLE001 - absence is an admissible steering outcome
        print(
            f"  transition carrier skipped: {type(exc).__name__}: {exc}",
            flush=True,
        )
        model = None
    return model, progress, goal


def _candidate_memory_records(project: Path) -> list[dict]:
    path = project / "workspace" / "candidate_memory.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    return [r for r in (records or []) if isinstance(r, dict)]


def _candidate_memory_rank(record: dict) -> tuple:
    return (
        int(record.get("visible_exact_rows") or 0),
        int(record.get("passed_gates") or 0),
        int(record.get("holdout_depth") or 0),
        float(record.get("gate_score") or 0.0),
        -int(record.get("visible_wrong_cells") or 10**12),
        str(record.get("observed_at_utc") or ""),
    )


def _load_candidate_memory_advice(project: Path, log: EpisodeLog):
    from ztare.worldmodel.gates import replay_consistency_gate

    for rec in sorted(_candidate_memory_records(project),
                      key=_candidate_memory_rank, reverse=True):
        ref = rec.get("submission") or rec.get("path")
        if not isinstance(ref, str) or not ref.strip():
            continue
        raw = Path(ref)
        if raw.is_absolute() or ".." in raw.parts:
            continue
        path = project / raw
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        _validate_carrier_rubric_aware(source, project)
        ns: dict = {"__name__": "candidate_memory_advice"}
        try:
            exec(compile(source, str(path), "exec"), ns)
            model, progress, goal = _model_from_namespace(project, ns)
            if model is None:
                continue
            replay = replay_consistency_gate(model, log)
            if replay.ok:
                return model, progress, goal, f"candidate_memory:{rec.get('sha') or path.name}"
            print(f"  advice candidate_memory skipped: {path.name}: {replay.detail}",
                  flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  advice candidate_memory skipped: {path.name}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
    return None, None, None, None


def _load_candidate_memory_steering_models(project: Path, *, max_patch_base_depth: int = 1):
    """Yield candidate-memory carriers as steering hypotheses.

    Unlike advice loading, this intentionally does not require replay
    consistency against the current log. The model is not promoted or used as
    authority; it only proposes actions for a live seed-recovery attempt, and
    the environment must confirm any level boundary before a seed is written.
    """
    for rec in sorted(_candidate_memory_records(project),
                      key=_candidate_memory_rank, reverse=True):
        ref = rec.get("submission") or rec.get("path")
        if not isinstance(ref, str) or not ref.strip():
            continue
        raw = Path(ref)
        if raw.is_absolute() or ".." in raw.parts:
            continue
        path = project / raw
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        _validate_carrier_rubric_aware(source, project)
        ns: dict = {"__name__": "candidate_memory_steering"}
        try:
            exec(compile(source, str(path), "exec"), ns)
            from ztare.worldmodel.patch_base_carrier import patch_base_chain_depth
            patch_base_depth = patch_base_chain_depth(
                ns, project_dir=project, max_depth=max(1, int(max_patch_base_depth) + 1))
            if patch_base_depth > max_patch_base_depth:
                print(f"  seed steering candidate skipped: {path.name}: "
                      f"PATCH_BASE depth {patch_base_depth} exceeds "
                      f"budget {max_patch_base_depth}", flush=True)
                continue
            model, progress, goal = _model_from_namespace(
                project, ns, allow_patch_base=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  seed steering candidate skipped: {path.name}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
            continue
        if model is not None:
            yield {
                "source": f"candidate_memory:{rec.get('sha') or path.name}",
                "model": model,
                "progress": progress,
                "goal": goal,
                "patch_base_depth": patch_base_depth,
            }


def _seed_recovery_cards(project: Path) -> list[dict]:
    try:
        from ztare.common.operator_proposal_contract import open_cards
        cards = open_cards(project / "workspace" / "strategy_experiments.jsonl")
    except Exception:  # noqa: BLE001
        return []
    out = []
    for card in cards:
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        gate = plan.get("required_next_gate") if isinstance(plan.get("required_next_gate"), dict) else {}
        if gate.get("command") == "recover_level_boundary_seed":
            out.append(card)
    return out


def _requested_seed_path(project: Path, cards: list[dict]) -> Path:
    for card in cards:
        plan = card.get("action_plan") if isinstance(card.get("action_plan"), dict) else {}
        seed = plan.get("seed_prerequisite") if isinstance(plan.get("seed_prerequisite"), dict) else {}
        raw = seed.get("seed_path")
        if isinstance(raw, str) and raw.strip():
            path = Path(raw)
            if not path.is_absolute() and ".." not in path.parts:
                return project / path
    return project / "workspace" / "level2_seed.json"


def _write_seed_recovery_receipt(project: Path, receipt: dict) -> dict:
    path = project / "workspace" / "level_boundary_seed_recovery.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def _recover_level_boundary_seed(
    project: Path,
    *,
    game_id: str,
    cfg: dict,
    adapter_factory=None,
) -> dict:
    """Execute the Strategy Office ``recover_level_boundary_seed`` producer.

    This is evidence acquisition, not candidate promotion. Stale or partial
    carriers may steer live actions, but only a sealed level increment writes a
    replayable seed.
    """
    cards = _seed_recovery_cards(project)
    if not cards:
        return {"schema": "ztare-level-boundary-seed-recovery-v1",
                "status": "skipped_no_open_card"}
    seed_path = _requested_seed_path(project, cards)
    if seed_path.exists():
        return _write_seed_recovery_receipt(project, {
            "schema": "ztare-level-boundary-seed-recovery-v1",
            "status": "seed_already_available",
            "seed_path": str(seed_path.relative_to(project)),
            "open_card_shas": [c.get("failure_family_sha") for c in cards],
        })

    adapter_factory = adapter_factory or ArcAgi3Adapter
    budget = max(1, int(cfg.get("seed_recovery_steps") or cfg.get("sprint_steps") or 250))
    max_carriers = max(0, int(cfg.get("seed_recovery_max_carriers") or 0))
    max_patch_base_depth = max(0, int(cfg.get("seed_recovery_patch_base_depth") or 0))
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    attempts = []
    adapter = adapter_factory(game_id)

    for n_carrier, candidate in enumerate(_load_candidate_memory_steering_models(
            project, max_patch_base_depth=max_patch_base_depth)):
        if max_carriers and n_carrier >= max_carriers:
            break
        print(f"  seed recovery steering: {candidate['source']}", flush=True)
        adapter.reset()
        pr = _play_round_multilife(
            adapter,
            candidate["model"],
            budget=budget,
            context_log=log,
            goal_fn=candidate.get("goal"),
            progress_fn=candidate.get("progress"),
            resource_colors=_resource_colors(
                project,
                log,
                source_epoch=_adapter_epoch(adapter),
            ),
            invariants=_invariants(project, candidate["model"]),
            abstract_fn=None,
            coverage_fn=None,
            visited_store=None,
            visited_path=None,
            plan_depth=int(cfg.get("plan_depth") or 12),
            max_replans=max(12, budget),
        )
        if pr.observed_transitions:
            _grow_evidence(project, pr.observed_transitions, adapter)
            log = EpisodeLog.read_jsonl(episode_log_path(project))
        attempt = {
            "source": candidate["source"],
            "patch_base_depth": int(candidate.get("patch_base_depth") or 0),
            "status": pr.status,
            "steps_spent": int(pr.steps_executed or 0),
            "levels_gained": int(pr.levels_gained or 0),
            "confirmed_level_after": int(getattr(adapter, "levels_completed", 0) or 0),
            "trace_len": len(getattr(pr, "trace", []) or []),
        }
        attempts.append(attempt)
        if int(pr.levels_gained or 0) > 0:
            completed_level = int(getattr(adapter, "levels_completed", 0) or pr.levels_gained)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=0,
                completed_level=completed_level,
                actions=list(getattr(pr, "trace", []) or []),
                source=f"strategy_seed_recovery:{candidate['source']}",
            )
            return _write_seed_recovery_receipt(project, {
                "schema": "ztare-level-boundary-seed-recovery-v1",
                "status": "seed_recovered",
                "seed_path": f"workspace/level{seed['target_level']}_seed.json",
                "sequence_len": seed["sequence_len"],
                "source": seed["source"],
                "attempts": attempts,
                "open_card_shas": [c.get("failure_family_sha") for c in cards],
                "composition_policy": {
                    "seed_recovery_patch_base_depth": max_patch_base_depth,
                    "seed_recovery_max_carriers": max_carriers,
                },
                "authority": (
                    "live environment confirmed the boundary; steering model was "
                    "not promoted"
                ),
            })

    # Last resort: spend a deterministic round-robin probe. This is weak but
    # makes the command executable even when no steering carrier is usable.
    adapter.reset()
    baseline = int(getattr(adapter, "levels_completed", 0) or 0)
    observed = []
    trace = []
    for i in range(budget):
        action = i % int(getattr(adapter, "action_arity", 1) or 1)
        before, t = adapter.state, adapter.t
        real = adapter.step(action)
        trace.append(int(action))
        observed.append((before, action, real, t))
        if int(getattr(adapter, "levels_completed", 0) or 0) > baseline:
            _grow_evidence(project, observed, adapter)
            completed_level = int(getattr(adapter, "levels_completed", 0) or 1)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=0,
                completed_level=completed_level,
                actions=trace,
                source="strategy_seed_recovery:round_robin",
            )
            return _write_seed_recovery_receipt(project, {
                "schema": "ztare-level-boundary-seed-recovery-v1",
                "status": "seed_recovered",
                "seed_path": f"workspace/level{seed['target_level']}_seed.json",
                "sequence_len": seed["sequence_len"],
                "source": seed["source"],
                "attempts": attempts + [{
                    "source": "round_robin",
                    "steps_spent": len(trace),
                    "levels_gained": completed_level - baseline,
                    "confirmed_level_after": completed_level,
                }],
                "open_card_shas": [c.get("failure_family_sha") for c in cards],
                "composition_policy": {
                    "seed_recovery_patch_base_depth": max_patch_base_depth,
                    "seed_recovery_max_carriers": max_carriers,
                },
                "authority": "live environment confirmed the boundary",
            })
    if observed:
        _grow_evidence(project, observed, adapter)
    return _write_seed_recovery_receipt(project, {
        "schema": "ztare-level-boundary-seed-recovery-v1",
        "status": "seed_not_recovered",
        "budget": budget,
        "attempts": attempts + [{
            "source": "round_robin",
            "steps_spent": len(trace),
            "levels_gained": int(getattr(adapter, "levels_completed", 0) or 0) - baseline,
            "confirmed_level_after": int(getattr(adapter, "levels_completed", 0) or 0),
        }],
        "open_card_shas": [c.get("failure_family_sha") for c in cards],
        "composition_policy": {
            "seed_recovery_patch_base_depth": max_patch_base_depth,
            "seed_recovery_max_carriers": max_carriers,
        },
        "next_action": "increase seed_recovery_steps or provide a replayable seed artifact",
    })


def _load_advice_model(project: Path):
    """Load a gate-passing model from the compiled advice string.

    Order matters: a persisted champion spec is the most compact symbolic advice;
    `test_model.py` is the mutator-produced carrier. Both must replay the current
    visible log before they are used for live play.
    """
    from ztare.worldmodel.gates import replay_consistency_gate
    log = EpisodeLog.read_jsonl(episode_log_path(project))

    prior = _load_prior_spec(project)
    spec = prior.get("spec") if isinstance(prior, dict) and prior.get("verdict") == "loaded" else None
    if spec is not None:
        try:
            from ztare.worldmodel.spec_catalog import lower_spec
            step, err = lower_spec(spec)
            if step is not None and replay_consistency_gate(step, log).ok:
                return step, None, None, "champion_spec"
            if err:
                print(f"  advice champion spec skipped: {err}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  advice champion spec skipped: {type(exc).__name__}: {exc}",
                  flush=True)

    model, progress, goal = _load_ratified_model(project)
    if model is not None:
        try:
            replay = replay_consistency_gate(model, log)
            if replay.ok:
                return model, progress, goal, "test_model"
            print(f"  advice test_model skipped: {replay.detail}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  advice test_model skipped: {type(exc).__name__}: {exc}",
                  flush=True)
    model, progress, goal, source = _load_candidate_memory_advice(project, log)
    if source:
        return model, progress, goal, source
    return None, None, None, None


def _clean_env() -> dict:
    """The make/loop subprocess imports `src.ztare...` and needs REPO (not
    `src`) on PYTHONPATH; this process runs with `src` on path for its own
    `ztare...` imports. Don't leak our PYTHONPATH into the subprocess."""
    import os
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    return env


def _run_governed_cycle(
    project_slug: str,
    rubric: str,
    iters: int,
    mutator: str,
    judge: str,
    *,
    turn_focus: str = "",
) -> int:
    # ITERS is a BUDGET; the rubric's `stop_on_gate_pass: true` ends the cycle
    # the moment a champion clears the hard gate, so a cycle never plays a
    # sub-gate model and never burns the full budget once a valid one exists
    # ("iterate until gates pass").
    cmd = ["make", "experiment-loop", f"PROJECT={project_slug}", f"RUBRIC={rubric}",
           f"ITERS={iters}", f"MUTATOR_MODEL={mutator}", f"JUDGE_MODEL={judge}",
           "AGENT_MUTATOR=1", "AGENT_JUDGE=1",
           "AGENT_MUTATOR_RUNTIME=codex", "AGENT_JUDGE_RUNTIME=codex", "AGENT_TIMEOUT=600"]
    env = _clean_env()
    # This conductor has already selected and gated the carrier frontier.
    # The child loop may refine it, but must not independently rescan recent
    # files and replace that identity before iteration 1.
    env["ZTARE_CHAMPION_MATERIALIZATION"] = "0"
    if turn_focus:
        env["ZTARE_WORLDMODEL_TURN_FOCUS"] = str(turn_focus)
    return subprocess.run(cmd, cwd=REPO, env=env).returncode


def archive_sealed_eval_slice(
    project: Path,
    log: EpisodeLog,
    *,
    source_carrier_sha256: str,
    source_carrier_execution_sha256: str = "",
    task_contract=None,
    task_discharge_receipt=None,
    search_control_predecessors=(),
    source_epoch=None,
    origin_seed_sha256="",
    goal_hypothesis_refutations=(),
    non_discharge_edge_indices=(),
    history_prefix_actions=(),
    history_prefix_operation_effects=(),
) -> dict:
    """Persist a live-play trajectory as a sealed eval slice.

    The slice is written to raw/episodes/eval_slices/ which is NEVER staged
    into briefing packs (briefing_pack._visible_artifact_ref_allowed blocks it).
    A ledger row is appended to workspace/sealed_eval_slices.jsonl so
    gate_harness can find the newest slice for the optional fresh-slice gate.

    Returns the ledger row dict.
    """
    import hashlib as _hl
    from datetime import datetime, timezone
    if len(source_carrier_sha256) != 64:
        raise ValueError("sealed eval slice requires a full source carrier sha256")
    if source_carrier_execution_sha256 and len(source_carrier_execution_sha256) != 64:
        raise ValueError(
            "sealed eval slice requires a full carrier execution sha256"
        )
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    slice_dir = project / "raw" / "episodes" / "eval_slices"
    slice_dir.mkdir(parents=True, exist_ok=True)
    slice_path = slice_dir / f"eval_{ts}.jsonl"
    log.write_jsonl(slice_path)
    sha256 = _hl.sha256(slice_path.read_bytes()).hexdigest()
    row = {
        "path": str(slice_path.relative_to(project)),
        "sha256": sha256,
        "recorded_utc": ts,
        "steps": len(log),
        "source": "live_play",
        "source_carrier_sha256": source_carrier_sha256,
    }
    edge_indices = tuple(dict.fromkeys(
        int(index) for index in non_discharge_edge_indices
    ))
    if any(index < 0 or index >= len(log) for index in edge_indices):
        raise ValueError("sealed non-discharge edge index is outside the slice")
    if edge_indices:
        row["non_discharge_edge_indices"] = list(edge_indices)
    history_prefix = tuple(int(action) for action in history_prefix_actions)
    if history_prefix:
        row["history_prefix_actions"] = list(history_prefix)
    operation_effect_prefix = tuple(
        tuple(token)
        for token in history_prefix_operation_effects
    )
    if operation_effect_prefix:
        row["history_prefix_operation_effects"] = [
            list(token) for token in operation_effect_prefix
        ]
    if source_carrier_execution_sha256:
        row["source_carrier_execution_sha256"] = (
            source_carrier_execution_sha256
        )
    if task_contract is not None or task_discharge_receipt is not None:
        if task_contract is None or task_discharge_receipt is None:
            raise ValueError(
                "sealed task binding requires both contract and adjudicator receipt"
            )
        from ztare.common.task_discharge import bind_task_discharge_receipt

        bound_contract, bound_receipt = bind_task_discharge_receipt(
            task_contract, task_discharge_receipt
        )
        row.update({
            "task_contract_sha256": bound_contract.sha256,
            "task_discharge_status": bound_receipt.status,
            "task_discharge_receipt_sha256": bound_receipt.sha256,
            "task_discharge_receipt": bound_receipt.to_dict(),
        })
        # Presence, including an empty list, is authoritative task-bound
        # evidence that no control boundary was adjudicated in this slice.
        row.setdefault("non_discharge_edge_indices", [])
        if source_epoch is not None:
            row["source_epoch"] = int(source_epoch)
        if origin_seed_sha256:
            if len(str(origin_seed_sha256)) != 64:
                raise ValueError("sealed task origin requires a full seed sha256")
            row["origin_seed_sha256"] = str(origin_seed_sha256)
        refuted = tuple(dict.fromkeys(
            str(item) for item in goal_hypothesis_refutations if str(item)
        ))
        if refuted:
            if bound_receipt.status != "open":
                raise ValueError(
                    "goal-hypothesis refutation requires an open task receipt"
                )
            if source_epoch is None or not origin_seed_sha256:
                raise ValueError(
                    "goal-hypothesis refutation requires source epoch and origin seed"
                )
            row["goal_hypothesis_refutations"] = list(refuted)
        if bound_receipt.status == "open" and search_control_predecessors:
            row["search_control_predecessors"] = [
                {"path": str(ref["path"]), "sha256": str(ref["sha256"])}
                for ref in search_control_predecessors
                if isinstance(ref, dict)
                and str(ref.get("path") or "")
                and len(str(ref.get("sha256") or "")) == 64
            ]
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _sealed_goal_hypothesis_refutations(
    project: Path,
    goal_hypotheses,
    *,
    task_contract,
    source_epoch: int,
    origin_seed_sha256: str,
    report_payload: dict | None = None,
) -> tuple[str, ...]:
    """Replay task-bound negative consequences into a goal version space.

    A stored identifier alone has no authority.  Admission requires the same
    task contract, lifecycle chart, and origin seed; an exact sealed trajectory
    must also contain a state satisfying the current executable predicate.
    The previous report is a one-run compatibility bridge.  Every subsequent
    archive carries the cumulative identities through this typed slice door.
    """
    from ztare.common.task_discharge import bind_task_discharge_receipt

    if (
        task_contract is None
        or not callable(getattr(goal_hypotheses, "predicate_for", None))
        or not callable(getattr(goal_hypotheses, "refute_ids", None))
        or len(str(origin_seed_sha256 or "")) != 64
    ):
        return ()
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    try:
        rows = [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, ValueError):
        rows = []

    admitted: list[str] = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("task_contract_sha256") != task_contract.sha256
            or row.get("task_discharge_status") != "open"
            or row.get("source_epoch") != int(source_epoch)
            or row.get("origin_seed_sha256") != origin_seed_sha256
        ):
            continue
        receipt_payload = row.get("task_discharge_receipt")
        try:
            _contract, receipt = bind_task_discharge_receipt(
                task_contract, receipt_payload
            )
        except (TypeError, ValueError):
            continue
        if (
            receipt.status != "open"
            or receipt.sha256 != row.get("task_discharge_receipt_sha256")
        ):
            continue
        slice_path = project / str(row.get("path") or "")
        try:
            if hashlib.sha256(slice_path.read_bytes()).hexdigest() != row.get("sha256"):
                continue
            trajectory = EpisodeLog.read_jsonl(slice_path)
        except (OSError, ValueError):
            continue
        states = tuple(
            state
            for transition in trajectory
            for state in (transition.s, transition.s_next)
        )
        # A task-open trajectory is a behavioral counterexample to every
        # current predicate that fires on one of its states.  Replay the
        # consequence instead of matching source ids, so syntactic rewrites of
        # an already-refuted predicate cannot reopen it under a new filename.
        if callable(getattr(goal_hypotheses, "satisfied_ids", None)):
            for state in states:
                admitted.extend(goal_hypotheses.satisfied_ids(state))
        for hypothesis_id in row.get("goal_hypothesis_refutations") or ():
            predicate = goal_hypotheses.predicate_for(str(hypothesis_id))
            if predicate is not None and any(predicate(state) for state in states):
                admitted.append(str(hypothesis_id))

    # The report bridge is bounded to the exact active lifecycle and exists so
    # the first typed archive can inherit the immediately preceding run.
    payload = report_payload if isinstance(report_payload, dict) else {}
    cycles = payload.get("cycles") if isinstance(payload.get("cycles"), list) else []
    prior = next((row for row in reversed(cycles) if isinstance(row, dict)), None)
    if isinstance(prior, dict):
        receipt = prior.get("task_discharge_receipt")
        seed = prior.get("seed_replay")
        if (
            isinstance(receipt, dict)
            and receipt.get("contract_sha256") == task_contract.sha256
            and receipt.get("status") == "open"
            and isinstance(seed, dict)
            and seed.get("active_epoch") == int(source_epoch)
            and seed.get("seed_sha256") == origin_seed_sha256
        ):
            admitted.extend(prior.get("prior_goal_hypotheses_refuted") or ())
            for leg in prior.get("planning_legs") or ():
                if not isinstance(leg, dict):
                    continue
                outcome = leg.get("planning_outcome")
                if not isinstance(outcome, dict):
                    continue
                admitted.extend(outcome.get("goal_hypotheses_refuted") or ())

    return goal_hypotheses.refute_ids(admitted)


def _sealed_non_discharge_edge_predicate(
    project: Path,
    *,
    source_carrier_sha256: str,
    source_carrier_execution_sha256: str = "",
    task_contract_sha256: str,
    report_payload: dict | None = None,
    abstract_fn=None,
    coverage_fn=None,
    fallback_operation_effect_prefix=(),
    source_epoch=None,
    origin_seed_sha256="",
    transition_evidence=None,
):
    """Compile prior live boundary consequences into search-only no-goods.

    The slice remains absent from prompts and candidate synthesis.  Reuse is
    allowed only for the carrier that generated the slice, with exact ledger
    and file identity, and only when the run-level task adjudicator remained
    open.  Level-completion edges retain their separate target authority.
    """
    if (
        len(str(source_carrier_sha256 or "")) != 64
        or (
            source_carrier_execution_sha256
            and len(str(source_carrier_execution_sha256)) != 64
        )
        or len(str(task_contract_sha256 or "")) != 64
    ):
        return None, 0, []
    payload = report_payload
    if not isinstance(payload, dict):
        try:
            payload = json.loads(
                (project / "workspace" / "arc3_play_loop_report.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, ValueError):
            return None, 0, []
    cycles = payload.get("cycles") if isinstance(payload.get("cycles"), list) else []
    cycle = next(
        (
            row
            for row in reversed(cycles)
            if isinstance(row, dict)
            and row.get("task_discharged") is False
            and isinstance(row.get("eval_slice"), dict)
        ),
        None,
    )
    ledger = project / "workspace" / "sealed_eval_slices.jsonl"
    try:
        ledger_rows = [
            json.loads(line)
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, ValueError):
        return None, 0, []

    carrier_rows = {
        (str(row.get("path") or ""), str(row.get("sha256") or "")): row
        for row in ledger_rows
        if isinstance(row, dict)
        and (
            row.get("source_carrier_sha256") == source_carrier_sha256
            or (
                source_carrier_execution_sha256
                and row.get("source_carrier_execution_sha256")
                == source_carrier_execution_sha256
            )
        )
        and (
            source_epoch is None
            or row.get("source_epoch") == int(source_epoch)
        )
        and (
            not origin_seed_sha256
            or row.get("origin_seed_sha256") == origin_seed_sha256
        )
    }
    requested_refs: list[dict] = []
    for row in carrier_rows.values():
        if (
            row.get("task_contract_sha256") == task_contract_sha256
            and row.get("task_discharge_status") == "open"
        ):
            requested_refs.append({"path": row.get("path"), "sha256": row.get("sha256")})
            requested_refs.extend(row.get("search_control_predecessors") or [])

    # Compatibility bridge for the immediately preceding run.  Its exact task
    # receipt supplies the identity missing from pre-schema ledger rows; the
    # next archive carries this ref forward under the typed task binding.
    if cycle is not None:
        receipt = cycle.get("task_discharge_receipt")
        if (
            isinstance(receipt, dict)
            and receipt.get("status") == "open"
            and receipt.get("contract_sha256") == task_contract_sha256
        ):
            requested_refs.append({
                "path": cycle["eval_slice"].get("path"),
                "sha256": cycle["eval_slice"].get("sha256"),
            })

    verified_refs: list[dict] = []
    trajectories: list[tuple[EpisodeLog, dict, dict | None]] = []
    for ref in requested_refs:
        if not isinstance(ref, dict):
            continue
        slice_ref = str(ref.get("path") or "")
        slice_sha = str(ref.get("sha256") or "")
        if (slice_ref, slice_sha) not in carrier_rows:
            continue
        if any(
            item["path"] == slice_ref and item["sha256"] == slice_sha
            for item in verified_refs
        ):
            continue
        slice_path = project / slice_ref
        try:
            if hashlib.sha256(slice_path.read_bytes()).hexdigest() != slice_sha:
                continue
            cycle_payload = None
            if (
                cycle is not None
                and cycle.get("eval_slice", {}).get("path") == slice_ref
                and cycle.get("eval_slice", {}).get("sha256") == slice_sha
            ):
                cycle_payload = cycle
            trajectories.append((
                EpisodeLog.read_jsonl(slice_path),
                carrier_rows[(slice_ref, slice_sha)],
                cycle_payload,
            ))
        except (OSError, ValueError):
            continue
        verified_refs.append({"path": slice_ref, "sha256": slice_sha})

    if not trajectories:
        return None, 0, []
    from ztare.worldmodel.gates import env_frame_indices

    fallback_seed_sha = str(
        origin_seed_sha256
        or (
            (cycle or {}).get("seed_replay") or {}
        ).get("seed_sha256")
        or ""
    )
    if not fallback_seed_sha:
        try:
            fallback_seed_sha = hashlib.sha256(
                (
                    project
                    / "workspace"
                    / "latest_level_boundary_seed.json"
                ).read_bytes()
            ).hexdigest()
        except OSError:
            fallback_seed_sha = ""
    from ztare.worldmodel.mechanism_effects import HistoryTrajectoryEvidence
    known_law_triples = set()
    if transition_evidence is not None:
        from ztare.worldmodel.gates import law_scored_view

        known_law_triples = {
            (transition.s, transition.a, transition.s_next)
            for transition in law_scored_view(
                transition_evidence,
                source_epoch=source_epoch,
            )
        }

    edges: list[tuple[object, object, str, tuple, tuple]] = []
    history_trajectories: list[HistoryTrajectoryEvidence] = []
    for trajectory, slice_row, cycle_payload in trajectories:
        detected_boundaries = set(env_frame_indices(trajectory))
        history_prefix = tuple(
            slice_row.get("history_prefix_actions") or ()
        )
        operation_effect_prefix = tuple(
            tuple(token)
            for token in (
                slice_row.get("history_prefix_operation_effects") or ()
            )
        )
        same_seed_origin = bool(
            fallback_seed_sha
            and slice_row.get("origin_seed_sha256") == fallback_seed_sha
        )
        if same_seed_origin and cycle_payload is not None:
            prefix_segment = next(
                (
                    segment
                    for segment in (
                        cycle_payload.get("execution_segments") or ()
                    )
                    if isinstance(segment, dict)
                    and segment.get("segment_kind")
                    == "disagreement_acquisition"
                ),
                None,
            )
            history_prefix = tuple(
                (prefix_segment or {}).get("actions") or ()
            )
        elif same_seed_origin and not operation_effect_prefix:
            # A verified level seed ends at a lifecycle boundary. Legacy
            # slices stored the whole seed sequence as a prefix even though
            # within-epoch predictive state must restart in the target epoch.
            history_prefix = ()
            operation_effect_prefix = tuple(
                tuple(token)
                for token in fallback_operation_effect_prefix
            )
        declared_indices = slice_row.get("non_discharge_edge_indices")
        if isinstance(declared_indices, list):
            edge_indices = {
                int(index)
                for index in declared_indices
                if isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < len(trajectory)
            }
        elif slice_row.get("task_contract_sha256"):
            # Typed task-bound archives own boundary identity explicitly.
            # Do not reinterpret an absent legacy field through frame-change
            # heuristics: an open ordinary transition would become a false
            # partiality witness.
            edge_indices = set()
        elif cycle_payload is not None:
            edge_indices = set()
            cursor = 0
            for leg in cycle_payload.get("planning_legs") or ():
                if not isinstance(leg, dict):
                    continue
                start = cursor
                cursor = min(
                    len(trajectory),
                    cursor + max(0, int(leg.get("steps_executed") or 0)),
                )
                if leg.get("status") not in {
                    "environment_boundary",
                    "environment_boundary_inferred",
                } or cursor <= start:
                    continue
                candidates = sorted(
                    index
                    for index in detected_boundaries
                    if start <= index < cursor
                )
                edge_indices.add(candidates[0] if candidates else cursor - 1)
            if not edge_indices:
                edge_indices = {
                    index
                    for index in detected_boundaries
                    if index - 1 not in detected_boundaries
                }
        else:
            # A boundary followed immediately by its reset is one lifecycle
            # consequence. Preserve the predecessor edge, not both repaints.
            edge_indices = {
                index
                for index in detected_boundaries
                if index - 1 not in detected_boundaries
            }
        # A task-open marker records failure to discharge the task. It cannot
        # overwrite an exact within-epoch transition identity already owned by
        # the law bank. Such a row remains in the trajectory and may transport
        # the controller into a different predictive context.
        edge_indices = {
            index
            for index in edge_indices
            if (
                trajectory.transitions()[index].s,
                trajectory.transitions()[index].a,
                trajectory.transitions()[index].s_next,
            ) not in known_law_triples
        }
        history_trajectories.append(HistoryTrajectoryEvidence(
            transitions=tuple(trajectory.transitions()),
            action_prefix=tuple(history_prefix),
            operation_effect_prefix=tuple(operation_effect_prefix),
            boundary_indices=frozenset(edge_indices),
            evidence_ref=str(slice_row.get("path") or "sealed_slice"),
        ))
        for index in sorted(edge_indices):
            transition = trajectory.transitions()[index]
            identity = transition.identity
            if (
                identity is not None
                and identity.is_authoritative
                and identity.kind == "epoch_boundary"
                and identity.boundary_kind == "level_completed"
            ):
                continue
            edge = (
                transition.s,
                transition.a,
                f"{slice_row.get('path', 'sealed_slice')}#{index}",
                tuple((
                    *history_prefix,
                    *(row.a for row in trajectory.transitions()[:index]),
                )),
                tuple(operation_effect_prefix),
            )
            if not any(
                edge[0] == source and edge[1] == intervention
                for (
                    source,
                    intervention,
                    _evidence_ref,
                    _action_history,
                    _effect_history,
                ) in edges
            ):
                edges.append(edge)
    if not edges:
        return None, 0, verified_refs

    projected_counts: dict[object, int] = {}
    for (
        source,
        intervention,
        _evidence_ref,
        _action_history,
        _effect_history,
    ) in edges:
        projected = _projected_control_edge_identity(
            source,
            intervention,
            abstract_fn=abstract_fn,
            coverage_fn=coverage_fn,
        )
        if projected is not None:
            projected_counts[projected] = projected_counts.get(projected, 0) + 1

    def excludes(source, intervention, _time_value):
        if any(
            source == prior_source and intervention == prior_intervention
            for (
                prior_source,
                prior_intervention,
                _evidence_ref,
                _action_history,
                _effect_history,
            ) in edges
        ):
            return True
        projected = _projected_control_edge_identity(
            source,
            intervention,
            abstract_fn=abstract_fn,
            coverage_fn=coverage_fn,
        )
        return projected is not None and projected_counts.get(projected, 0) >= 2

    excludes.predictive_evidence_edges = tuple(edges)
    excludes.evidence_edges = tuple(
        edge[:4] for edge in edges
    )
    excludes.history_trajectories = tuple(history_trajectories)
    return excludes, len(edges), verified_refs


def _strategy_office_enabled(cfg: dict) -> bool:
    import os as _os
    raw = _os.environ.get("ZTARE_STRATEGY_OFFICE")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return bool(cfg.get("enable_strategy_office", False))


def _has_open_strategy_cards(project: Path) -> bool:
    """Strategy cards are cross-cycle work orders.

    If one is open, producer shortcuts such as full pre-abduction should not
    starve the governed worker that can consume the card from the briefing.
    """
    try:
        from ztare.common.strategy_card_roles import (
            active_strategy_cards,
            blocking_strategy_cards,
        )

        cards = active_strategy_cards(
            project / "workspace" / "strategy_experiments.jsonl"
        )
        return bool(blocking_strategy_cards(cards, project_dir=project))
    except Exception:  # noqa: BLE001
        return False


def _maybe_convene_strategy_office(project: Path, cfg: dict, report: dict,
                                   *, cycle: int, entry: dict) -> dict:
    """Cross-cycle strategy hook.

    Default off for frugality. When enabled, it runs only after the loop has a
    persisted no-progress receipt: no level, no new evidence, and an exhausted
    plan. It commissions experiment cards; it never changes the candidate,
    gates, or terminal status.
    """
    if entry.get("pursuit") != "plan_exhausted":
        return {"enabled": True, "skipped": "pursuit_not_exhausted"}
    if int(entry.get("levels_gained") or 0) != 0:
        return {"enabled": True, "skipped": "level_gained"}
    if int(entry.get("evidence_grown_by") or 0) != 0:
        return {"enabled": True, "skipped": "new_evidence"}

    report_path = project / "workspace" / "arc3_play_loop_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    deterministic_cards = []
    try:
        from ztare.worldmodel.search_control_repair import (
            write_search_control_repair_card,
        )
        deterministic_cards = write_search_control_repair_card(project)
    except Exception:  # noqa: BLE001 — card emission cannot affect play status
        deterministic_cards = []
    if not _strategy_office_enabled(cfg):
        return {"enabled": False,
                "deterministic_cards_written": len(deterministic_cards)}
    try:
        from ztare.research_director.strategy_office import convene
        from ztare.worldmodel.strategy_battery import WorldmodelBattery
        leaf = str(cfg.get("strategy_office_leaf_model") or "gpt-5.5")
        dry = bool(cfg.get("strategy_office_dry_run", False))
        if dry:
            from ztare.research_director.strategy_office import render_dossier
            battery = WorldmodelBattery()
            dossier = battery.run_audits(project)
            text = render_dossier(dossier, battery.query_menu(),
                                  battery.experiment_kinds())
            out = project / "workspace" / "strategy_office_last_dry_run.txt"
            out.write_text(text, encoding="utf-8")
            return {"enabled": True, "dry_run": True,
                    "deterministic_cards_written": len(deterministic_cards),
                    "firing_signal": dossier.get("firing_signal"), "cycle": cycle}
        written = convene(project, WorldmodelBattery(), leaf_model=leaf,
                          judge_model=cfg.get("judge_model"),
                          mutator_model=cfg.get("mutator_model"))
        return {"enabled": True,
                "cards_written": len(written) + len(deterministic_cards),
                "deterministic_cards_written": len(deterministic_cards),
                "cycle": cycle}
    except Exception as exc:  # noqa: BLE001 — office failure cannot affect play status
        return {"enabled": True, "error": f"{type(exc).__name__}: {exc}",
                "deterministic_cards_written": len(deterministic_cards)}


def _bootstrap_explore(project: Path, adapter, cfg: dict) -> int:
    """Evidence-acquisition cold-start every fresh game needs.

    With no ratified model to play, take budgeted exploratory actions —
    round-robin over the action set with a light novelty bias from the visited
    store — and append the transitions through the honest `_grow_evidence` path
    so the next cycle's sprint re-abduces on a non-empty log and the checkpoint
    gets real evidence. No model assumptions: pure exploration. ls20 was
    bootstrapped by historical probes; a brand-new game has none, so it gathers
    its own. Budget: cfg['sprint_steps']."""
    af, _visited_path, visited = _frontier_memory(
        project,
        EpisodeLog.read_jsonl(episode_log_path(project)),
        source_epoch=_adapter_epoch(adapter),
    )
    arity, observed, tried = adapter.action_arity, [], {}
    for i in range(int(cfg["sprint_steps"])):
        s, t = adapter.state, adapter.t
        sig = af(s) if af is not None else None
        seen = tried.setdefault(sig, set())
        # light novelty bias: prefer an action not yet taken from this signature;
        # else round-robin so coverage still rotates the whole action set.
        a = next((x for x in range(arity) if x not in seen), i % arity)
        seen.add(a)
        s2 = adapter.step(a)
        observed.append((s, a, s2, t))
        if af is not None:
            visited.add(af(s2))
    return _grow_evidence(project, observed, adapter)


class _ConfiguredCandidateReady(Exception):
    """Internal control signal: a narrower System-1 producer closed its gates."""


def _gate_candidate_path(project: Path, candidate_path: Path):
    """Evaluate the exact carrier identity used by a live-play attempt."""
    project = Path(project).resolve()
    candidate_path = Path(candidate_path).resolve()
    if not candidate_path.is_file() or not (project / "gate_harness.py").is_file():
        return None
    from ztare.validator.core.pre_judge_gate import (
        consume_pre_judge_gate_receipt,
        run_pre_judge_gate_harness,
    )

    result = run_pre_judge_gate_harness(
        enabled=True,
        project_dir=project,
        latest_eval_results_path=project / "latest_eval_results.json",
        python_executable=sys.executable,
        candidate_path=candidate_path,
    )
    payload = result.payload if isinstance(result.payload, dict) else {}
    consumed = consume_pre_judge_gate_receipt(
        payload,
        candidate_path=candidate_path,
    )
    return {
        "result": result,
        "payload": payload,
        "consumed": consumed,
    }


def _gate_current_incumbent(project: Path):
    """Evaluate the mutable project root through the single pre-judge door."""

    return _gate_candidate_path(Path(project), Path(project) / "test_model.py")


def _apply_current_gate_consequences(project: Path, gate_payload: object) -> dict:
    """Route one gate receipt through the existing stale-surface producer."""
    if not isinstance(gate_payload, dict) or not gate_payload:
        return {}
    from ztare.worldmodel.stale_surface_audit import run_stale_surface_audit

    return run_stale_surface_audit(
        project,
        apply=True,
        gate_payload=gate_payload,
    )


def _current_cached_survivor(
    project: Path,
    *,
    observed_gate_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Select one current-epoch survivor through the candidate-memory door.

    Candidate memory joins carrier bytes to both the current evidence epoch
    and the policy that interpreted it.  Reuse is search-only; promotion
    remains outside this selector.
    """
    from ztare.common.candidate_memory import (
        best_admissible_candidate_memory_record,
        candidate_memory_source,
    )

    try:
        record = best_admissible_candidate_memory_record(
            project,
            source_types={"full_survivor"},
            require_submission_source=True,
        )
    except Exception:  # noqa: BLE001
        record = None
    if record is None:
        return None
    supplied = observed_gate_payloads or {}
    source_ref = str(record.get("submission") or "").strip()
    candidate_path = project / source_ref
    candidate_sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    from ztare.validator.core.pre_judge_gate import evaluation_policy_sha256

    current_policy = evaluation_policy_sha256()
    observed = supplied.get(candidate_sha, {})
    observed_gates = observed.get("gates") if isinstance(observed, dict) else None
    observed_current = bool(
        isinstance(observed_gates, dict)
        and observed_gates
        and all(
            isinstance(gate, dict) and gate.get("pass") is True
            for gate in observed_gates.values()
        )
        and str(observed.get("evaluation_policy_sha256") or "") == current_policy
    )
    if (
        str(record.get("evaluation_policy_sha256") or "") != current_policy
        and not observed_current
    ):
        return None
    source = candidate_memory_source(project, record)
    return {
        "status": "cached_survivor_current",
        "model": load_carrier_from_source(source, candidate_path.name, project),
        "source": source,
        "source_ref": source_ref,
        "candidate_sha256": candidate_sha,
        "producer_id": "candidate_memory_full_survivor",
        "gate_payload": observed,
        "membrane": {
            key: record.get(key)
            for key in ("run_role", "claim_class", "fresh_holdout_required")
        },
    }


def _configured_system1_candidate(project: Path, cfg: dict):
    """Return a configured producer's adoption or localized repair frontier."""
    project = Path(project).resolve()
    from ztare.worldmodel.deterministic_candidate_producers import (
        evaluate_configured_candidates,
    )
    from ztare.common.patch_base_identity import repair_frontier_order
    def residual_rank(payload: dict[str, Any]) -> tuple[int, int, float, int, int]:
        gates = payload.get("gates")
        if not isinstance(gates, dict):
            return (-1, -1, -1.0, -1, -(2**63))
        holdout = gates.get("holdout_rollout_exact")
        holdout_depth = holdout.get("value") if isinstance(holdout, dict) else 0
        best = (-1, -1, -1.0, -1, -(2**63))
        for gate in gates.values():
            if not isinstance(gate, dict) or gate.get("pass") is True:
                continue
            diagnostics = gate.get("diagnostics")
            if not isinstance(diagnostics, dict):
                continue
            residual = diagnostics.get("residual_table")
            if not isinstance(residual, list) or not residual:
                continue
            best = max(
                best,
                repair_frontier_order(
                    exact_rows=diagnostics.get("exact_rows"),
                    holdout_depth=holdout_depth,
                    gate_score=payload.get("score"),
                    wrong_cells=diagnostics.get("wrong_cell_count"),
                    description_length=payload.get("description_length"),
                ),
            )
        return best

    # A current-epoch full survivor already paid the deterministic gate and can
    # steer search without receiving promotion authority.  Select it before
    # replaying a stale mutable root.
    cached = _current_cached_survivor(project)
    if cached is not None:
        return cached

    # Incumbent and challenger have different authority contracts.  Reusing an
    # incumbent requires current-epoch gate coverage; replacing it additionally
    # requires strict improvement.  Check the incumbent before opening any
    # mutation producer, so an empty residual cannot be re-described as a new
    # candidate family and layered back onto the same carrier.
    incumbent_path = project / "test_model.py"
    incumbent_frontier = None
    incumbent_gate = _gate_current_incumbent(project)
    if incumbent_gate is not None:
        incumbent_result = incumbent_gate["result"]
        incumbent_payload = incumbent_gate["payload"]
        if incumbent_payload:
            consumed = incumbent_gate["consumed"]
            if not consumed["harness_ok"] or not consumed["gates_present"]:
                return {
                    "status": "verification_unavailable",
                    "causes": [
                        str(
                            (incumbent_payload.get("control_receipt") or {}).get("cause")
                            or incumbent_payload.get("verdict")
                            or "incumbent verifier emitted no gates"
                        )
                    ],
                    "candidate_sha256s": [consumed["candidate_sha256"]],
                }
            incumbent_covers_epoch = bool(
                incumbent_result.ran
                and consumed["harness_ok"]
                and consumed["gates_present"]
                and not consumed["failed_gates"]
            )
            if incumbent_covers_epoch:
                source = incumbent_path.read_text(encoding="utf-8")
                return {
                    "status": "incumbent_current",
                    "model": load_carrier_from_source(
                        source,
                        incumbent_path.name,
                        project,
                    ),
                    "source": source,
                    "candidate_sha256": consumed["candidate_sha256"],
                    "gate_payload": incumbent_payload,
                }
            incumbent_rank = residual_rank(incumbent_payload)
            if incumbent_rank[0] >= 0:
                incumbent_source = incumbent_path.read_text(encoding="utf-8")
                immutable = next(
                    (
                        path
                        for path in sorted(
                            (project / "workspace" / "submissions").glob("*.py")
                        )
                        if hashlib.sha256(path.read_bytes()).hexdigest()
                        == consumed["candidate_sha256"]
                    ),
                    incumbent_path,
                )
                incumbent_frontier = {
                    "source": incumbent_source,
                    "source_ref": str(immutable.relative_to(project)),
                    "candidate_sha256": consumed["candidate_sha256"],
                    "producer_id": "current_incumbent",
                    "rank": incumbent_rank,
                    "gate_payload": incumbent_payload,
                }

    assessed = evaluate_configured_candidates(
        project,
        cfg,
        phase="checkpoint_identification",
    )
    accepted = [candidate for candidate in assessed if candidate.gate_pass]
    if accepted:
        chosen = accepted[0]
        source = chosen.proposal.candidate_path.read_text(encoding="utf-8")
        model = load_carrier_from_source(
            source,
            chosen.proposal.candidate_path.name,
            project,
        )
        return {
            "status": "accepted",
            "model": model,
            "chosen": chosen,
            "source": source,
            "gate_payload": chosen.gate_payload,
        }

    # The producer gate writes candidate memory.  Re-enter the same selector
    # before consulting the older singleton repair-frontier receipt, reusing
    # the gate payload already observed in this call.
    cached = _current_cached_survivor(
        project,
        observed_gate_payloads={
            candidate.proposal.candidate_sha256: candidate.gate_payload
            for candidate in assessed
        },
    )
    if cached is not None:
        return cached

    # The epoch-scoped repair-frontier receipt owns continuation identity.
    # Candidate memory and producer gates are plural evidence; neither may
    # privately re-rank a role that this receipt has already resolved.
    repair_receipt = project / "workspace" / "latest_patch_base_regression.json"
    if repair_receipt.is_file():
        try:
            from ztare.common.patch_base_identity import (
                StaleRepairFrontierError,
                load_current_repair_frontier,
            )

            frontier = load_current_repair_frontier(project)
        except StaleRepairFrontierError:
            # Evidence growth expires the singleton lifecycle role.  Select a
            # replacement below from candidates verified on the current epoch;
            # an expired receipt is not verifier unavailability.
            frontier = None
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "verification_unavailable",
                "causes": [f"repair frontier unavailable: {type(exc).__name__}: {exc}"],
                "candidate_sha256s": [],
            }
        if frontier is not None:
            matching_gate_payload = next(
                (
                    row.get("gate_payload")
                    for row in ([incumbent_frontier] if incumbent_frontier else [])
                    if str(row.get("candidate_sha256") or "") == frontier["sha256"]
                ),
                None,
            )
            if matching_gate_payload is None:
                matching_gate_payload = next(
                    (
                        candidate.gate_payload
                        for candidate in assessed
                        if candidate.proposal.candidate_sha256 == frontier["sha256"]
                    ),
                    None,
                )
            return {
                "status": "residual_frontier",
                "source": frontier["path"].read_text(encoding="utf-8"),
                "source_ref": frontier["source_ref"],
                "candidate_sha256": frontier["sha256"],
                "producer_id": "repair_preflight_frontier",
                "rank": (frontier["exact_rows"], -frontier["wrong_cells"]),
                "gate_payload": matching_gate_payload,
            }

    frontiers = [
        candidate
        for candidate in assessed
        if residual_rank(candidate.gate_payload)[0] >= 0
    ]
    if not frontiers and incumbent_frontier is None:
        # A verifier that emitted no gates did not refute the proposal.  Keep
        # infrastructure availability distinct from scientific consequence:
        # otherwise a timeout/error is silently coerced to "no candidate" and
        # authorizes an unrelated raw-abduction path.
        unavailable = [
            candidate
            for candidate in assessed
            if candidate.gate_payload.get("verdict") == "harness_error"
            or not isinstance(candidate.gate_payload.get("gates"), dict)
            or not candidate.gate_payload.get("gates")
        ]
        if unavailable:
            causes = [
                str(
                    (candidate.gate_payload.get("control_receipt") or {}).get("cause")
                    or candidate.gate_payload.get("verdict")
                    or "no deterministic gates emitted"
                )
                for candidate in unavailable
            ]
            return {
                "status": "verification_unavailable",
                "causes": causes,
                "candidate_sha256s": [
                    candidate.proposal.candidate_sha256 for candidate in unavailable
                ],
            }
        return {"status": "none"}
    options = []
    if incumbent_frontier is not None:
        options.append(incumbent_frontier)
    if frontiers:
        chosen = max(frontiers, key=lambda row: residual_rank(row.gate_payload))
        options.append({
            "source": chosen.proposal.candidate_path.read_text(encoding="utf-8"),
            "source_ref": str(chosen.proposal.candidate_path.relative_to(project)),
            "candidate_sha256": chosen.proposal.candidate_sha256,
            "producer_id": chosen.proposal.producer_id,
            "rank": residual_rank(chosen.gate_payload),
            "gate_payload": chosen.gate_payload,
        })

    return {"status": "residual_frontier", **max(options, key=lambda row: row["rank"])}


def main() -> int:
    a = sys.argv
    if "--help" in a or "-h" in a:
        print(
            "usage: arc3_play_loop.py [--game GAME] [--cycles N] "
            "[--iters N] [--mode governed|sprint|hybrid|advice|competition]"
        )
        return 0
    game = a[a.index("--game") + 1] if "--game" in a else "ls20"
    cycles = int(a[a.index("--cycles") + 1]) if "--cycles" in a else 4
    iters = int(a[a.index("--iters") + 1]) if "--iters" in a else 3
    mode_override = a[a.index("--mode") + 1] if "--mode" in a else None
    slug = f"arc3_{_game_prefix(game)}_gov"
    rubric = f"rubrics/{slug}.json"
    project = REPO / "projects" / slug

    game_id = _resolve_game_id(game)
    if game_id is None:
        print(json.dumps({"error": f"game {game} not found"}))
        return 1

    cfg = _play_config(project)
    if mode_override is not None:
        cfg["mode"], cfg["mode_alias"] = _normalize_play_mode(mode_override)
    from ztare.common.task_discharge import task_discharge_from_profile

    task_contract = task_discharge_from_profile(cfg)
    print(f"play mode: {cfg['mode']} (sprint_steps={cfg['sprint_steps']}, "
          f"checkpoint_every={cfg['governed_checkpoint_every']})", flush=True)
    try:
        previous_report = json.loads(
            (project / "workspace" / "arc3_play_loop_report.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, ValueError):
        previous_report = {}
    report = {"game": game_id, "cycles": [], "mode": cfg["mode"]}
    seed_recovery = _recover_level_boundary_seed(project, game_id=game_id, cfg=cfg)
    if seed_recovery.get("status") not in {"skipped_no_open_card", None}:
        # producer emits seed_already_available|seed_recovered|seed_not_recovered
        # (never "replayable_boundary_seed_available" — that dead value left
        # satisfied seed cards permanently unrejected)
        if seed_recovery.get("status") in {"seed_already_available", "seed_recovered"}:
            rejected = reject_satisfied_seed_prerequisite_cards(
                project,
                source_ref=str(seed_recovery.get("seed_path") or "workspace/level2_seed.json"),
            )
            if rejected:
                seed_recovery["rejected_superseded_seed_cards"] = len(rejected)
        print(f"  seed recovery: {seed_recovery.get('status')}", flush=True)
        report["seed_recovery"] = seed_recovery
    # CHAMPION PERSISTENCE (bug fix): always PLAY the deepest-playing model ever
    # found, never the latest cycle's possibly-regressed submission. A governed
    # cycle only tries to IMPROVE the champion; a worse model never displaces it.
    best_model = None
    best_progress = None
    best_goal = None
    best_goal_edge = None
    best_model_path = None
    best_depth = -1
    advice_only = cfg["mode"] == "advice"
    if advice_only:
        best_model, best_progress, best_goal, _advice_source = _load_advice_model(project)
        if _advice_source:
            print(f"  advice model loaded: {_advice_source}", flush=True)
    for cyc in range(1, cycles + 1):
        # System 1 and the governed worker share one nervous-system fence: an
        # operational receipt may not be bypassed by starting another science
        # cycle while its registered consumer has not fired.
        try:
            from ztare.common.schema_routes import assert_operational_routes_ready

            assert_operational_routes_ready(project, entering_phase="governed_run")
        except Exception as route_exc:  # typed error is rendered into the play report
            report["result"] = "operational_route_obstruction"
            report["cycles"].append(
                {
                    "cycle": cyc,
                    "status": "operational_route_obstruction",
                    "cause": str(route_exc),
                }
            )
            print(f"  operational route fence: {route_exc}", flush=True)
            break

        # Resolve the configured deterministic identification door once before
        # generic sprint or router allocation.  The same result is consumed
        # below by adoption or governed repair.
        try:
            with phase("system1_candidate_gate", project / "workspace"):
                _system1 = _configured_system1_candidate(project, cfg)
        except Exception as _producer_err:  # noqa: BLE001
            report["cycles"].append(
                {
                    "cycle": cyc,
                    "status": "configured_producer_unavailable",
                    "cause": f"{type(_producer_err).__name__}: {_producer_err}",
                }
            )
            report["result"] = "configured_producer_unavailable"
            print(
                "  configured candidate producer unavailable; ending this attempt: "
                f"{type(_producer_err).__name__}: {_producer_err}",
                flush=True,
            )
            break
        _system1_status = str(_system1.get("status") or "none")
        # ESCALATION ESCAPE (env-gated, default off): residual-frontier
        # preemption assumes the patch compiler's language covers the
        # frontier. When the same frontier recurs across runs with no
        # gate-passing patch and the governed mutator is unavailable, that
        # assumption starves the ONLY producer with a wider hypothesis
        # language (sprint full abduction) — the routing deadlock observed
        # 2026-07-20 (frontier 389c8a1f recycled every cycle while abduce,
        # newly able to express the restoration family, never ran). The flag
        # demotes the preemption for this run; candidate authority is
        # unchanged (gates still decide).
        import os as _os_esc
        if (
            _system1_status == "residual_frontier"
            and _os_esc.environ.get("ZTARE_FORCE_SPRINT_REABDUCTION", "0") == "1"
        ):
            print(
                "  ZTARE_FORCE_SPRINT_REABDUCTION=1: demoting residual_frontier "
                "preemption -> sprint full re-abduction owns this cycle",
                flush=True,
            )
            _system1_status = "none"
        if _system1_status == "verification_unavailable":
            report["cycles"].append(
                {
                    "cycle": cyc,
                    "status": "verification_unavailable",
                    "candidate_sha256s": _system1.get("candidate_sha256s", []),
                    "causes": _system1.get("causes", []),
                }
            )
            report["result"] = "verification_unavailable"
            print(
                "  configured candidate verification unavailable; "
                "ending this attempt without changing search mode",
                flush=True,
            )
            break
        _system1_gate_payload = _system1.get("gate_payload")
        if isinstance(_system1_gate_payload, dict) and _system1_gate_payload:
            try:
                _surface_receipt = _apply_current_gate_consequences(
                    project, _system1_gate_payload
                )
                _surface_actions = _surface_receipt.get("actions") or []
                if _surface_actions:
                    print(
                        "  stale-surface producer applied current gate consequences: "
                        f"{len(_surface_actions)} action(s)",
                        flush=True,
                    )
            except Exception as _surface_err:  # noqa: BLE001
                print(
                    "  stale-surface producer unavailable: "
                    f"{type(_surface_err).__name__}: {_surface_err}",
                    flush=True,
                )
        # SPRINT HOT PATH (mode sprint|hybrid): zero-token act-learn rounds.
        # Governance runs as a CHECKPOINT (on catalog ceiling, or every Nth
        # cycle in hybrid) — the throughput fix, with every guarantee intact.
        if (
            cfg["mode"] in ("sprint", "hybrid", "advice")
            and _system1_status == "none"
        ):
            sp_adapter = ArcAgi3Adapter(game_id)
            sp_adapter.reset()
            print(f"\n===== CYCLE {cyc}/{cycles}: SPRINT (zero-token act-learn) =====",
                  flush=True)
            # The sprint (abduce -> play -> re-abduce) is an OPTIMIZATION, never a
            # blocker — same contract as the governed-path abduce guard below. It
            # was previously UNPROTECTED: an abduce failure (or the process being
            # reaped mid-abduce under memory pressure surfacing as an error here)
            # killed the whole loop with no output. Catch, LOG loudly, and degrade
            # to a governed checkpoint so a slow/failed sprint is observable and
            # recoverable rather than a silent death. (Uncatchable SIGKILL/OOM is
            # handled upstream by keeping abduce RSS bounded; see spec_abduction.)
            try:
                with phase("sprint", project / "workspace"):
                    sp = _sprint(project, sp_adapter, cfg, best_progress, best_goal,
                                 champion_model=best_model, game_id=game_id,
                                 goal_edge_fn=best_goal_edge)
            except Exception as _sp_err:  # noqa: BLE001 — sprint is optional, never fatal
                print(f"  ⚠️  sprint failed ({type(_sp_err).__name__}: {_sp_err}) "
                      f"-> degrading to governed checkpoint", flush=True)
                import traceback as _tb
                _tb.print_exc()
                sp = {"rounds": [{"status": "abduction_partial", "error": str(_sp_err)}],
                      "levels": 0, "deepest": 0}
            report["cycles"].append({"cycle": cyc, "sprint": sp})
            if sp.get("task_discharged") is True:
                report["result"] = "beat"
                print(f"  🏆 TASK DISCHARGED (sprint, cycle {cyc})", flush=True)
                break
            hit_ceiling = any(r.get("status") == "abduction_partial" for r in sp["rounds"])
            if cfg["mode"] == "sprint":
                continue
            if advice_only and hit_ceiling:
                report["cycles"].append({"cycle": cyc, "status": "advice_boundary",
                                         "reason": "catalog_ceiling",
                                         "sprint": sp})
                report["result"] = "advice_boundary"
                print("  advice boundary reached: catalog ceiling; governed loop suppressed",
                      flush=True)
                break
            if not hit_ceiling and (cyc % max(int(cfg["governed_checkpoint_every"]), 1)) != 0:
                continue          # hybrid: no ceiling + not a checkpoint -> keep sprinting
            if advice_only:
                report["cycles"].append({"cycle": cyc, "status": "advice_boundary",
                                         "reason": "checkpoint_due",
                                         "sprint": sp})
                report["result"] = "advice_boundary"
                print("  advice boundary reached: checkpoint due; governed loop suppressed",
                      flush=True)
                break
            print("  sprint hit catalog ceiling / checkpoint due -> governed cycle",
                  flush=True)

        # ENGINE ROUTER (hybrid mode): deterministic engine selection from receipts.
        # Kill-switch: ZTARE_ENGINE_ROUTER=0 → unconditional governed-loop (old behavior).
        import os as _os_er
        _er_active = (cfg["mode"] == "hybrid"
                      and not advice_only
                      and _system1_status == "none"
                      and _os_er.environ.get("ZTARE_ENGINE_ROUTER", "1") != "0")
        if _er_active:
            try:
                from ztare.worldmodel.engine_router import decide as _er_decide, execute as _er_execute
                with phase("engine_router", project / "workspace"):
                    _er_state, _er_decision = _er_decide(project)
                print(f"  [engine_router] {_er_decision['engine']}"
                      + (f"/{_er_decision['phase']}" if _er_decision.get("phase") else "")
                      + f": {_er_decision['reason']}", flush=True)
                _er_engine = _er_decision["engine"]
                # FIX C: open_world_brief receipt → log instruction so governed pass
                # sees the class-escape mandate before running autoresearch.
                if _er_engine == "autoresearch" and _er_decision.get("phase") == "open_world":
                    try:
                        _brief_path = project / "workspace" / "open_world_brief.jsonl"
                        if _brief_path.exists():
                            _brief_lines = [l for l in _brief_path.read_text(encoding="utf-8").splitlines() if l.strip()]
                            if _brief_lines:
                                _brief_row = json.loads(_brief_lines[-1])
                                _brief_instruction = _brief_row.get("instruction", "")
                                if _brief_instruction:
                                    print(f"  [open_world_brief] {_brief_instruction}", flush=True)
                                    # ponytail: write to well-known path the governed briefing reads
                                    _active_brief = project / "workspace" / "active_open_world_brief.json"
                                    _active_brief.write_text(
                                        json.dumps(_brief_row, sort_keys=True) + "\n",
                                        encoding="utf-8"
                                    )
                    except Exception:  # noqa: BLE001 — brief read must never block play
                        pass
                if _er_engine != "autoresearch":
                    # Non-autoresearch branch: execute and record, then continue outer loop
                    with phase(f"engine_router.{_er_engine}", project / "workspace"):
                        _er_result = _er_execute(_er_decision, project)
                    report["cycles"].append({
                        "cycle": cyc,
                        "engine_router": {
                            "engine": _er_engine,
                            "phase": _er_decision.get("phase"),
                            "reason": _er_decision["reason"],
                            "signals": _er_state,
                            "result_keys": list((_er_result or {}).keys()),
                        },
                        "sprint": sp,
                    })
                    continue   # skip governed-loop path for this cycle
                # autoresearch → fall through to existing governed-loop path unchanged
            except Exception as _er_err:  # noqa: BLE001 — router must never block play
                print(f"  [engine_router] error (falling through to governed): "
                      f"{type(_er_err).__name__}: {_er_err}", flush=True)

        # STEP 0 — spec abduction: try to identify the law deterministically
        # from diffs (zero model calls) before spending any mutator tokens.
        # Abduction proposes; the SAME gates verify; the mutator is the
        # fallback for what the catalog cannot express.
        rc = None
        candidate, cand_progress, cand_goal, cand_goal_edge, candidate_path, abduced = (
            None, None, None, None, None, False
        )
        configured_residual_frontier = False
        acquisition_only = False
        acquisition_obligation = None
        strategy_pending = _has_open_strategy_cards(project)
        if strategy_pending and not advice_only:
            print("  open strategy card present -> deterministic abduction still runs; "
                  "governed worker consumes briefing only if gates do not close", flush=True)
        # Narrow, already-compiled System-1 organs get first refusal. This is a
        # search-allocation decision only: their outputs still traverse the
        # project harness and candidate pool before use.
        try:
            if _system1.get("status") == "accepted":
                candidate = _system1["model"]
                chosen = _system1["chosen"]
                source = _system1["source"]
                candidate_path = chosen.proposal.candidate_path
                abduced = True
                from ztare.worldmodel.candidate_pool import add_candidate
                add_candidate(
                    project,
                    source,
                    carrier="deterministic_compiler",
                    origin=chosen.proposal.producer_id,
                )
                print(
                    f"\n===== CYCLE {cyc}/{cycles}: deterministic compiler "
                    f"candidate passed project gates "
                    f"({chosen.proposal.candidate_sha256[:16]}) =====",
                    flush=True,
                )
            elif _system1.get("status") == "cached_survivor_current":
                candidate = _system1["model"]
                source = _system1["source"]
                candidate_path = project / _system1["source_ref"]
                abduced = True
                from ztare.worldmodel.candidate_pool import add_candidate

                add_candidate(
                    project,
                    source,
                    carrier="candidate_memory",
                    origin=_system1["producer_id"],
                )
                print(
                    f"\n===== CYCLE {cyc}/{cycles}: current-epoch cached "
                    f"survivor reused ({_system1['candidate_sha256'][:16]}); "
                    "no mutation dispatched =====",
                    flush=True,
                )
            elif _system1.get("status") == "incumbent_current":
                best_model = _system1["model"]
                best_model_path = project / "test_model.py"
                abduced = True
                print(
                    f"\n===== CYCLE {cyc}/{cycles}: incumbent carrier covers "
                    f"the current evidence epoch "
                    f"({_system1['candidate_sha256'][:16]}); mutation abstained =====",
                    flush=True,
                )
            elif _system1.get("status") == "residual_frontier":
                configured_residual_frontier = True
                # Baseline materialization creates the current-epoch repair
                # task.  Do it before asking for an acquisition obligation so
                # the deterministic receipt-family executor can consume that
                # task in this cycle instead of forcing an LLM round merely to
                # make the task visible.
                _materialize_governed_baseline(
                    project,
                    source=_system1["source"],
                    source_ref=_system1["source_ref"],
                    candidate_sha256=_system1["candidate_sha256"],
                    producer_id=_system1["producer_id"],
                )
                try:
                    from ztare.worldmodel.compiled_fiber_planning import (
                        operation_recurrence_acquisition_obligation,
                    )

                    acquisition_obligation = (
                        operation_recurrence_acquisition_obligation(
                        project,
                        materialize=True,
                        )
                    )
                except Exception as _acquisition_err:  # noqa: BLE001
                    acquisition_obligation = None
                    print(
                        "  operation-acquisition obligation unavailable: "
                        f"{type(_acquisition_err).__name__}: {_acquisition_err}",
                        flush=True,
                    )
                if acquisition_obligation is not None:
                    candidate = load_carrier_from_source(
                        _system1["source"],
                        _system1["source_ref"],
                        project,
                    )
                    candidate_path = project / _system1["source_ref"]
                    abduced = True
                    acquisition_only = True
                print(
                    "  deterministic compiler supplied a localized residual "
                    f"frontier ({_system1['candidate_sha256'][:16]}); "
                    + (
                        "routing its typed recurrence obligation to live discrimination"
                        if acquisition_only
                        else "routing to governed repair without raw-bank re-abduction"
                    ),
                    flush=True,
                )
        except Exception as _producer_err:  # noqa: BLE001
            report["cycles"].append(
                {
                    "cycle": cyc,
                    "status": "configured_producer_unavailable",
                    "cause": f"{type(_producer_err).__name__}: {_producer_err}",
                }
            )
            report["result"] = "configured_producer_unavailable"
            print(
                "  configured candidate producer unavailable; ending this attempt: "
                f"{type(_producer_err).__name__}: {_producer_err}",
                flush=True,
            )
            break
        try:
            if abduced:
                raise _ConfiguredCandidateReady
            if not configured_residual_frontier:
                import os as _os
                from ztare.worldmodel.spec_abduction import abduce_spec
                from ztare.worldmodel.gates import rollout_depth as _rd
                _log = EpisodeLog.read_jsonl(episode_log_path(project))
                _hold = EpisodeLog.read_jsonl(episode_log_path(project, episode=2))
                _champion_prior = _load_prior_spec(project)
                _prior = (
                    _champion_prior.get("spec")
                    if isinstance(_champion_prior, dict) and _champion_prior.get("verdict") == "loaded"
                    else _load_abduced_core_spec(project)
                )
                _warm_only = (
                    isinstance(_champion_prior, dict) and _champion_prior.get("verdict") == "loaded"
                    and _os.environ.get("ZTARE_CHECKPOINT_FULL_ABDUCE", "0") != "1"
                )
                _ab = abduce_spec(_log, _log_arity(_log), prior_spec=_prior,
                                  warm_only=_warm_only)
                _bp = _write_worldmodel_blueprint(project, _log, getattr(_ab, "spec", None))
                try:
                    _bp_sha = json.loads(
                        (project / "workspace" / "worldmodel_lean_feedback_receipt.json").read_text()
                    ).get("blueprint_sha256")
                except Exception:  # noqa: BLE001
                    _bp_sha = None
                _lean_feedback_checkpoint(project, _bp, _bp_sha)
                if _ab.replay_ok and _ab.step_fn is not None \
                        and _rd(_ab.step_fn, _hold) >= len(_hold):
                    candidate, abduced = _ab.step_fn, True
                    _record_spec_receipt(project, _ab.spec, cyc)
                    from ztare.worldmodel.candidate_pool import add_candidate
                    _spec_source = "WORLD_MODEL_SPEC = " + repr(_ab.spec) + "\n"
                    add_candidate(project, _spec_source,
                                  carrier="spec", origin=f"abduction_cycle_{cyc}")
                    from ztare.worldmodel.patch_base_carrier import (
                        materialize_immutable_patch_base,
                    )
                    _spec_ref, _spec_sha = materialize_immutable_patch_base(
                        project,
                        _spec_source,
                        prefix="abduced_carrier",
                    )
                    candidate_path = project / _spec_ref
                    print(f"\n===== CYCLE {cyc}/{cycles}: law ABDUCED from diffs "
                          f"(zero model calls; replay+holdout pass) =====", flush=True)
                elif _warm_only and _ab.status == "prior_refuted":
                    print("  checkpoint champion refuted; full re-abduction skipped "
                          "(set ZTARE_CHECKPOINT_FULL_ABDUCE=1 to force it)",
                          flush=True)
        except _ConfiguredCandidateReady:
            pass
        except Exception as _ab_err:  # noqa: BLE001 — abduction is an optimization, never a blocker
            print(f"  abduction step-0 error (falling through to mutator): {_ab_err}", flush=True)

        # Transition identification and task-hypothesis induction are separate
        # version spaces.  An exact carrier must not suppress the generative
        # worker when the task-hypothesis language has no current presentation.
        _task_goal_generation = False
        _preserved_transition_candidate = None
        _candidate_goal_projection = None
        _goal_source_epoch = None
        try:
            from ztare.worldmodel.strategy_battery import WorldmodelBattery

            _goal_pressure = WorldmodelBattery().run_audits(project).get(
                "goal_hypothesis_pressure"
            ) or {}
            _goal_source_epoch = _goal_pressure.get("active_epoch")
            _candidate_goal_projection = _candidate_task_hypotheses(
                project,
                source_epoch=_goal_source_epoch,
                task_contract=task_contract,
            )
            if (
                abduced
                and not configured_residual_frontier
                and not acquisition_only
                and not advice_only
                and task_contract is not None
                and _goal_pressure.get("status") in {
                    "version_space_empty",
                    "version_space_stalled",
                }
                and int(
                    getattr(_candidate_goal_projection, "active_count", 0) or 0
                ) == 0
            ):
                _preserved_transition_candidate = (
                    candidate,
                    cand_progress,
                    cand_goal,
                    candidate_path,
                )
                _task_goal_generation = True
                abduced = False
                print(
                    "  task-hypothesis version space requires refinement; preserving the "
                    "transition carrier and routing a hypothesis-only governed turn",
                    flush=True,
                )
        except Exception as _goal_pressure_err:  # noqa: BLE001
            print(
                "  task-hypothesis pressure unavailable: "
                f"{type(_goal_pressure_err).__name__}: {_goal_pressure_err}",
                flush=True,
            )

        _governed_adopted = False
        _new_governed_submission_paths = ()
        if not abduced and advice_only:
            candidate, cand_progress, cand_goal, _advice_source = _load_advice_model(project)
            if candidate is None:
                report["cycles"].append({"cycle": cyc, "status": "advice_boundary",
                                         "reason": "no_gate_passing_advice"})
                report["result"] = "advice_boundary"
                print("  advice boundary reached: no gate-passing advice model",
                      flush=True)
                break
            print(f"  advice fallback model loaded: {_advice_source}", flush=True)
        elif not abduced:
            print(f"\n===== CYCLE {cyc}/{cycles}: governed identification =====", flush=True)
            _adoption_cursor = _governed_adoption_cursor(project)
            _submissions_dir = project / "workspace" / "submissions"
            _submissions_before = set(_submissions_dir.glob("*.py"))
            with phase("governed_loop", project / "workspace"):
                rc = _run_governed_cycle(
                    slug,
                    rubric,
                    iters,
                    "gpt5.5",
                    "gpt5.5",
                    turn_focus=(
                        "task_hypothesis" if _task_goal_generation else ""
                    ),
                )
            _new_governed_submission_paths = tuple(
                sorted(
                    set(_submissions_dir.glob("*.py")) - _submissions_before,
                    key=lambda path: path.name,
                )
            )
            _adoption = _governed_adoption_since(project, _adoption_cursor)
            _append_play_receipt(
                project,
                {"site": "arc3_play_loop.py:governed_adoption", **_adoption},
            )
            _governed_adopted = bool(_adoption["adopted"])
            if _adoption["adopted"]:
                candidate, cand_progress, cand_goal = _load_ratified_model(project)
                _adopted_ref = str(_adoption.get("immutable_source_ref") or "")
                candidate_path = (
                    project / _adopted_ref
                    if _adopted_ref
                    else project / "test_model.py"
                )
            else:
                candidate, cand_progress, cand_goal = None, None, None
                print(
                    "  governed cycle produced no current-run promoted candidate; "
                    + (
                        "checking its task-hypothesis projection independently"
                        if _task_goal_generation
                        else "preserving the unresolved identification state"
                    ),
                    flush=True,
                )
            if candidate is not None and _adoption["adopted"]:
                from ztare.worldmodel.candidate_pool import add_candidate
                add_candidate(project, (project / "test_model.py").read_text(),
                              carrier="mutator", origin=f"governed_cycle_{cyc}")

        if _task_goal_generation and not _governed_adopted:
            (
                candidate,
                cand_progress,
                cand_goal,
                candidate_path,
            ) = _preserved_transition_candidate
        if task_contract is not None and _goal_source_epoch is not None:
            _candidate_goal_projection = _candidate_task_hypotheses(
                project,
                source_epoch=_goal_source_epoch,
                task_contract=task_contract,
                candidate_paths=(
                    _new_governed_submission_paths
                    if _task_goal_generation
                    else ()
                ),
            )
        if _candidate_goal_projection is not None:
            if candidate is not None:
                cand_goal = _candidate_goal_projection
            else:
                best_goal = _candidate_goal_projection
            print(
                "  current-epoch leaf task hypotheses admitted for steering "
                f"({_candidate_goal_projection.active_count} candidate(s)); "
                "transition-carrier promotion remains separate",
                flush=True,
            )

        # Determine the active lifecycle before selecting any goal consumer.
        # Previously a witness from an older epoch suppressed structural
        # acquisition and was only scoped away after that decision.
        adapter = ArcAgi3Adapter(game_id)
        adapter.reset()
        (
            seed_replay,
            seed_transitions,
        ) = _replay_latest_level_boundary_seed_trace(project, adapter)
        seed_prefix = list(seed_replay.get("actions") or [])
        seed_segments = list(seed_replay.get("execution_segments") or [])
        active_epoch = int(getattr(adapter, "levels_completed", 0) or 0)
        if hasattr(cand_goal, "for_source_epoch"):
            cand_goal = cand_goal.for_source_epoch(active_epoch)
        if hasattr(best_goal, "for_source_epoch"):
            best_goal = best_goal.for_source_epoch(active_epoch)
        if hasattr(cand_goal_edge, "for_source_epoch"):
            cand_goal_edge = cand_goal_edge.for_source_epoch(active_epoch)
        if hasattr(best_goal_edge, "for_source_epoch"):
            best_goal_edge = best_goal_edge.for_source_epoch(active_epoch)

        # Goal abduction is a separate identity from transition-law abduction.
        # Any gate-passing carrier may consume a goal predicate induced from the
        # bank; the carrier producer must not smuggle a route or goal into its
        # source. This also keeps deterministic compiler candidates on the same
        # planning path as catalog and governed candidates.
        goal_carrier = candidate if candidate is not None else best_model
        goal_is_candidate = candidate is not None
        current_goal = cand_goal if goal_is_candidate else best_goal
        if goal_carrier is not None and not acquisition_only:
            try:
                from types import SimpleNamespace as _SimpleNamespace
                from ztare.worldmodel.goal_abduction import (
                    authoritative_goal_edge_predicate,
                    compose_goal_hypothesis_sets,
                )

                _goal_log = EpisodeLog.read_jsonl(episode_log_path(project))
                cand_goal_edge, _goal_edge_count = authoritative_goal_edge_predicate(
                    _goal_log,
                    source_epoch=active_epoch,
                )
                _goal_ab = locals().get("_ab")
                if _goal_ab is None or getattr(_goal_ab, "spec", None) is None:
                    _goal_carrier_path = (
                        candidate_path if goal_is_candidate else best_model_path
                    )
                    _goal_spec = None
                    if _goal_carrier_path is not None:
                        from ztare.worldmodel.patch_base_carrier import (
                            composed_literal_operator_spec,
                        )

                        _goal_spec = composed_literal_operator_spec(
                            _goal_carrier_path,
                            project_dir=project,
                        )
                    _goal_ab = _SimpleNamespace(spec=_goal_spec)
                if cand_goal_edge is None:
                    induced_goal, _goal_candidate_count = _structural_goal_fn(
                        project,
                        _goal_log,
                        _goal_ab,
                        source_epoch=active_epoch,
                        task_contract_sha256=(
                            task_contract.sha256 if task_contract else ""
                        ),
                    )
                else:
                    induced_goal = None
                    _goal_candidate_count = _goal_edge_count
                composed_goal = compose_goal_hypothesis_sets(
                    current_goal,
                    induced_goal,
                ) if induced_goal is not None else current_goal
                if goal_is_candidate:
                    cand_goal = composed_goal
                else:
                    best_goal = composed_goal
                    best_goal_edge = cand_goal_edge
                if cand_goal_edge is not None:
                    print(
                        "  environment goal-edge predicate induced independently "
                        f"of carrier ({_goal_edge_count} witnesses)",
                        flush=True,
                    )
                elif composed_goal is not None:
                    print(
                        "  task-hypothesis producers composed independently of "
                        "the transition carrier "
                        f"({getattr(composed_goal, 'active_count', _goal_candidate_count)} "
                        "active identities)",
                        flush=True,
                    )
            except Exception as _goal_err:  # noqa: BLE001
                print(f"  structural goal induction skipped: {_goal_err}", flush=True)

        # Evaluate the candidate by PLAY DEPTH (the beat metric), and always play
        # the best model we hold so exploration continues from real strength.
        if candidate is not None:
            play_model, play_progress, play_goal, play_goal_edge = (
                candidate, cand_progress, cand_goal, cand_goal_edge
            )
        else:
            play_model, play_progress, play_goal, play_goal_edge = (
                best_model, best_progress, best_goal, best_goal_edge
            )
        play_carrier_path = candidate_path if play_model is candidate else best_model_path
        if hasattr(play_goal_edge, "for_source_epoch"):
            play_goal_edge = play_goal_edge.for_source_epoch(active_epoch)
        if hasattr(acquisition_obligation, "for_source_epoch"):
            acquisition_obligation = (
                acquisition_obligation.for_source_epoch(active_epoch)
            )
        if play_model is None:
            _existing_log = EpisodeLog.read_jsonl(episode_log_path(project))
            if len(_existing_log) > 0:
                # ACQUISITION UNDER UNRESOLVED IDENTIFICATION (AGENTS.md 8a-2):
                # an open residual with banked evidence is not a reason to stop
                # acting. Steering never authors success (the sealed terminal
                # verifier owns it), so play an acquisition leg with the best
                # incumbent carrier instead of abstaining from the environment.
                # This restores the champion-persistence invariant stated above
                # ("always PLAY the deepest-playing model ever found"), which
                # the residual_frontier gate path silently dropped.
                try:
                    from ztare.worldmodel.carrier_loader import (
                        load_carrier_path,
                        project_dynamics_assumption,
                    )
                    _inc = load_carrier_path(
                        project / "test_model.py",
                        project_dir=project,
                        dynamics_assumption=project_dynamics_assumption(project),
                    )
                    play_model = _inc[0]
                    play_carrier_path = project / "test_model.py"
                    report["cycles"].append({
                        "cycle": cyc,
                        "status": "acquisition_with_unresolved_identification",
                        "transitions_available": len(_existing_log),
                        "loop_rc": rc,
                    })
                    print(
                        "  identification unresolved -> ACQUISITION leg with "
                        "incumbent carrier (steering-only, no promotion "
                        "authority)",
                        flush=True,
                    )
                except Exception as _inc_exc:  # noqa: BLE001
                    report["cycles"].append({
                        "cycle": cyc,
                        "status": "identification_unresolved",
                        "transitions_available": len(_existing_log),
                        "incumbent_lowering_error": str(_inc_exc)[:200],
                        "loop_rc": rc,
                    })
                    print(
                        "  no promoted model and incumbent failed to lower; "
                        "existing evidence is preserved without spending "
                        "environment actions",
                        flush=True,
                    )
                    continue
            if play_model is None and len(_existing_log) > 0:
                continue
        if play_model is None:
            grew = _bootstrap_explore(project, adapter, cfg)
            report["cycles"].append({"cycle": cyc, "status": "bootstrap_exploration",
                                     "transitions_added": grew, "loop_rc": rc})
            print(f"  no ratified model yet -> BOOTSTRAP EXPLORATION "
                  f"(cold-start): +{grew} transitions gathered; continuing", flush=True)
            continue
        # LOOP-LEVEL COMMITTEE: if multiple pooled candidates still survive the
        # log, spend a few live steps on their maximum-disagreement frontier —
        # the cheapest experiment that kills the most hypotheses — before
        # exploiting. (The seam's disagreement-frontier contract, multi-step.)
        try:
            from ztare.worldmodel.candidate_pool import surviving_committee
            from ztare.worldmodel.planner import plan_disagreement
            _log_now = EpisodeLog.read_jsonl(episode_log_path(project))
            committee = surviving_committee(project, _log_now)
            prelude_actions = []
            prelude_transitions = []
            if len(committee) >= 2:
                dplan = plan_disagreement(committee, adapter.state,
                                          adapter.action_arity, start_step=adapter.t)
                if dplan and dplan.actions:
                    print(f"  committee of {len(committee)} survives; probing "
                          f"disagreement frontier: {dplan.actions[:12]}", flush=True)
                    disc = []
                    for a in dplan.actions[:20]:
                        t_now, s_now = adapter.t, adapter.state
                        s2 = adapter.step(a)
                        prelude_actions.append(int(a))
                        disc.append((s_now, a, s2, t_now))
                        prelude_transitions.append(Transition(
                            t=t_now,
                            s=s_now,
                            a=int(a),
                            s_next=s2,
                            identity=getattr(
                                adapter,
                                "last_transition_identity",
                                None,
                            ),
                        ))
                    _grow_evidence(project, disc, adapter)
        except Exception as _dc_err:  # noqa: BLE001 — discrimination is an optimization
            print(f"  committee-discrimination skipped: {_dc_err}", flush=True)
            prelude_actions = []
            prelude_transitions = []

        steer = (
            "operation-discrimination" if acquisition_obligation is not None else
            "goal-edge" if play_goal_edge is not None else
            "goal-cue" if play_goal is not None else
            "progress-cue" if play_progress is not None else
            "novelty"
        )
        print(f"===== CYCLE {cyc}: live play ({steer} steering) =====", flush=True)
        context_log = EpisodeLog.read_jsonl(episode_log_path(project))
        af, visited_path, visited_store = _frontier_memory(
            project,
            context_log,
            source_epoch=active_epoch,
        )
        inherited_goal_refutations = _sealed_goal_hypothesis_refutations(
            project,
            play_goal,
            task_contract=task_contract,
            source_epoch=active_epoch,
            origin_seed_sha256=str(seed_replay.get("seed_sha256") or ""),
            report_payload=previous_report,
        )
        task_hypothesis_version = None
        task_hypothesis_identity = str(
            getattr(play_goal, "identity_sha256", "") or ""
        )
        if task_hypothesis_identity:
            task_hypothesis_version = {
                "identity_sha256": task_hypothesis_identity,
                "active_count": int(
                    getattr(play_goal, "active_count", 0) or 0
                ),
                "source_epoch": active_epoch,
                "task_contract_sha256": (
                    task_contract.sha256 if task_contract else ""
                ),
            }
        if play_carrier_path is None or not play_carrier_path.is_file():
            raise RuntimeError("live trajectory has no immutable source carrier")
        play_carrier_sha256 = hashlib.sha256(
            play_carrier_path.read_bytes()
        ).hexdigest()
        from ztare.worldmodel.patch_base_carrier import (
            carrier_execution_sha256_from_source,
        )

        play_carrier_execution_sha256 = carrier_execution_sha256_from_source(
            play_carrier_path.read_text(encoding="utf-8")
        )
        play_projection = getattr(
            play_model,
            "_ztare_factored_projection",
            None,
        )
        if play_projection is not None:
            from ztare.worldmodel.mechanism_effects import (
                predictive_prefixes_from_transitions,
            )

            (
                active_action_history,
                active_operation_effect_history,
            ) = predictive_prefixes_from_transitions(
                seed_transitions,
                projection=play_projection,
            )
            (
                active_action_history,
                active_operation_effect_history,
            ) = predictive_prefixes_from_transitions(
                prelude_transitions,
                projection=play_projection,
                action_prefix=active_action_history,
                operation_effect_prefix=active_operation_effect_history,
            )
        else:
            active_action_history = tuple((*seed_prefix, *prelude_actions))
            active_operation_effect_history = ()
        coverage_projection = _coverage_fn(
            project,
            context_log,
            source_epoch=active_epoch,
        )
        (
            prior_edge_exclusion,
            prior_edge_exclusion_count,
            prior_edge_slice_refs,
        ) = (
            _sealed_non_discharge_edge_predicate(
                project,
                source_carrier_sha256=play_carrier_sha256,
                source_carrier_execution_sha256=(
                play_carrier_execution_sha256
                ),
                task_contract_sha256=(task_contract.sha256 if task_contract else ""),
                report_payload=previous_report,
                abstract_fn=af,
                coverage_fn=coverage_projection,
                fallback_operation_effect_prefix=(
                    active_operation_effect_history
                ),
                source_epoch=active_epoch,
                origin_seed_sha256=str(
                    seed_replay.get("seed_sha256") or ""
                ),
                transition_evidence=context_log,
            )
        )
        with phase("live_play", project / "workspace"):
            pr = _play_round_multilife(
                adapter,
                play_model,
                budget=250,
                context_log=context_log,
                task_contract=task_contract,
                goal_fn=play_goal,
                goal_edge_fn=play_goal_edge,
                acquisition_obligation=acquisition_obligation,
                excluded_edge_fn=prior_edge_exclusion,
                progress_fn=(
                    play_progress
                    if play_goal is None
                    and play_goal_edge is None
                    and acquisition_obligation is None
                    else None
                ),
                resource_colors=_resource_colors(
                    project,
                    context_log,
                    source_epoch=active_epoch,
                ),
                invariants=_invariants(project, play_model), abstract_fn=af,
                coverage_fn=coverage_projection,
                visited_store=visited_store, visited_path=visited_path,
                carrier_execution_sha256=play_carrier_execution_sha256,
                control_history_prefix=active_action_history,
                control_operation_effect_history_prefix=(
                    active_operation_effect_history
                ),
                plan_depth=10, max_replans=12,
                receipts_dir=project / "workspace")
        # Truthful provenance: a governed cycle that exited rc!=0 leaves a STALE
        # test_model.py on disk; "candidate" would launder it as fresh output.
        played = (
            "provisional_acquisition_frontier"
            if acquisition_only
            else "candidate" if play_model is candidate else "prior_champion"
        )
        if rc not in (None, 0) and play_model is candidate:
            played = "stale_champion_after_failed_cycle"
        cycle_execution_segments = [*seed_segments]
        if prelude_actions:
            cycle_execution_segments.append({
                "segment_kind": "disagreement_acquisition",
                "source_ref": "candidate_pool:surviving_committee",
                "authority": "live_environment_execution",
                "actions": list(prelude_actions),
            })
        cycle_execution_segments.append({
            "segment_kind": "active_control",
            "source_ref": "arc3_play_loop:pursue_goal",
            "authority": "live_environment_execution",
            "actions": list(getattr(pr, "trace", []) or []),
        })
        entry = {"cycle": cyc, "pursuit": pr.status, "steps": pr.steps_executed,
                 "levels_gained": pr.levels_gained, "observed": len(pr.observed_transitions),
                 "planner_detail": getattr(pr, "detail", ""),
                 "planner_saturated": bool(getattr(pr, "saturated", False)),
                 "planning_outcome": getattr(pr, "planning_outcome", {}),
                 "planning_legs": getattr(pr, "leg_outcomes", []),
                 "lives": int(getattr(pr, "lives", 1) or 1),
                 "played": played,
                 "loop_rc": rc,
                 "transition_model_mismatch": _transition_model_mismatch(pr),
                 "terminal_verifier_model_mismatch": _terminal_model_mismatch(pr),
                 "terminal_witness_sha": _terminal_witness_sha(pr),
                 "kernel_role_bindings": _kernel_role_bindings(pr),
                 "task_contract": getattr(pr, "task_contract", None),
                 "prior_non_discharge_edges_excluded": prior_edge_exclusion_count,
                 "non_discharge_edge_indices": list(
                     getattr(pr, "non_discharge_edge_indices", ()) or ()
                 ),
                 "non_discharge_projection_count": int(
                     getattr(pr, "non_discharge_projection_count", 0) or 0
                 ),
                 "prior_goal_hypotheses_refuted": list(inherited_goal_refutations),
                 "task_hypothesis_version": task_hypothesis_version,
                 "task_discharge_receipt": getattr(pr, "task_discharge_receipt", None),
                 "seed_replay": {
                     key: value for key, value in seed_replay.items() if key != "actions"
                 },
                 "execution_segments": cycle_execution_segments,
                 "task_discharged": bool(getattr(pr, "task_discharged", False))}
        if entry["task_discharged"]:
            entry["status"] = "TASK_DISCHARGED"
        if pr.levels_gained > 0 and entry["task_discharged"]:
            completed_level = int(getattr(adapter, "levels_completed", 0) or pr.levels_gained)
            seed = _write_level_boundary_seed(
                project,
                game_id=game_id,
                cycle=cyc,
                completed_level=completed_level,
                actions=(
                    seed_prefix
                    + list(prelude_actions)
                    + list(getattr(pr, "trace", []) or [])
                ),
                execution_segments=cycle_execution_segments,
            )
            entry["level_boundary_seed"] = {
                "target_level": seed["target_level"],
                "sequence_len": seed["sequence_len"],
                "source_ref": f"workspace/level{seed['target_level']}_seed.json",
            }
            # GOAL EXEMPLAR: the transition that triggered the terminal verifier is
            # a labeled example of the goal predicate — abduction fuel for
            # goal-directed planning in the source lifecycle. Cross-epoch use
            # requires a separately certified transport.
            if pr.observed_transitions:
                _write_goal_exemplar(
                    project,
                    pr.observed_transitions[-1],
                    cycle=cyc,
                    game_id=game_id,
                    task_contract=task_contract,
                )
        if entry["task_discharged"]:
            report["cycles"].append(entry)
            report["result"] = "beat"
            try:
                from ztare.worldmodel.search_control_repair import (
                    disposition_search_control_cards_from_report as _close_strategy_cards,
                )
                dispositions = _close_strategy_cards(project, report)
                if dispositions:
                    entry["strategy_card_dispositions"] = [
                        {
                            "kind": d.get("kind"),
                            "failure_family_sha": d.get("failure_family_sha"),
                            "disposition": d.get("disposition"),
                            "discharge": d.get("discharge"),
                        }
                        for d in dispositions
                    ]
            except Exception as _strategy_close_err:  # noqa: BLE001
                print(f"  strategy-card disposition skipped: {_strategy_close_err}", flush=True)
            print(f"  🏆 TASK DISCHARGED in cycle {cyc} "
                  f"({pr.steps_executed} steps, {pr.levels_gained} level gains)",
                  flush=True)
            break
        if pr.levels_gained > 0:
            entry["status"] = "TASK_PROGRESS"
            print(
                f"  environment progress +{pr.levels_gained}; task contract remains open",
                flush=True,
            )
        # promote the candidate to champion only if it plays DEEPER (beat metric)
        if (
            pr.steps_executed > best_depth
            and play_model is candidate
            and not acquisition_only
        ):
            best_depth, best_model, best_progress, best_goal, best_goal_edge = \
                pr.steps_executed, candidate, cand_progress, cand_goal, cand_goal_edge
            best_model_path = play_carrier_path
            entry["champion_updated"] = True
        grown = _grow_evidence(
            project, pr.observed_transitions, adapter, log=context_log
        )
        entry["evidence_grown_by"] = grown
        entry["kernel_role_bindings"].extend(
            _planner_attention_bindings(
                pr, goal_fn=play_goal, goal_edge_fn=play_goal_edge,
                progress_fn=play_progress,
                evidence_grown_by=grown))
        if pr.observed_transitions:
            _trajectory = _observation_log(pr.observed_transitions)
            _slice_row = archive_sealed_eval_slice(
                project,
                _trajectory,
                source_carrier_sha256=play_carrier_sha256,
                source_carrier_execution_sha256=(
                    play_carrier_execution_sha256
                ),
                task_contract=task_contract,
                task_discharge_receipt=getattr(pr, "task_discharge_receipt", None),
                search_control_predecessors=prior_edge_slice_refs,
                source_epoch=active_epoch,
                origin_seed_sha256=str(seed_replay.get("seed_sha256") or ""),
                goal_hypothesis_refutations=(
                    tuple(sorted(getattr(play_goal, "refuted_ids", ()) or ()))
                ),
                non_discharge_edge_indices=tuple(
                    getattr(pr, "non_discharge_edge_indices", ()) or ()
                ),
                history_prefix_actions=active_action_history,
                history_prefix_operation_effects=(
                    active_operation_effect_history
                ),
            )
            entry["eval_slice"] = {"path": _slice_row["path"], "sha256": _slice_row["sha256"]}
        entry["best_depth"] = best_depth
        report["cycles"].append(entry)
        previous_report = report
        office = _maybe_convene_strategy_office(project, cfg, report,
                                                cycle=cyc, entry=entry)
        if office.get("enabled") or office.get("deterministic_cards_written"):
            entry["strategy_office"] = office
        unchanged_survivor = (
            grown == 0
            and _system1_status in {"cached_survivor_current", "incumbent_current"}
        )
        print(f"  no level; depth {pr.steps_executed} (best {best_depth}); grew evidence "
              f"by {grown} ({pr.status})", flush=True)
        if unchanged_survivor:
            entry["reseal_gate"] = {
                "status": "unchanged_identity_skipped",
                "reason": "current carrier and evidence epoch are unchanged",
            }
            continue
        # Appending evidence advances one project lifecycle; it does not create
        # a new project.  The full ``make seal`` door repeats rubric review and
        # runs the gate harness twice before the candidate-specific evaluation
        # below.  Validate only the changed evidence/leak membrane here, then
        # let the single candidate gate provide the integration attestation.
        with phase("reseal_preflight", project / "workspace"):
            seal_checks = [[
                sys.executable,
                str(REPO / "scripts" / "validate_evidence.py"),
                slug,
                "--rubric",
                str(REPO / rubric),
            ]]
            denylist = project / ".denylist"
            if denylist.is_file():
                seal_checks.append([
                    sys.executable,
                    "-m",
                    "src.ztare.validator.leak_sentinel",
                    str(project),
                    str(REPO / rubric),
                    "--denylist-file",
                    str(denylist),
                ])
            seal_result = None
            for command in seal_checks:
                result = subprocess.run(
                    command,
                    cwd=REPO,
                    env=_clean_env(),
                    stdout=subprocess.DEVNULL,
                )
                if result.returncode != 0:
                    seal_result = result
                    break
        if seal_result is not None:
            entry["reseal_gate"] = {
                "status": "artifact_seal_failed",
                "returncode": seal_result.returncode,
            }
            report["result"] = "verification_unavailable"
            print("  refreshed evidence failed the artifact seal", flush=True)
            break
        if grown:
            try:
                with phase("reseal_gate", project / "workspace"):
                    if play_carrier_path is None:
                        raise RuntimeError(
                            "live-play carrier has no immutable source identity"
                        )
                    reseal_gate = _gate_candidate_path(project, play_carrier_path)
                if reseal_gate is None:
                    raise RuntimeError("project root has no registered gate harness")
                reseal_payload = reseal_gate["payload"]
                reseal_consumed = reseal_gate["consumed"]
                from ztare.scaffold.write_seal import write_seal

                write_seal(
                    slug,
                    project,
                    REPO / rubric,
                    project / "sandbox_seal.json",
                )
                visible = (
                    (reseal_payload.get("gates") or {}).get("visible_replay_exact")
                    or {}
                )
                diagnostics = (
                    visible.get("diagnostics")
                    if isinstance(visible, dict)
                    and isinstance(visible.get("diagnostics"), dict)
                    else {}
                )
                entry["reseal_gate"] = {
                    "status": (
                        "carrier_covers_current_evidence"
                        if not reseal_consumed["failed_gates"]
                        else "carrier_refuted_on_current_evidence"
                    ),
                    "candidate_sha256": reseal_consumed["candidate_sha256"],
                    "failed_gates": list(reseal_consumed["failed_gates"]),
                    "evidence_epoch": reseal_payload.get("evidence_epoch") or {},
                    "checked_rows": diagnostics.get("checked_rows"),
                    "exact_rows": diagnostics.get("exact_rows"),
                    "wrong_rows": diagnostics.get("wrong_rows"),
                    "wrong_cell_count": diagnostics.get("wrong_cell_count"),
                    "first_mismatch": diagnostics.get("first_mismatch"),
                }
                _apply_current_gate_consequences(project, reseal_payload)
                print(
                    "  current-evidence gate: "
                    f"{entry['reseal_gate']['status']} "
                    f"({entry['reseal_gate']['exact_rows']}/"
                    f"{entry['reseal_gate']['checked_rows']} exact)",
                    flush=True,
                )
            except Exception as reseal_exc:  # noqa: BLE001
                entry["reseal_gate"] = {
                    "status": "verification_unavailable",
                    "cause": f"{type(reseal_exc).__name__}: {reseal_exc}",
                }
                report["result"] = "verification_unavailable"
                print(
                    "  current-evidence verification unavailable: "
                    f"{type(reseal_exc).__name__}: {reseal_exc}",
                    flush=True,
                )
                break

    report.setdefault("result", "no_level_in_budget")
    # Re-run the typed route fence at phase exit.  Entry preflight prevents a
    # stale obstruction; this catches an operational producer that fired during
    # the cycle without its registered consequence.
    try:
        from ztare.orchestrator.trace_auditor import run_audit as _ta_run
        _active, _advisory = _apply_trace_audit_consequence(
            report,
            _ta_run(project),
        )
        print(f"  trace-auditor: {len(_active)} active apparatus anomalies"
              + (f" -> {_active}" if _active else "")
              + f"; {len(_advisory)} catalog advisories", flush=True)
    except Exception as _ta_exc:  # noqa: BLE001
        report["result"] = "operational_route_obstruction"
        print(f"  trace-auditor route fence unavailable: {_ta_exc}", flush=True)
    _write_play_report_and_terminal_audit(project, report)
    try:
        from ztare.worldmodel.p0_metrics import write_p0_metrics as _write_p0
        _write_p0(project)
    except Exception as _p0_exc:  # noqa: BLE001
        print(f"  P0 snapshot error (non-fatal): {_p0_exc}", flush=True)
    print("\n" + json.dumps({k: report[k] for k in ("game", "result")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
