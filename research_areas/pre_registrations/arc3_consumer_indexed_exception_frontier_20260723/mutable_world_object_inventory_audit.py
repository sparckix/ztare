#!/usr/bin/env python3
"""Test a canonical mutable-world component inventory."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from dataclasses import replace
from functools import lru_cache
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


class MutableWorldInventoryProjection:
    """Parent factors plus canonical nonbackground world components."""

    def __init__(
        self,
        parent: Any,
        *,
        evidence_refs: tuple[str, ...],
    ) -> None:
        self.parent = parent
        rendered_rows = [
            int(row) for row, _col in parent.display_cells
        ]
        rendered_rows.extend(
            int(row)
            for group in parent.budget_groups
            for row, _col in group
        )
        if not rendered_rows:
            raise ValueError("projection has no owned rendering rows")
        self.interface_row = min(rendered_rows)
        self.evidence_refs = tuple(dict.fromkeys((
            *parent.evidence_refs,
            *evidence_refs,
        )))
        self.projection_sha256 = stable_sha256({
            "schema": "ztare-mutable-world-inventory-projection-v1",
            "parent_projection_sha256": parent.projection_sha256,
            "interface_row": self.interface_row,
            "connectivity": 4,
            "background": "modal_after_controlled_erasure",
            "component_identity": (
                "absolute_bbox",
                "first_occurrence_palette_partition",
            ),
            "evidence_refs": self.evidence_refs,
        })
        self._inventory_cached = lru_cache(maxsize=50_000)(
            self._inventory_uncached
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def inventory(
        self,
        state: Any,
        controlled_bases: tuple[tuple[int, int], ...],
    ) -> tuple[tuple[Any, ...], ...]:
        frozen = (
            state
            if isinstance(state, tuple)
            else tuple(tuple(row) for row in state)
        )
        return self._inventory_cached(
            frozen,
            tuple(tuple(base) for base in controlled_bases),
        )

    def _inventory_uncached(
        self,
        state: tuple[tuple[Any, ...], ...],
        controlled_bases: tuple[tuple[int, int], ...],
    ) -> tuple[tuple[Any, ...], ...]:
        height = min(self.interface_row, len(state))
        width = max((len(state[row]) for row in range(height)), default=0)
        erased = {
            (base_row + dy, base_col + dx)
            for base_row, base_col in controlled_bases
            for dy in range(len(self.parent.sprite))
            for dx in range(len(self.parent.sprite[0]))
        }
        values = [
            state[row][col]
            for row in range(height)
            for col in range(len(state[row]))
            if (row, col) not in erased
        ]
        if not values:
            raise ValueError("world region is empty after controlled erasure")
        counts = Counter(values)
        ranked = sorted(
            counts.items(),
            key=lambda item: (-item[1], repr(item[0])),
        )
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            raise ValueError("modal world background is ambiguous")
        background = ranked[0][0]
        occupied = {
            (row, col)
            for row in range(height)
            for col in range(len(state[row]))
            if (row, col) not in erased and state[row][col] != background
        }
        components = []
        while occupied:
            seed = min(occupied)
            occupied.remove(seed)
            component = {seed}
            stack = [seed]
            while stack:
                row, col = stack.pop()
                for neighbor in (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1),
                ):
                    if neighbor in occupied:
                        occupied.remove(neighbor)
                        component.add(neighbor)
                        stack.append(neighbor)
            rows = [row for row, _col in component]
            cols = [col for _row, col in component]
            top, bottom = min(rows), max(rows)
            left, right = min(cols), max(cols)
            matrix = tuple(
                tuple(
                    (
                        state[row][col]
                        if (row, col) in component
                        else affordance.OUTSIDE
                    )
                    for col in range(left, right + 1)
                )
                for row in range(top, bottom + 1)
            )
            components.append((
                (top, left, bottom, right),
                affordance._partition_matrix(matrix),
            ))
        return tuple(sorted(components, key=repr))

    def factor(self, state: Any) -> Any:
        factors = self.parent.factor(state)
        inventory = self.inventory(state, factors.controlled_base)
        identity = (len(inventory), stable_sha256(inventory))
        return replace(
            factors,
            operation_domain_assignment=(
                *factors.operation_domain_assignment,
                ("mutable_world_object_inventory", identity),
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


def _receipt_separation(
    projection: MutableWorldInventoryProjection,
    result: dict[str, Any],
) -> dict[str, Any]:
    receipt = result["search"]["projection_counterexample"]
    source_key = ast.literal_eval(receipt["merged_key"])
    origin = tuple(source_key[0][0][0])
    changed = receipt["consumer_difference"]["changed_cells"]
    max_row = max(
        projection.interface_row,
        max(int(row["coordinate"][0]) for row in changed) + 1,
        origin[0] + len(projection.parent.sprite),
    )
    max_col = max(
        64,
        max(int(row["coordinate"][1]) for row in changed) + 1,
        origin[1] + len(projection.parent.sprite[0]),
    )
    left = [[3 for _col in range(max_col)] for _row in range(max_row)]
    right = [[3 for _col in range(max_col)] for _row in range(max_row)]
    for dy, row in enumerate(projection.parent.sprite):
        for dx, value in enumerate(row):
            left[origin[0] + dy][origin[1] + dx] = value
            right[origin[0] + dy][origin[1] + dx] = value
    for row in changed:
        y, x = (int(value) for value in row["coordinate"])
        left[y][x] = row["left"]
        right[y][x] = row["right"]
    left_inventory = projection.inventory(left, (origin,))
    right_inventory = projection.inventory(right, (origin,))
    return {
        "origin": origin,
        "changed_cells": changed,
        "left_component_count": len(left_inventory),
        "right_component_count": len(right_inventory),
        "left_inventory_sha256": stable_sha256(left_inventory),
        "right_inventory_sha256": stable_sha256(right_inventory),
        "separated": left_inventory != right_inventory,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--counterexample-result", required=True)
    parser.add_argument("--h38-result", required=True)
    parser.add_argument("--h39-result", required=True)
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
    inventory_projection = MutableWorldInventoryProjection(
        split_projection,
        evidence_refs=(str(args.h38_result), str(args.h39_result)),
    )
    h38_result = json.loads(
        Path(args.h38_result).read_text(encoding="utf-8")
    )
    h39_result = json.loads(
        Path(args.h39_result).read_text(encoding="utf-8")
    )
    h38_separation = _receipt_separation(
        inventory_projection,
        h38_result,
    )
    h39_separation = _receipt_separation(
        inventory_projection,
        h39_result,
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
        projection=inventory_projection,
        active_result=active_result,
    )
    configurations = prior_search._selected_raw_configurations(
        project=project,
        projection=inventory_projection,
        joint_result=joint_result,
    )
    if len(configurations) != 1:
        raise SystemExit("selected raw configuration is not unique")
    configuration = configurations[0]
    target_factors = replace(
        inventory_projection.factor(target["grid"]),
        finite_configuration=configuration["raw_configuration"],
    )
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]
    problem = time_guarded.TimeGuardedTargetProblem(
        projection=inventory_projection,
        target=target_factors,
        terminal_intervention=operation,
        target_evidence_ref=configuration["evidence_refs"][0],
        additional_evidence_refs=(
            target["evidence_ref"],
            str(active_result_path),
            str(joint_result_path),
            str(counterexample_path),
            str(args.h38_result),
            str(args.h39_result),
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
            projection=inventory_projection,
            start=start,
            start_time=start_time,
            actions=result.actions,
            problem=problem,
            operation_map=operation_map,
        )
    passed = bool(
        h38_separation["separated"]
        and h39_separation["separated"]
        and result.status == "edge_found"
        and not result.projection_counterexample
        and replay.get("admissible")
        and replay.get("goal_edge")
        and replay.get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
    )
    payload = {
        "schema": "ztare-mutable-world-object-inventory-audit-v1",
        "status": (
            "mutable_world_object_inventory_confirmed"
            if passed
            else "mutable_world_object_inventory_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "parent_projection_sha256": parent.projection_sha256,
        "inventory_projection_sha256": inventory_projection.projection_sha256,
        "interface_row": inventory_projection.interface_row,
        "h38_separation": h38_separation,
        "h39_separation": h39_separation,
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
            "h38_separated": h38_separation["separated"],
            "h39_separated": h39_separation["separated"],
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
