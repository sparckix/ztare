#!/usr/bin/env python3
"""Build a semantic-retrieval ATLAS from the verified-inference prover corpus.

This is the §8.1 "retrieval-first" step (arch doc): it turns the dead-end `export_training_corpus.py`
output into a LIVE retrieval source for the leaf prompt, so the solver can be shown "here is a
KERNEL-VERIFIED proof of a cosine-similar statement" as a few-shot exemplar.

REUSES the existing `semantic_premise_shelf` DOMAIN-ATLAS plugin — NO shelf code change:
  * atlas file  = {"embeddings": [{"id", "embedding"}]}   (statement embeddings)
  * corpus file = {"entries":    [{"id","name","kind","text","status","tags"}]}
    where `text` is `<statement> :=\n<proof>` so the shelf's hit preview IS the verified exemplar.
Then register {name, atlas_path, corpus_path} under
`policy.operations.semantic_premise_shelf.domain_atlases` and the shelf retrieves it automatically.

ADVISORY ONLY — like every premise-shelf hit, a cited proof is re-verified in-context by the kernel,
so this adds NO soundness surface (it can only change WHICH proof the leaf tries, never whether a
closure is accepted). Lift is to be MEASURED via the reuse-rate telemetry (infer-via-use), not assumed.

Stdlib + the project's own embedder (`mathlib_semantic._embed_query_genai`, needs GOOGLE_API_KEY for a
real build). Run where the corpus + embedder live (the VPS).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
_DEFAULT_CORPUS = REPO / "analytics" / "public" / "leanmill" / "training_corpus" / "prover_corpus.jsonl"
_DEFAULT_OUT = REPO / "analytics" / "public" / "leanmill" / "training_corpus" / "atlas"
_ATLAS_NAME = "verified_corpus"


def _stmt_key(statement: str) -> str:
    """Dedup key — α-normalized statement (reuse the canonical proof_cache normalizer when available so the
    key matches the rest of the system; fall back to a whitespace-collapsed hash)."""
    s = statement or ""
    try:
        from ztare.leanmill.solver.proof_cache import normalize_statement_equiv
        s = normalize_statement_equiv(s)
    except Exception:  # noqa: BLE001 — normalizer optional; whitespace-collapse fallback
        s = " ".join(s.split())
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def build_atlas(corpus_jsonl: "str | Path", out_dir: "str | Path", *, embed_fn,
                max_proof_chars: int = 4000) -> dict:
    """Read the prover corpus, embed each unique statement, write the atlas + corpus files.

    `embed_fn(statement) -> list[float] | None` is injected (real: the genai embedder; test: a stub).
    Skips empty / sorried / un-embeddable rows; dedups by α-statement key. Returns a manifest."""
    corpus_jsonl = Path(corpus_jsonl)
    rows: "list[dict]" = []
    if corpus_jsonl.exists():
        for line in corpus_jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    entries: "list[dict]" = []
    embeds: "list[dict]" = []
    seen: "set[str]" = set()
    skipped = {"empty": 0, "sorry": 0, "dup": 0, "no_embed": 0}
    for r in rows:
        stmt = str(r.get("statement") or "").strip()
        proof = str(r.get("proof") or "").strip()
        if not stmt or not proof:
            skipped["empty"] += 1
            continue
        if "sorry" in proof.lower():
            skipped["sorry"] += 1
            continue
        key = _stmt_key(stmt)
        if key in seen:
            skipped["dup"] += 1
            continue
        vec = embed_fn(stmt)
        if not vec:
            skipped["no_embed"] += 1
            continue
        seen.add(key)
        eid = f"vproof_{key}"
        entries.append({
            "id": eid,
            "name": str(r.get("target") or eid),
            "kind": "verified_proof",
            "text": f"{stmt} :=\n{proof}"[: max_proof_chars],   # the hit preview = the verified exemplar
            "status": "kernel-verified",
            "tags": (["void-novel"] if r.get("void_novel") else []),
            "substrate": str(r.get("substrate") or ""),
        })
        embeds.append({"id": eid, "embedding": list(vec)})
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    atlas_path = out_dir / f"{_ATLAS_NAME}_atlas.json"
    corpus_path = out_dir / f"{_ATLAS_NAME}.json"
    atlas_path.write_text(json.dumps({"embeddings": embeds}, ensure_ascii=True), encoding="utf-8")
    corpus_path.write_text(json.dumps({"entries": entries}, ensure_ascii=True), encoding="utf-8")
    return {
        "atlas_name": _ATLAS_NAME,
        "entries": len(entries),
        "raw_rows": len(rows),
        "skipped": skipped,
        "atlas_path": str(atlas_path.relative_to(REPO) if str(atlas_path).startswith(str(REPO)) else atlas_path),
        "corpus_path": str(corpus_path.relative_to(REPO) if str(corpus_path).startswith(str(REPO)) else corpus_path),
        "registration": {"name": _ATLAS_NAME,
                         "atlas_path": str(atlas_path.relative_to(REPO) if str(atlas_path).startswith(str(REPO)) else atlas_path),
                         "corpus_path": str(corpus_path.relative_to(REPO) if str(corpus_path).startswith(str(REPO)) else corpus_path)},
    }


def _real_embedder():
    from ztare.research_director.mathlib_semantic import _embed_query_genai
    return _embed_query_genai


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        corpus = Path(td) / "prover_corpus.jsonl"
        corpus.write_text("\n".join(json.dumps(r) for r in [
            {"target": "lemX", "statement": "theorem lemX (n:Nat): n+0=n", "proof": "by simp", "void_novel": True},
            {"target": "lemY", "statement": "theorem lemY (n:Nat): n*1=n", "proof": "by simp"},
            {"target": "dupX", "statement": "theorem dupX (m:Nat): m+0=m", "proof": "by simp"},   # α-dup of lemX
            {"target": "bad", "statement": "theorem bad : True", "proof": "by sorry"},             # sorried → skip
            {"target": "empty", "statement": "", "proof": ""},                                      # empty → skip
        ]), encoding="utf-8")
        # deterministic stub embedder: a tiny content-hashed vector (no API)
        def stub(s: str):
            h = hashlib.sha256(s.encode()).digest()
            return [b / 255.0 for b in h[:8]]
        man = build_atlas(corpus, Path(td) / "atlas", embed_fn=stub)
        ok("sorried + empty rows skipped", man["skipped"]["sorry"] == 1 and man["skipped"]["empty"] == 1)
        ok("alpha-dup deduped (lemX vs dupX)", man["skipped"]["dup"] == 1)
        ok("two unique verified entries kept", man["entries"] == 2)
        atlas = json.loads((Path(td) / "atlas" / f"{_ATLAS_NAME}_atlas.json").read_text())
        corp = json.loads((Path(td) / "atlas" / f"{_ATLAS_NAME}.json").read_text())
        ok("atlas embeddings align with corpus entries (same ids)",
           {e["id"] for e in atlas["embeddings"]} == {e["id"] for e in corp["entries"]} and len(atlas["embeddings"]) == 2)
        ok("entry text is the verified EXEMPLAR (statement := proof)",
           all(":=\nby simp" in e["text"] for e in corp["entries"]))
        ok("void-novel tag carried", any("void-novel" in e["tags"] for e in corp["entries"]))
        ok("manifest emits a policy registration block",
           set(man["registration"]) == {"name", "atlas_path", "corpus_path"})
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default=str(_DEFAULT_CORPUS))
    ap.add_argument("--out", default=str(_DEFAULT_OUT))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--allow-legacy-diagnostic", action="store_true")
    ns = ap.parse_args(argv)
    if ns.selftest:
        return _selftest()
    from ztare.leanmill.training_corpus_contract import validate_training_corpus_directory
    validate_training_corpus_directory(
        Path(ns.corpus).parent,
        required_files=(Path(ns.corpus).name,),
        allow_legacy_diagnostic=ns.allow_legacy_diagnostic,
    )
    man = build_atlas(ns.corpus, ns.out, embed_fn=_real_embedder())
    print(json.dumps(man, indent=2))
    print("\nRegister under policy.operations.semantic_premise_shelf.domain_atlases:")
    print(json.dumps(man["registration"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
