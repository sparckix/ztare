#!/usr/bin/env python3
"""GP-216d / GP-216f — Director graph-query helper.

Pattern 10 deliverable: traversal-based queries on the ZTARE knowledge graph.
Replaces grep+manual cross-referencing for common Director synthesis-turn questions.

Usage:
    python -m scripts.query_graph --depends-on GP-216
    python -m scripts.query_graph --instantiates core_07
    python -m scripts.query_graph --hubs 10                    # top-N most-referenced seams
    python -m scripts.query_graph --connects GP-148 GP-216     # all paths from src → dst
    python -m scripts.query_graph --orphans                    # seams with no incoming edges
    python -m scripts.query_graph --json                       # output as JSON instead of text

Builds on:
  - scripts/public/validators/validate_knowledge_graph.py (drift validator) — same data source
  - /tmp/gp216_graph_db_prototype.py (extractor) — regenerate graph if needed

This is the load-bearing tool for Pattern 10 to actually deliver Director-leverage.
Until this exists, the graph is just data; with this, the graph is queryable infrastructure.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH = (
    REPO
    / "analytics"
    / "public"
    / "queries"
    / "graphs"
    / "ztare_knowledge_graph_prototype.json"
)


def load_graph(path: Path) -> tuple[list[dict], dict[str, dict]]:
    if not path.exists():
        print(f"ERROR: graph not found: {path}", file=sys.stderr)
        sys.exit(2)
    data = json.loads(path.read_text())
    nodes = data.get("@graph", [])
    by_id = {n["@id"]: n for n in nodes if "@id" in n}
    return nodes, by_id


def build_indices(nodes: list[dict]) -> dict[str, dict]:
    """Build forward + reverse adjacency by edge type."""
    forward = defaultdict(lambda: defaultdict(set))   # forward[edge_type][src] = {dst, ...}
    reverse = defaultdict(lambda: defaultdict(set))   # reverse[edge_type][dst] = {src, ...}
    for n in nodes:
        nid = n["@id"]
        for edge_type in ("depends_on", "instantiates_op", "references_gate"):
            for target in n.get(edge_type, []):
                forward[edge_type][nid].add(target)
                reverse[edge_type][target].add(nid)
    return {"forward": forward, "reverse": reverse}


def query_depends_on(seam_id: str, by_id: dict, indices: dict, transitive: bool = False) -> dict:
    """Return what depends on `seam_id` (transitively if requested)."""
    full_id = seam_id if seam_id.startswith("seam:") else f"seam:{seam_id}"
    direct_dependents = indices["reverse"]["depends_on"].get(full_id, set())
    if not transitive:
        return {"target": full_id, "direct_dependents": sorted(direct_dependents),
                 "n": len(direct_dependents)}
    # BFS for transitive
    visited = set()
    queue = deque(direct_dependents)
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for next_node in indices["reverse"]["depends_on"].get(node, set()):
            if next_node not in visited:
                queue.append(next_node)
    return {"target": full_id, "transitive_dependents": sorted(visited), "n": len(visited)}


def query_instantiates(op_id: str, by_id: dict, indices: dict) -> dict:
    """Return all seams that instantiate the given op."""
    full_id = op_id if op_id.startswith("op:") else f"op:{op_id}"
    instantiating_seams = indices["reverse"]["instantiates_op"].get(full_id, set())
    return {"op": full_id, "seams_instantiating": sorted(instantiating_seams),
             "n": len(instantiating_seams)}


def query_hubs(by_id: dict, indices: dict, n: int = 10) -> dict:
    """Return top-N most-referenced seams."""
    counts = {target: len(srcs) for target, srcs in indices["reverse"]["depends_on"].items()}
    top = sorted(counts.items(), key=lambda x: -x[1])[:n]
    return {"top_n": n, "hubs": [{"seam": s, "n_referrers": c} for s, c in top]}


def query_orphans(by_id: dict, indices: dict) -> dict:
    """Seams with no incoming depends_on edges."""
    referenced = set(indices["reverse"]["depends_on"].keys())
    seam_ids = [nid for nid, n in by_id.items() if n.get("@type") == "seam"]
    orphans = [s for s in seam_ids if s not in referenced]
    return {"n_orphans": len(orphans), "orphans": sorted(orphans)}


def query_connects(src: str, dst: str, indices: dict, max_depth: int = 6) -> dict:
    """Find all paths from src to dst (depth-bounded)."""
    src_full = src if src.startswith("seam:") else f"seam:{src}"
    dst_full = dst if dst.startswith("seam:") else f"seam:{dst}"
    paths: list[list[str]] = []

    def dfs(current: str, target: str, path: list[str], depth: int):
        if depth > max_depth:
            return
        if current == target:
            paths.append(path.copy())
            return
        for next_node in indices["forward"]["depends_on"].get(current, set()):
            if next_node not in path:
                path.append(next_node)
                dfs(next_node, target, path, depth + 1)
                path.pop()

    dfs(src_full, dst_full, [src_full], 0)
    return {"src": src_full, "dst": dst_full, "n_paths": len(paths),
             "paths": [list(p) for p in paths[:5]]}


def render_text(result: dict) -> str:
    """Render a query result as human/agent-readable text."""
    if "direct_dependents" in result:
        lines = [f"Seams depending on {result['target']} (direct, n={result['n']}):"]
        for s in result["direct_dependents"]:
            lines.append(f"  - {s}")
        return "\n".join(lines)
    if "transitive_dependents" in result:
        lines = [f"Seams depending on {result['target']} (transitive, n={result['n']}):"]
        for s in result["transitive_dependents"]:
            lines.append(f"  - {s}")
        return "\n".join(lines)
    if "seams_instantiating" in result:
        lines = [f"Seams instantiating {result['op']} (n={result['n']}):"]
        for s in result["seams_instantiating"]:
            lines.append(f"  - {s}")
        return "\n".join(lines)
    if "hubs" in result:
        lines = [f"Top {result['top_n']} most-referenced seams:"]
        for h in result["hubs"]:
            lines.append(f"  {h['n_referrers']:3d}  {h['seam']}")
        return "\n".join(lines)
    if "orphans" in result:
        lines = [f"Orphan seams (no incoming references, n={result['n_orphans']}):"]
        for s in result["orphans"][:30]:
            lines.append(f"  - {s}")
        if result["n_orphans"] > 30:
            lines.append(f"  ... ({result['n_orphans'] - 30} more)")
        return "\n".join(lines)
    if "n_paths" in result:
        lines = [f"Paths from {result['src']} to {result['dst']} (n={result['n_paths']}):"]
        for path in result["paths"]:
            lines.append("  " + " → ".join(path))
        return "\n".join(lines)
    return json.dumps(result, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--depends-on", type=str, help="seam id; show what depends on it")
    parser.add_argument("--instantiates", type=str, help="op id; show seams that instantiate it")
    parser.add_argument("--hubs", type=int, default=None, help="show top-N most-referenced seams")
    parser.add_argument("--connects", nargs=2, metavar=("SRC", "DST"),
                          help="find paths from src to dst")
    parser.add_argument("--orphans", action="store_true", help="show seams with no incoming edges")
    parser.add_argument("--transitive", action="store_true", help="for --depends-on, recurse")
    parser.add_argument("--json", action="store_true", help="output as JSON instead of text")
    args = parser.parse_args()

    nodes, by_id = load_graph(args.graph)
    indices = build_indices(nodes)

    result = None
    if args.depends_on:
        result = query_depends_on(args.depends_on, by_id, indices, transitive=args.transitive)
    elif args.instantiates:
        result = query_instantiates(args.instantiates, by_id, indices)
    elif args.hubs is not None:
        result = query_hubs(by_id, indices, n=args.hubs)
    elif args.connects:
        result = query_connects(args.connects[0], args.connects[1], indices)
    elif args.orphans:
        result = query_orphans(by_id, indices)
    else:
        # Default: summary
        n_nodes = len(nodes)
        n_seams = sum(1 for n in nodes if n.get("@type") == "seam")
        n_dep_edges = sum(len(s) for s in indices["forward"]["depends_on"].values())
        n_op_edges = sum(len(s) for s in indices["forward"]["instantiates_op"].values())
        n_gate_edges = sum(len(s) for s in indices["forward"]["references_gate"].values())
        result = {
            "summary": True,
            "n_nodes": n_nodes,
            "n_seams": n_seams,
            "n_depends_on_edges": n_dep_edges,
            "n_instantiates_op_edges": n_op_edges,
            "n_references_gate_edges": n_gate_edges,
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result) if "summary" not in result else json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
