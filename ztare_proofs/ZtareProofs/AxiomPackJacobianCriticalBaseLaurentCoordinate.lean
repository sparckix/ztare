import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxUniformization
import ZtareProofs.FormalAffineRatFuncLaurentTangentCarrier
import ZtareProofs.FormalCriticalConnectionRationalization
import ZtareProofs.FormalPowerSeriesLinearODE

/-!
# The critical differential field at the normalization point

The critical rational parameter has value `s = 1` at the original source
normalization.  In the local coordinate `z = q - 1`, its exact tangent germ
is `-2z/(2+z)`.  This file installs the corresponding affine Laurent field,
constructs the source and normalized visible power series, and proves the
singular rational connection equation after Laurent localization.
-/

namespace AxiomPackJacobianCriticalBaseLaurentCoordinate

open Polynomial PowerSeries
open scoped LaurentSeries

open AxiomPackJacobianCriticalPuiseuxUniformization
open FormalCriticalConnectionRationalization
open FormalAffineRatFuncLaurentTangentCarrier
open FormalPowerSeriesLinearODE
open FormalRatFuncLaurentTangentCarrier

noncomputable section

abbrev RF := RatFunc ℝ
abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

/-- Tangent part of `s=(3-q)/(q+1)` after `q=1+z`. -/
def baseTangentCoordinate : PS :=
  -(PowerSeries.C 2) * PowerSeries.X *
    (PowerSeries.C 2 + PowerSeries.X)⁻¹

@[simp]
theorem baseTangentCoordinate_constantCoeff :
    baseTangentCoordinate.constantCoeff = 0 := by
  simp [baseTangentCoordinate]

theorem baseTangentCoordinate_coeff_one :
    baseTangentCoordinate.coeff 1 = -1 := by
  norm_num [baseTangentCoordinate, PowerSeries.coeff_mul,
    Finset.antidiagonal, PowerSeries.constantCoeff_inv]

theorem baseTangentCoordinate_coeff_one_ne :
    baseTangentCoordinate.coeff 1 ≠ 0 := by
  rw [baseTangentCoordinate_coeff_one]
  norm_num

noncomputable instance baseTangentLinearInvertible :
    Invertible (baseTangentCoordinate.coeff 1) :=
  invertibleOfNonzero baseTangentCoordinate_coeff_one_ne

/-- Full critical parameter germ at the normalization point. -/
def baseSCoordinate : PS :=
  affineCoordinate 1 baseTangentCoordinate

@[simp]
theorem baseSCoordinate_constantCoeff :
    baseSCoordinate.constantCoeff = 1 := by
  simp [baseSCoordinate, affineCoordinate]

theorem baseSCoordinate_coeff_one : baseSCoordinate.coeff 1 = -1 := by
  simp [baseSCoordinate, affineCoordinate,
    baseTangentCoordinate_coeff_one]

/-- Uniformizing `q` germ in the centered coordinate. -/
def baseQCoordinate : PS := PowerSeries.C 1 + PowerSeries.X

/-- Exact source germ `x(s)` at `s=1`. -/
def baseSource : PS :=
  PowerSeries.C 6 * (baseSCoordinate ^ 2 - 1) *
    (baseSCoordinate ^ 2 + 3)⁻¹

@[simp]
theorem baseSource_constantCoeff : baseSource.constantCoeff = 0 := by
  simp [baseSource, baseSCoordinate_constantCoeff,
    PowerSeries.constantCoeff_inv]

theorem baseSource_coeff_one : baseSource.coeff 1 = -3 := by
  norm_num [baseSource, PowerSeries.coeff_mul, Finset.antidiagonal,
    PowerSeries.constantCoeff_inv, pow_two, map_ofNat,
    baseSCoordinate_constantCoeff, baseSCoordinate_coeff_one]

theorem baseSource_coeff_one_ne : baseSource.coeff 1 ≠ 0 := by
  rw [baseSource_coeff_one]
  norm_num

noncomputable instance baseSourceLinearInvertible :
    Invertible (baseSource.coeff 1) :=
  invertibleOfNonzero baseSource_coeff_one_ne

/-- Polynomial numerator of the regularized `q`-connection. -/
def baseRegularizedNumeratorPolynomial : ℂ[X] :=
  -39 * Polynomial.X ^ 6 + 234 * Polynomial.X ^ 5 -
    2233 * Polynomial.X ^ 4 + 11916 * Polynomial.X ^ 3 +
    1047 * Polynomial.X ^ 2 + 1386 * Polynomial.X + 2025

/-- Polynomial denominator of the regularized `q`-connection. -/
def baseFlowDenominatorPolynomial : ℂ[X] :=
  39 * Polynomial.X ^ 7 - 273 * Polynomial.X ^ 6 +
    1571 * Polynomial.X ^ 5 - 6981 * Polynomial.X ^ 4 +
    5493 * Polynomial.X ^ 3 - 21843 * Polynomial.X ^ 2 -
    8703 * Polynomial.X + 2025

def baseRegularizedNumeratorSeries : PS :=
  -(PowerSeries.C 39) * baseQCoordinate ^ 6 +
    PowerSeries.C 234 * baseQCoordinate ^ 5 -
    PowerSeries.C 2233 * baseQCoordinate ^ 4 +
    PowerSeries.C 11916 * baseQCoordinate ^ 3 +
    PowerSeries.C 1047 * baseQCoordinate ^ 2 +
    PowerSeries.C 1386 * baseQCoordinate + PowerSeries.C 2025

def baseFlowDenominatorSeries : PS :=
  PowerSeries.C 39 * baseQCoordinate ^ 7 -
    PowerSeries.C 273 * baseQCoordinate ^ 6 +
    PowerSeries.C 1571 * baseQCoordinate ^ 5 -
    PowerSeries.C 6981 * baseQCoordinate ^ 4 +
    PowerSeries.C 5493 * baseQCoordinate ^ 3 -
    PowerSeries.C 21843 * baseQCoordinate ^ 2 -
    PowerSeries.C 8703 * baseQCoordinate + PowerSeries.C 2025

def basePoleSeries : PS :=
  PowerSeries.C 199 * baseSCoordinate ^ 7 -
    PowerSeries.C 1393 * baseSCoordinate ^ 6 +
    PowerSeries.C 67 * baseSCoordinate ^ 5 +
    PowerSeries.C 219 * baseSCoordinate ^ 4 +
    PowerSeries.C 5973 * baseSCoordinate ^ 3 +
    PowerSeries.C 10125 * baseSCoordinate ^ 2 +
    PowerSeries.C 10593 * baseSCoordinate + PowerSeries.C 2889

/-- Regularized logarithmic coefficient at `q=1`. -/
def baseRegularizedCoefficient : PS :=
  baseRegularizedNumeratorSeries * baseFlowDenominatorSeries⁻¹

/-- Regularized endpoint, normalized by the exact source slope `-3`. -/
def baseRegularizedEndpoint : PS :=
  PowerSeries.C (-3) * normalizedEndpoint baseRegularizedCoefficient

/-- Exact critical visible germ at the original normalization point. -/
def baseVisible : PS :=
  PowerSeries.X * baseRegularizedEndpoint

@[reducible]
def criticalBaseLaurentAlgebra : Algebra RF LS :=
  affineRatFuncLaurentAlgebra 1 baseTangentCoordinate
    baseTangentCoordinate_constantCoeff

noncomputable local instance criticalBaseLaurentAlgebraInstance :
    Algebra RF LS := criticalBaseLaurentAlgebra

@[simp]
theorem algebraMap_powerSeries_C (constant : ℂ) :
    algebraMap PS LS (PowerSeries.C constant) =
      algebraMap ℂ LS constant := by
  change ((PowerSeries.C constant : PS) : LS) = _
  rw [PowerSeries.coe_C, HahnSeries.algebraMap_apply',
    PowerSeries.algebraMap_apply, HahnSeries.ofPowerSeries_C]
  simp

@[simp]
theorem algebraMap_complex_nat (number : ℕ) :
    algebraMap ℂ LS (number : ℂ) = (number : LS) := by
  exact map_natCast (algebraMap ℂ LS) number

@[simp]
theorem algebraMap_complex_ofNat (number : ℕ) [number.AtLeastTwo] :
    algebraMap ℂ LS (OfNat.ofNat number : ℂ) =
      (OfNat.ofNat number : LS) := by
  exact map_ofNat (algebraMap ℂ LS) number

theorem laurent_ofNat_ne_zero (number : ℕ) [number.AtLeastTwo] :
    (OfNat.ofNat number : LS) ≠ 0 := by
  intro hzero
  have hcoeff := congrArg (fun series : LS => series.coeff 0) hzero
  apply (OfNat.ofNat_ne_zero number : (OfNat.ofNat number : ℂ) ≠ 0)
  simpa only [← HahnSeries.single_zero_ofNat number,
    HahnSeries.coeff_single_same, HahnSeries.coeff_zero] using hcoeff

theorem laurent_mul_896_div_four (value : LS) :
    896 * value / 4 = value * 224 := by
  apply (div_eq_iff (laurent_ofNat_ne_zero 4)).2
  ring

theorem laurent_mul_57344_div_256 (value : LS) :
    value * 57344 / 256 = value * 224 := by
  apply (div_eq_iff (laurent_ofNat_ne_zero 256)).2
  ring

theorem constantCoeff_aeval (series : PS) (polynomial : ℂ[X]) :
    (Polynomial.aeval series polynomial).constantCoeff =
      polynomial.eval series.constantCoeff := by
  have hmap := Polynomial.map_aeval_eq_aeval_map
    (R := ℂ) (S := PS) (T := ℂ) (U := ℂ)
    (φ := RingHom.id ℂ) (ψ := PowerSeries.constantCoeff)
    (by ext constant; simp) polynomial series
  simpa only [Polynomial.map_id, Polynomial.aeval_def,
    Polynomial.eval₂_at_apply, RingHom.id_apply] using hmap

/-- The power-series inverse and the field inverse agree after Laurent
localization whenever the series has invertible constant term. -/
theorem algebraMap_powerSeries_inv
    (series : PS) (hconstant : series.constantCoeff ≠ 0) :
    algebraMap PS LS series⁻¹ = (algebraMap PS LS series)⁻¹ := by
  have hseries : series ≠ 0 := by
    intro hzero
    apply hconstant
    rw [hzero]
    simp
  apply eq_inv_of_mul_eq_one_right
  rw [← map_mul, PowerSeries.mul_inv_cancel series hconstant, map_one]

theorem base_parameter_binding :
    algebraMap RF LS parameter = algebraMap PS LS baseSCoordinate := by
  change affineRatFuncToLaurent 1 baseTangentCoordinate
      baseTangentCoordinate_constantCoeff parameter = _
  exact affineRatFuncToLaurent_X 1 baseTangentCoordinate
    baseTangentCoordinate_constantCoeff

theorem base_X_binding :
    algebraMap RF LS RatFunc.X = algebraMap PS LS baseSCoordinate := by
  simpa only [parameter] using base_parameter_binding

theorem base_real_constant_binding (constant : ℝ) :
    algebraMap RF LS (RatFunc.C constant) =
      algebraMap ℂ LS (constant : ℂ) := by
  change affineRatFuncToLaurent 1 baseTangentCoordinate
      baseTangentCoordinate_constantCoeff (RatFunc.C constant) = _
  rw [← RatFunc.algebraMap_C, affineRatFuncToLaurent_algebraMap]
  rw [affineRealPolynomialToLaurent_apply,
    Polynomial.map_C, Polynomial.aeval_C]
  exact algebraMap_powerSeries_C (constant : ℂ)

theorem base_source_binding :
    algebraMap RF LS xOfParameter = algebraMap PS LS baseSource := by
  have hdenominator : (baseSCoordinate ^ 2 + 3).constantCoeff ≠ 0 := by
    rw [map_add, map_pow, baseSCoordinate_constantCoeff, map_ofNat]
    norm_num
  unfold xOfParameter baseSource
  rw [map_div₀]
  simp only [map_mul, map_sub, map_pow, map_add, map_one, map_ofNat]
  rw [base_parameter_binding]
  simp [base_real_constant_binding, algebraMap_complex_nat]
  rw [div_eq_mul_inv]
  congr 1
  have hinverse := algebraMap_powerSeries_inv _ hdenominator
  simp only [map_add, map_pow, map_ofNat] at hinverse
  exact hinverse.symm

theorem base_coefficient_derivative_binding (coefficient : RF) :
    algebraMap RF LS
        (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
          coefficient) =
      coordinateDerivation baseTangentCoordinate
        (algebraMap RF LS coefficient) := by
  change affineRatFuncToLaurent 1 baseTangentCoordinate
      baseTangentCoordinate_constantCoeff
        (FormalRationalFunctionDerivationLocalOrder.rationalDerivative
          coefficient) = _
  exact affineRatFuncToLaurent_derivative 1 baseTangentCoordinate
    baseTangentCoordinate_constantCoeff coefficient

theorem rationalDerivative_xOfParameter :
    FormalRationalFunctionDerivationLocalOrder.rationalDerivative
        xOfParameter =
      xDerivativeOfParameter := by
  let numerator : ℝ[X] := 6 * (Polynomial.X ^ 2 - 1)
  let denominator : ℝ[X] := Polynomial.X ^ 2 + 3
  have hrepresentation :
      xOfParameter =
        algebraMap ℝ[X] RF numerator /
          algebraMap ℝ[X] RF denominator := by
    simp [xOfParameter, parameter, numerator, denominator]
    rw [map_ofNat (algebraMap ℝ[X] RF) 6,
      map_ofNat (algebraMap ℝ[X] RF) 3]
  rw [hrepresentation,
    FormalRationalFunctionDerivationLocalOrder.rationalDerivative_div]
  unfold FormalRationalFunctionDerivationLocalOrder.quotientDerivative
    numerator denominator xDerivativeOfParameter parameter
  simp only [map_sub, map_mul, map_pow, map_add, map_one, map_ofNat,
    RatFunc.algebraMap_X, Polynomial.derivative_sub,
    Polynomial.derivative_mul, Polynomial.derivative_pow,
    Polynomial.derivative_X, Polynomial.derivative_one,
    Polynomial.derivative_ofNat, zero_mul, add_zero, sub_zero]
  simp only [map_zero, RatFunc.algebraMap_C,
    FormalCriticalConnectionRationalization.ratFunc_C_natCast]
  field_simp [parameter_sq_add_three_ne_zero]
  ring

theorem base_source_derivative_binding :
    algebraMap RF LS xDerivativeOfParameter =
      coordinateDerivation baseTangentCoordinate
        (algebraMap RF LS xOfParameter) := by
  rw [← rationalDerivative_xOfParameter]
  exact base_coefficient_derivative_binding xOfParameter

@[simp]
theorem baseRegularizedEndpoint_constantCoeff :
    baseRegularizedEndpoint.constantCoeff = -3 := by
  simp [baseRegularizedEndpoint]

theorem baseRegularizedEndpoint_derivative :
    d⁄dX ℂ baseRegularizedEndpoint =
      baseRegularizedCoefficient * baseRegularizedEndpoint := by
  unfold baseRegularizedEndpoint
  rw [(PowerSeries.derivative ℂ).leibniz,
    normalizedEndpoint_derivative]
  simp
  ring

theorem baseTangentCoordinate_derivative :
    d⁄dX ℂ baseTangentCoordinate =
      -(PowerSeries.C 4) * (PowerSeries.C 2 + PowerSeries.X)⁻¹ ^ 2 := by
  simp [baseTangentCoordinate, PowerSeries.derivative_inv']
  have hcancel := PowerSeries.mul_inv_cancel
    (PowerSeries.C (2 : ℂ) + PowerSeries.X) (by norm_num)
  rw [show PowerSeries.C (4 : ℂ) = PowerSeries.C (2 : ℂ) ^ 2 by
    simpa only [map_pow] using congrArg PowerSeries.C
      (show (4 : ℂ) = 2 ^ 2 by norm_num)]
  linear_combination
    (PowerSeries.C (2 : ℂ) *
      (PowerSeries.C (2 : ℂ) + PowerSeries.X)⁻¹) * hcancel

theorem baseRegularizedCoefficient_binding :
    algebraMap PS LS baseRegularizedCoefficient =
      (-39 * algebraMap PS LS baseQCoordinate ^ 6 +
          234 * algebraMap PS LS baseQCoordinate ^ 5 -
          2233 * algebraMap PS LS baseQCoordinate ^ 4 +
          11916 * algebraMap PS LS baseQCoordinate ^ 3 +
          1047 * algebraMap PS LS baseQCoordinate ^ 2 +
          1386 * algebraMap PS LS baseQCoordinate + 2025) /
        (39 * algebraMap PS LS baseQCoordinate ^ 7 -
          273 * algebraMap PS LS baseQCoordinate ^ 6 +
          1571 * algebraMap PS LS baseQCoordinate ^ 5 -
          6981 * algebraMap PS LS baseQCoordinate ^ 4 +
          5493 * algebraMap PS LS baseQCoordinate ^ 3 -
          21843 * algebraMap PS LS baseQCoordinate ^ 2 -
          8703 * algebraMap PS LS baseQCoordinate + 2025) := by
  have hdenominator :
      baseFlowDenominatorSeries.constantCoeff ≠ 0 := by
    norm_num [baseFlowDenominatorSeries, baseQCoordinate]
  unfold baseRegularizedCoefficient
  rw [map_mul,
    algebraMap_powerSeries_inv _ hdenominator]
  simp only [baseRegularizedNumeratorSeries, baseFlowDenominatorSeries,
    map_neg, map_add, map_sub, map_mul, map_pow,
    algebraMap_powerSeries_C]
  rw [algebraMap_complex_ofNat 39,
    algebraMap_complex_ofNat 234,
    algebraMap_complex_ofNat 2233,
    algebraMap_complex_ofNat 11916,
    algebraMap_complex_ofNat 1047,
    algebraMap_complex_ofNat 1386,
    algebraMap_complex_ofNat 2025,
    algebraMap_complex_ofNat 273,
    algebraMap_complex_ofNat 1571,
    algebraMap_complex_ofNat 6981,
    algebraMap_complex_ofNat 5493,
    algebraMap_complex_ofNat 21843,
    algebraMap_complex_ofNat 8703]
  rw [div_eq_mul_inv]

theorem base_connection_formula :
    algebraMap RF LS explicitRationalDifferential =
      896 * algebraMap PS LS baseSCoordinate *
          (algebraMap PS LS baseSCoordinate - 3) *
          (algebraMap PS LS baseSCoordinate + 1) *
          (algebraMap PS LS baseSCoordinate ^ 2 -
            6 * algebraMap PS LS baseSCoordinate - 3) /
        ((algebraMap PS LS baseSCoordinate - 1) *
          (199 * algebraMap PS LS baseSCoordinate ^ 7 -
            1393 * algebraMap PS LS baseSCoordinate ^ 6 +
            67 * algebraMap PS LS baseSCoordinate ^ 5 +
            219 * algebraMap PS LS baseSCoordinate ^ 4 +
            5973 * algebraMap PS LS baseSCoordinate ^ 3 +
            10125 * algebraMap PS LS baseSCoordinate ^ 2 +
            10593 * algebraMap PS LS baseSCoordinate + 2889)) := by
  change affineRatFuncToLaurent 1 baseTangentCoordinate
      baseTangentCoordinate_constantCoeff explicitRationalDifferential = _
  unfold explicitRationalDifferential numeratorRationalFunction
    poleRationalFunction parameter
  rw [map_div₀, map_mul, map_sub, map_one,
    affineRatFuncToLaurent_algebraMap,
    affineRatFuncToLaurent_algebraMap,
    affineRatFuncToLaurent_X,
    affineRealPolynomialToLaurent_apply,
    affineRealPolynomialToLaurent_apply]
  simp [FormalCriticalMonodromyResidueBinding.numeratorPolynomial,
    FormalCriticalMonodromyResidueBinding.polePolynomial,
    baseSCoordinate, div_eq_mul_inv, nsmul_eq_mul,
    HahnSeries.single_zero_ofNat]
  left
  left
  ring

def baseLocalQ (z : LS) : LS := 1 + z

def baseLocalS (z : LS) : LS := 1 - 2 * z * (2 + z)⁻¹

def baseLocalNumerator (z : LS) : LS :=
  -39 * baseLocalQ z ^ 6 + 234 * baseLocalQ z ^ 5 -
    2233 * baseLocalQ z ^ 4 + 11916 * baseLocalQ z ^ 3 +
    1047 * baseLocalQ z ^ 2 + 1386 * baseLocalQ z + 2025

def baseLocalDenominator (z : LS) : LS :=
  39 * baseLocalQ z ^ 7 - 273 * baseLocalQ z ^ 6 +
    1571 * baseLocalQ z ^ 5 - 6981 * baseLocalQ z ^ 4 +
    5493 * baseLocalQ z ^ 3 - 21843 * baseLocalQ z ^ 2 -
    8703 * baseLocalQ z + 2025

def baseLocalPole (z : LS) : LS :=
  199 * baseLocalS z ^ 7 - 1393 * baseLocalS z ^ 6 +
    67 * baseLocalS z ^ 5 + 219 * baseLocalS z ^ 4 +
    5973 * baseLocalS z ^ 3 + 10125 * baseLocalS z ^ 2 +
    10593 * baseLocalS z + 2889

def baseLocalConnectionNumerator (z : LS) : LS :=
  896 * baseLocalS z * (baseLocalS z - 3) * (baseLocalS z + 1) *
    (baseLocalS z ^ 2 - 6 * baseLocalS z - 3)

def baseLocalFactor (z : LS) : LS :=
  (z - 2) * (z + 1) * (z ^ 2 - 4 * z - 8)

set_option maxHeartbeats 1000000 in
theorem base_local_rational_identity
    (z : LS)
    (hz : z ≠ 0)
    (htwo : 2 + z ≠ 0)
    (hdenominator : baseLocalDenominator z ≠ 0)
    (hpole : baseLocalPole z ≠ 0)
    (hsMinus : baseLocalS z - 1 ≠ 0) :
    (-4 * (2 + z)⁻¹ ^ 2)⁻¹ *
        (1 + z * (baseLocalNumerator z / baseLocalDenominator z)) =
      (baseLocalConnectionNumerator z /
          ((baseLocalS z - 1) * baseLocalPole z)) * z := by
  have hsum :
      baseLocalDenominator z + z * baseLocalNumerator z =
        -896 * baseLocalFactor z * (2 + z) := by
    simp only [baseLocalDenominator, baseLocalNumerator,
      baseLocalQ, baseLocalFactor]
    ring
  have hpoleTransform :
      (2 + z) ^ 7 * baseLocalPole z =
        -128 * baseLocalDenominator z := by
    simp only [baseLocalPole, baseLocalS,
      baseLocalDenominator, baseLocalQ]
    field_simp [htwo]
    ring
  have hconnectionTransform :
      (2 + z) ^ 5 * baseLocalConnectionNumerator z =
        57344 * baseLocalFactor z := by
    simp only [baseLocalConnectionNumerator, baseLocalS,
      baseLocalFactor]
    field_simp [htwo]
    ring
  have hpoleFormula :
      baseLocalPole z =
        (-128 * baseLocalDenominator z) / (2 + z) ^ 7 := by
    apply (eq_div_iff (pow_ne_zero 7 htwo)).2
    simpa only [mul_comm] using hpoleTransform
  have hconnectionFormula :
      baseLocalConnectionNumerator z =
        57344 * baseLocalFactor z / (2 + z) ^ 5 := by
    apply (eq_div_iff (pow_ne_zero 5 htwo)).2
    simpa only [mul_comm] using hconnectionTransform
  have hsFormula :
      baseLocalS z - 1 = (-2 * z) / (2 + z) := by
    simp only [baseLocalS]
    field_simp [htwo]
    ring
  calc
    (-4 * (2 + z)⁻¹ ^ 2)⁻¹ *
          (1 + z * (baseLocalNumerator z / baseLocalDenominator z)) =
        224 * baseLocalFactor z * (2 + z) ^ 3 /
          baseLocalDenominator z := by
            rw [show 1 + z *
                  (baseLocalNumerator z / baseLocalDenominator z) =
                (baseLocalDenominator z + z * baseLocalNumerator z) /
                  baseLocalDenominator z by
              field_simp [hdenominator]]
            rw [hsum]
            field_simp [htwo, hdenominator]
            exact laurent_mul_896_div_four (baseLocalFactor z)
    _ = (baseLocalConnectionNumerator z /
          ((baseLocalS z - 1) * baseLocalPole z)) * z := by
            rw [hconnectionFormula, hpoleFormula, hsFormula]
            field_simp [hz, htwo, hdenominator, hpole, hsMinus]
            rw [show (2 : LS) * 128 = 256 by ring]
            calc
              224 * baseLocalFactor z =
                  baseLocalFactor z * 224 := mul_comm _ _
              _ = baseLocalFactor z * 57344 / 256 :=
                (laurent_mul_57344_div_256 (baseLocalFactor z)).symm

def baseZ : LS := algebraMap PS LS PowerSeries.X

theorem baseQCoordinate_binding :
    algebraMap PS LS baseQCoordinate = baseLocalQ baseZ := by
  simp only [baseQCoordinate, baseLocalQ, baseZ, map_add,
    algebraMap_powerSeries_C]
  rw [show algebraMap ℂ LS (1 : ℂ) = (1 : LS) by exact map_one _]

theorem baseTwoPowerSeries_binding :
    algebraMap PS LS (PowerSeries.C (2 : ℂ) + PowerSeries.X) =
      2 + baseZ := by
  simp only [baseZ, map_add, algebraMap_powerSeries_C]
  rw [algebraMap_complex_ofNat 2]

theorem baseSCoordinate_binding :
    algebraMap PS LS baseSCoordinate = baseLocalS baseZ := by
  have hinverse := algebraMap_powerSeries_inv
    (PowerSeries.C (2 : ℂ) + PowerSeries.X)
    (by norm_num :
      (PowerSeries.C (2 : ℂ) + PowerSeries.X).constantCoeff ≠ (0 : ℂ))
  unfold baseSCoordinate affineCoordinate baseTangentCoordinate
    baseLocalS baseZ
  simp only [map_add, map_neg, map_mul, algebraMap_powerSeries_C]
  rw [hinverse, baseTwoPowerSeries_binding]
  norm_num only [Complex.ofReal_one, map_ofNat, map_one]
  simp only [baseZ]
  ring

theorem baseFlowDenominator_binding :
    algebraMap PS LS baseFlowDenominatorSeries =
      baseLocalDenominator baseZ := by
  simp only [baseFlowDenominatorSeries, baseLocalDenominator,
    map_sub, map_add, map_mul, map_pow, algebraMap_powerSeries_C,
    baseQCoordinate_binding]
  rw [algebraMap_complex_ofNat 39,
    algebraMap_complex_ofNat 273,
    algebraMap_complex_ofNat 1571,
    algebraMap_complex_ofNat 6981,
    algebraMap_complex_ofNat 5493,
    algebraMap_complex_ofNat 21843,
    algebraMap_complex_ofNat 8703,
    algebraMap_complex_ofNat 2025]

theorem basePoleSeries_binding :
    algebraMap PS LS basePoleSeries = baseLocalPole baseZ := by
  simp only [basePoleSeries, baseLocalPole, map_sub, map_add,
    map_mul, map_pow, algebraMap_powerSeries_C,
    baseSCoordinate_binding]
  rw [algebraMap_complex_ofNat 199,
    algebraMap_complex_ofNat 1393,
    algebraMap_complex_ofNat 67,
    algebraMap_complex_ofNat 219,
    algebraMap_complex_ofNat 5973,
    algebraMap_complex_ofNat 10125,
    algebraMap_complex_ofNat 10593,
    algebraMap_complex_ofNat 2889]

theorem baseZ_ne_zero : baseZ ≠ 0 := by
  simpa only [baseZ, map_zero] using
    (FaithfulSMul.algebraMap_injective PS LS).ne PowerSeries.X_ne_zero

theorem baseTwoPlusZ_ne_zero : 2 + baseZ ≠ 0 := by
  have hpower : PowerSeries.C (2 : ℂ) + PowerSeries.X ≠ 0 := by
    intro hzero
    have hconstant := congrArg PowerSeries.constantCoeff hzero
    norm_num at hconstant
  have hmapped := (FaithfulSMul.algebraMap_injective PS LS).ne hpower
  simp only [map_zero, map_add, algebraMap_powerSeries_C] at hmapped
  rw [algebraMap_complex_ofNat 2] at hmapped
  exact hmapped

theorem baseFlowDenominatorSeries_ne_zero :
    baseFlowDenominatorSeries ≠ 0 := by
  intro hzero
  have hconstant := congrArg PowerSeries.constantCoeff hzero
  norm_num [baseFlowDenominatorSeries, baseQCoordinate] at hconstant

theorem baseLocalDenominator_baseZ_ne_zero :
    baseLocalDenominator baseZ ≠ 0 := by
  have hmapped := (FaithfulSMul.algebraMap_injective PS LS).ne
    baseFlowDenominatorSeries_ne_zero
  simpa only [map_zero, baseFlowDenominator_binding] using hmapped

theorem baseSCoordinate_sub_one_ne_zero : baseSCoordinate - 1 ≠ 0 := by
  intro hzero
  have hcoefficient := congrArg (PowerSeries.coeff 1) hzero
  norm_num [baseSCoordinate, affineCoordinate,
    baseTangentCoordinate_coeff_one] at hcoefficient

theorem baseLocalS_baseZ_sub_one_ne_zero :
    baseLocalS baseZ - 1 ≠ 0 := by
  have hmapped := (FaithfulSMul.algebraMap_injective PS LS).ne
    baseSCoordinate_sub_one_ne_zero
  have hsub : algebraMap PS LS baseSCoordinate - 1 ≠ 0 := by
    simpa only [map_sub, map_one, map_zero] using hmapped
  simpa only [baseSCoordinate_binding] using hsub

theorem basePoleSeries_ne_zero : basePoleSeries ≠ 0 := by
  intro hzero
  have hconstant := congrArg PowerSeries.constantCoeff hzero
  norm_num [basePoleSeries, baseSCoordinate_constantCoeff] at hconstant

theorem baseLocalPole_baseZ_ne_zero : baseLocalPole baseZ ≠ 0 := by
  have hmapped := (FaithfulSMul.algebraMap_injective PS LS).ne
    basePoleSeries_ne_zero
  simpa only [map_zero, basePoleSeries_binding] using hmapped

theorem baseRegularizedEndpoint_mapped_ne_zero :
    algebraMap PS LS baseRegularizedEndpoint ≠ 0 := by
  have hpower : baseRegularizedEndpoint ≠ 0 := by
    intro hzero
    have hconstant := congrArg PowerSeries.constantCoeff hzero
    rw [baseRegularizedEndpoint_constantCoeff] at hconstant
    norm_num at hconstant
  simpa only [map_zero] using
    (FaithfulSMul.algebraMap_injective PS LS).ne hpower

theorem baseTangentCoordinate_derivative_binding :
    algebraMap PS LS (d⁄dX ℂ baseTangentCoordinate) =
      -4 * (2 + baseZ)⁻¹ ^ 2 := by
  rw [baseTangentCoordinate_derivative, map_mul, map_neg, map_pow,
    algebraMap_powerSeries_C]
  rw [algebraMap_complex_ofNat 4]
  have hinverse := algebraMap_powerSeries_inv
    (PowerSeries.C (2 : ℂ) + PowerSeries.X)
    (by norm_num :
      (PowerSeries.C (2 : ℂ) + PowerSeries.X).constantCoeff ≠ (0 : ℂ))
  rw [hinverse, baseTwoPowerSeries_binding]

theorem baseVisible_derivative :
    d⁄dX ℂ baseVisible =
      (1 + PowerSeries.X * baseRegularizedCoefficient) *
        baseRegularizedEndpoint := by
  unfold baseVisible
  rw [(PowerSeries.derivative ℂ).leibniz,
    PowerSeries.derivative_X, baseRegularizedEndpoint_derivative]
  ring

theorem baseRegularizedCoefficient_local_binding :
    algebraMap PS LS baseRegularizedCoefficient =
      baseLocalNumerator baseZ / baseLocalDenominator baseZ := by
  rw [baseRegularizedCoefficient_binding, baseQCoordinate_binding]
  rfl

theorem baseConnection_local_binding :
    algebraMap RF LS explicitRationalDifferential =
      baseLocalConnectionNumerator baseZ /
        ((baseLocalS baseZ - 1) * baseLocalPole baseZ) := by
  rw [base_connection_formula, baseSCoordinate_binding]
  rfl

theorem baseVisible_binding :
    algebraMap PS LS baseVisible =
      baseZ * algebraMap PS LS baseRegularizedEndpoint := by
  simp only [baseVisible, baseZ, map_mul]

theorem baseVisible_derivative_binding :
    algebraMap PS LS (d⁄dX ℂ baseVisible) =
      (1 + baseZ *
        (baseLocalNumerator baseZ / baseLocalDenominator baseZ)) *
          algebraMap PS LS baseRegularizedEndpoint := by
  rw [baseVisible_derivative, map_mul, map_add, map_one, map_mul,
    baseRegularizedCoefficient_local_binding]
  rfl

/- The regular base germ satisfies the exact singular critical connection
after localizing the centered coordinate. -/
theorem baseVisible_critical_ode :
    coordinateDerivation baseTangentCoordinate
        (algebraMap PS LS baseVisible) =
      algebraMap RF LS explicitRationalDifferential *
        algebraMap PS LS baseVisible := by
  rw [coordinateDerivation_algebraMap,
    baseVisible_derivative_binding,
    baseConnection_local_binding, baseVisible_binding,
    baseTangentCoordinate_derivative_binding]
  have hscalar :
      (-4 * (2 + baseZ)⁻¹ ^ 2)⁻¹ *
          (1 + baseZ *
            (baseLocalNumerator baseZ / baseLocalDenominator baseZ)) =
        (baseLocalConnectionNumerator baseZ /
          ((baseLocalS baseZ - 1) * baseLocalPole baseZ)) * baseZ :=
    base_local_rational_identity baseZ baseZ_ne_zero
      baseTwoPlusZ_ne_zero baseLocalDenominator_baseZ_ne_zero
      baseLocalPole_baseZ_ne_zero baseLocalS_baseZ_sub_one_ne_zero
  calc
    (-4 * (2 + baseZ)⁻¹ ^ 2)⁻¹ *
          ((1 + baseZ *
            (baseLocalNumerator baseZ / baseLocalDenominator baseZ)) *
            algebraMap PS LS baseRegularizedEndpoint) =
        ((-4 * (2 + baseZ)⁻¹ ^ 2)⁻¹ *
          (1 + baseZ *
            (baseLocalNumerator baseZ / baseLocalDenominator baseZ))) *
            algebraMap PS LS baseRegularizedEndpoint := by ring
    _ = ((baseLocalConnectionNumerator baseZ /
          ((baseLocalS baseZ - 1) * baseLocalPole baseZ)) * baseZ) *
          algebraMap PS LS baseRegularizedEndpoint := by rw [hscalar]
    _ = (baseLocalConnectionNumerator baseZ /
          ((baseLocalS baseZ - 1) * baseLocalPole baseZ)) *
          (baseZ * algebraMap PS LS baseRegularizedEndpoint) := by ring

theorem baseVisible_ne_zero : algebraMap PS LS baseVisible ≠ 0 := by
  have hpower : baseVisible ≠ 0 := by
    apply mul_ne_zero PowerSeries.X_ne_zero
    intro hzero
    have hconstant := congrArg PowerSeries.constantCoeff hzero
    rw [baseRegularizedEndpoint_constantCoeff] at hconstant
    norm_num at hconstant
  simpa only [map_zero] using
    (FaithfulSMul.algebraMap_injective PS LS).ne hpower

end

end AxiomPackJacobianCriticalBaseLaurentCoordinate
