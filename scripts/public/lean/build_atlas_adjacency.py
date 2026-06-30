#!/usr/bin/env python3
"""Build the COMPACT atlas-induced dependency adjacency for graph-expansion premise retrieval.

The full Mathlib dep-graph (`analytics/public/index/mathlib_graph/mathlib_graph.json`, ~254MB, 3.84M typed
`uses` edges over 122k decls) is too heavy to load on every solve. Graph-expansion only ever boosts candidates
that are (a) IN the embedding atlas (the rankable set) and (b) a dependency-neighbour of a cosine seed. So we
precompute, ONCE, the subgraph induced on the atlas's 46k decls: `{decl -> [atlas neighbours]}` (undirected —
both `uses` and `used_by`, since premise co-occurrence flows both ways; the A/B test measured plain
co-occurrence count as the best signal, with Adamic-Adar rarity-weighting REGRESSING).

Measured lift (inductive Mathlib premise selection, n=1500, no target-edge leakage): recall@10 0.225→0.266,
recall@20 0.270→0.360, recall@50 0.330→0.491, MRR flat — see the harness. Output is consumed by the live
premise shelf's Mathlib leg (graph-expansion re-rank, default-on, fail-safe).

  PYTHONPATH=src python scripts/public/lean/build_atlas_adjacency.py
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ATLAS = REPO / "analytics/public/queries/lean/mathlib_atlas_embeddings.json"
GRAPH = REPO / "analytics/public/index/mathlib_graph/mathlib_graph.json"
OUT = REPO / "analytics/public/queries/lean/mathlib_atlas_adjacency.json"


def main() -> int:
    atlas = {e["id"] for e in json.load(open(ATLAS))["embeddings"]}
    print(f"atlas decls: {len(atlas)}")
    g = json.load(open(GRAPH))
    adj: "dict[str, set[str]]" = {}
    n_edges = 0
    for o in g["@graph"]:
        s = o.get("src"); d = o.get("dst")
        if s is None or s == d:
            continue
        if s in atlas and d in atlas:        # atlas-induced subgraph only
            adj.setdefault(s, set()).add(d)
            adj.setdefault(d, set()).add(s)   # undirected co-occurrence
            n_edges += 1
    out = {k: sorted(v) for k, v in adj.items()}
    OUT.write_text(json.dumps({"n_nodes": len(out), "n_atlas_edges": n_edges,
                               "source": "mathlib_graph atlas-induced subgraph (undirected)",
                               "adjacency": out}), encoding="utf-8")
    deg = [len(v) for v in out.values()]
    print(f"wrote {OUT}")
    print(f"  nodes with neighbours: {len(out)} · atlas-induced edges: {n_edges} · "
          f"mean degree: {sum(deg)/len(deg):.1f} · max: {max(deg)} · size: {OUT.stat().st_size/1e6:.1f}MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
