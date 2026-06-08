#!/usr/bin/env python3
"""Test the proof-state partial-progress signal (the GP-187 middle-layer gradient).

Two layers:
  (1) PARSER unit tests on captured Lean output — no toolchain needed; asserts the
      gradient is monotone in open-goal count and that error classes route.
  (2) LIVE compile test (if lake is present) — compile a CLOSED proof, a PARTIAL
      proof (one goal left), and a BROKEN proof; assert goals_remaining and
      error_class come out 0 / >=1 / failed respectively. This is the end-to-end
      proof that the signal is real, not just a regex over fixtures.

One command:  python test_proof_state.py          (parser + live if lake)
              python test_proof_state.py --parser  (parser only)
Verification line printed at the end.
"""
from __future__ import annotations
import sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from ztare.leanmill.solver.proof_state import proof_state_signal  # noqa: E402

# ── (1) captured-output fixtures (real Lean message shapes) ────────────────
CLEAN = ("", 0)
ONE_GOAL = ("""Probe.lean:5:2: error: unsolved goals
case h
n : ℕ
⊢ n + 0 = n
""", 1)
THREE_GOALS = ("""Probe.lean:5:2: error: unsolved goals
case a
⊢ P x
case b
⊢ Q y
case c
⊢ R z
""", 1)
TACTIC_FAILED = ("Probe.lean:5:2: error: linarith failed to find a contradiction\n", 1)
UNKNOWN_ID = ("Probe.lean:3:7: error: unknown identifier 'foo_lemma'\n", 1)
TYPE_MISMATCH = ("Probe.lean:5:2: error: type mismatch\n  h : a = b\nhas type ...\n", 1)


def test_parser() -> int:
    fails = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    s_clean = proof_state_signal(0, CLEAN[0])
    check("clean → goals=0, progress=1.0, class=clean",
          s_clean["goals_remaining"] == 0 and s_clean["progress"] == 1.0
          and s_clean["error_class"] == "clean")

    s1 = proof_state_signal(1, ONE_GOAL[0])
    check("one open goal → class=unsolved_goals, goals=1",
          s1["error_class"] == "unsolved_goals" and s1["goals_remaining"] == 1)

    s3 = proof_state_signal(1, THREE_GOALS[0])
    check("three open goals → goals=3", s3["goals_remaining"] == 3)

    # THE GRADIENT: fewer open goals must score higher (what a DAG climbs).
    check("gradient monotone: progress(1 goal) > progress(3 goals)",
          s1["progress"] > s3["progress"])
    check("gradient monotone: progress(partial) > progress(broken-name)",
          s1["progress"] > proof_state_signal(1, UNKNOWN_ID[0])["progress"])

    check("tactic_failed routes", proof_state_signal(1, TACTIC_FAILED[0])["error_class"] == "tactic_failed")
    check("unknown_identifier routes", proof_state_signal(1, UNKNOWN_ID[0])["error_class"] == "unknown_identifier")
    check("type_mismatch routes", proof_state_signal(1, TYPE_MISMATCH[0])["error_class"] == "type_mismatch")
    return 1 if fails else 0


# ── (2) live compile (only if lake resolvable) ─────────────────────────────
def _lean_root() -> Path | None:
    for c in (REPO / "ztare_proofs", REPO / "lean", REPO):
        if (c / "lakefile.lean").exists() or (c / "lakefile.toml").exists():
            return c
    return None


def test_live() -> int:
    try:
        from ztare.gates.lean_compile_primitives import ensure_elan_on_path, run_lake_compile
    except Exception as e:
        print(f"  [SKIP] live: import failed {e!r}"); return 0
    ensure_elan_on_path()
    root = _lean_root()
    if root is None:
        print("  [SKIP] live: no lean project root found"); return 0
    cases = {
        "closed":  "import Mathlib\n\ntheorem t (n : Nat) : n + 0 = n := by simp\n",
        # leaves a genuine open goal: prove a conjunction, close only the left
        "partial": "import Mathlib\n\ntheorem t (n : Nat) : n + 0 = n ∧ n = n := by\n  constructor\n  · simp\n",
        "broken":  "import Mathlib\n\ntheorem t (n : Nat) : n + 0 = n := by exact foo_nonexistent\n",
    }
    fails = []
    for name, src in cases.items():
        with tempfile.TemporaryDirectory(prefix=f"ps_live_{name}_") as td:
            f = Path(td) / "Probe.lean"
            f.write_text(src, encoding="utf-8")
            rec = run_lake_compile(f, root, timeout_s=180)
            output = rec.get("stdout_tail", "") + "\n" + rec.get("stderr_tail", "")
            rc = rec.get("returncode")
            sig = proof_state_signal(rc, output)
            print(f"  live[{name}]: ok={rec.get('ok')} class={sig['error_class']} "
                  f"goals={sig['goals_remaining']} progress={sig['progress']}")
            if name == "closed" and not (sig["error_class"] == "clean" and sig["goals_remaining"] == 0):
                fails.append("closed")
            if name == "partial" and sig["goals_remaining"] < 1:
                fails.append("partial (expected >=1 open goal)")
            if name == "broken" and sig["progress"] >= 0.5:
                fails.append("broken (expected low progress)")
    return 1 if fails else 0


if __name__ == "__main__":
    print("=== parser unit tests ===")
    rc1 = test_parser()
    rc2 = 0
    if "--parser" not in sys.argv:
        print("\n=== live compile test ===")
        rc2 = test_live()
    rc = rc1 or rc2
    print(f"\nVERIFY: proof-state signal {'PASS' if rc == 0 else 'FAIL'} "
          f"(parser {'ok' if rc1==0 else 'FAIL'}, live {'ok' if rc2==0 else 'FAIL'})")
    sys.exit(rc)
