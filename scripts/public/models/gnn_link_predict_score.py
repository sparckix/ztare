#!/usr/bin/env python3
"""GNN inference — score candidate inequality edges using the trained checkpoint.

Loads the RGCN-lite checkpoint trained 2026-05-05 on Lambda A10. Scores
arbitrary candidate edges (u, v) and ranks them by predicted edge
probability. CPU-only; checkpoint is 132 KB.

# Inputs
  - Checkpoint: analytics/public/leanmill/gnn_ranker/gnn_checkpoint.pt (committed)
  - Candidate edges: either via --candidates arg (list of pairs) OR a JSONL
    file with {"src": "qty:foo", "dst": "qty:bar"} per line.

# Outputs
  - Per-candidate score (higher = more likely to be a "real" inequality)
  - Adamic-Adar baseline score on same candidates for comparison
  - Combined ranking

# Use cases
  1. Score the transitivity-closure top-3915 candidates: pipe
     orientation_synthesizer output through this for a prioritized list
  2. Score a hand-curated nominee set before submitting to lake build
  3. Validate Gemini's nominations against the GNN's structural prior

# Honest caveats
  - Test-time MRR was 0.875 on bootstrap dropout (held-out edges from
    same graph). Performance on TRULY novel inequalities (added by
    Codex tomorrow) is unverified — likely lower.
  - Score scale is logit-shaped; calibrate by ranking, not absolute value.
  - Identifiers must use 'qty:' prefix to match training-time names.

Usage:
    # score a single candidate pair
    python scripts/public/models/gnn_link_predict_score.py --pair qty:radialPowerWeight qty:calderonCommutatorResidualDecouple

    # score a JSONL file
    python scripts/public/models/gnn_link_predict_score.py --candidates projects/ns_millennium_hunt/workspace/queries/orientation_synthesized_candidates.jsonl --top 30

    # rank top-K predicted edges across ALL non-existing pairs
    python scripts/public/models/gnn_link_predict_score.py --top-k-novel 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

CHECKPOINT = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker" / "gnn_checkpoint.pt"
GRAPH_PATH = REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "ns_trackb_constraint_basin_graph.json"


def load_model():
    import torch
    from gnn_link_prediction_train import GCNEncoder, edges_to_tensor, score_edges
    if not CHECKPOINT.exists():
        print(f"missing {CHECKPOINT}; run scripts/public/models/gnn_link_prediction_train.py first")
        sys.exit(1)
    ckpt = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
    device = torch.device("cpu")
    encoder = GCNEncoder(len(ckpt["node_idx"]), ckpt["hidden"],
                          ckpt["num_relations"]).to(device)
    encoder.embed.load_state_dict(ckpt["embed_state"])
    for layer, sd in zip(encoder.W, ckpt["W_state"]):
        layer.load_state_dict(sd)
    for layer, sd in zip(encoder.rel_W, ckpt["rel_W_state"]):
        layer.load_state_dict(sd)
    return encoder, ckpt["node_idx"], device


def get_full_graph_edges():
    """Use full graph as the message-passing context."""
    if not GRAPH_PATH.exists():
        print(f"missing {GRAPH_PATH}; run projects/ns_millennium_hunt/scripts/ns_graph.py constraint --extract")
        sys.exit(1)
    g = json.loads(GRAPH_PATH.read_text())
    return [(e["src"], e["dst"]) for e in g["@graph"]
             if e.get("@type") == "ns_inequality_edge"]


def compute_node_embeddings(encoder, node_idx, device):
    """One forward pass on the full graph; returns h[N, hidden]."""
    import torch
    from gnn_link_prediction_train import edges_to_tensor
    full_edges = get_full_graph_edges()
    full_edges_in_idx = [(u, v) for u, v in full_edges
                          if u in node_idx and v in node_idx]
    et = edges_to_tensor(full_edges_in_idx, node_idx, device)
    edge_type = torch.zeros(et.shape[1], dtype=torch.long, device=device)
    with torch.no_grad():
        h = encoder.forward(et, edge_type, len(node_idx))
    return h


def score_pair(h, node_idx, src: str, dst: str) -> float | None:
    import torch
    from gnn_link_prediction_train import score_edges
    if src not in node_idx or dst not in node_idx:
        return None
    s = torch.tensor([node_idx[src]])
    d = torch.tensor([node_idx[dst]])
    with torch.no_grad():
        score = score_edges(h[s], h[d])
    return float(score.item())


def adamic_adar_score(graph_edges, src, dst):
    import math
    from collections import defaultdict
    deg = defaultdict(set)
    for u, v in graph_edges:
        deg[u].add(v); deg[v].add(u)
    common = deg[src] & deg[dst]
    return sum(1 / math.log(max(len(deg[w]), 2)) for w in common)


def cmd_pair(src: str, dst: str):
    encoder, node_idx, device = load_model()
    h = compute_node_embeddings(encoder, node_idx, device)
    if not src.startswith("qty:"):
        src = "qty:" + src
    if not dst.startswith("qty:"):
        dst = "qty:" + dst
    gnn = score_pair(h, node_idx, src, dst)
    if gnn is None:
        print(f"unknown node(s): {src!r} or {dst!r} not in trained vocab")
        return
    aa = adamic_adar_score(get_full_graph_edges(), src, dst)
    print(f"=== pair score: {src[4:]} -> {dst[4:]} ===")
    print(f"  GNN logit: {gnn:+.4f}  (higher = more likely to be a real inequality)")
    print(f"  AA score:  {aa:+.4f}")


def cmd_candidates(path: Path, top: int):
    encoder, node_idx, device = load_model()
    h = compute_node_embeddings(encoder, node_idx, device)
    full_edges = get_full_graph_edges()
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        # Accept either {"src": ..., "dst": ...} or top-level "src"/"dst" of any source
        src = rec.get("src") or rec.get("source")
        dst = rec.get("dst") or rec.get("target")
        if src and not src.startswith("qty:"):
            src = "qty:" + src
        if dst and not dst.startswith("qty:"):
            dst = "qty:" + dst
        if not (src and dst):
            continue
        gnn = score_pair(h, node_idx, src, dst)
        aa = adamic_adar_score(full_edges, src, dst)
        rows.append((src[4:] if src else "?",
                      dst[4:] if dst else "?",
                      gnn if gnn is not None else float("-inf"),
                      aa))
    rows.sort(key=lambda r: -r[2] if r[2] is not None else 0)
    print(f"=== ranked {len(rows)} candidates (top {top}) ===")
    print(f"  {'rank':>4} {'GNN':>8}  {'AA':>6}  edge")
    for i, (src, dst, gnn, aa) in enumerate(rows[:top], 1):
        gnn_str = f"{gnn:+.3f}" if gnn != float("-inf") else "  N/A"
        print(f"  {i:>4}  {gnn_str:>8}  {aa:>5.2f}  {src} -- {dst}")


def cmd_top_k_novel(top_k: int):
    """Score every non-existing pair among top-degree nodes; rank by GNN logit."""
    import torch
    encoder, node_idx, device = load_model()
    h = compute_node_embeddings(encoder, node_idx, device)
    full_edges = get_full_graph_edges()
    existing = set(full_edges)
    # Score top-50 most-connected nodes' pairs
    from collections import defaultdict
    deg = defaultdict(int)
    for u, v in full_edges:
        deg[u] += 1; deg[v] += 1
    candidates = [n for n, _ in sorted(deg.items(), key=lambda kv: -kv[1])
                   if n in node_idx][:50]
    pairs = [(u, v) for i, u in enumerate(candidates)
             for v in candidates[i + 1:]
             if (u, v) not in existing and (v, u) not in existing]
    rows = []
    for u, v in pairs:
        gnn = score_pair(h, node_idx, u, v)
        aa = adamic_adar_score(full_edges, u, v)
        rows.append((u[4:], v[4:], gnn, aa))
    rows.sort(key=lambda r: -r[2])
    print(f"=== top-{top_k} novel inequality candidates (by GNN score) ===")
    print(f"  scored {len(pairs)} non-existing pairs among 50 highest-degree nodes")
    print(f"  {'rank':>4} {'GNN':>8}  {'AA':>6}  candidate edge")
    for i, (u, v, gnn, aa) in enumerate(rows[:top_k], 1):
        print(f"  {i:>4}  {gnn:+.3f}  {aa:>5.2f}  {u}  --  {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, metavar=("SRC", "DST"),
                    help="score a single candidate pair (qty: prefix optional)")
    ap.add_argument("--candidates", type=Path,
                    help="score a JSONL file of candidates")
    ap.add_argument("--top-k-novel", type=int, metavar="K",
                    help="rank K most-likely missing inequalities globally")
    ap.add_argument("--top", type=int, default=30,
                    help="how many results to print")
    args = ap.parse_args()
    if args.pair:
        cmd_pair(args.pair[0], args.pair[1])
    elif args.candidates:
        cmd_candidates(args.candidates, args.top)
    elif args.top_k_novel:
        cmd_top_k_novel(args.top_k_novel)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
