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

DEFAULT_MODEL = "gemini-embedding-001"


def content_id(*parts: str) -> str:
    """Stable content-hash id for cache keying (path + body → 16-hex)."""
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:16]


def make_client(api_key: "str | None" = None):
    """Gemini client (raises SystemExit if no key). Kept here so no consumer imports genai."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Reuse the ONE canonical .env loader — daemon/manual launches often don't export the key
        # though it lives in the project-root .env (the gap that left the semantic shelf silently
        # dead on the VPS). No-op if already loaded; never clobbers an explicit env value.
        try:
            from ztare.common.llm_runtime import _bootstrap_dotenv_if_needed
            _bootstrap_dotenv_if_needed()
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required to build/query an embedding atlas")
    from google import genai
    return genai.Client(api_key=api_key)


def embed_batch(client, texts: list, *, model: str = DEFAULT_MODEL, dimensions: int = 768,
                task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 5,
                default_backoff: float = 30.0) -> list:
    """Embed a batch with rate-limit retry/backoff. The ONE embed call (was duplicated per builder)."""
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
               "size": len(entries), "embeddings_file": str(out_emb)}
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
                model: "str | None" = None) -> list:
    """Embed `query_text` (RETRIEVAL_QUERY) and return the top-k atlas entries by cosine:
    `[{score, id, **meta}]`. The ONE retrieval surface (consumers pass their atlas path)."""
    atlas = json.loads(Path(atlas_path).read_text(encoding="utf-8"))
    model = model or atlas.get("model", DEFAULT_MODEL)
    dims = atlas.get("dimensions", 768)
    client = client or make_client()
    qv = embed_batch(client, [query_text], model=model, dimensions=dims, task_type="RETRIEVAL_QUERY")[0]
    meta = atlas.get("meta", {})
    scored = [(round(_cos(qv, row["embedding"]), 4), row["id"]) for row in atlas.get("embeddings", [])]
    scored.sort(reverse=True)
    return [{"score": sc, "id": cid, **meta.get(cid, {})} for sc, cid in scored[:k]]
