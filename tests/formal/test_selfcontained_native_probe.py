from __future__ import annotations

"""native_hammer must carry a SELF-CONTAINED probe's warm-only theory (2026-07-06 gale-Shapley RCA).

Entry-point test on the real failing shape: a namespace-wrapped probe that defines its own theory inline
(`inductive ProposalRun`) and carries a REAL proof (no trailing `sorry`). The bug: `compile_stub` needed a
trailing sorry → returned "" → native_hammer fell back to a bare goal that dropped `ProposalRun`, then
substituted the substrate (warm-only, no `ProposalRun`) → `unknown identifier` on every attempt. These guards
lock the three-part fix: (1) `compile_stub` swaps a real proof for `:= by`, keeping the preamble def; (2) the
probe's `namespace …Probe` wrapper is stripped so its defs are reachable at top level; (3) `campaign_scope_prefix`
`open`s a namespace-style substrate so its own defs still resolve.
"""

from ztare.leanmill import lean_source as ls

PROBE = """\
import Mathlib
namespace Probe
structure StrictPreference (A B : Type) where r : A → B → B → Prop
inductive ProposalRun : Nat → Prop
  | z : ProposalRun 0
theorem tgt (n : Nat) (h : ProposalRun n) : n = n := by
  cases h
  rfl
end Probe
"""


def test_top_level_assign_skips_binder_defaults():
    assert ls.top_level_assign("theorem t (n : Nat := 0) : n = n := by rfl") == len(
        "theorem t (n : Nat := 0) : n = n ")  # the PROOF `:=`, not the binder-default one
    assert ls.top_level_assign("theorem t : True") == -1


def test_compile_stub_swaps_a_real_proof_and_keeps_the_inline_theory():
    out = ls.compile_stub(PROBE, "tgt")
    assert out, "compile_stub must not bail on a real (non-sorry) proof"
    assert "inductive ProposalRun" in out          # the warm-only def survives (was dropped → unknown_identifier)
    assert out.rstrip().endswith(":= by")          # proof swapped, ready for the tactic cascade
    assert "cases h" not in out                     # the real proof body is gone (only the stub remains)


def test_strip_scope_hoists_probe_defs_to_top_level():
    # the wrapper is stripped so `ProposalRun` is reachable without an unclosed `namespace Probe`
    stripped = ls.strip_scope_commands(ls.compile_stub(PROBE, "tgt"))
    assert "namespace Probe" not in stripped
    assert "inductive ProposalRun" in stripped


def test_sorry_probe_is_byte_identical_path():
    # a normal sorry-target still takes the unchanged path (no regression for prior campaigns)
    sp = "import Mathlib\n\ntheorem t (n : Nat) : n = n := by sorry\n"
    assert ls.compile_stub(sp, "t").rstrip().endswith(":= by")


def test_tactic_probe_owns_a_narrow_prelude_and_preserves_explicit_imports():
    stub = (
        "import Mathlib\n"
        "import Mathlib.Data.Nat.Prime.Basic\n"
        "theorem t : True := by"
    )
    out = ls.assemble_tactic_probe(stub, "trivial")
    assert "import Mathlib\n" not in out
    assert out.count("import Mathlib.Tactic") == 1
    assert "import Mathlib.Data.Nat.Prime.Basic" in out
    assert out.rstrip().endswith("trivial")


def test_tactic_probe_balances_scopes_at_an_exact_multidecl_boundary():
    src = (
        "import Mathlib.Tactic\n"
        "namespace Outer.Inner\n"
        "section Work\n"
        "theorem first : True := by sorry\n"
        "theorem later : False := by sorry\n"
        "end Work\n"
        "end Outer.Inner\n"
    )
    stub = ls.compile_stub(src, "Outer.Inner.first")
    out = ls.assemble_tactic_probe(stub, "trivial")
    assert "theorem first" in out
    assert "theorem later" not in out
    assert out.rstrip().endswith("end Outer.Inner")
    assert "\nend Work\nend Outer.Inner\n" in out


def test_later_target_drops_only_unreferenced_open_siblings():
    independent = (
        "theorem old_gap : True := by sorry\n"
        "theorem target (n : Nat) : n = n := by sorry\n"
    )
    assert "old_gap" not in ls.compile_stub(independent, "target")

    referenced = (
        "theorem needed_gap : True := by sorry\n"
        "theorem target (_h : needed_gap = needed_gap) : True := by sorry\n"
    )
    # A referenced open declaration remains visible, so the no-sorry checker
    # rejects rather than laundering it as context.
    kept = ls.compile_stub(referenced, "target")
    assert "theorem needed_gap" in kept
    assert ls.has_sorry(kept)


if __name__ == "__main__":
    for _n, _f in list(globals().items()):
        if _n.startswith("test_") and callable(_f):
            _f(); print(f"ok {_n}")
    print("all self-contained native-probe guards passed")
