#!/usr/bin/env python3
"""ratify_throughput_solved.py — ONE self-contained command.

CLOSES THE FALSE-POSITIVE VECTOR for the two disjoint serial throughput
halves (codex_proofstate_pilot on /tmp/rung1/_local_ckpt.jsonl +
_vps_ckpt.jsonl). Those halves use the PROVEN prover's *light* `_verify`
(compile-clean + no-`sorry`) and do NOT run `#print axioms` and do NOT
persist proofs ⇒ their output is "solved CANDIDATES", un-auditable
post-hoc. This driver does the FP-protocol-compliant authoritative pass:

  for each row the throughput run marked `stateful_solved=true`:
    re-run it through coherent_rung1.attempt  (the PROVEN codex prover,
    reused VERBATIM) under the AUTHORITATIVE govern_edited verifier
    (#print axioms ⊆ {propext,Classical.choice,Quot.sound}; sorryAx /
    non-STD ⇒ axiom_smuggled, 0-false-ratify HARD; persists proof +
    manifest) ⇒ verdict ∈ {closure, axiom_smuggled, open, unverified}.

  closure                 -> RATIFIED (now auditable; proof persisted)
  axiom_smuggled / open   -> FALSE POSITIVE exposed (throughput _verify
                             was too lax for this row)
  not reproduced in budget -> INCONCLUSIVE (honest; NOT counted ratified)
  solved-id w/o corpus meta-> UNRATIFIABLE (candidate stands, flagged)

Every outcome is routed through a residual_to_lever bridge (the bundle
non-treadmill invariant: every attempt -> typed residual + next lever).

This NEVER touches the running halves; it consumes their checkpoints.
Reuses proven code by IMPORT only (parity-control discipline). Run it
AFTER both halves finish (the watch-cron fires it / surfaces the tally).

Run (fetch VPS ckpt + ratify all throughput solves):
  python3 scripts/public/control/ratify_throughput_solved.py --fetch-vps
Plan only (NO Lean/codex — counts what would be ratified):
  python3 scripts/public/control/ratify_throughput_solved.py --plan
Machine-safe self-test (NO Lean/codex, mocks):
  python3 scripts/public/control/ratify_throughput_solved.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

LOCAL_CKPT = "/tmp/rung1/_local_ckpt.jsonl"
VPS_CKPT_REMOTE = "/tmp/rung1/_vps_ckpt.jsonl"
VPS_CKPT_LOCAL = "/tmp/rung1/_vps_ckpt.fetched.jsonl"
REPORT = "/tmp/rung1/ratify_throughput_report.json"


def die(m: str) -> None:
    print(f"FAIL-LOUD: {m}", file=sys.stderr)
    raise SystemExit(2)


def fetch_vps_ckpt() -> str | None:
    """scp the remote VPS ckpt locally. Non-fatal if unavailable."""
    vps = os.environ.get("ZTARE_VPS_SSH")
    key = os.environ.get("ZTARE_VPS_KEY")
    if not vps or not key:
        print("[warn] ZTARE_VPS_SSH and ZTARE_VPS_KEY are required to fetch VPS checkpoint")
        return None
    cmd = ["scp", "-i",
           key,
           f"{vps}:{VPS_CKPT_REMOTE}", VPS_CKPT_LOCAL]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        if r.returncode == 0 and Path(VPS_CKPT_LOCAL).exists():
            return VPS_CKPT_LOCAL
        print(f"[warn] VPS ckpt fetch rc={r.returncode}: "
              f"{r.stderr.decode(errors='ignore')[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] VPS ckpt fetch failed: {e}")
    return None


def solved_ids(ckpt_paths: list[str]) -> dict:
    """Collect ids the throughput run marked stateful_solved. Returns
    {id: {'src': path, 'secs': float, 'blind': bool}} (last wins)."""
    out: dict = {}
    for p in ckpt_paths:
        if not p or not Path(p).exists():
            continue
        for ln in Path(p).read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            st = d.get("stateful_solved")
            if st is None:
                st = (d.get("stateful") or {}).get("solved")
            if st:
                out[d["id"]] = {
                    "src": Path(p).name,
                    "secs": (d.get("stateful") or {}).get("secs"),
                    "blind": bool(d.get("blind_solved")
                                  or (d.get("blind") or {}).get("solved")),
                }
    return out


def residual_to_lever(verdict: str) -> dict:
    """Non-treadmill bridge: every outcome -> typed residual + lever."""
    return {
        "closure": {
            "residual": "none (authoritatively ratified, proof persisted)",
            "lever": "scale_corpus / promote to GP-233 F-row via "
                     "propose.py (NOT hand-edit)"},
        "axiom_smuggled": {
            "residual": "false_ratify_attempt (throughput _verify too "
                        "lax: accepted a sorryAx/non-STD-axiom proof)",
            "lever": "HARD-FAIL + quarantine row; tighten throughput "
                     "verifier to #print-axioms before any scale claim"},
        "open": {
            "residual": "throughput_verifier_laxity (light _verify said "
                        "solved; authoritative re-run did not close)",
            "lever": "treat throughput tally as candidates-only; the "
                     "authoritative pass is the scoreboard of record"},
        "unverified": {
            "residual": "infra_nondeterminism (govern open_file !ok)",
            "lever": "retry under warm REPL; if persistent, env parity bug"},
        "not_reproduced": {
            "residual": "non_reproduction_in_budget (solvable per "
                        "throughput; authoritative re-run timed out)",
            "lever": "raise authoritative budget OR accept as "
                     "INCONCLUSIVE — never count as ratified"},
        "unratifiable_no_corpus_meta": {
            "residual": "missing sorried_file/target meta in coherent "
                        "corpus (no mathlib_pairs used_lemmas) ⇒ cannot "
                        "authoritatively re-solve",
            "lever": "candidate stands UN-RATIFIED; extend corpus "
                     "builder coverage or hand-trace this row"},
    }.get(verdict, {"residual": f"unmapped:{verdict}",
                    "lever": "classify before any claim"})


def run(ckpt_paths: list[str], model: str, budget: float,
        limit: int) -> dict:
    import coherent_rung1 as cr
    import tool_router as tr
    from src.ztare.formal.lean_persistent import PersistentLean

    solved = solved_ids(ckpt_paths)
    if not solved:
        die("no stateful_solved ids in any ckpt (run not finished?).")
    corpus = {r["id"]: r for r in cr.build_corpus()}
    ids = sorted(solved)
    if limit:
        ids = ids[:limit]

    if not cr.SB.exists():
        die(f"pinned sandbox missing: {cr.SB}")
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)

    rows_out: list = []
    for rid in ids:
        if rid not in corpus:
            v = "unratifiable_no_corpus_meta"
            rows_out.append({"id": rid, "verdict": v,
                             "throughput": solved[rid],
                             "bridge": residual_to_lever(v)})
            print(json.dumps({"id": rid, "verdict": v}))
            continue
        # PROVEN prover reused VERBATIM (cr.attempt arm A = strongest:
        # router hint + up to 3 governed rounds), AUTHORITATIVE verifier.
        res = cr.attempt(L, tr, corpus[rid], "A", model, budget, 30)
        v = res["verdict"]
        if v not in ("closure", "axiom_smuggled", "open", "unverified"):
            v = "not_reproduced"
        rows_out.append({
            "id": rid, "verdict": v,
            "axioms_deps": res.get("axioms_deps"),
            "persisted": res.get("persisted"),
            "verified_by": res.get("verified_by"),
            "calls": res.get("calls"), "secs": res.get("secs"),
            "throughput": solved[rid],
            "bridge": residual_to_lever(v)})
        print(json.dumps({"id": rid, "verdict": v,
                          "persisted": bool(res.get("persisted"))}))
    L.close()

    n = len(rows_out)
    rat = sum(1 for r in rows_out if r["verdict"] == "closure")
    fp = sum(1 for r in rows_out
             if r["verdict"] in ("axiom_smuggled", "open"))
    inc = sum(1 for r in rows_out if r["verdict"] == "not_reproduced")
    unr = sum(1 for r in rows_out
              if r["verdict"] == "unratifiable_no_corpus_meta")
    smug = sum(1 for r in rows_out
               if r["verdict"] == "axiom_smuggled")
    summ = {
        "throughput_stateful_solved_total": len(solved),
        "audited": n,
        "RATIFIED_closure": rat,
        "FALSE_POSITIVE_exposed": fp,
        "  of_which_axiom_smuggled": smug,
        "INCONCLUSIVE_not_reproduced": inc,
        "UNRATIFIABLE_no_corpus_meta": unr,
        "false_ratify_HARD": smug,
        "VERDICT": ("FALSE-POSITIVES PRESENT — throughput tally is "
                    "candidates-only" if fp else
                    "all audited throughput solves authoritatively "
                    "RATIFIED" if rat == n and n else
                    "MIXED — see per-row"),
        "verified_by": "ratify_throughput_solved -> "
                       "coherent_rung1.govern_edited (#print axioms, "
                       "FP-protocol #1, 0-false-ratify HARD)",
        "caveat": "authoritative re-solve (proofs were NOT persisted by "
                  "the throughput run); non-reproduction ⇒ INCONCLUSIVE "
                  "not negative. NOT hand-recorded — route via propose.py.",
        "rows": rows_out,
    }
    Path(REPORT).write_text(json.dumps(summ, indent=1))
    return summ


def plan(ckpt_paths: list[str]) -> int:
    """NO Lean/codex: how many solves are pending authoritative audit."""
    import coherent_rung1 as cr
    solved = solved_ids(ckpt_paths)
    corpus = {r["id"] for r in cr.build_corpus()}
    have = sum(1 for i in solved if i in corpus)
    print(json.dumps({
        "ckpts": [p for p in ckpt_paths if p and Path(p).exists()],
        "stateful_solved_ids": len(solved),
        "ratifiable_in_corpus": have,
        "unratifiable_no_corpus_meta": len(solved) - have,
        "note": "run without --plan (after both halves finish) to "
                "authoritatively ratify via #print axioms"}, indent=1))
    return 0


def _self_test() -> int:
    """Machine-safe: NO Lean, NO codex. Mocks the proven prover + REPL
    (same shape as coherent_rung1's) and asserts the FP triage:
    clean->RATIFIED, sorryAx->FALSE-POSITIVE(HARD), error->FALSE-
    POSITIVE(open); ckpt parsing keeps ONLY stateful_solved; the
    residual_to_lever bridge is total over every verdict."""
    import shutil
    import tempfile

    import coherent_rung1 as cr
    import codex_proofstate_pilot_fast as _PF
    import tool_router as _tr

    # 1) ckpt parser keeps only stateful_solved
    td = Path(tempfile.mkdtemp())
    ck = td / "c.jsonl"
    ck.write_text("\n".join(json.dumps(x) for x in [
        {"id": "A", "stateful_solved": True,
         "stateful": {"solved": True, "secs": 9}, "blind_solved": False},
        {"id": "B", "stateful_solved": False,
         "stateful": {"solved": False}},
        {"id": "C", "stateful": {"solved": True, "secs": 3}}]) + "\n")
    s = solved_ids([str(ck)])
    assert set(s) == {"A", "C"}, s
    assert s["A"]["blind"] is False and s["C"]["secs"] == 3, s

    # 2) bridge is total over every verdict the driver can emit
    for v in ("closure", "axiom_smuggled", "open", "unverified",
              "not_reproduced", "unratifiable_no_corpus_meta", "weird"):
        b = residual_to_lever(v)
        assert b["residual"] and b["lever"], (v, b)

    # 3) authoritative triage via cr.attempt (PROVEN prover mocked;
    #    AUTHORITATIVE govern_edited real-but-mock-REPL) — reused verbatim
    o_codex, o_iso = _PF._codex_hard, _PF._row_iso

    def _fake_row_iso(base, p, rid):
        d = td / re.sub(r"[^A-Za-z0-9_]", "_", str(rid))
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _fake_codex(prompt, model, sandbox, cd, timeout, last_msg):
        assert sandbox == "workspace-write" and cd, (sandbox, cd)
        Path(cd, "mcb_target.lean").write_text(
            "theorem foo : True := by trivial\n")
        return True, "edited"
    _PF._codex_hard = _fake_codex
    _PF._row_iso = _fake_row_iso

    def _mkL(axioms_data, errs=None):
        class _L:
            def open_file(self, path, timeout=600):
                return {"ok": True, "errors": errs or [],
                        "sorries": [],
                        "messages": [{"data": axioms_data}]}
        return _L()
    (td / "src.lean").write_text("theorem foo : True := by\n  sorry\n")
    row = {"id": "m", "sorried_file": str(td / "src.lean"),
           "target_line": 1, "target_name": "foo", "gold_n_steps": 6}
    try:
        ra = cr.attempt(_mkL("'foo' depends on axioms: [propext, "
                             "Classical.choice, Quot.sound]"),
                        _tr, row, "A", "m", 30, 5)
        assert ra["verdict"] == "closure", ra            # RATIFIED
        rb = cr.attempt(_mkL("'foo' depends on axioms: [sorryAx]"),
                        _tr, row, "A", "m", 30, 5)
        assert rb["verdict"] == "axiom_smuggled", rb     # FP HARD
        rc = cr.attempt(_mkL("", errs=[{"data": "type mismatch"}]),
                        _tr, row, "A", "m", 30, 5)
        assert rc["verdict"] == "open", rc               # FP exposed
    finally:
        _PF._codex_hard, _PF._row_iso = o_codex, o_iso
        shutil.rmtree(td, ignore_errors=True)

    print("[self-test] ckpt parser keeps ONLY stateful_solved; "
          "residual_to_lever total over all verdicts; PROVEN prover "
          "reused VERBATIM (workspace-write iso) + AUTHORITATIVE "
          "govern_edited: clean->RATIFIED, sorryAx->FALSE-POSITIVE "
          "(axiom_smuggled HARD), error->FALSE-POSITIVE(open). "
          "NO Lean/codex touched.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-ckpt", default=LOCAL_CKPT)
    ap.add_argument("--vps-ckpt", default=None,
                    help="local path to a fetched VPS ckpt copy")
    ap.add_argument("--fetch-vps", action="store_true",
                    help="scp the remote VPS ckpt before auditing")
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--budget", type=float, default=400.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    ckpts = [a.local_ckpt]
    if a.fetch_vps:
        f = fetch_vps_ckpt()
        if f:
            ckpts.append(f)
    elif a.vps_ckpt:
        ckpts.append(a.vps_ckpt)
    elif Path(VPS_CKPT_LOCAL).exists():
        ckpts.append(VPS_CKPT_LOCAL)
    if a.plan:
        return plan(ckpts)
    out = run(ckpts, a.model, a.budget, a.limit)
    print("\n=== AUTHORITATIVE RATIFICATION OF THROUGHPUT SOLVES")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"},
                     indent=1))
    print(f"\nfull per-row report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
