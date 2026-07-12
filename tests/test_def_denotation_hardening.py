from ztare.leanmill.solver.def_denotation import (
    PINNED,
    UNDERDETERMINED,
    VACUITY_EXPOSED,
    WITNESSED,
    certify_def_denotation,
    certify_nonvacuity,
)


VACUITY_BASE = """import Mathlib

def StrongSetLE {X : Type*} [SemilatticeSup X] [SemilatticeInf X]
    (s u : Set X) : Prop :=
  ∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u
"""


def test_reflexive_anchor_cannot_pin_even_when_kernel_verified():
    src = """import Mathlib
def FrontierObject : Nat := 0
theorem anchor_FrontierObject_self : FrontierObject = FrontierObject := rfl
"""
    calls = []
    result = certify_def_denotation(src, verify_anchor_fn=lambda name: calls.append(name) or True)
    assert result["verdict"] == UNDERDETERMINED
    assert calls == []
    assert result["per_def"]["FrontierObject"]["invalid_anchors"] == ["anchor_FrontierObject_self"]
    assert result["anchors"][0]["state"] == "invalid_shape"


def test_legacy_external_relation_remains_compatible():
    src = """import Mathlib
def FrontierSucc (n : Nat) : Nat := n + 1
theorem anchor_FrontierSucc_nat (n : Nat) : FrontierSucc n = Nat.succ n := by simp [FrontierSucc]
"""
    result = certify_def_denotation(src, verify_anchor_fn=lambda _name: True)
    assert result["verdict"] == PINNED
    anchor = result["anchors"][0]
    assert anchor["kind"] == "definitional"
    assert anchor["external"] == "Nat.succ"
    assert anchor["metadata"] is False


def test_typed_special_case_requires_declared_external_in_signature():
    good = """import Mathlib
def StrongSingletonLE (s u : Set Nat) : Prop := ∀ x ∈ s, ∀ y ∈ u, x ≤ y
-- @denotation-anchor: anchor=anchor_StrongSingletonLE_singleton; target=StrongSingletonLE; kind=special_case; external=LE.le
theorem anchor_StrongSingletonLE_singleton (a b : Nat) :
    StrongSingletonLE {a} {b} ↔ a ≤ b := by simp [StrongSingletonLE]
"""
    result = certify_def_denotation(good, verify_anchor_fn=lambda _name: True)
    assert result["verdict"] == PINNED
    assert result["anchors"][0]["kind"] == "special_case"
    assert result["anchors"][0]["external"] == "LE.le"
    assert result["anchors"][0]["metadata"] is True

    forged = good.replace("external=LE.le", "external=Nat.gcd")
    result = certify_def_denotation(forged, verify_anchor_fn=lambda _name: True)
    assert result["verdict"] == UNDERDETERMINED
    assert result["anchors"][0]["state"] == "invalid_shape"
    assert "absent" in result["anchors"][0]["reason"]


def test_local_bridge_and_unused_binder_cannot_pose_as_external_reference():
    local_bridge = """import Mathlib
def FrontierObject : Nat := 0
theorem LocalReference : Nat := FrontierObject
theorem anchor_FrontierObject_local : FrontierObject = LocalReference := rfl
"""
    result = certify_def_denotation(local_bridge, verify_anchor_fn=lambda _name: True)
    assert result["verdict"] == UNDERDETERMINED
    assert "external reference" in result["anchors"][0]["reason"]

    binder_smuggling = """import Mathlib
def FrontierObject : Nat := 0
-- @denotation-anchor: anchor=anchor_FrontierObject_zero; target=FrontierObject; kind=definitional; external=Nat.gcd
theorem anchor_FrontierObject_zero (_unused : Nat.gcd 1 1 = 1) : FrontierObject = 0 := rfl
"""
    result = certify_def_denotation(binder_smuggling, verify_anchor_fn=lambda _name: True)
    assert result["verdict"] == UNDERDETERMINED
    assert "non-candidate side" in result["anchors"][0]["reason"]


def test_true_theorem_named_witness_cannot_witness():
    src = VACUITY_BASE + "\ntheorem witness_StrongSetLE_nonvacuous : True := trivial\n"
    calls = []
    result = certify_nonvacuity(src, verify_fn=lambda name: calls.append(name) or True)
    assert result["verdict"] == VACUITY_EXPOSED
    assert calls == []
    assert result["witnesses"][0]["state"] == "invalid_shape"


def test_nonempty_subject_must_be_an_argument_of_target_definition():
    src = VACUITY_BASE + """
theorem witness_StrongSetLE_unbound {X : Type*} [SemilatticeSup X] [SemilatticeInf X]
    (s u v : Set X) : s.Nonempty ∧ StrongSetLE u v := by sorry
"""
    result = certify_nonvacuity(src, verify_fn=lambda _name: True)
    assert result["verdict"] == VACUITY_EXPOSED
    assert result["witnesses"][0]["state"] == "invalid_shape"
    assert "do not cover" in result["witnesses"][0]["reason"]

    only_one_side = VACUITY_BASE + """
theorem witness_StrongSetLE_half {X : Type*} [SemilatticeSup X] [SemilatticeInf X]
    (s u : Set X) : s.Nonempty ∧ StrongSetLE s u := by sorry
"""
    result = certify_nonvacuity(only_one_side, verify_fn=lambda _name: True)
    assert result["verdict"] == VACUITY_EXPOSED
    assert result["witnesses"][0]["required_nonempty_counts"] == {"StrongSetLE": 2}


def test_bound_nonempty_witness_is_accepted_after_kernel_verification():
    src = VACUITY_BASE + """
theorem witness_StrongSetLE_nonvacuous {X : Type*} [SemilatticeSup X] [SemilatticeInf X] :
    ∃ s u : Set X, s.Nonempty ∧ u.Nonempty ∧ StrongSetLE s u := by sorry
"""
    result = certify_nonvacuity(src, verify_fn=lambda _name: True)
    assert result["verdict"] == WITNESSED
    witness = result["witnesses"][0]
    assert witness["kind"] == "nonempty_argument"
    assert witness["targets"] == ["StrongSetLE"]
    assert witness["nonempty_subjects"] == ["s", "u"]
    assert witness["required_nonempty_counts"] == {"StrongSetLE": 2}
