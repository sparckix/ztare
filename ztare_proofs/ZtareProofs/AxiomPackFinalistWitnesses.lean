import Mathlib.Tactic

/-!
Explicit non-projection models for the two finalist presentations selected by
the elementary-tetrahedron campaign.  Both carriers and operations are fully
transparent, so the finite checks below are replayed by Lean.
-/

namespace AxiomPackFinalistWitnesses

abbrev Carrier := Fin 3

def swap01 (y : Carrier) : Carrier :=
  if y = 0 then 1 else if y = 1 then 0 else 2

/-- Identity translations except at outer pair `(2, 2)`, where `0` and `1`
are exchanged. -/
def finalistZero (x y z : Carrier) : Carrier :=
  if x = 2 ∧ z = 2 then swap01 y else y

/-- Identity translations except when the first coordinate is `2` and the
third coordinate is `0` or `1`, where `0` and `1` are exchanged. -/
def finalistOne (x y z : Carrier) : Carrier :=
  if x = 2 ∧ (z = 0 ∨ z = 1) then swap01 y else y

theorem finalistZero_tetrahedron :
    ∀ x y z t p q,
      finalistZero (finalistZero x y z) (finalistZero x t p) q =
        finalistZero x (finalistZero y t q) (finalistZero z p q) := by
  native_decide

theorem finalistZero_middle_injective :
    ∀ x z y y', finalistZero x y z = finalistZero x y' z → y = y' := by
  native_decide

theorem finalistZero_first_law :
    ∀ x₀ x₁ x₂ x₃,
      finalistZero (finalistZero x₀ x₁ x₂) x₁ x₃ = x₁ := by
  native_decide

theorem finalistZero_second_law :
    ∀ x₀ x₁ x₂,
      finalistZero x₀ x₁ (finalistZero x₂ x₁ x₂) = x₁ := by
  native_decide

theorem finalistZero_nonprojection : finalistZero 2 0 2 ≠ 0 := by
  native_decide

theorem finalistZero_nonprojection_exists :
    ∃ x y z, finalistZero x y z ≠ y :=
  ⟨2, 0, 2, finalistZero_nonprojection⟩

theorem finalistOne_tetrahedron :
    ∀ x y z t p q,
      finalistOne (finalistOne x y z) (finalistOne x t p) q =
        finalistOne x (finalistOne y t q) (finalistOne z p q) := by
  native_decide

theorem finalistOne_middle_injective :
    ∀ x z y y', finalistOne x y z = finalistOne x y' z → y = y' := by
  native_decide

theorem finalistOne_first_law :
    ∀ x y, finalistOne x y (finalistOne x x x) = y := by
  native_decide

theorem finalistOne_second_law :
    ∀ x y, finalistOne x x y = finalistOne y x y := by
  native_decide

theorem finalistOne_nonprojection : finalistOne 2 0 0 ≠ 0 := by
  native_decide

theorem finalistOne_nonprojection_exists :
    ∃ x y z, finalistOne x y z ≠ y :=
  ⟨2, 0, 0, finalistOne_nonprojection⟩

end AxiomPackFinalistWitnesses
