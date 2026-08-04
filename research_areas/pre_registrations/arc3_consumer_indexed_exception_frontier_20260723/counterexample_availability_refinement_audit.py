#!/usr/bin/env python3
"""Refine one unsound search fiber from its commutation counterexample."""
from __future__ import annotations

import argparse
import ast
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

import joint_affordance_search_audit as prior_search
import joint_equivariant_affordance_audit as joint

from ztare.common.equivariance import stable_sha256
from ztare.common.factored_search import search_factored
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.compiled_fiber_planning import CompiledFiberSearchProblem
from ztare.worldmodel.episode_log import EpisodeLog


class CounterexampleAvailabilityProjection:
    """One evidence-owned equality split over a parent projection."""

    def __init__(
        self,
        parent: Any,
        *,
        cells: tuple[tuple[int, int], ...],
        reference: tuple[Any, ...],
        evidence_ref: str,
    ) -> None:
        self.parent = parent
        self.cells = cells
        self.reference = reference
        self.discriminator_id = (
            "counterexample_availability_"
            + stable_sha256({
                "parent_projection_sha256": parent.projection_sha256,
                "cells": cells,
                "reference": reference,
                "evidence_ref": evidence_ref,
            })[:16]
        )
        self.evidence_refs = tuple(dict.fromkeys((
            *parent.evidence_refs,
            evidence_ref,
        )))
        self.projection_sha256 = stable_sha256({
            "schema": "ztare-counterexample-availability-projection-v1",
            "parent_projection_sha256": parent.projection_sha256,
            "discriminator_id": self.discriminator_id,
            "cells": cells,
            "reference": reference,
            "evidence_refs": self.evidence_refs,
        })

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def factor(self, state: Any) -> Any:
        parent = self.parent.factor(state)
        observed = tuple(state[row][col] for row, col in self.cells)
        availability = (
            *parent.one_shot_availability,
            (self.discriminator_id, observed == self.reference),
        )
        return replace(parent, one_shot_availability=availability)

    def explain_state_difference(
        self,
        left: Any,
        right: Any,
    ) -> dict[str, Any]:
        payload = dict(self.parent.explain_state_difference(left, right))
        left_factor = self.factor(left)
        right_factor = self.factor(right)
        payload["changed_factor_names"] = [
            name
            for name in self.factor_names
            if (
                left_factor.as_mapping()[name]
                != right_factor.as_mapping()[name]
            )
        ]
        return payload


def _counterexample(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], tuple[tuple[int, int], ...], tuple[Any, ...]]:
    selected = payload.get("selected_searches") or []
    if len(selected) != 1:
        raise ValueError("H35 does not contain one selected search")
    search = selected[0].get("search") or {}
    receipt = search.get("projection_counterexample") or {}
    difference = receipt.get("consumer_difference") or {}
    changed = difference.get("changed_cells") or []
    if (
        search.get("status") != "projection_noncommuting"
        or receipt.get("kind") != "dominance_simulation_failed"
        or receipt.get("dominator_time") != receipt.get("dominated_time")
        or difference.get("changed_factor_names") != []
        or not changed
        or len(changed) > 64
    ):
        raise ValueError("H35 counterexample does not satisfy refinement contract")
    cells = tuple(
        (int(row["coordinate"][0]), int(row["coordinate"][1]))
        for row in changed
    )
    left = tuple(row["left"] for row in changed)
    right = tuple(row["right"] for row in changed)
    if left == right:
        raise ValueError("counterexample values do not separate")
    reference = min((left, right), key=repr)
    return receipt, cells, reference


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
    receipt, cells, reference = _counterexample(counterexample_payload)
    projection = CounterexampleAvailabilityProjection(
        parent,
        cells=cells,
        reference=reference,
        evidence_ref=str(counterexample_path),
    )
    left_bit = tuple(
        row["left"]
        for row in receipt["consumer_difference"]["changed_cells"]
    ) == reference
    right_bit = tuple(
        row["right"]
        for row in receipt["consumer_difference"]["changed_cells"]
    ) == reference
    separates_counterexample = left_bit != right_bit

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
    configurations = prior_search._selected_raw_configurations(
        project=project,
        projection=projection,
        joint_result=joint_result,
    )
    if len(configurations) != 1:
        raise SystemExit(
            f"expected one raw selected configuration, found {len(configurations)}"
        )
    configuration = configurations[0]
    target_factors = replace(
        projection.factor(target["grid"]),
        finite_configuration=configuration["raw_configuration"],
    )
    problem = CompiledFiberSearchProblem(
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
        separates_counterexample
        and result.status == "edge_found"
        and not result.projection_counterexample
        and replay.get("admissible")
        and replay.get("goal_edge")
        and replay.get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
    )
    payload = {
        "schema": "ztare-counterexample-availability-refinement-audit-v1",
        "status": (
            "counterexample_availability_refinement_confirmed"
            if passed
            else "counterexample_availability_refinement_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "parent_projection_sha256": parent.projection_sha256,
        "projection_sha256": projection.projection_sha256,
        "refinement": {
            "counterexample_result": str(counterexample_path),
            "kind": receipt["kind"],
            "same_time": (
                receipt["dominator_time"] == receipt["dominated_time"]
            ),
            "cells": cells,
            "reference": reference,
            "discriminator_id": projection.discriminator_id,
            "left_bit": left_bit,
            "right_bit": right_bit,
            "separates_counterexample": separates_counterexample,
            "target_independent": True,
        },
        "target": {
            "configuration_sha256": prior_search.SELECTED_CONFIGURATION,
            "joint_sha256": prior_search.EXPECTED_JOINT,
            "controlled_base": target_factors.controlled_base,
            "operation": repr(operation),
            "evidence_refs": configuration["evidence_refs"],
        },
        "search": prior_search._result_row(result),
        "replay": replay,
        "criteria": {
            "valid_counterexample": True,
            "separates_counterexample": separates_counterexample,
            "edge_found": result.status == "edge_found",
            "no_new_projection_counterexample": (
                not result.projection_counterexample
            ),
            "selected_joint_code": (
                replay.get("joint_sha256") == prior_search.EXPECTED_JOINT
            ),
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
        "refinement": payload["refinement"],
        "search": {
            key: value
            for key, value in payload["search"].items()
            if key not in {"actions", "continuation_actions"}
        },
        "action_count": len(result.actions),
        "replay": replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
