#!/usr/bin/env python3
"""Export role-separated subgraphs from the unified knowledge graph.

This does not replace the unified graph. It exists to prevent downstream
consumers from accidentally treating seams, code regions, and vocabulary nodes
as one undifferentiated population.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH = REPO / "analytics" / "public" / "queries" / "ztare_knowledge_graph.json"
DEFAULT_OUT_DIR = REPO / "exports" / "layered_graphs"


def classify_layer(node: dict) -> str:
    node_id = node.get("@id", "")
    node_type = node.get("@type", "")
    if node_type == "seam":
        return "artifact_graph"
    if node_id.startswith(("module:", "region:", "func:", "exit:")):
        return "code_graph"
    if node_id.startswith(("op:", "gate:")) or node_type in {"research_op", "gate"}:
        return "vocabulary_graph"
    return "other_graph"


def filter_edges(node: dict, allowed_ids: set[str]) -> dict:
    out = dict(node)
    for key in ("depends_on", "instantiates_op", "references_gate"):
        out[key] = [target for target in node.get(key, []) if target in allowed_ids]
    return out


def emit_layer(nodes: list[dict], out_path: Path) -> None:
    allowed_ids = {n["@id"] for n in nodes if "@id" in n}
    payload = {
        "@context": "ztare://kg/v2",
        "@graph": [filter_edges(n, allowed_ids) for n in nodes],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    data = json.loads(args.graph.read_text())
    nodes = data.get("@graph", [])
    buckets: dict[str, list[dict]] = {
        "artifact_graph": [],
        "code_graph": [],
        "vocabulary_graph": [],
        "other_graph": [],
    }
    for node in nodes:
        buckets[classify_layer(node)].append(node)

    for layer, layer_nodes in buckets.items():
        out_path = args.out_dir / f"ztare_{layer}.json"
        emit_layer(layer_nodes, out_path)
        print(f"Wrote {layer}: {out_path} ({len(layer_nodes)} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
