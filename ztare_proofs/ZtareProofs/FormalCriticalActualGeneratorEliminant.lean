import Mathlib.FieldTheory.RatFunc.IntermediateField
import Mathlib.RingTheory.Algebraic.Basic
import Mathlib.Tactic
import ZtareProofs.FormalCriticalGcdSaturatedFiniteDerivativeEliminant

/-!
# Actual constant-generator adapter for the critical saturated eliminant

The two autonomous generators originate over the constant field.  This file
constructs their quadratic tails, embeds them coefficientwise into the exact
rational differential field, proves the source scalar nonzero by
transcendence of the displayed critical parameterization, and invokes the
complete-gcd saturated finite-prefix theorem.
-/

namespace FormalCriticalActualGeneratorEliminant

open Polynomial
open FormalBivariateDerivationSwap
open FormalCoupledJuliaAllOrderSpecialization
open FormalCriticalConnectionRationalization
open FormalCriticalGcdSaturatedFiniteDerivativeEliminant
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFiniteDerivativeDarbouxAlternative
open FormalRationalFunctionDerivationLocalOrder

abbrev RF := RatFunc ℝ

noncomputable local instance criticalRFCanonicalIntAlgebra :
    Algebra ℤ RF :=
  Ring.toIntAlgebra RF

/-- Coefficientwise embedding of an actual constant-field generator. -/
noncomputable def liftRealGenerator (generator : ℝ[X]) : RF[X] :=
  generator.map (RatFunc.C (K := ℝ))

/-- Evaluation of the original full inner generator at the rational critical
source germ. -/
noncomputable def actualCriticalSourceEvaluation (inner : ℝ[X]) : RF :=
  inner.eval₂ (RatFunc.C (K := ℝ)) xOfParameter

/-- Parameter speed of the hidden inner trajectory under ordinary `d/dt`:
`G_t = c_p p(G)`. -/
noncomputable def actualCriticalHiddenSpeed (inner : ℝ[X]) : RF :=
  xDerivativeOfParameter / actualCriticalSourceEvaluation inner

/-- The Julia coefficient after dividing both parameterized Julia rows by
the nonzero source derivative `x_t`. -/
noncomputable def actualCriticalJuliaCoefficient : RF :=
  explicitRationalDifferential / xDerivativeOfParameter

/-- Correct normalized source scalar in the coupled relation:
`a₀ = (L / x_t) p(x) = L / c_p`. -/
noncomputable def actualCriticalSourceScalar (inner : ℝ[X]) : RF :=
  actualCriticalJuliaCoefficient * actualCriticalSourceEvaluation inner

/-- Stored hidden velocity for the ordinary rational parameter derivative.
The scalar belongs to the coefficient field; complete-gcd saturation remains
owned by the unscaled generator pair. -/
noncomputable def actualCriticalStoredVelocity (inner : ℝ[X]) : RF[X] :=
  C (actualCriticalHiddenSpeed inner) * liftRealGenerator inner

theorem liftRealGenerator_ne_zero
    {generator : ℝ[X]} (hgenerator : generator ≠ 0) :
    liftRealGenerator generator ≠ 0 := by
  exact (Polynomial.map_ne_zero_iff RatFunc.C_injective).2 hgenerator

/-- Constant-field coefficients are killed by the rational parameter
derivation. -/
theorem polynomialCoefficientDerivation_liftRealGenerator_eq_zero
    (generator : ℝ[X]) :
    polynomialCoefficientDerivation (ratFuncDerivation (K := ℝ))
      (liftRealGenerator generator) = 0 := by
  ext degree
  simp [liftRealGenerator, coeff_polynomialCoefficientDerivation,
    ratFuncDerivation_apply, rationalDerivative_C]

/-- The displayed rational parameterization is not a constant rational
function. -/
theorem xOfParameter_ne_C (constant : ℝ) :
    xOfParameter ≠ RatFunc.C constant := by
  intro hconstant
  have hcross :
      (6 : RF) * (parameter ^ 2 - 1) =
        RatFunc.C constant * (parameter ^ 2 + 3) := by
    apply (div_eq_iff parameter_sq_add_three_ne_zero).mp
    simpa [xOfParameter] using hconstant
  let witness : ℝ[X] :=
    Polynomial.C 6 *
        (Polynomial.X ^ 2 - Polynomial.C 1) -
      Polynomial.C constant *
        (Polynomial.X ^ 2 + Polynomial.C 3)
  have hmapped : algebraMap ℝ[X] RF witness = 0 := by
    rw [show algebraMap ℝ[X] RF witness =
      (6 : RF) * (parameter ^ 2 - 1) -
        RatFunc.C constant * (parameter ^ 2 + 3) by
      simp [witness, parameter, RatFunc.algebraMap_C,
        ratFunc_C_six, ratFunc_C_three]]
    exact sub_eq_zero.mpr hcross
  have hwitness : witness = 0 :=
    (RatFunc.algebraMap_injective ℝ) (by simpa using hmapped)
  have hdegreeTwo := congrArg (fun p : ℝ[X] => p.coeff 2) hwitness
  have hdegreeZero := congrArg (fun p : ℝ[X] => p.coeff 0) hwitness
  norm_num [witness, coeff_X, Polynomial.coeff_one]
    at hdegreeTwo hdegreeZero
  linarith

theorem xOfParameter_transcendental :
    Transcendental ℝ xOfParameter := by
  exact RatFunc.transcendental_of_ne_C xOfParameter
    (fun hconstant => by
      obtain ⟨constant, hconstant⟩ := hconstant
      exact xOfParameter_ne_C constant hconstant)

/-- Evaluation at the nonconstant critical parameterization is injective on
constant-field polynomials. -/
theorem eval₂_xOfParameter_ne_zero
    {generator : ℝ[X]} (hgenerator : generator ≠ 0) :
    generator.eval₂ (RatFunc.C (K := ℝ)) xOfParameter ≠ 0 := by
  intro heval
  have haeval : Polynomial.aeval xOfParameter generator = 0 := by
    simpa [Polynomial.aeval_def, RatFunc.algebraMap_eq_C] using heval
  exact hgenerator
    ((transcendental_iff.mp xOfParameter_transcendental) generator haeval)

theorem numeratorRationalFunction_ne_zero :
    numeratorRationalFunction ≠ 0 := by
  rw [numeratorRationalFunction_expansion]
  have hparameter : parameter ≠ 0 := by
    simpa using parameter_sub_constant_ne_zero 0
  exact mul_ne_zero
    (mul_ne_zero
      (mul_ne_zero
        (mul_ne_zero (by norm_num) hparameter)
          parameter_sub_three_ne_zero)
        parameter_add_one_ne_zero)
    parameter_quadratic_minus_ne_zero

theorem explicitRationalDifferential_ne_zero :
    explicitRationalDifferential ≠ 0 := by
  rw [explicitRationalDifferential]
  exact div_ne_zero numeratorRationalFunction_ne_zero
    (mul_ne_zero parameter_sub_one_ne_zero poleRationalFunction_ne_zero)

theorem xDerivativeOfParameter_ne_zero :
    xDerivativeOfParameter ≠ 0 := by
  rw [xDerivativeOfParameter]
  have hparameter : parameter ≠ 0 := by
    simpa using parameter_sub_constant_ne_zero 0
  exact div_ne_zero (mul_ne_zero (by norm_num) hparameter)
    (pow_ne_zero 2 parameter_sq_add_three_ne_zero)

theorem actualCriticalSourceEvaluation_ne_zero
    {inner : ℝ[X]} (hinner : inner ≠ 0) :
    actualCriticalSourceEvaluation inner ≠ 0 := by
  exact eval₂_xOfParameter_ne_zero hinner

theorem actualCriticalHiddenSpeed_ne_zero
    {inner : ℝ[X]} (hinner : inner ≠ 0) :
    actualCriticalHiddenSpeed inner ≠ 0 := by
  exact div_ne_zero xDerivativeOfParameter_ne_zero
    (actualCriticalSourceEvaluation_ne_zero hinner)

theorem actualCriticalJuliaCoefficient_ne_zero :
    actualCriticalJuliaCoefficient ≠ 0 := by
  exact div_ne_zero explicitRationalDifferential_ne_zero
    xDerivativeOfParameter_ne_zero

theorem actualCriticalHiddenSpeed_mul_sourceEvaluation
    {inner : ℝ[X]} (hinner : inner ≠ 0) :
    actualCriticalHiddenSpeed inner *
        actualCriticalSourceEvaluation inner =
      xDerivativeOfParameter := by
  exact div_mul_cancel₀ xDerivativeOfParameter
    (actualCriticalSourceEvaluation_ne_zero hinner)

theorem actualCriticalJuliaCoefficient_mul_xDerivative :
    actualCriticalJuliaCoefficient * xDerivativeOfParameter =
      explicitRationalDifferential := by
  exact div_mul_cancel₀ explicitRationalDifferential
    xDerivativeOfParameter_ne_zero

theorem xDerivative_mul_actualCriticalSourceScalar
    (inner : ℝ[X]) :
    xDerivativeOfParameter * actualCriticalSourceScalar inner =
      explicitRationalDifferential *
        actualCriticalSourceEvaluation inner := by
  rw [actualCriticalSourceScalar]
  calc
    xDerivativeOfParameter *
          (actualCriticalJuliaCoefficient *
            actualCriticalSourceEvaluation inner) =
        (actualCriticalJuliaCoefficient * xDerivativeOfParameter) *
          actualCriticalSourceEvaluation inner := by ring
    _ = explicitRationalDifferential *
          actualCriticalSourceEvaluation inner := by
      rw [actualCriticalJuliaCoefficient_mul_xDerivative]

theorem actualCriticalSourceScalar_ne_zero
    {inner : ℝ[X]} (hinner : inner ≠ 0) :
    actualCriticalSourceScalar inner ≠ 0 := by
  exact mul_ne_zero actualCriticalJuliaCoefficient_ne_zero
    (actualCriticalSourceEvaluation_ne_zero hinner)

/-- The source and coefficient polynomials used by the coupled-Julia kernel
produce exactly the declared full-generator source scalar. -/
theorem actual_source_scalar_polynomial_binding (inner : ℝ[X]) :
    (C actualCriticalJuliaCoefficient : RF[X]) *
        ((liftRealGenerator inner).map C).eval (C xOfParameter) =
      C (actualCriticalSourceScalar inner) := by
  simp [liftRealGenerator, actualCriticalSourceScalar,
    actualCriticalSourceEvaluation, eval_map]

/-- Tangency and coefficient embedding commute with the constructed
quadratic tail. -/
theorem lift_tangent_factorization
    (generator tail : ℝ[X])
    (hfactor : generator = X ^ 2 * tail) :
    liftRealGenerator generator =
      X ^ 2 * liftRealGenerator tail := by
  rw [hfactor]
  simp [liftRealGenerator]

/-- The actual parameter-scaled hidden velocity retains the quadratic
tangency required by the critical cross-weight theorem. -/
theorem actual_stored_velocity_tangent_binding
    (generator tail : ℝ[X])
    (hfactor : generator = X ^ 2 * tail) :
    actualCriticalStoredVelocity generator =
      X ^ 2 *
        (C (actualCriticalHiddenSpeed generator) *
          liftRealGenerator tail) := by
  rw [actualCriticalStoredVelocity,
    lift_tangent_factorization generator tail hfactor]
  ring

theorem tangent_tail_ne_zero
    {generator tail : ℝ[X]} (hgenerator : generator ≠ 0)
    (hfactor : generator = X ^ 2 * tail) :
    tail ≠ 0 := by
  intro htail
  apply hgenerator
  rw [hfactor, htail]
  simp

/-- Actual constant-field tangent generators satisfy every algebraic input of
the complete-gcd critical eliminant theorem. -/
theorem exists_actual_critical_gcd_saturated_visible_eliminant
    (inner outer : ℝ[X])
    (hinner : inner ≠ 0) (houter : outer ≠ 0)
    (hinnerConstant : inner.coeff 0 = 0)
    (hinnerLinear : inner.coeff 1 = 0)
    (houterConstant : outer.coeff 0 = 0)
    (houterLinear : outer.coeff 1 = 0) :
    ∃ innerTail outerTail : ℝ[X],
      inner = X ^ 2 * innerTail ∧
      outer = X ^ 2 * outerTail ∧
      innerTail ≠ 0 ∧ outerTail ≠ 0 ∧
      polynomialCoefficientDerivation (ratFuncDerivation (K := ℝ))
          (liftRealGenerator inner) = 0 ∧
      polynomialCoefficientDerivation (ratFuncDerivation (K := ℝ))
          (liftRealGenerator outer) = 0 ∧
      actualCriticalHiddenSpeed inner ≠ 0 ∧
      actualCriticalJuliaCoefficient ≠ 0 ∧
      actualCriticalSourceScalar inner ≠ 0 ∧
      ∃ eliminant : RF[X], eliminant ≠ 0 ∧
        C eliminant ∈ derivativePrefixIdeal
          (storedBivariateDerivation
            (ratFuncDerivation (K := ℝ))
            (actualCriticalStoredVelocity inner)
            explicitRationalDifferential)
          (normalizedCoupledRelation
            (criticalInnerQuotient
              (liftRealGenerator inner) (liftRealGenerator outer))
            (criticalOuterQuotient
              (liftRealGenerator inner) (liftRealGenerator outer))
            (liftRealGenerator outerTail)
            (actualCriticalSourceScalar inner))
          (normalizedCoupledRelation
            (criticalInnerQuotient
              (liftRealGenerator inner) (liftRealGenerator outer))
            (criticalOuterQuotient
              (liftRealGenerator inner) (liftRealGenerator outer))
            (liftRealGenerator outerTail)
            (actualCriticalSourceScalar inner)).natDegree := by
  obtain ⟨innerTail, hinnerFactor⟩ :=
    exists_tangentGenerator_tail inner hinnerConstant hinnerLinear
  obtain ⟨outerTail, houterFactor⟩ :=
    exists_tangentGenerator_tail outer houterConstant houterLinear
  have hinnerTail := tangent_tail_ne_zero hinner hinnerFactor
  have houterTail := tangent_tail_ne_zero houter houterFactor
  have hinnerLift := lift_tangent_factorization
    inner innerTail hinnerFactor
  have houterLift := lift_tangent_factorization
    outer outerTail houterFactor
  have hstoredVelocity := actual_stored_velocity_tangent_binding
    inner innerTail hinnerFactor
  have hspeed := actualCriticalHiddenSpeed_ne_zero hinner
  have hcoefficient := actualCriticalJuliaCoefficient_ne_zero
  have hsource := actualCriticalSourceScalar_ne_zero hinner
  have heliminant :=
    exists_critical_scaled_gcd_saturated_visible_eliminant
      (liftRealGenerator innerTail)
      (liftRealGenerator outer)
      (liftRealGenerator outerTail)
      (actualCriticalHiddenSpeed inner)
      (actualCriticalSourceScalar inner)
      (liftRealGenerator_ne_zero houter)
      (liftRealGenerator_ne_zero houterTail)
      hsource
  rw [← hstoredVelocity, ← hinnerLift] at heliminant
  exact ⟨innerTail, outerTail, hinnerFactor, houterFactor,
    hinnerTail, houterTail,
    polynomialCoefficientDerivation_liftRealGenerator_eq_zero inner,
    polynomialCoefficientDerivation_liftRealGenerator_eq_zero outer,
    hspeed, hcoefficient, hsource, heliminant⟩

/-- Aggregated actual-generator coefficient-origin and eliminant certificate.
-/
theorem critical_actual_generator_eliminant_terminal_certificate :
    ∀ (inner outer : ℝ[X]),
      inner ≠ 0 → outer ≠ 0 →
      inner.coeff 0 = 0 → inner.coeff 1 = 0 →
      outer.coeff 0 = 0 → outer.coeff 1 = 0 →
      ∃ innerTail outerTail : ℝ[X],
        inner = X ^ 2 * innerTail ∧
        outer = X ^ 2 * outerTail ∧
        innerTail ≠ 0 ∧ outerTail ≠ 0 ∧
        actualCriticalHiddenSpeed inner ≠ 0 ∧
        actualCriticalJuliaCoefficient ≠ 0 ∧
        actualCriticalSourceScalar inner ≠ 0 ∧
        ∃ eliminant : RF[X], eliminant ≠ 0 ∧
          C eliminant ∈ derivativePrefixIdeal
            (storedBivariateDerivation
              (ratFuncDerivation (K := ℝ))
              (actualCriticalStoredVelocity inner)
              explicitRationalDifferential)
            (normalizedCoupledRelation
              (criticalInnerQuotient
                (liftRealGenerator inner) (liftRealGenerator outer))
              (criticalOuterQuotient
                (liftRealGenerator inner) (liftRealGenerator outer))
              (liftRealGenerator outerTail)
              (actualCriticalSourceScalar inner))
            (normalizedCoupledRelation
              (criticalInnerQuotient
                (liftRealGenerator inner) (liftRealGenerator outer))
              (criticalOuterQuotient
                (liftRealGenerator inner) (liftRealGenerator outer))
              (liftRealGenerator outerTail)
              (actualCriticalSourceScalar inner)).natDegree := by
  intro inner outer hinner houter hinnerConstant hinnerLinear
    houterConstant houterLinear
  obtain ⟨innerTail, outerTail, hinnerFactor, houterFactor,
      hinnerTail, houterTail, _hinnerCoefficients, _houterCoefficients,
      hspeed, hcoefficient, hsource, heliminant⟩ :=
    exists_actual_critical_gcd_saturated_visible_eliminant
      inner outer hinner houter hinnerConstant hinnerLinear
      houterConstant houterLinear
  exact ⟨innerTail, outerTail, hinnerFactor, houterFactor,
    hinnerTail, houterTail, hspeed, hcoefficient, hsource, heliminant⟩

end FormalCriticalActualGeneratorEliminant
