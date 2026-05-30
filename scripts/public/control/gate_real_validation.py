#!/usr/bin/env python3
"""gate_real_validation.py — REAL-substrate validation of the fixed
authoritative gate (authoritative_axioms.govern), on the actual
persistent REPL over module-headered Lean. Mock self-tests pass but
are insufficient (the bare-file discriminator passed while the gate
was systematically broken — see memory positive-control-must-match-
real-substrate). This exercises the exact failure surface:

  POS_trivial_module   : module file, `by trivial`   -> MUST closure
  POS_classical_module : module file, Classical.em    -> MUST closure
                          (Classical.choice ⊆ STD)
  NEG_real_sorried_row : a REAL corpus sorried file    -> MUST open
                          (no false closure, no wrong unverified)
  NEG_sorry_smuggle    : module file, target proved via a `sorry`ed
                          `have`                       -> MUST
                          axiom_smuggled (sorryAx, HARD 0-false-ratify)

PASS only if all four hit their required verdict on real Lean.
Machine-safe with no other local heavy-Lean proc.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    import authoritative_axioms as _AX
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    print(f"[grv] warming REPL on {cr.SB.name} ...", flush=True)
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)

    row = cr.build_corpus()[1]   # a real module-headered corpus row
    real_sorried = Path(row["sorried_file"]).read_text(errors="ignore")

    cases = [
        ("POS_trivial_module",
         "module\nimport Mathlib\n\npublic theorem _grv_t : True := "
         "by trivial\n", 4, "_grv_t", "closure"),
        ("POS_classical_module",
         "module\nimport Mathlib\n\npublic theorem _grv_c : "
         "∀ p : Prop, p ∨ ¬ p := by\n  intro p\n  exact Classical.em "
         "p\n", 4, "_grv_c", "closure"),
        ("NEG_real_sorried_row",
         real_sorried, row["target_line"],
         row["target_name"], "open"),
        # smuggle FAR from target: a sorried helper + padding so Phase
        # A's ±3 sorry window MISSES it ⇒ only Phase B's #print axioms
        # can catch the transitive sorryAx ⇒ exercises the HARD path.
        ("NEG_sorry_smuggle",
         "module\nimport Mathlib\n\n"
         "theorem _grv_helper : (1 : Nat) = 1 := by sorry\n"
         "-- pad a\n-- pad b\n-- pad c\n-- pad d\n-- pad e\n"
         "theorem _grv_s : (1 : Nat) = 1 := _grv_helper\n",
         10, "_grv_s", "axiom_smuggled"),
    ]
    results = []
    for name, text, tline, tname, expect in cases:
        prov = _AX.govern(L, text, tline, tname, 200,
                          persist=(expect == "closure"))
        got = prov.get("verdict")
        ok = (got == expect)
        results.append((name, expect, got, prov.get("reason"),
                        prov.get("axioms_deps"),
                        bool(prov.get("persisted")), ok))
        print(f"  {name:22s} expect={expect:14s} got={got!s:14s} "
              f"reason={prov.get('reason')} axioms={prov.get('axioms_deps')} "
              f"persisted={bool(prov.get('persisted'))} "
              f"{'OK' if ok else '<<< MISMATCH'}", flush=True)
    L.close()

    allok = all(r[6] for r in results)
    print("\n=== GATE REAL-SUBSTRATE VALIDATION ===")
    print(json.dumps({"all_pass": allok,
                       "results": [{"case": r[0], "expect": r[1],
                                    "got": r[2], "ok": r[6]}
                                   for r in results]}, indent=1))
    if allok:
        print("PASS: the fixed gate, on REAL module-headered Lean via "
              "the real REPL, CLOSES known-good proofs, REJECTS a real "
              "sorried row (no false closure), and HARD-FAILS a "
              "sorry-smuggle. The #print-axioms-in-module bug is fixed "
              "and the gate discriminates on the real substrate. Reruns "
              "are now scientifically meaningful.")
    else:
        print("FAIL: a required verdict was not met on real Lean — do "
              "NOT rerun; inspect the mismatched case above.")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
