import Mathlib.RingTheory.Polynomial.GaussLemma
import Mathlib.RingTheory.Derivation.Basic

/-!
# Primitive Darboux descent from a fraction field

For a normalized GCD domain `A` with fraction field `L`, this module chooses
the primitive part of Mathlib's denominator-cleared representative of a
polynomial in `L[X]`.  It proves association after mapping, irreducibility
descent, reflection of divisibility into arbitrary polynomials over `A`, and
descent of Darboux divisibility along an intertwining pair of derivations.
-/

noncomputable section

open scoped nonZeroDivisors Polynomial

namespace ZtareProofs.FormalPrimitiveDarbouxFractionDescent

open Polynomial IsLocalization

variable {A L : Type*} [CommRing A] [IsDomain A] [NormalizedGCDMonoid A]
  [Field L] [Algebra A L] [IsFractionRing A L]

/-- The canonical primitive representative obtained by first clearing
fraction-field denominators and then removing coefficient content. -/
def primitiveFractionRepresentative (hL : L[X]) : A[X] :=
  (integerNormalization (nonZeroDivisors A) hL).primPart

omit [IsDomain A] in
/-- The chosen representative is primitive, including at the zero input. -/
theorem primitive_primitiveFractionRepresentative (hL : L[X]) :
    (primitiveFractionRepresentative hL : A[X]).IsPrimitive :=
  (integerNormalization (nonZeroDivisors A) hL).isPrimitive_primPart

/-- A nonzero fraction-field polynomial is associated to the image of its
chosen primitive denominator-cleared representative. -/
theorem map_primitiveFractionRepresentative_associated
    {hL : L[X]} (hL0 : hL ≠ 0) :
    Associated
      ((primitiveFractionRepresentative hL : A[X]).map (algebraMap A L))
      hL := by
  let cleared : A[X] := integerNormalization (nonZeroDivisors A) hL
  obtain ⟨denominator, hdenominator, hcleared⟩ :=
    integerNormalization_spec (nonZeroDivisors A) hL
  have hcleared0 : cleared ≠ 0 := by
    change integerNormalization (nonZeroDivisors A) hL ≠ 0
    exact mt IsFractionRing.integerNormalization_eq_zero_iff.mp hL0
  have hcontent0 : cleared.content ≠ 0 := by
    rwa [Ne, content_eq_zero_iff]
  have hmapContent0 : algebraMap A L cleared.content ≠ 0 :=
    by simpa using (IsFractionRing.injective A L).ne hcontent0
  have hmapDenominator0 : algebraMap A L denominator ≠ 0 :=
    by simpa using
      (IsFractionRing.injective A L).ne (nonZeroDivisors.ne_zero hdenominator)
  have hcontentUnit : IsUnit (C (algebraMap A L cleared.content) : L[X]) :=
    isUnit_C.mpr hmapContent0.isUnit
  have hdenominatorUnit :
      IsUnit (C (algebraMap A L denominator) : L[X]) :=
    isUnit_C.mpr hmapDenominator0.isUnit
  have hfactor :
      C (algebraMap A L cleared.content) *
          (primitiveFractionRepresentative hL : A[X]).map (algebraMap A L) =
        C (algebraMap A L denominator) * hL := by
    change
      C (algebraMap A L cleared.content) *
          cleared.primPart.map (algebraMap A L) =
        C (algebraMap A L denominator) * hL
    rw [← map_C, ← Polynomial.map_mul,
      ← cleared.eq_C_content_mul_primPart]
    simpa [cleared, Algebra.smul_def] using hcleared
  exact
    (associated_unit_mul_left
        ((primitiveFractionRepresentative hL : A[X]).map (algebraMap A L))
        (C (algebraMap A L cleared.content)) hcontentUnit).symm |>.trans <|
      (Associated.of_eq hfactor).trans
        (associated_unit_mul_left hL
          (C (algebraMap A L denominator)) hdenominatorUnit)

/-- Irreducibility contracts from the fraction-field polynomial to the
chosen primitive representative. -/
theorem irreducible_primitiveFractionRepresentative
    {hL : L[X]} (hirr : Irreducible hL) :
    Irreducible (primitiveFractionRepresentative hL : A[X]) := by
  have hassociated :=
    map_primitiveFractionRepresentative_associated (A := A) (L := L)
      hirr.ne_zero
  have hmappedIrreducible :
      Irreducible
        ((primitiveFractionRepresentative hL : A[X]).map (algebraMap A L)) :=
    hassociated.symm.irreducible hirr
  have hprimitive :=
    primitive_primitiveFractionRepresentative (A := A) (L := L) hL
  exact hprimitive.irreducible_of_irreducible_map_of_injective
    (IsFractionRing.injective A L) hmappedIrreducible

/-- Gauss reflection with a primitive divisor and an arbitrary target
polynomial.  The target is reduced to its primitive part internally. -/
theorem IsPrimitive.dvd_of_map_dvd_fraction
    {p q : A[X]} (hp : p.IsPrimitive)
    (hdvd : p.map (algebraMap A L) ∣ q.map (algebraMap A L)) :
    p ∣ q := by
  by_cases hq0 : q = 0
  · subst q
    exact dvd_zero p
  have hcontent0 : q.content ≠ 0 := by
    rwa [Ne, content_eq_zero_iff]
  have hmapContent0 : algebraMap A L q.content ≠ 0 := by
    simpa using (IsFractionRing.injective A L).ne hcontent0
  have hcontentUnit : IsUnit (C (algebraMap A L q.content) : L[X]) :=
    isUnit_C.mpr hmapContent0.isUnit
  have hfactor :
      C (algebraMap A L q.content) *
          q.primPart.map (algebraMap A L) =
        q.map (algebraMap A L) := by
    rw [← map_C, ← Polynomial.map_mul, ← q.eq_C_content_mul_primPart]
  have htargetAssociated :
      Associated (q.primPart.map (algebraMap A L))
        (q.map (algebraMap A L)) :=
    (associated_unit_mul_right
      (q.primPart.map (algebraMap A L))
      (C (algebraMap A L q.content)) hcontentUnit).trans
        (Associated.of_eq hfactor)
  have hdvdPrimitiveTarget :
      p.map (algebraMap A L) ∣ q.primPart.map (algebraMap A L) :=
    htargetAssociated.dvd_iff_dvd_right.mpr hdvd
  exact
    (hp.dvd_of_fraction_map_dvd_fraction_map q.isPrimitive_primPart
      hdvdPrimitiveTarget).trans q.primPart_dvd

/-- Divisibility by the fraction-field polynomial reflects to divisibility
by its chosen primitive representative in any polynomial over `A`. -/
theorem primitiveFractionRepresentative_dvd_of_dvd_map
    {hL : L[X]} (hL0 : hL ≠ 0) {q : A[X]}
    (hdvd : hL ∣ q.map (algebraMap A L)) :
    (primitiveFractionRepresentative hL : A[X]) ∣ q := by
  have hassociated :=
    map_primitiveFractionRepresentative_associated (A := A) (L := L) hL0
  have hmappedDvd :
      (primitiveFractionRepresentative hL : A[X]).map (algebraMap A L) ∣
        q.map (algebraMap A L) :=
    hassociated.dvd_iff_dvd_left.mpr hdvd
  exact
    IsPrimitive.dvd_of_map_dvd_fraction
      (primitive_primitiveFractionRepresentative (A := A) (L := L) hL)
      hmappedDvd

/-- Darboux divisibility is invariant under replacing a divisor by an
associated element.  The derivative of the associating unit is retained in
the Leibniz calculation rather than assumed to vanish. -/
theorem dvd_derivation_of_associated
    {R : Type*} [CommRing R] (D : Derivation ℤ R R) {p q : R}
    (hpq : Associated p q) (hq : q ∣ D q) :
    p ∣ D p := by
  have hpDq : p ∣ D q := hpq.dvd.trans hq
  obtain ⟨unit, hunit⟩ := hpq
  rw [← hunit, D.leibniz, smul_eq_mul] at hpDq
  have hpUnitMulDerivative : p ∣ (unit : R) * D p :=
    (dvd_add_right (dvd_mul_right p (D (unit : R)))).mp hpDq
  exact
    (associated_unit_mul_left (D p) (unit : R) unit.isUnit).dvd_iff_dvd_right.mp
      hpUnitMulDerivative

/-- If polynomial derivations over `A` and its fraction field intertwine the
coefficient map, Darboux divisibility of a nonzero fraction-field polynomial
descends to its chosen primitive representative. -/
theorem primitiveFractionRepresentative_dvd_derivation
    {hL : L[X]} (hL0 : hL ≠ 0)
    (dA : Derivation ℤ A[X] A[X]) (dL : Derivation ℤ L[X] L[X])
    (hcommute : ∀ polynomial : A[X],
      (dA polynomial).map (algebraMap A L) =
        dL (polynomial.map (algebraMap A L)))
    (hdarboux : hL ∣ dL hL) :
    (primitiveFractionRepresentative hL : A[X]) ∣
      dA (primitiveFractionRepresentative hL) := by
  let hA : A[X] := primitiveFractionRepresentative hL
  have hassociated : Associated (hA.map (algebraMap A L)) hL := by
    exact map_primitiveFractionRepresentative_associated (A := A) (L := L) hL0
  have hmappedDarboux :
      hA.map (algebraMap A L) ∣ dL (hA.map (algebraMap A L)) :=
    dvd_derivation_of_associated dL hassociated hdarboux
  have hmappedDerivative :
      hA.map (algebraMap A L) ∣ (dA hA).map (algebraMap A L) := by
    rwa [hcommute]
  exact
    IsPrimitive.dvd_of_map_dvd_fraction
      (primitive_primitiveFractionRepresentative (A := A) (L := L) hL)
      hmappedDerivative

/-- Aggregated primitive contraction certificate for an irreducible Darboux
polynomial over a fraction field. -/
theorem primitive_darboux_fraction_descent_terminal_certificate
    {hL : L[X]} (hirr : Irreducible hL)
    (dA : Derivation ℤ A[X] A[X]) (dL : Derivation ℤ L[X] L[X])
    (hcommute : ∀ polynomial : A[X],
      (dA polynomial).map (algebraMap A L) =
        dL (polynomial.map (algebraMap A L)))
    (hdarboux : hL ∣ dL hL) :
    let hA : A[X] := primitiveFractionRepresentative hL
    hA.IsPrimitive ∧
      Irreducible hA ∧
      Associated (hA.map (algebraMap A L)) hL ∧
      (∀ q : A[X], hL ∣ q.map (algebraMap A L) → hA ∣ q) ∧
      hA ∣ dA hA := by
  dsimp only
  exact ⟨
    primitive_primitiveFractionRepresentative (A := A) (L := L) hL,
    irreducible_primitiveFractionRepresentative (A := A) (L := L) hirr,
    map_primitiveFractionRepresentative_associated (A := A) (L := L)
      hirr.ne_zero,
    fun _ hdvd => primitiveFractionRepresentative_dvd_of_dvd_map
      (A := A) (L := L) hirr.ne_zero hdvd,
    primitiveFractionRepresentative_dvd_derivation
      (A := A) (L := L) hirr.ne_zero dA dL hcommute hdarboux⟩

end ZtareProofs.FormalPrimitiveDarbouxFractionDescent
