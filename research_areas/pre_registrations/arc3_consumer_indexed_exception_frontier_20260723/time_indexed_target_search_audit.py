#!/usr/bin/env python3
"""Test clock identity as the sole target-search ablation."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any, Hashable

import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.compiled_fiber_planning import CompiledFiberSearchProblem
from ztare.worldmodel.episode_log import EpisodeLog


class TimeIndexedFiberSearchProblem(CompiledFiberSearchProblem):
    """Audit-local clock guard; every other consumer method is inherited."""

    def dominance_key_at(
        self,
        state: Any,
        time_value: Any,
    ) -> Hashable:
        return self.dominance_key(state), time_value


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
        and baseline_control.get("expanded") == 458
        and not baseline_control.get("actions")
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
    problem = TimeIndexedFiberSearchProblem(
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
    passed = bool(
        baseline_bound
        and result.status == "edge_found"
        and not result.projection_counterexample
        and replay.get("admissible")
        and replay.get("goal_edge")
        and tuple(replay.get("controlled_base") or ())
        == tuple(projection.factor(target["grid"]).controlled_base)
        and replay.get("configuration_sha256")
        == active_result["matches"][0]["relation"][
            "configuration_sha256"
        ]
    )
    known_route = tuple(
        ast.literal_eval(action)
        for action in active_result["matches"][0]["route_actions"]
    )
    payload = {
        "schema": "ztare-time-indexed-target-search-audit-v1",
        "status": (
            "time_indexed_target_search_confirmed"
            if passed
            else "time_indexed_target_search_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "projection_sha256": projection.projection_sha256,
        "baseline": {
            "result": str(baseline_path),
            "bound": baseline_bound,
            "status": baseline_control.get("status"),
            "generated": baseline_control.get("generated"),
            "expanded": baseline_control.get("expanded"),
        },
        "ablation": {
            "class": "TimeIndexedFiberSearchProblem",
            "only_override": "dominance_key_at",
            "key": "(dominance_key(state), time_value)",
        },
        "bounds": {
            "max_depth": prior_search.MAX_DEPTH,
            "max_states": prior_search.MAX_STATES,
            "interventions": list(prior_search.INTERVENTIONS),
        },
        "search": prior_search._result_row(result),
        "replay": replay,
        "known_route": {
            "actions": [repr(action) for action in known_route],
            "action_count": len(known_route),
            "same_actions": tuple(result.actions) == known_route,
        },
        "criteria": {
            "baseline_bound": baseline_bound,
            "edge_found": result.status == "edge_found",
            "no_projection_counterexample": (
                not result.projection_counterexample
            ),
            "replay_goal_edge": bool(replay.get("goal_edge")),
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
        "criteria": payload["criteria"],
        "search": {
            key: value
            for key, value in payload["search"].items()
            if key not in {"actions", "continuation_actions"}
        },
        "action_count": len(result.actions),
        "same_actions_as_known_route": tuple(result.actions) == known_route,
        "replay": replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
