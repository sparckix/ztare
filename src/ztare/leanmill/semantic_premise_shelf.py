"""Semantic premise shelf for Lean proof-loop prompts.

This is an advisory retrieval layer. It gives proof-loop workers nearby
Mathlib/APN/NS declarations as candidate premise context, but it does not
create proof value and it does not bypass the existing anti-laundering gates.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from src.ztare.research_director.apn_semantic import apn_semantic_neighbours
from src.ztare.research_director.mathlib_semantic import (
    _cosine as _mathlib_cosine,
    _embed_query_genai,
    mathlib_semantic_neighbours,
)


REPO = Path(__file__).resolve().parents[3]


# ── Domain atlas registry (plugin / config-driven) ─────────────────────
# The shelf accepts ZERO hardcoded domain paths. Per-domain atlases are
# registered in the factory policy under
# `operations.semantic_premise_shelf.domain_atlases`, each entry shaped
# {name, atlas_path, corpus_path}. A public clone with no domain atlases
# registered just gets Mathlib + APN hits and a clean "no domain layer"
# fallthrough — never a path-not-found error.
def _domain_atlas_specs() -> list[dict[str, str]]:
    """Read registered domain atlases from policy; empty list if absent."""
    try:
        from ztare.leanmill.policy import read_policy
        policy_path = REPO / "analytics" / "public" / "leanmill" / "dashboard_data" / "leanmill_factory_policy.json"
        pol = read_policy(policy_path)
        ops = pol.get("operations") if isinstance(pol.get("operations"), dict) else {}
        sps = ops.get("semantic_premise_shelf") if isinstance(ops.get("semantic_premise_shelf"), dict) else {}
        specs = sps.get("domain_atlases") if isinstance(sps.get("domain_atlases"), list) else []
        return [s for s in specs if isinstance(s, dict) and s.get("atlas_path") and s.get("corpus_path")]
    except Exception:
        return []


_DOMAIN_ATLAS_CACHE: dict[tuple[str, str], tuple[list[dict[str, Any]], list[list[float]]]] = {}
# Back-compat aliases used by older call sites; deprecated.
_NS_CACHE = _DOMAIN_ATLAS_CACHE


def _load_domain_atlas(
    atlas_path: Path,
    corpus_path: Path,
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    key = (str(atlas_path.resolve()), str(corpus_path.resolve()))
    cached = _NS_CACHE.get(key)
    if cached is not None:
        return cached
    if not atlas_path.exists() or not corpus_path.exists():
        _NS_CACHE[key] = ([], [])
        return [], []
    atlas_payload = json.loads(atlas_path.read_text(encoding="utf-8"))
    corpus_payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    atlas_items = atlas_payload.get("embeddings", []) if isinstance(atlas_payload, dict) else atlas_payload
    embeddings_by_id: dict[str, list[float]] = {}
    for item in atlas_items:
        if isinstance(item, dict) and "id" in item and "embedding" in item:
            embeddings_by_id[str(item["id"])] = item["embedding"]
    corpus_entries = corpus_payload.get("entries", []) if isinstance(corpus_payload, dict) else corpus_payload
    rows: list[dict[str, Any]] = []
    vecs: list[list[float]] = []
    for entry in corpus_entries:
        if not isinstance(entry, dict):
            continue
        eid = str(entry.get("id") or "")
        vec = embeddings_by_id.get(eid)
        if not eid or vec is None:
            continue
        rows.append(entry)
        vecs.append(vec)
    _NS_CACHE[key] = (rows, vecs)
    return rows, vecs


def _cached_embedder() -> Callable[[str], list[float] | None]:
    cache: dict[str, list[float] | None] = {}

    def embed(query: str) -> list[float] | None:
        if query not in cache:
            cache[query] = _embed_query_genai(query)
        return cache[query]

    return embed


def _domain_atlas_semantic_hits(
    query: str,
    *,
    embedder: Callable[[str], list[float] | None],
    top_k: int,
    threshold: float,
) -> tuple[list[dict[str, Any]], int, str | None]:
    """Query every registered domain atlas (via policy) and return merged hits.
    Empty list when no domain atlases registered — that's a clean no-op, not
    an error.
    """
    specs = _domain_atlas_specs()
    if not specs:
        return [], 0, "no domain atlases registered in policy.operations.semantic_premise_shelf.domain_atlases"
    all_rows: list[dict[str, Any]] = []
    all_vecs: list[list[float]] = []
    atlas_names: list[str] = []
    for spec in specs:
        ap = Path(spec["atlas_path"])
        cp = Path(spec["corpus_path"])
        if not ap.is_absolute(): ap = REPO / ap
        if not cp.is_absolute(): cp = REPO / cp
        rows, vecs = _load_domain_atlas(ap, cp)
        for r in rows: r.setdefault("_atlas_name", spec.get("name") or "domain")
        all_rows.extend(rows); all_vecs.extend(vecs)
        if rows: atlas_names.append(spec.get("name") or str(ap.name))
    if not all_rows:
        return [], 0, f"domain atlases registered but empty: {[s.get('name') for s in specs]}"
    qvec = embedder(query)
    if qvec is None:
        return [], len(all_rows), "query embedding unavailable (no GOOGLE_API_KEY or google.genai)"
    scored = [(_mathlib_cosine(qvec, vec), idx) for idx, vec in enumerate(all_vecs)]
    scored.sort(reverse=True, key=lambda item: item[0])
    hits: list[dict[str, Any]] = []
    for cosine, idx in scored[:top_k]:
        if cosine < threshold:
            break
        row = all_rows[idx]
        hits.append(
            {
                "source": row.get("_atlas_name", "domain_atlas"),
                "name": str(row.get("name") or row.get("id") or "?"),
                "kind": str(row.get("kind") or ""),
                "file": str(row.get("path") or row.get("file") or ""),
                "score": round(float(cosine), 4),
                "preview": str(row.get("text") or "")[:300],
                "metadata": {
                    "status": str(row.get("status") or ""),
                    "tags": row.get("tags") or [],
                },
            }
        )
    return hits, len(rows), None


import re as _re_shelf


def _shelf_conclusion(stmt: str) -> str:
    """Text after the LAST top-level ':' (binders' ':' sit inside parens), ':='-stripped."""
    body = _re_shelf.split(r":=", stmt or "", 1)[0]
    depth = 0
    last = -1
    for i, ch in enumerate(body):
        if ch in "([{⦃":
            depth += 1
        elif ch in ")]}⦄":
            depth -= 1
        elif ch == ":" and depth == 0:
            last = i
    return body[last + 1:].strip() if last >= 0 else body.strip()


def _shelf_norm(s: str) -> str:
    return _re_shelf.sub(r"[()\s]", "", _re_shelf.sub(r"\bid\b", "", s or ""))


def in_scope_citation_hits(query: str, source: str, lean_root, *, k: int = 6) -> list:
    """The MEMOIZATION fix (RCA 2026-06-04): surface IMPORTED-file lemmas whose CONCLUSION matches the
    goal, so the agent (and the prompt) can `exact <name>` instead of re-deriving a result already in
    scope. The premise shelf used to index only the embedded atlases (Mathlib/APN/NS), NEVER the file
    the ad-hoc imports — so a 1-line citation (e.g. indicatorTranslationInteriorTerm_…) was invisible
    and the warm agent re-derived + failed. EXACT-conclusion match → score 1.0 ('this already closes
    it'); token-overlap ≥0.6 → near-match. Pure regex/CPU; advisory like the rest of the shelf."""
    if not source or lean_root is None:
        return []
    from pathlib import Path as _P
    lean_root = _P(lean_root)
    goal_concl_raw = _shelf_conclusion(query)
    goal_concl = _shelf_norm(goal_concl_raw)
    if len(goal_concl) < 4:
        return []
    goal_tokens = set(_re_shelf.findall(r"[A-Za-z_][\w'.]+", goal_concl_raw))
    hits, seen = [], set()
    for mod in _re_shelf.findall(r"(?m)^\s*import\s+([\w.]+)", source):
        f = lean_root / (mod.replace(".", "/") + ".lean")
        if str(f) in seen or not f.exists():
            continue
        seen.add(str(f))
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in _re_shelf.finditer(
                r"(?ms)^\s*(?:@\[[^\]]*\]\s*)?(?:theorem|lemma)\s+([A-Za-z_][\w'.]*)(.*?):=", text):
            name, sig = m.group(1), m.group(2)
            concl_raw = _shelf_conclusion(sig)
            nconcl = _shelf_norm(concl_raw)
            if len(nconcl) < 4:
                continue
            if nconcl == goal_concl:
                score = 1.0
            else:
                lt = set(_re_shelf.findall(r"[A-Za-z_][\w'.]+", concl_raw))
                ov = len(goal_tokens & lt) / max(1, len(goal_tokens | lt))
                if ov < 0.6:
                    continue
                score = round(0.6 + 0.39 * ov, 4)
            hits.append({"source": "in_scope", "name": name, "kind": "imported_lemma",
                         "file": mod, "score": score, "preview": concl_raw[:160],
                         "metadata": {"citation": f"exact {name}"}})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:k]


def build_semantic_premise_shelf(
    query: str,
    *,
    top_k_mathlib: int = 8,
    top_k_apn: int = 5,
    top_k_ns: int = 5,
    threshold: float = 0.55,
    include_ns: bool = True,
    embedder: Callable[[str], list[float] | None] | None = None,
    source: str = "",
    lean_root=None,
) -> dict[str, Any]:
    """Return an advisory candidate-premise shelf for a proof-loop query."""
    query = str(query or "").strip()
    if not query:
        return {
            "schema": "leanmill-semantic-premise-shelf-v1",
            "query_preview": "",
            "hits": [],
            "skip_reasons": ["empty query"],
        }
    embed_fn = embedder or _cached_embedder()
    hits: list[dict[str, Any]] = []
    skip_reasons: list[str] = []

    # IN-SCOPE citation leg FIRST (the memoization fix) — imported lemmas whose conclusion matches the
    # goal; an exact match (score 1.0) is a direct `exact <name>` closure. Surfaced ABOVE the atlas hits.
    try:
        hits.extend(in_scope_citation_hits(query, source, lean_root))
    except Exception as _e:  # never let the new leg break the shelf
        skip_reasons.append(f"in_scope: {str(_e)[:80]}")

    mathlib_hits, mathlib_size, mathlib_filtered, mathlib_skip = mathlib_semantic_neighbours(
        query,
        top_k=top_k_mathlib,
        threshold=threshold,
        embedder=embed_fn,
    )
    if mathlib_skip:
        skip_reasons.append(f"mathlib: {mathlib_skip}")
    for hit in mathlib_hits:
        hits.append(
            {
                "source": "mathlib",
                "name": hit.name,
                "kind": hit.kind,
                "file": hit.file,
                "score": hit.cosine,
                "preview": hit.preview,
                "metadata": {"shapes": hit.shapes},
            }
        )

    apn_hits, apn_size, apn_filtered, apn_skip = apn_semantic_neighbours(
        query,
        top_k=top_k_apn,
        threshold=threshold,
        domain_filter=None,
        embedder=embed_fn,
    )
    if apn_skip:
        skip_reasons.append(f"apn: {apn_skip}")
    for hit in apn_hits:
        hits.append(
            {
                "source": "apn",
                "name": hit.name,
                "kind": hit.kind,
                "file": hit.file,
                "score": hit.cosine,
                "preview": hit.snippet,
                "metadata": {
                    "domain": hit.domain,
                    "variant_tag": hit.variant_tag,
                    "id": hit.id,
                },
            }
        )

    ns_size = 0
    # `include_ns` parameter name retained for back-compat; meaning is now
    # "include domain atlas hits from any registered atlas in policy".
    if include_ns:
        domain_hits, ns_size, domain_skip = _domain_atlas_semantic_hits(
            query,
            embedder=embed_fn,
            top_k=top_k_ns,
            threshold=threshold,
        )
        if domain_skip:
            skip_reasons.append(f"domain_atlas: {domain_skip}")
        hits.extend(domain_hits)

    hits.sort(key=lambda item: (float(item.get("score") or 0.0), str(item.get("source") or "")), reverse=True)
    return {
        "schema": "leanmill-semantic-premise-shelf-v1",
        "query_preview": query[:500],
        "threshold": threshold,
        "corpus_sizes": {
            "mathlib": mathlib_size,
            "mathlib_filtered": mathlib_filtered,
            "apn": apn_size,
            "apn_filtered": apn_filtered,
            "domain_atlas": ns_size,
        },
        "hits": hits,
        "skip_reasons": skip_reasons,
        "science_rule": "Advisory retrieval context only; proof value still requires Lean replay, matched controls, and Governance Gate receipts.",
    }


def render_semantic_premise_shelf(shelf: dict[str, Any], *, max_hits: int = 12) -> str:
    """Render a compact prompt block."""
    hits = [h for h in shelf.get("hits") or [] if isinstance(h, dict)]
    lines = [
        "Candidate lemma shelf (semantic retrieval context only; not a negative dictionary and not proof credit):"
    ]
    if not hits:
        skips = "; ".join(str(x) for x in (shelf.get("skip_reasons") or []) if str(x))
        lines.append(f"- none available above threshold{': ' + skips if skips else ''}")
        return "\n".join(lines)
    for hit in hits[:max_hits]:
        source = str(hit.get("source") or "?")
        score = float(hit.get("score") or 0.0)
        kind = str(hit.get("kind") or "").strip()
        name = str(hit.get("name") or "?").strip()
        file = str(hit.get("file") or "").strip()
        preview = " ".join(str(hit.get("preview") or "").split())[:180]
        meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        tag = ""
        if source == "mathlib" and meta.get("shapes"):
            tag = f" shapes={','.join(str(s) for s in meta.get('shapes')[:4])}"
        elif source == "apn" and meta.get("domain"):
            tag = f" domain={meta.get('domain')}"
        elif meta.get("status"):
            tag = f" status={meta.get('status')}"
        loc = f" @ {file}" if file else ""
        if source == "in_scope":
            # the memoization hit: an imported lemma already in scope whose conclusion matches — the
            # agent should CITE it, not re-derive. A match≈1.0 is a direct one-line closure.
            verb = "CLOSES (try `exact " + name + "`)" if score >= 0.999 else "candidate (try `exact " + name + "`)"
            lines.append(f"- [IN-SCOPE match={score:.2f}] {verb} — imported lemma, conclusion matches the goal{loc}")
        else:
            lines.append(f"- [{source} cos={score:.4f}] {kind} {name}{tag}{loc}")
        if preview:
            lines.append(f"  preview: {preview}")
    if shelf.get("skip_reasons"):
        lines.append("Retrieval degradation notes: " + "; ".join(str(x) for x in shelf.get("skip_reasons")))
    return "\n".join(lines)


def semantic_premise_shelf_enabled() -> bool:
    return os.environ.get("LEANMILL_DISABLE_SEMANTIC_PREMISE_SHELF", "").lower() not in {"1", "true", "yes"}
