#!/usr/bin/env python3
"""Align a frozen evidence-graph route with predictive-carrier replay."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import active_affordance_frontier_audit as frontier
import joint_equivariant_affordance_audit as joint

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.compiled_fiber_planning import CompiledFiberSearchProblem
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


EXPECTED_GRAPH = {
    "node_count": 130,
    "relation_count": 145,
    "boundary_edge_count": 10,
    "context_transition_edge_count": 6,
    "ambiguous_relation_count": 0,
}


def _factor_mapping(projection: Any, state: Any) -> dict[str, Any]:
    return projection.factor(state).as_mapping()


def _differences(
    graph_factors: dict[str, Any],
    carrier_factors: dict[str, Any],
) -> list[str]:
    return [
        name
        for name in graph_factors
        if graph_factors[name] != carrier_factors.get(name)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_path = Path(args.trace).resolve()
    report_path = Path(args.report).resolve()
    active_result_path = Path(args.active_result)
    active_result = json.loads(
        active_result_path.read_text(encoding="utf-8")
    )
    matches = active_result.get("matches") or []
    if len(matches) != 1:
        raise SystemExit("frozen H29 result no longer has one match")
    frozen_match = matches[0]
    frozen_source_sha = str(frozen_match["source_sha256"])
    frozen_actions = tuple(
        ast.literal_eval(action)
        for action in frozen_match["route_actions"]
    )
    terminal_operation = frozen_actions[-1]
    frozen_prefix = frozen_actions[:-1]

    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")
    carrier_execution_sha = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )

    (
        problem,
        system,
        fibers,
        _active_rows,
        diagnostics,
    ) = frontier._active_problem(
        project=project,
        trace_path=trace_path,
        report_path=report_path,
        carrier=carrier,
        carrier_sha=carrier_sha,
        carrier_execution_sha=carrier_execution_sha,
        projection=projection,
    )
    routes, context_crossings = frontier._reachable_routes(
        fibers,
        diagnostics["start_key"],
    )
    graph_counts = {
        "node_count": len(fibers.nodes),
        "relation_count": len(fibers.edges),
        "boundary_edge_count": len(fibers.boundary_edges),
        "context_transition_edge_count": len(
            fibers.context_transition_edges
        ),
        "ambiguous_relation_count": len(system.noncommuting_relations),
    }
    graph_matches_expected = graph_counts == EXPECTED_GRAPH
    source_keys = [
        key for key in routes if stable_sha256(key) == frozen_source_sha
    ]
    if len(source_keys) != 1:
        raise SystemExit(
            f"expected one frozen source key, found {len(source_keys)}"
        )
    target_source = source_keys[0]
    graph_prefix = tuple(routes[target_source])
    route_matches_expected = graph_prefix == frozen_prefix

    trace_rows = tuple(EpisodeLog.read_jsonl(trace_path))
    if not trace_rows:
        raise SystemExit("start trace is empty")
    predicted_state = trace_rows[0].s
    time_value = int(trace_rows[0].t)
    node = diagnostics["start_key"]
    steps = []
    first_terminal_key_divergence = None
    first_any_factor_divergence = None
    carrier_missing_step = None
    prefix_edges_valid = True

    for index, operation in enumerate(graph_prefix):
        edge = fibers.edges.get((node, operation))
        if edge is None or not edge.deterministic or edge.boundary_kinds:
            prefix_edges_valid = False
            steps.append({
                "step": index,
                "operation": repr(operation),
                "graph_source_sha256": stable_sha256(node),
                "graph_edge_missing_or_invalid": True,
                "boundary_kinds": (
                    list(edge.boundary_kinds) if edge is not None else []
                ),
            })
            break
        target = edge.targets[0]
        graph_source_rep = system.representative(node)
        graph_source_state = getattr(
            graph_source_rep,
            "observation",
            graph_source_rep,
        )
        graph_target_rep = system.representative(target)
        graph_target_state = getattr(
            graph_target_rep,
            "observation",
            graph_target_rep,
        )
        graph_source_factors = _factor_mapping(
            projection,
            graph_source_state,
        )
        graph_target_factors = _factor_mapping(
            projection,
            graph_target_state,
        )
        carrier_source_factors = _factor_mapping(
            projection,
            predicted_state,
        )
        next_predicted = carrier(predicted_state, operation, time_value)
        if next_predicted is None:
            carrier_missing_step = index
            steps.append({
                "step": index,
                "operation": repr(operation),
                "time": time_value,
                "graph_source_sha256": stable_sha256(node),
                "graph_target_sha256": stable_sha256(target),
                "carrier_returned_none": True,
                "edge_evidence_refs": list(edge.evidence_refs),
            })
            break
        carrier_target_factors = _factor_mapping(
            projection,
            next_predicted,
        )
        changed_factors = _differences(
            graph_target_factors,
            carrier_target_factors,
        )
        terminal_key_equal = (
            graph_target_factors["controlled_base"]
            == carrier_target_factors["controlled_base"]
            and graph_target_factors["finite_configuration"]
            == carrier_target_factors["finite_configuration"]
        )
        if changed_factors and first_any_factor_divergence is None:
            first_any_factor_divergence = index
        if not terminal_key_equal and first_terminal_key_divergence is None:
            first_terminal_key_divergence = index
        graph_effect = fiber_mechanism_effect(
            projection.factor(graph_source_state),
            projection.factor(graph_target_state),
        )
        carrier_effect = fiber_mechanism_effect(
            projection.factor(predicted_state),
            projection.factor(next_predicted),
        )
        steps.append({
            "step": index,
            "operation": repr(operation),
            "time": time_value,
            "graph_source_sha256": stable_sha256(node),
            "graph_target_sha256": stable_sha256(target),
            "graph_source_representative_sha256": stable_sha256(
                graph_source_state
            ),
            "graph_target_representative_sha256": stable_sha256(
                graph_target_state
            ),
            "carrier_source_sha256": stable_sha256(predicted_state),
            "carrier_target_sha256": stable_sha256(next_predicted),
            "source_factor_differences": _differences(
                graph_source_factors,
                carrier_source_factors,
            ),
            "target_factor_differences": changed_factors,
            "terminal_key_equal": terminal_key_equal,
            "graph_controlled_base": graph_target_factors[
                "controlled_base"
            ],
            "carrier_controlled_base": carrier_target_factors[
                "controlled_base"
            ],
            "graph_configuration_sha256": stable_sha256(
                affordance_configuration := tuple(
                    graph_target_factors["finite_configuration"]
                )
            ),
            "carrier_configuration_sha256": stable_sha256(tuple(
                carrier_target_factors["finite_configuration"]
            )),
            "graph_effect": repr(graph_effect),
            "carrier_effect": repr(carrier_effect),
            "effect_equal": graph_effect == carrier_effect,
            "context_transition": edge.context_transition,
            "boundary_kinds": list(edge.boundary_kinds),
            "edge_evidence_refs": list(edge.evidence_refs),
            "target_lineage_sha256s": sorted(
                fibers.lineage_sha256s_by_node[target]
            ),
            "graph_configuration_value": affordance_configuration,
        })
        predicted_state = next_predicted
        time_value += 1
        node = target

    active_target = joint._active_target(
        project=project,
        projection=projection,
        active_result=active_result,
    )
    observed_problem = CompiledFiberSearchProblem(
        projection=projection,
        target=projection.factor(active_target["grid"]),
        terminal_intervention=terminal_operation,
        target_evidence_ref=active_target["evidence_ref"],
        additional_evidence_refs=(str(active_result_path),),
    )
    prefix_complete = len(steps) == len(graph_prefix) and carrier_missing_step is None
    final_goal_edge = bool(
        prefix_complete
        and observed_problem.goal_edge(
            predicted_state,
            terminal_operation,
            time_value,
        )
    )
    passed = bool(
        graph_matches_expected
        and route_matches_expected
        and prefix_edges_valid
        and first_terminal_key_divergence is None
        and carrier_missing_step is None
        and final_goal_edge
    )
    payload = {
        "schema": "ztare-carrier-graph-route-commutation-audit-v1",
        "status": (
            "carrier_graph_route_commutation_confirmed"
            if passed
            else "carrier_graph_route_commutation_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "carrier_execution_sha256": carrier_execution_sha,
        "projection_sha256": projection.projection_sha256,
        "graph": {
            **graph_counts,
            "matches_expected": graph_matches_expected,
            "reachable_node_count": len(routes),
            "target_source_sha256": frozen_source_sha,
            "route_context_crossings": context_crossings[target_source],
        },
        "route": {
            "expected_actions": [repr(action) for action in frozen_prefix],
            "graph_actions": [repr(action) for action in graph_prefix],
            "matches_expected": route_matches_expected,
            "prefix_length": len(graph_prefix),
            "terminal_operation": repr(terminal_operation),
            "prefix_edges_valid": prefix_edges_valid,
        },
        "comparison": {
            "first_any_factor_divergence": first_any_factor_divergence,
            "first_terminal_key_divergence": (
                first_terminal_key_divergence
            ),
            "carrier_missing_step": carrier_missing_step,
            "final_goal_edge": final_goal_edge,
            "steps_compared": len(steps),
            "steps": steps,
        },
        "criteria": {
            "graph_identity": graph_matches_expected,
            "route_identity": route_matches_expected,
            "prefix_edges_valid": prefix_edges_valid,
            "terminal_key_commutes": (
                first_terminal_key_divergence is None
                and carrier_missing_step is None
            ),
            "final_goal_edge": final_goal_edge,
            "no_environment_contact": True,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    first_terminal_row = (
        steps[first_terminal_key_divergence]
        if first_terminal_key_divergence is not None
        and first_terminal_key_divergence < len(steps)
        else None
    )
    print(json.dumps({
        "status": payload["status"],
        "criteria": payload["criteria"],
        "graph": payload["graph"],
        "route": {
            key: value
            for key, value in payload["route"].items()
            if key not in {"expected_actions", "graph_actions"}
        },
        "first_any_factor_divergence": first_any_factor_divergence,
        "first_terminal_key_divergence": first_terminal_key_divergence,
        "first_terminal_divergence": first_terminal_row,
        "final_goal_edge": final_goal_edge,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
