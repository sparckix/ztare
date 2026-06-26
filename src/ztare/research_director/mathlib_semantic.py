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
MATHLIB_THRESHOLD_DEFAULT = 0.55
MATHLIB_TOP_K_DEFAULT = 8


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
