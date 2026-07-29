from ztare.leanmill.solver.canonical_reelaboration import _strip_hijack_context
from ztare.leanmill.solver.statement_integrity import check, decl_blocks


ORIGINAL = """\
import Mathlib

class Marker (α : Type) where
  mark : α

theorem target : True := by
  sorry

instance : Marker Nat := ⟨0⟩

instance : Marker Nat := ⟨1⟩
"""


def _anonymous_blocks(source: str) -> dict[str, str]:
    return {name: block for name, block in decl_blocks(source) if "instance@" in name}


def test_anonymous_declaration_identity_survives_earlier_proof_displacement():
    probe = ORIGINAL.replace(
        "  sorry\n",
        "  have h₁ : True := trivial\n"
        "  have h₂ : True := h₁\n"
        "  exact h₂\n",
    )

    assert list(_anonymous_blocks(ORIGINAL)) == list(_anonymous_blocks(probe))
    assert check(ORIGINAL, probe, "target").ok
    _, removed = _strip_hijack_context(probe, ORIGINAL)
    assert removed == []


def test_new_anonymous_core_instance_is_still_rejected_and_stripped():
    probe = ORIGINAL.replace(
        "theorem target",
        "local instance {α : Type u} : HAdd α Nat α where\n"
        "  hAdd a _ := a\n\n"
        "theorem target",
    ).replace("  sorry\n", "  trivial\n")

    verdict = check(ORIGINAL, probe, "target")
    assert not verdict.ok
    assert any("instance_shadowing" in violation for violation in verdict.violations)
    stripped, removed = _strip_hijack_context(probe, ORIGINAL)
    assert any(item.startswith("instance:") for item in removed)
    assert "hAdd a _ := a" not in stripped


def test_removed_anonymous_instance_remains_detectable_with_duplicate_signatures():
    probe = ORIGINAL.replace("\ninstance : Marker Nat := ⟨0⟩\n", "", 1).replace(
        "  sorry\n", "  trivial\n"
    )

    verdict = check(ORIGINAL, probe, "target")
    assert not verdict.ok
    assert any(
        marker in violation
        for violation in verdict.violations
        for marker in ("deleted:", "definition_altered:")
    )


def test_anonymous_instance_signature_and_body_mutations_remain_detectable():
    signature_probe = ORIGINAL.replace(
        "instance : Marker Nat := ⟨0⟩",
        "instance : Marker Int := ⟨0⟩",
        1,
    ).replace("  sorry\n", "  trivial\n")
    signature_verdict = check(ORIGINAL, signature_probe, "target")
    assert not signature_verdict.ok
    assert any("deleted:" in violation for violation in signature_verdict.violations)

    body_probe = ORIGINAL.replace("⟨0⟩", "⟨2⟩", 1).replace(
        "  sorry\n", "  trivial\n"
    )
    body_verdict = check(ORIGINAL, body_probe, "target")
    assert not body_verdict.ok
    assert any(
        marker in violation
        for violation in body_verdict.violations
        for marker in ("deleted:", "definition_altered:")
    )
