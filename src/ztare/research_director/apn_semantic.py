"""APN (AlphaProof Nexus) semantic neighbour primitive — RD kernel.

Sibling to `mathlib_semantic.py`. The APN atlas (~2568 declarations from
google-deepmind/alphaproof-nexus-results) carries Lean proofs across
optimization (monotone-operator convergence, Ryu-Yuan-Yin), additive
combinatorics, Erdos problems, and OEIS conjectures.

For NS work specifically, the most directly applicable corpus is
AICollaborator/Optimization/LastIterateConvergence.lean — monotone-operator
iterate bounds, contraction-factor algebra, bounded-iterate / bounded-
differences lemmas — which map cleanly to NS Leray-Hopf sequence analysis.

Use as additive cross-corpus signal: when the shape-tagged Mathlib shelf
AND the Mathlib semantic fallback both return weak hits, APN may surface a
relevant declaration the operator wouldn't otherwise see. Filter by domain
to restrict to NS-relevant slices (optimization, additive_combinatorics).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DEFAULT_APN_ATLAS = REPO / "analytics" / "public" / "queries" / "lean" / "apn_atlas_embeddings.json"
# Corpus path is env-overridable so a LEAK-TIGHT benchmark can point at a
# quarantined corpus (one with the target's own proof-helper DAG removed)
# WITHOUT mutating the shipped general-purpose shelf. The retrieval join is
# corpus-driven (rows iterate the corpus, embeddings joined by id), so swapping
# the corpus alone fully quarantines — no embedding rebuild needed. See
# docs/concepts/leanmill_architecture.md §"Solver Lane Subsystem · premise-shelf
# leakage". Default = the canonical shipped corpus.
DEFAULT_APN_CORPUS = Path(
    os.environ.get("ZTARE_LEANMILL_APN_CORPUS")
    or (REPO / "analytics" / "public" / "queries" / "lean" / "apn_atlas_corpus.json")
)
APN_THRESHOLD_DEFAULT = 0.55
APN_TOP_K_DEFAULT = 5
# NS-relevant default domain filter (optimization carries monotone-operator
# convergence; additive_combinatorics carries Bohr/Diophantine machinery)
APN_NS_DOMAIN_FILTER = ("optimization", "additive_combinatorics", "graphs")


@dataclass(frozen=True)
class APNSemanticHit:
    id: str
    name: str
    kind: str
    domain: str
    file: str
    variant_tag: str | None
    cosine: float
    snippet: str


_APN_CACHE: dict[str, tuple[list[dict], list[list[float]]]] = {}


def _load_apn_atlas(atlas_path: Path, corpus_path: Path) -> tuple[list[dict], list[list[float]]]:
    """Load + cache atlas embeddings paired with corpus entries by `id`."""
    key = str(atlas_path.resolve())
    cached = _APN_CACHE.get(key)
    if cached is not None:
        return cached
    if not atlas_path.exists() or not corpus_path.exists():
        _APN_CACHE[key] = ([], [])
        return [], []
    atlas_payload = json.loads(atlas_path.read_text(encoding="utf-8"))
    corpus_payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    atlas_items = atlas_payload.get("embeddings", []) if isinstance(atlas_payload, dict) else atlas_payload
    embeddings_by_id: dict[str, list[float]] = {}
    for item in atlas_items:
        if isinstance(item, dict) and "id" in item and "embedding" in item:
            embeddings_by_id[str(item["id"])] = item["embedding"]
    corpus_entries = corpus_payload.get("entries", []) if isinstance(corpus_payload, dict) else corpus_payload
    aligned_rows: list[dict] = []
    aligned_vecs: list[list[float]] = []
    for entry in corpus_entries:
        if not isinstance(entry, dict):
            continue
        eid = entry.get("id")
        if eid is None:
            continue
        vec = embeddings_by_id.get(str(eid))
        if vec is None:
            continue
        aligned_rows.append(entry)
        aligned_vecs.append(vec)
    _APN_CACHE[key] = (aligned_rows, aligned_vecs)
    return aligned_rows, aligned_vecs


def _embed_query_genai(query: str) -> list[float] | None:
    # Migrated to the canonical embedding engine (ztare.common.embeddings). The
    # embedding space is preserved EXACTLY: model gemini-embedding-001, 384 dims,
    # task_type RETRIEVAL_QUERY (asymmetric query side; atlas docs are
    # RETRIEVAL_DOCUMENT) — so existing apn_atlas_embeddings.json + cosine stay
    # compatible. Graceful-None contract kept: make_client raises SystemExit (not
    # caught by `except Exception`), so check the key BEFORE calling it.
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from ztare.common.embeddings import embed_batch, make_client
        return embed_batch(
            make_client(api_key),
            [query],
            model="gemini-embedding-001",
            dimensions=384,
            task_type="RETRIEVAL_QUERY",
        )[0]
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0; na = 0.0; nb = 0.0
    for x, y in zip(a, b):
        dot += x * y; na += x * x; nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / ((na**0.5) * (nb**0.5))


def apn_semantic_neighbours(
    query: str,
    *,
    atlas_path: Path = DEFAULT_APN_ATLAS,
    corpus_path: Path = DEFAULT_APN_CORPUS,
    top_k: int = APN_TOP_K_DEFAULT,
    threshold: float = APN_THRESHOLD_DEFAULT,
    domain_filter: tuple[str, ...] | None = APN_NS_DOMAIN_FILTER,
    embedder=None,
) -> tuple[list[APNSemanticHit], int, int, str | None]:
    """Return APN atlas neighbours for ``query``.

    Returns ``(hits, corpus_size, filtered_size, skip_reason)`` mirroring
    ``mathlib_semantic.mathlib_semantic_neighbours``. ``domain_filter`` defaults
    to NS-relevant slices (optimization, additive_combinatorics, graphs) —
    pass None to query the full atlas.
    """
    if not atlas_path.exists():
        return [], 0, 0, f"apn atlas missing: {atlas_path}"
    rows, vecs = _load_apn_atlas(atlas_path, corpus_path)
    if not rows:
        return [], 0, 0, "apn atlas empty after alignment"

    embed_fn = embedder or _embed_query_genai
    qvec = embed_fn(query)
    if qvec is None:
        return [], len(rows), 0, "query embedding unavailable (no GOOGLE_API_KEY or google.genai)"

    filter_set = {d.lower() for d in domain_filter} if domain_filter else None
    if filter_set is not None:
        indices = [i for i, r in enumerate(rows) if str(r.get("domain", "")).lower() in filter_set]
    else:
        indices = list(range(len(rows)))
    if not indices:
        return [], len(rows), 0, "no apn entries match domain filter"

    scored = [(_cosine(qvec, vecs[i]), i) for i in indices]
    scored.sort(reverse=True, key=lambda t: t[0])
    hits: list[APNSemanticHit] = []
    for cosine, i in scored[:top_k]:
        if cosine < threshold:
            break
        row = rows[i]
        hits.append(APNSemanticHit(
            id=str(row.get("id", "")),
            name=str(row.get("name", "?")),
            kind=str(row.get("kind", "")),
            domain=str(row.get("domain", "")),
            file=str(row.get("file", "")),
            variant_tag=row.get("variant_tag"),
            cosine=round(float(cosine), 4),
            snippet=str(row.get("snippet", ""))[:300],
        ))
    return hits, len(rows), len(indices), None


def render_text(hits: list[APNSemanticHit], *, header: str = "APN semantic neighbours") -> str:
    if not hits:
        return f"  {header}: none above threshold"
    lines = [f"  {header}:"]
    for hit in hits:
        vt = f" [variant={hit.variant_tag}]" if hit.variant_tag else ""
        lines.append(f"    - cos={hit.cosine:.4f}  {hit.kind} {hit.name}  ({hit.domain}/{hit.file}{vt})")
    return "\n".join(lines)
