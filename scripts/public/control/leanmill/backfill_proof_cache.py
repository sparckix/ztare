#!/usr/bin/env python3
"""Backfill the proof cache from the closure-certificate ledger, keyed on the canonical `Expr.hash`.

THE cross-run-reuse migration (2026-06-24). Every kernel-verified closure lands in the cert ledger
(`adhoc_closure_certificates.jsonl`) with its `recompilable_probe` + `proof_text`, but the historical proof CACHE
(`solver_lane_proof_cache.jsonl`, the "cite don't re-derive" store) only held closures from the dag-search deposit
path — so native-pre-filter / warm-direct closures (the APR `waterfallDistribution_*` lemmas) were NEVER cacheable
and got re-derived every run. Going forward solve_adhoc deposits at its single closure chokepoint; this migrates the
EXISTING ledger so prior work is immediately reusable too.

Keyed on `repl_compile.canonical_type_hash_via_repl` — the kernel `Expr.hash` of the target's de-Bruijn TYPE, which
is α-/∀-fronting-invariant (the equivalences no text key can collapse). Idempotent: `ProofCache.put` dedups, so a
re-run is cheap. SOUND: a cache hit is always re-verified in-context before it can close anything, so an over-broad
key is a re-verify miss, never a false closure — this only curates retrieval keys, never the kernel verdict.

  PYTHONPATH=src python scripts/public/control/leanmill/backfill_proof_cache.py [--since ISO] [--limit N] [--lean-root DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

CERTS = REPO / "analytics/public/queries/adhoc_closure_certificates.jsonl"
CACHE = REPO / "analytics/public/queries/solver_lane_proof_cache.jsonl"


def backfill(lean_root: str, since: str = "", limit: int = 0) -> dict:
    from ztare.formal.repl_compile import canonical_type_hash_via_repl
    from ztare.leanmill.solver.proof_cache import ProofCache

    pc = ProofCache(CACHE)
    rows = [l for l in CERTS.read_text(encoding="utf-8").splitlines() if l.strip()] if CERTS.exists() else []
    seen_keys: set = set()
    deposited = no_hash = skipped_dup = scanned = 0
    for line in rows:
        try:
            c = json.loads(line)
        except ValueError:
            continue
        if c.get("outcome") != "closed":
            continue
        if since and str(c.get("ts") or "") < since:
            continue
        probe, proof, tgt = (c.get("recompilable_probe") or ""), (c.get("proof_text") or ""), (c.get("target") or "")
        if not (probe.strip() and proof.strip() and tgt):
            continue
        scanned += 1
        hk = canonical_type_hash_via_repl(probe, tgt, lean_root)
        if not hk:
            no_hash += 1
            continue
        if hk in seen_keys:           # an earlier cert already banked this exact type ⇒ first-verified-wins
            skipped_dup += 1
            continue
        seen_keys.add(hk)
        if pc.put(probe, proof, source=f"backfill:{tgt}", key=hk):
            deposited += 1
        else:
            skipped_dup += 1
        if limit and deposited >= limit:
            break
    return {"scanned": scanned, "deposited": deposited, "no_hash": no_hash,
            "skipped_dup": skipped_dup, "cache_size": len(pc)}


def compact() -> dict:
    """MECHANICAL dedup + rewrite of the on-disk cache — no LLM, no per-row REPL. The append-only ledger
    accumulates redundant rows two ways: (1) MIGRATION TWINS — a backfill added an `Expr.hash`-keyed row for a
    statement that already had a legacy text-keyed row; (2) legacy α-VARIANTS — the old exact text key was
    binder-name-sensitive, so `∀ x` and `∀ y` got separate rows (the canonical equiv key collapses them). Re-key
    every row through `_key_for` (the SAME canonical normalizer `get` uses — α-/whitespace-collapsing), keep
    `Expr.hash` (`H:`) rows as the canonical winners, and DROP any row whose canonical identity is already
    covered (by its `H:` key OR its equiv text key). First-verified-wins. Atomic rewrite via a temp file + a
    `.bak`. SOUND: identity is the SAME key the cache reads by, and every hit is re-verified in-context anyway —
    compaction only removes provably-redundant retrieval rows, never a proof the kernel hasn't re-checked."""
    from ztare.leanmill.solver.proof_cache import _key_for
    if not CACHE.exists():
        return {"before_rows": 0, "after_rows": 0, "dropped": 0}
    rows = []
    for line in CACHE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    # Expr-keyed rows FIRST so a canonical `Expr.hash` entry wins over a legacy text twin.
    rows.sort(key=lambda r: 0 if str(r.get("key") or "").startswith("H:") else 1)
    out: "dict[str, dict]" = {}
    seen_text: set = set()
    dropped = 0
    for r in rows:
        stmt = r.get("statement") or ""
        text_key = _key_for(stmt)
        primary = r.get("key") if str(r.get("key") or "").startswith("H:") else text_key
        if not primary:
            continue
        if primary in out or (text_key and text_key in seen_text):
            dropped += 1                       # canonical identity already banked ⇒ redundant row
            continue
        r2 = dict(r); r2["key"] = primary; r2["text_key"] = text_key
        out[primary] = r2
        if text_key:
            seen_text.add(text_key)
    CACHE.with_suffix(".jsonl.bak").write_text(CACHE.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = CACHE.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out.values()), encoding="utf-8")
    tmp.replace(CACHE)
    return {"before_rows": len(rows), "after_rows": len(out), "dropped": dropped,
            "expr_keyed": sum(1 for r in out.values() if str(r.get("key") or "").startswith("H:"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default="", help="only certs with ts >= this ISO timestamp")
    ap.add_argument("--limit", type=int, default=0, help="stop after N deposits (0 = all)")
    ap.add_argument("--lean-root", default=str(REPO / "ztare_proofs"), help="lake project for the warm REPL")
    ap.add_argument("--compact", action="store_true",
                    help="mechanically dedup + rewrite the on-disk cache (no REPL). Do NOT run during a live solve.")
    args = ap.parse_args(argv)
    if args.compact:
        print(json.dumps(compact(), indent=2))
        return 0
    m = backfill(args.lean_root, since=args.since, limit=args.limit)
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
