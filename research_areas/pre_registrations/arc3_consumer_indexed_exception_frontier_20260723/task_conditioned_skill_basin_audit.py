#!/usr/bin/env python3
"""Run H77 against the frozen H63 mechanism snapshot and H71 relation."""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any, Hashable

import active_affordance_frontier_audit as active
import relational_factored_search_audit as relational

from ztare.common.equivariance import stable_sha256
from ztare.common.task_conditioned_reachability import (
    TaskRelationEdge,
    compile_task_reachability_basin,
    plan_task_conditioned_acquisition,
)
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import law_scored_view
from ztare.worldmodel.mechanism_effects import (
    HistoryTrajectoryEvidence,
    fiber_mechanism_effect,
    select_fiber_history_action_system,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


OPERATIONS = (0, 1, 2, 3)
EXPECTED_TASK_RELATION = (
    "c19683438c8aebf80055531bc063ab560e2cd5538de63675345cff4614438072"
)
EXPECTED_CONFIGURATION = (
    "4dd96788ba556af49abb6b84a143ff58f4e933b8c8c331159017b9c91d77a000"
)
ISOMORPHISM_DISPATCH_ID = (
    "b94f05b5460014852d685b92c0a512f6df71869c47bb5ddd321ffcf401af7fc2"
)


def _play_record(report: dict[str, Any], trace_ref: str) -> dict[str, Any]:
    cycles = report.get("cycles")
    if not isinstance(cycles, list):
        return report
    return next(
        (
            row
            for row in reversed(cycles)
            if isinstance(row, dict)
            and (
                not isinstance(row.get("eval_slice"), dict)
                or row["eval_slice"].get("path") == trace_ref
            )
        ),
        cycles[-1] if cycles else {},
    )


def _history_prefixes(
    play: dict[str, Any],
) -> tuple[tuple[Hashable, ...], tuple[Hashable, ...]]:
    segments = tuple(play.get("execution_segments") or ())
    active_index = next(
        (
            index
            for index, segment in enumerate(segments)
            if isinstance(segment, dict)
            and segment.get("segment_kind") == "active_control"
        ),
        0,
    )
    actions = tuple(
        play.get("active_action_history_prefix")
        or (
            action
            for segment in segments[:active_index]
            if isinstance(segment, dict)
            and segment.get("segment_kind") != "verified_origin"
            for action in (segment.get("actions") or ())
        )
    )
    effects = tuple(
        tuple(value)
        for value in (
            play.get("active_operation_effect_history_prefix") or ()
        )
    )
    return actions, effects


def _reconstruct_snapshot(
    *,
    project: Path,
    carrier: Any,
    carrier_sha256: str,
    carrier_execution_sha256: str,
    projection: Any,
    active_epoch: int,
    origin_seed_sha256: str,
    through_trace: str,
) -> dict[str, Any]:
    bank = EpisodeLog.read_jsonl(
        project / "raw/episodes/episode_001.jsonl"
    )
    active_rows = tuple(
        law_scored_view(bank, source_epoch=active_epoch)
    )
    known_law = {
        (row.s, row.a, row.s_next) for row in active_rows
    }
    report = json.loads(
        (project / "workspace/arc3_acquisition_probe_report.json")
        .read_text(encoding="utf-8")
    )
    play = _play_record(report, through_trace)
    default_actions, default_effects = _history_prefixes(play)

    ledger_path = project / "workspace/sealed_eval_slices.jsonl"
    ledger = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    positions = [
        index
        for index, row in enumerate(ledger)
        if str(row.get("path") or "") == through_trace
    ]
    if not positions:
        raise ValueError("H63 trace is absent from the sealed-slice ledger")
    ledger = ledger[:positions[-1] + 1]
    trajectories = []
    for row in ledger:
        if (
            (
                row.get("source_carrier_sha256") != carrier_sha256
                and row.get("source_carrier_execution_sha256")
                != carrier_execution_sha256
            )
            or row.get("source_epoch") != active_epoch
            or row.get("origin_seed_sha256") != origin_seed_sha256
        ):
            continue
        path = project / str(row.get("path") or "")
        if not path.is_file():
            continue
        transitions = tuple(EpisodeLog.read_jsonl(path))
        declared = row.get("non_discharge_edge_indices")
        declared = declared if isinstance(declared, list) else []
        boundaries = frozenset(
            int(index)
            for index in declared
            if isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(transitions)
            and (
                transitions[index].s,
                transitions[index].a,
                transitions[index].s_next,
            ) not in known_law
        )
        action_prefix = tuple(row.get("history_prefix_actions") or ())
        effect_prefix = tuple(
            tuple(value)
            for value in (
                row.get("history_prefix_operation_effects") or ()
            )
        )
        if not effect_prefix:
            action_prefix = ()
        trajectories.append(HistoryTrajectoryEvidence(
            transitions=transitions,
            action_prefix=action_prefix or default_actions,
            operation_effect_prefix=effect_prefix or default_effects,
            boundary_indices=boundaries,
            evidence_ref=str(row.get("path") or "sealed_slice"),
        ))
    selection = select_fiber_history_action_system(
        active_rows,
        projection=projection,
        evidence_ref="raw/episodes/episode_001.jsonl",
        history_trajectories=tuple(trajectories),
    )
    trace = tuple(EpisodeLog.read_jsonl(project / through_trace))
    if not trace:
        raise ValueError("H63 trace is empty")
    start_key = selection.start_key(
        projection.factor(trace[0].s),
        observation=trace[0].s,
        action_history=default_actions,
        operation_effect_history=default_effects,
    )
    return {
        "bank": bank,
        "active_rows": active_rows,
        "selection": selection,
        "trajectories": tuple(trajectories),
        "trace": trace,
        "start_key": start_key,
        "history_actions": default_actions,
        "history_effects": default_effects,
        "ledger_count": len(ledger),
    }


def _task_edges(
    *,
    system: Any,
    projection: Any,
    operation_maps: dict[str, dict[str, Any]],
    target_sha256: str,
    task_evidence_ref: str,
) -> tuple[tuple[TaskRelationEdge, ...], list[dict[str, Any]]]:
    edges = []
    diagnostics = []
    for source_key, fiber in system.fibers.items():
        representative = fiber.representative
        observation = getattr(
            representative,
            "observation",
            representative,
        )
        for operation in OPERATIONS:
            descriptor = relational._descriptor_receipt(
                observation,
                operation,
                projection=projection,
                operation_maps=operation_maps,
            )
            if (
                descriptor.get("status") != "admissible"
                or descriptor.get("joint_sha256") != target_sha256
            ):
                continue
            edges.append(TaskRelationEdge(
                source=source_key,
                operation=operation,
                hypothesis_id="joint_affordance:" + target_sha256,
                evidence_refs=(
                    fiber.evidence_ref,
                    task_evidence_ref,
                ),
            ))
            diagnostics.append({
                "source_key_sha256": stable_sha256(source_key),
                "source_observation_sha256": stable_sha256(observation),
                "operation": repr(operation),
                "source_evidence_ref": fiber.evidence_ref,
                "descriptor": descriptor,
            })
    return tuple(edges), diagnostics


def _concrete_transport(
    *,
    carrier: Any,
    projection: Any,
    selection: Any,
    system: Any,
    start_key: Hashable,
    start_state: Any,
    start_time: int,
) -> dict[str, Any]:
    concrete: dict[Hashable, tuple[Any, int, tuple[Hashable, ...]]] = {
        start_key: (start_state, start_time, ())
    }
    queue = deque((start_key,))
    failures = []
    boundary_classes = frozenset(system.boundary_kinds)
    while queue:
        source = queue.popleft()
        state, time, path = concrete[source]
        for operation in OPERATIONS:
            key = source, operation
            effects = system.relation_effects.get(key)
            targets = system.relation_targets.get(key, frozenset())
            if (
                not effects
                or len(targets) != 1
                or any(
                    (operation, effect) in boundary_classes
                    for effect in effects
                )
            ):
                continue
            predicted = carrier(state, operation, time)
            if predicted is None:
                failures.append({
                    "source_sha256": stable_sha256(source),
                    "operation": repr(operation),
                    "kind": "carrier_undefined",
                    "path": list(map(repr, path)),
                })
                continue
            predicted_key = selection.start_key(
                projection.factor(predicted),
                observation=predicted,
            )
            expected = next(iter(targets))
            if predicted_key != expected:
                failures.append({
                    "source_sha256": stable_sha256(source),
                    "operation": repr(operation),
                    "kind": "task_chart_transport_noncommuting",
                    "expected_target_sha256": stable_sha256(expected),
                    "predicted_target_sha256": stable_sha256(predicted_key),
                    "path": list(map(repr, path)),
                })
                continue
            if expected not in concrete:
                concrete[expected] = (
                    predicted,
                    int(time) + 1,
                    (*path, operation),
                )
                queue.append(expected)
    return {
        "concrete": concrete,
        "failures": failures,
    }


def _replay_route(
    *,
    route: Any,
    carrier: Any,
    projection: Any,
    selection: Any,
    operation_maps: dict[str, dict[str, Any]],
    target_sha256: str,
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
                "source_key_sha256": stable_sha256(source_key),
                "expected_source_sha256": stable_sha256(expected_source),
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
    descriptor = relational._descriptor_receipt(
        state,
        route.probe_operation,
        projection=projection,
        operation_maps=operation_maps,
    )
    return {
        "status": (
            "replayed_relation_edge"
            if descriptor.get("joint_sha256") == target_sha256
            else "route_relation_mismatch"
        ),
        "rows": rows,
        "terminal_source_sha256": stable_sha256(state),
        "terminal_time": time,
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
    target_sha256 = str(
        h71["prior_tests"]["joint"]["template_sha256"]
    )
    if target_sha256 != EXPECTED_TASK_RELATION:
        raise SystemExit("H71 task relation identity drifted")
    active_matches = h71["active"]["matches"]["joint"]
    if {
        str(row["configuration_sha256"]) for row in active_matches
    } != {EXPECTED_CONFIGURATION}:
        raise SystemExit("H71 active relation preimage drifted")

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
    snapshot = _reconstruct_snapshot(
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
        raise SystemExit(
            "H63 action-system reconstruction drifted: "
            f"{system.sha256} != {expected_system_sha256}"
        )

    operation_maps = active._operation_maps(
        snapshot["active_rows"],
        projection=projection,
    )
    if tuple(
        operation
        for operation in OPERATIONS
        if operation_maps[repr(operation)].get("admitted")
    ) != OPERATIONS:
        raise SystemExit("active evidence no longer admits four operations")
    task_edges, task_edge_diagnostics = _task_edges(
        system=system,
        projection=projection,
        operation_maps=operation_maps,
        target_sha256=target_sha256,
        task_evidence_ref=str(h71_path),
    )
    if not task_edges:
        payload = {
            "schema": "ztare-task-conditioned-skill-basin-audit-v1",
            "hypothesis_id": (
                "H-GPSA-TASK-CONDITIONED-SKILL-BASIN-20260727-77"
            ),
            "status": "task_relation_unrepresented",
            "isomorphism": {
                "dispatch_id": ISOMORPHISM_DISPATCH_ID,
                "selected_mother_structure": (
                    "guarded reachability kernel with "
                    "evidence/postcondition adjunction"
                ),
                "rejected_candidate": (
                    "fibered closure operator additive-law candidate"
                ),
            },
            "identities": {
                "carrier_sha256": carrier_sha256,
                "carrier_execution_sha256": execution_sha256,
                "projection_sha256": projection.projection_sha256,
                "task_relation_sha256": target_sha256,
                "task_configuration_sha256": EXPECTED_CONFIGURATION,
                "origin_seed_sha256": origin_seed_sha256,
                "start_state_sha256": stable_sha256(
                    snapshot["trace"][0].s
                ),
                "start_source_key_sha256": stable_sha256(
                    snapshot["start_key"]
                ),
                "evidence_through_trace": through_trace,
                "source_system_sha256": system.sha256,
            },
            "snapshot_reconstruction": {
                "ledger_row_count": snapshot["ledger_count"],
                "matched_trajectory_count": len(
                    snapshot["trajectories"]
                ),
                "history_kind": selection.history_kind,
                "history_suffix_length": selection.suffix_length,
                "observation_count": selection.observation_count,
                "fiber_count": len(system.fibers),
                "relation_count": len(system.relation_effects),
                "noncommuting_relation_count": len(
                    system.noncommuting_relations
                ),
                "matches_h63": system.sha256 == expected_system_sha256,
            },
            "control_join": {
                "checked_source_operation_pairs": (
                    len(system.fibers) * len(OPERATIONS)
                ),
                "matched_pair_count": 0,
                "status": "empty",
            },
            "task_edge_count": 0,
            "task_edges": task_edge_diagnostics,
            "basin": None,
            "start_membership": {
                "may": None,
                "must": None,
                "reason": "task relation has no control-fiber member",
            },
            "plan": {
                "schema": "ztare-task-conditioned-acquisition-plan-v1",
                "status": "task_relation_unrepresented",
                "route": None,
                "selected_frontier": None,
                "task_changing_frontier": [],
            },
            "route_replay": None,
            "concrete_transport": None,
        }
        output = Path(args.output)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "output": str(output),
            "status": payload["status"],
            "task_edge_count": 0,
            "checked_source_operation_pairs": (
                len(system.fibers) * len(OPERATIONS)
            ),
            "source_system_matches_h63": True,
        }, indent=2, sort_keys=True))
        return 0
    basin = compile_task_reachability_basin(
        system,
        task_edges=task_edges,
        task_relation_sha256=target_sha256,
        operations=OPERATIONS,
    )
    start_key = snapshot["start_key"]
    trace = snapshot["trace"]
    transport = _concrete_transport(
        carrier=carrier,
        projection=projection,
        selection=selection,
        system=system,
        start_key=start_key,
        start_state=trace[0].s,
        start_time=int(trace[0].t),
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

    plan = plan_task_conditioned_acquisition(
        basin,
        start_source=start_key,
        predict_targets=predict_targets,
    )
    replay = (
        _replay_route(
            route=plan.route,
            carrier=carrier,
            projection=projection,
            selection=selection,
            operation_maps=operation_maps,
            target_sha256=target_sha256,
            start_state=trace[0].s,
            start_time=int(trace[0].t),
        )
        if plan.route is not None
        else None
    )
    payload = {
        "schema": "ztare-task-conditioned-skill-basin-audit-v1",
        "hypothesis_id": (
            "H-GPSA-TASK-CONDITIONED-SKILL-BASIN-20260727-77"
        ),
        "isomorphism": {
            "dispatch_id": ISOMORPHISM_DISPATCH_ID,
            "selected_mother_structure": (
                "guarded reachability kernel with "
                "evidence/postcondition adjunction"
            ),
            "rejected_candidate": (
                "fibered closure operator additive-law candidate"
            ),
        },
        "identities": {
            "carrier_sha256": carrier_sha256,
            "carrier_execution_sha256": execution_sha256,
            "projection_sha256": projection.projection_sha256,
            "task_relation_sha256": target_sha256,
            "task_configuration_sha256": EXPECTED_CONFIGURATION,
            "task_contract_sha256": str(
                active_payload["active_problem"].get(
                    "task_contract_sha256",
                    "",
                )
            ),
            "origin_seed_sha256": origin_seed_sha256,
            "start_state_sha256": stable_sha256(trace[0].s),
            "start_source_key_sha256": stable_sha256(start_key),
            "evidence_through_trace": through_trace,
            "source_system_sha256": system.sha256,
        },
        "snapshot_reconstruction": {
            "ledger_row_count": snapshot["ledger_count"],
            "matched_trajectory_count": len(snapshot["trajectories"]),
            "history_kind": selection.history_kind,
            "history_suffix_length": selection.suffix_length,
            "observation_count": selection.observation_count,
            "fiber_count": len(system.fibers),
            "relation_count": len(system.relation_effects),
            "noncommuting_relation_count": len(
                system.noncommuting_relations
            ),
            "matches_h63": system.sha256 == expected_system_sha256,
        },
        "task_edge_count": len(task_edges),
        "task_edges": task_edge_diagnostics,
        "basin": basin.to_receipt(),
        "start_membership": {
            "may": start_key in basin.may_sources,
            "must": start_key in basin.must_sources,
            "decision_class_id": (
                basin.decision_class_by_source[start_key]
            ),
        },
        "plan": plan.to_receipt(),
        "route_replay": replay,
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
        "task_edge_count": len(task_edges),
        "may_source_count": len(basin.may_sources),
        "must_source_count": len(basin.must_sources),
        "interval_source_count": len(basin.interval_sources),
        "start_membership": payload["start_membership"],
        "plan_status": plan.status,
        "route_replay_status": (
            replay.get("status") if replay is not None else None
        ),
        "transported_source_count": len(concrete),
        "transport_failure_count": len(transport["failures"]),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
