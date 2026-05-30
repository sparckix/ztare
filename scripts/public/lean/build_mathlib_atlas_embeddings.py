#!/usr/bin/env python3
"""Build a Gemini embedding artifact for the Mathlib lemma index.

This is a static-public RAG artifact for the RD-side `mathlib_semantic`
primitive (fallback when shape-tag retrieval returns 0). It reads
`analytics/public/queries/lean/mathlib_lemma_index.json` and writes embedding
+ manifest artifacts under the same directory. Reuses cached vectors when the
model/dimensions match; pass `--rebuild` to force a fresh embed pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_INDEX = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json"
DEFAULT_EMBEDDINGS = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_atlas_embeddings.json"
DEFAULT_MANIFEST = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_atlas_embeddings_manifest.json"

ANALYSIS_SUBDIRS_DEFAULT = (
    "Analysis", "MeasureTheory", "Topology", "Probability",
    "Geometry", "Order", "NumberTheory",
)


def stable_json(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(data))
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def corpus_text(name: str, entry: dict) -> str:
    """Compact embedding-input string per lemma."""
    shapes = entry.get("shapes") or []
    parts = [
        f"Mathlib {entry.get('kind', 'theorem')}: {name}",
        f"File: {entry.get('file', '')}",
    ]
    if shapes:
        parts.append(f"Shape tags: {', '.join(map(str, shapes))}")
    preview = (entry.get("preview") or "").strip()
    if preview:
        parts.append(f"Statement: {preview}")
    return "\n".join(parts)[:2400]


def select_entries(
    index: dict,
    *,
    untagged_only: bool,
    subdir_filter: tuple[str, ...] | None,
    max_entries: int,
) -> list[dict]:
    by_name = index.get("by_name", {})
    rows: list[dict] = []
    subdir_set = set(subdir_filter) if subdir_filter else None
    for name, entry in by_name.items():
        if not isinstance(entry, dict):
            continue
        if untagged_only and entry.get("shapes"):
            continue
        if subdir_set is not None:
            top = (entry.get("file") or "").split("/", 1)[0]
            if top not in subdir_set:
                continue
        rows.append({
            "id": name,
            "name": name,
            "kind": entry.get("kind", ""),
            "file": entry.get("file", ""),
            "shapes": list(entry.get("shapes") or []),
            "preview": (entry.get("preview") or "")[:600],
            "text": corpus_text(name, entry),
        })
    rows.sort(key=lambda r: r["id"])
    if max_entries > 0:
        rows = rows[:max_entries]
    return rows


def load_existing_embeddings(path: Path, model: str, dimensions: int) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if payload.get("model") != model or payload.get("dimensions") != dimensions:
        return {}
    return {
        row["id"]: row["embedding"]
        for row in payload.get("embeddings", [])
        if isinstance(row, dict) and "id" in row and isinstance(row.get("embedding"), list)
    }


def embed_batch(client, model: str, dimensions: int, texts: list[str]) -> list[list[float]]:
    """Embed a single batch. Caller handles retry/backoff."""
    from google.genai import types  # type: ignore[import-not-found]
    response = client.models.embed_content(
        model=model,
        contents=texts,
        config=types.EmbedContentConfig(
            taskType="RETRIEVAL_DOCUMENT",
            outputDimensionality=dimensions,
        ),
    )
    return [
        [round(float(value), 6) for value in embedding.values]
        for embedding in response.embeddings
    ]


def embed_batch_with_retry(
    client, model: str, dimensions: int, texts: list[str],
    *, max_retries: int = 5, default_backoff: float = 30.0,
) -> list[list[float]]:
    """Wrap embed_batch with 429/quota retry. Respects `retryDelay` when present."""
    attempt = 0
    while True:
        try:
            return embed_batch(client, model, dimensions, texts)
        except Exception as exc:
            msg = str(exc)
            is_quota = ("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("quota" in msg.lower())
            if not is_quota or attempt >= max_retries:
                raise
            # Try to parse retryDelay from the error message (Google APIs include it as e.g. "retryDelay': '51s'")
            backoff = default_backoff
            m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", msg)
            if m:
                try:
                    backoff = float(m.group(1)) + 2.0  # small buffer past the suggested delay
                except ValueError:
                    pass
            attempt += 1
            print(f"  rate-limit hit (attempt {attempt}/{max_retries}); sleeping {backoff:.1f}s")
            time.sleep(backoff)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--embeddings-out", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--model", default="gemini-embedding-001")
    parser.add_argument("--dimensions", type=int, default=384)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=1000,
        help="Flush embeddings to disk every N entries (resumable on crash).",
    )
    parser.add_argument("--max-entries", type=int, default=0, help="0 = no cap.")
    parser.add_argument("--untagged-only", action="store_true",
                        help="Restrict to lemmas with empty shape-tag list (the slice the tag-typed index cannot retrieve).")
    parser.add_argument("--analysis-only", action="store_true",
                        help="Restrict to analysis-relevant top-level subdirs.")
    parser.add_argument("--subdir", action="append", default=None,
                        help="Repeatable: restrict to lemmas under this Mathlib top-level subdir.")
    parser.add_argument("--rebuild", action="store_true", help="Ignore cached embeddings.")
    parser.add_argument("--no-embed", action="store_true", help="Write nothing; just print selection size.")
    parser.add_argument("--dry-run", action="store_true", help="Print selection stats and exit, no writes.")
    args = parser.parse_args()

    if not args.index.exists():
        raise SystemExit(f"Mathlib index missing: {args.index}")

    index = json.loads(args.index.read_text(encoding="utf-8"))
    if args.subdir:
        subdir_filter: tuple[str, ...] | None = tuple(args.subdir)
    elif args.analysis_only:
        subdir_filter = ANALYSIS_SUBDIRS_DEFAULT
    else:
        subdir_filter = None

    entries = select_entries(
        index,
        untagged_only=args.untagged_only,
        subdir_filter=subdir_filter,
        max_entries=args.max_entries,
    )
    total = len(index.get("by_name", {}))
    print(f"Mathlib index total: {total}")
    print(f"selection size: {len(entries)}")
    if subdir_filter:
        print(f"  subdir filter: {subdir_filter}")
    if args.untagged_only:
        print(f"  untagged_only: True (only lemmas with no shape tags)")
    if args.max_entries > 0:
        print(f"  max_entries cap: {args.max_entries}")

    if args.dry_run:
        print("(dry-run; no embed, no writes)")
        return 0

    embeddings: list[dict] = []
    reused = 0
    if not args.no_embed:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is required unless --no-embed is set")
        from google import genai  # type: ignore[import-not-found]
        client = genai.Client(api_key=api_key)
        existing: dict[str, list[float]] = (
            {} if args.rebuild else load_existing_embeddings(args.embeddings_out, args.model, args.dimensions)
        )
        pending: list[dict] = []
        for row in entries:
            vector = existing.get(str(row["id"]))
            if vector is not None:
                embeddings.append({"id": row["id"], "embedding": vector})
                reused += 1
            else:
                pending.append(row)
        checkpoint_every = max(1, args.checkpoint_every)
        since_checkpoint = 0
        for start in range(0, len(pending), args.batch_size):
            batch = pending[start:start + args.batch_size]
            vectors = embed_batch_with_retry(
                client, args.model, args.dimensions, [row["text"] for row in batch]
            )
            if len(vectors) != len(batch):
                raise RuntimeError(f"embedding batch returned {len(vectors)} vectors for {len(batch)} inputs")
            embeddings.extend({"id": row["id"], "embedding": vector} for row, vector in zip(batch, vectors))
            done = reused + min(start + len(batch), len(pending))
            print(f"embedded {done}/{len(entries)}")
            since_checkpoint += len(batch)
            if since_checkpoint >= checkpoint_every:
                # Checkpoint write — preserves progress against rate-limit crashes.
                # Sorted by selection order so cache-reuse on resume is deterministic.
                order = {row["id"]: i for i, row in enumerate(entries)}
                snapshot = sorted(embeddings, key=lambda row: order.get(row["id"], 10**9))
                write_json(args.embeddings_out, {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "model": args.model,
                    "dimensions": args.dimensions,
                    "selection": {
                        "subdir_filter": list(subdir_filter) if subdir_filter else None,
                        "untagged_only": args.untagged_only,
                        "max_entries": args.max_entries,
                        "size": len(entries),
                    },
                    "checkpoint": True,
                    "embeddings": snapshot,
                })
                print(f"  checkpoint: wrote {len(snapshot)} embeddings so far")
                since_checkpoint = 0
            if args.sleep:
                time.sleep(args.sleep)
        order = {row["id"]: i for i, row in enumerate(entries)}
        embeddings.sort(key=lambda row: order.get(row["id"], 10**9))
        write_json(args.embeddings_out, {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "dimensions": args.dimensions,
            "selection": {
                "subdir_filter": list(subdir_filter) if subdir_filter else None,
                "untagged_only": args.untagged_only,
                "max_entries": args.max_entries,
                "size": len(entries),
            },
            "embeddings": embeddings,
        })
        print(f"wrote {args.embeddings_out.relative_to(REPO)} embeddings={len(embeddings)} reused={reused}")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model if not args.no_embed else None,
        "dimensions": args.dimensions if not args.no_embed else None,
        "selection": {
            "subdir_filter": list(subdir_filter) if subdir_filter else None,
            "untagged_only": args.untagged_only,
            "max_entries": args.max_entries,
            "size": len(entries),
        },
        "entries": len(embeddings),
        "embedding_path": str(args.embeddings_out.relative_to(REPO)) if embeddings else None,
        "embedding_sha256": sha256_path(args.embeddings_out) if embeddings and args.embeddings_out.exists() else None,
        "no_embed": args.no_embed,
    }
    write_json(args.manifest_out, manifest)
    print(f"wrote {args.manifest_out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
