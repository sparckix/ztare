"""Structural-leg smoke test: the firewall's DETERMINISTIC checks must run end-to-end on a realistic statement
without a module-level breakage (a shadowed global, a missing name, a regex-vs-tuple mixup). The `_PROP_MARKERS`
collision (2026-07-02) fail-closed the whole firewall in production because NO test drove `_parse_lean_statement`
on a statement whose signature carries instance binders AND propositional hypotheses — the shape that touches
every module-level structural name. This drives exactly that shape and asserts no crash + sane structure.

Runnable: `python tests/test_firewall_structural_smoke.py`. No LLM — only the deterministic legs.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import ztare.leanmill.solver.autoformalize as af  # noqa: E402

# a realistic multi-binder statement: type vars, INSTANCE binders, and PROPOSITIONAL hypotheses — the exact shape
# whose `_parse_lean_statement`/`_instance_classes`/`_explicit_hypotheses` paths the collision silently broke.
_STMT = ("theorem t {X T : Type*} [Fintype X] [LinearOrder T] (f : X → T → ℝ) "
         "(h_mono : ∀ t : T, Monotone (fun x => f x t)) (h_pos : ∀ x t, 0 ≤ f x t) : "
         "∀ ⦃t t' : T⦄, t ≤ t' → True := by intro; trivial")


def test_module_level_names_are_consistent():
    # the exact regression: the compiled-regex `_PROP_MARKERS` must not be shadowed by a tuple.
    assert isinstance(af._PROP_MARKERS, re.Pattern), f"_PROP_MARKERS is {type(af._PROP_MARKERS)}, not a regex"
    assert af._PROP_MARKERS.search("a ≤ b")
    assert isinstance(af._HYP_PROP_MARKERS, tuple)
    print("OK: _PROP_MARKERS is the regex; _HYP_PROP_MARKERS is the tuple — no shadow")


def test_structural_leg_runs_end_to_end():
    # every deterministic structural fn must run on the realistic shape without raising (the fail-closed-on-crash
    # bug was an AttributeError deep in `_parse_lean_statement`). We assert no exception + a sane result shape.
    parsed = af._parse_lean_statement(_STMT)
    assert isinstance(parsed, dict), parsed
    classes = af._instance_classes(_STMT)
    assert "Fintype" in classes and "LinearOrder" in classes, classes
    hyps = af._explicit_hypotheses(_STMT)
    assert any("h_mono" in h for h in hyps) and any("h_pos" in h for h in hyps), hyps
    fp = af.reference_fingerprint(_STMT)
    assert isinstance(fp, dict), fp
    # structural_faithfulness with expected=its own fingerprint must accept (identity) — proves the whole
    # deterministic carrier is wired, not just individually callable.
    assert af.structural_faithfulness("a monotone objective", _STMT, expected=fp) is True
    print("OK: parse/instances/hypotheses/fingerprint/structural_faithfulness all run + self-consistent")


if __name__ == "__main__":
    test_module_level_names_are_consistent()
    test_structural_leg_runs_end_to_end()
