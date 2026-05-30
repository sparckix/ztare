#!/usr/bin/env python3
"""GNN lemma-relevance data prep — Graph2Tac-style training pairs.

Extracts (target_theorem, used_lemmas) pairs from the NS Track B spine
and Mathlib4 dependency graph. Each pair is positive supervision for a
relevance ranker that predicts: "which lemmas should be in the prompt
for this target?"

# Why this is the right training data

For each existing closed theorem T in the spine, the set of lemmas
referenced in T's proof body is the positive relevance signal. T's
type signature is the input; the used-lemma set is the supervision.
This gives THOUSANDS of training pairs without any GPT/Gemini
involvement — pure proof-spine mining.

# Data scale

  - Spine: ~1850 decls in ztare_proofs/ZtareProofs/ → ~1500 closed theorems
  - Mathlib: ~69k decls in indexed subset
  - Per-theorem average: 5-30 referenced lemmas
  - Training pairs: spine_theorems × avg_lemmas ≈ 30k-50k positive pairs
  - Plus negative samples drawn from the lemma corpus

# Output

  analytics/public/leanmill/gnn_ranker/training_pairs.jsonl  — jsonl of
    {target_signature, positive_lemmas, negative_samples, target_features}
  analytics/public/leanmill/gnn_ranker/lemma_vocab.json — global lemma dict
  analytics/public/leanmill/gnn_ranker/target_vocab.json — global target dict

# Reuse

  - `lean_decl_index.py` (spine declarations)
  - `mathlib_lemma_scout.py` (mathlib lemma index)

Usage:
    python scripts/public/models/gnn_lemma_relevance_data_prep.py
    python scripts/public/models/gnn_lemma_relevance_data_prep.py --max-targets 100  # quick test
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LEAN_DIR = REPO / "ztare_proofs" / "ZtareProofs"
MATHLIB_INDEX = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json"
SPINE_INDEX = REPO / "analytics" / "public" / "queries" / "lean" / "lean_decl_index.json"
OUT_DIR = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker"


DECL_HEADER_RE = re.compile(
    r"^(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
NEXT_DECL_RE = re.compile(
    r"^(theorem|lemma|def|structure|class|instance|abbrev|inductive|namespace|end)\s+",
    re.MULTILINE,
)


def iter_theorems(text):
    """Yield (kind, name, sig, body) tuples from Lean source.

    Robust to multi-line signatures with `:` in type binders (where DECL_RE
    style 'capture up to :=' fails). Matches just the header, then takes a
    window of text up to the next top-level declaration.
    """
    headers = list(DECL_HEADER_RE.finditer(text))
    headers.append(None)  # sentinel
    for i in range(len(headers) - 1):
        m = headers[i]
        kind = m.group(1)
        name = m.group(2)
        start = m.end()
        # Find next top-level decl after start
        next_m = NEXT_DECL_RE.search(text, pos=start)
        end = next_m.start() if next_m else len(text)
        chunk = text[start:end]
        # Split sig vs body at first := if present
        if ":=" in chunk:
            split_at = chunk.find(":=")
            sig = chunk[:split_at].strip()
            body = chunk[split_at + 2:].strip()
        else:
            sig = chunk[:300].strip()
            body = ""
        yield kind, name, sig, body
IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\b")
SAFE_IDENTS = {
    "theorem", "lemma", "def", "structure", "class", "instance",
    "by", "exact", "apply", "intro", "refine", "have", "show",
    "from", "rfl", "simp", "ring", "linarith", "omega", "decide",
    "use", "constructor", "cases", "rcases", "match", "with",
    "fun", "let", "in", "if", "then", "else", "do", "where",
    "this", "and", "or", "not", "True", "False", "Eq", "Iff",
    "Nat", "Int", "Real", "Rat", "Type", "Sort", "Prop",
    "ℝ", "ℕ", "ℤ", "ℚ",
}


def extract_used_lemmas(proof_body: str, valid_lemma_names: set[str]) -> list[str]:
    """Find lemma references in a proof body (heuristic: matches name DB)."""
    used = []
    for m in IDENT_RE.finditer(proof_body):
        ident = m.group(1)
        # tail of dotted name often is the lemma
        tail = ident.split(".")[-1]
        head = ident.split(".")[0]
        if ident in valid_lemma_names:
            used.append(ident)
        elif tail in valid_lemma_names and head not in SAFE_IDENTS:
            used.append(tail)
    # Dedupe preserving order
    seen = set()
    out = []
    for u in used:
        if u not in seen and u not in SAFE_IDENTS and len(u) >= 3:
            seen.add(u); out.append(u)
    return out


def extract_target_features(signature: str) -> dict:
    """Cheap hand-features for the target theorem signature."""
    return {
        "n_chars": len(signature),
        "has_le": "≤" in signature,
        "has_lt": "<" in signature,
        "has_eq": "=" in signature,
        "has_norm": "‖" in signature or "norm" in signature,
        "has_integral": "∫" in signature or "integral" in signature,
        "has_forall": "∀" in signature,
        "has_exists": "∃" in signature,
        "n_binders": signature.count("("),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-targets", type=int, default=0,
                    help="cap number of target theorems (debug)")
    ap.add_argument("--n-negatives", type=int, default=20,
                    help="negative samples per positive")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=== loading lemma vocabulary ===")
    if not MATHLIB_INDEX.exists():
        print(f"  missing {MATHLIB_INDEX}")
        return 1
    if not SPINE_INDEX.exists():
        print(f"  missing {SPINE_INDEX}")
        return 1
    mathlib_idx = json.loads(MATHLIB_INDEX.read_text())
    spine_idx = json.loads(SPINE_INDEX.read_text())
    mathlib_lemmas = set(mathlib_idx["by_name"].keys())
    spine_decls = set(spine_idx["decls"].keys())
    valid_lemmas = mathlib_lemmas | spine_decls
    print(f"  mathlib lemmas: {len(mathlib_lemmas)}")
    print(f"  spine decls:    {len(spine_decls)}")
    print(f"  combined vocab: {len(valid_lemmas)}")

    print("\n=== walking spine for (target, used_lemmas) pairs ===")
    targets_seen = 0
    pairs = []
    for path in sorted(LEAN_DIR.glob("ns_*.lean")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for kind, name, sig, body in iter_theorems(text):
            used = extract_used_lemmas(body, valid_lemmas)
            if not used:
                continue
            features = extract_target_features(sig)
            pairs.append({
                "target_name": name,
                "target_kind": kind,
                "target_file": path.stem,
                "target_signature": sig[:300],
                "target_features": features,
                "used_lemmas": used[:30],  # cap
            })
            targets_seen += 1
            if args.max_targets and targets_seen >= args.max_targets:
                break
        if args.max_targets and targets_seen >= args.max_targets:
            break

    print(f"  extracted {len(pairs)} (target, used_lemmas) pairs")
    n_total_lemmas = sum(len(p["used_lemmas"]) for p in pairs)
    print(f"  total positive supervision: {n_total_lemmas} target-lemma pairs")
    print(f"  avg lemmas per target: {n_total_lemmas / max(len(pairs), 1):.1f}")

    print("\n=== sampling negatives ===")
    random.seed(args.seed)
    valid_lemmas_list = sorted(valid_lemmas)
    for p in pairs:
        positives = set(p["used_lemmas"])
        # Sample negatives — random lemmas NOT used by this target
        neg_candidates = []
        attempts = 0
        while len(neg_candidates) < args.n_negatives and attempts < args.n_negatives * 4:
            cand = random.choice(valid_lemmas_list)
            if cand not in positives:
                neg_candidates.append(cand)
            attempts += 1
        p["negative_samples"] = neg_candidates

    print(f"  added {args.n_negatives} negatives per positive")

    print("\n=== train/val/test split (80/10/10 by target) ===")
    random.seed(args.seed)
    random.shuffle(pairs)
    n = len(pairs)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    splits = {
        "train": pairs[:train_end],
        "val": pairs[train_end:val_end],
        "test": pairs[val_end:],
    }
    for split_name, split_pairs in splits.items():
        path = args.out_dir / f"{split_name}.jsonl"
        with path.open("w") as f:
            for p in split_pairs:
                f.write(json.dumps(p) + "\n")
        print(f"  {split_name}.jsonl: {len(split_pairs)} pairs → {path}")

    # Vocabularies
    target_vocab = sorted(set(p["target_name"] for p in pairs))
    lemma_vocab = sorted(valid_lemmas)
    (args.out_dir / "target_vocab.json").write_text(
        json.dumps(target_vocab, indent=1))
    (args.out_dir / "lemma_vocab.json").write_text(
        json.dumps(lemma_vocab, indent=1))
    print(f"  target_vocab: {len(target_vocab)} → target_vocab.json")
    print(f"  lemma_vocab:  {len(lemma_vocab)} → lemma_vocab.json")

    print(f"\n=== done ===")
    print(f"  ready for GPU training: scripts/public/models/gnn_lemma_relevance_train.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
