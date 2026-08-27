import Mathlib.Tactic
import ZtareProofs.FormalCriticalRationalEigenrowExclusion
import ZtareProofs.FormalPolynomialTotalDerivativeDichotomy
import ZtareProofs.FormalSaturatedDarbouxPrimeExclusion

/-!
# The critical finite derivative prefix forces a visible eliminant

For the exact July rational connection, localize the visible endpoint ring
`RF[F]` and regard the normalized coupled relation as a polynomial in the
hidden variable `Y`.  The localized finite-prefix dichotomy produces either
a visible eliminant or a primitive polynomial-domain Darboux factor.  The
critical irrational-residue nonresonance theorem excludes the latter.

The output is the algebraic branch needed by the global continuation
argument.  This file does not evaluate the eliminant on continued endpoint
branches.
-/

namespace FormalCriticalFiniteDerivativeEliminant

open Polynomial
open FormalBivariateDerivationSwap
open FormalCoupledJuliaAllOrderSpecialization
open FormalCriticalConnectionRationalization
open FormalCriticalRationalEigenrowExclusion
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFiniteDerivativeDarbouxAlternative
open FormalPolynomialTotalDerivativeDichotomy
open FormalRationalFunctionDerivationLocalOrder
open FormalSaturatedDarbouxPrimeExclusion

abbrev RF := RatFunc ℝ

noncomputable local instance criticalRFCanonicalIntAlgebra :
    Algebra ℤ RF :=
  Ring.toIntAlgebra RF

/-- The visible coefficient derivation: parameter differentiation plus the
exact logarithmic critical velocity of `F`. -/
noncomputable def criticalVisiblePolynomialDerivation :
    Derivation ℤ RF[X] RF[X] :=
  polynomialTotalDerivation
    (ratFuncDerivation (K := ℝ))
    (C explicitRationalDifferential * X)

theorem criticalStoredDerivation_eq_total (pTail : RF[X]) :
    storedBivariateDerivation
        (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
        explicitRationalDifferential =
      polynomialTotalDerivation criticalVisiblePolynomialDerivation
        ((X ^ 2 * pTail).map C) := by
  rfl

/-- Nonvanishing of the special fiber proves nonvanishing of the normalized
coupled relation without a separate initial-polynomial premise. -/
theorem criticalNormalizedCoupledRelation_ne_zero
    (pTail q qTail : RF[X]) (a0 : RF)
    (hq : q ≠ 0) (ha0 : a0 ≠ 0) :
    normalizedCoupledRelation (X ^ 2 * pTail) q qTail a0 ≠ 0 := by
  intro hzero
  have hmapped := congrArg
    (fun polynomial : RF[X][X] ↦ polynomial.map (evalRingHom 0)) hzero
  have hmapped' :
      (normalizedCoupledRelation
        (X ^ 2 * pTail) q qTail a0).map (evalRingHom 0) = 0 := by
    simpa using hmapped
  rw [map_eval_zero_normalizedCoupledRelation] at hmapped'
  have hproduct : -C a0 * q ≠ 0 :=
    mul_ne_zero (neg_ne_zero.mpr (C_ne_zero.mpr ha0)) hq
  exact hproduct hmapped'

/-- The Darboux branch of the localized dichotomy is impossible for the
critical connection. -/
theorem no_critical_normalized_darboux_factor
    (pTail q qTail : RF[X]) (a0 : RF)
    (hq : q ≠ 0) (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime (X ^ 2 * pTail) q)
    (h : RF[X][X]) (hirreducible : Irreducible h)
    (hdivRelation :
      h ∣ normalizedCoupledRelation (X ^ 2 * pTail) q qTail a0)
    (hdivDerivative : h ∣
      polynomialTotalDerivation criticalVisiblePolynomialDerivation
        ((X ^ 2 * pTail).map C) h) :
    False := by
  have hstoredDerivative : h ∣
      storedBivariateDerivation
        (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
        explicitRationalDifferential h := by
    rw [criticalStoredDerivation_eq_total]
    exact hdivDerivative
  apply no_saturated_persistent_darboux_prime_over_polynomial_domain
    (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail) q qTail
    explicitRationalDifferential a0 hq hqTail ha0 hcoprime
    h hirreducible hdivRelation hstoredDerivative
  intro firstWeight secondWeight hweights hfirst hsecond
  exact no_critical_polynomial_cross_weight_row
    pTail
    ((Bivariate.swap h).coeff firstWeight)
    ((Bivariate.swap h).coeff secondWeight)
    firstWeight secondWeight hweights hfirst hsecond

/-- Every critical normalized finite derivative prefix contains a nonzero
polynomial in the visible endpoint alone.  The prefix length is the intrinsic
hidden degree of the normalized relation. -/
theorem exists_critical_visible_eliminant
    (pTail q qTail : RF[X]) (a0 : RF)
    (hq : q ≠ 0) (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime (X ^ 2 * pTail) q) :
    ∃ eliminant : RF[X], eliminant ≠ 0 ∧
      C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation
          (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
          explicitRationalDifferential)
        (normalizedCoupledRelation (X ^ 2 * pTail) q qTail a0)
        (normalizedCoupledRelation
          (X ^ 2 * pTail) q qTail a0).natDegree := by
  let initial : RF[X][X] :=
    normalizedCoupledRelation (X ^ 2 * pTail) q qTail a0
  have hinitial : initial ≠ 0 :=
    criticalNormalizedCoupledRelation_ne_zero
      pTail q qTail a0 hq ha0
  obtain heliminant | ⟨h, hirreducible, hdivInitial, hdarboux⟩ :=
    exists_base_eliminant_or_primitive_darboux_factor_for_total_derivation
      criticalVisiblePolynomialDerivation
      ((X ^ 2 * pTail).map C) initial hinitial
  · rw [criticalStoredDerivation_eq_total]
    exact heliminant
  · exact (no_critical_normalized_darboux_factor
      pTail q qTail a0 hq hqTail ha0 hcoprime
      h hirreducible hdivInitial hdarboux).elim

/-- Aggregated critical finite-prefix eliminant certificate. -/
theorem critical_finite_derivative_eliminant_terminal_certificate :
    ∀ (pTail q qTail : RF[X]) (a0 : RF),
      q ≠ 0 → qTail ≠ 0 → a0 ≠ 0 →
      IsCoprime (X ^ 2 * pTail) q →
      ∃ eliminant : RF[X], eliminant ≠ 0 ∧
        C eliminant ∈ derivativePrefixIdeal
          (storedBivariateDerivation
            (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
            explicitRationalDifferential)
          (normalizedCoupledRelation (X ^ 2 * pTail) q qTail a0)
          (normalizedCoupledRelation
            (X ^ 2 * pTail) q qTail a0).natDegree := by
  intro pTail q qTail a0 hq hqTail ha0 hcoprime
  exact exists_critical_visible_eliminant
    pTail q qTail a0 hq hqTail ha0 hcoprime

end FormalCriticalFiniteDerivativeEliminant
