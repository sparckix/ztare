#!/usr/bin/env python3
"""demodule_probe.py — find the MINIMAL correct de-module transform for
the axiom-audit phase (env-command approach already refuted: the env
itself is a module env, #print axioms blocked there too).

Principle (scientifically defensible): the axiom dependency set of a
kernel-checked proof term is invariant to module *visibility*
(public/private/module are frontend export concerns; the term's axioms
are fixed once it elaborates). So elaborating a DE-MODULED copy yields
the SAME axioms — IFF de-moduling does not introduce NEW elaboration
errors vs the as-is module elaboration. If it does, we must FAIL CLOSED
(verdict `unverified`, never a false closure / never a false open).

Two-phase gate design under test:
  A (validity, leak-tight): open file AS-IS (module) -> errors/sorries
     in true context. (already works.)
  B (axiom audit): open a DE-MODULED copy -> #print axioms; trust ONLY
     if B's elaboration errors ⊆ A's (no NEW errors from de-moduling).

This probe finds which transform makes B both (i) #print-axioms-capable
and (ii) error-equivalent to A, on REAL module corpus rows + synthetic
module known-good. Transforms tried (least invasive first):
  T1: drop a leading `module` header line only
  T2: T1 + strip leading `public `/`private `/`protected ` modifiers
  T3: T2 + strip a leading `prelude` line

Run: python3 scripts/public/control/demodule_probe.py
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))

MOD_ERR = re.compile(r"cannot use .#print axioms. in a .module.", re.I)
OUT = "/tmp/rung1/_demodule_probe.json"


def t1(src: str) -> str:
    out, done = [], False
    for ln in src.splitlines(keepends=True):
        if not done and ln.strip() == "module":
            done = True
            continue
        out.append(ln)
    return "".join(out)


def t2(src: str) -> str:
    s = t1(src)
    return re.sub(r"(?m)^(\s*)(public|private|protected)\s+",
                  r"\1", s)


def t3(src: str) -> str:
    out, dropped = [], False
    for ln in t2(src).splitlines(keepends=True):
        if not dropped and ln.strip() == "prelude":
            dropped = True
            continue
        out.append(ln)
    return "".join(out)


def err_set(of: dict):
    return sorted({str(m.get("data", ""))[:80]
                   for m in (of.get("errors") or [])})


def axioms_of(L, body: str, name: str, tag: str):
    f = Path(f"/tmp/rung1/_dmp_{tag}.lean")
    f.write_text(body + f"\n#print axioms {name}\n")
    of = L.open_file(str(f), 240)
    f.unlink(missing_ok=True)
    raw = "\n".join(str(m.get("data", "")) for m in
                    (of.get("messages") or []))
    return {
        "open_ok": of.get("ok"),
        "module_err": bool(MOD_ERR.search(raw)
                           or any(MOD_ERR.search(str(e))
                                  for e in (of.get("errors") or []))),
        "sorryAx": "sorryax" in raw.lower(),
        "no_axioms": "does not depend on any axioms" in raw.lower(),
        "depends_line": bool(re.search(r"depends on axioms", raw, re.I)),
        "errs": err_set(of),
    }


def main() -> int:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    print(f"[dmp] warming REPL on {cr.SB.name} ...", flush=True)
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    res = {}

    # synthetic MODULE known-good (positive control for axiom phase)
    syn = ("module\nimport Mathlib\n\npublic theorem _dmp_t : True := "
           "by trivial\n")
    for tag, fn in [("syn_T1", t1), ("syn_T2", t2), ("syn_T3", t3)]:
        res[tag] = axioms_of(L, fn(syn), "_dmp_t", tag)
        print(f"  {tag}: {json.dumps(res[tag])[:220]}", flush=True)

    # real corpus rows: AS-IS validity baseline + de-moduled axiom phase
    rows = cr.build_corpus()[:2]
    for row in rows:
        rid = row["id"]
        full = row["target_name"]
        short = full.split(".")[-1]
        src = Path(row["sorried_file"]).read_text(errors="ignore")
        as_is = L.open_file(row["sorried_file"], 300)
        base_errs = err_set(as_is)
        rec = {"id": rid, "as_is_open_ok": as_is.get("ok"),
               "as_is_errs": base_errs,
               "as_is_sorries": len(as_is.get("sorries") or [])}
        for tag, fn in [("T1", t1), ("T2", t2), ("T3", t3)]:
            a = axioms_of(L, fn(src), short, f"{rid}_{tag}")
            new_errs = sorted(set(a["errs"]) - set(base_errs))
            a["new_errs_vs_asis"] = new_errs
            a["error_equiv"] = (len(new_errs) == 0)
            rec[tag] = a
            print(f"  {rid} {tag}: module_err={a['module_err']} "
                  f"sorryAx={a['sorryAx']} err_equiv={a['error_equiv']} "
                  f"new_errs={new_errs[:1]}", flush=True)
        res[f"B_{rid}"] = rec
    L.close()
    Path(OUT).write_text(json.dumps(res, indent=1))

    # pick the least-invasive transform that, on ALL real rows,
    # (i) kills the module error, (ii) shows sorryAx (sorry rows),
    # (iii) introduces NO new elaboration errors vs as-is.
    chosen = None
    for tag in ("T1", "T2", "T3"):
        b = [res[k] for k in res if k.startswith("B_")]
        if b and all((not r[tag]["module_err"]) and r[tag]["sorryAx"]
                     and r[tag]["error_equiv"] for r in b):
            chosen = tag
            break
    print("\n=== DEMODULE-PROBE VERDICT ===")
    if chosen:
        print(f"USE {chosen}: de-modules cleanly — no module error, "
              f"sorryAx detected on the sorried target, and ZERO new "
              f"elaboration errors vs the as-is module open (axiom set "
              f"invariant preserved). Implement two-phase gate: A=as-is "
              f"validity, B={chosen}-demoduled #print axioms, fail-"
              f"closed if B introduces new errors on a given row.")
    else:
        print("NO transform is universally error-equivalent — "
              "de-moduling is unsafe for some rows. Fall back: per-row, "
              "use the least transform that is error-equivalent FOR "
              "THAT ROW; if none, verdict=unverified (fail-closed, "
              "never a false closure/open). Inspect detail.")
    print("detail:", OUT)
    return 0 if chosen else 1


if __name__ == "__main__":
    raise SystemExit(main())
