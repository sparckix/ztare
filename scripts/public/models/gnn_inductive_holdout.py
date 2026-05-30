#!/usr/bin/env python3
"""Inductive GNN holdout — does the link-predictor generalize to unseen nodes?

Bootstrap eval (the +103% MRR run on 2026-05-05) is *transductive*: train
and test share the same node set, the GNN just predicts which edges were
randomly held out. This script runs the *inductive* eval that would
falsify or confirm the GNN's actual generalization claim.

# Protocol

1. Hold out 20% of NODES uniformly at random.
2. Build training snapshots from edges where BOTH endpoints are NOT
   held-out nodes (so the GNN never sees held-out nodes at training).
3. Eval set: edges where AT LEAST ONE endpoint is a held-out node.
4. Train RGCN-lite identical to the bootstrap run.
5. Compare: inductive MRR / hit@K to bootstrap MRR / hit@K and to
   Adamic-Adar's inductive baseline.

# What outcomes mean

  - Inductive MRR collapses to AA-baseline level → GNN was memorizing
    node embeddings; the +103% bootstrap claim is unreliable for
    "predict the next lemma" use cases. Trust AA, kill GNN claim.
  - Inductive MRR remains substantially above AA → GNN learned
    transferable structure; bootstrap claim becomes credible for new
    nodes too. Promote to decision-grade.
  - Intermediate (GNN > AA but gap narrows) → GNN learned partial
    transferable signal + partial memorization; honest middle.

Usage:
    python scripts/public/models/gnn_inductive_holdout.py
    python scripts/public/models/gnn_inductive_holdout.py --epochs 80 --hidden 64 --device cpu
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


def split_nodes(nodes, holdout_frac=0.20, seed=42):
    random.seed(seed)
    shuffled = list(nodes); random.shuffle(shuffled)
    n_hold = int(len(shuffled) * holdout_frac)
    held = set(shuffled[:n_hold])
    train = set(shuffled[n_hold:])
    return train, held


def filter_edges_inductive(edges, train_nodes):
    """train edges: BOTH endpoints in train_nodes."""
    train_edges = [(u, v) for u, v in edges
                   if u in train_nodes and v in train_nodes]
    test_edges = [(u, v) for u, v in edges
                  if u not in train_nodes or v not in train_nodes]
    return train_edges, test_edges


def build_bootstrap_pairs_inductive(train_edges, n_snapshots=200,
                                     keep_min=0.6, keep_max=0.95, seed=42):
    """Same as gnn_training_data_prep bootstrap mode, but on inductive train_edges."""
    pairs = []
    for i in range(n_snapshots):
        random.seed(seed + i)
        keep_frac = random.uniform(keep_min, keep_max)
        n_keep = int(len(train_edges) * keep_frac)
        kept = random.sample(train_edges, n_keep)
        held_out = list(set(train_edges) - set(kept))
        pairs.append({
            "graph_edges_at_t": kept,
            "target_added_edges": held_out,
        })
    return pairs


def train_gnn_inductive(pairs, all_nodes, hidden, epochs, device, lr=1e-3,
                         k_neg=5, batch_size=8):
    """Train RGCN-lite on inductive pairs; return encoder + node_idx.

    node_idx covers ALL nodes (train + held-out) so we can score test
    edges later. Held-out nodes' embeddings stay at random init since
    they never appear in training pairs — that IS the inductive test.
    """
    import torch
    import torch.nn as nn
    from gnn_link_prediction_train import (
        GCNEncoder, edges_to_tensor, negative_sample, score_edges,
    )
    nodes_sorted = sorted(all_nodes)
    node_idx = {n: i for i, n in enumerate(nodes_sorted)}
    num_nodes = len(node_idx)
    encoder = GCNEncoder(num_nodes, hidden, 1).to(device)
    optimizer = torch.optim.Adam(encoder.parameters(), lr=lr)
    print(f"[train inductive] num_nodes={num_nodes}, num_pairs={len(pairs)}")
    for epoch in range(epochs):
        order = list(range(len(pairs))); random.seed(epoch); random.shuffle(order)
        epoch_loss = 0.0
        for bs in range(0, len(pairs), batch_size):
            optimizer.zero_grad()
            loss = 0.0
            for i in order[bs:bs + batch_size]:
                snap = pairs[i]
                kept = edges_to_tensor(snap["graph_edges_at_t"], node_idx, device)
                if kept.shape[1] == 0:
                    continue
                et = torch.zeros(kept.shape[1], dtype=torch.long, device=device)
                h = encoder.forward(kept, et, num_nodes)
                pos = edges_to_tensor(snap["target_added_edges"], node_idx, device)
                if pos.shape[1] == 0:
                    continue
                neg = negative_sample(pos, num_nodes, k_neg, device)
                ps = score_edges(h[pos[0]], h[pos[1]])
                ns = score_edges(h[neg[0]], h[neg[1]])
                loss = loss + nn.functional.binary_cross_entropy_with_logits(
                    ps, torch.ones_like(ps))
                loss = loss + nn.functional.binary_cross_entropy_with_logits(
                    ns, torch.zeros_like(ns))
            if isinstance(loss, float):
                continue
            loss.backward(); optimizer.step()
            epoch_loss += loss.item()
        if epoch % 20 == 0:
            print(f"  epoch {epoch}: loss={epoch_loss:.2f}")
    return encoder, node_idx


def evaluate_inductive_gnn(encoder, train_edges, test_edges, node_idx,
                            device, held_nodes, k_neg=20):
    """Eval on test edges where ≥1 endpoint is a held-out (novel) node.

    All test-edge endpoints are in node_idx (we extended node_idx to
    cover full graph), but held-out endpoints have UNTRAINED embeddings.
    This is the canonical inductive test: the GNN must generalize to
    novel nodes via message passing through training edges.

    Message-passing context: all train edges (between non-held nodes).
    Held-out nodes have no inbound train edges, so their embedding is
    just `embed.weight[i]` (random init).
    """
    import torch
    from gnn_link_prediction_train import edges_to_tensor, score_edges
    encoder.embed.eval()
    # Test edges where both endpoints exist in our node_idx (always true
    # for full-graph index, just sanity check)
    valid_test = [(u, v) for u, v in test_edges
                   if u in node_idx and v in node_idx]
    novel_endpoint_test = [(u, v) for u, v in valid_test
                            if u in held_nodes or v in held_nodes]
    print(f"  test edges: {len(test_edges)} total, "
          f"{len(novel_endpoint_test)} have ≥1 novel endpoint")

    et = edges_to_tensor(train_edges, node_idx, device)
    edge_type = torch.zeros(et.shape[1], dtype=torch.long, device=device)
    with torch.no_grad():
        h = encoder.forward(et, edge_type, len(node_idx))
    pos_scores, neg_scores = [], []
    nodes_arr = list(node_idx.keys())
    for u, v in novel_endpoint_test:
        ps = score_edges(h[node_idx[u]:node_idx[u]+1],
                         h[node_idx[v]:node_idx[v]+1])
        neg_dst = [random.choice(nodes_arr) for _ in range(k_neg)]
        neg_dst_idx = torch.tensor([node_idx[n] for n in neg_dst],
                                    device=device)
        ns = score_edges(h[node_idx[u]].repeat(k_neg, 1), h[neg_dst_idx])
        pos_scores.append(ps.item())
        neg_scores.append(ns)
    return (_mrr_hits(pos_scores, neg_scores),
            len(novel_endpoint_test), len(test_edges) - len(novel_endpoint_test))


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
    """Adamic-Adar baseline on test edges with novel endpoints.

    For a novel-endpoint test edge (u, v) where u is held-out: u has 0
    neighbors in the train graph; common neighbors = empty set; AA = 0.
    This is the appropriate baseline — AA naturally fails on truly novel
    nodes, which sets the bar the GNN has to beat to be 'generalizing'.
    """
    from collections import defaultdict
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
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--n-snapshots", type=int, default=200)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    print("=== INDUCTIVE GNN HOLDOUT ===")
    nodes, edges = load_full_graph()
    print(f"  full graph: {len(nodes)} nodes, {len(edges)} edges")
    train_nodes, held_nodes = split_nodes(nodes, args.holdout_frac, args.seed)
    print(f"  held out {len(held_nodes)}/{len(nodes)} nodes "
          f"({args.holdout_frac:.0%})")
    train_edges, test_edges = filter_edges_inductive(edges, train_nodes)
    print(f"  train edges (both endpoints in train_nodes): {len(train_edges)}")
    print(f"  test edges (≥1 endpoint held-out): {len(test_edges)}")

    if not train_edges or not test_edges:
        print("insufficient edges; bailing")
        return 1

    pairs = build_bootstrap_pairs_inductive(
        train_edges, n_snapshots=args.n_snapshots, seed=args.seed)
    print(f"  {len(pairs)} inductive bootstrap snapshots\n")

    import torch
    device = torch.device(args.device)
    # Train with FULL node vocab (held-out nodes get random init, never
    # touched during training)
    encoder, node_idx = train_gnn_inductive(
        pairs, set(nodes), args.hidden, args.epochs, device)

    print("\n=== eval ===")
    gnn_metrics, n_novel, n_other = evaluate_inductive_gnn(
        encoder, train_edges, test_edges, node_idx, device, held_nodes)
    aa_metrics = aa_inductive_baseline(train_edges, test_edges, held_nodes)

    print(f"\n=== inductive results (vs bootstrap MRR 0.875) ===")
    print(f"  GNN inductive (n={n_novel} novel-endpoint test edges):")
    for k, v in gnn_metrics.items():
        print(f"    {k}: {v:.4f}")
    print(f"  AA inductive baseline:")
    for k, v in aa_metrics.items():
        print(f"    {k}: {v:.4f}")
    print(f"\n  other test edges (no novel endpoint): {n_other}")
    print(f"\n  delta GNN vs AA:")
    for k in gnn_metrics:
        if k in aa_metrics:
            d = gnn_metrics[k] - aa_metrics[k]
            print(f"    {k}: {d:+.4f}")

    # VERDICT
    bootstrap_mrr = 0.875
    inductive_mrr = gnn_metrics.get("mrr", 0)
    aa_mrr = aa_metrics.get("mrr", 0)
    print(f"\n=== VERDICT ===")
    print(f"  bootstrap MRR (transductive):  {bootstrap_mrr:.4f}")
    print(f"  inductive MRR (this run):      {inductive_mrr:.4f}")
    print(f"  inductive AA baseline MRR:     {aa_mrr:.4f}")
    if inductive_mrr < aa_mrr * 1.10:
        print(f"  → GNN was MEMORIZING. Inductive performance ≈ AA. "
              f"Discount the +103% bootstrap claim.")
    elif inductive_mrr > aa_mrr * 1.5:
        print(f"  → GNN GENERALIZES. Inductive >> AA. The bootstrap +103% "
              f"becomes credible for novel-edge prediction too.")
    else:
        print(f"  → MIXED. GNN learned partial transferable signal + partial "
              f"memorization. Honest middle.")

    out = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker" / "inductive_holdout_result.json"
    out.write_text(json.dumps({
        "bootstrap_mrr": bootstrap_mrr,
        "inductive_gnn": gnn_metrics,
        "inductive_aa": aa_metrics,
        "n_novel_endpoint_test": n_novel,
        "n_other_test": n_other,
        "config": vars(args),
    }, indent=2))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
