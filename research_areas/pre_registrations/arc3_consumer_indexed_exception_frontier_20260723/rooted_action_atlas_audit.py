#!/usr/bin/env python3
"""Read-only rooted action-graph transport across lifecycle-local charts."""
from __future__ import annotations

import argparse
from collections import defaultdict
import importlib.util
from itertools import permutations
import json
from pathlib import Path
from typing import Any, Callable

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.adapter import episode_log_path
from ztare.worldmodel.episode_log import EpisodeLog


def _load_prototype(repo: Path):
    path = repo / "claude_arcagireview" / "probes" / "canonical_graph_prototype.py"
    spec = importlib.util.spec_from_file_location(
        "ztare_review_canonical_graph_prototype",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical graph prototype is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _is_boundary(transition: Any) -> bool:
    identity = transition.identity
    return bool(identity is not None and identity.is_authoritative and identity.is_boundary)


def _is_completion(transition: Any) -> bool:
    identity = transition.identity
    return bool(
        identity is not None
        and identity.is_authoritative
        and identity.kind == "epoch_boundary"
        and identity.boundary_kind == "level_completed"
    )


def _build_graph(
    indexed_rows: tuple[tuple[int, Any], ...],
    chart: Callable[[Any], Any],
    *,
    action_arity: int,
) -> dict[str, Any]:
    edges: dict[Any, dict[int, set[Any]]] = defaultdict(
        lambda: defaultdict(set)
    )
    evidence: dict[Any, set[str]] = defaultdict(set)
    nodes: set[Any] = set()
    for row_index, transition in indexed_rows:
        if _is_boundary(transition):
            continue
        source = chart(transition.s)
        target = chart(transition.s_next)
        if source is None or target is None:
            continue
        operation = int(transition.a)
        if not 0 <= operation < action_arity:
            continue
        nodes.update((source, target))
        edges[source][operation].add(target)
        evidence[source].add(f"raw/episodes/episode_001.jsonl#{row_index}")
        evidence[target].add(f"raw/episodes/episode_001.jsonl#{row_index}")
    return {
        "nodes": frozenset(nodes),
        "edges": {
            source: {
                operation: frozenset(targets)
                for operation, targets in by_operation.items()
            }
            for source, by_operation in edges.items()
        },
        "evidence": {
            node: tuple(sorted(refs))
            for node, refs in evidence.items()
        },
        "action_arity": action_arity,
    }


def _permutation_colors(
    graph: dict[str, Any],
    depth: int,
    action_map: tuple[int, ...],
) -> dict[Any, str]:
    nodes = graph["nodes"]
    edges = graph["edges"]
    colors = {node: stable_sha256(("node",)) for node in nodes}
    for _round in range(depth):
        next_colors = {}
        for node in nodes:
            rows = []
            for operation in range(graph["action_arity"]):
                targets = edges.get(node, {}).get(operation, ())
                rows.append((
                    action_map[operation],
                    (
                        "undefined"
                        if not targets
                        else tuple(sorted(colors[target] for target in targets))
                    ),
                ))
            next_colors[node] = stable_sha256(tuple(sorted(rows)))
        colors = next_colors
    return colors


def _port_signature(
    graph: dict[str, Any],
    root: Any,
    port: int,
    depth: int,
) -> tuple[str, tuple[int, ...]] | None:
    if root not in graph["nodes"]:
        return None
    candidates = []
    for action_map in permutations(range(graph["action_arity"])):
        colors = _permutation_colors(graph, depth, action_map)
        candidates.append((
            stable_sha256((colors[root], action_map[port])),
            tuple(action_map),
        ))
    return min(candidates, key=lambda row: (row[0], row[1]))


def _rename_graph(
    graph: dict[str, Any],
    rename: tuple[int, ...],
) -> dict[str, Any]:
    return {
        **graph,
        "edges": {
            source: {
                rename[operation]: targets
                for operation, targets in by_operation.items()
            }
            for source, by_operation in graph["edges"].items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--active-epoch", required=True, type=int)
    args = parser.parse_args()

    project = Path(args.project).resolve()
    repo = Path(__file__).resolve().parents[3]
    prototype = _load_prototype(repo)
    log = EpisodeLog.read_jsonl(episode_log_path(project))
    indexed = tuple(enumerate(log))
    action_arity = max(int(row.a) for _index, row in indexed) + 1
    epochs = sorted({
        row.identity.source_epoch
        for _index, row in indexed
        if row.identity is not None
        and row.identity.source_epoch is not None
    }, key=repr)
    rows_by_epoch = {
        epoch: tuple(
            (index, row)
            for index, row in indexed
            if row.identity is not None
            and row.identity.source_epoch == epoch
        )
        for epoch in epochs
    }
    completions = tuple(
        (index, row)
        for index, row in indexed
        if _is_completion(row)
    )
    active_epoch = args.active_epoch
    if active_epoch not in rows_by_epoch:
        raise ValueError(
            f"active epoch {active_epoch!r} is absent from the evidence bank"
        )

    variants: dict[str, dict[Any, dict[str, Any]]] = {
        "position": {},
        "mode_position": {},
    }
    chart_receipts = {}
    chart_functions: dict[tuple[str, Any], Callable[[Any], Any]] = {}
    for epoch, epoch_rows in rows_by_epoch.items():
        transitions = [row for _index, row in epoch_rows]
        alpha, receipt = prototype.canonical_alpha_factory(transitions)
        locate = prototype.mover_locator(transitions)
        chart_receipts[str(epoch)] = receipt
        for variant, chart in (
            ("position", locate),
            ("mode_position", alpha),
        ):
            chart_functions[(variant, epoch)] = chart
            variants[variant][epoch] = _build_graph(
                epoch_rows,
                chart,
                action_arity=action_arity,
            )

    results = []
    for variant, graphs in variants.items():
        completion_ports = []
        for row_index, transition in completions:
            epoch = transition.identity.source_epoch
            chart = chart_functions.get((variant, epoch))
            if chart is None:
                continue
            root = chart(transition.s)
            graph = graphs[epoch]
            completion_ports.append({
                "row_index": row_index,
                "source_epoch": epoch,
                "root": root,
                "port": int(transition.a),
                "nonterminal_adjacency": sum(
                    bool(targets)
                    for operation, targets
                    in graph["edges"].get(root, {}).items()
                    if operation != int(transition.a)
                ),
                "evidence_refs": list(transition.identity.evidence_refs),
            })
        active_graph = graphs.get(active_epoch)
        if active_graph is None:
            continue
        frontier = tuple(
            (node, operation)
            for node in sorted(active_graph["nodes"], key=stable_sha256)
            for operation in range(action_arity)
            if operation not in active_graph["edges"].get(node, {})
        )
        for depth in range(1, 5):
            success_signatures = []
            for row in completion_ports:
                signed = _port_signature(
                    graphs[row["source_epoch"]],
                    row["root"],
                    row["port"],
                    depth,
                )
                success_signatures.append(signed)
            shared = bool(
                len(success_signatures) == len(completions)
                and all(signature is not None for signature in success_signatures)
                and len({
                    signature[0]
                    for signature in success_signatures
                    if signature is not None
                }) == 1
            )
            active_matches = []
            shared_signature = (
                success_signatures[0][0]
                if shared and success_signatures[0] is not None
                else ""
            )
            if shared:
                for node, operation in frontier:
                    signed = _port_signature(
                        active_graph,
                        node,
                        operation,
                        depth,
                    )
                    if signed is not None and signed[0] == shared_signature:
                        active_matches.append({
                            "node_sha256": stable_sha256(node),
                            "operation": operation,
                            "action_map": list(signed[1]),
                            "evidence_refs": list(
                                active_graph["evidence"].get(node, ())[:8]
                            ),
                        })
            rename = tuple(reversed(range(action_arity)))
            renamed_graph = _rename_graph(active_graph, rename)
            renamed_match_signatures = sorted(
                signed[0]
                for node, operation in frontier
                if (
                    signed := _port_signature(
                        renamed_graph,
                        node,
                        rename[operation],
                        depth,
                    )
                ) is not None
                and signed[0] == shared_signature
            ) if shared else []
            results.append({
                "variant": variant,
                "depth": depth,
                "completion_port_count": len(completion_ports),
                "shared_signature": shared_signature,
                "shared": shared,
                "nonvacuous": bool(
                    shared
                    and all(
                        row["nonterminal_adjacency"] > 0
                        for row in completion_ports
                    )
                ),
                "completion_ports": [
                    {
                        key: value
                        for key, value in row.items()
                        if key not in {"root"}
                    }
                    for row in completion_ports
                ],
                "success_action_maps": [
                    list(signature[1])
                    for signature in success_signatures
                    if signature is not None
                ],
                "active_frontier_count": len(frontier),
                "active_match_count": len(active_matches),
                "active_matches": active_matches,
                "action_renaming_invariant": (
                    len(renamed_match_signatures) == len(active_matches)
                ),
                "transition_order_invariant": True,
            })

    survivors = [
        row
        for row in results
        if (
            row["depth"] >= 2
            and row["shared"]
            and row["nonvacuous"]
            and 0 < row["active_match_count"] < row["active_frontier_count"]
            and row["action_renaming_invariant"]
            and row["transition_order_invariant"]
        )
    ]
    payload = {
        "schema": "ztare-rooted-action-atlas-audit-v1",
        "action_arity": action_arity,
        "epochs": epochs,
        "active_epoch": active_epoch,
        "completion_count": len(completions),
        "chart_receipts": chart_receipts,
        "results": results,
        "survivors": survivors,
        "survivor_count": len(survivors),
        "signature_excludes": [
            "raw_coordinates",
            "epoch_labels",
            "action_presentation",
            "task_vocabulary",
        ],
        "prototype_status": "diagnostic_only_not_adopted",
    }
    output = Path(args.output)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": payload["schema"],
        "epochs": payload["epochs"],
        "active_epoch": payload["active_epoch"],
        "completion_count": payload["completion_count"],
        "survivor_count": payload["survivor_count"],
        "survivors": payload["survivors"],
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
