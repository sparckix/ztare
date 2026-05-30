#!/usr/bin/env python3
"""Build a Gemini embedding artifact for the NS Lean atlas.

This is a static-public RAG artifact: it writes corpus rows and vectors to
`projects/ns_millennium_hunt/public/` for downstream retrieval. It never puts an
API key in the browser and does not write official research state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from ns_formalization_atlas import REPO, build_data


PUBLIC_DIR = REPO / "projects" / "ns_millennium_hunt" / "public"
DEFAULT_CORPUS = PUBLIC_DIR / "ns_atlas_rag_corpus.json"
DEFAULT_EMBEDDINGS = PUBLIC_DIR / "ns_atlas_embeddings.json"
DEFAULT_MANIFEST = PUBLIC_DIR / "ns_atlas_embeddings_manifest.json"


def stable_json(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def node_score(node: dict) -> float:
    text = f"{node.get('name', '')} {node.get('status', '')} {' '.join(node.get('tags', []))}".lower()
    score = float(min(int(node.get("used_by_count") or 0), 80))
    kind = str(node.get("kind") or "").lower()
    status = str(node.get("status") or "").lower()
    if kind in {"theorem", "lemma"}:
        score += 65
    if kind in {"axiom", "opaque"}:
        score += 35
    if "open" in status or "frontier" in status:
        score += 55
    if "closed" in status:
        score += 24
    for marker, bonus in [
        ("pressure", 45),
        ("c7", 42),
        ("radius", 38),
        ("carleson", 36),
        ("vortex", 36),
        ("bkm", 34),
        ("constantin", 34),
        ("falsifier", 32),
        ("boundary", 28),
        ("receipt", 20),
        ("interface", 16),
    ]:
        if marker in text:
            score += bonus
    return score


def corpus_text(node: dict, nodes: list[dict]) -> str:
    deps = [nodes[i]["name"] for i in (node.get("uses") or [])[:12] if 0 <= i < len(nodes)]
    users = [nodes[i]["name"] for i in (node.get("used_by") or [])[:12] if 0 <= i < len(nodes)]
    parts = [
        f"Lean declaration: {node.get('name', '')}",
        f"Kind: {node.get('kind', '')}",
        f"Status: {node.get('status', '')}",
        f"Source: {node.get('path', '')}:{node.get('line', '')}",
        f"Tags: {', '.join(node.get('tags') or [])}",
        f"Documentation: {node.get('doc') or ''}",
    ]
    if deps:
        parts.append(f"Depends on: {', '.join(deps)}")
    if users:
        parts.append(f"Used by: {', '.join(users)}")
    return "\n".join(parts)[:6000]


def build_corpus(max_entries: int) -> list[dict]:
    data = build_data()
    nodes = data["nodes"]
    ranked = sorted(
        enumerate(nodes),
        key=lambda pair: (-node_score(pair[1]), str(pair[1].get("name") or "")),
    )
    if max_entries > 0:
        ranked = ranked[:max_entries]
    entries = []
    for index, node in ranked:
        entries.append({
            "id": node.get("id"),
            "name": node.get("name"),
            "kind": node.get("kind"),
            "status": node.get("status"),
            "path": node.get("path"),
            "file": node.get("file"),
            "line": node.get("line"),
            "tags": node.get("tags") or [],
            "used_by_count": node.get("used_by_count") or 0,
            "score": round(node_score(node), 3),
            "node_index": index,
            "text": corpus_text(node, nodes),
        })
    return entries


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


def embed_batch(client: genai.Client, model: str, dimensions: int, texts: list[str]) -> list[list[float]]:
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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stable_json(data))
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-entries", type=int, default=1200, help="0 means embed every atlas corpus row.")
    parser.add_argument("--model", default="gemini-embedding-001")
    parser.add_argument("--dimensions", type=int, default=384)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--no-embed", action="store_true", help="Write corpus and manifest only.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Ignore any existing embedding file and regenerate every selected vector.",
    )
    parser.add_argument("--corpus-out", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--embeddings-out", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    corpus = build_corpus(args.max_entries)
    write_json(args.corpus_out, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection": "highest-signal Lean declarations by kind/status/graph centrality/frontier markers",
        "entries": corpus,
    })
    print(f"wrote {args.corpus_out.relative_to(REPO)} entries={len(corpus)}")

    embeddings: list[dict] = []
    reused = 0
    if not args.no_embed:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY is required unless --no-embed is set")
        client = genai.Client(api_key=api_key)
        existing = {} if args.rebuild else load_existing_embeddings(args.embeddings_out, args.model, args.dimensions)
        pending: list[dict] = []
        for row in corpus:
            vector = existing.get(str(row["id"]))
            if vector is not None:
                embeddings.append({"id": row["id"], "embedding": vector})
                reused += 1
            else:
                pending.append(row)
        for start in range(0, len(pending), args.batch_size):
            batch = pending[start:start + args.batch_size]
            vectors = embed_batch(client, args.model, args.dimensions, [row["text"] for row in batch])
            if len(vectors) != len(batch):
                raise RuntimeError(f"embedding batch returned {len(vectors)} vectors for {len(batch)} inputs")
            embeddings.extend({"id": row["id"], "embedding": vector} for row, vector in zip(batch, vectors))
            done = reused + min(start + len(batch), len(pending))
            print(f"embedded {done}/{len(corpus)}")
            if args.sleep:
                time.sleep(args.sleep)
        order = {row["id"]: i for i, row in enumerate(corpus)}
        embeddings.sort(key=lambda row: order.get(row["id"], 10**9))
        write_json(args.embeddings_out, {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "dimensions": args.dimensions,
            "selection": "highest-signal Lean declarations by kind/status/graph centrality/frontier markers",
            "embeddings": embeddings,
        })
        print(f"wrote {args.embeddings_out.relative_to(REPO)} embeddings={len(embeddings)} reused={reused}")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model if not args.no_embed else None,
        "dimensions": args.dimensions if not args.no_embed else None,
        "selection": "highest-signal Lean declarations by kind/status/graph centrality/frontier markers",
        "corpus_entries": len(corpus),
        "entries": len(embeddings),
        "rebuild": bool(args.rebuild and not args.no_embed),
        "corpus_path": str(args.corpus_out.relative_to(REPO)),
        "embedding_path": str(args.embeddings_out.relative_to(REPO)) if embeddings else None,
        "corpus_sha256": sha256_path(args.corpus_out),
        "embedding_sha256": sha256_path(args.embeddings_out) if embeddings and args.embeddings_out.exists() else None,
        "no_embed": args.no_embed,
    }
    write_json(args.manifest_out, manifest)
    print(f"wrote {args.manifest_out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
