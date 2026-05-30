#!/usr/bin/env python3
"""GNN lemma-relevance ranker v6 — InfoNCE loss + mixed negatives + warmup.

Why v6 exists: v4 + v5 both showed feature collapse (loss drops sharply,
val_hit@10 stays at 0). Diagnosis: BCE-loss + aggressive-hard-neg mining
collapses the projection space — model learns to make all embeddings
similar so BCE minimizes uniformly, ranking sees no signal.

v4 had encoder fine-tune; v5 had frozen encoder — both collapsed.
That isolates the cause to BCE+hard-neg, not encoder.

What v6 changes vs v5:

1. **InfoNCE / softmax-cross-entropy loss** instead of BCE:
   Proper contrastive loss. For each anchor target with positives
   {p_1..p_n} and negatives {n_1..n_k}, compute softmax over
   [s(t,p), s(t,n_1), ..., s(t,n_k)] and use cross-entropy.
   The softmax enforces RELATIVE separation, not absolute thresholds.
   No collapse pathway (the model can't satisfy softmax by making
   everything similar).

2. **Mixed hard + easy negatives** (1:2 ratio default):
   Current v4/v5 used 32-64 hard negatives per target — pure hard.
   v6 uses 8 hard + 16 random per target. Random negatives give
   gradient signal on "obvious wrong" cases; hard negatives sharpen
   the difficult boundary. The mix prevents the model from learning
   only the hard boundary while collapsing on easy.

3. **Hard-neg warm-up**: hard-neg mining doesn't fire until epoch 3
   (configurable via ``--hard-neg-warmup``). Lets the model learn
   easy/random structure first. Only when easy retrieval is non-
   degenerate does mining shift to harder examples.

4. **Smaller projection**: hidden=256 (was 512). Less capacity to
   collapse. Bigger projections in v4/v5 were a partial cause —
   2.4M head params overfitting on 880 ZTARE pairs is plausible.

5. **Mix mathlib + ZTARE pairs** (same as v5): augmented training
   distribution preserved.

6. **CLIP-style temperature** stays (logit_scale = 1/0.07 init), but
   now meaningful since InfoNCE uses it.

Honest expectation:
  v6 test hit@10: 0.30-0.42 (recover v2-class baseline + the
    learning gain from contrastive done right)
  v6 val_mrr: 0.15-0.22
  Production hit@10 on NS: probably 0.08-0.20 (still data-shift-
    limited, but real signal vs ~0)

If v6 collapses too: learned ranking on this distribution doesn't
pay. Stop spending. The remaining wins are deterministic
(GP-223 endpoint compression, mathlib reconnaissance prompt
injection).

Usage:
    python scripts/public/models/gnn_lemma_relevance_train_v6.py \\
        --device cuda --epochs 30 --patience 8 \\
        --hidden 256 --dropout 0.2 \\
        --hard-neg 8 --random-neg 16 --hard-neg-warmup 3 \\
        --mix-ztare
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA_DIR = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker"


def load_jsonl(path: Path):
    return [
        json.loads(line) for line in path.read_text().splitlines() if line.strip()
    ]


def build_features(p):
    f = p["target_features"]
    import numpy as np

    return np.array(
        [
            min(f["n_chars"] / 500.0, 1.0),
            float(f["has_le"]),
            float(f["has_lt"]),
            float(f["has_eq"]),
            float(f["has_norm"]),
            float(f["has_integral"]),
            float(f["has_forall"]),
            float(f["has_exists"]),
            min(f["n_binders"] / 20.0, 1.0),
        ],
        dtype="float32",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda", choices=["cpu", "cuda", "mps"])
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--hidden", type=int, default=256,
                    help="projection hidden dim (smaller than v5's 512)")
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--hard-neg", type=int, default=8,
                    help="hard negatives per target (mined per cycle)")
    ap.add_argument("--random-neg", type=int, default=16,
                    help="random negatives per target (drawn fresh each iter)")
    ap.add_argument("--hard-neg-warmup", type=int, default=3,
                    help="epochs of random-only training before hard-neg mining starts")
    ap.add_argument("--mine-every", type=int, default=5,
                    help="re-mine hard negatives every N epochs (after warmup)")
    ap.add_argument(
        "--encoder",
        default="sentence-transformers/all-mpnet-base-v2",
        help="sentence encoder model id (frozen)",
    )
    ap.add_argument("--mix-mathlib", action="store_true", default=True)
    ap.add_argument("--mix-ztare", action="store_true", default=False)
    ap.add_argument(
        "--out-checkpoint", type=Path, default=DATA_DIR / "ranker_checkpoint_v6.pt"
    )
    args = ap.parse_args()

    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from sentence_transformers import SentenceTransformer

    device = torch.device(args.device)
    use_bf16 = (
        device.type == "cuda" and torch.cuda.is_bf16_supported()
    )

    print(f"=== GNN lemma-relevance ranker v6 ===")
    print(f"  device: {device}  bfloat16: {use_bf16}")
    print(f"  encoder: {args.encoder} (FROZEN)")
    print(f"  hidden: {args.hidden}  dropout: {args.dropout}")
    print(f"  loss: InfoNCE (softmax cross-entropy)")
    print(
        f"  negatives: {args.hard_neg} hard + {args.random_neg} random per target"
    )
    print(
        f"  hard-neg warmup: {args.hard_neg_warmup} epochs random-only, "
        f"then re-mine every {args.mine_every}"
    )

    print("\n[load data]")
    train = load_jsonl(DATA_DIR / "train.jsonl")
    val = load_jsonl(DATA_DIR / "val.jsonl")
    test = load_jsonl(DATA_DIR / "test.jsonl")

    if args.mix_mathlib and (DATA_DIR / "mathlib_pairs.jsonl").exists():
        mathlib_pairs = load_jsonl(DATA_DIR / "mathlib_pairs.jsonl")
        print(f"  mathlib pairs available: {len(mathlib_pairs)}")
        random.seed(42)
        random.shuffle(mathlib_pairs)
        n_ml = len(mathlib_pairs)
        train.extend(mathlib_pairs[: int(n_ml * 0.8)])
        val.extend(mathlib_pairs[int(n_ml * 0.8) : int(n_ml * 0.9)])
        test.extend(mathlib_pairs[int(n_ml * 0.9) :])
        random.shuffle(train)
        random.shuffle(val)
        random.shuffle(test)

    if args.mix_ztare and (DATA_DIR / "ztare_pairs.jsonl").exists():
        ztare_pairs = load_jsonl(DATA_DIR / "ztare_pairs.jsonl")
        print(f"  ztare pairs available: {len(ztare_pairs)} (NS-internal)")
        random.seed(43)
        random.shuffle(ztare_pairs)
        n_zt = len(ztare_pairs)
        train.extend(ztare_pairs[: int(n_zt * 0.85)])
        val.extend(ztare_pairs[int(n_zt * 0.85) : int(n_zt * 0.92)])
        test.extend(ztare_pairs[int(n_zt * 0.92) :])
        random.shuffle(train)
        random.shuffle(val)
        random.shuffle(test)

    lemma_vocab = json.loads((DATA_DIR / "lemma_vocab.json").read_text())
    print(f"  train: {len(train)} val: {len(val)} test: {len(test)}")
    print(f"  lemma vocab: {len(lemma_vocab)}")
    lemma_to_idx = {n: i for i, n in enumerate(lemma_vocab)}

    print("\n[setup encoder — frozen mpnet]")
    st = SentenceTransformer(args.encoder, device=str(device))
    encoder_dim = st.get_sentence_embedding_dimension()
    print(f"  encoder embedding dim: {encoder_dim}")
    # Encoder fully frozen — v6 does NOT fine-tune
    for p in st._first_module().auto_model.parameters():
        p.requires_grad = False

    def chunked_encode(texts, label, chunk=4000):
        out_parts = []
        st.eval()
        for i in range(0, len(texts), chunk):
            with torch.no_grad():
                emb = st.encode(
                    texts[i : i + chunk],
                    batch_size=128,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
            out_parts.append(emb)
            print(
                f"  [{label}] encoded {min(i + chunk, len(texts))}/{len(texts)}",
                flush=True,
            )
        return np.concatenate(out_parts, axis=0)

    print("\n[encode]")
    train_sigs = [p["target_signature"] for p in train]
    val_sigs = [p["target_signature"] for p in val]
    test_sigs = [p["target_signature"] for p in test]
    train_emb = chunked_encode(train_sigs, "train")
    val_emb = chunked_encode(val_sigs, "val")
    test_emb = chunked_encode(test_sigs, "test")

    print("  encoding lemma vocab...")
    mathlib_idx = json.loads(
        (REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json").read_text()
    )
    lemma_sentences = []
    for name in lemma_vocab:
        if name in mathlib_idx["by_name"]:
            preview = mathlib_idx["by_name"][name].get("preview", name)
        else:
            preview = name
        lemma_sentences.append(f"{name}: {preview[:200]}")
    lemma_emb = chunked_encode(lemma_sentences, "lemmas")
    print(f"  lemma emb shape: {lemma_emb.shape}")

    target_feat_dim = encoder_dim + 9
    lemma_feat_dim = encoder_dim

    class RankerV6(nn.Module):
        """3-layer projection (smaller than v5's 4-layer/512), L2-norm,
        CLIP-style temperature."""

        def __init__(self, target_in, lemma_in, hidden, dropout):
            super().__init__()
            self.target_proj = nn.Sequential(
                nn.Linear(target_in, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
            )
            self.lemma_proj = nn.Sequential(
                nn.Linear(lemma_in, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
            )
            # CLIP-style temperature (init at log(1/0.07) ≈ 2.66)
            self.logit_scale = nn.Parameter(torch.tensor(2.6593))

        def encode_target(self, t_emb):
            return F.normalize(self.target_proj(t_emb), dim=-1)

        def encode_lemma(self, l_emb):
            return F.normalize(self.lemma_proj(l_emb), dim=-1)

        def score_pair(self, t_emb, l_emb):
            t = self.encode_target(t_emb)
            l = self.encode_lemma(l_emb)
            return self.logit_scale.exp() * (t * l).sum(dim=-1)

        def score_batch(self, t_emb, l_emb_all):
            t = self.encode_target(t_emb)
            l = self.encode_lemma(l_emb_all)
            return self.logit_scale.exp() * (t @ l.T)

    model = RankerV6(target_feat_dim, lemma_feat_dim, args.hidden, args.dropout).to(
        device
    )
    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n[model] RankerV6 head params: {n_params:,}")

    optim = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    total_steps = max(1, args.epochs * (len(train) // args.batch_size + 1))
    warmup_steps = int(total_steps * 0.1)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optim,
        lr_lambda=lambda step: (
            step / max(1, warmup_steps)
            if step < warmup_steps
            else 0.5
            * (
                1
                + math.cos(
                    math.pi
                    * (step - warmup_steps)
                    / max(1, total_steps - warmup_steps)
                )
            )
        ),
    )

    train_target_t = torch.tensor(
        np.concatenate(
            [train_emb, np.stack([build_features(p) for p in train])], axis=1
        ),
        dtype=torch.float32,
        device=device,
    )
    val_target_t = torch.tensor(
        np.concatenate([val_emb, np.stack([build_features(p) for p in val])], axis=1),
        dtype=torch.float32,
        device=device,
    )
    test_target_t = torch.tensor(
        np.concatenate(
            [test_emb, np.stack([build_features(p) for p in test])], axis=1
        ),
        dtype=torch.float32,
        device=device,
    )
    lemma_emb_t = torch.tensor(lemma_emb, dtype=torch.float32, device=device)

    train_pos_sets: list[set[int]] = []
    for p in train:
        s = set()
        for l in p.get("used_lemmas", []):
            if l in lemma_to_idx:
                s.add(lemma_to_idx[l])
        train_pos_sets.append(s)

    n_lemmas = len(lemma_vocab)
    rng = random.Random(0)

    def sample_random_negs(pos_set: set[int], k: int) -> list[int]:
        """Sample k random lemma indices not in pos_set."""
        if k <= 0 or n_lemmas <= len(pos_set):
            return []
        out = []
        attempts = 0
        while len(out) < k and attempts < k * 5:
            cand = rng.randrange(n_lemmas)
            attempts += 1
            if cand in pos_set or cand in out:
                continue
            out.append(cand)
        return out

    def mine_hard_negatives(K: int) -> list[list[int]]:
        model.eval()
        out: list[list[int]] = []
        with torch.no_grad():
            for i in range(len(train)):
                pos = train_pos_sets[i]
                if not pos:
                    out.append([])
                    continue
                scores = model.score_batch(
                    train_target_t[i].unsqueeze(0), lemma_emb_t
                ).squeeze(0)
                for pi in pos:
                    scores[pi] = float("-inf")
                topk = torch.topk(scores, k=min(K, len(scores))).indices.tolist()
                out.append(topk)
        model.train()
        return out

    print(
        f"\n[train up to {args.epochs} epochs, patience {args.patience}, "
        f"warmup {args.hard_neg_warmup} epochs random-only]"
    )
    best_val_mrr = 0.0
    best_epoch = 0
    epochs_since_best = 0
    best_state = None
    hard_negs: list[list[int]] = [[] for _ in range(len(train))]

    for epoch in range(args.epochs):
        # Hard-neg mining: skip during warmup; then re-mine every mine_every
        if epoch >= args.hard_neg_warmup and (
            epoch == args.hard_neg_warmup
            or (epoch - args.hard_neg_warmup) % args.mine_every == 0
        ):
            print(
                f"  [epoch {epoch}] mining {args.hard_neg} hard negs per target...",
                flush=True,
            )
            hard_negs = mine_hard_negatives(args.hard_neg)

        model.train()
        idxs = list(range(len(train)))
        random.seed(epoch)
        random.shuffle(idxs)
        ep_loss = 0.0
        n_batches = 0
        for bs in range(0, len(idxs), args.batch_size):
            batch_idxs = idxs[bs : bs + args.batch_size]
            optim.zero_grad()
            batch_loss = 0.0
            n_in_batch = 0
            for i in batch_idxs:
                pos = list(train_pos_sets[i])
                if not pos:
                    continue
                # First positive (loop later if multiple — for InfoNCE
                # we score pos vs negs as anchor)
                pos_idx = pos[0]
                # Mix: hard (after warmup) + random
                negs = list(hard_negs[i]) if hard_negs[i] else []
                if len(negs) > args.hard_neg:
                    negs = negs[: args.hard_neg]
                negs.extend(sample_random_negs(train_pos_sets[i], args.random_neg))
                if not negs:
                    continue

                # InfoNCE: score = [s(t,pos), s(t,neg_1), ..., s(t,neg_k)]
                # Cross-entropy with label=0 (positive is at index 0).
                t_emb = train_target_t[i]
                cand_indices = [pos_idx] + negs
                cand_emb = lemma_emb_t[cand_indices]  # (1+K, lemma_dim)
                scores = model.score_batch(t_emb.unsqueeze(0), cand_emb)  # (1, 1+K)
                target_idx = torch.zeros(1, dtype=torch.long, device=device)
                loss = F.cross_entropy(scores, target_idx)
                batch_loss = batch_loss + loss
                n_in_batch += 1

            if isinstance(batch_loss, float) or n_in_batch == 0:
                continue
            batch_loss = batch_loss / n_in_batch
            batch_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            scheduler.step()
            ep_loss += batch_loss.item()
            n_batches += 1

        with torch.no_grad():
            model.eval()
            val_metrics = eval_split(
                model, val, val_target_t, lemma_emb_t, lemma_to_idx, sample_size=300
            )
        val_mrr = val_metrics["mrr"]
        if val_mrr > best_val_mrr:
            best_val_mrr = val_mrr
            best_epoch = epoch
            epochs_since_best = 0
            best_state = {
                k: v.detach().clone() for k, v in model.state_dict().items()
            }
            star = "★"
        else:
            epochs_since_best += 1
            star = " "
        cur_lr = scheduler.get_last_lr()[0]
        phase = "warmup" if epoch < args.hard_neg_warmup else "hard+rand"
        print(
            f"  epoch {epoch:3d} ({phase:9s}): loss={ep_loss / max(n_batches, 1):.4f} "
            f"val_hit@10={val_metrics['hit@10']:.3f} val_mrr={val_metrics['mrr']:.3f} "
            f"lr={cur_lr:.2e} {star} "
            f"best={best_val_mrr:.3f}@{best_epoch} pat={epochs_since_best}/{args.patience}",
            flush=True,
        )

        if epochs_since_best >= args.patience:
            print(
                f"\n  early stopping at epoch {epoch}; "
                f"best val_mrr={best_val_mrr:.4f} at epoch {best_epoch}"
            )
            break

    if best_state:
        model.load_state_dict(best_state)
        print(f"\n  loaded best-val checkpoint (epoch {best_epoch})")

    print("\n[final test eval]")
    with torch.no_grad():
        model.eval()
        test_metrics = eval_split(
            model, test, test_target_t, lemma_emb_t, lemma_to_idx, sample_size=0
        )
    print(f"  test:")
    for k, v in test_metrics.items():
        print(f"    {k}: {v:.4f}")
    print(
        f"\n  comparison vs v2 (BCE baseline): "
        f"hit@10 0.271→{test_metrics['hit@10']:.3f}, "
        f"MRR 0.126→{test_metrics['mrr']:.3f}"
    )

    torch.save(
        {
            "model_state": model.state_dict(),
            "config": {
                "target_in": target_feat_dim,
                "lemma_in": lemma_feat_dim,
                "hidden": args.hidden,
                "dropout": args.dropout,
                "encoder": args.encoder,
                "loss": "InfoNCE",
                "hard_neg": args.hard_neg,
                "random_neg": args.random_neg,
                "hard_neg_warmup": args.hard_neg_warmup,
            },
            "metrics": test_metrics,
            "best_epoch": best_epoch,
            "best_val_mrr": best_val_mrr,
            "lemma_vocab": lemma_vocab,
        },
        args.out_checkpoint,
    )
    print(f"\nsaved {args.out_checkpoint}")


def eval_split(model, pairs, target_t, lemma_emb_t, lemma_to_idx, sample_size=0):
    import torch

    if sample_size > 0 and len(pairs) > sample_size:
        idxs = random.sample(range(len(pairs)), sample_size)
    else:
        idxs = list(range(len(pairs)))

    rrs = []
    h1 = h5 = h10 = h20 = 0
    n = 0
    with torch.no_grad():
        for i in idxs:
            p = pairs[i]
            pos = [lemma_to_idx[l] for l in p.get("used_lemmas", []) if l in lemma_to_idx]
            if not pos:
                continue
            scores = model.score_batch(target_t[i].unsqueeze(0), lemma_emb_t).squeeze(
                0
            )
            ranking = torch.argsort(scores, descending=True).tolist()
            best_rank = None
            pos_set = set(pos)
            for rk, idx in enumerate(ranking, start=1):
                if idx in pos_set:
                    best_rank = rk
                    break
            if best_rank is None:
                continue
            rrs.append(1.0 / best_rank)
            if best_rank <= 1:
                h1 += 1
            if best_rank <= 5:
                h5 += 1
            if best_rank <= 10:
                h10 += 1
            if best_rank <= 20:
                h20 += 1
            n += 1
    if n == 0:
        return {"hit@1": 0.0, "hit@5": 0.0, "hit@10": 0.0, "hit@20": 0.0, "mrr": 0.0}
    return {
        "hit@1": h1 / n,
        "hit@5": h5 / n,
        "hit@10": h10 / n,
        "hit@20": h20 / n,
        "mrr": sum(rrs) / n,
    }


if __name__ == "__main__":
    main()
