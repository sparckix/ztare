import Mathlib.Algebra.Group.Action.Faithful
import ZtareProofs.AxiomPackFinalistOneBridge
import ZtareProofs.AxiomPackFinalistZeroBridge

/-!
Exact label constraints for the two frozen elementary-tetrahedron finalists.

The general theorems classify orbit-action operations on the image of the
orbit map.  Recovering a group-element identity from finalist one's diagonal
law uses faithfulness of the action.  The canonical translation action is by a
subgroup of permutations and is therefore faithful.

The final two theorems concern equality with the canonical translation-orbit
reconstruction.  They do not assert an up-to-isomorphism classification.
-/

namespace AxiomPackFinalistOrbitClassification

open AxiomPackOrbitAction

universe u v w

variable {G : Type u} {X : Type v} {O : Type w}

def TetrahedronEquation (T : X → X → X → X) : Prop :=
  ∀ x y z t p q,
    T (T x y z) (T x t p) q = T x (T y t q) (T z p q)

def FinalistZeroLaws (T : X → X → X → X) : Prop :=
  (∀ x y z w, T (T x y z) y w = y) ∧
    (∀ x y z, T x y (T z y z) = y)

def FinalistOneLaws (T : X → X → X → X) : Prop :=
  (∀ x y, T x y (T x x x) = y) ∧
    (∀ x y, T x x y = T y x y)

/-- Each label fixes a representative of its first indexed orbit.  Since the
representative is universally quantified and the label depends only on its
orbit, this is pointwise fixing of that orbit. -/
def FixesFirstIndexedOrbit [SMul G X]
    (orbit : X → O) (label : O → O → G) : Prop :=
  ∀ x z, label (orbit x) (orbit z) • x = x

/-- Each label fixes a representative of its second indexed orbit, hence the
whole indexed orbit pointwise. -/
def FixesSecondIndexedOrbit [SMul G X]
    (orbit : X → O) (label : O → O → G) : Prop :=
  ∀ x z, label (orbit x) (orbit z) • z = z

/-- Diagonal identity restricted to orbit indices that occur in `X`. -/
def DiagonalIdentityOnIndexedOrbits [One G]
    (orbit : X → O) (label : O → O → G) : Prop :=
  ∀ x, label (orbit x) (orbit x) = 1

theorem fixesFirstIndexedOrbit_iff_pointwise [SMul G X]
    (orbit : X → O) (label : O → O → G) :
    FixesFirstIndexedOrbit orbit label ↔
      ∀ x z y, orbit y = orbit x → label (orbit x) (orbit z) • y = y := by
  constructor
  · intro fixes x z y hy
    simpa [hy] using fixes y z
  · intro fixes x z
    exact fixes x z x rfl

theorem fixesSecondIndexedOrbit_iff_pointwise [SMul G X]
    (orbit : X → O) (label : O → O → G) :
    FixesSecondIndexedOrbit orbit label ↔
      ∀ x z y, orbit y = orbit z → label (orbit x) (orbit z) • y = y := by
  constructor
  · intro fixes x z y hy
    simpa [hy] using fixes x y
  · intro fixes x z
    exact fixes x z z rfl

theorem orbitAction_tetrahedronEquation [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (orbit_invariant : ∀ (g : G) (x : X), orbit (g • x) = orbit x) :
    TetrahedronEquation (orbitActionOp orbit label) := by
  exact orbitAction_tetrahedron orbit label orbit_invariant

/-- On an orbit action, finalist zero is exactly pointwise fixing of both
indexed orbits. -/
theorem orbitAction_finalistZero_iff [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (orbit_invariant : ∀ (g : G) (x : X), orbit (g • x) = orbit x) :
    FinalistZeroLaws (orbitActionOp orbit label) ↔
      FixesFirstIndexedOrbit orbit label ∧
        FixesSecondIndexedOrbit orbit label := by
  constructor
  · rintro ⟨first_law, second_law⟩
    constructor
    · intro x z
      simpa [orbitActionOp, orbit_invariant] using first_law x x x z
    · intro x z
      simpa [orbitActionOp, orbit_invariant] using second_law x z z
  · rintro ⟨fixes_first, fixes_second⟩
    constructor
    · intro x y z w
      simpa [orbitActionOp, orbit_invariant] using fixes_first y w
    · intro x y z
      simpa [orbitActionOp, orbit_invariant] using fixes_second x y

/-- The finalist-zero constraints construct an operation satisfying both the
tetrahedron equation and the frozen law pair. -/
theorem orbitAction_finalistZero_construction [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (orbit_invariant : ∀ (g : G) (x : X), orbit (g • x) = orbit x)
    (fixes_first : FixesFirstIndexedOrbit orbit label)
    (fixes_second : FixesSecondIndexedOrbit orbit label) :
    TetrahedronEquation (orbitActionOp orbit label) ∧
      FinalistZeroLaws (orbitActionOp orbit label) := by
  exact ⟨orbitAction_tetrahedronEquation orbit label orbit_invariant,
    (orbitAction_finalistZero_iff orbit label orbit_invariant).2
      ⟨fixes_first, fixes_second⟩⟩

/-- For a faithful action, finalist one is exactly diagonal label identity plus
pointwise fixing of the first indexed orbit. -/
theorem orbitAction_finalistOne_iff [CommGroup G] [MulAction G X]
    [FaithfulSMul G X]
    (orbit : X → O) (label : O → O → G)
    (orbit_invariant : ∀ (g : G) (x : X), orbit (g • x) = orbit x) :
    FinalistOneLaws (orbitActionOp orbit label) ↔
      DiagonalIdentityOnIndexedOrbits orbit label ∧
        FixesFirstIndexedOrbit orbit label := by
  constructor
  · rintro ⟨diagonal_law, cross_law⟩
    have diagonal_action : ∀ (x y : X), label (orbit x) (orbit x) • y = y := by
      intro x y
      simpa [orbitActionOp, orbit_invariant] using diagonal_law x y
    have diagonal_identity : DiagonalIdentityOnIndexedOrbits orbit label := by
      intro x
      apply eq_of_smul_eq_smul (M := G) (α := X)
      intro y
      simpa using diagonal_action x y
    refine ⟨diagonal_identity, ?_⟩
    intro x z
    calc
      label (orbit x) (orbit z) • x =
          label (orbit z) (orbit z) • x := by
        simpa [orbitActionOp] using cross_law x z
      _ = x := by rw [diagonal_identity z, one_smul]
  · rintro ⟨diagonal_identity, fixes_first⟩
    constructor
    · intro x y
      simp [orbitActionOp, diagonal_identity x]
    · intro x y
      simpa [orbitActionOp, diagonal_identity y] using fixes_first x y

/-- The finalist-one constraints are sufficient without assuming faithfulness;
faithfulness is needed only for the reverse implication above. -/
theorem orbitAction_finalistOne_construction [CommGroup G] [MulAction G X]
    (orbit : X → O) (label : O → O → G)
    (orbit_invariant : ∀ (g : G) (x : X), orbit (g • x) = orbit x)
    (diagonal_identity : DiagonalIdentityOnIndexedOrbits orbit label)
    (fixes_first : FixesFirstIndexedOrbit orbit label) :
    TetrahedronEquation (orbitActionOp orbit label) ∧
      FinalistOneLaws (orbitActionOp orbit label) := by
  refine ⟨orbitAction_tetrahedronEquation orbit label orbit_invariant, ?_⟩
  constructor
  · intro x y
    simp [orbitActionOp, diagonal_identity x]
  · intro x y
    simpa [orbitActionOp, diagonal_identity y] using fixes_first x y

/-- A canonical translation-orbit label fixes the whole second generated orbit
when every translation fixes its second index. -/
theorem translationOrbitLabel_fixes_target_orbit
    (translation : X → X → Equiv.Perm X)
    (right_constant : ∀ (h : translationSubgroup translation) x z,
      translation x (h • z) = translation x z)
    (left_constant : ∀ (h : translationSubgroup translation) x z,
      translation (h • x) z = translation x z)
    (target_fixed : ∀ x z, translation x z z = z) :
    ∀ (h : translationSubgroup translation) x z,
      (translationOrbitLabel translation right_constant left_constant
        (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) (h • z) = h • z := by
  intro h x z
  change translation x z (h • z) = h • z
  rw [← right_constant h x z]
  exact target_fixed x (h • z)

/-- The canonical label of a finalist-zero permutation-slice model takes values
in an abelian translation subgroup and fixes both indexed generated orbits
pointwise. -/
theorem finalistZero_canonical_label_constraints
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (finalistA : ∀ x y z w,
      translation (translation x z y) w y = y)
    (finalistB : ∀ x y z,
      translation x (translation z z y) y = y) :
    IsMulCommutative (translationSubgroup translation) ∧
      ∃ label : TranslationOrbit translation →
          TranslationOrbit translation → translationSubgroup translation,
        (∀ x z,
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) =
            translation x z) ∧
        (∀ (h : translationSubgroup translation) x z,
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) (h • x) =
            h • x) ∧
        (∀ (h : translationSubgroup translation) x z,
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) (h • z) =
            h • z) := by
  obtain ⟨source_fixed, commute⟩ :=
    AxiomPackFinalistZeroBridge.finalistZero_forces_orbit_assumptions
      translation tetrahedron finalistA finalistB
  refine ⟨translationSubgroup_isMulCommutative translation commute, ?_⟩
  obtain ⟨right_generator, left_generator⟩ :=
    commutingTranslations_factor_through_orbits
      translation tetrahedron source_fixed commute
  obtain ⟨right_constant, left_constant⟩ :=
    translation_constant_on_generated_orbits
      translation right_generator left_generator
  let label := translationOrbitLabel translation right_constant left_constant
  have target_fixed : ∀ x z, translation x z z = z := by
    exact AxiomPackFinalistZeroBridge.finalistZero_diagonal
      (fun x y z ↦ translation x z y) finalistB
  refine ⟨label, ?_, ?_, ?_⟩
  · intro x z
    rfl
  · simpa [label] using
      (translationOrbitLabel_fixes_source_orbit translation right_constant
        left_constant source_fixed)
  · simpa [label] using
      (translationOrbitLabel_fixes_target_orbit translation right_constant
        left_constant target_fixed)

/-- The canonical label of a finalist-one permutation-slice model takes values
in an abelian translation subgroup, is the identity on every diagonal orbit
index, and fixes the first indexed generated orbit pointwise. -/
theorem finalistOne_canonical_label_constraints
    (translation : X → X → Equiv.Perm X)
    (tetrahedron : ∀ x y z t p q,
      translation (translation x z y) q (translation x p t) =
        translation x (translation z q p) (translation y q t))
    (diagonal_inverse : ∀ x y,
      translation x (translation x x x) y = y)
    (cross_diagonal : ∀ x y,
      translation x y x = translation y y x) :
    IsMulCommutative (translationSubgroup translation) ∧
      ∃ label : TranslationOrbit translation →
          TranslationOrbit translation → translationSubgroup translation,
        (∀ x z,
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) =
            translation x z) ∧
        (∀ a : TranslationOrbit translation, label a a = 1) ∧
        (∀ (h : translationSubgroup translation) x z,
          (label (Quotient.mk'' x) (Quotient.mk'' z) : Equiv.Perm X) (h • x) =
            h • x) := by
  have source_fixed :=
    AxiomPackFinalistOneBridge.finalistOne_source_fixed
      translation tetrahedron diagonal_inverse cross_diagonal
  have commute :=
    AxiomPackFinalistOneBridge.finalistOne_commute
      translation tetrahedron diagonal_inverse cross_diagonal
  refine ⟨translationSubgroup_isMulCommutative translation commute, ?_⟩
  obtain ⟨right_generator, left_generator⟩ :=
    commutingTranslations_factor_through_orbits
      translation tetrahedron source_fixed commute
  obtain ⟨right_constant, left_constant⟩ :=
    translation_constant_on_generated_orbits
      translation right_generator left_generator
  let label := translationOrbitLabel translation right_constant left_constant
  have diagonal_mk :=
    translationOrbitLabel_diagonal_identity translation right_constant
      left_constant source_fixed diagonal_inverse
  refine ⟨label, ?_, ?_, ?_⟩
  · intro x z
    rfl
  · intro a
    refine Quotient.inductionOn' a ?_
    intro x
    simpa [label] using diagonal_mk x
  · simpa [label] using
      (translationOrbitLabel_fixes_source_orbit translation right_constant
        left_constant source_fixed)

end AxiomPackFinalistOrbitClassification
