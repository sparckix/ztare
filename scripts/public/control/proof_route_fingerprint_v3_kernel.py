#!/usr/bin/env python3
"""proof_route_fingerprint_v3_kernel.py — v3 with kernel features from v28B artifacts.

Reuses prior v22-v30 infrastructure (anti-`scientific_amnesia`):
- analytics/public/leanmill/results/v28B_dep_graph_artifacts/node2vec_embeddings.npy
- analytics/public/leanmill/results/v28B_dep_graph_artifacts/node_index.pkl
- analytics/public/index/mathlib_graph/mathlib_graph.json (already indexed in v28B)

Adds a 7th distance axis: kernel_embedding_distance.

For each proof's cited_constants list, look up node2vec embeddings (when names
match), compute the centroid embedding, then take cosine distance between
the two proofs' centroids. This adds kernel-level structural information that
surface+signature can't see.
"""
from __future__ import annotations
import argparse, json, pickle, sys
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
V28B_ROOT = ROOT / "analytics/public/leanmill/results/v28B_dep_graph_artifacts"


_emb_cache = None
_name_to_idx = None


def _load_kernel_artifacts():
    global _emb_cache, _name_to_idx
    if _emb_cache is None:
        _emb_cache = np.load(V28B_ROOT / "node2vec_embeddings.npy")
        idx_pkl = pickle.load(open(V28B_ROOT / "node_index.pkl", "rb"))
        _name_to_idx = idx_pkl["name_to_idx"]
    return _emb_cache, _name_to_idx


def cited_constants_centroid(cited: list[str]) -> np.ndarray | None:
    """Return the centroid of embeddings for cited constants, or None if no matches."""
    emb, name_to_idx = _load_kernel_artifacts()
    vectors = []
    for c in cited:
        # Try exact match first
        idx = name_to_idx.get(c)
        if idx is None:
            # Try splitting on dots — sometimes citations like `Real.foo` need both forms
            parts = c.split(".")
            for p in [c, parts[-1] if parts else c]:
                if p in name_to_idx:
                    idx = name_to_idx[p]
                    break
        if idx is not None:
            vectors.append(emb[idx])
    if not vectors:
        return None
    return np.mean(vectors, axis=0)


def kernel_embedding_distance(cited_a: list[str], cited_b: list[str]) -> float:
    """Cosine distance between centroids of cited-constant embeddings.

    Returns:
      - 0.0 if both centroids identical
      - 1.0 if orthogonal
      - 0.5 if either side has no matches (penalize unknown)
    """
    ca = cited_constants_centroid(cited_a)
    cb = cited_constants_centroid(cited_b)
    if ca is None or cb is None:
        return 0.5
    na = np.linalg.norm(ca)
    nb = np.linalg.norm(cb)
    if na < 1e-9 or nb < 1e-9:
        return 0.5
    cos_sim = float(np.dot(ca, cb) / (na * nb))
    cos_sim = max(-1.0, min(1.0, cos_sim))
    return (1.0 - cos_sim) / 2.0  # rescale [-1, 1] → [1, 0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-coverage", action="store_true",
                    help="Report how many TRAIN/TEST cited_constants match name_to_idx")
    args = ap.parse_args()

    if args.test_coverage:
        emb, name_to_idx = _load_kernel_artifacts()
        print(f"Loaded node2vec embeddings: shape={emb.shape}")
        print(f"name_to_idx size: {len(name_to_idx)}")

        # Coverage on v3 TRAIN
        train = json.load(open("/tmp/gp235_train_v3_alpha_rename_60pairs.json"))
        train_pairs = train if isinstance(train, list) else train.get("pairs", [])
        n_cited = 0
        n_found = 0
        for p in train_pairs:
            for side in ("left", "right"):
                # We need the cited_constants — extract via proof_route_fingerprint
                pb = p.get(side, {}).get("proof_body", "")
                # Simple regex for capitalized identifiers
                import re
                cands = set(re.findall(r"\b([A-Z][\w'.]*)\b", pb))
                for c in cands:
                    n_cited += 1
                    if c in name_to_idx:
                        n_found += 1
                    elif "." in c and c.rsplit(".", 1)[-1] in name_to_idx:
                        n_found += 1
        coverage = n_found / max(n_cited, 1)
        print(f"\nTRAIN v3 cited-constant coverage: {n_found}/{n_cited} = {100*coverage:.1f}%")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
