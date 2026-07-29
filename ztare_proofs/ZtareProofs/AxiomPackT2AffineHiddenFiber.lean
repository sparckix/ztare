import Mathlib.Data.ZMod.Basic
import ZtareProofs.AxiomPackT2ReconstructionCounterexample

/-!
The centered affine hidden fiber for the second-tetrahedral-groupoid
reconstruction question.

For an additive endomorphism `a` and a biadditive operation `mu`, the ternary
operation studied here is

`T x y z = a y + mu x z`.

The tetrahedron equation is equivalent to associativity of `mu` together
with the two centroid laws relating `a` and `mu`.  When `a` is an additive
equivalence, the published extraction at basepoint zero sees only `a`; it
forgets `mu` completely.
-/

namespace AxiomPackT2AffineHiddenFiber

open AxiomPackFinalistOrbitClassification
open AxiomPackT2ReconstructionCounterexample

universe u

variable {A : Type u} [AddCommGroup A]

/-- A biadditive binary operation, curried as an additive homomorphism in
each argument. -/
abbrev BiadditiveOp (A : Type u) [AddCommGroup A] := A →+ A →+ A

/-- The centered affine elementary operation `T(x,y,z) = a(y) + mu(x,z)`. -/
def affineOp (a : A →+ A) (mu : BiadditiveOp A) (x y z : A) : A :=
  a y + mu x z

/-- Associativity of the possibly noncommutative, nonunital operation `mu`. -/
def AssociativeMu (mu : BiadditiveOp A) : Prop :=
  ∀ x z q, mu (mu x z) q = mu x (mu z q)

/-- `a` commutes with applying `mu` in its first argument. -/
def LeftCentroid (a : A →+ A) (mu : BiadditiveOp A) : Prop :=
  ∀ x z, mu (a x) z = a (mu x z)

/-- `a` commutes with applying `mu` in its second argument. -/
def RightCentroid (a : A →+ A) (mu : BiadditiveOp A) : Prop :=
  ∀ x z, a (mu x z) = mu x (a z)

/-- The affine operation satisfies the tetrahedron equation exactly when
`mu` is associative and `a` satisfies both centroid laws.  No invertibility
of `a`, commutativity of `mu`, or unit for `mu` is used. -/
theorem affineOp_tetrahedron_iff
    (a : A →+ A) (mu : BiadditiveOp A) :
    TetrahedronEquation (affineOp a mu) ↔
      AssociativeMu mu ∧ LeftCentroid a mu ∧ RightCentroid a mu := by
  constructor
  · intro tetrahedron
    constructor
    · intro x z q
      simpa [affineOp] using tetrahedron x 0 z 0 0 q
    · constructor
      · intro y q
        simpa [affineOp] using tetrahedron 0 y 0 0 0 q
      · intro x p
        simpa [affineOp] using tetrahedron x 0 0 0 p 0
  · rintro ⟨associative, left_centroid, right_centroid⟩
    intro x y z t p q
    simp only [affineOp, map_add, AddMonoidHom.add_apply]
    rw [right_centroid x p, left_centroid y q, associative x z q]
    abel

/-- The inverse of the affine elementary map when the middle linear part is
an additive equivalence. -/
def affineElementaryInverse (a : A ≃+ A) (mu : BiadditiveOp A) :
    A × A × A → A × A × A
  | (x, w, z) => (x, a.symm (w - mu x z), z)

theorem affineElementaryInverse_leftInverse
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    Function.LeftInverse (affineElementaryInverse a mu)
      (elementaryMap (affineOp a.toAddMonoidHom mu)) := by
  rintro ⟨x, y, z⟩
  simp [affineElementaryInverse, elementaryMap, affineOp]

theorem affineElementaryInverse_rightInverse
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    Function.RightInverse (affineElementaryInverse a mu)
      (elementaryMap (affineOp a.toAddMonoidHom mu)) := by
  rintro ⟨x, w, z⟩
  simp [affineElementaryInverse, elementaryMap, affineOp]

/-- Invertibility of `a` makes the elementary map bijective, independently
of the tetrahedron and centroid laws. -/
theorem affine_elementaryMap_bijective
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    Function.Bijective (elementaryMap (affineOp a.toAddMonoidHom mu)) := by
  exact ⟨(affineElementaryInverse_leftInverse a mu).injective,
    (affineElementaryInverse_rightInverse a mu).surjective⟩

/-- The five extraction hypotheses of Bardakov et al. at basepoint zero,
with the inverse-slice map `a.symm`, in the published orientation. -/
theorem affine_extraction_hypotheses
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    ExtractionHypotheses (affineOp a.toAddMonoidHom mu) 0 a.symm := by
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · simp [affineOp]
  · intro x
    simp [affineOp]
  · intro x
    simp [affineOp]
  · intro x y
    simp [affineOp]
  · intro x y
    simp [affineOp]

@[simp]
theorem affine_extractedStar
    (a : A ≃+ A) (mu : BiadditiveOp A) (x y : A) :
    extractedStar (affineOp a.toAddMonoidHom mu) 0 x y = a y := by
  simp [extractedStar, affineOp]

@[simp]
theorem affine_extractedCircle
    (a : A ≃+ A) (mu : BiadditiveOp A) (x y : A) :
    extractedCircle (affineOp a.toAddMonoidHom mu) 0 x y = a x := by
  simp [extractedCircle, affineOp]

@[simp]
theorem affine_extractedLeft
    (a : A ≃+ A) (mu : BiadditiveOp A) (x y : A) :
    extractedLeft (affineOp a.toAddMonoidHom mu) 0 a.symm x y = x := by
  simp [extractedLeft, affineOp]

@[simp]
theorem affine_extractedRight
    (a : A ≃+ A) (mu : BiadditiveOp A) (x y : A) :
    extractedRight (affineOp a.toAddMonoidHom mu) 0 a.symm x y = y := by
  simp [extractedRight, affineOp]

/-- The extracted second tetrahedral 4-groupoid depends on `a` and forgets
`mu`. -/
theorem affine_extracted_t2_groupoid
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    T2GroupoidLaws
      (extractedStar (affineOp a.toAddMonoidHom mu) 0)
      (extractedCircle (affineOp a.toAddMonoidHom mu) 0)
      (extractedLeft (affineOp a.toAddMonoidHom mu) 0 a.symm)
      (extractedRight (affineOp a.toAddMonoidHom mu) 0 a.symm) := by
  simp [T2GroupoidLaws, extractedStar, extractedCircle, extractedLeft,
    extractedRight, affineOp]

@[simp]
theorem affine_reconstructed
    (a : A ≃+ A) (mu : BiadditiveOp A) (x y z : A) :
    reconstructed (affineOp a.toAddMonoidHom mu) 0 a.symm x y z = a y := by
  simp [reconstructed, extractedRight, extractedCircle, affineOp]

/-- Reconstruction holds for the affine family exactly when the forgotten
biadditive operation is identically zero. -/
theorem affine_reconstruction_iff_mu_eq_zero
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    (∀ x y z,
      affineOp a.toAddMonoidHom mu x y z =
        reconstructed (affineOp a.toAddMonoidHom mu) 0 a.symm x y z) ↔
      mu = 0 := by
  constructor
  · intro reconstructs
    ext x z
    simpa [affineOp, reconstructed, extractedRight, extractedCircle] using
      reconstructs x 0 z
  · rintro rfl
    intro x y z
    simp [affineOp, reconstructed, extractedRight, extractedCircle]

/-- Combining the exact tetrahedron criterion with elementary-map
bijectivity. -/
theorem affine_is_elementaryTwoSolution
    (a : A ≃+ A) (mu : BiadditiveOp A)
    (associative : AssociativeMu mu)
    (left_centroid : LeftCentroid a.toAddMonoidHom mu)
    (right_centroid : RightCentroid a.toAddMonoidHom mu) :
    ElementaryTwoSolution (affineOp a.toAddMonoidHom mu) := by
  exact ⟨(affineOp_tetrahedron_iff a.toAddMonoidHom mu).2
      ⟨associative, left_centroid, right_centroid⟩,
    affine_elementaryMap_bijective a mu⟩

section ZModTwo

/-- Multiplication on `ZMod 2`, packaged as a biadditive operation. -/
def zmodTwoMul : BiadditiveOp (ZMod 2) where
  toFun x :=
    { toFun := fun z => x * z
      map_zero' := mul_zero x
      map_add' := fun y z => mul_add x y z }
  map_zero' := by
    ext z
    exact zero_mul z
  map_add' := by
    intro x y
    ext z
    exact add_mul x y z

/-- The cardinality-two affine operation `T(x,y,z) = y + x*z`. -/
def zmodTwoAffine (x y z : ZMod 2) : ZMod 2 :=
  affineOp (AddMonoidHom.id (ZMod 2)) zmodTwoMul x y z

@[simp]
theorem zmodTwoAffine_apply (x y z : ZMod 2) :
    zmodTwoAffine x y z = y + x * z :=
  rfl

theorem zmodTwoMul_associative : AssociativeMu zmodTwoMul := by
  intro x z q
  exact mul_assoc x z q

theorem zmodTwoMul_leftCentroid :
    LeftCentroid (AddMonoidHom.id (ZMod 2)) zmodTwoMul := by
  intro x z
  rfl

theorem zmodTwoMul_rightCentroid :
    RightCentroid (AddMonoidHom.id (ZMod 2)) zmodTwoMul := by
  intro x z
  rfl

theorem zmodTwoAffine_tetrahedron :
    TetrahedronEquation zmodTwoAffine := by
  exact (affineOp_tetrahedron_iff (AddMonoidHom.id (ZMod 2)) zmodTwoMul).2
    ⟨zmodTwoMul_associative, zmodTwoMul_leftCentroid,
      zmodTwoMul_rightCentroid⟩

theorem zmodTwoAffine_elementaryMap_bijective :
    Function.Bijective (elementaryMap zmodTwoAffine) := by
  simpa [zmodTwoAffine] using
    (affine_elementaryMap_bijective (AddEquiv.refl (ZMod 2)) zmodTwoMul)

theorem zmodTwoAffine_is_elementaryTwoSolution :
    ElementaryTwoSolution zmodTwoAffine :=
  ⟨zmodTwoAffine_tetrahedron, zmodTwoAffine_elementaryMap_bijective⟩

theorem zmodTwoAffine_extraction_hypotheses :
    ExtractionHypotheses zmodTwoAffine 0 (fun x => x) := by
  simpa [zmodTwoAffine] using
    (affine_extraction_hypotheses (AddEquiv.refl (ZMod 2)) zmodTwoMul)

theorem zmodTwoAffine_extracted_t2_groupoid :
    T2GroupoidLaws
      (extractedStar zmodTwoAffine 0)
      (extractedCircle zmodTwoAffine 0)
      (extractedLeft zmodTwoAffine 0 (fun x => x))
      (extractedRight zmodTwoAffine 0 (fun x => x)) := by
  simpa [zmodTwoAffine] using
    (affine_extracted_t2_groupoid (AddEquiv.refl (ZMod 2)) zmodTwoMul)

theorem zmodTwoAffine_reconstruction_failure :
    zmodTwoAffine 1 0 1 ≠
      reconstructed zmodTwoAffine 0 (fun x => x) 1 0 1 := by
  norm_num [zmodTwoAffine, affineOp, reconstructed, extractedRight,
    extractedCircle, zmodTwoMul]

/-- A complete two-element counterexample certificate in the exact published
orientation. -/
theorem zmodTwoAffine_t2_reconstruction_counterexample :
    ElementaryTwoSolution zmodTwoAffine ∧
      ExtractionHypotheses zmodTwoAffine 0 (fun x => x) ∧
      T2GroupoidLaws
        (extractedStar zmodTwoAffine 0)
        (extractedCircle zmodTwoAffine 0)
        (extractedLeft zmodTwoAffine 0 (fun x => x))
        (extractedRight zmodTwoAffine 0 (fun x => x)) ∧
      ¬ ∀ x y z,
        zmodTwoAffine x y z =
          reconstructed zmodTwoAffine 0 (fun x => x) x y z := by
  refine ⟨zmodTwoAffine_is_elementaryTwoSolution,
    zmodTwoAffine_extraction_hypotheses,
    zmodTwoAffine_extracted_t2_groupoid, ?_⟩
  intro reconstructs
  exact zmodTwoAffine_reconstruction_failure (reconstructs 1 0 1)

end ZModTwo

end AxiomPackT2AffineHiddenFiber
