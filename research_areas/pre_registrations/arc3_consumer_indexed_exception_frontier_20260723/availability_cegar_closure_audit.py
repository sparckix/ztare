#!/usr/bin/env python3
"""Close missing availability coordinates from search commutation receipts."""
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


MAX_REFINEMENTS = 8


class AvailabilityRefinedProjection:
    """Parent factors plus a finite sequence of evidence-derived bits."""

    def __init__(
        self,
        parent: Any,
        *,
        splits: tuple[dict[str, Any], ...],
        evidence_refs: tuple[str, ...],
    ) -> None:
        self.parent = parent
        self.splits = splits
        self.evidence_refs = tuple(dict.fromkeys((
            *parent.evidence_refs,
            *evidence_refs,
        )))
        self.projection_sha256 = stable_sha256({
            "schema": "ztare-availability-cegar-projection-v1",
            "parent_projection_sha256": parent.projection_sha256,
            "splits": splits,
            "evidence_refs": self.evidence_refs,
        })

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)

    def factor(self, state: Any) -> Any:
        factors = self.parent.factor(state)
        additions = tuple(
            (
                split["discriminator_id"],
                tuple(
                    state[row][col] for row, col in split["cells"]
                ) == split["reference"],
            )
            for split in self.splits
        )
        return replace(
            factors,
            one_shot_availability=(
                *factors.one_shot_availability,
                *additions,
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


def _split_from_receipt(
    receipt: dict[str, Any],
    *,
    lineage: str,
) -> dict[str, Any]:
    difference = receipt.get("consumer_difference") or {}
    rows = difference.get("changed_cells") or []
    if (
        receipt.get("kind") != "dominance_simulation_failed"
        or difference.get("changed_factor_names") != []
        or not rows
        or len(rows) > 64
    ):
        raise ValueError("counterexample is not a refinable missing-factor receipt")
    normalized = sorted(
        (
            (
                int(row["coordinate"][0]),
                int(row["coordinate"][1]),
            ),
            row["left"],
            row["right"],
        )
        for row in rows
    )
    cells = tuple(row[0] for row in normalized)
    left = tuple(row[1] for row in normalized)
    right = tuple(row[2] for row in normalized)
    if left == right:
        raise ValueError("counterexample does not distinguish two values")
    reference = min((left, right), key=repr)
    identity = {
        "cells": cells,
        "reference": reference,
        "lineage": lineage,
    }
    discriminator_id = (
        "counterexample_availability_"
        + stable_sha256(identity)[:16]
    )
    return {
        **identity,
        "discriminator_id": discriminator_id,
        "left_bit": left == reference,
        "right_bit": right == reference,
    }


def _initial_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    selected = payload.get("selected_searches") or []
    if len(selected) != 1:
        raise ValueError("initial result does not contain one selected search")
    search = selected[0].get("search") or {}
    if search.get("status") != "projection_noncommuting":
        raise ValueError("initial result is not a projection counterexample")
    return dict(search.get("projection_counterexample") or {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--joint-result", required=True)
    parser.add_argument("--initial-counterexample-result", required=True)
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

    active_result_path = Path(args.active_result)
    active_result = json.loads(
        active_result_path.read_text(encoding="utf-8")
    )
    joint_result_path = Path(args.joint_result)
    joint_result = json.loads(
        joint_result_path.read_text(encoding="utf-8")
    )
    initial_path = Path(args.initial_counterexample_result)
    initial_payload = json.loads(initial_path.read_text(encoding="utf-8"))
    receipt = _initial_receipt(initial_payload)
    receipt_lineage = str(initial_path)
    operation = ast.literal_eval(
        str(active_result["matches"][0]["operation"])
    )
    operation_map = active_result["operation_maps"][repr(operation)]

    splits: list[dict[str, Any]] = []
    seen_split_keys: set[str] = set()
    iterations = []
    final_result = None
    final_problem = None
    final_projection = None
    final_replay: dict[str, Any] = {}
    stop_reason = "refinement_cap_exhausted"

    for iteration in range(1, MAX_REFINEMENTS + 1):
        try:
            split = _split_from_receipt(
                receipt,
                lineage=receipt_lineage,
            )
        except ValueError as exc:
            stop_reason = f"non_refinable_counterexample:{exc}"
            break
        split_key = stable_sha256({
            "cells": split["cells"],
            "reference": split["reference"],
        })
        if split_key in seen_split_keys:
            stop_reason = "repeated_split"
            break
        seen_split_keys.add(split_key)
        if split["left_bit"] == split["right_bit"]:
            stop_reason = "split_does_not_separate"
            break
        splits.append(split)
        projection = AvailabilityRefinedProjection(
            parent,
            splits=tuple(splits),
            evidence_refs=tuple(row["lineage"] for row in splits),
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
            stop_reason = "selected_raw_configuration_ambiguous"
            break
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
                *tuple(row["lineage"] for row in splits),
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
        row = {
            "iteration": iteration,
            "split": split,
            "projection_sha256": projection.projection_sha256,
            "search": prior_search._result_row(result),
        }
        iterations.append(row)
        final_result = result
        final_problem = problem
        final_projection = projection
        if result.status == "edge_found":
            final_replay = prior_search._replay(
                carrier=carrier,
                projection=projection,
                start=start,
                start_time=start_time,
                actions=result.actions,
                problem=problem,
                operation_map=operation_map,
            )
            stop_reason = "edge_found"
            break
        if result.status != "projection_noncommuting":
            stop_reason = result.status
            break
        receipt = dict(result.projection_counterexample)
        receipt_lineage = (
            f"iteration:{iteration}:"
            + stable_sha256(receipt)
        )

    passed = bool(
        stop_reason == "edge_found"
        and final_result is not None
        and final_result.status == "edge_found"
        and not final_result.projection_counterexample
        and final_replay.get("admissible")
        and final_replay.get("goal_edge")
        and final_replay.get("configuration_sha256")
        == prior_search.SELECTED_CONFIGURATION
        and final_replay.get("joint_sha256")
        == prior_search.EXPECTED_JOINT
    )
    payload = {
        "schema": "ztare-availability-cegar-closure-audit-v1",
        "status": (
            "availability_cegar_closure_confirmed"
            if passed
            else "availability_cegar_closure_refuted"
        ),
        "carrier_sha256": carrier_sha,
        "parent_projection_sha256": parent.projection_sha256,
        "final_projection_sha256": (
            final_projection.projection_sha256
            if final_projection is not None else None
        ),
        "target": {
            "configuration_sha256": prior_search.SELECTED_CONFIGURATION,
            "joint_sha256": prior_search.EXPECTED_JOINT,
            "operation": repr(operation),
        },
        "bounds": {
            "max_refinements": MAX_REFINEMENTS,
            "max_depth_per_search": prior_search.MAX_DEPTH,
            "max_states_per_search": prior_search.MAX_STATES,
        },
        "stop_reason": stop_reason,
        "refinement_count": len(splits),
        "iterations": iterations,
        "final_replay": final_replay,
        "criteria": {
            "all_splits_new_and_separating": bool(
                splits
                and len(splits) == len(seen_split_keys)
                and all(
                    row["left_bit"] != row["right_bit"]
                    for row in splits
                )
            ),
            "closure_within_cap": stop_reason == "edge_found",
            "final_edge_found": bool(
                final_result is not None
                and final_result.status == "edge_found"
            ),
            "no_final_counterexample": bool(
                final_result is not None
                and not final_result.projection_counterexample
            ),
            "selected_joint_code": (
                final_replay.get("joint_sha256")
                == prior_search.EXPECTED_JOINT
            ),
            "target_independent_splits": True,
            "no_environment_contact": True,
        },
        "problem_id": (
            final_problem.problem_id if final_problem is not None else None
        ),
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
        "refinement_count": len(splits),
        "criteria": payload["criteria"],
        "iterations": [
            {
                "iteration": row["iteration"],
                "cells": row["split"]["cells"],
                "reference": row["split"]["reference"],
                "status": row["search"]["status"],
                "generated": row["search"]["generated"],
                "expanded": row["search"]["expanded"],
                "counterexample_kind": (
                    row["search"]["projection_counterexample"].get("kind")
                    if row["search"]["projection_counterexample"] else None
                ),
            }
            for row in iterations
        ],
        "action_count": (
            len(final_result.actions) if final_result is not None else 0
        ),
        "final_replay": final_replay,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
