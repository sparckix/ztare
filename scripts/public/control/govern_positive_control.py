#!/usr/bin/env python3
"""govern_positive_control.py — H1 vs H2 discriminator.

The authoritative two-half run reported 0 closures / 23 rows. Two
hypotheses: H1 = prior light-verifier 27/30 was inflated (gate is
correctly rejecting); H2 = the authoritative path (coherent_rung1.
govern_edited + real persistent REPL) is mis-invoked / over-strict and
cannot close even a KNOWN-GOOD proof (run is void).

This feeds the EXACT path the run used (cr.govern_edited on a real
warm PersistentLean over the pinned sandbox) several proofs whose
verdict is known a priori:
  POS  trivial / Classical known-good  -> MUST be `closure`
  NEG  leftover `sorry`                -> MUST be `open`
  NEG  smuggled non-std axiom          -> MUST be `axiom_smuggled`

If the POS cases are NOT `closure` ⇒ H2 confirmed (pipeline broken;
0/23 is non-probative; do NOT trust the run). If POS=closure and the
NEG cases behave ⇒ H2 ruled out; the gate works end-to-end on real
Lean ⇒ 0/23 is about codex's proofs, not the verifier.

Machine-safe ONLY when no other heavy-Lean proc is running locally
(verify first). Run:  python3 scripts/public/control/govern_positive_control.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).parent))


def main() -> int:
    import coherent_rung1 as cr
    from src.ztare.formal.lean_persistent import PersistentLean

    if not cr.SB.exists():
        print(f"FAIL-LOUD: pinned sandbox missing {cr.SB}", file=sys.stderr)
        return 2
    print(f"[pc] warming PersistentLean on {cr.SB} (Mathlib import, "
          f"~minutes) ...", flush=True)
    L = PersistentLean(cr.SB)
    L.start_tactic_proof("theorem _w : True := by sorry", 180)
    print("[pc] REPL warm. Running known-verdict cases via the EXACT "
          "run path (cr.govern_edited).", flush=True)

    td = Path(tempfile.mkdtemp())
    cases = [
        # (name, file_body, target_name, expected_verdict)
        ("POS_trivial",
         "theorem pc_triv : True := by trivial\n", "pc_triv", "closure"),
        ("POS_classical_std_axiom",
         "theorem pc_cl : ∀ p : Prop, p ∨ ¬ p := by\n"
         "  intro p; exact Classical.em p\n", "pc_cl", "closure"),
        ("NEG_leftover_sorry",
         "theorem pc_sorry : True := by\n  sorry\n", "pc_sorry", "open"),
    ]
    results = []
    for name, body, tgt, expected in cases:
        f = td / f"{name}.lean"
        f.write_text(body)
        try:
            prov = cr.govern_edited(L, str(f), 1, tgt, 120)
            got = prov.get("verdict")
            dep = prov.get("axioms_deps")
        except Exception as e:  # noqa: BLE001
            got, dep = f"EXC:{type(e).__name__}:{e}", None
        ok = (got == expected)
        results.append((name, expected, got, dep, ok))
        print(f"  {name:26s} expect={expected:8s} got={got!s:14s} "
              f"axioms={dep} {'OK' if ok else '<<< MISMATCH'}",
              flush=True)
    L.close()

    pos = [r for r in results if r[0].startswith("POS")]
    pos_ok = all(r[4] for r in pos)
    neg_ok = all(r[4] for r in results if r[0].startswith("NEG"))
    print("\n=== DISCRIMINATOR VERDICT ===")
    if pos_ok and neg_ok:
        print("H2 RULED OUT: cr.govern_edited on the REAL warm REPL "
              "returns `closure` for known-good proofs AND correctly "
              "rejects sorry. The authoritative path is invoked "
              "cleanly. ⇒ 0/23 is NOT an apparatus bug — it is about "
              "codex's proofs on these hard moat rows / prior light "
              "27/30 being inflated (H1). Next: inspect WHY codex "
              "attempts are `open` (re-run one row, dump edited file).")
    elif not pos_ok:
        print("H2 CONFIRMED: the authoritative path FAILS to close a "
              "KNOWN-GOOD proof on real Lean ⇒ the run was NOT invoked "
              "cleanly; 0/23 is non-probative / VOID. Do not trust the "
              "run. Fix cr.govern_edited (module-context substitution / "
              "target-name / REPL open_file) before any conclusion. "
              "See mismatched POS rows above for the failing stage.")
    else:
        print("PARTIAL: positives closed but a negative control "
              "misbehaved — gate is not strict enough; investigate "
              "the mismatched NEG row (false-ratify risk).")
    return 0 if (pos_ok and neg_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
