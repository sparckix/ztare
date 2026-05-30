#!/usr/bin/env python3
"""Mine (theorem, used_lemmas) pairs from mathlib4 itself.

Standard data scaling: 945 spine theorems → ~45k mathlib theorems.
~50x more training data for the relevance ranker.

Reuses the same iter_theorems regex pattern from gnn_lemma_relevance_data_prep.

Output:
  analytics/public/leanmill/gnn_ranker/mathlib_pairs.jsonl
    one record per mathlib theorem: {target_signature, used_lemmas, ...}

Usage:
    python scripts/public/lean/mine_mathlib_pairs.py
    python scripts/public/lean/mine_mathlib_pairs.py --limit-files 1000  # quick test
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

MATHLIB_ROOT = REPO / "ztare_proofs" / ".lake" / "packages" / "mathlib" / "Mathlib"
DEFAULT_INCLUDE_PATHS = ["Analysis", "MeasureTheory", "Topology",
                          "LinearAlgebra/Matrix", "NumberTheory",
                          "Combinatorics", "Algebra/Order", "Order"]
OUT_DIR = REPO / "analytics" / "public" / "leanmill" / "gnn_ranker"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-paths", nargs="*", default=DEFAULT_INCLUDE_PATHS)
    ap.add_argument("--limit-files", type=int, default=0)
    ap.add_argument("--n-negatives", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "mathlib_pairs.jsonl")
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    # Load lemma vocab to filter "used_lemmas"
    print("=== loading vocabularies ===")
    mathlib_idx_path = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json"
    if not mathlib_idx_path.exists():
        print(f"missing {mathlib_idx_path}; run mathlib_lemma_scout.py --build first")
        return 1
    mathlib_idx = json.loads(mathlib_idx_path.read_text())
    mathlib_lemmas = set(mathlib_idx["by_name"].keys())
    print(f"  mathlib lemma vocab: {len(mathlib_lemmas)}")

    # Reuse extraction from gnn_lemma_relevance_data_prep
    from gnn_lemma_relevance_data_prep import (
        iter_theorems, extract_used_lemmas, extract_target_features,
    )

    print(f"\n=== walking mathlib for (target, used_lemmas) pairs ===")
    files = []
    for sub in args.include_paths:
        sub_path = MATHLIB_ROOT / sub
        if sub_path.is_dir():
            files.extend(sub_path.rglob("*.lean"))
    if args.limit_files:
        files = files[:args.limit_files]
    print(f"  scanning {len(files)} files")

    pairs = []
    for i, path in enumerate(files):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for kind, name, sig, body in iter_theorems(text):
            used = extract_used_lemmas(body, mathlib_lemmas)
            if not used:
                continue
            pairs.append({
                "target_name": name,
                "target_kind": kind,
                "target_file": str(path.relative_to(MATHLIB_ROOT)),
                "target_signature": sig[:300],
                "target_features": extract_target_features(sig),
                "used_lemmas": used[:30],
            })
        if (i + 1) % 500 == 0:
            print(f"  [{i + 1}/{len(files)}] {len(pairs)} pairs so far")

    print(f"\n  extracted {len(pairs)} mathlib (target, used_lemmas) pairs")
    n_total = sum(len(p["used_lemmas"]) for p in pairs)
    print(f"  total positive supervision: {n_total}")

    # Sample negatives
    print(f"\n=== sampling negatives ===")
    random.seed(args.seed)
    vocab_list = sorted(mathlib_lemmas)
    for p in pairs:
        positives = set(p["used_lemmas"])
        neg = []
        attempts = 0
        while len(neg) < args.n_negatives and attempts < args.n_negatives * 4:
            cand = random.choice(vocab_list)
            if cand not in positives:
                neg.append(cand)
            attempts += 1
        p["negative_samples"] = neg

    print(f"  added {args.n_negatives} negatives per positive")

    # Write
    with args.out.open("w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")
    print(f"\nwrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
