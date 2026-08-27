import Mathlib.Tactic
import ZtareProofs.FormalCriticalActualGeneratorEliminant
import ZtareProofs.FormalCriticalDifferentialGermEliminantExclusion

/-!
# Parameterized critical two-Julia confinement

The raw Julia rows retain the derivative of the rational source
parameterization.  They therefore construct the parameter-scaled hidden ODE
and the corrected normalized coupled relation.  On every branch where the
complete generator gcd does not vanish, the corrected finite eliminant and
algebraic-eigenvector endgame give a contradiction.

The exact output is confinement of the hidden endpoint to the common-
equilibrium locus.  Excluding that remaining locus belongs to autonomous-flow
invertibility or equilibrium-trajectory uniqueness.
-/

namespace FormalCriticalParameterizedTwoJuliaConfinement

open Polynomial
open FormalCoupledJuliaAllOrderSpecialization
open FormalCriticalActualGeneratorEliminant
open FormalCriticalConnectionRationalization
open FormalCriticalDifferentialGermEliminantExclusion
open FormalCriticalGcdSaturatedFiniteDerivativeEliminant
open FormalDifferentialGermEvaluation

noncomputable section

abbrev CriticalRF := RatFunc ℝ

variable {E : Type*} [Field E] [Algebra CriticalRF E]

/-- A nonzero base-field scalar remains nonzero in every field extension. -/
theorem critical_algebraMap_ne_zero
    {scalar : CriticalRF} (hscalar : scalar ≠ 0) :
    algebraMap CriticalRF E scalar ≠ 0 := by
  intro hmapped
  apply hscalar
  apply FaithfulSMul.algebraMap_injective CriticalRF E
  simpa using hmapped

/-- The parameterized inner Julia row constructs the exact stored hidden ODE
used by the corrected finite eliminant. -/
theorem hidden_scaled_ode_of_parameterized_inner_julia
    (inner : ℝ[X]) (hinner : inner ≠ 0)
    (dE : Derivation ℤ E E) (hidden : E)
    (hinnerJulia :
      algebraMap CriticalRF E xDerivativeOfParameter *
          (liftRealGenerator inner).eval₂
            (algebraMap CriticalRF E) hidden =
        dE hidden *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner)) :
    dE hidden =
      (actualCriticalStoredVelocity inner).eval₂
        (algebraMap CriticalRF E) hidden := by
  have hsource :
      algebraMap CriticalRF E
          (actualCriticalSourceEvaluation inner) ≠ 0 :=
    critical_algebraMap_ne_zero
      (actualCriticalSourceEvaluation_ne_zero hinner)
  have hspeedBinding :
      algebraMap CriticalRF E (actualCriticalHiddenSpeed inner) *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner) =
        algebraMap CriticalRF E xDerivativeOfParameter := by
    simpa only [map_mul] using congrArg (algebraMap CriticalRF E)
      (actualCriticalHiddenSpeed_mul_sourceEvaluation hinner)
  have hscaled :
      dE hidden =
        algebraMap CriticalRF E (actualCriticalHiddenSpeed inner) *
          (liftRealGenerator inner).eval₂
            (algebraMap CriticalRF E) hidden := by
    apply mul_right_cancel₀ hsource
    calc
      dE hidden *
            algebraMap CriticalRF E
              (actualCriticalSourceEvaluation inner) =
          algebraMap CriticalRF E xDerivativeOfParameter *
            (liftRealGenerator inner).eval₂
              (algebraMap CriticalRF E) hidden := hinnerJulia.symm
      _ = (algebraMap CriticalRF E
              (actualCriticalHiddenSpeed inner) *
            (liftRealGenerator inner).eval₂
              (algebraMap CriticalRF E) hidden) *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner) := by
        rw [← hspeedBinding]
        ring
  simpa [actualCriticalStoredVelocity] using hscaled

/-- The two parameterized Julia rows and the critical visible logarithmic ODE
evaluate the corrected unsaturated actual relation to zero. -/
theorem nestedEval_corrected_actualCoupledRelation_eq_zero
    (inner outer : ℝ[X])
    (dE : Derivation ℤ E E) (visible hidden : E)
    (hvisible :
      dE visible =
        algebraMap CriticalRF E explicitRationalDifferential * visible)
    (hinnerJulia :
      algebraMap CriticalRF E xDerivativeOfParameter *
          (liftRealGenerator inner).eval₂
            (algebraMap CriticalRF E) hidden =
        dE hidden *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner))
    (houterJulia :
      (liftRealGenerator outer).eval₂
          (algebraMap CriticalRF E) visible * dE hidden =
        dE visible *
          (liftRealGenerator outer).eval₂
            (algebraMap CriticalRF E) hidden) :
    nestedEvalRingHom (algebraMap CriticalRF E) visible hidden
        (actualCoupledRelation
          (liftRealGenerator inner) (liftRealGenerator outer)
          (actualCriticalSourceScalar inner)) = 0 := by
  rw [actualCoupledRelation]
  simp only [map_sub, map_mul]
  simp [nestedEvalRingHom,
    FormalDifferentialGermEvaluation.eval₂_map_C]
  have hsourceBinding :
      algebraMap CriticalRF E xDerivativeOfParameter *
          algebraMap CriticalRF E (actualCriticalSourceScalar inner) =
        algebraMap CriticalRF E explicitRationalDifferential *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner) := by
    simpa only [map_mul] using congrArg (algebraMap CriticalRF E)
      (xDerivative_mul_actualCriticalSourceScalar inner)
  have hxdot :
      algebraMap CriticalRF E xDerivativeOfParameter ≠ 0 :=
    critical_algebraMap_ne_zero xDerivativeOfParameter_ne_zero
  apply (mul_eq_zero.mp ?_).resolve_left hxdot
  calc
    algebraMap CriticalRF E xDerivativeOfParameter *
          ((liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) visible *
            (liftRealGenerator inner).eval₂
              (algebraMap CriticalRF E) hidden -
            visible *
              algebraMap CriticalRF E
                (actualCriticalSourceScalar inner) *
              (liftRealGenerator outer).eval₂
                (algebraMap CriticalRF E) hidden) =
        (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) visible *
            (algebraMap CriticalRF E xDerivativeOfParameter *
              (liftRealGenerator inner).eval₂
                (algebraMap CriticalRF E) hidden) -
          visible *
            (algebraMap CriticalRF E xDerivativeOfParameter *
              algebraMap CriticalRF E
                (actualCriticalSourceScalar inner)) *
            (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) hidden := by ring
    _ = (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) visible *
            (dE hidden *
              algebraMap CriticalRF E
                (actualCriticalSourceEvaluation inner)) -
          visible *
            (algebraMap CriticalRF E explicitRationalDifferential *
              algebraMap CriticalRF E
                (actualCriticalSourceEvaluation inner)) *
            (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) hidden := by
      rw [hinnerJulia, hsourceBinding]
    _ = ((liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) visible * dE hidden) *
            algebraMap CriticalRF E
              (actualCriticalSourceEvaluation inner) -
          visible *
            (algebraMap CriticalRF E explicitRationalDifferential *
              algebraMap CriticalRF E
                (actualCriticalSourceEvaluation inner)) *
            (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) hidden := by ring
    _ = (dE visible *
              (liftRealGenerator outer).eval₂
                (algebraMap CriticalRF E) hidden) *
            algebraMap CriticalRF E
              (actualCriticalSourceEvaluation inner) -
          visible *
            (algebraMap CriticalRF E explicitRationalDifferential *
              algebraMap CriticalRF E
                (actualCriticalSourceEvaluation inner)) *
            (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) hidden := by rw [houterJulia]
    _ = 0 := by rw [hvisible]; ring

/-- Vanishing of the evaluated complete gcd forces both original relation
generators to vanish at the same hidden endpoint. -/
theorem generator_evaluations_eq_zero_of_gcd_eval_eq_zero
    (velocity relationOuter : CriticalRF[X])
    (hrelationOuter : relationOuter ≠ 0) (hidden : E)
    (hgcd :
      (criticalGeneratorGcd velocity relationOuter).eval₂
          (algebraMap CriticalRF E) hidden = 0) :
    velocity.eval₂ (algebraMap CriticalRF E) hidden = 0 ∧
      relationOuter.eval₂ (algebraMap CriticalRF E) hidden = 0 := by
  have hinnerFactorization :=
    criticalInner_factorization velocity relationOuter hrelationOuter
  have houterFactorization :=
    criticalOuter_factorization velocity relationOuter hrelationOuter
  constructor
  · have hevaluated := congrArg
      (fun polynomial : CriticalRF[X] ↦
        polynomial.eval₂ (algebraMap CriticalRF E) hidden)
      hinnerFactorization
    simpa only [eval₂_mul, hgcd, zero_mul] using hevaluated.symm
  · have hevaluated := congrArg
      (fun polynomial : CriticalRF[X] ↦
        polynomial.eval₂ (algebraMap CriticalRF E) hidden)
      houterFactorization
    simpa only [eval₂_mul, hgcd, zero_mul] using hevaluated.symm

/-- Every compatible nonzero parameterized critical two-Julia germ lies on
the complete common-equilibrium locus of the two unscaled generators. -/
theorem parameterized_two_julia_force_common_equilibrium
    (inner outer : ℝ[X])
    (hinner : inner ≠ 0) (houter : outer ≠ 0)
    (hinnerConstant : inner.coeff 0 = 0)
    (hinnerLinear : inner.coeff 1 = 0)
    (houterConstant : outer.coeff 0 = 0)
    (houterLinear : outer.coeff 1 = 0)
    (dE : Derivation ℤ E E) (visible hidden : E)
    (hcoefficients : ∀ coefficient : CriticalRF,
      algebraMap CriticalRF E
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ) coefficient) =
        dE (algebraMap CriticalRF E coefficient))
    (hvisible :
      dE visible =
        algebraMap CriticalRF E explicitRationalDifferential * visible)
    (hinnerJulia :
      algebraMap CriticalRF E xDerivativeOfParameter *
          (liftRealGenerator inner).eval₂
            (algebraMap CriticalRF E) hidden =
        dE hidden *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner))
    (houterJulia :
      (liftRealGenerator outer).eval₂
          (algebraMap CriticalRF E) visible * dE hidden =
        dE visible *
          (liftRealGenerator outer).eval₂
            (algebraMap CriticalRF E) hidden)
    (hvisibleNonzero : visible ≠ 0) :
    (criticalGeneratorGcd
      (liftRealGenerator inner) (liftRealGenerator outer)).eval₂
        (algebraMap CriticalRF E) hidden = 0 := by
  obtain ⟨innerTail, outerTail, hinnerFactor, houterFactor,
      hinnerTail, houterTail, hinnerCoefficients, houterCoefficients,
      hspeed, hcoefficient, hsource, eliminant, heliminant, hmember⟩ :=
    exists_actual_critical_gcd_saturated_visible_eliminant
      inner outer hinner houter hinnerConstant hinnerLinear
      houterConstant houterLinear
  have hhidden :
      dE hidden =
        (actualCriticalStoredVelocity inner).eval₂
          (algebraMap CriticalRF E) hidden :=
    hidden_scaled_ode_of_parameterized_inner_julia
      inner hinner dE hidden hinnerJulia
  have houterLiftFactor :
      liftRealGenerator outer =
        X ^ 2 * liftRealGenerator outerTail :=
    lift_tangent_factorization outer outerTail houterFactor
  let unsaturated : CriticalRF[X][X] :=
    normalizedCoupledRelation
      (liftRealGenerator inner) (liftRealGenerator outer)
      (liftRealGenerator outerTail) (actualCriticalSourceScalar inner)
  let saturated : CriticalRF[X][X] :=
    normalizedCoupledRelation
      (criticalInnerQuotient
        (liftRealGenerator inner) (liftRealGenerator outer))
      (criticalOuterQuotient
        (liftRealGenerator inner) (liftRealGenerator outer))
      (liftRealGenerator outerTail) (actualCriticalSourceScalar inner)
  have hactual :=
    nestedEval_corrected_actualCoupledRelation_eq_zero
      inner outer dE visible hidden hvisible hinnerJulia houterJulia
  have hvisibleProduct :
      visible *
        nestedEvalRingHom (algebraMap CriticalRF E) visible hidden
          unsaturated = 0 := by
    have hfactorization :=
      actualCoupledRelation_eq_X_mul_normalized
        (liftRealGenerator inner) (liftRealGenerator outer)
        (liftRealGenerator outerTail) (actualCriticalSourceScalar inner)
        houterLiftFactor
    have hevaluated := congrArg
      (nestedEvalRingHom (algebraMap CriticalRF E) visible hidden)
      hfactorization
    rw [hactual] at hevaluated
    simpa [unsaturated, nestedEvalRingHom] using hevaluated.symm
  have hunsaturated :
      nestedEvalRingHom (algebraMap CriticalRF E) visible hidden
        unsaturated = 0 :=
    (mul_eq_zero.mp hvisibleProduct).resolve_left hvisibleNonzero
  have hgcdFactorization :=
    critical_normalized_relation_gcd_factorization
      (liftRealGenerator inner) (liftRealGenerator outer)
      (liftRealGenerator outerTail) (actualCriticalSourceScalar inner)
      (liftRealGenerator_ne_zero houter)
  have hevaluatedFactorization := congrArg
    (nestedEvalRingHom (algebraMap CriticalRF E) visible hidden)
    hgcdFactorization
  have hfactorProduct :
      (criticalGeneratorGcd
        (liftRealGenerator inner) (liftRealGenerator outer)).eval₂
          (algebraMap CriticalRF E) hidden *
        nestedEvalRingHom (algebraMap CriticalRF E) visible hidden
          saturated = 0 := by
    rw [hunsaturated] at hevaluatedFactorization
    simpa [unsaturated, saturated, nestedEvalRingHom,
      FormalDifferentialGermEvaluation.eval₂_map_C]
      using hevaluatedFactorization.symm
  by_contra hgcdNonzero
  have hsaturated :
      nestedEvalRingHom (algebraMap CriticalRF E) visible hidden
        saturated = 0 :=
    (mul_eq_zero.mp hfactorProduct).resolve_left hgcdNonzero
  exact critical_finite_prefix_differential_germ_impossible
    dE visible hidden (actualCriticalStoredVelocity inner) saturated
    saturated.natDegree eliminant hcoefficients hvisible hhidden
    hsaturated hmember heliminant hvisibleNonzero

/-- The same no-callback hypotheses force both unscaled generators to vanish
at the hidden germ. -/
theorem parameterized_two_julia_force_common_generator_zeros
    (inner outer : ℝ[X])
    (hinner : inner ≠ 0) (houter : outer ≠ 0)
    (hinnerConstant : inner.coeff 0 = 0)
    (hinnerLinear : inner.coeff 1 = 0)
    (houterConstant : outer.coeff 0 = 0)
    (houterLinear : outer.coeff 1 = 0)
    (dE : Derivation ℤ E E) (visible hidden : E)
    (hcoefficients : ∀ coefficient : CriticalRF,
      algebraMap CriticalRF E
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ) coefficient) =
        dE (algebraMap CriticalRF E coefficient))
    (hvisible :
      dE visible =
        algebraMap CriticalRF E explicitRationalDifferential * visible)
    (hinnerJulia :
      algebraMap CriticalRF E xDerivativeOfParameter *
          (liftRealGenerator inner).eval₂
            (algebraMap CriticalRF E) hidden =
        dE hidden *
          algebraMap CriticalRF E
            (actualCriticalSourceEvaluation inner))
    (houterJulia :
      (liftRealGenerator outer).eval₂
          (algebraMap CriticalRF E) visible * dE hidden =
        dE visible *
          (liftRealGenerator outer).eval₂
            (algebraMap CriticalRF E) hidden)
    (hvisibleNonzero : visible ≠ 0) :
    (liftRealGenerator inner).eval₂
          (algebraMap CriticalRF E) hidden = 0 ∧
      (liftRealGenerator outer).eval₂
          (algebraMap CriticalRF E) hidden = 0 := by
  have hgcd := parameterized_two_julia_force_common_equilibrium
    inner outer hinner houter hinnerConstant hinnerLinear houterConstant
    houterLinear dE visible hidden hcoefficients hvisible hinnerJulia
    houterJulia hvisibleNonzero
  exact generator_evaluations_eq_zero_of_gcd_eval_eq_zero
    (liftRealGenerator inner) (liftRealGenerator outer)
    (liftRealGenerator_ne_zero houter) hidden hgcd

/-- Aggregated parameterized two-Julia confinement certificate. -/
theorem critical_parameterized_two_julia_confinement_terminal_certificate :
    ∀ (inner outer : ℝ[X]),
      inner ≠ 0 → outer ≠ 0 →
      inner.coeff 0 = 0 → inner.coeff 1 = 0 →
      outer.coeff 0 = 0 → outer.coeff 1 = 0 →
      ∀ (dE : Derivation ℤ E E) (visible hidden : E),
        (∀ coefficient : CriticalRF,
          algebraMap CriticalRF E
              (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
                (K := ℝ) coefficient) =
            dE (algebraMap CriticalRF E coefficient)) →
        dE visible =
          algebraMap CriticalRF E explicitRationalDifferential * visible →
        algebraMap CriticalRF E xDerivativeOfParameter *
            (liftRealGenerator inner).eval₂
              (algebraMap CriticalRF E) hidden =
          dE hidden *
            algebraMap CriticalRF E
              (actualCriticalSourceEvaluation inner) →
        (liftRealGenerator outer).eval₂
            (algebraMap CriticalRF E) visible * dE hidden =
          dE visible *
            (liftRealGenerator outer).eval₂
              (algebraMap CriticalRF E) hidden →
        visible ≠ 0 →
        (criticalGeneratorGcd
          (liftRealGenerator inner) (liftRealGenerator outer)).eval₂
            (algebraMap CriticalRF E) hidden = 0 := by
  intro inner outer hinner houter hinnerConstant hinnerLinear
    houterConstant houterLinear dE visible hidden hcoefficients hvisible
    hinnerJulia houterJulia hvisibleNonzero
  exact parameterized_two_julia_force_common_equilibrium
    inner outer hinner houter hinnerConstant hinnerLinear houterConstant
    houterLinear dE visible hidden hcoefficients hvisible hinnerJulia
    houterJulia hvisibleNonzero

end

end FormalCriticalParameterizedTwoJuliaConfinement
