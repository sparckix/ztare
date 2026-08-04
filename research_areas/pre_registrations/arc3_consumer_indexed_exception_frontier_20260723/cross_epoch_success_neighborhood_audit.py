#!/usr/bin/env python3
"""Audit rooted success-edge transport without using rendered coordinates."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from ztare.common.boundary_reachability import (
    compile_boundary_reachability_fibers,
)
from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.carrier_loader import load_carrier_path
from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.mechanism_effects import (
    build_fiber_action_system,
    fiber_transition_key,
)


OPERATIONS = ("0", "1", "2", "3")
SYMMETRIES = (
    ("operation_preserving_exact_effect", False, False),
    ("operation_renaming_exact_effect", True, False),
    ("operation_preserving_effect_family", False, True),
    ("operation_renaming_effect_family", True, True),
)


def _sign(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return (number > 0) - (number < 0)


def _effect_family(effect: Any) -> Any:
    """Mechanism family with presentation values and coordinates removed."""
    if not isinstance(effect, tuple):
        return ("opaque_effect", type(effect).__name__)
    if effect[:1] == ("boundary",):
        return ("lifecycle_boundary",)
    normalized = []
    for item in effect:
        if not isinstance(item, tuple) or not item:
            normalized.append(("opaque_component", type(item).__name__))
            continue
        factor = item[0]
        if factor == "controlled_base":
            mechanism = item[1] if len(item) > 1 else ()
            kind = (
                mechanism[0]
                if isinstance(mechanism, tuple) and mechanism
                else "unknown"
            )
            if kind == "support_change":
                before = mechanism[1] if len(mechanism) > 1 else 0
                after = mechanism[2] if len(mechanism) > 2 else 0
                normalized.append((factor, kind, _sign(after - before)))
            else:
                normalized.append((factor, kind))
        elif factor in {
            "finite_configuration",
            "operation_domain_assignment",
        }:
            normalized.append((factor, "changed"))
        elif factor in {
            "ordered_feasibility_configuration",
            "ordered_budget",
        }:
            normalized.append((factor, _sign(item[1] if len(item) > 1 else 0)))
        elif factor == "one_shot_availability":
            changes = item[1] if len(item) > 1 and isinstance(item[1], tuple) else ()
            directions = []
            for change in changes:
                if not isinstance(change, tuple) or len(change) < 3:
                    directions.append("changed")
                elif change[1] is False and change[2] is True:
                    directions.append("enabled")
                elif change[1] is True and change[2] is False:
                    directions.append("consumed")
                else:
                    directions.append("changed")
            normalized.append((factor, tuple(sorted(directions))))
        elif factor == "identity":
            normalized.append(("identity",))
        else:
            normalized.append((str(factor), "changed"))
    return tuple(sorted(normalized, key=repr))


def _system_graph(system: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    fibers = compile_boundary_reachability_fibers(
        system,
        operations=(0, 1, 2, 3),
        context_key=lambda _source: (),
        support_key=lambda source: stable_sha256(system.representative(source)),
    )
    effect_families: dict[str, Any] = {}
    for effects in system.relation_effects.values():
        for effect in effects:
            effect_families[stable_sha256(effect)] = _effect_family(effect)
    nodes = {stable_sha256(node) for node in fibers.nodes}
    edges = []
    for edge in fibers.edges.values():
        source = stable_sha256(edge.source)
        targets = tuple(sorted(stable_sha256(target) for target in edge.targets))
        nodes.add(source)
        nodes.update(targets)
        edges.append({
            "source": source,
            "operation": repr(edge.operation),
            "effect_sha256s": tuple(
                sorted(stable_sha256(effect) for effect in edge.effects)
            ),
            "targets": targets,
            "boundary": bool(edge.boundary_kinds),
        })
    return {
        "nodes": tuple(sorted(nodes)),
        "edges": tuple(edges),
        "operations": OPERATIONS,
    }, effect_families


def _receipt_graph(receipt: dict[str, Any]) -> dict[str, Any]:
    nodes: set[str] = set()
    edges = []
    for edge in receipt.get("edges") or ():
        source = str(edge["source_sha256"])
        targets = tuple(sorted(str(value) for value in edge.get("target_sha256s") or ()))
        nodes.add(source)
        nodes.update(targets)
        edges.append({
            "source": source,
            "operation": str(edge["operation"]),
            "effect_sha256s": tuple(
                sorted(str(value) for value in edge.get("effect_sha256s") or ())
            ),
            "targets": targets,
            "boundary": bool(edge.get("boundary_kinds")),
        })
    return {
        "nodes": tuple(sorted(nodes)),
        "edges": tuple(edges),
        "operations": tuple(str(value) for value in receipt.get("operations") or OPERATIONS),
    }


def _refinement_codes(
    graph: dict[str, Any],
    *,
    effect_families: dict[str, Any],
    operation_renaming: bool,
    family_effects: bool,
    max_depth: int = 3,
) -> dict[int, dict[str, str]]:
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph["edges"]:
        outgoing[edge["source"]].append(edge)
        for target in edge["targets"]:
            incoming[target].append(edge)
    codes = {
        node: stable_sha256(("rooted_partial_action_node",))
        for node in graph["nodes"]
    }
    by_depth = {0: codes}
    for depth in range(1, max_depth + 1):
        next_codes = {}
        for node in graph["nodes"]:
            descriptors = []
            for direction, edge_rows in (
                ("out", outgoing.get(node, ())),
                ("in", incoming.get(node, ())),
            ):
                for edge in edge_rows:
                    operation = "*" if operation_renaming else edge["operation"]
                    if edge["boundary"]:
                        mechanism = ("lifecycle_boundary",)
                        adjacent = ()
                    else:
                        if family_effects:
                            mechanism = tuple(sorted(
                                stable_sha256(
                                    effect_families.get(
                                        digest,
                                        ("unknown_effect", digest),
                                    )
                                )
                                for digest in edge["effect_sha256s"]
                            ))
                        else:
                            mechanism = edge["effect_sha256s"]
                        adjacent_nodes = (
                            edge["targets"]
                            if direction == "out"
                            else (edge["source"],)
                        )
                        adjacent = tuple(sorted(
                            codes.get(
                                target,
                                stable_sha256(("unseen_target", target)),
                            )
                            for target in adjacent_nodes
                        ))
                    descriptors.append((
                        direction,
                        operation,
                        "boundary" if edge["boundary"] else "transition",
                        mechanism,
                        adjacent,
                    ))
            next_codes[node] = stable_sha256((
                "rooted_partial_action_neighborhood",
                tuple(sorted(descriptors, key=repr)),
            ))
        codes = next_codes
        by_depth[depth] = codes
    return by_depth


def _continuous(left: Any, right: Any) -> bool:
    return bool(
        left.s_next == right.s
        and getattr(left, "t", None) is not None
        and getattr(right, "t", None) is not None
        and int(right.t) == int(left.t) + 1
    )


def _anchored_epoch_rows(
    bank_rows: tuple[Any, ...],
    success_index: int,
    source_epoch: int,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Recover only the continuous route ending at an attested success edge.

    Identity-less legacy rows receive no global epoch assignment. Their order is
    used only inside the exact state/successor-contiguous window whose terminal
    row carries the authoritative source epoch. Other authoritative rows from
    that epoch are added individually so terminal failures remain confusers.
    """
    start = success_index
    while start > 0:
        prior = bank_rows[start - 1]
        current = bank_rows[start]
        if (
            getattr(prior, "identity", None) is not None
            and prior.identity.is_authoritative
            and prior.identity.is_boundary
        ):
            break
        if not _continuous(prior, current):
            break
        start -= 1
    selected = set(range(start, success_index + 1))
    for index, transition in enumerate(bank_rows):
        identity = getattr(transition, "identity", None)
        if (
            identity is not None
            and identity.is_authoritative
            and identity.source_epoch == source_epoch
        ):
            selected.add(index)
    ordered = tuple(bank_rows[index] for index in sorted(selected))
    return ordered, {
        "success_index": success_index,
        "continuous_window_start": start,
        "continuous_window_end_exclusive": success_index + 1,
        "continuous_window_length": success_index - start + 1,
        "selected_row_count": len(ordered),
        "added_authoritative_confuser_count": (
            len(ordered) - (success_index - start + 1)
        ),
    }


def _boundary_sources(graph: dict[str, Any]) -> set[str]:
    return {
        edge["source"]
        for edge in graph["edges"]
        if edge["boundary"]
    }


def _frontier_sources(graph: dict[str, Any]) -> dict[str, list[str]]:
    observed: dict[str, set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        observed[edge["source"]].add(edge["operation"])
    return {
        node: sorted(set(graph["operations"]) - observed.get(node, set()))
        for node in graph["nodes"]
        if set(graph["operations"]) - observed.get(node, set())
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--active-audit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    carrier, _kind, _sha = load_carrier_path(
        project / "test_model.py",
        project_dir=project,
    )
    projection = getattr(carrier, "_ztare_factored_projection", None)
    if projection is None:
        raise SystemExit("carrier has no factored projection")

    bank = EpisodeLog.read_jsonl(project / "raw/episodes/episode_001.jsonl")
    bank_rows = tuple(bank)
    success_rows = [
        (index, transition)
        for index, transition in enumerate(bank_rows)
        if transition.identity is not None
        and transition.identity.is_authoritative
        and transition.identity.kind == "epoch_boundary"
        and transition.identity.boundary_kind == "level_completed"
    ]
    success_by_epoch = {
        int(transition.identity.source_epoch): {
            "bank_row": index,
            "source_sha256": stable_sha256(
                fiber_transition_key(projection.factor(transition.s))
            ),
            "operation": repr(transition.a),
            "source_epoch": transition.identity.source_epoch,
            "target_epoch": transition.identity.target_epoch,
            "evidence_refs": list(transition.identity.evidence_refs),
        }
        for index, transition in success_rows
    }
    if set(success_by_epoch) != {0, 1}:
        raise SystemExit(
            "audit requires one authoritative prior success in epochs 0 and 1"
        )

    graphs: dict[int, dict[str, Any]] = {}
    effect_families: dict[str, Any] = {}
    epoch_receipts = {}
    anchored_windows = {}
    for epoch in (0, 1):
        rows, window_receipt = _anchored_epoch_rows(
            bank_rows,
            int(success_by_epoch[epoch]["bank_row"]),
            epoch,
        )
        anchored_windows[str(epoch)] = window_receipt
        system = build_fiber_action_system(
            rows,
            projection=projection,
            evidence_ref=f"law_scored_view(episode_001.jsonl,source_epoch={epoch})",
        )
        graph, families = _system_graph(system)
        graphs[epoch] = graph
        effect_families.update(families)
        epoch_receipts[str(epoch)] = {
            "observation_count": len(rows),
            "node_count": len(graph["nodes"]),
            "relation_count": len(graph["edges"]),
            "boundary_source_count": len(_boundary_sources(graph)),
            "noncommuting_relation_count": len(system.noncommuting_relations),
            "success_source_sha256": success_by_epoch[epoch]["source_sha256"],
            "success_source_present": (
                success_by_epoch[epoch]["source_sha256"] in graph["nodes"]
            ),
        }

    active_payload = json.loads(
        Path(args.active_audit).read_text(encoding="utf-8")
    )
    active_graph = _receipt_graph(
        active_payload["boundary_reachability_fibers"]
    )
    active_boundaries = _boundary_sources(active_graph)
    active_frontier = _frontier_sources(active_graph)

    results = []
    survivors = []
    for name, rename_operations, family_effects in SYMMETRIES:
        codes = {
            epoch: _refinement_codes(
                graph,
                effect_families=effect_families,
                operation_renaming=rename_operations,
                family_effects=family_effects,
            )
            for epoch, graph in graphs.items()
        }
        active_codes = _refinement_codes(
            active_graph,
            effect_families=effect_families,
            operation_renaming=rename_operations,
            family_effects=family_effects,
        )
        for depth in (1, 2, 3):
            success0 = success_by_epoch[0]["source_sha256"]
            success1 = success_by_epoch[1]["source_sha256"]
            code0 = codes[0][depth].get(success0, "")
            code1 = codes[1][depth].get(success1, "")
            matches_1 = sorted(
                node for node, code in codes[1][depth].items()
                if code == code0
            )
            matches_0 = sorted(
                node for node, code in codes[0][depth].items()
                if code == code1
            )
            baseline_0 = _boundary_sources(graphs[0])
            baseline_1 = _boundary_sources(graphs[1])
            heldout_forward = success1 in matches_1
            heldout_reverse = success0 in matches_0
            baseline_dominance = (
                len(matches_1) <= len(baseline_1)
                and len(matches_0) <= len(baseline_0)
                and (
                    len(matches_1) < len(baseline_1)
                    or len(matches_0) < len(baseline_0)
                )
            )
            active_matches = sorted(
                node for node, code in active_codes[depth].items()
                if code == code0 and node in active_frontier
            )
            outside_non_discharge = sorted(
                set(active_matches) - active_boundaries
            )
            passed = bool(
                code0
                and code0 == code1
                and heldout_forward
                and heldout_reverse
                and baseline_dominance
                and outside_non_discharge
            )
            row = {
                "symmetry": name,
                "depth": depth,
                "success_code_equal": bool(code0 and code0 == code1),
                "forward": {
                    "heldout_recovered": heldout_forward,
                    "match_count": len(matches_1),
                    "boundary_baseline_count": len(baseline_1),
                    "matches": matches_1,
                },
                "reverse": {
                    "heldout_recovered": heldout_reverse,
                    "match_count": len(matches_0),
                    "boundary_baseline_count": len(baseline_0),
                    "matches": matches_0,
                },
                "baseline_dominance": baseline_dominance,
                "active": {
                    "frontier_match_count": len(active_matches),
                    "known_non_discharge_overlap_count": len(
                        set(active_matches) & active_boundaries
                    ),
                    "outside_known_non_discharge_count": len(
                        outside_non_discharge
                    ),
                    "candidates": [
                        {
                            "source_sha256": node,
                            "missing_operations": active_frontier[node],
                            "known_non_discharge_source": node in active_boundaries,
                        }
                        for node in active_matches
                    ],
                },
                "passed": passed,
            }
            results.append(row)
            if passed:
                survivors.append(row)

    payload = {
        "schema": "ztare-cross-epoch-success-neighborhood-audit-v1",
        "success_edges": [
            success_by_epoch[epoch] for epoch in sorted(success_by_epoch)
        ],
        "epoch_graphs": epoch_receipts,
        "anchored_windows": anchored_windows,
        "active_graph": {
            "node_count": len(active_graph["nodes"]),
            "relation_count": len(active_graph["edges"]),
            "boundary_source_count": len(active_boundaries),
            "frontier_source_count": len(active_frontier),
        },
        "symmetry_results": results,
        "survivor_count": len(survivors),
        "survivors": survivors,
        "status": (
            "candidate_transport_survived"
            if survivors
            else "graph_neighborhood_transport_refuted"
        ),
    }
    output = Path(args.output)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "success_edges": payload["success_edges"],
        "epoch_graphs": payload["epoch_graphs"],
        "active_graph": payload["active_graph"],
        "survivor_count": payload["survivor_count"],
        "closest": [
            {
                "symmetry": row["symmetry"],
                "depth": row["depth"],
                "success_code_equal": row["success_code_equal"],
                "forward": row["forward"],
                "reverse": row["reverse"],
                "active": row["active"],
                "passed": row["passed"],
            }
            for row in results
            if row["success_code_equal"]
            or row["forward"]["heldout_recovered"]
            or row["reverse"]["heldout_recovered"]
        ],
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
