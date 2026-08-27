import Mathlib.Tactic
import ZtareProofs.FormalCriticalConnectionRationalization
import ZtareProofs.FormalInvariantDivisorValuationNormalization
import ZtareProofs.FormalRationalEigenrowResidueBinding

/-!
# Excluding rational eigenrows for the critical July connection

The critical rational differential has a certified simple pole with an
irrational residue.  This module constructs the reduced local denominator
at that pole, binds it to the exact rationalized July connection, and
excludes every nonzero integral scalar eigenrow.  The final theorem lifts
that scalar exclusion through automatic invariant-divisor valuation
normalization to the polynomial cross-weight rows used by filtered Darboux
rigidity.
-/

namespace FormalCriticalRationalEigenrowExclusion

open Polynomial

open FormalCriticalConnectionRationalization
open FormalCriticalMonodromyResidueBinding
open FormalDifferentialPolynomialInvariantSpecialization
open FormalInvariantDivisorValuationNormalization
open FormalRationalEigenrowResidueBinding
open FormalRationalFunctionDerivationLocalOrder
open FormalRationalLogDerivativeResidueComparison

abbrev RF := RatFunc ℝ

noncomputable local instance criticalRFCanonicalIntAlgebra :
    Algebra ℤ RF :=
  Ring.toIntAlgebra RF

/-- Remove the certified linear pole factor while retaining the separate
parameter-minus-one factor of the critical connection. -/
noncomputable def criticalReducedDenominator (point : ℝ) : ℝ[X] :=
  (X - C 1) * (polePolynomial /ₘ (X - C point))

theorem polePolynomial_factorization_of_root
    {point : ℝ} (hroot : poleValue point = 0) :
    (X - C point) * (polePolynomial /ₘ (X - C point)) =
      polePolynomial := by
  apply mul_divByMonic_eq_iff_isRoot.mpr
  simpa only [IsRoot, poleValue] using hroot

theorem reduced_pole_factor_eval_eq_derivative
    (point : ℝ) :
    (polePolynomial /ₘ (X - C point)).eval point =
      poleDerivativeValue point := by
  have hderivative :=
    divByMonic_add_X_sub_C_mul_derivative_divByMonic_eq_derivative
      polePolynomial point
  have hevaluated := congrArg (fun value : ℝ[X] ↦ value.eval point)
    hderivative
  simpa only [eval_add, eval_mul, eval_sub, eval_X, eval_C, sub_self,
    zero_mul, add_zero, poleDerivativeValue] using hevaluated

theorem criticalReducedDenominator_eval
    (point : ℝ) :
    (criticalReducedDenominator point).eval point =
      residueDenominator point := by
  rw [criticalReducedDenominator, eval_mul, eval_sub, eval_X, eval_C,
    reduced_pole_factor_eval_eq_derivative]
  rfl

theorem critical_denominator_polynomial_factorization
    {point : ℝ} (hroot : poleValue point = 0) :
    (X - C point) * criticalReducedDenominator point =
      (X - C 1) * polePolynomial := by
  rw [criticalReducedDenominator]
  calc
    (X - C point) *
          ((X - C 1) * (polePolynomial /ₘ (X - C point))) =
        (X - C 1) *
          ((X - C point) * (polePolynomial /ₘ (X - C point))) := by
      ring
    _ = (X - C 1) * polePolynomial := by
      rw [polePolynomial_factorization_of_root hroot]

/-- The displayed critical differential in the exact local denominator form
consumed by the rational residue kernel. -/
theorem explicitRationalDifferential_local_form
    {point : ℝ} (hroot : poleValue point = 0) :
    explicitRationalDifferential =
      algebraMap ℝ[X] RF numeratorPolynomial /
        algebraMap ℝ[X] RF
          ((X - C point) * criticalReducedDenominator point) := by
  have hfactor := congrArg (algebraMap ℝ[X] RF)
    (critical_denominator_polynomial_factorization hroot)
  rw [explicitRationalDifferential, numeratorRationalFunction,
    poleRationalFunction]
  congr 1
  simpa only [map_mul, map_sub, RatFunc.algebraMap_X,
    RatFunc.algebraMap_C, map_one] using hfactor.symm

theorem critical_residue_equation
    {point residue : ℝ}
    (hroot : poleValue point = 0)
    (hresidue : residue = residueAt point) :
    numeratorPolynomial.eval point =
      residue * (criticalReducedDenominator point).eval point := by
  have hdenominator := residueDenominator_ne_zero_of_root hroot
  rw [criticalReducedDenominator_eval, hresidue, residueAt,
    numeratorValue]
  field_simp [hdenominator]

/-- No nonzero integral multiple of the exact critical connection admits a
cross row between two nonzero rational functions. -/
theorem no_nonzero_integral_critical_rational_cross
    (weight : ℤ) (hweight : weight ≠ 0)
    (first second : RF) (hfirst : first ≠ 0) (hsecond : second ≠ 0) :
    second * ratFuncDerivation first -
          first * ratFuncDerivation second ≠
        RatFunc.C (weight : ℝ) * explicitRationalDifferential *
          first * second := by
  intro hcross
  obtain ⟨point, residue, _, hroot, _, hresidueDenominator,
      hresidue, _, hirrational, _⟩ :=
    exists_critical_irrational_residue_with_infinite_monodromy
  have hreducedAtPoint :
      (criticalReducedDenominator point).eval point ≠ 0 := by
    rw [criticalReducedDenominator_eval]
    exact hresidueDenominator
  have horder :=
    local_order_eq_weight_mul_residue_of_rational_cross
      point (weight : ℝ) residue numeratorPolynomial
        (criticalReducedDenominator point) explicitRationalDifferential
        first second hfirst hsecond hreducedAtPoint
        (critical_residue_equation hroot hresidue)
        (explicitRationalDifferential_local_form hroot) hcross
  exact
    (irrational_residue_excludes_integral_weight residue hirrational
      weight hweight ((first / second).num.rootMultiplicity point)
        ((first / second).denom.rootMultiplicity point)) horder

/-- Natural filtered weights differ by a nonzero integral weight. -/
theorem no_distinct_natural_weight_critical_rational_cross
    (firstWeight secondWeight : ℕ)
    (hweights : firstWeight ≠ secondWeight)
    (first second : RF) (hfirst : first ≠ 0) (hsecond : second ≠ 0) :
    second * ratFuncDerivation first -
          first * ratFuncDerivation second ≠
        ((secondWeight : RF) - (firstWeight : RF)) *
          explicitRationalDifferential * first * second := by
  have hintegerWeight :
      (secondWeight : ℤ) - (firstWeight : ℤ) ≠ 0 := by
    exact sub_ne_zero.mpr (by exact_mod_cast hweights.symm)
  have hcritical := no_nonzero_integral_critical_rational_cross
    ((secondWeight : ℤ) - (firstWeight : ℤ)) hintegerWeight
      first second hfirst hsecond
  simpa only [Int.cast_sub, Int.cast_natCast,
    map_sub, map_natCast] using hcritical

/-- The exact cross-weight nonresonance row required by the direct
polynomial-domain Darboux-prime exclusion theorem. -/
theorem no_critical_polynomial_cross_weight_row
    (pTail first second : RF[X])
    (firstWeight secondWeight : ℕ)
    (hweights : firstWeight ≠ secondWeight)
    (hfirst : first ≠ 0) (hsecond : second ≠ 0) :
    second * polynomialTotalDerivation (ratFuncDerivation (K := ℝ))
          (X ^ 2 * pTail)
          first -
        first * polynomialTotalDerivation (ratFuncDerivation (K := ℝ))
          (X ^ 2 * pTail)
          second ≠
      ((secondWeight : RF[X]) - (firstWeight : RF[X])) *
        C explicitRationalDifferential * first * second := by
  have hnormalized :=
    no_polynomial_cross_eigenrow_of_scalar_nonresonance
      (ratFuncDerivation (K := ℝ)) pTail first second
        (((secondWeight : RF) - (firstWeight : RF)) *
          explicitRationalDifferential)
        hfirst hsecond (by
          intro firstValue secondValue hfirstValue hsecondValue
          exact no_distinct_natural_weight_critical_rational_cross
            firstWeight secondWeight hweights firstValue secondValue
              hfirstValue hsecondValue)
  simpa only [Nat.cast_sub, map_sub, map_natCast, C_mul] using hnormalized

/-- Aggregated base-field critical nonresonance certificate. -/
theorem critical_rational_eigenrow_exclusion_terminal_certificate :
    ∀ (pTail first second : RF[X])
      (firstWeight secondWeight : ℕ),
      firstWeight ≠ secondWeight → first ≠ 0 → second ≠ 0 →
      second * polynomialTotalDerivation (ratFuncDerivation (K := ℝ))
            (X ^ 2 * pTail) first -
          first * polynomialTotalDerivation (ratFuncDerivation (K := ℝ))
            (X ^ 2 * pTail) second ≠
        ((secondWeight : RF[X]) - (firstWeight : RF[X])) *
          C explicitRationalDifferential * first * second := by
  intro pTail first second firstWeight secondWeight hweights hfirst hsecond
  exact no_critical_polynomial_cross_weight_row pTail first second
    firstWeight secondWeight hweights hfirst hsecond

end FormalCriticalRationalEigenrowExclusion
