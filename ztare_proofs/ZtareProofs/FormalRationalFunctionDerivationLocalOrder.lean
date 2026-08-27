import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.FieldTheory.RatFunc.AsPolynomial
import Mathlib.RingTheory.Derivation.Basic
import Mathlib.Tactic

/-!
# Formal differentiation and local orders in a rational-function field

This module constructs the ordinary formal derivative on `RatFunc K` from
the quotient rule, proves its exact action on every polynomial quotient, and
constructs the zero/pole normal form of a rational function at a finite
point from the root multiplicities of its canonical numerator and
denominator.
-/

namespace FormalRationalFunctionDerivationLocalOrder

open Polynomial

variable {K : Type*} [Field K]

/-- Quotient-rule numerator divided by the square of the denominator. -/
noncomputable def quotientDerivative
    (numerator denominator : K[X]) : RatFunc K :=
  algebraMap K[X] (RatFunc K)
      (numerator.derivative * denominator -
        numerator * denominator.derivative) /
    algebraMap K[X] (RatFunc K) denominator ^ 2

/-- The quotient derivative is unchanged when numerator and denominator are
multiplied by the same nonzero polynomial. -/
theorem quotientDerivative_mul_common
    (numerator denominator common : K[X])
    (hdenominator : denominator ≠ 0) (hcommon : common ≠ 0) :
    quotientDerivative (common * numerator) (common * denominator) =
      quotientDerivative numerator denominator := by
  rw [quotientDerivative, quotientDerivative]
  simp only [derivative_mul, map_add, map_sub, map_mul]
  field_simp [RatFunc.algebraMap_ne_zero hdenominator,
    RatFunc.algebraMap_ne_zero hcommon]
  ring

/-- Ordinary formal differentiation on the rational-function field. -/
noncomputable def rationalDerivative (value : RatFunc K) : RatFunc K :=
  value.liftOn' quotientDerivative (by
    intro numerator denominator common hdenominator hcommon
    exact quotientDerivative_mul_common numerator denominator common
      hdenominator hcommon)

/-- Exact quotient rule for arbitrary polynomial representatives. -/
theorem rationalDerivative_div
    (numerator denominator : K[X]) :
    rationalDerivative
        (algebraMap K[X] (RatFunc K) numerator /
          algebraMap K[X] (RatFunc K) denominator) =
      quotientDerivative numerator denominator := by
  rw [rationalDerivative]
  apply RatFunc.liftOn'_div
  intro polynomial
  simp [quotientDerivative]

/-- Formal differentiation commutes with addition. -/
theorem rationalDerivative_add (first second : RatFunc K) :
    rationalDerivative (first + second) =
      rationalDerivative first + rationalDerivative second := by
  induction first using RatFunc.induction_on with
  | f firstNumerator firstDenominator hfirstDenominator =>
      induction second using RatFunc.induction_on with
      | f secondNumerator secondDenominator hsecondDenominator =>
          have hproduct :
              firstDenominator * secondDenominator ≠ 0 :=
            mul_ne_zero hfirstDenominator hsecondDenominator
          rw [show
              algebraMap K[X] (RatFunc K) firstNumerator /
                    algebraMap K[X] (RatFunc K) firstDenominator +
                  algebraMap K[X] (RatFunc K) secondNumerator /
                    algebraMap K[X] (RatFunc K) secondDenominator =
                algebraMap K[X] (RatFunc K)
                      (firstNumerator * secondDenominator +
                        firstDenominator * secondNumerator) /
                    algebraMap K[X] (RatFunc K)
                      (firstDenominator * secondDenominator) by
                simp only [map_add, map_mul]
                field_simp [RatFunc.algebraMap_ne_zero hfirstDenominator,
                  RatFunc.algebraMap_ne_zero hsecondDenominator]]
          rw [rationalDerivative_div, rationalDerivative_div,
            rationalDerivative_div]
          rw [quotientDerivative, quotientDerivative, quotientDerivative]
          simp only [derivative_mul, map_add, map_sub,
            map_mul]
          field_simp [RatFunc.algebraMap_ne_zero hfirstDenominator,
            RatFunc.algebraMap_ne_zero hsecondDenominator,
            RatFunc.algebraMap_ne_zero hproduct]
          ring

/-- Formal differentiation obeys the Leibniz law. -/
theorem rationalDerivative_mul (first second : RatFunc K) :
    rationalDerivative (first * second) =
      first * rationalDerivative second +
        second * rationalDerivative first := by
  induction first using RatFunc.induction_on with
  | f firstNumerator firstDenominator hfirstDenominator =>
      induction second using RatFunc.induction_on with
      | f secondNumerator secondDenominator hsecondDenominator =>
          have hproduct :
              firstDenominator * secondDenominator ≠ 0 :=
            mul_ne_zero hfirstDenominator hsecondDenominator
          rw [show
              (algebraMap K[X] (RatFunc K) firstNumerator /
                    algebraMap K[X] (RatFunc K) firstDenominator) *
                  (algebraMap K[X] (RatFunc K) secondNumerator /
                    algebraMap K[X] (RatFunc K) secondDenominator) =
                algebraMap K[X] (RatFunc K)
                      (firstNumerator * secondNumerator) /
                    algebraMap K[X] (RatFunc K)
                      (firstDenominator * secondDenominator) by
                simp only [map_mul]
                exact div_mul_div_comm _ _ _ _]
          rw [rationalDerivative_div, rationalDerivative_div,
            rationalDerivative_div]
          rw [quotientDerivative, quotientDerivative, quotientDerivative]
          simp only [derivative_mul, map_add, map_sub, map_mul]
          field_simp [RatFunc.algebraMap_ne_zero hfirstDenominator,
            RatFunc.algebraMap_ne_zero hsecondDenominator,
            RatFunc.algebraMap_ne_zero hproduct]
          ring

/-- The rational derivative as an additive homomorphism. -/
noncomputable def rationalDerivativeAddHom : RatFunc K →+ RatFunc K where
  toFun := rationalDerivative
  map_zero' := by
    simpa [quotientDerivative] using
      (rationalDerivative_div (0 : K[X]) 1)
  map_add' := rationalDerivative_add

@[simp]
theorem rationalDerivative_one :
    rationalDerivative (1 : RatFunc K) = 0 := by
  simpa [quotientDerivative] using
    (rationalDerivative_div (1 : K[X]) 1)

@[simp]
theorem rationalDerivative_C (constant : K) :
    rationalDerivative (RatFunc.C constant) = 0 := by
  rw [← RatFunc.algebraMap_C]
  simpa [quotientDerivative] using
    (rationalDerivative_div (Polynomial.C constant) 1)

/-- Linearity over the constant field. -/
noncomputable def rationalDerivativeLinearMap :
    RatFunc K →ₗ[K] RatFunc K where
  toFun := rationalDerivative
  map_add' := rationalDerivative_add
  map_smul' := by
    intro constant value
    rw [RatFunc.smul_eq_C_mul, RatFunc.smul_eq_C_mul,
      rationalDerivative_mul, rationalDerivative_C]
    simp only [RingHom.id_apply]
    ring

/-- The ordinary formal derivative as a derivation over the constant field.
-/
noncomputable def ratFuncDerivationOverConstants :
    Derivation K (RatFunc K) (RatFunc K) :=
  Derivation.mk'
    (rationalDerivativeLinearMap (K := K))
    (by
      intro first second
      simpa only [smul_eq_mul] using
        (rationalDerivative_mul first second))

/-- Use the canonical integer algebra on the rational-function ring.  The
generic `RatFunc` algebra instance factors through `K[X]`; that instance has
the same integer action but is not definitionally the one expected by
integer-linear polynomial derivation kernels. -/
noncomputable local instance ratFuncCanonicalIntAlgebra :
    Algebra ℤ (RatFunc K) :=
  Ring.toIntAlgebra (RatFunc K)

/-- The ordinary formal derivative packaged as a derivation over `ℤ`.
Constructing it directly from the canonical integer-linear structure avoids
introducing a second, tower-induced `Algebra ℤ (RatFunc K)` instance. -/
noncomputable def ratFuncDerivation :
    Derivation ℤ (RatFunc K) (RatFunc K) :=
  Derivation.mk'
    rationalDerivativeAddHom.toIntLinearMap
    (by
      intro first second
      simpa only [smul_eq_mul] using
        (rationalDerivative_mul first second))

@[simp]
theorem ratFuncDerivation_apply (value : RatFunc K) :
    ratFuncDerivation value = rationalDerivative value :=
  rfl

/-- The packaged derivation has the exact quotient-rule formula. -/
theorem ratFuncDerivation_div
    (numerator denominator : K[X]) :
    ratFuncDerivation
        (algebraMap K[X] (RatFunc K) numerator /
          algebraMap K[X] (RatFunc K) denominator) =
      quotientDerivative numerator denominator := by
  exact rationalDerivative_div numerator denominator

/-- The exact finite local factorization of a nonzero polynomial. -/
theorem localPolynomialFactorization
    (polynomial : K[X]) (point : K) (hpolynomial : polynomial ≠ 0) :
    polynomial =
        (X - C point) ^ polynomial.rootMultiplicity point *
          (polynomial /ₘ
            (X - C point) ^ polynomial.rootMultiplicity point) ∧
      (polynomial /ₘ
          (X - C point) ^ polynomial.rootMultiplicity point).eval point ≠
        0 := by
  constructor
  · exact (pow_mul_divByMonic_rootMultiplicity_eq polynomial point).symm
  · exact eval_divByMonic_pow_rootMultiplicity_ne_zero point hpolynomial

/-- Canonical zero/pole orders and unit factors of a nonzero rational
function at a finite point. -/
theorem rationalFunctionLocalNormalForm
    (value : RatFunc K) (point : K) (hvalue : value ≠ 0) :
    let numeratorUnit :=
      value.num /ₘ (X - C point) ^ value.num.rootMultiplicity point
    let denominatorUnit :=
      value.denom /ₘ (X - C point) ^ value.denom.rootMultiplicity point
    value.num =
        (X - C point) ^ value.num.rootMultiplicity point *
          numeratorUnit ∧
      value.denom =
        (X - C point) ^ value.denom.rootMultiplicity point *
          denominatorUnit ∧
      numeratorUnit.eval point ≠ 0 ∧
      denominatorUnit.eval point ≠ 0 := by
  dsimp only
  have hnumerator := localPolynomialFactorization
    value.num point (RatFunc.num_ne_zero hvalue)
  have hdenominator := localPolynomialFactorization
    value.denom point value.denom_ne_zero
  exact ⟨hnumerator.1, hdenominator.1,
    hnumerator.2, hdenominator.2⟩

end FormalRationalFunctionDerivationLocalOrder
