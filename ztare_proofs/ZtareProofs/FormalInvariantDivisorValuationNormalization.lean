import Mathlib.Algebra.Polynomial.Degree.TrailingDegree
import Mathlib.Algebra.Polynomial.Div
import Mathlib.Tactic
import ZtareProofs.FormalDifferentialPolynomialInvariantSpecialization
import ZtareProofs.FormalInvariantDivisorEigenrowSpecialization

/-!
# Automatic valuation normalization on an invariant polynomial divisor

Every nonzero polynomial has a canonical power of `X`, measured by its
natural trailing degree, whose quotient is nonzero at `X = 0`.  For a total
derivation whose visible velocity has a double zero, differentiating this
factorization produces only a first-order valuation correction.  A cross
row for two polynomials therefore cancels its common `X`-power and
specializes to a scalar eigenrow for the coefficient derivation.

The quotient polynomials and their valuations are constructed here.  They
are not carrier data for downstream Darboux arguments.
-/

namespace FormalInvariantDivisorValuationNormalization

open Polynomial
open FormalDifferentialPolynomialInvariantSpecialization
open FormalInvariantDivisorEigenrowSpecialization

variable {K : Type*} [CommRing K]

/-- Remove the exact `X`-valuation of a nonzero polynomial.  The remaining
factor is nonzero on the invariant divisor `X = 0`. -/
theorem exists_X_power_unit_factorization
    (polynomial : K[X]) (hpolynomial : polynomial ≠ 0) :
    ∃ unitPart : K[X],
      polynomial = X ^ polynomial.natTrailingDegree * unitPart ∧
      unitPart.eval 0 ≠ 0 := by
  have hdvd : X ^ polynomial.natTrailingDegree ∣ polynomial := by
    rw [X_pow_dvd_iff]
    intro degree hdegree
    exact coeff_eq_zero_of_lt_natTrailingDegree hdegree
  obtain ⟨unitPart, hfactorization⟩ := hdvd
  have htrailing :
      polynomial.coeff polynomial.natTrailingDegree ≠ 0 :=
    coeff_natTrailingDegree_ne_zero.mpr hpolynomial
  have hcoefficient :
      polynomial.coeff polynomial.natTrailingDegree = unitPart.coeff 0 := by
    calc
      polynomial.coeff polynomial.natTrailingDegree =
          (X ^ polynomial.natTrailingDegree * unitPart).coeff
            polynomial.natTrailingDegree :=
        congrArg
          (fun value : K[X] ↦
            value.coeff polynomial.natTrailingDegree)
          hfactorization
      _ = unitPart.coeff 0 := by
        simpa only [zero_add] using
          (coeff_X_pow_mul unitPart polynomial.natTrailingDegree 0)
  have hunitCoefficient : unitPart.coeff 0 ≠ 0 := by
    intro hzero
    exact htrailing (hcoefficient.trans hzero)
  refine ⟨unitPart, hfactorization, ?_⟩
  simpa only [← coeff_zero_eq_eval_zero] using hunitCoefficient

/-- A double-zero velocity preserves the exact `X`-power and records its
logarithmic derivative as one additional factor of `X`. -/
theorem polynomialTotalDerivation_X_power_mul
    (d : Derivation ℤ K K) (pTail unitPart : K[X]) (valuation : ℕ) :
    polynomialTotalDerivation d (X ^ 2 * pTail)
        (X ^ valuation * unitPart) =
      X ^ valuation *
        (polynomialTotalDerivation d (X ^ 2 * pTail) unitPart +
          C (valuation : K) * X * pTail * unitPart) := by
  cases valuation with
  | zero => simp
  | succ valuation =>
      rw [Derivation.leibniz, Derivation.leibniz_pow,
        polynomialTotalDerivation_X]
      simp only [Nat.succ_sub_one, nsmul_eq_mul]
      push_cast
      simp only [map_add, map_one, map_natCast]
      rw [pow_succ]
      ring

variable [IsDomain K]

/-- Cancel the common invariant-divisor power from a polynomial cross row.
The valuation correction is the difference of the two exact orders. -/
theorem normalized_cross_of_X_power_factorizations
    (d : Derivation ℤ K K) (pTail first second : K[X])
    (firstUnit secondUnit : K[X]) (firstValuation secondValuation : ℕ)
    (eigenvalue : K)
    (hfirst : first = X ^ firstValuation * firstUnit)
    (hsecond : second = X ^ secondValuation * secondUnit)
    (hcross :
      second * polynomialTotalDerivation d (X ^ 2 * pTail) first -
          first * polynomialTotalDerivation d (X ^ 2 * pTail) second =
        C eigenvalue * first * second) :
    secondUnit *
          polynomialTotalDerivation d (X ^ 2 * pTail) firstUnit -
        firstUnit *
          polynomialTotalDerivation d (X ^ 2 * pTail) secondUnit +
        C ((firstValuation : K) - (secondValuation : K)) * X * pTail *
          firstUnit * secondUnit =
      C eigenvalue * firstUnit * secondUnit := by
  have hfirstDerivative :=
    polynomialTotalDerivation_X_power_mul
      d pTail firstUnit firstValuation
  have hsecondDerivative :=
    polynomialTotalDerivation_X_power_mul
      d pTail secondUnit secondValuation
  have hfactored :
      X ^ (firstValuation + secondValuation) *
          (secondUnit *
                polynomialTotalDerivation d (X ^ 2 * pTail) firstUnit -
              firstUnit *
                polynomialTotalDerivation d (X ^ 2 * pTail) secondUnit +
              C ((firstValuation : K) - (secondValuation : K)) * X *
                pTail * firstUnit * secondUnit) =
        X ^ (firstValuation + secondValuation) *
          (C eigenvalue * firstUnit * secondUnit) := by
    calc
      X ^ (firstValuation + secondValuation) *
            (secondUnit *
                  polynomialTotalDerivation d (X ^ 2 * pTail) firstUnit -
                firstUnit *
                  polynomialTotalDerivation d (X ^ 2 * pTail) secondUnit +
                C ((firstValuation : K) - (secondValuation : K)) * X *
                  pTail * firstUnit * secondUnit) =
          (X ^ secondValuation * secondUnit) *
                polynomialTotalDerivation d (X ^ 2 * pTail)
                  (X ^ firstValuation * firstUnit) -
              (X ^ firstValuation * firstUnit) *
                polynomialTotalDerivation d (X ^ 2 * pTail)
                  (X ^ secondValuation * secondUnit) := by
            rw [hfirstDerivative, hsecondDerivative, pow_add]
            simp only [map_sub, map_natCast]
            ring
      _ = second * polynomialTotalDerivation d (X ^ 2 * pTail) first -
            first * polynomialTotalDerivation d (X ^ 2 * pTail) second := by
          rw [hfirst, hsecond]
      _ = C eigenvalue * first * second := hcross
      _ = X ^ (firstValuation + secondValuation) *
            (C eigenvalue * firstUnit * secondUnit) := by
          rw [hfirst, hsecond, pow_add]
          ring
  exact mul_left_cancel₀
    (pow_ne_zero _ (X_ne_zero : (X : K[X]) ≠ 0)) hfactored

/-- A raw polynomial cross row automatically yields nonvanishing normalized
unit parts and the scalar eigenrow on the invariant divisor. -/
theorem exists_normalized_scalar_eigenrow
    (d : Derivation ℤ K K) (pTail first second : K[X])
    (eigenvalue : K)
    (hfirst : first ≠ 0) (hsecond : second ≠ 0)
    (hcross :
      second * polynomialTotalDerivation d (X ^ 2 * pTail) first -
          first * polynomialTotalDerivation d (X ^ 2 * pTail) second =
        C eigenvalue * first * second) :
    ∃ firstUnit secondUnit : K[X],
      first = X ^ first.natTrailingDegree * firstUnit ∧
      second = X ^ second.natTrailingDegree * secondUnit ∧
      firstUnit.eval 0 ≠ 0 ∧ secondUnit.eval 0 ≠ 0 ∧
      secondUnit.eval 0 * d (firstUnit.eval 0) -
          firstUnit.eval 0 * d (secondUnit.eval 0) =
        eigenvalue * firstUnit.eval 0 * secondUnit.eval 0 := by
  obtain ⟨firstUnit, hfirstFactorization, hfirstUnit⟩ :=
    exists_X_power_unit_factorization first hfirst
  obtain ⟨secondUnit, hsecondFactorization, hsecondUnit⟩ :=
    exists_X_power_unit_factorization second hsecond
  have hnormalized := normalized_cross_of_X_power_factorizations
    d pTail first second firstUnit secondUnit
      first.natTrailingDegree second.natTrailingDegree eigenvalue
      hfirstFactorization hsecondFactorization hcross
  refine ⟨firstUnit, secondUnit, hfirstFactorization,
    hsecondFactorization, hfirstUnit, hsecondUnit, ?_⟩
  exact eval_zero_normalized_cross_eigenrow
    d pTail firstUnit secondUnit
      ((first.natTrailingDegree : K) - (second.natTrailingDegree : K))
      eigenvalue hnormalized

/-- Scalar nonresonance at the invariant divisor excludes every nonzero raw
polynomial cross row with the same eigenvalue. -/
theorem no_polynomial_cross_eigenrow_of_scalar_nonresonance
    (d : Derivation ℤ K K) (pTail first second : K[X])
    (eigenvalue : K)
    (hfirst : first ≠ 0) (hsecond : second ≠ 0)
    (hnoScalar : ∀ firstValue secondValue : K,
      firstValue ≠ 0 → secondValue ≠ 0 →
      secondValue * d firstValue - firstValue * d secondValue ≠
        eigenvalue * firstValue * secondValue) :
    second * polynomialTotalDerivation d (X ^ 2 * pTail) first -
          first * polynomialTotalDerivation d (X ^ 2 * pTail) second ≠
        C eigenvalue * first * second := by
  intro hcross
  obtain ⟨firstUnit, secondUnit, _, _, hfirstUnit, hsecondUnit,
      hscalar⟩ :=
    exists_normalized_scalar_eigenrow d pTail first second eigenvalue
      hfirst hsecond hcross
  exact (hnoScalar (firstUnit.eval 0) (secondUnit.eval 0)
    hfirstUnit hsecondUnit) hscalar

/-- Aggregated valuation-normalization certificate. -/
theorem invariant_divisor_valuation_normalization_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (pTail first second : K[X])
      (eigenvalue : K),
      first ≠ 0 → second ≠ 0 →
      (∀ firstValue secondValue : K,
        firstValue ≠ 0 → secondValue ≠ 0 →
        secondValue * d firstValue - firstValue * d secondValue ≠
          eigenvalue * firstValue * secondValue) →
      second * polynomialTotalDerivation d (X ^ 2 * pTail) first -
            first * polynomialTotalDerivation d (X ^ 2 * pTail) second ≠
          C eigenvalue * first * second := by
  intro d pTail first second eigenvalue hfirst hsecond hnoScalar
  exact no_polynomial_cross_eigenrow_of_scalar_nonresonance
    d pTail first second eigenvalue hfirst hsecond hnoScalar

end FormalInvariantDivisorValuationNormalization
