import ZtareProofs.AxiomPackT2AffineHiddenFiber

/-!
Exact packaging of the centered affine extraction fiber.

The imported module proves the tetrahedron criterion and the four extracted
operation formulas for

`T(x,y,z) = a(y) + mu(x,z)`.

This module packages the remaining classification statements inside that
affine chart: recovery of both parameters from `T`, injectivity of the chart,
the split extraction projection and its fixed fiber, and conjugacy under an
additive equivalence.  No statement about arbitrary set bijections is made.
-/

namespace AxiomPackT2AffineExtractionFiber

open AxiomPackFinalistOrbitClassification
open AxiomPackT2ReconstructionCounterexample
open AxiomPackT2AffineHiddenFiber

universe u v

variable {A : Type u} [AddCommGroup A]

/-! ## Recovery and injectivity of the affine chart -/

@[simp]
theorem affineOp_recover_linear
    (a : A →+ A) (mu : BiadditiveOp A) (y : A) :
    affineOp a mu 0 y 0 = a y := by
  simp [affineOp]

@[simp]
theorem affineOp_recover_product
    (a : A →+ A) (mu : BiadditiveOp A) (x z : A) :
    affineOp a mu x 0 z = mu x z := by
  simp [affineOp]

/-- Equality of affine ternary operations recovers equality of both the
middle linear part and the hidden biadditive product. -/
theorem affineOp_eq_iff
    (a b : A →+ A) (mu nu : BiadditiveOp A) :
    affineOp a mu = affineOp b nu ↔ a = b ∧ mu = nu := by
  constructor
  · intro h
    constructor
    · ext y
      have hy := congrFun (congrFun (congrFun h 0) y) 0
      simpa using hy
    · ext x z
      have hxz := congrFun (congrFun (congrFun h x) 0) z
      simpa using hxz
  · rintro ⟨rfl, rfl⟩
    rfl

/-- The centered affine parameterization by `(a, mu)` is injective. -/
theorem affineOp_parameterization_injective :
    Function.Injective
      (fun p : (A →+ A) × BiadditiveOp A => affineOp p.1 p.2) := by
  rintro ⟨a, mu⟩ ⟨b, nu⟩ h
  rcases (affineOp_eq_iff a b mu nu).1 h with ⟨rfl, rfl⟩
  rfl

/-! ## The extracted signature -/

/-- The four binary operations produced by the published extraction, kept as
one equality-bearing object. -/
@[ext]
structure ExtractionSignature (A : Type u) where
  star : A → A → A
  circle : A → A → A
  left : A → A → A
  right : A → A → A

/-- The signature determined by an additive automorphism. -/
def canonicalExtraction (a : A ≃+ A) : ExtractionSignature A where
  star := fun _ y => a y
  circle := fun x _ => a x
  left := fun x _ => x
  right := fun _ y => y

/-- The actual four operations extracted from an affine ternary operation. -/
def affineExtractionSignature
    (a : A ≃+ A) (mu : BiadditiveOp A) : ExtractionSignature A where
  star := extractedStar (affineOp a.toAddMonoidHom mu) 0
  circle := extractedCircle (affineOp a.toAddMonoidHom mu) 0
  left := extractedLeft (affineOp a.toAddMonoidHom mu) 0 a.symm
  right := extractedRight (affineOp a.toAddMonoidHom mu) 0 a.symm

/-- Extraction forgets `mu` exactly at the level of all four operations. -/
theorem affineExtractionSignature_eq_canonical
    (a : A ≃+ A) (mu : BiadditiveOp A) :
    affineExtractionSignature a mu = canonicalExtraction a := by
  apply ExtractionSignature.ext
  · funext x y
    simpa [affineExtractionSignature, canonicalExtraction] using
      affine_extractedStar a mu x y
  · funext x y
    simpa [affineExtractionSignature, canonicalExtraction] using
      affine_extractedCircle a mu x y
  · funext x y
    simpa [affineExtractionSignature, canonicalExtraction] using
      affine_extractedLeft a mu x y
  · funext x y
    simpa [affineExtractionSignature, canonicalExtraction] using
      affine_extractedRight a mu x y

/-- The canonical extracted signature still recovers `a`. -/
theorem canonicalExtraction_injective :
    Function.Injective (canonicalExtraction (A := A)) := by
  intro a b h
  apply AddEquiv.ext
  intro y
  have hstar := congrArg ExtractionSignature.star h
  have hy := congrFun (congrFun hstar 0) y
  simpa [canonicalExtraction] using hy

/-- Two affine operations have equal extracted four-groupoids exactly when
their additive automorphisms agree; their products may differ freely. -/
theorem affineExtractionSignature_eq_iff
    (a b : A ≃+ A) (mu nu : BiadditiveOp A) :
    affineExtractionSignature a mu = affineExtractionSignature b nu ↔
      a = b := by
  constructor
  · intro h
    apply canonicalExtraction_injective
    calc
      canonicalExtraction a = affineExtractionSignature a mu :=
        (affineExtractionSignature_eq_canonical a mu).symm
      _ = affineExtractionSignature b nu := h
      _ = canonicalExtraction b :=
        affineExtractionSignature_eq_canonical b nu
  · rintro rfl
    calc
      affineExtractionSignature a mu = canonicalExtraction a :=
        affineExtractionSignature_eq_canonical a mu
      _ = affineExtractionSignature a nu :=
        (affineExtractionSignature_eq_canonical a nu).symm

/-! ## Compatible products and the split extraction projection -/

/-- The exact products allowed over a fixed additive automorphism by the
affine tetrahedron criterion. -/
def CompatibleProduct (a : A →+ A) :=
  { mu : BiadditiveOp A //
      AssociativeMu mu ∧ LeftCentroid a mu ∧ RightCentroid a mu }

/-- Every automorphism has the compatible zero product. -/
def zeroCompatibleProduct (a : A →+ A) : CompatibleProduct a :=
  ⟨0, by simp [AssociativeMu, LeftCentroid, RightCentroid]⟩

/-- Total parameter space of centered affine elementary tetrahedron maps. -/
abbrev AffineTetrahedronParameter (A : Type u) [AddCommGroup A] :=
  Σ a : A ≃+ A, CompatibleProduct a.toAddMonoidHom

/-- The affine operation represented by a compatible parameter. -/
def affineParameterOp (d : AffineTetrahedronParameter A) : A → A → A → A :=
  affineOp d.1.toAddMonoidHom d.2.1

theorem affineParameterOp_tetrahedron
    (d : AffineTetrahedronParameter A) :
    TetrahedronEquation (affineParameterOp d) := by
  exact (affineOp_tetrahedron_iff d.1.toAddMonoidHom d.2.1).2 d.2.2

/-- The parameter-level extraction projection. -/
def affineExtractionProjection
    (d : AffineTetrahedronParameter A) : A ≃+ A :=
  d.1

/-- The zero-product section selected by the published reconstruction. -/
def affineZeroSection (a : A ≃+ A) : AffineTetrahedronParameter A :=
  ⟨a, zeroCompatibleProduct a.toAddMonoidHom⟩

@[simp]
theorem affineExtractionProjection_zeroSection (a : A ≃+ A) :
    affineExtractionProjection (affineZeroSection a) = a :=
  rfl

/-- The extraction projection is split-surjective. -/
theorem affineExtractionProjection_surjective :
    Function.Surjective
      (affineExtractionProjection : AffineTetrahedronParameter A → A ≃+ A) := by
  intro a
  exact ⟨affineZeroSection a, rfl⟩

/-- The extracted signature of a compatible parameter. -/
def affineParameterExtraction
    (d : AffineTetrahedronParameter A) : ExtractionSignature A :=
  affineExtractionSignature d.1 d.2.1

theorem affineParameterExtraction_eq_canonical
    (d : AffineTetrahedronParameter A) :
    affineParameterExtraction d =
      canonicalExtraction (affineExtractionProjection d) := by
  exact affineExtractionSignature_eq_canonical d.1 d.2.1

/-- The strict fiber over `a`, expressed using equality of the actual
extracted four-operation signature. -/
def AffineExtractionFiber (a : A ≃+ A) :=
  { d : AffineTetrahedronParameter A //
      affineParameterExtraction d = canonicalExtraction a }

/-- The actual extraction fiber over `a` is exactly the type of compatible
associative, centroid products over `a`. -/
def affineExtractionFiberEquiv (a : A ≃+ A) :
    AffineExtractionFiber a ≃ CompatibleProduct a.toAddMonoidHom where
  toFun d := by
    rcases d with ⟨⟨b, mu⟩, h⟩
    have hb : b = a := by
      apply canonicalExtraction_injective
      calc
        canonicalExtraction b = affineExtractionSignature b mu.1 :=
          (affineExtractionSignature_eq_canonical b mu.1).symm
        _ = canonicalExtraction a := h
    subst b
    exact mu
  invFun mu :=
    ⟨⟨a, mu⟩, affineExtractionSignature_eq_canonical a mu.1⟩
  left_inv d := by
    rcases d with ⟨⟨b, mu⟩, h⟩
    have hb : b = a := by
      apply canonicalExtraction_injective
      calc
        canonicalExtraction b = affineExtractionSignature b mu.1 :=
          (affineExtractionSignature_eq_canonical b mu.1).symm
        _ = canonicalExtraction a := h
    subst b
    rfl
  right_inv mu := by
    rfl

/-! ## Additive conjugacy -/

/-- Conjugacy of affine ternary operations under an additive equivalence is
equivalent to conjugacy of the linear part together with transport of the
biadditive product. -/
theorem affineOp_addEquiv_conjugacy_iff
    {B : Type v} [AddCommGroup B]
    (f : A ≃+ B) (a : A ≃+ A) (b : B ≃+ B)
    (mu : BiadditiveOp A) (nu : BiadditiveOp B) :
    (∀ x y z,
      f (affineOp a.toAddMonoidHom mu x y z) =
        affineOp b.toAddMonoidHom nu (f x) (f y) (f z)) ↔
      (∀ y, f (a y) = b (f y)) ∧
      (∀ x z, f (mu x z) = nu (f x) (f z)) := by
  constructor
  · intro h
    constructor
    · intro y
      simpa [affineOp] using h 0 y 0
    · intro x z
      simpa [affineOp] using h x 0 z
  · rintro ⟨hlinear, hproduct⟩ x y z
    simp only [affineOp, map_add]
    change f (a y) + f (mu x z) = b (f y) + nu (f x) (f z)
    rw [hlinear y, hproduct x z]

end AxiomPackT2AffineExtractionFiber
