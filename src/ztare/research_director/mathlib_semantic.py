"""Mathlib semantic neighbour primitive (RD kernel).

Additive fallback for when the shape-tagged Mathlib index cannot retrieve a
relevant lemma — 61% of Mathlib entries carry no shape tags at all
(``mathlib_lemma_index.json``), so any gap-typed shelf lookup that returns
empty silently drops that 61% before any agent sees it.

This primitive is general-purpose: it is not NS-specific and does not depend on
the obstruction atlas. Callers pass a free-text query (typed goal, hypothesis
statement, eigenquestion); the function returns vocabulary-invariant Mathlib
neighbours above a cosine threshold. Use it ONLY as a fallback — the
shape-tagged shelf in ``gap_typed_prompter.fetch_gap_specific_lemmas`` is the
authoritative retrieval surface because its 0-hit signal carries information
("the gap has no canonical Mathlib shelf") that embeddings erase.

The atlas is built once by
``scripts/public/lean/build_mathlib_atlas_embeddings.py`` against
``analytics/public/queries/lean/mathlib_lemma_index.json``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DEFAULT_MATHLIB_ATLAS = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_atlas_embeddings.json"
DEFAULT_MATHLIB_INDEX = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json"
DEFAULT_ATLAS_ADJACENCY = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_atlas_adjacency.json"
MATHLIB_THRESHOLD_DEFAULT = 0.55
MATHLIB_TOP_K_DEFAULT = 8
# Graph-expansion re-rank (2026-06-30) — MEASURED lift on inductive Mathlib premise selection (n=1500, no
# target-edge leakage): recall@10 0.225→0.266, @20 0.270→0.360, @50 0.330→0.491, MRR flat. Best config from the
# A/B sweep (plain co-occurrence count beat Adamic-Adar rarity-weighting, which REGRESSED). ZTARE_LEANMILL_
# GRAPH_EXPAND=0 reverts to pure cosine.
GRAPH_EXPAND_SEEDS = 25
GRAPH_EXPAND_ALPHA = 0.15
_ADJ_CACHE: "dict[str, dict]" = {}


def _atlas_adjacency() -> "dict[str, list]":
    """The compact atlas-induced dependency adjacency `{decl: [atlas neighbours]}` (undirected co-occurrence),
    built by `scripts/public/lean/build_atlas_adjacency.py` from the Mathlib dep-graph. Cached; ``{}`` when the
    artifact is absent (⇒ graph-expansion is a no-op, pure-cosine parity)."""
    if "adj" not in _ADJ_CACHE:
        try:
            if DEFAULT_ATLAS_ADJACENCY.exists():
                _ADJ_CACHE["adj"] = json.loads(DEFAULT_ATLAS_ADJACENCY.read_text(encoding="utf-8")).get("adjacency", {})
            else:
                _ADJ_CACHE["adj"] = {}
        except Exception:  # noqa: BLE001 — adjacency is advisory; any load failure ⇒ cosine-only
            _ADJ_CACHE["adj"] = {}
    return _ADJ_CACHE["adj"]


def _graph_expand_rerank(scored: "list[tuple[float, int]]", rows: "list[dict]") -> "list[tuple[float, int]]":
    """Re-rank cosine-scored candidates `(cosine, idx)` with a DEPENDENCY-GRAPH co-occurrence boost: a candidate
    that is a dep-neighbour of the top cosine SEEDS is boosted by `cosine + α·log1p(#seed-neighbours)`. This is
    the retrieve-then-graph-expand pattern; the graph structure is a strong premise signal (the gnn_ranker eval
    showed even a graph heuristic beats the GNN). RETRIEVAL only — never injects an un-embedded name, never
    closes a goal; the kernel still ratifies. Default-on; `ZTARE_LEANMILL_GRAPH_EXPAND=0` reverts. Fail-safe:
    no adjacency artifact ⇒ returns `scored` unchanged."""
    import math
    if os.environ.get("ZTARE_LEANMILL_GRAPH_EXPAND", "1") == "0" or not scored:
        return scored
    adj = _atlas_adjacency()
    if not adj:
        return scored
    name_of = {idx: str(rows[idx].get("name", "")) for _, idx in scored}
    boost: "dict[str, int]" = {}
    for _c, idx in scored[:GRAPH_EXPAND_SEEDS]:
        for nb in adj.get(name_of[idx], ()):       # neighbours are atlas decl names
            boost[nb] = boost.get(nb, 0) + 1
    if not boost:
        return scored
    rescored = [(c + GRAPH_EXPAND_ALPHA * math.log1p(boost.get(name_of[idx], 0)), idx) for c, idx in scored]
    rescored.sort(reverse=True, key=lambda t: t[0])
    return rescored


@dataclass(frozen=True)
class MathlibSemanticHit:
    """Vocabulary-invariant Mathlib neighbour.

    A cosine match against the embedded Mathlib lemma corpus. Surfaces
    lemmas whose name/preview is semantically close to the query but whose
    shape tags do not overlap the gap-typer's expected tag set (or are
    absent entirely).
    """

    name: str
    kind: str
    file: str
    cosine: float
    preview: str
    shapes: list[str]


_MATHLIB_CACHE: dict[str, tuple[list[dict], list[list[float]]]] = {}


def _load_mathlib_atlas(
    atlas_path: Path, index_path: Path
) -> tuple[list[dict], list[list[float]]]:
    """Load + cache atlas embeddings paired with their lemma metadata."""
    key = str(atlas_path.resolve())
    cached = _MATHLIB_CACHE.get(key)
    if cached is not None:
        return cached
    atlas_payload = json.loads(atlas_path.read_text(encoding="utf-8"))
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))

    if isinstance(atlas_payload, dict):
        atlas_items = atlas_payload.get("embeddings", [])
    else:
        atlas_items = atlas_payload
    embeddings_by_id: dict[str, list[float]] = {}
    for item in atlas_items:
        if isinstance(item, dict) and "id" in item and "embedding" in item:
            embeddings_by_id[str(item["id"])] = item["embedding"]

    by_name = index_payload.get("by_name", {}) if isinstance(index_payload, dict) else {}
    aligned_rows: list[dict] = []
    aligned_vecs: list[list[float]] = []
    for name, entry in by_name.items():
        vec = embeddings_by_id.get(str(name))
        if vec is None:
            continue
        if isinstance(entry, dict):
            row = dict(entry)
            row.setdefault("name", name)
        else:
            row = {"name": name}
        aligned_rows.append(row)
        aligned_vecs.append(vec)
    _MATHLIB_CACHE[key] = (aligned_rows, aligned_vecs)
    return aligned_rows, aligned_vecs


def _embed_query_genai(query: str) -> list[float] | None:
    """Embed via gemini-embedding-001 at 384 dims (RETRIEVAL_QUERY). Returns None on missing deps/key.

    Delegates the embed call to the canonical engine (``ztare.common.embeddings``).
    The API key is checked BEFORE ``make_client`` because ``make_client`` raises
    ``SystemExit`` on a missing key (not caught by ``except Exception``); the
    graceful-degradation contract here is to return ``None`` instead.

    KEY-BOOTSTRAP (2026-06-25 RCA — embedder silently DEAD on the VPS despite keys
    in ``.env`` + live credits): a daemon/nohup launch that did not ``source .env``
    leaves the key absent from ``os.environ`` here, so this early-check returned
    ``None`` and the WHOLE semantic compounding layer (leaf + planner premise
    shelves) fell dead. Resolution now routes through the ONE canonical resolver
    (``embeddings.resolve_gemini_key``), which reads env then bootstraps the
    project-root ``.env`` and re-reads — the SAME loader ``make_client`` uses — so
    this can never be a forgotten sibling again. No-op when the key is exported.
    """
    try:
        from ztare.common.embeddings import resolve_gemini_key
        api_key = resolve_gemini_key()
    except Exception:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from ztare.common.embeddings import embed_batch, make_client
    except Exception:
        return None
    try:
        client = make_client(api_key)
        vecs = embed_batch(
            client,
            [query],
            model="gemini-embedding-001",
            dimensions=384,
            task_type="RETRIEVAL_QUERY",
        )
    except Exception:
        return None
    if not vecs:
        return None
    return list(vecs[0])


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / ((na**0.5) * (nb**0.5))


def mathlib_semantic_neighbours(
    query: str,
    *,
    atlas_path: Path = DEFAULT_MATHLIB_ATLAS,
    index_path: Path = DEFAULT_MATHLIB_INDEX,
    top_k: int = MATHLIB_TOP_K_DEFAULT,
    threshold: float = MATHLIB_THRESHOLD_DEFAULT,
    untagged_only: bool = False,
    embedder=None,
) -> tuple[list[MathlibSemanticHit], int, int, str | None]:
    """Return semantically-similar Mathlib lemmas for the given free-text query.

    Returns ``(hits, corpus_size, filtered_size, skip_reason)``.
    ``skip_reason`` is non-None when the layer degraded gracefully (missing
    atlas, no API key, embed failure). When ``untagged_only`` is True, the
    search is restricted to lemmas whose shape-tag list is empty — the slice
    where the tag-typed index cannot retrieve them and a semantic fallback has
    the strongest information gain.
    """
    if not atlas_path.exists():
        return [], 0, 0, f"mathlib atlas missing: {atlas_path}"
    if not index_path.exists():
        return [], 0, 0, f"mathlib index missing: {index_path}"
    rows, vecs = _load_mathlib_atlas(atlas_path, index_path)
    if not rows:
        return [], 0, 0, "mathlib atlas empty after alignment"

    embed_fn = embedder or _embed_query_genai
    qvec = embed_fn(query)
    if qvec is None:
        return [], len(rows), 0, "query embedding unavailable (no GOOGLE_API_KEY or google.genai)"

    if untagged_only:
        filtered_indices = [i for i, row in enumerate(rows) if not row.get("shapes")]
    else:
        filtered_indices = list(range(len(rows)))
    if not filtered_indices:
        return [], len(rows), 0, "no mathlib entries match filter"

    scored: list[tuple[float, int]] = []
    for idx in filtered_indices:
        scored.append((_cosine(qvec, vecs[idx]), idx))
    scored.sort(reverse=True, key=lambda t: t[0])
    # GRAPH-EXPANSION re-rank (measured lift; default-on, fail-safe — see _graph_expand_rerank). The cosine
    # SEED set is the current top of `scored`; the re-rank can only reorder these same candidates by adding a
    # dep-graph co-occurrence boost, so the threshold gate + hit construction below are unchanged. The boosted
    # cosine value may exceed `threshold` for a candidate whose RAW cosine was below it — that is intended (a
    # strong graph signal earns surfacing), and it stays a Mathlib decl that is re-verified downstream.
    scored = _graph_expand_rerank(scored, rows)

    hits: list[MathlibSemanticHit] = []
    for cosine, idx in scored[:top_k]:
        if cosine < threshold:
            break
        row = rows[idx]
        shapes = row.get("shapes") or []
        if not isinstance(shapes, list):
            shapes = []
        hits.append(
            MathlibSemanticHit(
                name=str(row.get("name", f"row_{idx}")),
                kind=str(row.get("kind", "")),
                file=str(row.get("file", "")),
                cosine=round(float(cosine), 4),
                preview=str(row.get("preview", ""))[:300],
                shapes=[str(s) for s in shapes],
            )
        )
    return hits, len(rows), len(filtered_indices), None


def render_text(hits: list[MathlibSemanticHit], *, header: str = "Mathlib semantic neighbours") -> str:
    """Compact CLI rendering helper for embedding-fallback output."""
    if not hits:
        return f"  {header}: none above threshold"
    lines = [f"  {header}:"]
    for hit in hits:
        tag_suffix = f" [{','.join(hit.shapes)}]" if hit.shapes else " [no-shapes]"
        loc = hit.file or "(no file)"
        lines.append(f"    - cos={hit.cosine:.4f}  {hit.kind} {hit.name}{tag_suffix}  @ {loc}")
    return "\n".join(lines)
