"""Canonical embedding engine — ONE place to create + query Gemini embedding atlases.

WHY: embedding builders were duplicated across corpora (Lean APN / Mathlib / NS, the
primitive atlas, the seam atlas), each copy-pasting the same `embed_batch_with_retry` +
cache-load + build-loop. Per the engine/consumer invariant (AGENTS.md §6n.12/§6n.13): ONE
engine (this module), and each corpus is a thin CONSUMER that only supplies its harvest
(a list of `{id, text, ...meta}` entries) + a config (model/dims/paths). No corpus
re-implements the embed call, the retry/backoff, the content-hash cache, or cosine query.

An "atlas" file is `{generated_at, model, dimensions, size, meta:{id->meta}, embeddings:[{id,embedding}]}`.
Documents are embedded with taskType=RETRIEVAL_DOCUMENT; a query is embedded with
RETRIEVAL_QUERY and scored by cosine — asymmetric retrieval, the established convention.

Typical builder (the whole consumer):
    from ztare.common.embeddings import build_atlas
    entries = harvest()                      # corpus-specific: [{id, text, title, ...}]
    build_atlas(entries, OUT_EMB, OUT_MANIFEST, model="gemini-embedding-001", dimensions=768)

Typical query (the whole retrieval surface):
    from ztare.common.embeddings import query_atlas
    hits = query_atlas(OUT_EMB, "produce a defect-budget certificate", k=8)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from ztare.common.google_genai_client import build_google_genai_client

# FRUGAL LOCAL EMBEDDER (2026-07-05): runtime per-goal query embeddings (`semantic_premise_shelf` + `move_atlas`,
# every dispatch) were hitting the PAID Gemini API — thousands of calls per campaign. sentence-transformers runs a
# strong retrieval embedder LOCALLY (free, ~10ms/query), which is the right tool for cosine recall. DEFAULT-ON;
# `ZTARE_LEANMILL_LOCAL_EMBED=0` reverts to Gemini. The atlas cache keys on the model name, so flipping this
# RE-KEYS every atlas → it rebuilds ONCE in the local space (corpus + query then share one space; cosine is valid).
_LOCAL_EMBED = os.environ.get("ZTARE_LEANMILL_LOCAL_EMBED", "1") != "0"
# Local model choice: all-MiniLM-L6-v2 is the VALIDATED default — clean cosine separation (rel≈0.58 vs unrel≈−0.03
# on a spot check), fast (~33M). SOTA-small retrievers (BAAI/bge-small-en-v1.5, thenlper/gte-small, intfloat/
# e5-small-v2, BAAI/bge-m3 for dense+sparse+multivector) score higher on MTEB and are ONE env-var away
# (`ZTARE_EMBED_LOCAL_MODEL`) — the query-instruction prefixes are already wired (`_QUERY_INSTR`) — BUT they carry
# a COMPRESSED cosine distribution (bge spot-checked rel≈0.56 vs unrel≈0.51), which would silently mis-fire the
# cosine THRESHOLDS in move-atlas recall / structural triggers. So swapping is a config + a threshold re-tune +
# a recall eval, not a blind flip. Default stays on the validated model until that eval is done.
_LOCAL_MODEL_NAME = os.environ.get("ZTARE_EMBED_LOCAL_MODEL", "all-MiniLM-L6-v2")
DEFAULT_MODEL = ("st:" + _LOCAL_MODEL_NAME) if _LOCAL_EMBED else "gemini-embedding-001"
REPO = Path(__file__).resolve().parents[3]
VECTOR_CACHE_SCHEMA = "ztare-embedding-vector-cache-v1"

_ST_MODEL = None
# Instruction-tuned retrievers (BGE/GTE/E5) score query↔doc asymmetrically: the QUERY gets a task instruction,
# the DOCUMENT does not. Skipping this silently drops recall on exactly these models. (all-MiniLM ignores it.)
_QUERY_INSTR = {"bge": "Represent this sentence for searching relevant passages: ",
                "gte": "", "e5": "query: ", "default": ""}


def _embed_local(texts: list, task_type: str = "RETRIEVAL_DOCUMENT") -> list:
    """Embed `texts` with the LOCAL sentence-transformers model (no API, no key). Normalized vectors so a plain
    dot product == cosine (matches `_cos`). Loaded once (first call downloads/caches it). A QUERY gets the model's
    task-instruction prefix; a DOCUMENT does not — the asymmetry these retrievers are trained for."""
    global _ST_MODEL
    if _ST_MODEL is None:
        from sentence_transformers import SentenceTransformer
        import os as _os
        # Default CPU: sentence-transformers auto-selects MPS on Apple
        # silicon, and under memory pressure the Metal allocator SIGTRAPs
        # the whole process (2026-07-11: killed a governed round mid-
        # iteration from inside briefing embed). Batches here are small;
        # CPU is crash-proof. Set ZTARE_EMBED_DEVICE=mps to opt back in.
        _ST_MODEL = SentenceTransformer(
            _LOCAL_MODEL_NAME,
            device=_os.environ.get("ZTARE_EMBED_DEVICE", "cpu"))
    _m = _LOCAL_MODEL_NAME.lower()
    _fam = "bge" if "bge" in _m else "e5" if "e5" in _m else "gte" if "gte" in _m else "default"
    _pre = _QUERY_INSTR.get(_fam, "") if "QUERY" in (task_type or "").upper() else ("query: " if _fam == "e5" and False else "")
    # e5 also needs a "passage: " prefix on documents; handle both sides for e5 specifically.
    if _fam == "e5" and "QUERY" not in (task_type or "").upper():
        _pre = "passage: "
    vecs = _ST_MODEL.encode([_pre + t for t in texts], normalize_embeddings=True, show_progress_bar=False)
    return [[round(float(x), 6) for x in v] for v in vecs]


def content_id(*parts: str) -> str:
    """Stable content-hash id for cache keying (path + body → 16-hex)."""
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:16]


def resolve_gemini_key() -> "str | None":
    """The ONE Gemini/Google API-key resolver for graceful-None embed callers (single door).

    Reads ``os.environ``; if the key is ABSENT, bootstraps the project-root ``.env`` (the SAME
    canonical loader ``make_client`` uses) and re-reads, then returns the key or ``None`` — it
    NEVER raises. WHY this exists: every graceful-None embed entry point (``mathlib_semantic`` /
    ``apn_semantic`` ``_embed_query_genai``, the amnesia/recommender embedders) hand-rolled
    ``os.environ.get(...) or None`` and bailed BEFORE reaching ``make_client``'s bootstrap — so a
    daemon/nohup launch that did not ``source .env`` left the WHOLE semantic compounding layer
    silently dead even with keys on disk + live credits (2026-06-25 RCA). Routing every such
    caller through this ONE resolver means the bootstrap can never be a forgotten sibling again.
    Callers that want a hard failure instead of None use ``make_client`` (it raises SystemExit)."""
    if _LOCAL_EMBED:   # local embedder needs no API key; return a non-None sentinel so graceful-None guards PASS
        return "LOCAL"
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    # Daemon/manual launches often don't export the key though it lives in the project-root .env.
    # No-op if already loaded; never clobbers an explicit env value.
    try:
        from ztare.common.llm_runtime import _bootstrap_dotenv_if_needed
        _bootstrap_dotenv_if_needed()
    except Exception:  # noqa: BLE001 — graceful-None contract: a bootstrap failure ⇒ no key, not a raise
        return None
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def make_client(api_key: "str | None" = None):
    """Gemini client (raises SystemExit if no key). Kept here so no consumer imports genai."""
    # `resolve_gemini_key` does the env-read + project-root .env bootstrap (the ONE door); daemon/
    # manual launches often don't export the key though it lives in .env (the gap that left the
    # semantic shelf silently dead on the VPS). No-op if already loaded; never clobbers explicit env.
    if _LOCAL_EMBED:   # local embedder ignores the client (embed_batch routes to sentence-transformers)
        return "LOCAL"
    api_key = api_key or resolve_gemini_key()
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required to build/query an embedding atlas")
    from google import genai
    return build_google_genai_client(genai.Client, api_key=api_key)


def embed_batch(client, texts: list, *, model: str = DEFAULT_MODEL, dimensions: int = 768,
                task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 5,
                default_backoff: float = 30.0) -> list:
    """Embed a batch with rate-limit retry/backoff. The ONE embed call (was duplicated per builder)."""
    if _LOCAL_EMBED or str(model).startswith("st:"):   # frugal: local sentence-transformers, no API/key
        return _embed_local(texts, task_type)
    from google.genai import types
    attempt = 0
    while True:
        try:
            resp = client.models.embed_content(
                model=model, contents=texts,
                config=types.EmbedContentConfig(taskType=task_type, outputDimensionality=dimensions))
            return [[round(float(v), 6) for v in e.values] for e in resp.embeddings]
        except Exception as exc:
            msg = str(exc)
            if not (("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("quota" in msg.lower())) \
                    or attempt >= max_retries:
                raise
            backoff = default_backoff
            m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", msg)
            if m:
                try:
                    backoff = float(m.group(1)) + 2.0
                except Exception:
                    pass
            attempt += 1
            print(f"  rate-limit (attempt {attempt}/{max_retries}); sleeping {backoff:.1f}s")
            time.sleep(backoff)


def cached_text_embeddings(
    texts: list[str],
    *,
    cache_path: Path,
    cache_keys: "list[str] | None" = None,
    embedder: "Callable[[str], list[float] | None] | None" = None,
    client=None,
    model: str = DEFAULT_MODEL,
    dimensions: int = 768,
    task_type: str = "RETRIEVAL_DOCUMENT",
    max_new: "int | None" = None,
) -> tuple[list[list[float] | None], int, int]:
    """Return embeddings with a content-addressed disk cache.

    This is the general-purpose cache primitive used by retrieval consumers that
    do not own a full atlas. Cache keys include model, dimensions, task type,
    and text hash, so local-vs-Gemini spaces cannot collide. ``max_new`` caps
    fresh embeddings per call; capped entries return ``None`` and can be filled
    by a later pass. Returns ``(vectors, new_embeds, pending)``.
    """
    cache_path = Path(cache_path)
    vectors = _load_vector_cache(cache_path)
    out: list[list[float] | None] = []
    missing: list[tuple[int, str, str]] = []
    cache_keys = list(cache_keys or [])
    for idx, text in enumerate(texts):
        key = (
            str(cache_keys[idx])
            if idx < len(cache_keys) and str(cache_keys[idx]).strip()
            else _vector_cache_key(
                text,
                model=model,
                dimensions=dimensions,
                task_type=task_type,
            )
        )
        vec = vectors.get(key)
        if _valid_vector(vec):
            out.append(vec)
            continue
        out.append(None)
        missing.append((idx, key, text))

    if max_new is not None:
        to_embed = missing[:max(0, int(max_new))]
        pending = max(0, len(missing) - len(to_embed))
    else:
        to_embed = missing
        pending = 0

    new_embeds = 0
    if to_embed:
        if embedder is not None:
            fresh = [embedder(text) for _, _, text in to_embed]
        else:
            client = client or make_client()
            fresh = embed_batch(
                client,
                [text for _, _, text in to_embed],
                model=model,
                dimensions=dimensions,
                task_type=task_type,
            )
        for (idx, key, _text), vec in zip(to_embed, fresh):
            if _valid_vector(vec):
                v = [float(x) for x in vec]
                vectors[key] = v
                out[idx] = v
                new_embeds += 1
        if new_embeds:
            _write_vector_cache(cache_path, vectors)
    return out, new_embeds, pending


def _vector_cache_key(text: str, *, model: str, dimensions: int, task_type: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "dimensions": int(dimensions),
            "task_type": task_type,
            "sha256": hashlib.sha256(str(text or "").encode("utf-8")).hexdigest(),
        },
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _load_vector_cache(path: Path) -> dict[str, list[float]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, dict) and payload.get("schema") == VECTOR_CACHE_SCHEMA:
        rows = payload.get("vectors") or {}
    elif isinstance(payload, dict):
        rows = payload
    else:
        return {}
    return {
        str(key): [float(x) for x in vec]
        for key, vec in rows.items()
        if isinstance(key, str) and _valid_vector(vec)
    }


def _write_vector_cache(path: Path, vectors: dict[str, list[float]]) -> None:
    payload = {
        "schema": VECTOR_CACHE_SCHEMA,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "vectors": vectors,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _valid_vector(vec: object) -> bool:
    return (
        isinstance(vec, list)
        and bool(vec)
        and all(isinstance(x, (int, float)) for x in vec)
    )


def load_cached(path: Path, model: str, dimensions: int) -> dict:
    """Reuse prior embeddings iff model+dims match (content-hash ids ⇒ only changed docs re-embed)."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if payload.get("model") != model or payload.get("dimensions") != dimensions:
        return {}
    return {row["id"]: row["embedding"] for row in payload.get("embeddings", [])
            if isinstance(row, dict) and "id" in row}


def _manifest_path(path: Path) -> str:
    """Return a publish-safe manifest path for repo-owned atlas artifacts."""
    p = Path(path)
    try:
        return p.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(p)


def build_atlas(entries: list, out_emb: Path, out_manifest: "Path | None" = None, *,
                model: str = DEFAULT_MODEL, dimensions: int = 768, batch_size: int = 32,
                rebuild: bool = False, sleep: float = 0.05, client=None,
                extra_manifest: "dict | None" = None) -> dict:
    """Build/refresh an atlas from harvested `entries` (each needs `id` + `text`; other keys → meta).
    Content-hash cached: only entries whose id is absent re-embed. Returns the atlas dict."""
    out_emb = Path(out_emb)
    client = client or make_client()
    existing = {} if rebuild else load_cached(out_emb, model, dimensions)
    pending = [e for e in entries if e["id"] not in existing]
    rows = [{"id": e["id"], "embedding": existing[e["id"]]} for e in entries if e["id"] in existing]
    print(f"[embeddings] {model} {dimensions}d — {len(pending)} new, {len(rows)} reused, {len(entries)} total")
    for s in range(0, len(pending), batch_size):
        batch = pending[s:s + batch_size]
        vecs = embed_batch(client, [e["text"] for e in batch], model=model, dimensions=dimensions)
        rows.extend({"id": e["id"], "embedding": v} for e, v in zip(batch, vecs))
        print(f"  embedded {min(s + batch_size, len(pending))}/{len(pending)}")
        if sleep:
            time.sleep(sleep)
    meta = {e["id"]: {k: v for k, v in e.items() if k not in ("id", "text", "embedding")} for e in entries}
    atlas = {"generated_at": datetime.now(timezone.utc).isoformat(), "model": model,
             "dimensions": dimensions, "size": len(entries), "meta": meta, "embeddings": rows}
    out_emb.parent.mkdir(parents=True, exist_ok=True)
    out_emb.write_text(json.dumps(atlas, ensure_ascii=False), encoding="utf-8")
    if out_manifest:
        man = {"generated_at": atlas["generated_at"], "model": model, "dimensions": dimensions,
               "size": len(entries), "embeddings_file": _manifest_path(out_emb)}
        man.update(extra_manifest or {})
        Path(out_manifest).write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(f"[embeddings] wrote {out_emb}")
    return atlas


def _cos(a: list, b: list) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return s / (na * nb) if na and nb else 0.0


def query_atlas(atlas_path: Path, query_text: str, *, k: int = 8, client=None,
                model: "str | None" = None,
                query_cache_path: "Path | None" = None) -> list:
    """Embed `query_text` (RETRIEVAL_QUERY) and return the top-k atlas entries by cosine:
    `[{score, id, **meta}]`. The ONE retrieval surface (consumers pass their atlas path)."""
    atlas = json.loads(Path(atlas_path).read_text(encoding="utf-8"))
    model = model or atlas.get("model", DEFAULT_MODEL)
    dims = atlas.get("dimensions", 768)
    client = client or make_client()
    if query_cache_path is not None:
        qv = cached_text_embeddings(
            [query_text],
            cache_path=Path(query_cache_path),
            client=client,
            model=model,
            dimensions=dims,
            task_type="RETRIEVAL_QUERY",
        )[0][0]
    else:
        qv = embed_batch(client, [query_text], model=model, dimensions=dims, task_type="RETRIEVAL_QUERY")[0]
    if qv is None:
        return []
    meta = atlas.get("meta", {})
    scored = [(round(_cos(qv, row["embedding"]), 4), row["id"]) for row in atlas.get("embeddings", [])]
    scored.sort(reverse=True)
    return [{"score": sc, "id": cid, **meta.get(cid, {})} for sc, cid in scored[:k]]
