#!/usr/bin/env python3
"""GNN v3 inference — score candidate edges using the v3 checkpoint.

Replaces gnn_link_predict_score.py (v2, deprecated). The v3 checkpoint
trained 2026-05-05 on Lambda A10 reaches inductive MRR 0.43 (9.1x AA,
3.5x v2). The architecture is feature-aware GraphSAGE + edge-type-aware
RGCN aggregation + asymmetric (TransE-style) scoring.

# Inputs
  - Checkpoint: analytics/public/leanmill/gnn_ranker/v3_checkpoint.pt
  - Constraint graph: projects/ns_millennium_hunt/workspace/queries/ns_trackb_constraint_basin_graph.json

# Use cases
  1. Score a single candidate (qty, op, qty) inequality
  2. Score a JSONL file of candidates (e.g. transitivity-closure output)
  3. Top-K novel inequalities globally (cross-checked with AA), optionally
     filtered by node regexes so plumbing quantities do not dominate review.

# Honest caveats
  - Inductive MRR 0.43 measured on held-out NODES from the same NS spine.
    Performance on truly novel theorems Codex adds tomorrow is unverified.
  - v3 uses asymmetric scoring: score(a, op, b) ≠ score(b, op, a).
    Direction matters; pass src and dst correctly.
  - Cross-check against AA: if v3 gives high score and AA = 0, treat with
    caution — could be embedding-space artifact rather than structural fact.

Usage:
    # single pair
    python scripts/public/models/gnn_link_predict_score_v3.py \\
        --pair S.payoffLimit leraySelfTaxLimitPrice --op le

    # JSONL file
    python scripts/public/models/gnn_link_predict_score_v3.py \\
        --candidates projects/ns_millennium_hunt/workspace/queries/orientation_synthesized_candidates.jsonl \\
        --top 30

    # top-K novel globally
    python scripts/public/models/gnn_link_predict_score_v3.py --top-k-novel 30
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHECKPOINT = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker" / "v3_checkpoint.pt"
GRAPH_PATH = REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "ns_trackb_constraint_basin_graph.json"

REL_TO_ID = {"le": 0, "lt": 1, "eq": 2, "gt": 3, "ge": 4}
NUM_RELATIONS = len(REL_TO_ID)


def load_v3():
    """Load v3 checkpoint, reconstruct encoder + scorer + features."""
    sys.path.insert(0, str(REPO))
    from gnn_v3_train import (
        RGCNSAGEEncoder, AsymmetricScorer, compute_features,
        load_full_graph_with_ops,
    )
    import torch
    if not CHECKPOINT.exists():
        print(f"missing {CHECKPOINT}; run gnn_v3_train.py first")
        sys.exit(1)
    ckpt = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
    device = torch.device("cpu")

    # Recompute features (sentence-transformer + struct) from the same graph
    nodes, edges = load_full_graph_with_ops()
    nodes = sorted(nodes)
    feat = ckpt.get("feat")
    if feat is None:
        # Older checkpoint may not have stored features
        from gnn_v3_train import compute_features as cf
        name_embs, struct = cf(nodes, edges)
        feat = torch.cat([name_embs, struct], dim=-1)
    feat = feat.to(device)

    in_dim = ckpt["in_dim"]
    hidden = ckpt["hidden"]
    n_relations = ckpt["n_relations"]

    encoder = RGCNSAGEEncoder(in_dim, hidden, n_relations).to(device)
    for layer, sd in zip(encoder.layers, ckpt["encoder_layers_state"]):
        layer.load_state_dict(sd)
    for rl, sd_list in zip(encoder.rel_layers, ckpt["encoder_rel_layers_state"]):
        for layer, sd in zip(rl, sd_list):
            layer.load_state_dict(sd)

    scorer = AsymmetricScorer(hidden, n_relations).to(device)
    scorer.rel_emb.load_state_dict(ckpt["scorer_rel_emb_state"])

    return encoder, scorer, feat, ckpt["node_idx"], edges, device


def get_h(encoder, feat, edges, node_idx, device):
    """Compute node embeddings from the full graph."""
    import torch
    sys.path.insert(0, str(REPO))
    from gnn_v3_train import edges_with_rel
    edge_index, edge_rel = edges_with_rel(edges, node_idx, device)
    encoder.layers.eval()
    with torch.no_grad():
        h = encoder.forward(feat, edge_index, edge_rel, len(node_idx))
    return h


def score_pair(scorer, h, node_idx, src: str, dst: str, op: str = "le", device=None):
    import torch
    if device is None:
        device = torch.device("cpu")
    if not src.startswith("qty:"):
        src = "qty:" + src
    if not dst.startswith("qty:"):
        dst = "qty:" + dst
    if src not in node_idx or dst not in node_idx:
        return None
    s_idx = node_idx[src]; d_idx = node_idx[dst]
    rel_id = REL_TO_ID.get(op, 0)
    rel_t = torch.tensor([rel_id], device=device)
    score = scorer.forward(h[s_idx:s_idx+1], h[d_idx:d_idx+1], rel_t)
    return float(score.item())


def adamic_adar(edges, src, dst):
    deg = defaultdict(set)
    for u, v, _ in edges:
        deg[u].add(v); deg[v].add(u)
    common = deg[src] & deg[dst]
    return sum(1 / math.log(max(len(deg[w]), 2)) for w in common)


def cmd_pair(src: str, dst: str, op: str):
    encoder, scorer, feat, node_idx, edges, device = load_v3()
    h = get_h(encoder, feat, edges, node_idx, device)
    if not src.startswith("qty:"):
        src = "qty:" + src
    if not dst.startswith("qty:"):
        dst = "qty:" + dst
    gnn = score_pair(scorer, h, node_idx, src, dst, op, device)
    if gnn is None:
        print(f"unknown node(s): {src!r} or {dst!r}")
        return
    aa = adamic_adar(edges, src, dst)
    print(f"=== pair score: {src[4:]} {op} {dst[4:]} ===")
    print(f"  v3 GNN score: {gnn:+.4f}  (TransE-style: higher = more likely)")
    print(f"  AA score:     {aa:+.4f}")
    print(f"  cross-check: " + (
        "AA-confirmed" if aa > 0 else "AA = 0 (no shared neighbors); treat with caution"
    ))


def cmd_candidates(path: Path, top: int, op_default: str):
    encoder, scorer, feat, node_idx, edges, device = load_v3()
    h = get_h(encoder, feat, edges, node_idx, device)
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip(): continue
        rec = json.loads(line)
        src = rec.get("src") or rec.get("source")
        dst = rec.get("dst") or rec.get("target")
        op = rec.get("op", op_default)
        if not (src and dst): continue
        gnn = score_pair(scorer, h, node_idx, src, dst, op, device)
        s_full = ("qty:" + src) if not src.startswith("qty:") else src
        d_full = ("qty:" + dst) if not dst.startswith("qty:") else dst
        aa = adamic_adar(edges, s_full, d_full)
        rows.append((src, dst, op, gnn if gnn is not None else float("-inf"), aa))
    rows.sort(key=lambda r: -r[3] if r[3] != float("-inf") else 1)
    print(f"=== ranked {len(rows)} candidates ===")
    print(f"  {'rank':>4} {'GNN':>7}  {'AA':>5}  candidate")
    for i, (src, dst, op, gnn, aa) in enumerate(rows[:top], 1):
        gnn_str = f"{gnn:+.3f}" if gnn != float("-inf") else "  N/A"
        marker = "✓" if aa > 0 else "?"
        print(f"  {i:>4}  {gnn_str:>7}  {aa:>4.2f} {marker}  {src} {op} {dst}")


def cmd_top_k_novel(
    top_k: int,
    op: str,
    node_regex: str | None = None,
    exclude_node_regex: str | None = None,
    min_aa: float = 0.0,
    candidate_pool: int = 50,
):
    encoder, scorer, feat, node_idx, edges, device = load_v3()
    h = get_h(encoder, feat, edges, node_idx, device)
    existing = {(u, v) for u, v, _ in edges}
    deg = defaultdict(int)
    for u, v, _ in edges:
        deg[u] += 1; deg[v] += 1
    include_pat = re.compile(node_regex) if node_regex else None
    exclude_pat = re.compile(exclude_node_regex) if exclude_node_regex else None

    def keep_node(node: str) -> bool:
        label = node[4:] if node.startswith("qty:") else node
        if include_pat and not include_pat.search(label):
            return False
        if exclude_pat and exclude_pat.search(label):
            return False
        return True

    candidates_n = [
        n for n, _ in sorted(deg.items(), key=lambda kv: -kv[1])
        if n in node_idx and keep_node(n)
    ][:candidate_pool]
    pairs = [(u, v) for i, u in enumerate(candidates_n)
             for v in candidates_n[i+1:]
             if (u, v) not in existing and (v, u) not in existing]
    rows = []
    for u, v in pairs:
        gnn = score_pair(scorer, h, node_idx, u, v, op, device)
        aa = adamic_adar(edges, u, v)
        if aa >= min_aa:
            rows.append((u[4:], v[4:], gnn, aa))
    rows.sort(key=lambda r: -r[2])
    print(f"=== top-{top_k} novel candidates (op={op}, by v3 GNN score) ===")
    print(f"  scored {len(pairs)} non-existing pairs among {len(candidates_n)} filtered high-degree nodes")
    if node_regex:
        print(f"  include node regex: {node_regex}")
    if exclude_node_regex:
        print(f"  exclude node regex: {exclude_node_regex}")
    if min_aa > 0:
        print(f"  min AA: {min_aa}")
    print(f"  {'rank':>4} {'GNN':>7}  {'AA':>5}  candidate")
    for i, (u, v, gnn, aa) in enumerate(rows[:top_k], 1):
        marker = "✓" if aa > 0 else "?"
        print(f"  {i:>4}  {gnn:+.3f}  {aa:>4.2f} {marker}  {u}  {op}  {v}")
    print(f"\n  ✓ = AA-confirmed (real common neighbors)")
    print(f"  ? = AA = 0; v3 says yes but no structural support; possible artifact")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, metavar=("SRC", "DST"))
    ap.add_argument("--op", default="le", choices=list(REL_TO_ID.keys()))
    ap.add_argument("--candidates", type=Path)
    ap.add_argument("--top-k-novel", type=int, metavar="K")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--node-regex", default=None,
                    help="only score top-k nodes whose quantity label matches this regex")
    ap.add_argument("--exclude-node-regex", default=None,
                    help="drop top-k nodes whose quantity label matches this regex")
    ap.add_argument("--min-aa", type=float, default=0.0,
                    help="minimum Adamic-Adar score for top-k novel output")
    ap.add_argument("--candidate-pool", type=int, default=50,
                    help="number of filtered high-degree nodes used for global top-k")
    args = ap.parse_args()
    if args.pair:
        cmd_pair(args.pair[0], args.pair[1], args.op)
    elif args.candidates:
        cmd_candidates(args.candidates, args.top, args.op)
    elif args.top_k_novel:
        cmd_top_k_novel(
            args.top_k_novel,
            args.op,
            node_regex=args.node_regex,
            exclude_node_regex=args.exclude_node_regex,
            min_aa=args.min_aa,
            candidate_pool=args.candidate_pool,
        )
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
