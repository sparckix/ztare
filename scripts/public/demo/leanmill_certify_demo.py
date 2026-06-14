#!/usr/bin/env python3
"""LeanMill — one-command demo: a plain-English rule → a kernel-CERTIFIED guarantee, and a silently-laundered
version CAUGHT. Showcases the three engines in one run:

  1. AGENT/spec   — a compliance rule in English + its Lean 4 formalization.
  2. SMT (z3)     — searches the boundary: the EXACT value where a faithful vs an off-by-one rule disagree
                    (the adversarial case a human reviewer misses).
  3. Lean kernel  — RATIFIES: the faithful formalization decides every labelled case correctly (an auditable
                    certificate); the laundered one misclassifies the boundary case and is REJECTED.

The point: the verdict isn't the differentiator (a strong model is often as accurate) — the auditable KERNEL CERTIFICATE
is. You can stand behind a kernel proof; you can't behind an LLM opinion.

Run:  make leanmill-certify-demo      (or: ./venv/bin/python scripts/public/demo/leanmill_certify_demo.py)
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

RULE = "Basel III: a bank is ADEQUATELY CAPITALIZED iff its CET1 ratio is at least the 4.50% minimum (cet1Bp >= 450)."
FAITHFUL = ("structure Bank where\n  cet1Bp : Nat\n\n"
            "abbrev adequate (b : Bank) : Prop := 450 ≤ b.cet1Bp\n")
LAUNDERED = ("structure Bank where\n  cet1Bp : Nat\n\n"
             "abbrev adequate (b : Bank) : Prop := 449 ≤ b.cet1Bp   -- off-by-one: admits a 4.49% bank\n")
BATTERY = [("⟨460⟩", True), ("⟨450⟩", True), ("⟨300⟩", False)]   # boundary case (449) is added by z3 below


def _hr(t=""):
    print("\n" + "─" * 78 + (f"\n {t}" if t else ""), flush=True)


def main() -> int:
    print("\n  LeanMill — from English rule to kernel certificate", flush=True)
    _hr("1. THE RULE (natural language) + its Lean formalization")
    print(f"  RULE: {RULE}\n  LEAN: abbrev adequate (b : Bank) : Prop := 450 ≤ b.cet1Bp", flush=True)

    _hr("2. SMT (z3) — find the adversarial boundary a reviewer would miss")
    import z3
    x = z3.Int("cet1Bp")
    faithful_pred, laundered_pred = (450 <= x), (449 <= x)
    s = z3.Solver(); s.add(faithful_pred != laundered_pred); s.add(x >= 0)
    boundary = s.model()[x].as_long() if s.check() == z3.sat else None
    print(f"  z3: ∃ cet1Bp where faithful(450≤) and laundered(449≤) DISAGREE  →  cet1Bp = {boundary}", flush=True)
    print(f"  i.e. a bank at {boundary}bp (4.49%) is INADEQUATE by the rule but the laundered code would PASS it.", flush=True)

    _hr("3. Lean KERNEL — ratify the faithful rule, reject the laundered one")
    from ztare.leanmill.solver.autoformalize import default_instance_battery
    lean_root = REPO / "ztare_proofs"
    cases = BATTERY + [(f"⟨{boundary}⟩", False)]   # the z3-found boundary case, ground-truth label = inadequate
    print(f"  battery (human-labelled, incl. the z3 boundary case ⟨{boundary}⟩→inadequate): {cases}", flush=True)
    print("  …compiling against the Lean kernel (cold Mathlib, ~1-2 min)…", flush=True)
    faithful_ok = default_instance_battery(FAITHFUL, "adequate", cases, sandbox=lean_root)
    laundered_ok = default_instance_battery(LAUNDERED, "adequate", cases, sandbox=lean_root)

    _hr("RESULT")
    print(f"  FAITHFUL  formalization → kernel CERTIFICATE: {'✅ ADMITTED (decides every case correctly)' if faithful_ok else '❌'}", flush=True)
    print(f"  LAUNDERED formalization → {'❌ REJECTED — kernel caught the off-by-one at the boundary' if not laundered_ok else '⚠️ ADMITTED (unexpected)'}", flush=True)
    ok = (faithful_ok is True) and (laundered_ok is False)
    _hr()
    if ok:
        print("  ✅ The kernel certifies the faithful rule and catches the laundering — an AUDITABLE guarantee,\n"
              "     not an LLM opinion. That certificate is the product.", flush=True)
    else:
        print("  ⚠️  Unexpected result — see above (the kernel verdict is still the ground truth).", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
