import Mathlib.RingTheory.EuclideanDomain
import Mathlib.Tactic
import ZtareProofs.FormalCriticalRationalEigenrowExclusion
import ZtareProofs.FormalPolynomialTotalDerivativeDichotomy
import ZtareProofs.FormalSaturatedDarbouxPrimeExclusionIndependentVelocity

/-!
# Critical finite derivative eliminant after complete gcd saturation

The two tangent polynomial generators can share equilibria beyond their
universal quadratic factor.  This module divides their complete polynomial
gcd out of the normalized coupled relation while leaving the actual hidden
velocity unchanged in the stored derivation.  The coprime quotient generators
exclude the Darboux branch, so the saturated finite derivative prefix contains
a nonzero visible eliminant.
-/

namespace FormalCriticalGcdSaturatedFiniteDerivativeEliminant

open Polynomial
open FormalBivariateDerivationSwap
open FormalCoupledJuliaAllOrderSpecialization
open FormalCoupledJuliaCommonFactorSaturation
open FormalCriticalConnectionRationalization
open FormalCriticalRationalEigenrowExclusion
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFiniteDerivativeDarbouxAlternative
open FormalPolynomialTotalDerivativeDichotomy
open FormalRationalFunctionDerivationLocalOrder
open FormalSaturatedDarbouxPrimeExclusionIndependentVelocity

abbrev RF := RatFunc ℝ

noncomputable local instance criticalRFCanonicalIntAlgebra :
    Algebra ℤ RF :=
  Ring.toIntAlgebra RF

noncomputable local instance criticalRFNormalizationMonoid :
    NormalizationMonoid RF :=
  UniqueFactorizationMonoid.normalizationMonoid

noncomputable local instance criticalRFNormalizedGCDMonoid :
    NormalizedGCDMonoid RF :=
  UniqueFactorizationMonoid.toNormalizedGCDMonoid RF

noncomputable local instance criticalPolynomialNormalizedGCDMonoid :
    NormalizedGCDMonoid RF[X] :=
  Polynomial.normalizedGcdMonoid

/-- The complete common-equilibrium factor of the two actual generators. -/
noncomputable def criticalGeneratorGcd
    (velocity relationOuter : RF[X]) : RF[X] :=
  GCDMonoid.gcd velocity relationOuter

/-- The first coprime quotient generator. -/
noncomputable def criticalInnerQuotient
    (velocity relationOuter : RF[X]) : RF[X] :=
  velocity / criticalGeneratorGcd velocity relationOuter

/-- The second coprime quotient generator. -/
noncomputable def criticalOuterQuotient
    (velocity relationOuter : RF[X]) : RF[X] :=
  relationOuter / criticalGeneratorGcd velocity relationOuter

/-- The visible coefficient derivation for the exact critical connection. -/
noncomputable def criticalVisiblePolynomialDerivation :
    Derivation ℤ RF[X] RF[X] :=
  polynomialTotalDerivation
    (ratFuncDerivation (K := ℝ))
    (C explicitRationalDifferential * X)

theorem criticalStoredDerivation_eq_total
    (velocity : RF[X]) :
    storedBivariateDerivation
        (ratFuncDerivation (K := ℝ)) velocity
        explicitRationalDifferential =
      polynomialTotalDerivation criticalVisiblePolynomialDerivation
        (velocity.map C) := by
  rfl

theorem criticalGeneratorGcd_ne_zero
    (velocity relationOuter : RF[X])
    (hrelationOuter : relationOuter ≠ 0) :
    criticalGeneratorGcd velocity relationOuter ≠ 0 := by
  exact gcd_ne_zero_of_right hrelationOuter

theorem criticalInner_factorization
    (velocity relationOuter : RF[X])
    (hrelationOuter : relationOuter ≠ 0) :
    criticalGeneratorGcd velocity relationOuter *
        criticalInnerQuotient velocity relationOuter = velocity := by
  exact EuclideanDomain.mul_div_cancel'
    (criticalGeneratorGcd_ne_zero velocity relationOuter hrelationOuter)
    (GCDMonoid.gcd_dvd_left velocity relationOuter)

theorem criticalOuter_factorization
    (velocity relationOuter : RF[X])
    (hrelationOuter : relationOuter ≠ 0) :
    criticalGeneratorGcd velocity relationOuter *
        criticalOuterQuotient velocity relationOuter = relationOuter := by
  exact EuclideanDomain.mul_div_cancel'
    (criticalGeneratorGcd_ne_zero velocity relationOuter hrelationOuter)
    (GCDMonoid.gcd_dvd_right velocity relationOuter)

theorem criticalQuotients_isCoprime
    (velocity relationOuter : RF[X])
    (hrelationOuter : relationOuter ≠ 0) :
    IsCoprime
      (criticalInnerQuotient velocity relationOuter)
      (criticalOuterQuotient velocity relationOuter) := by
  exact isCoprime_div_gcd_div_gcd hrelationOuter

theorem criticalOuterQuotient_ne_zero
    (velocity relationOuter : RF[X])
    (hrelationOuter : relationOuter ≠ 0) :
    criticalOuterQuotient velocity relationOuter ≠ 0 := by
  exact right_div_gcd_ne_zero hrelationOuter

/-- Complete gcd division factors the unsaturated normalized relation while
retaining the original visible tail. -/
theorem critical_normalized_relation_gcd_factorization
    (velocity relationOuter relationOuterTail : RF[X]) (a0 : RF)
    (hrelationOuter : relationOuter ≠ 0) :
    normalizedCoupledRelation
        velocity relationOuter relationOuterTail a0 =
      (criticalGeneratorGcd velocity relationOuter).map C *
        normalizedCoupledRelation
          (criticalInnerQuotient velocity relationOuter)
          (criticalOuterQuotient velocity relationOuter)
          relationOuterTail a0 := by
  calc
    normalizedCoupledRelation
        velocity relationOuter relationOuterTail a0 =
      normalizedCoupledRelation
        (criticalGeneratorGcd velocity relationOuter *
          criticalInnerQuotient velocity relationOuter)
        (criticalGeneratorGcd velocity relationOuter *
          criticalOuterQuotient velocity relationOuter)
        relationOuterTail a0 := by
          rw [criticalInner_factorization
            velocity relationOuter hrelationOuter,
            criticalOuter_factorization
              velocity relationOuter hrelationOuter]
    _ = (criticalGeneratorGcd velocity relationOuter).map C *
        normalizedCoupledRelation
          (criticalInnerQuotient velocity relationOuter)
          (criticalOuterQuotient velocity relationOuter)
          relationOuterTail a0 :=
      normalizedCoupledRelation_mul_common_factor
        (criticalGeneratorGcd velocity relationOuter)
        (criticalInnerQuotient velocity relationOuter)
        (criticalOuterQuotient velocity relationOuter)
        relationOuterTail a0

/-- Nonvanishing follows from the nonzero special fiber of the saturated
relation. -/
theorem criticalSaturatedNormalizedRelation_ne_zero
    (velocity relationOuter relationOuterTail : RF[X]) (a0 : RF)
    (hrelationOuter : relationOuter ≠ 0) (ha0 : a0 ≠ 0) :
    normalizedCoupledRelation
      (criticalInnerQuotient velocity relationOuter)
      (criticalOuterQuotient velocity relationOuter)
      relationOuterTail a0 ≠ 0 := by
  intro hzero
  have hmapped := congrArg
    (fun polynomial : RF[X][X] ↦ polynomial.map (evalRingHom 0)) hzero
  have hmapped' :
      (normalizedCoupledRelation
        (criticalInnerQuotient velocity relationOuter)
        (criticalOuterQuotient velocity relationOuter)
        relationOuterTail a0).map (evalRingHom 0) = 0 := by
    simpa using hmapped
  rw [map_eval_zero_normalizedCoupledRelation] at hmapped'
  have hproduct :
      -C a0 * criticalOuterQuotient velocity relationOuter ≠ 0 :=
    mul_ne_zero (neg_ne_zero.mpr (C_ne_zero.mpr ha0))
      (criticalOuterQuotient_ne_zero
        velocity relationOuter hrelationOuter)
  exact hproduct hmapped'

/-- The independent-velocity Darboux branch is impossible for the exact
critical connection and the complete-gcd quotient relation. -/
theorem no_critical_gcd_saturated_darboux_factor
    (pTail relationOuter relationOuterTail : RF[X]) (a0 : RF)
    (hrelationOuter : relationOuter ≠ 0)
    (hrelationOuterTail : relationOuterTail ≠ 0)
    (ha0 : a0 ≠ 0)
    (h : RF[X][X]) (hirreducible : Irreducible h)
    (hdivRelation :
      h ∣ normalizedCoupledRelation
        (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
        (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
        relationOuterTail a0)
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
  apply
    no_saturated_persistent_darboux_prime_over_polynomial_domain_independent_velocity
      (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
      (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
      (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
      relationOuterTail explicitRationalDifferential a0
      (criticalOuterQuotient_ne_zero
        (X ^ 2 * pTail) relationOuter hrelationOuter)
      hrelationOuterTail ha0
      (criticalQuotients_isCoprime
        (X ^ 2 * pTail) relationOuter hrelationOuter)
      h hirreducible hdivRelation hstoredDerivative
  intro firstWeight secondWeight hweights hfirst hsecond
  exact no_critical_polynomial_cross_weight_row
    pTail
    ((Bivariate.swap h).coeff firstWeight)
    ((Bivariate.swap h).coeff secondWeight)
    firstWeight secondWeight hweights hfirst hsecond

/-- Parameter scaling may change the stored hidden velocity by a nonzero
coefficient-field scalar without changing the two generators that own the
complete-gcd saturation. -/
theorem no_critical_scaled_gcd_saturated_darboux_factor
    (pTail relationOuter relationOuterTail : RF[X]) (speed a0 : RF)
    (hrelationOuter : relationOuter ≠ 0)
    (hrelationOuterTail : relationOuterTail ≠ 0)
    (ha0 : a0 ≠ 0)
    (h : RF[X][X]) (hirreducible : Irreducible h)
    (hdivRelation :
      h ∣ normalizedCoupledRelation
        (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
        (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
        relationOuterTail a0)
    (hdivDerivative : h ∣
      polynomialTotalDerivation criticalVisiblePolynomialDerivation
        ((X ^ 2 * (C speed * pTail)).map C) h) :
    False := by
  have hstoredDerivative : h ∣
      storedBivariateDerivation
        (ratFuncDerivation (K := ℝ))
        (X ^ 2 * (C speed * pTail))
        explicitRationalDifferential h := by
    rw [criticalStoredDerivation_eq_total]
    exact hdivDerivative
  apply
    no_saturated_persistent_darboux_prime_over_polynomial_domain_independent_velocity
      (ratFuncDerivation (K := ℝ))
      (X ^ 2 * (C speed * pTail))
      (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
      (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
      relationOuterTail explicitRationalDifferential a0
      (criticalOuterQuotient_ne_zero
        (X ^ 2 * pTail) relationOuter hrelationOuter)
      hrelationOuterTail ha0
      (criticalQuotients_isCoprime
        (X ^ 2 * pTail) relationOuter hrelationOuter)
      h hirreducible hdivRelation hstoredDerivative
  intro firstWeight secondWeight hweights hfirst hsecond
  exact no_critical_polynomial_cross_weight_row
    (C speed * pTail)
    ((Bivariate.swap h).coeff firstWeight)
    ((Bivariate.swap h).coeff secondWeight)
    firstWeight secondWeight hweights hfirst hsecond

/-- The finite complete-gcd eliminant with stored hidden velocity scaled
independently from the unscaled relation generators. -/
theorem exists_critical_scaled_gcd_saturated_visible_eliminant
    (pTail relationOuter relationOuterTail : RF[X]) (speed a0 : RF)
    (hrelationOuter : relationOuter ≠ 0)
    (hrelationOuterTail : relationOuterTail ≠ 0)
    (ha0 : a0 ≠ 0) :
    ∃ eliminant : RF[X], eliminant ≠ 0 ∧
      C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation
          (ratFuncDerivation (K := ℝ))
          (X ^ 2 * (C speed * pTail))
          explicitRationalDifferential)
        (normalizedCoupledRelation
          (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
          (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
          relationOuterTail a0)
        (normalizedCoupledRelation
          (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
          (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
          relationOuterTail a0).natDegree := by
  let initial : RF[X][X] :=
    normalizedCoupledRelation
      (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
      (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
      relationOuterTail a0
  have hinitial : initial ≠ 0 :=
    criticalSaturatedNormalizedRelation_ne_zero
      (X ^ 2 * pTail) relationOuter relationOuterTail a0
      hrelationOuter ha0
  obtain heliminant | ⟨h, hirreducible, hdivInitial, hdarboux⟩ :=
    exists_base_eliminant_or_primitive_darboux_factor_for_total_derivation
      criticalVisiblePolynomialDerivation
      ((X ^ 2 * (C speed * pTail)).map C) initial hinitial
  · rw [criticalStoredDerivation_eq_total]
    exact heliminant
  · exact (no_critical_scaled_gcd_saturated_darboux_factor
      pTail relationOuter relationOuterTail speed a0
      hrelationOuter hrelationOuterTail ha0
      h hirreducible hdivInitial hdarboux).elim

/-- Every complete-gcd-saturated critical derivative prefix contains a
nonzero visible eliminant.  No coprimality premise is supplied by the caller. -/
theorem exists_critical_gcd_saturated_visible_eliminant
    (pTail relationOuter relationOuterTail : RF[X]) (a0 : RF)
    (hrelationOuter : relationOuter ≠ 0)
    (hrelationOuterTail : relationOuterTail ≠ 0)
    (ha0 : a0 ≠ 0) :
    ∃ eliminant : RF[X], eliminant ≠ 0 ∧
      C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation
          (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
          explicitRationalDifferential)
        (normalizedCoupledRelation
          (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
          (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
          relationOuterTail a0)
        (normalizedCoupledRelation
          (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
          (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
          relationOuterTail a0).natDegree := by
  let initial : RF[X][X] :=
    normalizedCoupledRelation
      (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
      (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
      relationOuterTail a0
  have hinitial : initial ≠ 0 :=
    criticalSaturatedNormalizedRelation_ne_zero
      (X ^ 2 * pTail) relationOuter relationOuterTail a0
      hrelationOuter ha0
  obtain heliminant | ⟨h, hirreducible, hdivInitial, hdarboux⟩ :=
    exists_base_eliminant_or_primitive_darboux_factor_for_total_derivation
      criticalVisiblePolynomialDerivation
      ((X ^ 2 * pTail).map C) initial hinitial
  · rw [criticalStoredDerivation_eq_total]
    exact heliminant
  · exact (no_critical_gcd_saturated_darboux_factor
      pTail relationOuter relationOuterTail a0
      hrelationOuter hrelationOuterTail ha0
      h hirreducible hdivInitial hdarboux).elim

/-- Aggregated complete-gcd saturation and finite-prefix certificate. -/
theorem critical_gcd_saturated_finite_derivative_eliminant_terminal_certificate :
    ∀ (pTail relationOuter relationOuterTail : RF[X]) (a0 : RF),
      relationOuter ≠ 0 → relationOuterTail ≠ 0 → a0 ≠ 0 →
      normalizedCoupledRelation
          (X ^ 2 * pTail) relationOuter relationOuterTail a0 =
        (criticalGeneratorGcd (X ^ 2 * pTail) relationOuter).map C *
          normalizedCoupledRelation
            (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
            (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
            relationOuterTail a0 ∧
      ∃ eliminant : RF[X], eliminant ≠ 0 ∧
        C eliminant ∈ derivativePrefixIdeal
          (storedBivariateDerivation
            (ratFuncDerivation (K := ℝ)) (X ^ 2 * pTail)
            explicitRationalDifferential)
          (normalizedCoupledRelation
            (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
            (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
            relationOuterTail a0)
          (normalizedCoupledRelation
            (criticalInnerQuotient (X ^ 2 * pTail) relationOuter)
            (criticalOuterQuotient (X ^ 2 * pTail) relationOuter)
            relationOuterTail a0).natDegree := by
  intro pTail relationOuter relationOuterTail a0
    hrelationOuter hrelationOuterTail ha0
  exact ⟨
    critical_normalized_relation_gcd_factorization
      (X ^ 2 * pTail) relationOuter relationOuterTail a0 hrelationOuter,
    exists_critical_gcd_saturated_visible_eliminant
      pTail relationOuter relationOuterTail a0
      hrelationOuter hrelationOuterTail ha0⟩

end FormalCriticalGcdSaturatedFiniteDerivativeEliminant
