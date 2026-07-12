from __future__ import annotations

"""Scaffold harvest/compose — the gale-Shapley thrash fix (2026-07-06).

Entry-point test (per feedback_test_entry_point_not_component): exercise the REAL
`_harvest_scaffold` on the REAL failing shape — a conjecture-style probe whose whole
body still carries the target `sorry` but whose helper lemmas are individually proven.
The bug was that the whole-probe sorry-free gate persisted NOTHING for this shape, so
every re-dispatch rebuilt the helpers. These guards lock in: proven helpers survive,
the sorried target and any sorried decl are dropped, and the composed probe seeds the
helpers above a fresh stub. The soundness invariant (never persist a `sorry`) is the
load-bearing property — a regression here would let a phantom `sorryAx` be reused.
"""

from ztare.leanmill.solver.agentic_leaf import _harvest_scaffold

# The real gale shape: two proven helpers + a still-sorried conjecture target.
PROBE = """\
import Mathlib

theorem chooseBetterForW_weakly_prefers_right (a b : Nat) :
    max a b ≥ b := le_max_right a b

theorem chooseBetterForW_comm (a b : Nat) : max a b = max b a := Nat.max_comm a b

theorem conj_anchor_woman_held_monotone_a (a b : Nat) : max a b ≥ a := by
  sorry
"""


def test_harvest_keeps_proven_helpers_drops_sorried_target():
    scaf = _harvest_scaffold(PROBE, "conj_anchor_woman_held_monotone_a")
    # both proven helpers survive...
    assert "chooseBetterForW_weakly_prefers_right" in scaf
    assert "chooseBetterForW_comm" in scaf
    # ...the sorried target is dropped, and NOTHING sorried is ever persisted (the invariant).
    assert "conj_anchor_woman_held_monotone_a" not in scaf
    assert "sorry" not in scaf and "admit" not in scaf


def test_harvest_drops_a_helper_that_itself_carries_a_sorry():
    # a helper the agent left half-done must NOT be persisted (would be a phantom sorryAx).
    probe = PROBE.replace("max a b = max b a := Nat.max_comm a b", "max a b = max b a := by sorry")
    scaf = _harvest_scaffold(probe, "conj_anchor_woman_held_monotone_a")
    assert "chooseBetterForW_weakly_prefers_right" in scaf  # the still-good one stays
    assert "chooseBetterForW_comm" not in scaf              # the sorried one is dropped
    assert "sorry" not in scaf


def test_harvest_returns_empty_when_no_proven_helper():
    probe = "import Mathlib\n\ntheorem t (a : Nat) : a = a := by sorry\n"
    assert _harvest_scaffold(probe, "t") == ""


def test_composed_probe_seeds_helpers_above_a_fresh_stub():
    # the compose step the seed site does: scaffold + stub → agent proves the target ON the helpers.
    scaf = _harvest_scaffold(PROBE, "conj_anchor_woman_held_monotone_a")
    stub = "theorem conj_anchor_woman_held_monotone_a (a b : Nat) : max a b ≥ a := by sorry\n"
    composed = scaf.rstrip() + "\n\n" + stub
    assert "chooseBetterForW_weakly_prefers_right" in composed  # helper present to cite
    assert composed.count("sorry") == 1                          # exactly the target stub, nothing else


if __name__ == "__main__":  # ponytail: runnable without pytest
    for _n, _f in list(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f()
            print(f"ok {_n}")
    print("all scaffold-harvest guards passed")
