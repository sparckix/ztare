#!/usr/bin/env python3
"""Compose target-search clock identity with the first same-time split."""
from __future__ import annotations

import argparse
import ast
from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Hashable

import availability_cegar_closure_audit as cegar
import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.compiled_fiber_planning import CompiledFiberSearchProblem
from ztare.worldmodel.episode_log import EpisodeLog


class TimeGuardedTargetProblem(CompiledFiberSearchProblem):
    """Target consumer with clock identity and no other behavior change."""

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
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--counterexample-result", required=True)
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
    parent = getattr(carrier, "_ztare_factored_projection", None)
    if parent is None:
        raise SystemExit("carrier has no factored projection")

    counterexample_path = Path(args.counterexample_result)
    counterexample_payload = json.loads(
        counterexample_path.read_text(encoding="utf-8")
    )
    receipt = cegar._initial_receipt(counterexample_payload)
    split = cegar._split_from_receipt(
        receipt,
        lineage=str(counterexample_path),
    )
    if receipt["dominator_time"] != receipt["dominated_time"]:
        raise SystemExit("source counterexample is not same-time")
    projection = cegar.AvailabilityRefinedProjection(
        parent,
        splits=(split,),
        evidence_refs=(str(counterexample_path),),
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
    problem = TimeGuardedTargetProblem(
        projection=projection,
        target=target_factors,
        terminal_intervention=operation,
        target_evidence_ref=configuration["evidence_refs"][0],
        additional_evidence_refs=(
            target["evidence_ref"],
            str(active_result_path),
            str(joint_result_path),
            str(counterexample_path),
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
    replay = {}
    if result.status == "edge_found":
        replay = prior_search._replay(
            carrier=carrier,
            projection=projection,
            start=start,
            start_time=start_time,
            actions=result.actions,
            problem=problem,
            operation_map=operation_map,
        )
    next_receipt = dict(result.projection_counterexample)
    same_time_residual = bool(
        next_receipt
        and next_receipt.get("dominator_time")
        == next_receipt.get("dominated_time")
    )
    cross_time_residual = bool(next_receipt and not same_time_residual)
    passed = bool(
        split["left_bit"] != split["right_bit"]
        and result.status == "edge_found"
        and not next_receipt
        and replay.get("admissible")
        and replay.get("goal_edge")
        and replay.get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
    )
    payload = {
        "schema": "ztare-time-guarded-affordance-refinement-audit-v1",
        "status": (
            "time_guarded_affordance_refinement_confirmed"
            if passed
            else "time_guarded_affordance_refinement_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "parent_projection_sha256": parent.projection_sha256,
        "refined_projection_sha256": projection.projection_sha256,
        "clock_identity": {
            "key": "(dominance_key(state), time_value)",
            "time_translation_certificate": None,
        },
        "split": split,
        "target": {
            "configuration_sha256": prior_search.SELECTED_CONFIGURATION,
            "joint_sha256": prior_search.EXPECTED_JOINT,
            "operation": repr(operation),
        },
        "bounds": {
            "max_depth": prior_search.MAX_DEPTH,
            "max_states": prior_search.MAX_STATES,
        },
        "search": prior_search._result_row(result),
        "replay": replay,
        "criteria": {
            "source_split_same_time": True,
            "split_separates": split["left_bit"] != split["right_bit"],
            "edge_found": result.status == "edge_found",
            "no_projection_counterexample": not next_receipt,
            "no_cross_time_residual": not cross_time_residual,
            "no_same_time_residual": not same_time_residual,
            "selected_joint_code": (
                replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
            ),
            "no_environment_contact": True,
        },
        "start_state_sha256": stable_sha256(start),
        "problem_id": problem.problem_id,
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
        "residual_times": {
            "dominator": next_receipt.get("dominator_time"),
            "dominated": next_receipt.get("dominated_time"),
        },
        "consumer_difference": next_receipt.get("consumer_difference"),
        "replay": replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
