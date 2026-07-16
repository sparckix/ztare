from __future__ import annotations

import pytest

from ztare.leanmill.lean_source import (
    _decl_body,
    has_sorry,
    open_decl_for_ratification,
    replace_decl_proof,
)


def test_open_decl_for_ratification_preserves_siblings_and_extracts_proof() -> None:
    source = """import Mathlib
namespace Demo

theorem helper : True := by
  trivial

theorem target (h : (let k := 3; k) = 3) : True := by
  exact True.intro

theorem sibling : 1 = 1 := by
  rfl

end Demo
"""

    opened, proof = open_decl_for_ratification(source, "Demo.target")

    assert proof == "by\n  exact True.intro"
    assert has_sorry(_decl_body(opened, "Demo.target") or "")
    assert _decl_body(opened, "Demo.helper") == _decl_body(source, "Demo.helper")
    assert _decl_body(opened, "Demo.sibling") == _decl_body(source, "Demo.sibling")
    assert "(let k := 3; k) = 3" in opened


def test_open_decl_for_ratification_rejects_open_or_missing_target() -> None:
    source = "theorem target : True := by\n  sorry\n"
    with pytest.raises(ValueError, match="already open"):
        open_decl_for_ratification(source, "target")
    with pytest.raises(ValueError, match="absent or ambiguous"):
        open_decl_for_ratification(source, "missing")


def test_open_decl_for_ratification_resolves_full_namespace_identity() -> None:
    source = """import Mathlib
namespace Left
theorem target : True := by
  trivial
end Left

namespace Right
theorem target : True := by
  exact True.intro

theorem sibling : True := by
  trivial
end Right
"""

    with pytest.raises(ValueError, match="absent or ambiguous"):
        open_decl_for_ratification(source, "target")

    opened, proof = open_decl_for_ratification(source, "Right.target")

    assert proof == "by\n  exact True.intro"
    assert not has_sorry(_decl_body(opened, "Left.target") or "")
    assert has_sorry(_decl_body(opened, "Right.target") or "")
    assert _decl_body(opened, "Right.sibling") == _decl_body(
        source, "Right.sibling"
    )
    assert replace_decl_proof(opened, "Right.target", proof) == source
