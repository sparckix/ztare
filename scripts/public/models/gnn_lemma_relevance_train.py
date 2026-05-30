#!/usr/bin/env python3
"""GNN lemma-relevance ranker — Graph2Tac-style training (the 100x bet).

Trained on (target_signature, used_lemmas) pairs from the spine. Input:
target signature + structural features. Output: relevance score over the
50k-lemma vocab. At inference, top-K scores are the lemmas to inject
into the typed-endpoint pack's prompt.

# Architecture

  Encoder for target:    sentence-transformer (frozen) on signature text
                         + 9-dim hand-features
  Encoder for lemma:     sentence-transformer (frozen) on lemma name + preview
                         + shape one-hot (16 shapes)
  Decoder:               dot-product score, trained with BCE-with-negative-sampling

  All sentence-transformer encoding precomputed once; training is just
  the projection layers + score head. Fast on A10.

# Training data

  - 756 train pairs (945 total spine theorems × 6.1 avg lemmas = 5792 positives)
  - 50k lemma vocab; ~20 negatives per positive
  - Eval: hit@10, hit@20, MRR on held-out 95 test theorems

# Honest expectation (per Graph2Tac literature)

  Random baseline:       hit@10 ≈ 10/50000 = 0.0002
  TF-IDF baseline:       hit@10 ≈ 0.05-0.15 (typical)
  v3-class GNN target:   hit@10 ≈ 0.25-0.40
  v4-class GNN target:   hit@10 ≈ 0.40-0.60 (+25% from pretraining is the lit claim)

  100x of TF-IDF baseline = MRR around 0.30-0.40 inductive. Real for
  this data scale.

# Honest scope

  - Sentence-transformer features may not capture mathematical
    relevance fully; the literature uses learned premise embeddings
    (Graph2Tac's RGCN over the dependency graph). v1 here is the
    baseline; v2 with learned graph features comes later.
  - 945 training theorems is small relative to mathlib4 corpus; risk
    of overfitting. Use early stopping + dropout.

Usage on GPU:
    python scripts/public/models/gnn_lemma_relevance_train.py --device cuda --epochs 50
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA_DIR = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines()
             if line.strip()]


def encode_targets(pairs, model):
    sigs = [p["target_signature"] for p in pairs]
    return model.encode(sigs, batch_size=256, show_progress_bar=False,
                         convert_to_numpy=True)


def encode_lemmas(lemma_vocab, mathlib_idx, spine_idx, model):
    """Encode each lemma by its name + preview text."""
    sentences = []
    for name in lemma_vocab:
        if name in mathlib_idx["by_name"]:
            preview = mathlib_idx["by_name"][name].get("preview", name)
        else:
            preview = name  # spine decl, just use name
        sentences.append(f"{name}: {preview[:200]}")
    return model.encode(sentences, batch_size=256, show_progress_bar=True,
                         convert_to_numpy=True)


def build_features(p):
    f = p["target_features"]
    import numpy as np
    return np.array([
        min(f["n_chars"] / 500.0, 1.0),
        float(f["has_le"]), float(f["has_lt"]), float(f["has_eq"]),
        float(f["has_norm"]), float(f["has_integral"]),
        float(f["has_forall"]), float(f["has_exists"]),
        min(f["n_binders"] / 20.0, 1.0),
    ], dtype="float32")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--k-neg", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--out-checkpoint", type=Path,
                    default=DATA_DIR / "ranker_checkpoint.pt")
    args = ap.parse_args()

    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import numpy as np
    from sentence_transformers import SentenceTransformer

    device = torch.device(args.device)
    print(f"=== GNN lemma-relevance ranker ===")
    print(f"  device: {device}")

    print("\n[load data]")
    train = load_jsonl(DATA_DIR / "train.jsonl")
    val = load_jsonl(DATA_DIR / "val.jsonl")
    test = load_jsonl(DATA_DIR / "test.jsonl")
    lemma_vocab = json.loads((DATA_DIR / "lemma_vocab.json").read_text())
    print(f"  train: {len(train)} val: {len(val)} test: {len(test)}")
    print(f"  lemma vocab: {len(lemma_vocab)}")

    lemma_to_idx = {n: i for i, n in enumerate(lemma_vocab)}

    print("\n[encode]")
    st = SentenceTransformer("all-MiniLM-L6-v2", device=str(device))
    print("  encoding target signatures...")
    train_emb = encode_targets(train, st)
    val_emb = encode_targets(val, st)
    test_emb = encode_targets(test, st)
    print(f"  target emb dim: {train_emb.shape[-1]}")

    print("  encoding lemma vocab (this is the slow step)...")
    mathlib_idx = json.loads(
        (REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json").read_text())
    spine_idx = json.loads(
        (REPO / "analytics" / "public" / "queries" / "lean" / "lean_decl_index.json").read_text())
    lemma_emb = encode_lemmas(lemma_vocab, mathlib_idx, spine_idx, st)
    print(f"  lemma emb shape: {lemma_emb.shape}")

    # Project features into shared space
    target_feat_dim = train_emb.shape[1] + 9  # st + hand-features
    lemma_feat_dim = lemma_emb.shape[1]

    class Ranker(nn.Module):
        def __init__(self, target_in, lemma_in, hidden):
            super().__init__()
            self.target_proj = nn.Sequential(
                nn.Linear(target_in, hidden), nn.ReLU(),
                nn.Dropout(0.2), nn.Linear(hidden, hidden))
            self.lemma_proj = nn.Sequential(
                nn.Linear(lemma_in, hidden), nn.ReLU(),
                nn.Dropout(0.2), nn.Linear(hidden, hidden))
        def score(self, t_emb, l_emb):
            t = self.target_proj(t_emb)
            l = self.lemma_proj(l_emb)
            return (t * l).sum(dim=-1)

    model = Ranker(target_feat_dim, lemma_feat_dim, args.hidden).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=args.lr)

    train_target_t = torch.tensor(np.concatenate([
        train_emb,
        np.stack([build_features(p) for p in train])], axis=1),
        dtype=torch.float32, device=device)
    val_target_t = torch.tensor(np.concatenate([
        val_emb,
        np.stack([build_features(p) for p in val])], axis=1),
        dtype=torch.float32, device=device)
    test_target_t = torch.tensor(np.concatenate([
        test_emb,
        np.stack([build_features(p) for p in test])], axis=1),
        dtype=torch.float32, device=device)
    lemma_emb_t = torch.tensor(lemma_emb, dtype=torch.float32, device=device)

    print(f"\n[train {args.epochs} epochs]")
    for epoch in range(args.epochs):
        model.train()
        idxs = list(range(len(train))); random.seed(epoch); random.shuffle(idxs)
        ep_loss = 0.0; n_batches = 0
        for bs in range(0, len(idxs), args.batch_size):
            batch_idxs = idxs[bs:bs + args.batch_size]
            optim.zero_grad()
            batch_loss = 0.0
            for i in batch_idxs:
                p = train[i]
                t_emb = train_target_t[i]
                pos = [lemma_to_idx[l] for l in p["used_lemmas"]
                       if l in lemma_to_idx]
                neg = [lemma_to_idx[l] for l in p["negative_samples"]
                       if l in lemma_to_idx]
                if not pos or not neg: continue
                pos_emb = lemma_emb_t[pos]
                neg_emb = lemma_emb_t[neg]
                pos_scores = model.score(t_emb.expand(len(pos), -1), pos_emb)
                neg_scores = model.score(t_emb.expand(len(neg), -1), neg_emb)
                loss = (F.binary_cross_entropy_with_logits(
                    pos_scores, torch.ones_like(pos_scores))
                    + F.binary_cross_entropy_with_logits(
                    neg_scores, torch.zeros_like(neg_scores)))
                batch_loss = batch_loss + loss
            if isinstance(batch_loss, float): continue
            batch_loss = batch_loss / len(batch_idxs)
            batch_loss.backward(); optim.step()
            ep_loss += batch_loss.item(); n_batches += 1
        if epoch % 5 == 0 or epoch == args.epochs - 1:
            # Quick val eval
            with torch.no_grad():
                model.eval()
                val_metrics = eval_split(model, val, val_target_t, lemma_emb_t,
                                          lemma_to_idx)
            print(f"  epoch {epoch}: loss={ep_loss / max(n_batches, 1):.4f} "
                  f"val_hit@10={val_metrics['hit@10']:.3f} "
                  f"val_mrr={val_metrics['mrr']:.3f}")

    print("\n[final test eval]")
    with torch.no_grad():
        model.eval()
        test_metrics = eval_split(model, test, test_target_t, lemma_emb_t,
                                    lemma_to_idx)
    print(f"  test:")
    for k, v in test_metrics.items():
        print(f"    {k}: {v:.4f}")

    # Save
    torch.save({
        "model_state": model.state_dict(),
        "config": {
            "target_in": target_feat_dim, "lemma_in": lemma_feat_dim,
            "hidden": args.hidden,
        },
        "test_metrics": test_metrics,
        "lemma_vocab": lemma_vocab,
    }, args.out_checkpoint)
    print(f"\nsaved {args.out_checkpoint}")
    return 0


def eval_split(model, pairs, target_t, lemma_emb_t, lemma_to_idx):
    """Score every (target, every_lemma) pair, compute hit@K + MRR."""
    import torch
    n_lemmas = lemma_emb_t.shape[0]
    hits = {1: 0, 5: 0, 10: 0, 20: 0}
    mrr_sum = 0.0
    n_evaluated = 0
    for i, p in enumerate(pairs):
        positives = set(lemma_to_idx[l] for l in p["used_lemmas"]
                         if l in lemma_to_idx)
        if not positives: continue
        t_emb = target_t[i:i+1]
        # Score all lemmas
        scores = model.score(t_emb.expand(n_lemmas, -1), lemma_emb_t)
        sorted_idx = torch.argsort(scores, descending=True)
        ranks = []
        for pos in positives:
            rank = (sorted_idx == pos).nonzero()
            if len(rank) > 0:
                ranks.append(rank[0].item() + 1)
        if not ranks: continue
        # Use min rank (best-positioned positive)
        min_rank = min(ranks)
        for k in hits:
            if min_rank <= k: hits[k] += 1
        mrr_sum += 1.0 / min_rank
        n_evaluated += 1
    return {f"hit@{k}": hits[k] / max(n_evaluated, 1) for k in hits} | {
        "mrr": mrr_sum / max(n_evaluated, 1)
    }


if __name__ == "__main__":
    sys.exit(main())
