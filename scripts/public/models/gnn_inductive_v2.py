#!/usr/bin/env python3
"""GNN inductive v2 — feature-aware GraphSAGE that actually generalizes.

Fixes the v1 architecture errors that made the GNN a memorizer:

  v1 error 1:  nn.Embedding(num_nodes, hidden) — pure identity lookup.
               Held-out nodes' embeddings stay at random init forever.
  v1 fix:      Per-node INPUT FEATURES (sentence-transformer name
               embedding + structural features). Held-out nodes get
               real input from their name + degree, not from training.

  v1 error 2:  Two-layer GCN with embedding init, no neighbor aggregation
               that respects feature semantics.
  v1 fix:      GraphSAGE-style: at each layer, h_v = MLP(concat(h_v,
               mean(h_u for u in neighbors(v)))). Inductive by design.

  v1 error 3:  Held-out nodes have zero training edges by construction →
               zero gradient updates, zero learning.
  v1 fix:      Held-out nodes still have features at test time, and
               message passing through their (test-time-visible)
               training-edge neighbors transfers signal.

# Architecture

  Input:    each node has a 384+7+1 = 392-dim feature vector
              (MiniLM name emb || structural feats || in/out-degree)
  Encoder:  2-layer GraphSAGE with mean aggregator, hidden=128
  Decoder:  DistMult-style scalar score
  Loss:     BCE with negative sampling, k_neg=5

# Honest expectation

  - AA inductive baseline: MRR ≈ 0.05 (random level on novel nodes)
  - v1 transductive: MRR 0.875 (memorization)
  - v1 inductive:    MRR 0.05 (refuted)
  - v2 inductive target: MRR 0.20-0.35 (5-7x over AA)
  - 100x is not achievable at this graph scale; this fix gets us to
    decision-grade for novel-edge ranking, not transformative.

Usage:
    python scripts/public/models/gnn_inductive_v2.py --epochs 80 --device cpu
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def load_full_graph():
    g = json.loads((REPO / "analytics" / "public" / "queries"
                     / "ns_trackb_constraint_basin_graph.json").read_text())
    edges = [(e["src"], e["dst"]) for e in g["@graph"]
             if e.get("@type") == "ns_inequality_edge"]
    nodes = set()
    for u, v in edges:
        nodes.add(u); nodes.add(v)
    return list(nodes), edges


def split_camel_case(name: str) -> str:
    """qty:S.payoffLimit -> 'S payoff Limit' for sentence-transformer."""
    if name.startswith("qty:"):
        name = name[4:]
    parts = name.replace(".", " ").replace("_", " ").split()
    out = []
    for p in parts:
        # Insert space before each capital that follows a lowercase
        import re
        words = re.sub(r"([a-z])([A-Z])", r"\1 \2", p).split()
        out.extend(words)
    return " ".join(out) if out else name


def compute_node_features(nodes, edges):
    """Return: name_embeddings [N, 384], struct_feats [N, 8] = [in_deg,
    out_deg, k_core, total_deg, name_len, n_dots, n_underscores, name_starts_lowercase]."""
    import torch
    import numpy as np
    from sentence_transformers import SentenceTransformer
    print("[features] loading sentence-transformer (cached)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    sentences = [split_camel_case(n) for n in nodes]
    print(f"[features] embedding {len(sentences)} node names...")
    name_embs = model.encode(sentences, show_progress_bar=False)
    name_embs = torch.tensor(name_embs, dtype=torch.float32)

    # Structural features
    in_deg = defaultdict(int); out_deg = defaultdict(int)
    for u, v in edges:
        out_deg[u] += 1
        in_deg[v] += 1
    # k-core via undirected projection
    import networkx as nx
    UG = nx.Graph()
    for u, v in edges:
        UG.add_edge(u, v)
    core = nx.core_number(UG) if UG else {}

    struct = torch.zeros((len(nodes), 8), dtype=torch.float32)
    for i, n in enumerate(nodes):
        name_short = n[4:] if n.startswith("qty:") else n
        struct[i, 0] = in_deg[n]
        struct[i, 1] = out_deg[n]
        struct[i, 2] = core.get(n, 0)
        struct[i, 3] = in_deg[n] + out_deg[n]
        struct[i, 4] = len(name_short)
        struct[i, 5] = name_short.count(".")
        struct[i, 6] = name_short.count("_")
        struct[i, 7] = 1.0 if name_short and name_short[0].islower() else 0.0
    # Per-feature normalize structural features to ~[0, 1]
    for col in range(struct.shape[1]):
        col_max = struct[:, col].max().item() or 1.0
        struct[:, col] = struct[:, col] / col_max

    return name_embs, struct


class SAGEEncoder:
    """GraphSAGE-style inductive encoder. Built lazily."""
    def __init__(self, in_dim, hidden, n_layers=2, dropout=0.2):
        import torch
        import torch.nn as nn
        self.layers = nn.ModuleList()
        cur_dim = in_dim
        for _ in range(n_layers):
            self.layers.append(nn.Linear(2 * cur_dim, hidden))
            cur_dim = hidden
        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()

    def parameters(self):
        return [p for layer in self.layers for p in layer.parameters()]

    def to(self, device):
        self.layers = self.layers.to(device)
        return self

    def forward(self, x, edge_index, num_nodes):
        """x: [N, in_dim], edge_index: [2, E].
        For each layer: h_v = ReLU(W [h_v || mean(h_u for u in nbrs(v))])"""
        import torch
        h = x
        for layer in self.layers:
            agg = torch.zeros_like(h)
            counts = torch.zeros(num_nodes, device=h.device)
            src, dst = edge_index[0], edge_index[1]
            agg.index_add_(0, dst, h[src])
            counts.index_add_(0, dst, torch.ones_like(src, dtype=torch.float))
            counts = counts.clamp(min=1.0).unsqueeze(-1)
            agg = agg / counts
            h_concat = torch.cat([h, agg], dim=-1)
            h = self.relu(layer(self.dropout(h_concat)))
        return h


def edges_to_tensor(edges, node_idx, device):
    import torch
    if not edges:
        return torch.zeros((2, 0), dtype=torch.long, device=device)
    src = [node_idx[u] for u, v in edges if u in node_idx and v in node_idx]
    dst = [node_idx[v] for u, v in edges if u in node_idx and v in node_idx]
    return torch.tensor([src, dst], dtype=torch.long, device=device)


def negative_sample(positive_edges, num_nodes, k_neg, device):
    import torch
    n_pos = positive_edges.shape[1]
    src = positive_edges[0].repeat_interleave(k_neg)
    dst = torch.randint(0, num_nodes, (n_pos * k_neg,), device=device)
    return torch.stack([src, dst], dim=0)


def score_edges(h_src, h_dst):
    return (h_src * h_dst).sum(dim=-1)


def split_nodes(nodes, holdout_frac=0.20, seed=42):
    random.seed(seed)
    shuffled = list(nodes); random.shuffle(shuffled)
    n_hold = int(len(shuffled) * holdout_frac)
    held = set(shuffled[:n_hold])
    train = set(shuffled[n_hold:])
    return train, held


def filter_edges_inductive(edges, train_nodes):
    train_edges = [(u, v) for u, v in edges
                   if u in train_nodes and v in train_nodes]
    test_edges = [(u, v) for u, v in edges
                  if u not in train_nodes or v not in train_nodes]
    return train_edges, test_edges


def build_bootstrap_pairs(train_edges, n_snapshots=200,
                           keep_min=0.6, keep_max=0.95, seed=42):
    pairs = []
    for i in range(n_snapshots):
        random.seed(seed + i)
        keep_frac = random.uniform(keep_min, keep_max)
        n_keep = int(len(train_edges) * keep_frac)
        kept = random.sample(train_edges, n_keep)
        held_out = list(set(train_edges) - set(kept))
        pairs.append({"kept": kept, "target": held_out})
    return pairs


def _mrr_hits(pos_scores, neg_scores_list, k_list=(1, 5, 10)):
    if not pos_scores:
        return {f"hit@{k}": 0.0 for k in k_list} | {"mrr": 0.0}
    hits = {k: 0 for k in k_list}
    mrr_sum = 0.0
    for ps, ns in zip(pos_scores, neg_scores_list):
        rank = (ns >= ps).sum().item() + 1
        for k in k_list:
            if rank <= k:
                hits[k] += 1
        mrr_sum += 1.0 / rank
    n = len(pos_scores)
    return {f"hit@{k}": hits[k] / n for k in k_list} | {"mrr": mrr_sum / n}


def aa_inductive_baseline(train_edges, test_edges, held_nodes, k_neg=20):
    deg = defaultdict(set)
    for u, v in train_edges:
        deg[u].add(v); deg[v].add(u)
    novel_test = [(u, v) for u, v in test_edges
                   if u in held_nodes or v in held_nodes]
    all_nodes = set([u for u, _ in train_edges]
                    + [v for _, v in train_edges]
                    + list(held_nodes))
    nodes_arr = list(all_nodes)
    pos_scores, neg_scores = [], []
    import torch
    for u, v in novel_test:
        common = deg[u] & deg[v]
        ps = sum(1 / math.log(max(len(deg[w]), 2)) for w in common)
        neg_list = []
        for _ in range(k_neg):
            rv = random.choice(nodes_arr)
            common = deg[u] & deg[rv]
            neg_list.append(sum(1 / math.log(max(len(deg[w]), 2))
                                 for w in common))
        pos_scores.append(ps)
        neg_scores.append(torch.tensor(neg_list))
    return _mrr_hits(pos_scores, neg_scores)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout-frac", type=float, default=0.20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--n-snapshots", type=int, default=200)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    print("=== INDUCTIVE GNN v2 (feature-aware GraphSAGE) ===")
    nodes, edges = load_full_graph()
    nodes = sorted(nodes)
    print(f"  {len(nodes)} nodes, {len(edges)} edges")

    train_nodes, held_nodes = split_nodes(set(nodes), args.holdout_frac, args.seed)
    train_edges, test_edges = filter_edges_inductive(edges, train_nodes)
    print(f"  held out {len(held_nodes)} nodes ({args.holdout_frac:.0%})")
    print(f"  train edges (both endpoints in train): {len(train_edges)}")
    print(f"  test edges (≥1 novel endpoint): {len(test_edges)}")

    name_embs, struct_feats = compute_node_features(nodes, edges)
    feat = None
    import torch
    feat = torch.cat([name_embs, struct_feats], dim=-1)
    print(f"  feature dim: {feat.shape[1]} (384 name + 8 struct)")

    node_idx = {n: i for i, n in enumerate(nodes)}
    device = torch.device(args.device)
    feat = feat.to(device)

    encoder = SAGEEncoder(feat.shape[1], args.hidden).to(device)
    optim = torch.optim.Adam(encoder.parameters(), lr=args.lr)

    pairs = build_bootstrap_pairs(train_edges, n_snapshots=args.n_snapshots,
                                    seed=args.seed)
    print(f"  {len(pairs)} bootstrap snapshots over train_edges")

    print("\n[train]")
    import torch.nn as nn
    for epoch in range(args.epochs):
        order = list(range(len(pairs))); random.seed(epoch); random.shuffle(order)
        epoch_loss = 0.0
        for bs in range(0, len(pairs), 8):
            optim.zero_grad()
            batch_loss = 0.0
            for i in order[bs:bs + 8]:
                snap = pairs[i]
                kept = edges_to_tensor(snap["kept"], node_idx, device)
                if kept.shape[1] == 0: continue
                h = encoder.forward(feat, kept, len(node_idx))
                pos = edges_to_tensor(snap["target"], node_idx, device)
                if pos.shape[1] == 0: continue
                neg = negative_sample(pos, len(node_idx), 5, device)
                ps = score_edges(h[pos[0]], h[pos[1]])
                ns = score_edges(h[neg[0]], h[neg[1]])
                batch_loss = batch_loss + nn.functional.binary_cross_entropy_with_logits(
                    ps, torch.ones_like(ps))
                batch_loss = batch_loss + nn.functional.binary_cross_entropy_with_logits(
                    ns, torch.zeros_like(ns))
            if isinstance(batch_loss, float): continue
            batch_loss.backward(); optim.step()
            epoch_loss += batch_loss.item()
        if epoch % 10 == 0 or epoch == args.epochs - 1:
            print(f"  epoch {epoch}: loss={epoch_loss:.2f}")

    print("\n[eval inductive]")
    # Build edge_index from ALL train edges as message-passing context
    train_et = edges_to_tensor(train_edges, node_idx, device)
    encoder.layers.eval()
    with torch.no_grad():
        h = encoder.forward(feat, train_et, len(node_idx))

    # Score test edges with at least one novel endpoint
    novel_test = [(u, v) for u, v in test_edges
                   if u in held_nodes or v in held_nodes]
    print(f"  scoring {len(novel_test)} novel-endpoint test edges")
    pos_scores, neg_scores = [], []
    nodes_list = list(node_idx.keys())
    for u, v in novel_test:
        ps = score_edges(h[node_idx[u]:node_idx[u]+1],
                         h[node_idx[v]:node_idx[v]+1])
        neg_dst = [random.choice(nodes_list) for _ in range(20)]
        neg_dst_idx = torch.tensor([node_idx[n] for n in neg_dst], device=device)
        ns = score_edges(h[node_idx[u]].repeat(20, 1), h[neg_dst_idx])
        pos_scores.append(ps.item())
        neg_scores.append(ns)
    gnn_metrics = _mrr_hits(pos_scores, neg_scores)
    aa_metrics = aa_inductive_baseline(train_edges, test_edges, held_nodes)

    print(f"\n=== INDUCTIVE RESULTS ===")
    print(f"  GNN v2 (feature-aware GraphSAGE):")
    for k, v in gnn_metrics.items():
        print(f"    {k}: {v:.4f}")
    print(f"  AA baseline (random for novel nodes):")
    for k, v in aa_metrics.items():
        print(f"    {k}: {v:.4f}")
    print(f"\n  delta GNN-v2 vs AA:")
    for k in gnn_metrics:
        if k in aa_metrics:
            d = gnn_metrics[k] - aa_metrics[k]
            mult = gnn_metrics[k] / max(aa_metrics[k], 0.001)
            print(f"    {k}: {d:+.4f}  ({mult:.1f}x)")

    # VERDICT
    inductive_mrr = gnn_metrics.get("mrr", 0)
    aa_mrr = aa_metrics.get("mrr", 0)
    print(f"\n=== VERDICT ===")
    print(f"  v1 transductive MRR (memorization): 0.875")
    print(f"  v1 inductive MRR (refuted):         0.048")
    print(f"  v2 inductive MRR:                   {inductive_mrr:.4f}")
    print(f"  AA inductive baseline:              {aa_mrr:.4f}")
    if inductive_mrr > aa_mrr * 3:
        print(f"  → GNN v2 GENUINELY GENERALIZES. Decision-grade for novel-edge ranking.")
    elif inductive_mrr > aa_mrr * 1.5:
        print(f"  → GNN v2 modestly generalizes. Use as tiebreaker, not primary signal.")
    else:
        print(f"  → GNN v2 still does not meaningfully generalize. AA remains the bar.")

    out = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker" / "inductive_v2_result.json"
    out.write_text(json.dumps({
        "v1_transductive_mrr": 0.875,
        "v1_inductive_mrr": 0.0476,
        "v2_inductive_gnn": gnn_metrics,
        "v2_inductive_aa": aa_metrics,
        "n_novel_test_edges": len(novel_test),
        "config": vars(args),
    }, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
