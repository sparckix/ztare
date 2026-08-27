import Mathlib.FieldTheory.RatFunc.Basic
import Mathlib.RingTheory.LaurentSeries
import Mathlib.Tactic
import ZtareProofs.FormalLocalizationDerivationExtension
import ZtareProofs.FormalRationalFunctionDerivationLocalOrder
import ZtareProofs.FormalTangentSubstitutionInjectivity

/-!
# A rational differential field inside a Laurent tangent chart

A zero-constant formal coordinate with invertible linear coefficient is a
valid local parameter.  Evaluation in that coordinate embeds real rational
functions into complex Laurent series.  Rescaling formal Laurent
differentiation by the inverse coordinate derivative transports the ordinary
rational derivative exactly.

The construction is coordinate-covariant: the distinguished rational
variable is sent to the supplied tangent germ, not necessarily to `X`.
-/

namespace FormalRatFuncLaurentTangentCarrier

open Polynomial PowerSeries
open scoped LaurentSeries

noncomputable section

abbrev RF := RatFunc ℝ
abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

noncomputable local instance laurentCanonicalIntAlgebra : Algebra ℤ LS :=
  Ring.toIntAlgebra LS

/-- Evaluation of a real polynomial on a complex power-series coordinate,
followed by the canonical embedding into Laurent series. -/
def realPolynomialToLaurent (coordinate : PS) : ℝ[X] →+* LS :=
  (algebraMap PS LS).comp
    (Polynomial.eval₂RingHom
      ((PowerSeries.C : ℂ →+* PS).comp (algebraMap ℝ ℂ)) coordinate)

@[simp]
theorem realPolynomialToLaurent_apply
    (coordinate : PS) (polynomial : ℝ[X]) :
    realPolynomialToLaurent coordinate polynomial =
      algebraMap PS LS
        (Polynomial.aeval coordinate
          (polynomial.map (algebraMap ℝ ℂ))) := by
  simp [realPolynomialToLaurent, Polynomial.aeval_def,
    Polynomial.eval₂_map]

/-- A tangent coordinate makes polynomial evaluation faithful. -/
theorem realPolynomialToLaurent_injective
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    Function.Injective (realPolynomialToLaurent coordinate) := by
  intro first second hequal
  by_contra hne
  have hdifference : first - second ≠ 0 := sub_ne_zero.mpr hne
  have hcomplex :
      (first - second).map (algebraMap ℝ ℂ) ≠ 0 :=
    by
      simpa only [Polynomial.map_zero] using
        (Polynomial.map_injective (algebraMap ℝ ℂ)
          Complex.ofReal_injective).ne hdifference
  have hpower :
      Polynomial.aeval coordinate
          ((first - second).map (algebraMap ℝ ℂ)) ≠ 0 :=
    FormalTangentSubstitutionInjectivity.polynomial_aeval_ne_zero_of_invertible_linear
      coordinate hconstant _ hcomplex
  have hlaurent :
      algebraMap PS LS
        (Polynomial.aeval coordinate
          ((first - second).map (algebraMap ℝ ℂ))) ≠ 0 :=
    by
      simpa only [map_zero] using
        (FaithfulSMul.algebraMap_injective PS LS).ne hpower
  apply hlaurent
  rw [← realPolynomialToLaurent_apply]
  simp only [map_sub, hequal, sub_self]

/-- Every nonzero polynomial denominator stays nonzero in the Laurent
chart. -/
def denominatorCondition
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    nonZeroDivisors ℝ[X] ≤
      (nonZeroDivisors LS).comap (realPolynomialToLaurent coordinate) :=
  nonZeroDivisors_le_comap_nonZeroDivisors_of_injective _
    (realPolynomialToLaurent_injective coordinate hconstant)

/-- The induced embedding of the real rational-function field. -/
def ratFuncToLaurent
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] : RF →+* LS :=
  RatFunc.liftRingHom (realPolynomialToLaurent coordinate)
    (denominatorCondition coordinate hconstant)

theorem ratFuncToLaurent_injective
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    Function.Injective (ratFuncToLaurent coordinate hconstant) :=
  RatFunc.liftRingHom_injective
    (realPolynomialToLaurent coordinate)
    (realPolynomialToLaurent_injective coordinate hconstant)

/-- The field algebra structure owned by the tangent-coordinate embedding. -/
@[reducible]
def ratFuncLaurentAlgebra
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] : Algebra RF LS :=
  (ratFuncToLaurent coordinate hconstant).toAlgebra

@[simp]
theorem ratFuncToLaurent_algebraMap
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] (polynomial : ℝ[X]) :
    ratFuncToLaurent coordinate hconstant
        (algebraMap ℝ[X] RF polynomial) =
      realPolynomialToLaurent coordinate polynomial := by
  exact RatFunc.liftRingHom_algebraMap _ _ polynomial

@[simp]
theorem ratFuncToLaurent_X
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] :
    ratFuncToLaurent coordinate hconstant RatFunc.X =
      algebraMap PS LS coordinate := by
  rw [← RatFunc.algebraMap_X, ratFuncToLaurent_algebraMap]
  simp [realPolynomialToLaurent]

/-- The coordinate derivative is nonzero because its constant coefficient is
the invertible linear coefficient of the coordinate. -/
theorem coordinateDerivative_ne_zero
    (coordinate : PS) [Invertible (coordinate.coeff 1)] :
    algebraMap PS LS (PowerSeries.derivative ℂ coordinate) ≠ 0 := by
  have hpower : PowerSeries.derivative ℂ coordinate ≠ 0 := by
    intro hzero
    have hcoefficient := congrArg (PowerSeries.coeff 0) hzero
    norm_num [PowerSeries.coeff_derivative] at hcoefficient
    exact Invertible.ne_zero (coordinate.coeff 1) hcoefficient
  simpa only [map_zero] using
    (FaithfulSMul.algebraMap_injective PS LS).ne hpower

/-- Differentiation with respect to the supplied rational coordinate. -/
def coordinateDerivation (coordinate : PS) : Derivation ℤ LS LS :=
  (algebraMap PS LS (PowerSeries.derivative ℂ coordinate))⁻¹ •
    FormalLocalizationDerivationExtension.laurentSeriesDerivation ℂ

@[simp]
theorem coordinateDerivation_algebraMap
    (coordinate series : PS) :
    coordinateDerivation coordinate (algebraMap PS LS series) =
      (algebraMap PS LS (PowerSeries.derivative ℂ coordinate))⁻¹ *
        algebraMap PS LS (PowerSeries.derivative ℂ series) := by
  change
    (algebraMap PS LS (PowerSeries.derivative ℂ coordinate))⁻¹ *
        FormalLocalizationDerivationExtension.laurentSeriesDerivation ℂ
          (algebraMap PS LS series) = _
  rw [FormalLocalizationDerivationExtension.laurentSeriesDerivation_algebraMap]

@[simp]
theorem coordinateDerivation_coordinate
    (coordinate : PS) [Invertible (coordinate.coeff 1)] :
    coordinateDerivation coordinate (algebraMap PS LS coordinate) = 1 := by
  rw [coordinateDerivation_algebraMap]
  exact inv_mul_cancel₀ (coordinateDerivative_ne_zero coordinate)

@[simp]
theorem coordinateDerivation_real_constant
    (coordinate : PS) (constant : ℝ) :
    coordinateDerivation coordinate
        (algebraMap PS LS (PowerSeries.C (constant : ℂ))) = 0 := by
  rw [coordinateDerivation_algebraMap]
  simp

/-- Polynomial evaluation intertwines ordinary polynomial differentiation
with differentiation in the tangent coordinate. -/
theorem coordinateDerivation_realPolynomialToLaurent
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] (polynomial : ℝ[X]) :
    coordinateDerivation coordinate
        (realPolynomialToLaurent coordinate polynomial) =
      realPolynomialToLaurent coordinate polynomial.derivative := by
  rw [realPolynomialToLaurent_apply,
    realPolynomialToLaurent_apply,
    coordinateDerivation_algebraMap]
  have hchain :=
    (PowerSeries.derivative ℂ).comp_aeval_eq
      (a := coordinate) (polynomial.map (algebraMap ℝ ℂ))
  simp only [smul_eq_mul] at hchain
  rw [hchain, map_mul]
  rw [show Polynomial.derivative
      (polynomial.map (algebraMap ℝ ℂ)) =
        polynomial.derivative.map (algebraMap ℝ ℂ) by
      exact Polynomial.derivative_map polynomial (algebraMap ℝ ℂ)]
  have hderivative := coordinateDerivative_ne_zero coordinate
  field_simp

/-- Quotient rule for any derivation on a field. -/
theorem derivation_div
    {K : Type*} [Field K] (d : Derivation ℤ K K)
    (numerator denominator : K) (hdenominator : denominator ≠ 0) :
    d (numerator / denominator) =
      (d numerator * denominator - numerator * d denominator) /
        denominator ^ 2 := by
  rw [div_eq_mul_inv, d.leibniz]
  simp only [smul_eq_mul]
  have hinverse :
      d denominator⁻¹ = -denominator⁻¹ ^ 2 * d denominator :=
    d.leibniz_of_mul_eq_one (inv_mul_cancel₀ hdenominator)
  rw [hinverse]
  field_simp
  ring

/-- The field embedding intertwines the ordinary rational derivative with
the normalized Laurent derivation for every rational function. -/
theorem ratFuncToLaurent_derivative
    (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
    [Invertible (coordinate.coeff 1)] (value : RF) :
    ratFuncToLaurent coordinate hconstant
        (FormalRationalFunctionDerivationLocalOrder.rationalDerivative value) =
      coordinateDerivation coordinate
        (ratFuncToLaurent coordinate hconstant value) := by
  induction value using RatFunc.induction_on with
  | f numerator denominator hdenominator =>
      have hmappedDenominator :
          realPolynomialToLaurent coordinate denominator ≠ 0 :=
        by
          simpa only [map_zero] using
            (realPolynomialToLaurent_injective coordinate hconstant).ne
              hdenominator
      rw [FormalRationalFunctionDerivationLocalOrder.rationalDerivative_div]
      rw [FormalRationalFunctionDerivationLocalOrder.quotientDerivative]
      simp only [map_div₀, map_sub, map_mul, map_pow,
        ratFuncToLaurent_algebraMap]
      rw [derivation_div _ _ _ hmappedDenominator]
      rw [coordinateDerivation_realPolynomialToLaurent
          coordinate hconstant numerator,
        coordinateDerivation_realPolynomialToLaurent
          coordinate hconstant denominator]

/-- Aggregated coordinate-covariant rational Laurent carrier. -/
theorem ratfunc_laurent_tangent_carrier_terminal_certificate :
    ∀ (coordinate : PS) (hconstant : coordinate.constantCoeff = 0)
      [Invertible (coordinate.coeff 1)],
      Function.Injective (ratFuncToLaurent coordinate hconstant) ∧
      ratFuncToLaurent coordinate hconstant RatFunc.X =
        algebraMap PS LS coordinate ∧
      (∀ value : RF,
        ratFuncToLaurent coordinate hconstant
            (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
              value) =
          coordinateDerivation coordinate
            (ratFuncToLaurent coordinate hconstant value)) := by
  intro coordinate hconstant _
  exact ⟨ratFuncToLaurent_injective coordinate hconstant,
    ratFuncToLaurent_X coordinate hconstant,
    ratFuncToLaurent_derivative coordinate hconstant⟩

end

end FormalRatFuncLaurentTangentCarrier
