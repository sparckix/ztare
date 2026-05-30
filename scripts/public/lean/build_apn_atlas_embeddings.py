#!/usr/bin/env python3
"""Build a Gemini embedding atlas over the AlphaProof Nexus (APN) Lean outputs.

Pulls `.lean` files from `google-deepmind/alphaproof-nexus-results/APNOutputs`,
extracts theorem/lemma/def/abbrev declarations, and embeds them in the same
gemini-embedding-001 384-dim space as the NS atlas + Mathlib atlas. Output is
consumed by `src/ztare/research_director/apn_semantic.py` as a second
cross-corpus bridge target (alongside Mathlib).

Why APN matters for NS:
  - LastIterateConvergence.lean (arXiv:1905.10899 Ryu-Yuan-Yin) contains
    monotone-operator iterate-bound machinery directly applicable to NS
    Leray-Hopf sequence analysis (audit 2026-05-26).
  - AdditiveCombinatorics/57.lean is Bohr/Diophantine-adjacent (NS uses
    these patterns in route1).
  - Multi-part decomposition pattern (`.parts.i.lean` / `.parts.ii.lean`)
    is methodology-level — NS Track-B can model its route reductions
    similarly.

Cost: ~9 files × ~30 declarations × ~$0.0001/embed ≈ $0.03 one-shot.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
DEFAULT_EMBEDDINGS = REPO / "analytics" / "public" / "queries" / "lean" / "apn_atlas_embeddings.json"
DEFAULT_CORPUS = REPO / "analytics" / "public" / "queries" / "lean" / "apn_atlas_corpus.json"
DEFAULT_MANIFEST = REPO / "analytics" / "public" / "queries" / "lean" / "apn_atlas_embeddings_manifest.json"

APN_REPO = "google-deepmind/alphaproof-nexus-results"
APN_TREE_ROOT = "APNOutputs"

# Domains to harvest (recurse one level). Tag each file with its domain so
# downstream consumers (workbench, basin enricher) can filter by relevance.
APN_DOMAINS = [
    ("AICollaborator/AdditiveCombinatorics", "additive_combinatorics"),
    ("AICollaborator/AlgebraicGeometry", "algebraic_geometry"),
    ("AICollaborator/Graphs", "graphs"),
    ("AICollaborator/Optimization", "optimization"),
    ("AICollaborator/QuantumOptics", "quantum_optics"),
    ("ErdosProblems", "erdos"),
    ("OEIS", "oeis"),
]

# Lean declaration extraction (theorem/lemma/def/abbrev/structure with optional modifiers)
DECL_PAT = re.compile(
    r"^(?:noncomputable\s+)?(?:private\s+)?(?:protected\s+)?"
    r"(theorem|lemma|def|abbrev|structure|opaque|axiom)\s+([A-Za-z][A-Za-z0-9_'.]*)"
    r"(?:\s*[\(\{:]|.*?\s+:=)",
    re.M,
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


def gh_get_file(api_path: str) -> str | None:
    """Fetch a single file content via gh api; return decoded text or None."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{APN_REPO}/contents/{api_path}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        payload = json.loads(result.stdout)
        if payload.get("encoding") != "base64" or "content" not in payload:
            return None
        return base64.b64decode(payload["content"]).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  gh_get_file({api_path}) failed: {e}")
        return None


def gh_list_dir(api_path: str) -> list[dict]:
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{APN_REPO}/contents/{api_path}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except Exception:
        return []


def harvest_apn_declarations() -> list[dict]:
    """Walk APN_DOMAINS and extract declarations from every .lean file."""
    entries: list[dict] = []
    for domain_subpath, domain_tag in APN_DOMAINS:
        api_path = f"{APN_TREE_ROOT}/{domain_subpath}"
        files = gh_list_dir(api_path)
        print(f"  scanning {domain_subpath}: {len(files)} files")
        for f in files:
            if f.get("type") != "file" or not f.get("name", "").endswith(".lean"):
                continue
            file_api_path = f["path"]
            text = gh_get_file(file_api_path)
            if not text:
                continue
            # Variant tag from filename (parts.i / variants.X / conjecture_X)
            fname = f["name"]
            variant_tag = None
            m = re.search(r"\.parts\.([a-z]+i*)\.", fname)
            if m: variant_tag = f"parts_{m.group(1)}"
            else:
                m = re.search(r"\.variants?\.([a-z_]+)\.", fname)
                if m: variant_tag = f"variant_{m.group(1)}"
                else:
                    m = re.search(r"conjecture_([a-z_]+)", fname)
                    if m: variant_tag = f"conjecture_{m.group(1)}"
            # Extract each declaration with surrounding context (signature only — bounded chars)
            for match in DECL_PAT.finditer(text):
                kind = match.group(1)
                name = match.group(2)
                start = match.start()
                # Take a window around the declaration (up to first := or 800 chars, whichever first)
                end = min(start + 800, len(text))
                snippet = text[start:end].split(":=", 1)[0].strip()
                if len(snippet) < 30:
                    continue
                # Embedding-input text: kind + name + file + domain + variant + snippet
                embed_text = "\n".join([
                    f"AlphaProof Nexus {kind}: {name}",
                    f"Domain: {domain_tag}",
                    f"File: {fname}" + (f"  Variant: {variant_tag}" if variant_tag else ""),
                    f"Signature: {snippet[:1500]}",
                ])
                entries.append({
                    "id": f"apn:{domain_tag}:{fname}:{name}",
                    "name": name,
                    "kind": kind,
                    "domain": domain_tag,
                    "file": fname,
                    "variant_tag": variant_tag,
                    "snippet": snippet[:600],
                    "text": embed_text,
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
        if isinstance(row, dict) and "id" in row
    }


def embed_batch_with_retry(client, model, dims, texts, *, max_retries=5, default_backoff=30.0):
    from google.genai import types
    attempt = 0
    while True:
        try:
            response = client.models.embed_content(
                model=model, contents=texts,
                config=types.EmbedContentConfig(taskType="RETRIEVAL_DOCUMENT", outputDimensionality=dims))
            return [[round(float(v), 6) for v in e.values] for e in response.embeddings]
        except Exception as exc:
            msg = str(exc)
            if not (("429" in msg) or ("RESOURCE_EXHAUSTED" in msg) or ("quota" in msg.lower())) or attempt >= max_retries:
                raise
            backoff = default_backoff
            m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", msg)
            if m:
                try: backoff = float(m.group(1)) + 2.0
                except: pass
            attempt += 1
            print(f"  rate-limit hit (attempt {attempt}/{max_retries}); sleeping {backoff:.1f}s")
            time.sleep(backoff)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-out", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--embeddings-out", type=Path, default=DEFAULT_EMBEDDINGS)
    ap.add_argument("--manifest-out", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--model", default="gemini-embedding-001")
    ap.add_argument("--dimensions", type=int, default=384)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument("--rebuild", action="store_true", help="Ignore cached embeddings.")
    ap.add_argument("--no-embed", action="store_true",
                    help="Harvest + write corpus but skip API embed (dry run).")
    args = ap.parse_args()

    print(f"harvesting APN declarations from {APN_REPO}/{APN_TREE_ROOT}")
    entries = harvest_apn_declarations()
    print(f"  total declarations: {len(entries)}")
    domain_counts: dict[str, int] = {}
    for e in entries:
        domain_counts[e["domain"]] = domain_counts.get(e["domain"], 0) + 1
    print(f"  by domain: {domain_counts}")

    write_json(args.corpus_out, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repo": APN_REPO,
        "size": len(entries),
        "by_domain": domain_counts,
        "entries": entries,
    })
    print(f"  wrote corpus: {args.corpus_out.relative_to(REPO)}")

    if args.no_embed:
        print("(no-embed; harvest + corpus written; skipping API)")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY required for embed")
    from google import genai
    client = genai.Client(api_key=api_key)

    existing = {} if args.rebuild else load_existing_embeddings(args.embeddings_out, args.model, args.dimensions)
    pending = []
    embeddings = []
    reused = 0
    for e in entries:
        vec = existing.get(e["id"])
        if vec is not None:
            embeddings.append({"id": e["id"], "embedding": vec})
            reused += 1
        else:
            pending.append(e)

    print(f"\nembedding {len(pending)} new entries (reused {reused})...")
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start:start + args.batch_size]
        vecs = embed_batch_with_retry(client, args.model, args.dimensions, [e["text"] for e in batch])
        embeddings.extend({"id": e["id"], "embedding": v} for e, v in zip(batch, vecs))
        done = reused + min(start + args.batch_size, len(pending))
        print(f"  embedded {done}/{len(entries)}")
        if args.sleep: time.sleep(args.sleep)

    order = {e["id"]: i for i, e in enumerate(entries)}
    embeddings.sort(key=lambda r: order.get(r["id"], 10**9))
    write_json(args.embeddings_out, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model, "dimensions": args.dimensions,
        "source_repo": APN_REPO,
        "size": len(entries),
        "embeddings": embeddings,
    })
    print(f"  wrote embeddings: {args.embeddings_out.relative_to(REPO)} ({len(embeddings)} entries)")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repo": APN_REPO,
        "model": args.model, "dimensions": args.dimensions,
        "size": len(entries),
        "by_domain": domain_counts,
        "corpus_path": str(args.corpus_out.relative_to(REPO)),
        "corpus_sha256": sha256_path(args.corpus_out),
        "embeddings_path": str(args.embeddings_out.relative_to(REPO)),
        "embeddings_sha256": sha256_path(args.embeddings_out),
    }
    write_json(args.manifest_out, manifest)
    print(f"  wrote manifest: {args.manifest_out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
