#!/usr/bin/env python3
"""Lower a frozen prior-success affordance onto the active control frontier."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
from typing import Any

import terminal_affordance_relation_audit as affordance

from ztare.common.boundary_reachability import (
    compile_boundary_reachability_fibers,
)
from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import law_scored_view
from ztare.worldmodel.mechanism_effects import (
    HistoryTrajectoryEvidence,
    fiber_mechanism_effect,
)
from ztare.worldmodel.patch_base_carrier import (
    carrier_execution_sha256_from_source,
)


OPERATIONS = (0, 1, 2, 3)


def _operation_maps(
    transitions: tuple[Any, ...],
    *,
    projection: Any,
) -> dict[str, dict[str, Any]]:
    counts: dict[Any, Counter] = defaultdict(Counter)
    for transition in transitions:
        identity = getattr(transition, "identity", None)
        if identity is not None and identity.is_authoritative and identity.is_boundary:
            continue
        effect = fiber_mechanism_effect(
            projection.factor(transition.s),
            projection.factor(transition.s_next),
        )
        vector = affordance._translation(effect)
        if vector is not None:
            counts[transition.a][vector] += 1
    output = {}
    for operation in OPERATIONS:
        ranked = sorted(
            counts.get(operation, {}).items(),
            key=lambda item: (-item[1], repr(item[0])),
        )
        if not ranked:
            output[repr(operation)] = {
                "operation": repr(operation),
                "admitted": False,
                "support": 0,
                "runner_up_support": 0,
                "alternatives": [],
            }
            continue
        vector, support = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        output[repr(operation)] = {
            "operation": repr(operation),
            "vector": vector,
            "support": support,
            "runner_up_support": runner_up,
            "admitted": support >= 2 and support > runner_up,
            "alternatives": [
                {"vector": candidate, "support": count}
                for candidate, count in ranked
            ],
        }
    return output


def _play_row(report: dict[str, Any], trace_ref: str) -> dict[str, Any]:
    cycles = report.get("cycles")
    if not isinstance(cycles, list):
        return report
    return next(
        (
            row for row in reversed(cycles)
            if isinstance(row, dict)
            and (
                not isinstance(row.get("eval_slice"), dict)
                or row["eval_slice"].get("path") == trace_ref
            )
        ),
        report,
    )


def _active_problem(
    *,
    project: Path,
    trace_path: Path,
    report_path: Path,
    carrier: Any,
    carrier_sha: str,
    carrier_execution_sha: str,
    projection: Any,
) -> tuple[Any, Any, Any, tuple[Any, ...], dict[str, Any]]:
    bank = EpisodeLog.read_jsonl(project / "raw/episodes/episode_001.jsonl")
    trace_rows = tuple(EpisodeLog.read_jsonl(trace_path))
    if not trace_rows or trace_rows[0].identity is None:
        raise ValueError("active trace lacks source-epoch identity")
    active_epoch = trace_rows[0].identity.source_epoch
    active_rows = tuple(law_scored_view(bank, source_epoch=active_epoch))
    known_law_triples = {
        (transition.s, transition.a, transition.s_next)
        for transition in active_rows
    }
    report = json.loads(report_path.read_text(encoding="utf-8"))
    trace_ref = str(trace_path.relative_to(project))
    play = _play_row(report, trace_ref)
    declared = (
        play.get("non_discharge_edge_indices")
        or play.get("new_non_discharge_edge_indices")
        or ()
    )
    boundary_indices = frozenset(
        int(index)
        for index in declared
        if (
            isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(trace_rows)
            and (
                trace_rows[index].s,
                trace_rows[index].a,
                trace_rows[index].s_next,
            ) not in known_law_triples
        )
    )
    history_prefix = tuple(play.get("active_action_history_prefix") or ())
    effect_prefix = tuple(
        tuple(token)
        for token in (play.get("active_operation_effect_history_prefix") or ())
    )
    boundary_edges = tuple(
        (
            trace_rows[index].s,
            trace_rows[index].a,
            f"{trace_ref}#{index}",
            (*history_prefix, *(row.a for row in trace_rows[:index])),
            (),
        )
        for index in sorted(boundary_indices)
    )
    current_seed_sha = str(
        (play.get("seed_replay") or {}).get("seed_sha256")
        or (report.get("seed_replay") or {}).get("seed_sha256")
        or ""
    )
    if not current_seed_sha:
        current_seed_sha = hashlib.sha256(
            (project / "workspace/latest_level_boundary_seed.json").read_bytes()
        ).hexdigest()

    trajectories = []
    ledger_path = project / "workspace/sealed_eval_slices.jsonl"
    for ledger_row in (
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ):
        if (
            (
                ledger_row.get("source_carrier_sha256") != carrier_sha
                and ledger_row.get("source_carrier_execution_sha256")
                != carrier_execution_sha
            )
            or ledger_row.get("source_epoch") != active_epoch
            or ledger_row.get("origin_seed_sha256") != current_seed_sha
        ):
            continue
        slice_path = project / str(ledger_row.get("path") or "")
        if not slice_path.is_file():
            continue
        rows = tuple(EpisodeLog.read_jsonl(slice_path))
        declared_indices = ledger_row.get("non_discharge_edge_indices")
        declared_indices = (
            declared_indices if isinstance(declared_indices, list) else []
        )
        indices = frozenset(
            int(index)
            for index in declared_indices
            if (
                isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < len(rows)
                and (
                    rows[index].s,
                    rows[index].a,
                    rows[index].s_next,
                ) not in known_law_triples
            )
        )
        stored_action_prefix = tuple(
            ledger_row.get("history_prefix_actions") or ()
        )
        stored_effect_prefix = tuple(
            tuple(token)
            for token in (
                ledger_row.get("history_prefix_operation_effects") or ()
            )
        )
        trajectories.append(HistoryTrajectoryEvidence(
            transitions=rows,
            action_prefix=stored_action_prefix,
            operation_effect_prefix=stored_effect_prefix,
            boundary_indices=indices,
            evidence_ref=str(ledger_row.get("path") or "sealed_slice"),
        ))

    problem = projection.mechanism_acquisition_problem(
        start=trace_rows[0].s,
        evidence_transitions=active_rows,
        predict=carrier,
        evidence_ref="raw/episodes/episode_001.jsonl",
        boundary_edges=boundary_edges,
        history_trajectories=tuple(trajectories),
        exhaustive_history_candidates=False,
    )
    if problem is None:
        raise ValueError("active mechanism problem did not compile")
    start_key = problem.observed_start_key(
        trace_rows[0].s,
        history_prefix,
        effect_prefix,
    )
    system = problem.action_system
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=OPERATIONS,
        context_key=problem.acquisition_context_key,
        support_key=lambda source_key: stable_sha256(
            getattr(
                system.representative(source_key),
                "observation",
                system.representative(source_key),
            )
        ),
        source_lineage_keys=problem.source_lineage_keys,
    )
    diagnostics = {
        "active_epoch": active_epoch,
        "active_observation_count": len(active_rows),
        "trajectory_count": len(trajectories),
        "current_seed_sha256": current_seed_sha,
        "history_kind": getattr(problem.history_lift, "history_kind", ""),
        "history_suffix_length": problem.history_suffix_length,
    }
    return problem, system, fibers, active_rows, {
        **diagnostics,
        "start_key": start_key,
    }


def _reachable_routes(
    fibers: Any,
    start_key: Any,
) -> tuple[dict[Any, tuple[Any, ...]], dict[Any, int]]:
    routes = {start_key: ()}
    context_crossings = {start_key: 0}
    queue = deque([start_key])
    while queue:
        source = queue.popleft()
        for operation in fibers.operations:
            edge = fibers.edges.get((source, operation))
            if edge is None or edge.boundary_kinds or not edge.deterministic:
                continue
            target = edge.targets[0]
            if target in routes:
                continue
            routes[target] = (*routes[source], operation)
            context_crossings[target] = (
                context_crossings[source] + int(edge.context_transition)
            )
            queue.append(target)
    return routes, context_crossings


def _footprint_relation(
    *,
    grid: Any,
    operation: Any,
    projection: Any,
    operation_maps: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    operation_row = operation_maps.get(repr(operation))
    factors = projection.factor(grid)
    origins = tuple(factors.controlled_base)
    if operation_row is None or not operation_row["admitted"] or len(origins) != 1:
        return {
            "admissible": False,
            "operation": repr(operation),
            "controlled_origin_count": len(origins),
            "operation_map": operation_row,
        }
    origin = origins[0]
    delta_row, delta_col = operation_row["vector"]
    attempted = origin[0] + delta_row, origin[1] + delta_col
    height = len(projection.sprite)
    width = len(projection.sprite[0])
    span = max(height, width)
    raw = affordance._window(
        grid,
        top=attempted[0],
        left=attempted[1],
        size=span,
        current_origin=origin,
        sprite_shape=(height, width),
    )
    footprint, transform = affordance._canonical_matrix(raw)
    value = ("footprint", footprint)
    configuration = affordance._configuration_partition(
        tuple(factors.finite_configuration)
    )
    return {
        "admissible": True,
        "operation": repr(operation),
        "controlled_origin": origin,
        "attempted_origin": attempted,
        "global_transform": transform,
        "descriptor_sha256": stable_sha256(value),
        "configuration_sha256": stable_sha256(configuration),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--trace", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--template-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    trace_path = Path(args.trace).resolve()
    report_path = Path(args.report).resolve()
    carrier_path = project / "test_model.py"
    carrier, _kind, carrier_sha = load_carrier_path(
        carrier_path,
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")
    carrier_execution_sha = carrier_execution_sha256_from_source(
        carrier_path.read_text(encoding="utf-8")
    )
    template_payload = json.loads(
        Path(args.template_result).read_text(encoding="utf-8")
    )
    template = template_payload["template"]["relation"]["descriptors"]["footprint"]
    frozen_sha = (
        "5f332d7e3f1cf374998f1da7bc323ebe6cee405acb23268c60992eb8f7760bec"
    )
    if template["sha256"] != frozen_sha:
        raise SystemExit("template result drifted from preregistered footprint")
    if stable_sha256(tuple(template["value"])) == frozen_sha:
        # JSON turns nested tuples into lists; the content hash is already
        # bound by the source result. This branch records a convenient replay
        # when its top-level conversion happens to preserve the digest.
        template_replay = "direct"
    else:
        template_replay = "source_result_bound"

    (
        problem,
        system,
        fibers,
        active_rows,
        diagnostics,
    ) = _active_problem(
        project=project,
        trace_path=trace_path,
        report_path=report_path,
        carrier=carrier,
        carrier_sha=carrier_sha,
        carrier_execution_sha=carrier_execution_sha,
        projection=projection,
    )
    operation_maps = _operation_maps(active_rows, projection=projection)
    routes, context_crossings = _reachable_routes(
        fibers,
        diagnostics["start_key"],
    )

    matches = []
    frontier_count = 0
    inadmissible_count = 0
    for source, route in routes.items():
        representative = system.representative(source)
        grid = getattr(representative, "observation", representative)
        support = fibers.support_by_node.get(source, frozenset())
        for operation in OPERATIONS:
            edge = fibers.edges.get((source, operation))
            if edge is not None:
                disposition = (
                    "observed_boundary"
                    if edge.boundary_kinds
                    else "observed_law"
                )
                evidence_refs = edge.evidence_refs
            elif operation in support:
                disposition = "admission_fiber_supported"
                support_identity = fibers.support_identity_by_node[source]
                evidence_refs = tuple(sorted({
                    ref
                    for (peer, peer_operation), peer_edge in fibers.edges.items()
                    if (
                        peer_operation == operation
                        and fibers.support_identity_by_node.get(peer)
                        == support_identity
                    )
                    for ref in peer_edge.evidence_refs
                }))
            else:
                disposition = "unsupported"
                evidence_refs = ()
                frontier_count += 1
            relation = _footprint_relation(
                grid=grid,
                operation=operation,
                projection=projection,
                operation_maps=operation_maps,
            )
            if not relation["admissible"]:
                inadmissible_count += 1
                continue
            if relation["descriptor_sha256"] != frozen_sha:
                continue
            matches.append({
                "source_sha256": stable_sha256(source),
                "source_representative_sha256": stable_sha256(grid),
                "source_representative_evidence_ref": (
                    system.fibers[source].evidence_ref
                ),
                "source_lineage_sha256s": sorted(
                    fibers.lineage_sha256s_by_node[source]
                ),
                "operation": repr(operation),
                "disposition": disposition,
                "boundary_kinds": (
                    list(edge.boundary_kinds) if edge is not None else []
                ),
                "evidence_refs": list(evidence_refs),
                "route_actions": [repr(value) for value in (*route, operation)],
                "route_length": len(route) + 1,
                "context_crossings_before_terminal": context_crossings[source],
                "relation": relation,
            })

    matches.sort(
        key=lambda row: (
            row["disposition"] != "unsupported",
            row["route_length"],
            row["source_sha256"],
            row["operation"],
        )
    )
    candidates = [
        row for row in matches if row["disposition"] == "unsupported"
    ]
    known_negative_matches = [
        row for row in matches if row["disposition"] != "unsupported"
    ]
    graph_ambiguity = len(system.noncommuting_relations)
    operation_maps_admitted = all(
        row["admitted"] for row in operation_maps.values()
    )
    passed = bool(
        graph_ambiguity == 0
        and not fibers.section_failures
        and operation_maps_admitted
        and not known_negative_matches
        and candidates
        and len(candidates) < frontier_count
        and all(row["source_representative_evidence_ref"] for row in candidates)
    )
    payload = {
        "schema": "ztare-active-affordance-frontier-audit-v1",
        "template": {
            "descriptor_sha256": frozen_sha,
            "source_result": str(args.template_result),
            "replay_status": template_replay,
        },
        "active_graph": {
            "node_count": len(fibers.nodes),
            "relation_count": len(fibers.edges),
            "ambiguous_relation_count": graph_ambiguity,
            "boundary_edge_count": len(fibers.boundary_edges),
            "context_transition_edge_count": len(
                fibers.context_transition_edges
            ),
            "reachable_node_count": len(routes),
            "reachable_frontier_pair_count": frontier_count,
            "section_failure_count": len(fibers.section_failures),
        },
        "active_problem": {
            key: (
                stable_sha256(value) if key == "start_key" else value
            )
            for key, value in diagnostics.items()
        },
        "operation_maps": operation_maps,
        "inadmissible_pair_count": inadmissible_count,
        "match_count": len(matches),
        "known_negative_match_count": len(known_negative_matches),
        "candidate_count": len(candidates),
        "matches": matches,
        "known_negative_matches": known_negative_matches,
        "candidates": candidates,
        "status": (
            "active_affordance_frontier_confirmed"
            if passed
            else "active_affordance_frontier_refuted"
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
        "active_graph": payload["active_graph"],
        "operation_maps": operation_maps,
        "match_count": payload["match_count"],
        "known_negative_match_count": payload[
            "known_negative_match_count"
        ],
        "candidate_count": payload["candidate_count"],
        "matches": matches,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
