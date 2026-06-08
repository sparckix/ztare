"""Semantic retrieval over the seam/spec atlas — find the seam/spec that OWNS a capability.

A thin consumer of `ztare.common.embeddings.query_atlas` over the seam atlas built by
`scripts/public/mining/build_seam_atlas_embeddings.py`. This is the embedding complement to
the structural `seam_interaction_map.md` + knowledge graph, and the mechanized §6n.13 check:
before building a capability, ask which seam/spec already owns it.

    python -m ztare.research_director.seam_semantic "produce a defect-budget certificate"
    from ztare.research_director.seam_semantic import find_owning_seams
    hits = find_owning_seams("anti-laundering governance for a closed proof", k=8)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())
ATLAS = REPO / "analytics/public/index/seam_atlas_embeddings.json"


def find_owning_seams(capability: str, k: int = 8) -> list:
    """Top-k seams/specs most semantically similar to `capability` → [{score, path, gp_id, title, kind}]."""
    if not ATLAS.exists():
        raise SystemExit(f"seam atlas absent — build it: python scripts/public/mining/"
                         f"build_seam_atlas_embeddings.py ({ATLAS})")
    from ztare.common.embeddings import query_atlas
    return query_atlas(ATLAS, capability, k=k)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    q = " ".join(sys.argv[1:])
    print(f"=== seams/specs owning: {q!r} ===")
    for h in find_owning_seams(q):
        print(f"  {h['score']:.3f}  [{h.get('kind','?')}] {h.get('gp_id') or ''} {h.get('title','')[:60]}")
        print(f"          {h.get('path','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
