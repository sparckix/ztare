#!/usr/bin/env python3
"""Compose bounded factored searches through their continuation contract."""
from __future__ import annotations

import argparse
import ast
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import budget_anchored_product_state_audit as anchor
import composed_world_resource_state_audit as product
import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint
import mutable_world_object_inventory_audit as world_inventory
import time_guarded_affordance_refinement_audit as time_guarded

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog


MAX_SEGMENTS = 4


def _advance(
    *,
    carrier: Any,
    problem: Any,
    state: Any,
    time_value: int,
    actions: tuple[Any, ...],
) -> tuple[Any, int, dict[str, Any]]:
    start_key = problem.dominance_key_at(state, time_value)
    for step, action in enumerate(actions):
        successor = carrier(state, action, time_value)
        if successor is None:
            return state, time_value, {
                "admissible": False,
                "reason": "missing_successor",
                "step": step,
            }
        if not problem.admissible(successor):
            return state, time_value, {
                "admissible": False,
                "reason": "successor_outside_domain",
                "step": step,
            }
        state = successor
        time_value += 1
    return state, time_value, {
        "admissible": True,
        "action_count": len(actions),
        "start_key_sha256": stable_sha256(start_key),
        "end_key_sha256": stable_sha256(
            problem.dominance_key_at(state, time_value)
        ),
        "end_time": time_value,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--h35-result", required=True)
    parser.add_argument("--h38-result", required=True)
    parser.add_argument("--h39-result", required=True)
    parser.add_argument("--h40-result", required=True)
    parser.add_argument("--h42-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_rows = tuple(EpisodeLog.read_jsonl(Path(args.trace).resolve()))
    evidence_rows = tuple(EpisodeLog.read_jsonl(Path(args.evidence).resolve()))
    if not trace_rows or not evidence_rows:
        raise SystemExit("trace/evidence must be nonempty")
    start = trace_rows[0].s
    start_time = int(trace_rows[0].t)
    carrier, _kind, carrier_sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    parent = getattr(carrier, "_ztare_factored_projection", None)
    if parent is None:
        raise SystemExit("carrier has no factored projection")
    inventory_projection = world_inventory.MutableWorldInventoryProjection(
        parent,
        evidence_refs=(str(args.h38_result), str(args.h39_result)),
    )
    inference = anchor._infer_secondary_budget_anchor(
        parent,
        evidence_rows,
    )
    projection = product.SecondaryResourceProjection(
        inventory_projection,
        cells=inference["cells"],
        background=inference["background"],
        evidence_refs=(
            str(Path(args.evidence)),
            str(args.h35_result),
            str(args.h40_result),
        ),
    )

    active_result_path = Path(args.active_result)
    active_result = json.loads(
        active_result_path.read_text(encoding="utf-8")
    )
    joint_result_path = Path(args.joint_result)
    joint_result = json.loads(
        joint_result_path.read_text(encoding="utf-8")
    )
    target = joint._active_target(
        project=project,
        projection=projection,
        active_result=active_result,
    )
    configurations = prior_search._selected_raw_configurations(
        project=project,
        projection=projection,
        joint_result=joint_result,
    )
    if len(configurations) != 1:
        raise SystemExit("selected raw configuration is not unique")
    configuration = configurations[0]
    target_factors = replace(
        projection.factor(target["grid"]),
        finite_configuration=configuration["raw_configuration"],
    )
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]
    problem = time_guarded.TimeGuardedTargetProblem(
        projection=projection,
        target=target_factors,
        terminal_intervention=operation,
        target_evidence_ref=configuration["evidence_refs"][0],
        additional_evidence_refs=(
            target["evidence_ref"],
            str(active_result_path),
            str(joint_result_path),
            str(args.evidence),
        ),
    )

    state = start
    time_value = start_time
    prefix: tuple[Any, ...] = ()
    h42_payload = json.loads(
        Path(args.h42_result).read_text(encoding="utf-8")
    )
    h42_selected = h42_payload["selected_search"]
    identity_bound = bool(
        h42_payload["projection_sha256"] == projection.projection_sha256
        and h42_selected["problem_id"] == problem.problem_id
    )
    if not identity_bound:
        raise SystemExit("H42 projection/problem identity did not reconstruct")
    seed_search = h42_selected["search"]
    if (
        seed_search["status"] != "search_budget_exhausted"
        or seed_search["projection_counterexample"]
        or not seed_search["continuation_actions"]
    ):
        raise SystemExit("H42 selected search is not a consumable first segment")
    seed_actions = tuple(
        ast.literal_eval(action)
        for action in seed_search["continuation_actions"]
    )
    segments = [{
        "segment": 1,
        "start_time": time_value,
        "prefix_length": 0,
        "search": seed_search,
        "source_result": str(args.h42_result),
    }]
    boundary_keys = {
        stable_sha256(problem.dominance_key_at(state, time_value))
    }
    stop_reason = "segment_cap_exhausted"
    final_actions: tuple[Any, ...] = ()
    state, time_value, seed_receipt = _advance(
        carrier=carrier,
        problem=problem,
        state=state,
        time_value=time_value,
        actions=seed_actions,
    )
    segments[0]["continuation_replay"] = seed_receipt
    if not seed_receipt["admissible"]:
        stop_reason = seed_receipt["reason"]
    elif seed_receipt["end_key_sha256"] in boundary_keys:
        stop_reason = "repeated_boundary"
    else:
        boundary_keys.add(seed_receipt["end_key_sha256"])
        prefix = seed_actions

    for segment_index in range(2, MAX_SEGMENTS + 1):
        if stop_reason != "segment_cap_exhausted":
            break
        result = search_factored(
            predict=carrier,
            start=state,
            interventions=prior_search.INTERVENTIONS,
            problem=problem,
            start_time=time_value,
            max_depth=prior_search.MAX_DEPTH,
            max_states=prior_search.MAX_STATES,
        )
        row = {
            "segment": segment_index,
            "start_time": time_value,
            "prefix_length": len(prefix),
            "search": prior_search._result_row(result),
        }
        segments.append(row)
        if result.projection_counterexample:
            stop_reason = "projection_counterexample"
            break
        if result.status == "edge_found":
            final_actions = (*prefix, *result.actions)
            stop_reason = "edge_found"
            break
        if (
            result.status != "search_budget_exhausted"
            or not result.continuation_actions
        ):
            stop_reason = result.status
            break
        next_state, next_time, receipt = _advance(
            carrier=carrier,
            problem=problem,
            state=state,
            time_value=time_value,
            actions=result.continuation_actions,
        )
        row["continuation_replay"] = receipt
        if not receipt["admissible"]:
            stop_reason = receipt["reason"]
            break
        boundary_sha = receipt["end_key_sha256"]
        if boundary_sha in boundary_keys:
            stop_reason = "repeated_boundary"
            break
        boundary_keys.add(boundary_sha)
        prefix = (*prefix, *result.continuation_actions)
        state = next_state
        time_value = next_time

    replay = {}
    if final_actions:
        replay = prior_search._replay(
            carrier=carrier,
            projection=projection,
            start=start,
            start_time=start_time,
            actions=final_actions,
            problem=problem,
            operation_map=operation_map,
        )
    passed = bool(
        stop_reason == "edge_found"
        and final_actions
        and all(
            not row["search"]["projection_counterexample"]
            for row in segments
        )
        and replay.get("admissible")
        and replay.get("goal_edge")
        and replay.get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
    )
    payload = {
        "schema": "ztare-continuation-composed-target-search-audit-v1",
        "status": (
            "continuation_composed_target_search_confirmed"
            if passed
            else "continuation_composed_target_search_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "problem_id": problem.problem_id,
        "h42_identity_bound": identity_bound,
        "bounds": {
            "max_segments": MAX_SEGMENTS,
            "max_depth_per_segment": prior_search.MAX_DEPTH,
            "max_states_per_segment": prior_search.MAX_STATES,
        },
        "stop_reason": stop_reason,
        "segments": segments,
        "boundary_count": len(boundary_keys),
        "full_actions": [repr(action) for action in final_actions],
        "full_action_count": len(final_actions),
        "replay": replay,
        "criteria": {
            "edge_within_cap": stop_reason == "edge_found",
            "h42_identity_bound": identity_bound,
            "no_projection_counterexample": all(
                not row["search"]["projection_counterexample"]
                for row in segments
            ),
            "no_repeated_boundary": stop_reason != "repeated_boundary",
            "full_replay_goal_edge": bool(replay.get("goal_edge")),
            "selected_joint_code": (
                replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
            ),
            "no_environment_contact": True,
        },
        "start_state_sha256": stable_sha256(start),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "stop_reason": stop_reason,
        "criteria": payload["criteria"],
        "segments": [
            {
                "segment": row["segment"],
                "status": row["search"]["status"],
                "generated": row["search"]["generated"],
                "expanded": row["search"]["expanded"],
                "deepest_depth": row["search"]["deepest_depth"],
                "continuation_length": len(
                    row["search"]["continuation_actions"]
                ),
                "prefix_length": row["prefix_length"],
            }
            for row in segments
        ],
        "full_action_count": len(final_actions),
        "replay": replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
