import Mathlib.Tactic
import ZtareProofs.FormalDifferentialPolynomialInvariantSpecialization

/-!
# Specializing a normalized eigenrow on a multiple equilibrium divisor

After removing the exact powers of an invariant variable from two filtered
coefficients, their cross relation contains one correction term proportional
to `p(Y) / Y`.  For a double equilibrium `p(Y) = Y^2 pTail(Y)`, that
correction vanishes on `Y=0`.  Evaluation therefore turns the polynomial
cross row into a scalar eigenrow for the coefficient derivation.

This file owns only that specialization step.  Nonresonance of the scalar row
may come from monodromy, residues, or another coefficient-field theorem.
-/

namespace FormalInvariantDivisorEigenrowSpecialization

open Polynomial

open FormalDifferentialPolynomialInvariantSpecialization

variable {R : Type*} [CommRing R]

/-- The velocity `Y^2 * pTail` preserves `Y=0`. -/
theorem eval_zero_quadratic_velocity (pTail : R[X]) :
    (X ^ 2 * pTail).eval 0 = 0 := by
  simp

/-- A normalized cross row specializes to the coefficient-field eigenrow;
the valuation-correction term disappears because the velocity has a double
zero. -/
theorem eval_zero_normalized_cross_eigenrow
    (d : Derivation ℤ R R)
    (pTail firstUnit secondUnit : R[X])
    (valuationCorrection eigenvalue : R)
    (hcross :
      secondUnit *
            polynomialTotalDerivation d (X ^ 2 * pTail) firstUnit -
          firstUnit *
            polynomialTotalDerivation d (X ^ 2 * pTail) secondUnit +
          C valuationCorrection * X * pTail * firstUnit * secondUnit =
        C eigenvalue * firstUnit * secondUnit) :
    secondUnit.eval 0 * d (firstUnit.eval 0) -
        firstUnit.eval 0 * d (secondUnit.eval 0) =
      eigenvalue * firstUnit.eval 0 * secondUnit.eval 0 := by
  have hmapped := congrArg (fun polynomial : R[X] ↦ polynomial.eval 0) hcross
  simp only [eval_add, eval_sub, eval_mul, eval_C, eval_X] at hmapped
  rw [eval_zero_polynomialTotalDerivation d (X ^ 2 * pTail)
      (eval_zero_quadratic_velocity pTail) firstUnit,
    eval_zero_polynomialTotalDerivation d (X ^ 2 * pTail)
      (eval_zero_quadratic_velocity pTail) secondUnit] at hmapped
  simpa using hmapped

/-- If the scalar coefficient field excludes the specialized eigenrow, then
the normalized polynomial cross row is impossible. -/
theorem no_normalized_cross_eigenrow_of_scalar_nonresonance
    (d : Derivation ℤ R R)
    (pTail firstUnit secondUnit : R[X])
    (valuationCorrection eigenvalue : R)
    (hnoScalar :
      secondUnit.eval 0 * d (firstUnit.eval 0) -
          firstUnit.eval 0 * d (secondUnit.eval 0) ≠
        eigenvalue * firstUnit.eval 0 * secondUnit.eval 0) :
    ¬(
      secondUnit *
            polynomialTotalDerivation d (X ^ 2 * pTail) firstUnit -
          firstUnit *
            polynomialTotalDerivation d (X ^ 2 * pTail) secondUnit +
          C valuationCorrection * X * pTail * firstUnit * secondUnit =
        C eigenvalue * firstUnit * secondUnit) := by
  intro hcross
  exact hnoScalar
    (eval_zero_normalized_cross_eigenrow d pTail firstUnit secondUnit
      valuationCorrection eigenvalue hcross)

/-- Aggregated invariant-divisor eigenrow specialization certificate. -/
theorem invariant_divisor_eigenrow_specialization_terminal_certificate :
    ∀ (d : Derivation ℤ R R)
      (pTail firstUnit secondUnit : R[X])
      (valuationCorrection eigenvalue : R),
      (secondUnit.eval 0 * d (firstUnit.eval 0) -
            firstUnit.eval 0 * d (secondUnit.eval 0) ≠
          eigenvalue * firstUnit.eval 0 * secondUnit.eval 0) →
      ¬(
        secondUnit *
              polynomialTotalDerivation d (X ^ 2 * pTail) firstUnit -
            firstUnit *
              polynomialTotalDerivation d (X ^ 2 * pTail) secondUnit +
            C valuationCorrection * X * pTail * firstUnit * secondUnit =
          C eigenvalue * firstUnit * secondUnit) := by
  intro d pTail firstUnit secondUnit valuationCorrection eigenvalue
    hnoScalar
  exact no_normalized_cross_eigenrow_of_scalar_nonresonance
    d pTail firstUnit secondUnit valuationCorrection eigenvalue
    hnoScalar

end FormalInvariantDivisorEigenrowSpecialization
