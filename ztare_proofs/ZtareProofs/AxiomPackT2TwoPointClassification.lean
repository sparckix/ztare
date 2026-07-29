import ZtareProofs.AxiomPackT2ReconstructionCounterexample

/-!
The pointed two-element classification at the reconstruction boundary.

This module keeps the exact bijective elementary-map convention used by the
campaign.  Without middle-slice bijectivity, the classification is false.
-/

namespace AxiomPackT2TwoPointClassification

open AxiomPackT2ReconstructionCounterexample
open AxiomPackFinalistOrbitClassification

/-- The two-element translation selected by a Boolean label. -/
def boolTranslation (flag y : Bool) : Bool :=
  if flag then !y else y

/-- The unique nonprojection pointed two-element normal form. -/
def booleanProductT (x y z : Bool) : Bool :=
  boolTranslation (x && z) y

theorem middle_injective_of_elementaryMap_injective
    (T : Bool → Bool → Bool → Bool)
    (elementary_injective : Function.Injective (elementaryMap T)) :
    ∀ x z, Function.Injective (fun y => T x y z) := by
  intro x z y y' equality
  have map_equality :
      elementaryMap T (x, y, z) = elementaryMap T (x, y', z) := by
    simp [elementaryMap, equality]
  have tuple_equality := elementary_injective map_equality
  exact congrArg (fun xyz : Bool × Bool × Bool => xyz.2.1) tuple_equality

theorem bool_bijective_row_is_translation
    (T : Bool → Bool → Bool → Bool)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z)) :
    ∀ x z, T x true z = !(T x false z) := by
  intro x z
  have distinct : T x false z ≠ T x true z := by
    intro equality
    exact Bool.false_ne_true (middle_injective x z equality)
  cases hfalse : T x false z <;> cases htrue : T x true z <;>
    simp_all

theorem bool_middle_translation_normal_form
    (T : Bool → Bool → Bool → Bool)
    (middle_injective : ∀ x z, Function.Injective (fun y => T x y z)) :
    ∀ x y z, T x y z = boolTranslation (T x false z) y := by
  intro x y z
  cases y
  · cases T x false z <;> simp [boolTranslation]
  · rw [bool_bijective_row_is_translation T middle_injective x z]
    cases T x false z <;> simp [boolTranslation]

/-- Every pointed bijective elementary two-solution on `Bool` is either the
middle projection or the associative-ring normal form `y + xz` over `F₂`.
Only the tetrahedron equation, elementary-map injectivity, and the pointed
fixed-value condition are needed. -/
theorem pointed_bool_elementaryTwoSolution_classification
    (T : Bool → Bool → Bool → Bool)
    (tetrahedron : TetrahedronEquation T)
    (elementary_injective : Function.Injective (elementaryMap T))
    (pointed : T false false false = false) :
    (∀ x y z, T x y z = y) ∨
      ∀ x y z, T x y z = booleanProductT x y z := by
  have middle_injective :=
    middle_injective_of_elementaryMap_injective T elementary_injective
  let f : Bool → Bool → Bool := fun x z => T x false z
  have normal_form : ∀ x y z, T x y z = boolTranslation (f x z) y := by
    intro x y z
    simpa only [f] using
      bool_middle_translation_normal_form T middle_injective x y z
  have f00 : f false false = false := by
    simpa only [f] using pointed
  have f01 : f false true = false := by
    cases h01 : f false true
    · rfl
    · have constraint :=
        tetrahedron false false false false false true
      simp [normal_form, boolTranslation, f00, h01] at constraint
  have f10 : f true false = false := by
    cases h10 : f true false
    · rfl
    · have constraint :=
        tetrahedron true false false false false false
      simp [normal_form, boolTranslation, f00, h10] at constraint
  cases h11 : f true true
  · left
    intro x y z
    rw [normal_form]
    cases x <;> cases z <;>
      simp [boolTranslation, f00, f01, f10, h11]
  · right
    intro x y z
    rw [normal_form]
    cases x <;> cases z <;>
      simp [booleanProductT, boolTranslation, f00, f01, f10, h11]

theorem pointed_bool_elementaryTwoSolution_classification_of_bijective
    (T : Bool → Bool → Bool → Bool)
    (solution : ElementaryTwoSolution T)
    (pointed : T false false false = false) :
    (∀ x y z, T x y z = y) ∨
      ∀ x y z, T x y z = booleanProductT x y z :=
  pointed_bool_elementaryTwoSolution_classification
    T solution.1 solution.2.1 pointed

theorem booleanProductT_tetrahedron :
    TetrahedronEquation booleanProductT := by
  intro x y z t p q
  cases x <;> cases y <;> cases z <;> cases t <;> cases p <;> cases q <;>
    decide

theorem booleanProductT_elementaryMap_involutive :
    Function.Involutive (elementaryMap booleanProductT) := by
  rintro ⟨x, y, z⟩
  cases x <;> cases y <;> cases z <;> rfl

theorem booleanProductT_is_elementaryTwoSolution :
    ElementaryTwoSolution booleanProductT :=
  ⟨booleanProductT_tetrahedron,
    booleanProductT_elementaryMap_involutive.bijective⟩

theorem booleanProductT_identity_extraction :
    ExtractionHypotheses booleanProductT false (fun x => x) := by
  refine ⟨rfl, ?_, ?_, ?_, ?_⟩
  · intro x
    cases x <;> rfl
  · intro x
    cases x <;> rfl
  · intro x y
    cases x <;> cases y <;> rfl
  · intro x y
    cases x <;> cases y <;> rfl

theorem booleanProductT_reconstruction_formula :
    ∀ x y z,
      reconstructed booleanProductT false (fun x => x) x y z = y := by
  intro x y z
  cases x <;> cases y <;> cases z <;> rfl

theorem booleanProductT_reconstruction_fails :
    booleanProductT true false true ≠
      reconstructed booleanProductT false (fun x => x) true false true := by
  decide

/-- A two-element kernel witness, proving that cardinality two is enough for
failure of the published reconstruction. -/
theorem booleanProductT_t2_reconstruction_counterexample :
    ElementaryTwoSolution booleanProductT ∧
      ExtractionHypotheses booleanProductT false (fun x => x) ∧
      ¬ ∀ x y z,
        booleanProductT x y z =
          reconstructed booleanProductT false (fun x => x) x y z := by
  refine ⟨booleanProductT_is_elementaryTwoSolution,
    booleanProductT_identity_extraction, ?_⟩
  intro reconstructs
  exact booleanProductT_reconstruction_fails (reconstructs true false true)

end AxiomPackT2TwoPointClassification
