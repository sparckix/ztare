#!/usr/bin/env python3
"""authoritative_two_half.py — ONE self-contained command.

The throughput run, RESTARTED with #print axioms baked in from row 1
(operator-directed 2026-05-18). Verifier-only delta off the proven
27/30 substrate: the prover PIECES are reused VERBATIM by import
(coherent_rung1.attempt -> _PP.STATE_PROMPT / _PF._codex_hard
workspace-write iso / _PF._row_iso); the ONLY change vs the light
throughput run is the verdict gate -> AUTHORITATIVE govern_edited
(#print axioms ⊆ {propext,Classical.choice,Quot.sound}; persist;
sorryAx/non-STD ⇒ axiom_smuggled, 0-false-ratify HARD).

NO REGRESSION (honest): #print axioms is strictly-additive verification
— a genuinely-clean proof still passes; the gate can only reclassify a
row that was actually leaking ⇒ catches a false positive (intended),
never invalidates a real closure.

Disjoint two halves, checkpoint + resume (machine-safe pattern: ONE
warm PersistentLean per machine, serialized behind coherent_rung1's
_REPL_LOCK; codex is remote I/O so bounded-parallel is safe — this is
the validated fast pattern, NOT the parallel-heavy-Lean crash):
  --half local  -> corpus[0::2]  ckpt /tmp/rung1/_local_gov_ckpt.jsonl
  --half vps    -> corpus[1::2]  ckpt /tmp/rung1/_vps_gov_ckpt.jsonl

Run a half:  python3 .../authoritative_two_half.py --half local
Resume:      (same command — done rows skipped from ckpt)
Tally:       python3 .../authoritative_two_half.py --verify-only
Self-test:   python3 .../authoritative_two_half.py --self-test  (NO Lean/codex)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

CKPT = {"local": "/tmp/rung1/_local_gov_ckpt.jsonl",
        "vps": "/tmp/rung1/_vps_gov_ckpt.jsonl"}
SUMMARY = "/tmp/rung1/authoritative_two_half_summary.json"


def die(m: str) -> None:
    print(f"FAIL-LOUD: {m}", file=sys.stderr)
    raise SystemExit(2)


def _load_ckpt(p: str) -> dict:
    d: dict = {}
    if Path(p).exists():
        for ln in Path(p).read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
                d[r["id"]] = r
            except Exception:
                pass
    return d


def _tally(recs: list) -> dict:
    from ratify_throughput_solved import residual_to_lever
    n = len(recs)
    clo = sum(1 for r in recs if r["verdict"] == "closure")
    smug = sum(1 for r in recs if r["verdict"] == "axiom_smuggled")
    opn = sum(1 for r in recs if r["verdict"] in ("open", "unverified"))
    return {
        "audited": n,
        "RATIFIED_closure": clo,
        "axiom_smuggled_FALSE_RATIFY_HARD": smug,
        "open_or_unverified": opn,
        "false_ratify_HARD": smug,
        "VERDICT": ("FALSE-RATIFY PRESENT — HARD FAIL" if smug else
                    f"{clo}/{n} authoritatively RATIFIED closures"
                    if n else "no rows yet"),
        "verified_by": "authoritative_two_half -> "
                        "coherent_rung1.govern_edited (#print axioms, "
                        "FP-protocol #1, 0-false-ratify HARD)",
        "caveat": "NOT hand-recorded — route any GP-233/F-row via "
                  "propose.py. non-reproduction ⇒ open (honest), not "
                  "a negative.",
        "bridge_by_verdict": {v: residual_to_lever(v) for v in
                              sorted({r["verdict"] for r in recs})}
        if recs else {},
    }


def run(half: str, model: str, budget: float, workers: int,
        limit: int) -> dict:
    import coherent_rung1 as cr
    import tool_router as tr
    from src.ztare.formal.lean_persistent import PersistentLean

    rows = cr.build_corpus()
    rows = rows[0::2] if half == "local" else rows[1::2]
    if limit:
        rows = rows[:limit]
    ckpt = CKPT[half]
    Path(ckpt).parent.mkdir(parents=True, exist_ok=True)
    done = _load_ckpt(ckpt)
    todo = [r for r in rows if r["id"] not in done]
    print(f"[{half}] {len(todo)} to run ({len(done)} resumed) "
          f"of {len(rows)} workers={workers} budget={budget}")
    if not cr.SB.exists():
        die(f"pinned sandbox missing: {cr.SB}")
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    fh = open(ckpt, "a")

    def one(row):
        # PROVEN prover reused VERBATIM (arm A, strongest) +
        # AUTHORITATIVE govern_edited. REPL is serialized inside
        # govern_edited via coherent_rung1._REPL_LOCK.
        res = cr.attempt(L, tr, row, "A", model, budget, 30)
        return {"id": row["id"], "gold_steps": row.get("gold_n_steps"),
                "verdict": res["verdict"],
                "axioms_deps": res.get("axioms_deps"),
                "persisted": res.get("persisted"),
                "verified_by": res.get("verified_by"),
                "calls": res.get("calls"), "secs": res.get("secs")}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(one, r): r["id"] for r in todo}
        for f in as_completed(futs):
            rec = f.result()
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            done[rec["id"]] = rec
            print(json.dumps({"id": rec["id"],
                              "verdict": rec["verdict"],
                              "persisted": bool(rec["persisted"])}))
    fh.close()
    L.close()
    out = _tally(list(done.values()))
    out["half"] = half
    Path(SUMMARY.replace(".json", f"_{half}.json")).write_text(
        json.dumps(out, indent=1))
    return out


def _self_test() -> int:
    """Machine-safe: NO Lean, NO codex. Reuses coherent_rung1's
    verbatim prover (mocked) + AUTHORITATIVE govern_edited (mock REPL);
    asserts clean->closure, sorryAx->axiom_smuggled(HARD), error->open,
    ckpt-resume skip, and tally false-ratify-HARD."""
    import authoritative_axioms as _AX
    _AX.isolate_selftest_ledger()   # never pollute the real ledger
    import re
    import shutil
    import tempfile

    import coherent_rung1 as cr
    import codex_proofstate_pilot_fast as _PF
    import tool_router as _tr

    # ckpt-resume skip
    td = Path(tempfile.mkdtemp())
    ck = td / "c.jsonl"
    ck.write_text(json.dumps({"id": "X", "verdict": "closure"}) + "\n")
    d = _load_ckpt(str(ck))
    assert set(d) == {"X"}, d
    assert [r for r in [{"id": "X"}, {"id": "Y"}]
            if r["id"] not in d] == [{"id": "Y"}]

    # tally: any axiom_smuggled ⇒ HARD
    t = _tally([{"id": "a", "verdict": "closure"},
                {"id": "b", "verdict": "axiom_smuggled"}])
    assert t["false_ratify_HARD"] == 1 and "HARD FAIL" in t["VERDICT"], t
    t2 = _tally([{"id": "a", "verdict": "closure"},
                 {"id": "b", "verdict": "closure"}])
    assert t2["RATIFIED_closure"] == 2 and "RATIFIED" in t2["VERDICT"]

    # verbatim prover (mock) + authoritative govern triage
    o_codex, o_iso = _PF._codex_hard, _PF._row_iso

    def _fri(base, p, rid):
        q = td / re.sub(r"[^A-Za-z0-9_]", "_", str(rid))
        q.mkdir(parents=True, exist_ok=True)
        return q

    def _fc(prompt, model, sandbox, cd, timeout, last_msg):
        assert sandbox == "workspace-write" and cd, (sandbox, cd)
        Path(cd, "mcb_target.lean").write_text(
            "theorem foo : True := by trivial\n")
        return True, "edited"
    _PF._codex_hard, _PF._row_iso = _fc, _fri

    def _mkL(ax, errs=None):
        class _L:
            def open_file(self, path, timeout=600):
                return {"ok": True, "errors": errs or [], "sorries": [],
                        "messages": [{"data": ax}]}
        return _L()
    (td / "s.lean").write_text("theorem foo : True := by\n  sorry\n")
    row = {"id": "m", "sorried_file": str(td / "s.lean"),
           "target_line": 1, "target_name": "foo", "gold_n_steps": 6}
    try:
        a = cr.attempt(_mkL("'foo' depends on axioms: [propext, "
                            "Classical.choice, Quot.sound]"),
                       _tr, row, "A", "m", 30, 5)
        assert a["verdict"] == "closure", a
        b = cr.attempt(_mkL("'foo' depends on axioms: [sorryAx]"),
                       _tr, row, "A", "m", 30, 5)
        assert b["verdict"] == "axiom_smuggled", b
        c = cr.attempt(_mkL("", errs=[{"data": "type mismatch"}]),
                       _tr, row, "A", "m", 30, 5)
        assert c["verdict"] == "open", c
    finally:
        _PF._codex_hard, _PF._row_iso = o_codex, o_iso
        shutil.rmtree(td, ignore_errors=True)

    print("[self-test] ckpt-resume skip OK; tally false-ratify HARD OK; "
          "PROVEN prover reused VERBATIM (workspace-write iso) + "
          "AUTHORITATIVE govern_edited: clean->closure(persist), "
          "sorryAx->axiom_smuggled(HARD), error->open. NO Lean/codex.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--half", choices=["local", "vps"])
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=float, default=400.0)
    ap.add_argument("--workers", type=int, default=3,
                    help="parallel codex (I/O-bound, safe); the warm "
                         "REPL is serialized behind a lock regardless")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if a.verify_only:
        recs = []
        for p in CKPT.values():
            recs += list(_load_ckpt(p).values())
        print(json.dumps(_tally(recs), indent=1))
        return 0
    if not a.half:
        die("--half {local,vps} required (disjoint two-machine run).")
    out = run(a.half, a.model, a.budget, a.workers, a.limit)
    print("\n=== AUTHORITATIVE THROUGHPUT (#print axioms from row 1)")
    print(json.dumps({k: v for k, v in out.items()
                      if k != "bridge_by_verdict"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
