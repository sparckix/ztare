#!/usr/bin/env python3
"""Test recoverable zero-resource states in target-search admissibility."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint

from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.compiled_fiber_planning import CompiledFiberSearchProblem
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import fiber_mechanism_effect


class RecoverableZeroFiberSearchProblem(CompiledFiberSearchProblem):
    """Audit-local feasibility change; terminal goal remains positive-budget."""

    def admissible(self, state: Any) -> bool:
        return self.projection.in_domain(state)


def _budget_trace(
    *,
    carrier: Any,
    projection: Any,
    start: Any,
    start_time: int,
    actions: tuple[Any, ...],
) -> dict[str, Any]:
    state = start
    time_value = start_time
    start_factors = projection.factor(state)
    rows = [{
        "depth": 0,
        "time": time_value,
        "ordered_budget": start_factors.ordered_budget,
        "in_domain": projection.in_domain(state),
    }]
    renewals = []
    for depth, action in enumerate(actions[:-1], 1):
        prior_factors = projection.factor(state)
        successor = carrier(state, action, time_value)
        if successor is None:
            return {
                "complete": False,
                "missing_depth": depth,
                "rows": rows,
                "renewals": renewals,
            }
        successor_factors = projection.factor(successor)
        effect = fiber_mechanism_effect(prior_factors, successor_factors)
        if (
            prior_factors.ordered_budget == 0
            and successor_factors.ordered_budget > 0
        ):
            renewals.append({
                "depth": depth,
                "operation": repr(action),
                "from_budget": prior_factors.ordered_budget,
                "to_budget": successor_factors.ordered_budget,
                "effect": repr(effect),
            })
        time_value += 1
        state = successor
        rows.append({
            "depth": depth,
            "time": time_value,
            "operation": repr(action),
            "ordered_budget": successor_factors.ordered_budget,
            "in_domain": projection.in_domain(successor),
        })
    return {
        "complete": True,
        "rows": rows,
        "renewals": renewals,
        "zero_depths": [
            row["depth"] for row in rows if row["ordered_budget"] == 0
        ],
        "all_in_domain": all(row["in_domain"] for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--baseline-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_path = Path(args.trace).resolve()
    trace_rows = tuple(EpisodeLog.read_jsonl(trace_path))
    if not trace_rows:
        raise SystemExit("start trace is empty")
    start = trace_rows[0].s
    start_time = int(trace_rows[0].t)

    baseline_path = Path(args.baseline_result)
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_control = baseline["positive_control"]["search"]
    baseline_bound = bool(
        baseline.get("status") == "joint_affordance_search_refuted"
        and baseline_control.get("status") == "projected_frontier_exhausted"
        and baseline_control.get("generated") == 457
        and baseline_control.get("deepest_depth") == 20
    )

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
    target = joint._active_target(
        project=project,
        projection=projection,
        active_result=active_result,
    )
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]
    problem = RecoverableZeroFiberSearchProblem(
        projection=projection,
        target=projection.factor(target["grid"]),
        terminal_intervention=operation,
        target_evidence_ref=target["evidence_ref"],
        additional_evidence_refs=(
            str(active_result_path),
            str(baseline_path),
        ),
    )
    result = search_factored(
        predict=carrier,
        start=start,
        interventions=prior_search.INTERVENTIONS,
        problem=problem,
        start_time=start_time,
        max_depth=prior_search.MAX_DEPTH,
        max_states=prior_search.MAX_STATES,
    )
    replay = prior_search._replay(
        carrier=carrier,
        projection=projection,
        start=start,
        start_time=start_time,
        actions=result.actions,
        problem=problem,
        operation_map=operation_map,
    )
    budget_trace = _budget_trace(
        carrier=carrier,
        projection=projection,
        start=start,
        start_time=start_time,
        actions=result.actions,
    )
    known_route = tuple(
        ast.literal_eval(action)
        for action in active_result["matches"][0]["route_actions"]
    )
    known_budget_trace = _budget_trace(
        carrier=carrier,
        projection=projection,
        start=start,
        start_time=start_time,
        actions=known_route,
    )
    expected_configuration = active_result["matches"][0]["relation"][
        "configuration_sha256"
    ]
    passed = bool(
        baseline_bound
        and result.status == "edge_found"
        and not result.projection_counterexample
        and replay.get("admissible")
        and replay.get("goal_edge")
        and replay.get("configuration_sha256") == expected_configuration
        and budget_trace.get("complete")
        and budget_trace.get("all_in_domain")
        and budget_trace.get("zero_depths")
        and budget_trace.get("renewals")
        and known_budget_trace.get("zero_depths") == [21]
        and known_budget_trace.get("renewals")
    )
    payload = {
        "schema": "ztare-recoverable-zero-target-search-audit-v1",
        "status": (
            "recoverable_zero_target_search_confirmed"
            if passed
            else "recoverable_zero_target_search_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "baseline": {
            "result": str(baseline_path),
            "bound": baseline_bound,
            "status": baseline_control.get("status"),
            "generated": baseline_control.get("generated"),
            "expanded": baseline_control.get("expanded"),
            "deepest_depth": baseline_control.get("deepest_depth"),
        },
        "ablation": {
            "class": "RecoverableZeroFiberSearchProblem",
            "only_override": "admissible",
            "predicate": "projection.in_domain(state)",
            "goal_positive_budget_unchanged": True,
        },
        "search": prior_search._result_row(result),
        "replay": replay,
        "budget_trace": budget_trace,
        "known_route_budget_trace": known_budget_trace,
        "known_route": {
            "action_count": len(known_route),
            "same_actions": tuple(result.actions) == known_route,
        },
        "criteria": {
            "baseline_bound": baseline_bound,
            "edge_found": result.status == "edge_found",
            "no_projection_counterexample": (
                not result.projection_counterexample
            ),
            "in_domain_zero_state": bool(
                budget_trace.get("all_in_domain")
                and budget_trace.get("zero_depths")
            ),
            "zero_to_positive_renewal": bool(
                budget_trace.get("renewals")
            ),
            "replay_goal_edge": bool(replay.get("goal_edge")),
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
        "search": {
            key: value
            for key, value in payload["search"].items()
            if key not in {"actions", "continuation_actions"}
        },
        "action_count": len(result.actions),
        "same_actions_as_known_route": tuple(result.actions) == known_route,
        "zero_depths": budget_trace.get("zero_depths"),
        "renewals": budget_trace.get("renewals"),
        "replay": replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
