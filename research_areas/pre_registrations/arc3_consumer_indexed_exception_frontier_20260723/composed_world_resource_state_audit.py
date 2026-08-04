#!/usr/bin/env python3
"""Compose mutable-world inventory with an inferred secondary resource."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint
import mutable_world_object_inventory_audit as world_inventory
import time_guarded_affordance_refinement_audit as time_guarded

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog


class SecondaryResourceProjection:
    """Parent factors plus binary variable cells after the owned budget."""

    def __init__(
        self,
        parent: Any,
        *,
        cells: tuple[tuple[int, int], ...],
        background: Any,
        evidence_refs: tuple[str, ...],
    ) -> None:
        self.parent = parent
        self.secondary_cells = cells
        self.background = background
        self.evidence_refs = tuple(dict.fromkeys((
            *parent.evidence_refs,
            *evidence_refs,
        )))
        self.projection_sha256 = stable_sha256({
            "schema": "ztare-secondary-resource-projection-v1",
            "parent_projection_sha256": parent.projection_sha256,
            "cells": cells,
            "state_map": "value_differs_from_modal_world_background",
            "evidence_refs": self.evidence_refs,
        })
        self._factor_cached = lru_cache(maxsize=50_000)(
            self._factor_uncached
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def resource_state(self, state: Any) -> tuple[bool, ...]:
        return tuple(
            state[row][col] != self.background
            for row, col in self.secondary_cells
        )

    def factor(self, state: Any) -> Any:
        frozen = (
            state
            if isinstance(state, tuple)
            else tuple(tuple(row) for row in state)
        )
        return self._factor_cached(frozen)

    def _factor_uncached(
        self,
        state: tuple[tuple[Any, ...], ...],
    ) -> Any:
        factors = self.parent.factor(state)
        return replace(
            factors,
            ordered_feasibility_configuration=(
                *factors.ordered_feasibility_configuration,
                *self.resource_state(state),
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


def _infer_secondary(
    parent: Any,
    rows: tuple[Any, ...],
) -> dict[str, Any]:
    budget_rows = sorted({
        int(row)
        for group in parent.budget_groups
        for row, _col in group
    })
    budget_cols = [
        int(col)
        for group in parent.budget_groups
        for _row, col in group
    ]
    if not budget_rows or not budget_cols:
        raise ValueError("primary budget rendering is empty")
    boundary = max(budget_cols)
    first = rows[0].s
    interface_row = min(
        int(row) for row, _col in parent.display_cells
    )
    world_values = [
        first[row][col]
        for row in range(min(interface_row, len(first)))
        for col in range(len(first[row]))
    ]
    background_counts = Counter(world_values)
    ranked_background = sorted(
        background_counts.items(),
        key=lambda item: (-item[1], repr(item[0])),
    )
    if (
        not ranked_background
        or (
            len(ranked_background) > 1
            and ranked_background[0][1] == ranked_background[1][1]
        )
    ):
        raise ValueError("modal world background is ambiguous")
    background = ranked_background[0][0]
    candidates = [
        (row, col)
        for row in budget_rows
        for col in range(boundary + 1, len(first[row]))
    ]
    values = {
        cell: {
            state[cell[0]][cell[1]]
            for transition in rows
            for state in (transition.s, transition.s_next)
        }
        for cell in candidates
    }
    cells = tuple(
        cell for cell in candidates if len(values[cell]) >= 2
    )
    if not cells:
        raise ValueError("secondary resource has no variable cells")
    invalid = {
        cell: sorted(values[cell], key=repr)
        for cell in cells
        if len(values[cell]) != 2 or background not in values[cell]
    }
    if invalid:
        raise ValueError(f"secondary cells are not background-binary: {invalid}")
    return {
        "budget_rows": tuple(budget_rows),
        "primary_boundary_col": boundary,
        "background": background,
        "cells": cells,
        "cell_values": {
            repr(cell): sorted(values[cell], key=repr)
            for cell in cells
        },
    }


def _resource_codebook(
    projection: SecondaryResourceProjection,
    rows: tuple[Any, ...],
) -> dict[str, Any]:
    states = {
        projection.resource_state(state)
        for transition in rows
        for state in (transition.s, transition.s_next)
    }
    edges: dict[tuple[bool, ...], Counter] = defaultdict(Counter)
    for transition in rows:
        source = projection.resource_state(transition.s)
        target = projection.resource_state(transition.s_next)
        if source != target:
            edges[source][target] += 1
    deterministic = all(len(targets) == 1 for targets in edges.values())
    next_map = {
        source: next(iter(targets))
        for source, targets in edges.items()
        if len(targets) == 1
    }
    single_cycle = bool(
        len(states) == 4
        and len(next_map) == 4
        and set(next_map) == states
        and set(next_map.values()) == states
    )
    return {
        "state_count": len(states),
        "state_sha256s": sorted(stable_sha256(state) for state in states),
        "changed_source_count": len(edges),
        "deterministic_changed_edges": deterministic,
        "single_cycle": single_cycle,
        "edges": [
            {
                "source_sha256": stable_sha256(source),
                "target_sha256": stable_sha256(target),
                "support": sum(targets.values()),
            }
            for source, targets in sorted(edges.items(), key=lambda item: repr(item[0]))
            if len(targets) == 1
            for target in targets
        ],
    }


def _interface_separation(
    projection: SecondaryResourceProjection,
    result: dict[str, Any],
) -> dict[str, Any]:
    search = result.get("search")
    if not isinstance(search, dict):
        selected = result.get("selected_searches") or []
        if len(selected) != 1:
            raise ValueError("result has no unique search receipt")
        search = selected[0]["search"]
    receipt = search["projection_counterexample"]
    changed = receipt["consumer_difference"]["changed_cells"]
    cells = set(projection.secondary_cells)
    separated_rows = [
        row
        for row in changed
        if tuple(int(value) for value in row["coordinate"]) in cells
        and (row["left"] != projection.background)
        != (row["right"] != projection.background)
    ]
    return {
        "changed_cells": changed,
        "separating_secondary_cells": [
            row["coordinate"] for row in separated_rows
        ],
        "separated": bool(separated_rows),
    }


def _search_row(
    *,
    carrier: Any,
    projection: SecondaryResourceProjection,
    start: Any,
    start_time: int,
    target_factors: Any,
    operation: Any,
    operation_map: dict[str, Any],
    evidence_refs: tuple[str, ...],
) -> dict[str, Any]:
    problem = time_guarded.TimeGuardedTargetProblem(
        projection=projection,
        target=target_factors,
        terminal_intervention=operation,
        target_evidence_ref=evidence_refs[0],
        additional_evidence_refs=evidence_refs[1:],
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
    return {
        "problem_id": problem.problem_id,
        "search": prior_search._result_row(result),
        "replay": replay,
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
    inference = _infer_secondary(parent, evidence_rows)
    projection = SecondaryResourceProjection(
        inventory_projection,
        cells=inference["cells"],
        background=inference["background"],
        evidence_refs=(str(Path(args.evidence)), str(args.h35_result), str(args.h40_result)),
    )
    codebook = _resource_codebook(projection, evidence_rows)

    h38_result = json.loads(Path(args.h38_result).read_text(encoding="utf-8"))
    h39_result = json.loads(Path(args.h39_result).read_text(encoding="utf-8"))
    h35_result = json.loads(Path(args.h35_result).read_text(encoding="utf-8"))
    h40_result = json.loads(Path(args.h40_result).read_text(encoding="utf-8"))
    world_witnesses = {
        "h38": world_inventory._receipt_separation(
            inventory_projection,
            h38_result,
        ),
        "h39": world_inventory._receipt_separation(
            inventory_projection,
            h39_result,
        ),
    }
    interface_witnesses = {
        "h35": _interface_separation(projection, h35_result),
        "h40": _interface_separation(projection, h40_result),
    }

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
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]
    positive_factors = projection.factor(target["grid"])
    positive = _search_row(
        carrier=carrier,
        projection=projection,
        start=start,
        start_time=start_time,
        target_factors=positive_factors,
        operation=operation,
        operation_map=operation_map,
        evidence_refs=(
            target["evidence_ref"],
            str(active_result_path),
            str(args.evidence),
        ),
    )
    configurations = prior_search._selected_raw_configurations(
        project=project,
        projection=projection,
        joint_result=joint_result,
    )
    if len(configurations) != 1:
        raise SystemExit("selected raw configuration is not unique")
    configuration = configurations[0]
    selected_factors = replace(
        positive_factors,
        finite_configuration=configuration["raw_configuration"],
    )
    selected = _search_row(
        carrier=carrier,
        projection=projection,
        start=start,
        start_time=start_time,
        target_factors=selected_factors,
        operation=operation,
        operation_map=operation_map,
        evidence_refs=(
            configuration["evidence_refs"][0],
            target["evidence_ref"],
            str(active_result_path),
            str(joint_result_path),
            str(args.evidence),
        ),
    )
    positive_ok = bool(
        positive["search"]["status"] == "edge_found"
        and not positive["search"]["projection_counterexample"]
        and positive["replay"].get("admissible")
        and positive["replay"].get("goal_edge")
    )
    selected_ok = bool(
        selected["search"]["status"] == "edge_found"
        and not selected["search"]["projection_counterexample"]
        and selected["replay"].get("admissible")
        and selected["replay"].get("goal_edge")
        and selected["replay"].get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and selected["replay"].get("joint_sha256")
        == prior_search.EXPECTED_JOINT
    )
    witnesses_separated = bool(
        all(row["separated"] for row in world_witnesses.values())
        and all(row["separated"] for row in interface_witnesses.values())
    )
    passed = bool(
        codebook["state_count"] == 4
        and codebook["deterministic_changed_edges"]
        and codebook["single_cycle"]
        and witnesses_separated
        and positive_ok
        and selected_ok
    )
    payload = {
        "schema": "ztare-composed-world-resource-state-audit-v1",
        "status": (
            "composed_world_resource_state_confirmed"
            if passed
            else "composed_world_resource_state_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "parent_projection_sha256": parent.projection_sha256,
        "projection_sha256": projection.projection_sha256,
        "inference": inference,
        "codebook": codebook,
        "world_witnesses": world_witnesses,
        "interface_witnesses": interface_witnesses,
        "positive_control": positive,
        "selected_search": selected,
        "criteria": {
            "four_state_codebook": codebook["state_count"] == 4,
            "deterministic_single_cycle": (
                codebook["deterministic_changed_edges"]
                and codebook["single_cycle"]
            ),
            "all_four_witnesses_separated": witnesses_separated,
            "positive_edge": positive_ok,
            "selected_edge": selected_ok,
            "selected_joint_code": (
                selected["replay"].get("joint_sha256")
                == prior_search.EXPECTED_JOINT
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
        "criteria": payload["criteria"],
        "inference": {
            "background": inference["background"],
            "cell_count": len(inference["cells"]),
            "cells": inference["cells"],
        },
        "codebook": codebook,
        "positive": {
            "status": positive["search"]["status"],
            "actions": len(positive["search"]["actions"]),
            "generated": positive["search"]["generated"],
            "expanded": positive["search"]["expanded"],
            "counterexample": positive["search"]["projection_counterexample"],
        },
        "selected": {
            "status": selected["search"]["status"],
            "actions": len(selected["search"]["actions"]),
            "generated": selected["search"]["generated"],
            "expanded": selected["search"]["expanded"],
            "counterexample": selected["search"]["projection_counterexample"],
            "replay": selected["replay"],
        },
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
