#!/usr/bin/env python3
"""Run H78: join every calibrated task relation to concrete H63 edges."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Hashable

import active_affordance_frontier_audit as active
import joint_equivariant_affordance_audit as joint
import task_conditioned_skill_basin_audit as h77

from ztare.common.equivariance import stable_sha256
from ztare.common.task_conditioned_reachability import (
    TaskRelationEdge,
    compile_task_reachability_basin,
    plan_task_conditioned_acquisition,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


OPERATIONS = (0, 1, 2, 3)
CODE_NAMES = (
    "joint",
    "footprint_only",
    "configuration_only",
    "independent_product",
)


def _descriptor_codes(
    source: Any,
    operation: Hashable,
    *,
    projection: Any,
    operation_maps: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    operation_row = operation_maps.get(repr(operation))
    if operation_row is None or not operation_row.get("admitted"):
        return {"status": "inadmissible_operation"}
    factors = projection.factor(source)
    origins = tuple(factors.controlled_base)
    configuration = joint._square(tuple(factors.finite_configuration))
    if len(origins) != 1 or configuration is None:
        return {
            "status": "factor_domain_failure",
            "controlled_origin_count": len(origins),
            "configuration_length": len(factors.finite_configuration),
        }
    origin = origins[0]
    delta_row, delta_col = operation_row["vector"]
    attempted = origin[0] + delta_row, origin[1] + delta_col
    height = len(projection.sprite)
    width = len(projection.sprite[0])
    footprint = joint.affordance._window(
        source,
        top=attempted[0],
        left=attempted[1],
        size=max(height, width),
        current_origin=origin,
        sprite_shape=(height, width),
    )
    codes = joint._codes(footprint, configuration)
    return {
        "status": "admissible",
        "operation": repr(operation),
        "controlled_origin": origin,
        "attempted_origin": attempted,
        "configuration_sha256": stable_sha256(
            joint.affordance._configuration_partition(
                tuple(factors.finite_configuration)
            )
        ),
        "codes": {
            name: {
                key: value
                for key, value in code.items()
                if key != "value"
            }
            for name, code in codes.items()
        },
    }


def _task_open_paths(
    project: Path,
    *,
    through_trace: str,
) -> dict[str, dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (
            project / "workspace/sealed_eval_slices.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    positions = [
        index
        for index, row in enumerate(rows)
        if str(row.get("path") or "") == through_trace
    ]
    if not positions:
        raise ValueError("H63 causal cut is absent from the sealed ledger")
    return {
        str(row.get("path") or ""): row
        for row in rows[:positions[-1] + 1]
        if row.get("task_discharge_status") == "open"
    }


def _replay_code_route(
    *,
    route: Any,
    code_name: str,
    template_sha256: str,
    carrier: Any,
    projection: Any,
    selection: Any,
    operation_maps: dict[str, dict[str, Any]],
    start_state: Any,
    start_time: int,
) -> dict[str, Any]:
    state = start_state
    time = start_time
    rows = []
    for index, operation in enumerate(route.preparation):
        source_key = selection.start_key(
            projection.factor(state),
            observation=state,
        )
        expected_source = route.source_path[index]
        if source_key != expected_source:
            return {
                "status": "route_source_transport_noncommuting",
                "failed_index": index,
                "rows": rows,
            }
        predicted = carrier(state, operation, time)
        if predicted is None:
            return {
                "status": "route_carrier_undefined",
                "failed_index": index,
                "rows": rows,
            }
        target_key = selection.start_key(
            projection.factor(predicted),
            observation=predicted,
        )
        expected_target = route.source_path[index + 1]
        rows.append({
            "index": index,
            "operation": repr(operation),
            "source_key_sha256": stable_sha256(source_key),
            "target_key_sha256": stable_sha256(target_key),
            "expected_target_sha256": stable_sha256(expected_target),
        })
        if target_key != expected_target:
            return {
                "status": "route_target_transport_noncommuting",
                "failed_index": index,
                "rows": rows,
            }
        state = predicted
        time = int(time) + 1
    descriptor = _descriptor_codes(
        state,
        route.probe_operation,
        projection=projection,
        operation_maps=operation_maps,
    )
    actual = (
        descriptor.get("codes", {})
        .get(code_name, {})
        .get("sha256")
    )
    return {
        "status": (
            "replayed_relation_edge"
            if actual == template_sha256
            else "route_relation_mismatch"
        ),
        "rows": rows,
        "terminal_time": time,
        "terminal_source_sha256": stable_sha256(state),
        "descriptor": descriptor,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--h63-result", required=True)
    parser.add_argument("--h71-result", required=True)
    parser.add_argument("--active-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    h63_path = Path(args.h63_result).resolve()
    h71_path = Path(args.h71_result).resolve()
    h63 = json.loads(h63_path.read_text(encoding="utf-8"))
    h71 = json.loads(h71_path.read_text(encoding="utf-8"))
    active_payload = json.loads(
        Path(args.active_result).read_text(encoding="utf-8")
    )
    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha256 = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("current carrier has no compiled fiber projection")
    execution_sha256 = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )
    active_epoch = int(h71["active"]["epoch"])
    origin_seed_sha256 = str(
        active_payload["active_problem"]["current_seed_sha256"]
    )
    through_trace = str(h63["history_snapshot"]["through_trace"])
    snapshot = h77._reconstruct_snapshot(
        project=project,
        carrier=carrier,
        carrier_sha256=carrier_sha256,
        carrier_execution_sha256=execution_sha256,
        projection=projection,
        active_epoch=active_epoch,
        origin_seed_sha256=origin_seed_sha256,
        through_trace=through_trace,
    )
    selection = snapshot["selection"]
    system = selection.action_system
    expected_system_sha256 = str(
        h63["history_lift"]["action_system_sha256"]
    )
    if system.sha256 != expected_system_sha256:
        raise SystemExit("H63 action-system reconstruction drifted")
    operation_maps = active._operation_maps(
        snapshot["active_rows"],
        projection=projection,
    )
    templates = {
        name: str(h71["prior_tests"][name]["template_sha256"])
        for name in CODE_NAMES
    }

    matches_by_code: dict[str, list[TaskRelationEdge]] = defaultdict(list)
    pair_diagnostics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source_key, fiber in system.fibers.items():
        representative = getattr(
            fiber.representative,
            "observation",
            fiber.representative,
        )
        for operation in OPERATIONS:
            descriptor = _descriptor_codes(
                representative,
                operation,
                projection=projection,
                operation_maps=operation_maps,
            )
            if descriptor["status"] != "admissible":
                continue
            for name in CODE_NAMES:
                if (
                    descriptor["codes"][name]["sha256"]
                    != templates[name]
                ):
                    continue
                matches_by_code[name].append(TaskRelationEdge(
                    source=source_key,
                    operation=operation,
                    hypothesis_id=f"{name}:{templates[name]}",
                    evidence_refs=(fiber.evidence_ref, str(h71_path)),
                ))
                pair_diagnostics[name].append({
                    "source_key_sha256": stable_sha256(source_key),
                    "source_observation_sha256": stable_sha256(
                        representative
                    ),
                    "operation": repr(operation),
                    "source_evidence_ref": fiber.evidence_ref,
                    "descriptor": descriptor,
                })

    open_rows = _task_open_paths(
        project,
        through_trace=through_trace,
    )
    open_matches: dict[str, dict[tuple[str, str], set[str]]] = {
        name: defaultdict(set) for name in CODE_NAMES
    }
    eligible_transition_count = 0
    for trajectory in snapshot["trajectories"]:
        if trajectory.evidence_ref not in open_rows:
            continue
        for index, transition in enumerate(trajectory.transitions):
            eligible_transition_count += 1
            descriptor = _descriptor_codes(
                transition.s,
                transition.a,
                projection=projection,
                operation_maps=operation_maps,
            )
            if descriptor["status"] != "admissible":
                continue
            pair_key = (
                stable_sha256(transition.s),
                repr(transition.a),
            )
            evidence_ref = f"{trajectory.evidence_ref}#{index}"
            for name in CODE_NAMES:
                if (
                    descriptor["codes"][name]["sha256"]
                    == templates[name]
                ):
                    open_matches[name][pair_key].add(evidence_ref)

    def classify(names: tuple[str, ...]) -> dict[str, str]:
        dispositions = {}
        for name in names:
            prior_negative = int(
                h71["prior_tests"][name]["negative_match_count"]
            )
            active_negative = len(open_matches[name])
            if prior_negative or active_negative:
                dispositions[name] = "refuted"
            elif matches_by_code[name]:
                dispositions[name] = "control_supported"
            else:
                dispositions[name] = "unrepresented"
        return dispositions

    dispositions = classify(CODE_NAMES)
    order_invariant = dispositions == classify(tuple(reversed(CODE_NAMES)))
    transport = h77._concrete_transport(
        carrier=carrier,
        projection=projection,
        selection=selection,
        system=system,
        start_key=snapshot["start_key"],
        start_state=snapshot["trace"][0].s,
        start_time=int(snapshot["trace"][0].t),
    )
    concrete = transport["concrete"]

    def predict_targets(
        source: Hashable,
        operation: Hashable,
    ) -> tuple[Hashable, ...]:
        row = concrete.get(source)
        if row is None:
            return ()
        state, time, _path = row
        predicted = carrier(state, operation, time)
        if predicted is None:
            return ()
        return (
            selection.start_key(
                projection.factor(predicted),
                observation=predicted,
            ),
        )

    candidates = []
    for name in CODE_NAMES:
        prior = h71["prior_tests"][name]
        active_refs = sorted({
            ref
            for refs in open_matches[name].values()
            for ref in refs
        })
        row = {
            "hypothesis_id": f"{name}:{templates[name]}",
            "code_name": name,
            "template_sha256": templates[name],
            "prior_positive_match_count": int(
                prior["positive_match_count"]
            ),
            "prior_negative_match_count": int(
                prior["negative_match_count"]
            ),
            "control_pair_match_count": len(matches_by_code[name]),
            "task_open_pair_match_count": len(open_matches[name]),
            "task_open_evidence_refs": active_refs,
            "disposition": dispositions[name],
            "control_pair_matches": pair_diagnostics[name],
            "basin": None,
            "plan": None,
            "route_replay": None,
        }
        if dispositions[name] == "control_supported":
            basin = compile_task_reachability_basin(
                system,
                task_edges=matches_by_code[name],
                task_relation_sha256=templates[name],
                operations=OPERATIONS,
            )
            plan = plan_task_conditioned_acquisition(
                basin,
                start_source=snapshot["start_key"],
                predict_targets=predict_targets,
            )
            replay = (
                _replay_code_route(
                    route=plan.route,
                    code_name=name,
                    template_sha256=templates[name],
                    carrier=carrier,
                    projection=projection,
                    selection=selection,
                    operation_maps=operation_maps,
                    start_state=snapshot["trace"][0].s,
                    start_time=int(snapshot["trace"][0].t),
                )
                if plan.route is not None
                else None
            )
            row["basin"] = basin.to_receipt()
            row["plan"] = plan.to_receipt()
            row["route_replay"] = replay
        candidates.append(row)

    supported = [
        row["hypothesis_id"]
        for row in candidates
        if row["disposition"] == "control_supported"
    ]
    unrepresented = [
        row["hypothesis_id"]
        for row in candidates
        if row["disposition"] == "unrepresented"
    ]
    status = (
        "control_supported_hypotheses_available"
        if supported
        else "representation_acquisition_required"
        if unrepresented
        else "task_version_space_refuted"
    )
    payload = {
        "schema": "ztare-task-carrier-join-audit-v1",
        "hypothesis_id": "H-GPSA-TASK-CARRIER-JOIN-20260727-78",
        "status": status,
        "identities": {
            "carrier_sha256": carrier_sha256,
            "carrier_execution_sha256": execution_sha256,
            "projection_sha256": projection.projection_sha256,
            "source_system_sha256": system.sha256,
            "evidence_through_trace": through_trace,
            "origin_seed_sha256": origin_seed_sha256,
        },
        "source_system_matches_h63": (
            system.sha256 == expected_system_sha256
        ),
        "checked_control_pair_count": (
            len(system.fibers) * len(OPERATIONS)
        ),
        "eligible_task_open_transition_count": eligible_transition_count,
        "candidate_order_invariant": order_invariant,
        "supported_hypothesis_ids": supported,
        "unrepresented_hypothesis_ids": unrepresented,
        "candidates": candidates,
        "concrete_transport": {
            "reachable_source_count": len(concrete),
            "failure_count": len(transport["failures"]),
            "failures": transport["failures"][:40],
        },
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "status": status,
        "checked_control_pair_count": payload[
            "checked_control_pair_count"
        ],
        "eligible_task_open_transition_count": (
            eligible_transition_count
        ),
        "candidate_order_invariant": order_invariant,
        "candidates": [
            {
                "code_name": row["code_name"],
                "control_pair_match_count": row[
                    "control_pair_match_count"
                ],
                "task_open_pair_match_count": row[
                    "task_open_pair_match_count"
                ],
                "disposition": row["disposition"],
                "plan_status": (
                    row["plan"].get("status")
                    if row["plan"] else None
                ),
                "route_replay_status": (
                    row["route_replay"].get("status")
                    if row["route_replay"] else None
                ),
            }
            for row in candidates
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
