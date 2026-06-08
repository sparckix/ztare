#!/usr/bin/env python3
"""Seam + spec embedding atlas — a thin CONSUMER of the canonical embedding engine.

Embeds every `research_areas/seams/**/*.md` (incl. private seams) and
`research_areas/specs/**/*spec*.md` so a capability description can be matched
SEMANTICALLY to the seam/spec that already owns it — the embedding complement to
the STRUCTURAL `seam_interaction_map.md` (citations) and the knowledge graph, and
the mechanized form of AGENTS.md §6n.13 ("EXTEND the canonical home, don't create a
parallel"): before building, query this atlas for the seam that owns the capability.

The embed call / retry / cache / cosine all live in `ztare.common.embeddings` — this
file is ONLY the corpus harvest + config. Query surface:
`src/ztare/research_director/seam_semantic.py`. Cost ≈ $0.02 one-shot, content-hash cached.

Usage:
    python scripts/public/mining/build_seam_atlas_embeddings.py            # build/refresh
    python scripts/public/mining/build_seam_atlas_embeddings.py --no-embed # harvest only (free)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())
sys.path.insert(0, str(REPO / "src"))
from ztare.common.embeddings import build_atlas, content_id  # noqa: E402

SEAM_ROOTS = [REPO / "research_areas/seams", REPO / "research_areas/private/seams"]
SPEC_ROOT = REPO / "research_areas/specs"
OUT_EMB = REPO / "analytics/public/index/seam_atlas_embeddings.json"
OUT_MANIFEST = REPO / "analytics/public/index/seam_atlas_embeddings_manifest.json"


def _title_and_snippet(text: str) -> "tuple[str, str]":
    desc = ""
    m = re.search(r"(?ms)^---\s*\n(.*?)\n---\s*\n", text)
    if m:
        d = re.search(r"(?mi)^description:\s*[\"']?(.+?)[\"']?\s*$", m.group(1))
        if d:
            desc = d.group(1).strip()
        text = text[m.end():]
    h = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    title = h.group(1).strip() if h else ""
    body = re.sub(r"\s+", " ", text).strip()
    return title, (desc + " — " + body[:900] if desc else body[:1000])


def harvest_seams() -> list:
    entries, seen = [], set()
    for kind, root in [("seam", SEAM_ROOTS[0]), ("seam", SEAM_ROOTS[1]), ("spec", SPEC_ROOT)]:
        if not root.exists():
            continue
        for f in sorted(root.rglob("*.md")):
            if kind == "spec" and "spec" not in f.name.lower():
                continue
            if f.name.upper() == "README.md":
                continue
            try:
                raw = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = str(f.relative_to(REPO))
            title, snippet = _title_and_snippet(raw)
            gp = re.search(r"GP-\d+", f.name) or re.search(r"GP-\d+", title or "")
            cid = content_id(rel, raw)
            if cid in seen:
                continue
            seen.add(cid)
            entries.append({"id": cid, "path": rel, "kind": kind,
                            "gp_id": gp.group(0) if gp else None,
                            "title": title or f.stem, "snippet": snippet[:600],
                            "text": f"{rel}\n{title}\n{snippet}"})
    return entries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="gemini-embedding-001")
    ap.add_argument("--dimensions", type=int, default=768)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--no-embed", action="store_true", help="harvest only, no API (free)")
    args = ap.parse_args()

    entries = harvest_seams()
    by_kind: dict = {}
    for e in entries:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    print(f"harvested {len(entries)} seam/spec docs {by_kind}")
    if args.no_embed:
        return 0
    build_atlas(entries, OUT_EMB, OUT_MANIFEST, model=args.model, dimensions=args.dimensions,
                rebuild=args.rebuild,
                extra_manifest={"by_kind": by_kind,
                                "source_roots": ["research_areas/seams", "research_areas/private/seams",
                                                 "research_areas/specs"],
                                "query_surface": "src/ztare/research_director/seam_semantic.py"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
