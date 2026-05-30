#!/usr/bin/env python3
"""Ranker production hit@10 falsifier.

Originally built for the v2 ranker. Kept compatible with that path, but
now also supports the v1 checkpoint so future ranker work can anchor on
the best known prior instead of the most recent prior.

Per `apparatus_level2_review.py::claim_v3_gnn_predicts_real`:

  > Take the last 20 verified-patch lemma references. For each, see if
  > the v2 ranker would have surfaced it in top-10. If hit-rate < 0.20
  > (vs claimed 0.27 test), there's a spine→production distribution
  > shift that invalidates the metric.

This script extracts (theorem_signature, used_lemmas) pairs from
recently-modified ZTARE Lean proofs (proofs Codex has shipped), runs a
selected ranker checkpoint against each, and computes production hit@k.

Why production, not test:
  test hit@10 = 0.271 was measured on held-out spine + mathlib pairs.
  Production hit@10 measures whether v2 would actually have helped
  Codex find the right lemma when typed_endpoint_pack is invoked on
  a real Lean target. The two distributions can diverge — that's the
  whole point of the falsifier.

Decision rule (from claim_v3_gnn_predicts_real):
  - production hit@10 ≥ 0.30: ship v2 as typed_endpoint_pack
    enrichment provider; defer v4
  - production hit@10 in 0.15-0.30: v4 architecture work is worth
    pursuing
  - production hit@10 < 0.15: data-shift dominates; bigger models
    won't help. Mine more diverse training pairs first

Usage:
    python scripts/public/models/v2_production_hit10_falsifier.py [--max-targets N] [--device mps]
    python scripts/public/models/v2_production_hit10_falsifier.py \
      --checkpoint analytics/public/leanmill/gnn_ranker/ranker_checkpoint.pt \
      --architecture v1 --out analytics/public/leanmill/results/v1_production_hit_at_k.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
DATA_DIR = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker"
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
DEFAULT_EMB_CACHE = DATA_DIR / "minilm_lemma_embeddings.npy"
DEFAULT_EMB_META = DATA_DIR / "minilm_lemma_embeddings.meta.json"


# Patterns for extracting tactic-level lemma references
TACTIC_LEMMA_PATTERNS = [
    # by exact <lemma> [args]
    re.compile(r"\bby\s+exact\s+(\w[\w.']*)"),
    re.compile(r"\bexact\s+(\w[\w.']*)"),
    # by apply <lemma>
    re.compile(r"\bby\s+apply\s+(\w[\w.']*)"),
    re.compile(r"\bapply\s+(\w[\w.']*)"),
    # by rw [foo, bar, baz]
    re.compile(r"\brw\s*\[\s*([^\]]+?)\s*\]"),
    # by simp [foo, bar]
    re.compile(r"\bsimp\s*(?:only|rw)?\s*\[\s*([^\]]+?)\s*\]"),
    # have h : ... := by exact <lemma>
    re.compile(r":=\s*by\s+(\w[\w.']*)"),
    re.compile(r":=\s+(\w[\w.']*)"),
]

# Theorem/lemma signature extraction
THM_SIGNATURE_RE = re.compile(
    r"^(?:theorem|lemma|def|noncomputable\s+def|noncomputable\s+lemma)"
    r"\s+(\w[\w.]*)\s*((?:[^:=]|::)*)\s*:\s*(.+?)(?=\s*:=|\s*\n)",
    re.MULTILINE | re.DOTALL,
)


def extract_used_lemmas(body: str) -> list[str]:
    """Extract names referenced in tactics (by exact / apply / rw / simp).

    Best-effort: handles the common cases. Doesn't try to be a Lean
    parser. Returns deduplicated list.

    2026-05-06 hardening (post v4-kill incident): added explicit
    filters for local hypotheses + field accesses. The unfiltered
    regex captured `hmissing`, `hmono.ge_of_tendsto`,
    `S.smoothCandidatePayoff`, etc. as "lemmas" — these are local
    proof terms. The contaminated falsifier signal led to a wrong
    kill decision on v4 GPU training. Don't repeat.
    """
    names: set[str] = set()
    for pat in TACTIC_LEMMA_PATTERNS:
        for match in pat.finditer(body):
            captured = match.group(1)
            if "," in captured:
                for piece in captured.split(","):
                    piece = piece.strip().split()[0] if piece.strip() else ""
                    if piece and not piece.startswith("-"):
                        names.add(piece)
            else:
                token = captured.strip().split()[0] if captured.strip() else ""
                if token:
                    names.add(token)

    NOISE = {
        "this", "by", "exact", "apply", "rw", "simp", "intro", "intros",
        "constructor", "split", "rfl", "trivial", "decide", "tauto",
        "ring", "ring_nf", "linarith", "nlinarith", "omega", "norm_num",
        "show", "obtain", "rcases", "cases", "use", "and", "or", "fun",
        "let", "match", "with", "have", "if", "then", "else",
    }

    def is_likely_local_hypothesis(name: str) -> bool:
        """Local-hypothesis convention: starts with 'h' followed by
        lowercase / underscore. Lean code commonly names hypotheses
        h1, hx, h_step, hmissing, hmono, hbridge, etc."""
        if len(name) < 2:
            return True
        if name[0] != "h":
            return False
        c = name[1]
        return c.islower() or c == "_" or c.isdigit()

    def is_likely_field_access(name: str) -> bool:
        """`X.foo` is a field/method on a local term unless `X` looks
        like a Module/Type prefix (capitalized + non-trivial). We
        keep the conservative side: drop dotted names whose prefix
        is short or starts lowercase (likely local terms)."""
        if "." not in name:
            return False
        prefix = name.split(".", 1)[0]
        if not prefix:
            return True
        # Local-named prefix (lowercase or 1-letter) → field access on local
        if prefix[0].islower():
            return True
        if len(prefix) == 1:
            return True
        return False

    out = []
    for n in sorted(names):
        if n.lower() in NOISE:
            continue
        if len(n) <= 1:
            continue
        if is_likely_local_hypothesis(n):
            continue
        if is_likely_field_access(n):
            continue
        out.append(n)
    return out


def extract_pairs_from_file(path: Path) -> list[dict]:
    """Extract (target_signature, used_lemmas) pairs from one Lean file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    pairs: list[dict] = []
    # Walk theorem/lemma declarations. Each one has a signature; for
    # the body we take from the `:= by` (or `:=`) up to the next
    # top-level declaration or end-of-file.
    decls = []
    for match in re.finditer(
        r"^(?:theorem|lemma|noncomputable\s+def|noncomputable\s+lemma|def)\s+(\w[\w.]*)\s*",
        text,
        re.MULTILINE,
    ):
        decls.append((match.start(), match.group(1)))

    for i, (start, name) in enumerate(decls):
        end = decls[i + 1][0] if i + 1 < len(decls) else len(text)
        block = text[start:end]
        # Signature: from `theorem name` to the first `:=`
        sig_match = re.search(r"^(?:theorem|lemma|noncomputable\s+def|noncomputable\s+lemma|def)\s+(\w[\w.]*)\s+(.*?):\s*(.+?)(?=\s*:=)", block, re.DOTALL)
        if not sig_match:
            continue
        signature = (sig_match.group(2) + " : " + sig_match.group(3)).strip()
        # Body: after the first `:=` to end of block
        body_pos = block.find(":=")
        body = block[body_pos:] if body_pos >= 0 else ""
        if not body:
            continue
        used = extract_used_lemmas(body)
        if not used:
            continue
        # Build target_features (matching v2 schema)
        features = {
            "n_chars": len(signature),
            "has_le": int("≤" in signature or "<=" in signature or " le " in signature),
            "has_lt": int("<" in signature),
            "has_eq": int("=" in signature),
            "has_norm": int("‖" in signature or "norm" in signature.lower()),
            "has_integral": int("∫" in signature or "integral" in signature.lower()),
            "has_forall": int("∀" in signature or "forall" in signature.lower()),
            "has_exists": int("∃" in signature or "exists" in signature.lower()),
            "n_binders": signature.count("("),
        }
        pairs.append({
            "source_file": path.name,
            "target_name": name,
            "target_start_line": text[:start].count("\n") + 1,
            "target_signature": signature[:500],
            "target_features": features,
            "used_lemmas": used,
        })
    return pairs


def build_features(p: dict):
    import numpy as np

    f = p["target_features"]
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


def load_or_encode_lemma_embeddings(st, lemma_vocab, lemma_sentences, cache_path, meta_path):
    import numpy as np

    expected = {
        "encoder": "sentence-transformers/all-MiniLM-L6-v2",
        "n_lemmas": len(lemma_vocab),
        "first_lemma": lemma_vocab[0] if lemma_vocab else None,
        "last_lemma": lemma_vocab[-1] if lemma_vocab else None,
    }
    if cache_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            if all(meta.get(k) == v for k, v in expected.items()):
                print(f"  loading cached lemma embeddings: {cache_path}")
                return np.load(cache_path)
        except Exception:
            pass
    print("  encoding lemma vocab once; writing cache for future runs...")
    emb = st.encode(
        lemma_sentences,
        batch_size=128,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, emb)
    meta_path.write_text(json.dumps(expected, indent=2))
    return emb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="mps", choices=["cpu", "mps", "cuda"])
    ap.add_argument(
        "--max-targets",
        type=int,
        default=200,
        help="cap on extracted (theorem, lemma) pairs (default: 200)",
    )
    ap.add_argument(
        "--checkpoint",
        type=Path,
        default=DATA_DIR / "ranker_checkpoint_v2.pt",
    )
    ap.add_argument(
        "--architecture",
        choices=["auto", "v1", "v2"],
        default="auto",
        help="ranker head architecture; auto infers from checkpoint state keys",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DATA_DIR / "v2_production_hit_at_k.json",
    )
    ap.add_argument(
        "--vocab-limit",
        type=int,
        default=0,
        help="debug/smoke only: score first N vocab entries plus positives",
    )
    ap.add_argument("--lemma-emb-cache", type=Path, default=DEFAULT_EMB_CACHE)
    ap.add_argument("--lemma-emb-meta", type=Path, default=DEFAULT_EMB_META)
    args = ap.parse_args()

    import numpy as np
    import torch
    import torch.nn as nn
    from sentence_transformers import SentenceTransformer

    print(f"=== ranker production hit@k falsifier ===")
    print(f"  checkpoint: {args.checkpoint}")
    device = torch.device(args.device)

    # Load checkpoint
    if not args.checkpoint.exists():
        print(f"  ERROR: checkpoint not found at {args.checkpoint}")
        return 1
    payload = torch.load(args.checkpoint, map_location=device, weights_only=False)
    cfg = payload["config"]
    state_keys = set(payload["model_state"].keys())
    architecture = args.architecture
    if architecture == "auto":
        architecture = "v2" if "target_proj.6.weight" in state_keys else "v1"
    print(
        f"  architecture: {architecture}"
    )
    print(
        f"  config: target_in={cfg['target_in']}, "
        f"lemma_in={cfg['lemma_in']}, hidden={cfg['hidden']}"
    )
    checkpoint_metrics = payload.get("test_metrics", payload.get("metrics", {}))
    print(f"  checkpoint test metrics: {checkpoint_metrics}")

    class RankerV1(nn.Module):
        def __init__(self, target_in, lemma_in, hidden):
            super().__init__()
            self.target_proj = nn.Sequential(
                nn.Linear(target_in, hidden),
                nn.ReLU(),
                nn.Dropout(0.0),
                nn.Linear(hidden, hidden),
            )
            self.lemma_proj = nn.Sequential(
                nn.Linear(lemma_in, hidden),
                nn.ReLU(),
                nn.Dropout(0.0),
                nn.Linear(hidden, hidden),
            )

        def score_batch(self, t_emb, l_emb_all):
            t = self.target_proj(t_emb)
            l = self.lemma_proj(l_emb_all)
            return t @ l.T

    class RankerV2(nn.Module):
        def __init__(self, target_in, lemma_in, hidden, dropout):
            super().__init__()
            self.target_proj = nn.Sequential(
                nn.Linear(target_in, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
            )
            self.lemma_proj = nn.Sequential(
                nn.Linear(lemma_in, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, hidden),
            )

        def score_batch(self, t_emb, l_emb_all):
            t = self.target_proj(t_emb)
            l = self.lemma_proj(l_emb_all)
            return t @ l.T

    if architecture == "v1":
        model = RankerV1(cfg["target_in"], cfg["lemma_in"], cfg["hidden"]).to(device)
    else:
        model = RankerV2(
            cfg["target_in"], cfg["lemma_in"], cfg["hidden"], cfg.get("dropout", 0.3)
        ).to(device)
    model.load_state_dict(payload["model_state"])
    model.eval()

    # Lemma vocab + mathlib index
    lemma_vocab = json.loads((DATA_DIR / "lemma_vocab.json").read_text())
    lemma_to_idx = {n: i for i, n in enumerate(lemma_vocab)}
    print(f"  lemma vocab size: {len(lemma_vocab)}")
    mathlib_idx = json.loads(
        (REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json").read_text()
    )

    # ---- Extract production pairs from recent ZTARE Lean files
    print(f"\n[extract pairs from {LEAN_DIR}/]")
    lean_files = sorted(LEAN_DIR.glob("*.lean"), key=lambda p: -p.stat().st_mtime)
    # Take the most recent 30 files (covers ~2 weeks of work)
    recent = lean_files[:30]
    print(f"  most recent {len(recent)} files; sample: {[f.name for f in recent[:3]]}")

    all_pairs = []
    for f in recent:
        all_pairs.extend(extract_pairs_from_file(f))
        if len(all_pairs) >= args.max_targets:
            break
    all_pairs = all_pairs[: args.max_targets]
    print(f"  extracted {len(all_pairs)} (theorem, used_lemmas) pairs")

    if not all_pairs:
        print("  ERROR: no pairs extracted; check Lean parsing")
        return 1

    # Filter to pairs whose used_lemmas intersect the v2 vocab
    in_vocab_pairs = []
    for p in all_pairs:
        in_vocab = [l for l in p["used_lemmas"] if l in lemma_to_idx]
        if in_vocab:
            p["used_lemmas_in_vocab"] = in_vocab
            in_vocab_pairs.append(p)
    print(
        f"  pairs with ≥1 used_lemma in vocab: {len(in_vocab_pairs)} "
        f"({len(in_vocab_pairs) / max(len(all_pairs), 1):.1%})"
    )

    if not in_vocab_pairs:
        print("  WARNING: no production pairs have used_lemmas in vocab.")
        print("  This is itself a finding: tactic lemmas in the spine are")
        print("  outside the trained vocab. Logging and exiting.")
        return 0
    eval_indices = list(range(len(lemma_vocab)))
    smoke_vocab_restricted = False
    if args.vocab_limit:
        smoke_vocab_restricted = True
        forced = {lemma_to_idx[l] for p in in_vocab_pairs for l in p["used_lemmas_in_vocab"]}
        eval_indices = sorted(set(range(min(args.vocab_limit, len(lemma_vocab)))) | forced)
        print(
            f"  SMOKE MODE: scoring restricted vocab {len(eval_indices)}/{len(lemma_vocab)} "
            f"(includes all positives)"
        )

    # ---- Encode targets + lemma vocab via the SAME sentence encoder v2 used
    print(f"\n[encode with all-MiniLM-L6-v2 (matches v1/v2 encoder)]")
    st = SentenceTransformer("all-MiniLM-L6-v2", device=str(device))

    target_sigs = [p["target_signature"] for p in in_vocab_pairs]
    target_emb = st.encode(target_sigs, batch_size=64, convert_to_numpy=True)
    print(f"  target emb shape: {target_emb.shape}")

    print("  encoding/loading lemma vocab...")
    lemma_sentences = []
    for name in lemma_vocab:
        if name in mathlib_idx["by_name"]:
            preview = mathlib_idx["by_name"][name].get("preview", name)
        else:
            preview = name
        lemma_sentences.append(f"{name}: {preview[:200]}")
    if smoke_vocab_restricted:
        lemma_emb = st.encode(
            [lemma_sentences[idx] for idx in eval_indices],
            batch_size=128,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    else:
        lemma_emb = load_or_encode_lemma_embeddings(
            st, lemma_vocab, lemma_sentences, args.lemma_emb_cache, args.lemma_emb_meta
        )
    print(f"  lemma emb shape: {lemma_emb.shape}")

    # Build target tensor with feature pack
    target_feat = np.stack([build_features(p) for p in in_vocab_pairs])
    target_t = torch.tensor(np.concatenate([target_emb, target_feat], axis=1), dtype=torch.float32, device=device)
    lemma_t = torch.tensor(lemma_emb, dtype=torch.float32, device=device)
    local_to_global = eval_indices if smoke_vocab_restricted else list(range(len(lemma_vocab)))

    # ---- Score and compute hit@k
    print(f"\n[score against vocab + compute hit@k]")
    rrs = []
    h1 = h5 = h10 = h20 = h50 = 0
    n = 0
    per_target_records = []
    with torch.no_grad():
        for i, p in enumerate(in_vocab_pairs):
            scores = model.score_batch(target_t[i].unsqueeze(0), lemma_t).squeeze(0)
            ranking_local = torch.argsort(scores, descending=True).tolist()
            ranking = [local_to_global[idx] for idx in ranking_local]
            pos_set = set(lemma_to_idx[l] for l in p["used_lemmas_in_vocab"])
            best_rank = None
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
            if best_rank <= 50:
                h50 += 1
            n += 1
            per_target_records.append({
                "source_file": p["source_file"],
                "target_name": p["target_name"],
                "used_lemmas_in_vocab": p["used_lemmas_in_vocab"],
                "best_rank": best_rank,
                "top10_lemmas": [lemma_vocab[idx] for idx in ranking[:10]],
            })

    if n == 0:
        print("  no scoring possible (no positive lemmas resolved); aborting")
        return 1

    metrics = {
        "n_targets_evaluated": n,
        "hit@1": h1 / n,
        "hit@5": h5 / n,
        "hit@10": h10 / n,
        "hit@20": h20 / n,
        "hit@50": h50 / n,
        "mrr": sum(rrs) / n,
    }

    print("\n=== production metrics (checkpoint vs Codex-shipped Lean targets) ===")
    for k, v in metrics.items():
        print(f"  {k}: {v if isinstance(v, int) else f'{v:.4f}'}")

    print("\n=== comparison ===")
    claimed_hit10 = checkpoint_metrics.get("hit@10")
    if claimed_hit10 is None and architecture == "v2":
        claimed_hit10 = 0.271
    print(f"  checkpoint spine-eval test hit@10: {claimed_hit10 if claimed_hit10 is not None else 'unknown'}")
    print(f"  production hit@10:              {metrics['hit@10']:.3f}")
    delta = None if claimed_hit10 is None else metrics['hit@10'] - claimed_hit10
    print(f"  delta:                     {delta:+.3f}")
    print()
    if metrics["hit@10"] >= 0.30:
        verdict = "SHIP_V2"
        print("  VERDICT: SHIP_V2 — production hit@10 ≥ 0.30; v4 architecture work is overkill")
    elif metrics["hit@10"] >= 0.15:
        verdict = "PURSUE_V4"
        print("  VERDICT: PURSUE_V4 — production hit@10 in [0.15, 0.30); architecture work worth attempting")
    else:
        verdict = "DATA_SHIFT_DOMINATES"
        print("  VERDICT: DATA_SHIFT_DOMINATES — production hit@10 < 0.15; bigger models won't help")
        print("           Mine more diverse training pairs first.")

    out_payload = {
        "evaluator_version": "ranker_production_hit10_falsifier_2026_05_11",
        "checkpoint": str(args.checkpoint),
        "architecture": architecture,
        "claimed_test_hit_at_10": claimed_hit10,
        "n_lean_files_scanned": len(recent),
        "n_pairs_extracted": len(all_pairs),
        "n_pairs_with_lemmas_in_vocab": len(in_vocab_pairs),
        "smoke_vocab_restricted": smoke_vocab_restricted,
        "vocab_scored": len(eval_indices),
        "production_metrics": metrics,
        "verdict": verdict,
        "per_target_records": per_target_records[:50],  # cap for readability
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_payload, indent=2))
    print(f"\n  saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
