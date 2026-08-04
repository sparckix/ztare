#!/usr/bin/env python3
"""Calibrate and search the compiled carrier for a composed joint target."""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import joint_equivariant_affordance_audit as joint
import terminal_affordance_relation_audit as affordance

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.compiled_fiber_planning import CompiledFiberSearchProblem
from ztare.worldmodel.episode_log import EpisodeLog


SELECTED_CONFIGURATION = (
    "4dd96788ba556af49abb6b84a143ff58f4e933b8c8c331159017b9c91d77a000"
)
EXPECTED_JOINT = (
    "c19683438c8aebf80055531bc063ab560e2cd5538de63675345cff4614438072"
)
MAX_DEPTH = 180
MAX_STATES = 20_000
INTERVENTIONS = (0, 1, 2, 3)


def _state_from_ref(
    project: Path,
    ref: str,
    cache: dict[str, tuple[Any, ...]],
) -> Any:
    path_text, location = ref.rsplit("#", 1)
    if ":" in location:
        index_text, side = location.split(":", 1)
    else:
        index_text, side = location, "s"
    rows = cache.get(path_text)
    if rows is None:
        rows = tuple(EpisodeLog.read_jsonl(project / path_text))
        cache[path_text] = rows
    transition = rows[int(index_text)]
    if side not in {"s", "s_next"}:
        raise ValueError(f"unsupported state-ref side: {side}")
    return getattr(transition, side)


def _selected_raw_configurations(
    *,
    project: Path,
    projection: Any,
    joint_result: dict[str, Any],
) -> list[dict[str, Any]]:
    selected_rows = [
        row for row in joint_result["active"]["configurations"]
        if row["configuration_sha256"] == SELECTED_CONFIGURATION
    ]
    if len(selected_rows) != 1:
        raise ValueError(
            f"expected one selected configuration row, found {len(selected_rows)}"
        )
    cache: dict[str, tuple[Any, ...]] = {}
    by_raw: dict[str, dict[str, Any]] = {}
    for ref in selected_rows[0]["evidence_refs"]:
        state = _state_from_ref(project, str(ref), cache)
        factors = projection.factor(state)
        raw = tuple(factors.finite_configuration)
        partition = affordance._configuration_partition(raw)
        if stable_sha256(partition) != SELECTED_CONFIGURATION:
            raise ValueError("selected-configuration evidence ref drifted")
        raw_sha = stable_sha256(raw)
        row = by_raw.setdefault(raw_sha, {
            "raw_sha256": raw_sha,
            "raw_configuration": raw,
            "partition_sha256": SELECTED_CONFIGURATION,
            "evidence_refs": [],
        })
        row["evidence_refs"].append(str(ref))
    return sorted(by_raw.values(), key=lambda row: row["raw_sha256"])


def _problem(
    *,
    projection: Any,
    target: Any,
    operation: Any,
    target_ref: str,
    evidence_refs: tuple[str, ...],
) -> CompiledFiberSearchProblem:
    return CompiledFiberSearchProblem(
        projection=projection,
        target=target,
        terminal_intervention=operation,
        target_evidence_ref=target_ref,
        additional_evidence_refs=evidence_refs,
    )


def _result_row(result: Any) -> dict[str, Any]:
    return {
        "status": result.status,
        "actions": [repr(action) for action in result.actions],
        "action_count": len(result.actions),
        "continuation_actions": [
            repr(action) for action in result.continuation_actions
        ],
        "generated": result.generated,
        "expanded": result.expanded,
        "frontier_remaining": result.frontier_remaining,
        "deepest_depth": result.deepest_depth,
        "projection_counterexample": result.projection_counterexample,
    }


def _replay(
    *,
    carrier: Any,
    projection: Any,
    start: Any,
    start_time: int,
    actions: tuple[Any, ...],
    problem: CompiledFiberSearchProblem,
    operation_map: dict[str, Any],
) -> dict[str, Any]:
    if not actions:
        return {"admissible": False, "reason": "empty_route"}
    state = start
    time_value = start_time
    for step, action in enumerate(actions[:-1]):
        state = carrier(state, action, time_value)
        if state is None:
            return {
                "admissible": False,
                "reason": "missing_predicted_successor",
                "step": step,
            }
        time_value += 1
    terminal_operation = actions[-1]
    factors = projection.factor(state)
    origins = tuple(factors.controlled_base)
    goal_edge = problem.goal_edge(
        state,
        terminal_operation,
        time_value,
    )
    if len(origins) != 1 or not operation_map.get("admitted"):
        return {
            "admissible": False,
            "reason": "terminal_relation_inadmissible",
            "controlled_origin_count": len(origins),
            "goal_edge": goal_edge,
        }
    origin = origins[0]
    delta_row, delta_col = operation_map["vector"]
    attempted = origin[0] + delta_row, origin[1] + delta_col
    height = len(projection.sprite)
    width = len(projection.sprite[0])
    footprint = affordance._window(
        state,
        top=attempted[0],
        left=attempted[1],
        size=max(height, width),
        current_origin=origin,
        sprite_shape=(height, width),
    )
    configuration_values = tuple(factors.finite_configuration)
    configuration = joint._square(configuration_values)
    if configuration is None:
        return {
            "admissible": False,
            "reason": "nonsquare_configuration",
            "goal_edge": goal_edge,
        }
    codes = joint._codes(footprint, configuration)
    configuration_partition = affordance._configuration_partition(
        configuration_values
    )
    return {
        "admissible": True,
        "goal_edge": goal_edge,
        "terminal_operation": repr(terminal_operation),
        "terminal_time": time_value,
        "controlled_base": origins,
        "attempted_origin": attempted,
        "configuration_sha256": stable_sha256(configuration_partition),
        "raw_configuration_sha256": stable_sha256(configuration_values),
        "joint_sha256": codes["joint"]["sha256"],
        "joint_transform": codes["joint"]["transform"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_path = Path(args.trace).resolve()
    trace_rows = tuple(EpisodeLog.read_jsonl(trace_path))
    if not trace_rows:
        raise SystemExit("start trace is empty")
    start = trace_rows[0].s
    start_time = int(trace_rows[0].t)

    carrier, _kind, carrier_sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    active_result_path = Path(args.active_result)
    active_result = json.loads(
        active_result_path.read_text(encoding="utf-8")
    )
    joint_result_path = Path(args.joint_result)
    joint_result = json.loads(
        joint_result_path.read_text(encoding="utf-8")
    )
    if joint_result.get("status") != "joint_equivariant_affordance_confirmed":
        raise SystemExit("H30 result is not confirmed")
    active_target = joint._active_target(
        project=project,
        projection=projection,
        active_result=active_result,
    )
    observed_factors = projection.factor(active_target["grid"])
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]
    known_route = tuple(
        ast.literal_eval(action)
        for action in active_result["matches"][0]["route_actions"]
    )

    positive_problem = _problem(
        projection=projection,
        target=observed_factors,
        operation=operation,
        target_ref=active_target["evidence_ref"],
        evidence_refs=(str(active_result_path),),
    )
    positive_result = search_factored(
        predict=carrier,
        start=start,
        interventions=INTERVENTIONS,
        problem=positive_problem,
        start_time=start_time,
        max_depth=MAX_DEPTH,
        max_states=MAX_STATES,
    )
    positive_replay = _replay(
        carrier=carrier,
        projection=projection,
        start=start,
        start_time=start_time,
        actions=positive_result.actions,
        problem=positive_problem,
        operation_map=operation_map,
    )

    raw_configurations = _selected_raw_configurations(
        project=project,
        projection=projection,
        joint_result=joint_result,
    )
    selected_searches = []
    for configuration in raw_configurations:
        target = replace(
            observed_factors,
            finite_configuration=configuration["raw_configuration"],
        )
        problem = _problem(
            projection=projection,
            target=target,
            operation=operation,
            target_ref=configuration["evidence_refs"][0],
            evidence_refs=(
                active_target["evidence_ref"],
                str(active_result_path),
                str(joint_result_path),
            ),
        )
        result = search_factored(
            predict=carrier,
            start=start,
            interventions=INTERVENTIONS,
            problem=problem,
            start_time=start_time,
            max_depth=MAX_DEPTH,
            max_states=MAX_STATES,
        )
        replay = _replay(
            carrier=carrier,
            projection=projection,
            start=start,
            start_time=start_time,
            actions=result.actions,
            problem=problem,
            operation_map=operation_map,
        )
        selected_searches.append({
            "raw_configuration_sha256": configuration["raw_sha256"],
            "partition_sha256": configuration["partition_sha256"],
            "evidence_refs": configuration["evidence_refs"],
            "search": _result_row(result),
            "replay": replay,
            "differs_from_known_route_before_terminal": bool(
                result.actions
                and tuple(result.actions[:-1]) != known_route[:-1]
            ),
        })

    positive_passed = bool(
        positive_result.status == "edge_found"
        and positive_replay.get("goal_edge")
    )
    selected_passed = bool(
        selected_searches
        and all(
            row["search"]["status"] == "edge_found"
            and not row["search"]["projection_counterexample"]
            and row["replay"].get("admissible")
            and row["replay"].get("goal_edge")
            and row["replay"].get("configuration_sha256")
            == SELECTED_CONFIGURATION
            and row["replay"].get("joint_sha256") == EXPECTED_JOINT
            and row["differs_from_known_route_before_terminal"]
            for row in selected_searches
        )
    )
    payload = {
        "schema": "ztare-joint-affordance-search-audit-v1",
        "status": (
            "joint_affordance_search_confirmed"
            if positive_passed and selected_passed
            else "joint_affordance_search_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "start": {
            "trace": str(trace_path.relative_to(project)),
            "row": 0,
            "time": start_time,
            "state_sha256": stable_sha256(start),
        },
        "target": {
            "evidence_ref": active_target["evidence_ref"],
            "controlled_base": observed_factors.controlled_base,
            "operation": repr(operation),
            "expected_joint_sha256": EXPECTED_JOINT,
            "selected_configuration_sha256": SELECTED_CONFIGURATION,
            "raw_selected_configuration_count": len(raw_configurations),
        },
        "bounds": {
            "max_depth": MAX_DEPTH,
            "max_states": MAX_STATES,
            "interventions": list(INTERVENTIONS),
        },
        "known_graph_route": {
            "actions": [repr(action) for action in known_route],
            "action_count": len(known_route),
        },
        "positive_control": {
            "problem_id": positive_problem.problem_id,
            "search": _result_row(positive_result),
            "replay": positive_replay,
            "passed": positive_passed,
        },
        "selected_searches": selected_searches,
        "criteria": {
            "positive_control": positive_passed,
            "raw_configuration_witnesses": bool(raw_configurations),
            "all_selected_targets": selected_passed,
            "no_environment_contact": True,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "criteria": payload["criteria"],
        "raw_selected_configuration_count": len(raw_configurations),
        "positive_control": {
            "status": positive_result.status,
            "action_count": len(positive_result.actions),
            "generated": positive_result.generated,
            "expanded": positive_result.expanded,
            "replay": positive_replay,
        },
        "selected": [
            {
                "raw_configuration_sha256": row[
                    "raw_configuration_sha256"
                ],
                "status": row["search"]["status"],
                "action_count": row["search"]["action_count"],
                "generated": row["search"]["generated"],
                "expanded": row["search"]["expanded"],
                "projection_counterexample": row["search"][
                    "projection_counterexample"
                ],
                "replay": row["replay"],
                "differs_from_known_route_before_terminal": row[
                    "differs_from_known_route_before_terminal"
                ],
            }
            for row in selected_searches
        ],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
