import Mathlib.FieldTheory.RatFunc.Basic
import Mathlib.Tactic
import ZtareProofs.FormalRatFuncLaurentTangentCarrier

/-!
# An affine-centered rational differential field in Laurent series

The zero-centered tangent carrier is extended to a finite real basepoint.
The rational variable is sent to `center + coordinate`, while differentiation
is normalized only by the tangent derivative.  Translation occurs at the
polynomial layer before fraction-field localization.
-/

namespace FormalAffineRatFuncLaurentTangentCarrier

open Polynomial PowerSeries
open scoped LaurentSeries

open FormalRatFuncLaurentTangentCarrier

noncomputable section

abbrev RF := RatFunc ℝ
abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

/-- The affine base series representing the distinguished rational variable. -/
def affineCoordinate (center : ℝ) (coordinate : PS) : PS :=
  PowerSeries.C (center : ℂ) + coordinate

/-- Real-polynomial evaluation at an affine complex tangent coordinate. -/
def affineRealPolynomialToLaurent
    (center : ℝ) (coordinate : PS) : ℝ[X] →+* LS :=
  (algebraMap PS LS).comp
    (Polynomial.eval₂RingHom
      ((PowerSeries.C : ℂ →+* PS).comp (algebraMap ℝ ℂ))
      (affineCoordinate center coordinate))

@[simp]
theorem affineRealPolynomialToLaurent_apply
    (center : ℝ) (coordinate : PS) (polynomial : ℝ[X]) :
    affineRealPolynomialToLaurent center coordinate polynomial =
      algebraMap PS LS
        (Polynomial.aeval (affineCoordinate center coordinate)
          (polynomial.map (algebraMap ℝ ℂ))) := by
  simp [affineRealPolynomialToLaurent, Polynomial.aeval_def,
    Polynomial.eval₂_map]

theorem affineRealPolynomialToLaurent_injective
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    Function.Injective (affineRealPolynomialToLaurent center coordinate) := by
  intro first second hequal
  by_contra hne
  have hdifference : first - second ≠ 0 := sub_ne_zero.mpr hne
  have hcomplex :
      (first - second).map (algebraMap ℝ ℂ) ≠ 0 := by
    simpa only [Polynomial.map_zero] using
      (Polynomial.map_injective (algebraMap ℝ ℂ)
        Complex.ofReal_injective).ne hdifference
  let translated : ℂ[X] :=
    ((first - second).map (algebraMap ℝ ℂ)).comp
      (Polynomial.X + Polynomial.C (center : ℂ))
  have htranslated : translated ≠ 0 := by
    exact (Polynomial.comp_X_add_C_ne_zero_iff).2 hcomplex
  have hpower : Polynomial.aeval coordinate translated ≠ 0 :=
    FormalTangentSubstitutionInjectivity.polynomial_aeval_ne_zero_of_invertible_linear
      coordinate hconstant translated htranslated
  have haeval :
      Polynomial.aeval (affineCoordinate center coordinate)
          ((first - second).map (algebraMap ℝ ℂ)) =
        Polynomial.aeval coordinate translated := by
    dsimp [translated]
    rw [Polynomial.aeval_comp]
    simp [affineCoordinate, add_comm]
  have hlaurent :
      algebraMap PS LS
        (Polynomial.aeval (affineCoordinate center coordinate)
          ((first - second).map (algebraMap ℝ ℂ))) ≠ 0 := by
    rw [haeval]
    simpa only [map_zero] using
      (FaithfulSMul.algebraMap_injective PS LS).ne hpower
  apply hlaurent
  rw [← affineRealPolynomialToLaurent_apply]
  simp only [map_sub, hequal, sub_self]

def affineDenominatorCondition
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    nonZeroDivisors ℝ[X] ≤
      (nonZeroDivisors LS).comap
        (affineRealPolynomialToLaurent center coordinate) :=
  nonZeroDivisors_le_comap_nonZeroDivisors_of_injective _
    (affineRealPolynomialToLaurent_injective center coordinate hconstant)

/-- The affine-centered embedding of the rational-function field. -/
def affineRatFuncToLaurent
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] : RF →+* LS :=
  RatFunc.liftRingHom (affineRealPolynomialToLaurent center coordinate)
    (affineDenominatorCondition center coordinate hconstant)

theorem affineRatFuncToLaurent_injective
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    Function.Injective
      (affineRatFuncToLaurent center coordinate hconstant) :=
  RatFunc.liftRingHom_injective
    (affineRealPolynomialToLaurent center coordinate)
    (affineRealPolynomialToLaurent_injective center coordinate hconstant)

@[reducible]
def affineRatFuncLaurentAlgebra
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] : Algebra RF LS :=
  (affineRatFuncToLaurent center coordinate hconstant).toAlgebra

@[simp]
theorem affineRatFuncToLaurent_algebraMap
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] (polynomial : ℝ[X]) :
    affineRatFuncToLaurent center coordinate hconstant
        (algebraMap ℝ[X] RF polynomial) =
      affineRealPolynomialToLaurent center coordinate polynomial := by
  exact RatFunc.liftRingHom_algebraMap _ _ polynomial

@[simp]
theorem affineRatFuncToLaurent_X
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    affineRatFuncToLaurent center coordinate hconstant RatFunc.X =
      algebraMap PS LS (affineCoordinate center coordinate) := by
  rw [← RatFunc.algebraMap_X, affineRatFuncToLaurent_algebraMap]
  simp [affineRealPolynomialToLaurent]

theorem coordinateDerivation_affineRealPolynomialToLaurent
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] (polynomial : ℝ[X]) :
    coordinateDerivation coordinate
        (affineRealPolynomialToLaurent center coordinate polynomial) =
      affineRealPolynomialToLaurent center coordinate
        polynomial.derivative := by
  rw [affineRealPolynomialToLaurent_apply,
    affineRealPolynomialToLaurent_apply,
    coordinateDerivation_algebraMap]
  have hchain :=
    (PowerSeries.derivative ℂ).comp_aeval_eq
      (a := affineCoordinate center coordinate)
      (polynomial.map (algebraMap ℝ ℂ))
  simp only [smul_eq_mul] at hchain
  have haffineDerivative :
      d⁄dX ℂ (affineCoordinate center coordinate) =
        d⁄dX ℂ coordinate := by
    simp [affineCoordinate]
  rw [hchain, haffineDerivative, map_mul]
  rw [show Polynomial.derivative
      (polynomial.map (algebraMap ℝ ℂ)) =
        polynomial.derivative.map (algebraMap ℝ ℂ) by
      exact Polynomial.derivative_map polynomial (algebraMap ℝ ℂ)]
  have hderivative := coordinateDerivative_ne_zero coordinate
  calc
    (algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
        (algebraMap PS LS
            (Polynomial.aeval (affineCoordinate center coordinate)
              (Polynomial.map (algebraMap ℝ ℂ)
                polynomial.derivative)) *
          algebraMap PS LS (d⁄dX ℂ coordinate)) =
      algebraMap PS LS
          (Polynomial.aeval (affineCoordinate center coordinate)
            (Polynomial.map (algebraMap ℝ ℂ)
              polynomial.derivative)) *
        ((algebraMap PS LS (d⁄dX ℂ coordinate))⁻¹ *
          algebraMap PS LS (d⁄dX ℂ coordinate)) := by ring
    _ = _ := by rw [inv_mul_cancel₀ hderivative, mul_one]

/-- Ordinary rational differentiation intertwines the affine Laurent
embedding and the normalized tangent derivation. -/
theorem affineRatFuncToLaurent_derivative
    (center : ℝ) (coordinate : PS)
    (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] (value : RF) :
    affineRatFuncToLaurent center coordinate hconstant
        (FormalRationalFunctionDerivationLocalOrder.rationalDerivative value) =
      coordinateDerivation coordinate
        (affineRatFuncToLaurent center coordinate hconstant value) := by
  induction value using RatFunc.induction_on with
  | f numerator denominator hdenominator =>
      have hmappedDenominator :
          affineRealPolynomialToLaurent center coordinate denominator ≠ 0 := by
        simpa only [map_zero] using
          (affineRealPolynomialToLaurent_injective center coordinate
            hconstant).ne hdenominator
      rw [FormalRationalFunctionDerivationLocalOrder.rationalDerivative_div]
      rw [FormalRationalFunctionDerivationLocalOrder.quotientDerivative]
      simp only [map_div₀, map_sub, map_mul, map_pow,
        affineRatFuncToLaurent_algebraMap]
      rw [FormalRatFuncLaurentTangentCarrier.derivation_div _ _ _
        hmappedDenominator]
      rw [coordinateDerivation_affineRealPolynomialToLaurent
          center coordinate hconstant numerator,
        coordinateDerivation_affineRealPolynomialToLaurent
          center coordinate hconstant denominator]

theorem affine_ratfunc_laurent_tangent_carrier_terminal_certificate :
    ∀ (center : ℝ) (coordinate : PS)
      (hconstant : coordinate.constantCoeff = 0)
      [Invertible (coordinate.coeff 1)],
      Function.Injective
          (affineRatFuncToLaurent center coordinate hconstant) ∧
      affineRatFuncToLaurent center coordinate hconstant RatFunc.X =
        algebraMap PS LS (affineCoordinate center coordinate) ∧
      ∀ value : RF,
        affineRatFuncToLaurent center coordinate hconstant
            (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
              value) =
          coordinateDerivation coordinate
            (affineRatFuncToLaurent center coordinate hconstant value) := by
  intro center coordinate hconstant _
  exact ⟨affineRatFuncToLaurent_injective center coordinate hconstant,
    affineRatFuncToLaurent_X center coordinate hconstant,
    affineRatFuncToLaurent_derivative center coordinate hconstant⟩

end

end FormalAffineRatFuncLaurentTangentCarrier
