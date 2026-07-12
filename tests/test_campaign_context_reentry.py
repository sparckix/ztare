"""GUARD for the 2026-07-02 synthInstance RCA: a section-style campaign substrate exposes its decls' type/
instance binders via section `variable`s that close with the section; warm-verify / the conjecture audits
re-entered the namespace (names resolve) but DROPPED that variable context ⇒ any target whose signature needs
a section instance (`Fintype.card V` ⇒ `[Fintype V]`) failed `synthInstanceFailed` and could never ratify.

Cure = ONE door: lean_source.section_variable_lines + conjecture._campaign_probe re-declare the substrate's
variable lines after namespace re-entry. This guard pins: (1) extraction correctness + flat-theory `[]` parity;
(2) _campaign_probe wraps a body in `namespace X / <vars> / body / end X` ONLY for a single-namespace substrate,
and is byte-flat otherwise. Pure-python (no Lean, no pytest). Run: `python tests/test_campaign_context_reentry.py`.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ztare.leanmill.lean_source import section_variable_lines
from ztare.leanmill.solver.conjecture import _campaign_probe
from ztare.formal import repl_compile as rc

_SECTION_STYLE = """import Mathlib
namespace MV
variable {A B V : Type*}
section S
variable [LinearOrder A] [Fintype V]
def Foo (v : V) : Prop := True
-- variable this_is_a_comment must NOT be captured
variable [LinearOrder A] [Fintype V]
end S
end MV"""


def test_section_variable_lines():
    got = section_variable_lines(_SECTION_STYLE)
    assert got == ["variable {A B V : Type*}", "variable [LinearOrder A] [Fintype V]"], got
    assert section_variable_lines("import Mathlib\ntheorem t : 1 = 1 := rfl") == [], "flat theory ⇒ [] (parity)"
    assert section_variable_lines("") == []
    print("OK section_variable_lines: extracts + dedups; [] for flat; comment ignored")


def test_campaign_probe_parity_no_substrate():
    rc.set_campaign_substrate(None)
    out = _campaign_probe("import Mathlib\ndef Foo := 1", "theorem t : 1 = 1 := rfl")
    assert out.lstrip().startswith("import Mathlib") and "namespace" not in out, out
    print("OK _campaign_probe: no substrate ⇒ flat form (byte-parity with prior behaviour)")


def test_campaign_probe_wraps_single_namespace():
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as f:
        f.write(_SECTION_STYLE)
        path = f.name
    try:
        rc.set_campaign_substrate(path)
        rc._CAMPAIGN_NS_CACHE.clear(); rc._CAMPAIGN_VAR_CACHE.clear()
        body = "theorem t_conj : ∀ (v : V), Foo v := by sorry"
        out = _campaign_probe("flat preamble ignored when substrate present", body)
        assert "namespace MV\n" in out, out
        assert "variable {A B V : Type*}" in out and "variable [LinearOrder A] [Fintype V]" in out, out
        assert out.rstrip().endswith("end MV"), out
        # the body sits AFTER the re-declared variables and INSIDE the namespace (so its short-names + instances resolve)
        assert out.index("variable [LinearOrder A]") < out.index(body) < out.rindex("end MV"), out
        print("OK _campaign_probe: single-namespace ⇒ substrate + `namespace/vars/body/end` re-entry")
    finally:
        rc.set_campaign_substrate(None)
        Path(path).unlink(missing_ok=True)


def test_campaign_probe_multi_namespace_is_noop():
    txt = "import Mathlib\nnamespace A\nend A\nnamespace B\nvariable {x : Nat}\nend B"
    with tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False) as f:
        f.write(txt)
        path = f.name
    try:
        rc.set_campaign_substrate(path)
        rc._CAMPAIGN_NS_CACHE.clear(); rc._CAMPAIGN_VAR_CACHE.clear()
        out = _campaign_probe("import Mathlib\ndef P := 1", "theorem t : True := trivial")
        assert out.lstrip().startswith("import Mathlib") and "namespace A" not in out, out  # ns!=1 ⇒ flat (parity)
        print("OK _campaign_probe: multi-namespace substrate ⇒ flat form (no re-entry, parity)")
    finally:
        rc.set_campaign_substrate(None)
        Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_section_variable_lines()
    test_campaign_probe_parity_no_substrate()
    test_campaign_probe_wraps_single_namespace()
    test_campaign_probe_multi_namespace_is_noop()
    print("\nALL PASS — campaign-context re-entry single-door guard green")
