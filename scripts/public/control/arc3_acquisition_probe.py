#!/usr/bin/env python3
"""Run one governed acquisition transaction without candidate identification.

This entry point preserves the normal seed replay, carrier identity, sealed
control exclusions, task adjudicator, evidence admission, and slice archive.
It has no carrier-promotion path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from arc3_play_loop import (
    _adapter_epoch,
    _coverage_fn,
    _frontier_memory,
    _invariants,
    _observation_log,
    _play_config,
    _play_round_multilife,
    _resolve_game_id,
    _sealed_non_discharge_edge_predicate,
    _write_level_boundary_seed,
    archive_sealed_eval_slice,
)
from ztare.common.task_discharge import task_discharge_from_profile
from ztare.substrates.arc_agi3 import ArcAgi3Adapter
from ztare.worldmodel.adapter import (
    episode_log_path,
    grow_evidence,
)
from ztare.worldmodel.carrier_loader import (
    load_carrier_path,
    project_dynamics_assumption,
)
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.level_boundary_seed import replay_latest_seed_trace
from ztare.worldmodel.mechanism_effects import (
    predictive_prefixes_from_transitions,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="ls20")
    parser.add_argument("--budget", type=int, default=32)
    args = parser.parse_args()
    if args.budget <= 0:
        raise SystemExit("--budget must be positive")

    repo = Path(__file__).resolve().parents[3]
    game_id = _resolve_game_id(args.game)
    if game_id is None:
        raise SystemExit(f"game {args.game!r} not found")
    project = repo / "projects" / f"arc3_{str(args.game).split('-', 1)[0]}_gov"
    cfg = _play_config(project)
    task_contract = task_discharge_from_profile(cfg)

    adapter = ArcAgi3Adapter(game_id)
    adapter.reset()
    seed_replay, seed_transitions = replay_latest_seed_trace(project, adapter)
    seed_actions = tuple(seed_replay.get("actions") or ())
    active_epoch = _adapter_epoch(adapter)

    carrier_path = project / "test_model.py"
    carrier_source = carrier_path.read_text(encoding="utf-8")
    carrier, _kind, carrier_sha = load_carrier_path(
        carrier_path,
        project_dir=project,
        dynamics_assumption=project_dynamics_assumption(project),
    )
    carrier_execution_sha = carrier_execution_sha256_from_source(
        carrier_source
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise RuntimeError(
            "acquisition probe requires the accepted factored projection"
        )
    (
        active_action_history,
        active_operation_effect_history,
    ) = predictive_prefixes_from_transitions(
        seed_transitions,
        projection=projection,
    )
    context_log = EpisodeLog.read_jsonl(episode_log_path(project))
    abstract_fn, visited_path, visited_store = _frontier_memory(
        project,
        context_log,
        source_epoch=active_epoch,
    )
    coverage_fn = _coverage_fn(
        project,
        context_log,
        source_epoch=active_epoch,
    )
    try:
        previous_report = json.loads(
            (
                project
                / "workspace"
                / "arc3_play_loop_report.json"
            ).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        previous_report = {}
    if task_contract is not None:
        (
            prior_exclusion,
            prior_exclusion_count,
            prior_slice_refs,
        ) = _sealed_non_discharge_edge_predicate(
            project,
            source_carrier_sha256=carrier_sha,
            source_carrier_execution_sha256=carrier_execution_sha,
            task_contract_sha256=task_contract.sha256,
            report_payload=previous_report,
            abstract_fn=abstract_fn,
            coverage_fn=coverage_fn,
            fallback_operation_effect_prefix=(
                active_operation_effect_history
            ),
            source_epoch=active_epoch,
            origin_seed_sha256=str(
                seed_replay.get("seed_sha256") or ""
            ),
            transition_evidence=context_log,
        )
    else:
        prior_exclusion, prior_exclusion_count, prior_slice_refs = (
            None,
            0,
            [],
        )

    receipt = _play_round_multilife(
        adapter,
        carrier,
        budget=args.budget,
        context_log=context_log,
        task_contract=task_contract,
        excluded_edge_fn=prior_exclusion,
        invariants=_invariants(project, carrier),
        abstract_fn=abstract_fn,
        coverage_fn=coverage_fn,
        visited_store=visited_store,
        visited_path=visited_path,
        carrier_execution_sha256=carrier_execution_sha,
        control_history_prefix=active_action_history,
        control_operation_effect_history_prefix=(
            active_operation_effect_history
        ),
        plan_depth=10,
        max_replans=12,
        receipts_dir=project / "workspace",
    )

    grown = grow_evidence(
        project,
        receipt.observed_transitions,
        adapter,
        log=context_log,
    )
    slice_row = None
    if receipt.observed_transitions:
        slice_row = archive_sealed_eval_slice(
            project,
            _observation_log(receipt.observed_transitions),
            source_carrier_sha256=carrier_sha,
            source_carrier_execution_sha256=carrier_execution_sha,
            task_contract=task_contract,
            task_discharge_receipt=receipt.task_discharge_receipt,
            search_control_predecessors=prior_slice_refs,
            source_epoch=active_epoch,
            origin_seed_sha256=str(
                seed_replay.get("seed_sha256") or ""
            ),
            non_discharge_edge_indices=tuple(
                receipt.non_discharge_edge_indices or ()
            ),
            history_prefix_actions=active_action_history,
            history_prefix_operation_effects=(
                active_operation_effect_history
            ),
        )

    execution_segments = [
        *(seed_replay.get("execution_segments") or ()),
        {
            "segment_kind": "active_control",
            "source_ref": "arc3_acquisition_probe",
            "authority": "live_environment_execution",
            "actions": list(receipt.trace or ()),
        },
    ]
    level_seed = None
    if receipt.task_discharged:
        completed_level = int(getattr(adapter, "levels_completed", 0))
        level_seed = _write_level_boundary_seed(
            project,
            game_id=game_id,
            cycle=0,
            completed_level=completed_level,
            actions=(*seed_actions, *tuple(receipt.trace or ())),
            execution_segments=execution_segments,
        )

    payload = {
        "schema": "ztare-arc3-acquisition-probe-v1",
        "game": game_id,
        "budget": args.budget,
        "status": receipt.status,
        "steps_executed": receipt.steps_executed,
        "levels_gained": receipt.levels_gained,
        "task_discharged": bool(receipt.task_discharged),
        "trace": list(receipt.trace or ()),
        "planning_outcome": receipt.planning_outcome,
        "planning_legs": receipt.leg_outcomes,
        "prior_non_discharge_edges": prior_exclusion_count,
        "new_non_discharge_edge_indices": list(
            receipt.non_discharge_edge_indices or ()
        ),
        "seed_replay": {
            key: value
            for key, value in seed_replay.items()
            if key != "actions"
        },
        "active_action_history_prefix": list(active_action_history),
        "active_operation_effect_history_prefix": [
            list(token) for token in active_operation_effect_history
        ],
        "evidence_grown_by": grown,
        "eval_slice": (
            {
                "path": slice_row["path"],
                "sha256": slice_row["sha256"],
            }
            if slice_row is not None
            else None
        ),
        "carrier_sha256": hashlib.sha256(
            carrier_path.read_bytes()
        ).hexdigest(),
        "carrier_execution_sha256": carrier_execution_sha,
        "task_discharge_receipt": receipt.task_discharge_receipt,
        "level_boundary_seed": (
            {
                "target_level": level_seed["target_level"],
                "sequence_len": level_seed["sequence_len"],
            }
            if level_seed is not None
            else None
        ),
    }
    output = project / "workspace" / "arc3_acquisition_probe_report.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if receipt.status != "apparatus_obstructed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
