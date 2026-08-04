#!/usr/bin/env python3
"""Test an action-indexed actor-relative affordance field."""
from __future__ import annotations

import argparse
import ast
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import availability_cegar_closure_audit as cegar
import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint
import terminal_affordance_relation_audit as affordance
import time_guarded_affordance_refinement_audit as time_guarded

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog


class ActorRelativeAffordanceProjection:
    """Parent factors plus local destination geometry for every operation."""

    def __init__(
        self,
        parent: Any,
        *,
        operation_maps: tuple[tuple[str, tuple[int, int]], ...],
        evidence_refs: tuple[str, ...],
    ) -> None:
        self.parent = parent
        self.operation_maps = operation_maps
        self.evidence_refs = tuple(dict.fromkeys((
            *parent.evidence_refs,
            *evidence_refs,
        )))
        self.projection_sha256 = stable_sha256({
            "schema": "ztare-actor-relative-affordance-projection-v1",
            "parent_projection_sha256": parent.projection_sha256,
            "operation_maps": operation_maps,
            "window_shape": (
                len(parent.sprite),
                len(parent.sprite[0]),
            ),
            "palette_normalization": "first_occurrence_partition",
            "evidence_refs": self.evidence_refs,
        })

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def _field(
        self,
        state: Any,
        controlled_bases: tuple[tuple[int, int], ...],
    ) -> tuple[tuple[str, Any], ...]:
        if len(controlled_bases) != 1:
            return (("controlled_origin_arity", len(controlled_bases)),)
        origin = controlled_bases[0]
        height = len(self.parent.sprite)
        width = len(self.parent.sprite[0])
        if height != width:
            raise ValueError("affordance audit requires a square controlled object")
        rows = []
        for operation, (delta_row, delta_col) in self.operation_maps:
            attempted = origin[0] + delta_row, origin[1] + delta_col
            raw = affordance._window(
                state,
                top=attempted[0],
                left=attempted[1],
                size=height,
                current_origin=origin,
                sprite_shape=(height, width),
            )
            rows.append((
                operation,
                affordance._partition_matrix(raw),
            ))
        return tuple(rows)

    def factor(self, state: Any) -> Any:
        factors = self.parent.factor(state)
        field = self._field(state, factors.controlled_base)
        return replace(
            factors,
            operation_domain_assignment=(
                *factors.operation_domain_assignment,
                ("actor_relative_affordance_field", field),
            ),
        )

    def explain_state_difference(
        self,
        left: Any,
        right: Any,
    ) -> dict[str, Any]:
        payload = dict(self.parent.explain_state_difference(left, right))
        left_factors = self.factor(left).as_mapping()
        right_factors = self.factor(right).as_mapping()
        payload["changed_factor_names"] = [
            name
            for name in self.factor_names
            if left_factors[name] != right_factors[name]
        ]
        return payload


def _operation_maps(
    active_result: dict[str, Any],
) -> tuple[tuple[str, tuple[int, int]], ...]:
    rows = []
    for operation, payload in sorted(
        active_result["operation_maps"].items(),
        key=lambda item: repr(item[0]),
    ):
        if not payload.get("admitted"):
            raise ValueError(f"operation map {operation!r} is not admitted")
        vector = tuple(int(value) for value in payload["vector"])
        if len(vector) != 2:
            raise ValueError(f"operation map {operation!r} is not two-dimensional")
        rows.append((str(operation), vector))
    return tuple(rows)


def _h38_separation(
    *,
    field_projection: ActorRelativeAffordanceProjection,
    h38_result: dict[str, Any],
) -> dict[str, Any]:
    receipt = h38_result["search"]["projection_counterexample"]
    difference = receipt["consumer_difference"]
    source_key = ast.literal_eval(receipt["merged_key"])
    origin = tuple(source_key[0][0][0])
    changed = difference["changed_cells"]
    left = [[3 for _col in range(80)] for _row in range(64)]
    right = [[3 for _col in range(80)] for _row in range(64)]
    # Only field equality is tested here. Populate the shared controlled
    # rendering and the receipt's exact differing cells; all other cells are
    # a common background and therefore cancel.
    for dy, row in enumerate(field_projection.parent.sprite):
        for dx, value in enumerate(row):
            left[origin[0] + dy][origin[1] + dx] = value
            right[origin[0] + dy][origin[1] + dx] = value
    for row in changed:
        y, x = (int(value) for value in row["coordinate"])
        left[y][x] = row["left"]
        right[y][x] = row["right"]
    left_field = field_projection._field(left, (origin,))
    right_field = field_projection._field(right, (origin,))
    return {
        "origin": origin,
        "changed_cells": changed,
        "left_field_sha256": stable_sha256(left_field),
        "right_field_sha256": stable_sha256(right_field),
        "separated": left_field != right_field,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--counterexample-result", required=True)
    parser.add_argument("--time-guarded-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_rows = tuple(EpisodeLog.read_jsonl(Path(args.trace).resolve()))
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
    split_projection = cegar.AvailabilityRefinedProjection(
        parent,
        splits=(split,),
        evidence_refs=(str(counterexample_path),),
    )

    active_result_path = Path(args.active_result)
    active_result = json.loads(
        active_result_path.read_text(encoding="utf-8")
    )
    maps = _operation_maps(active_result)
    field_projection = ActorRelativeAffordanceProjection(
        split_projection,
        operation_maps=maps,
        evidence_refs=(str(active_result_path),),
    )
    h38_path = Path(args.time_guarded_result)
    h38_result = json.loads(h38_path.read_text(encoding="utf-8"))
    h38_separation = _h38_separation(
        field_projection=field_projection,
        h38_result=h38_result,
    )

    joint_result_path = Path(args.joint_result)
    joint_result = json.loads(
        joint_result_path.read_text(encoding="utf-8")
    )
    target = joint._active_target(
        project=project,
        projection=field_projection,
        active_result=active_result,
    )
    configurations = prior_search._selected_raw_configurations(
        project=project,
        projection=field_projection,
        joint_result=joint_result,
    )
    if len(configurations) != 1:
        raise SystemExit("selected raw configuration is not unique")
    configuration = configurations[0]
    target_factors = replace(
        field_projection.factor(target["grid"]),
        finite_configuration=configuration["raw_configuration"],
    )
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]
    problem = time_guarded.TimeGuardedTargetProblem(
        projection=field_projection,
        target=target_factors,
        terminal_intervention=operation,
        target_evidence_ref=configuration["evidence_refs"][0],
        additional_evidence_refs=(
            target["evidence_ref"],
            str(active_result_path),
            str(joint_result_path),
            str(counterexample_path),
            str(h38_path),
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
            projection=field_projection,
            start=start,
            start_time=start_time,
            actions=result.actions,
            problem=problem,
            operation_map=operation_map,
        )
    passed = bool(
        len(maps) == len(prior_search.INTERVENTIONS)
        and h38_separation["separated"]
        and result.status == "edge_found"
        and not result.projection_counterexample
        and replay.get("admissible")
        and replay.get("goal_edge")
        and replay.get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
    )
    payload = {
        "schema": "ztare-actor-relative-affordance-field-audit-v1",
        "status": (
            "actor_relative_affordance_field_confirmed"
            if passed
            else "actor_relative_affordance_field_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "parent_projection_sha256": parent.projection_sha256,
        "field_projection_sha256": field_projection.projection_sha256,
        "operation_maps": maps,
        "h38_separation": h38_separation,
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
            "all_operation_maps_admitted": (
                len(maps) == len(prior_search.INTERVENTIONS)
            ),
            "h38_separated": h38_separation["separated"],
            "edge_found": result.status == "edge_found",
            "no_projection_counterexample": (
                not result.projection_counterexample
            ),
            "selected_joint_code": (
                replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
            ),
            "no_environment_contact": True,
        },
        "problem_id": problem.problem_id,
        "start_state_sha256": stable_sha256(start),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    next_receipt = result.projection_counterexample
    print(json.dumps({
        "status": payload["status"],
        "criteria": payload["criteria"],
        "search": {
            key: value
            for key, value in payload["search"].items()
            if key not in {"actions", "continuation_actions"}
        },
        "action_count": len(result.actions),
        "consumer_difference": (
            next_receipt.get("consumer_difference")
            if next_receipt else None
        ),
        "replay": replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
