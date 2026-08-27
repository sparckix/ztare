import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalBaseTwoFlowExclusion

/-!
# Intrinsic critical-holonomy two-flow exclusion

The regular normalization source is an invertible formal coordinate.  The
intrinsic critical holonomy is therefore the visible base germ conjugated
back through the formal substitution inverse.  This file proves that any
factorization of that intrinsic holonomy by two normalized autonomous
polynomial time-one substitutions would give the base-germ composition
excluded by `AxiomPackJacobianCriticalBaseTwoFlowExclusion`.

No continuation, branch selection, or degree bound occurs in this bridge.
-/

namespace AxiomPackJacobianCriticalHolonomyTwoFlowExclusion

open Polynomial PowerSeries

open AxiomPackJacobianCriticalBaseLaurentCoordinate
open AxiomPackJacobianCriticalBaseTwoFlowExclusion
open FormalAutonomousFlow

noncomputable section

abbrev PS := PowerSeries ℂ

/-- The critical holonomy in its intrinsic source coordinate. -/
def baseCriticalHolonomy : PS :=
  PowerSeries.subst baseSource.substInv baseVisible

/-- Conjugating the intrinsic holonomy through the normalization source
recovers the exact visible base germ. -/
theorem baseCriticalHolonomy_subst_source :
    PowerSeries.subst baseSource baseCriticalHolonomy = baseVisible := by
  have hsource : HasSubst baseSource :=
    HasSubst.of_constantCoeff_zero' baseSource_constantCoeff
  have hinverse : HasSubst baseSource.substInv :=
    PowerSeries.hasSubst_substInv baseSource
  unfold baseCriticalHolonomy
  rw [PowerSeries.subst_comp_subst_apply hinverse hsource baseVisible,
    PowerSeries.subst_substInv_left baseSource baseSource_constantCoeff,
    PowerSeries.X_subst]

/-- Content of a finite critical factorization by two normalized autonomous
polynomial time-one substitutions. -/
structure CriticalHolonomyTwoFlowFactorization where
  inner : ℝ[X]
  outer : ℝ[X]
  inner_ne_zero : inner ≠ 0
  outer_ne_zero : outer ≠ 0
  inner_constant : inner.coeff 0 = 0
  inner_linear : inner.coeff 1 = 0
  outer_constant : outer.coeff 0 = 0
  outer_linear : outer.coeff 1 = 0
  innerEndpoint : PS
  outerEndpoint : PS
  innerFlow : AutonomousSubstitutionTimeOne
    ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint
  outerFlow : AutonomousSubstitutionTimeOne
    ((baseComplexifyPolynomial outer : ℂ[X]) : PS) outerEndpoint
  endpointFactorization :
    PowerSeries.subst innerEndpoint outerEndpoint = baseCriticalHolonomy

/-- The exact critical holonomy admits no factorization object in the
declared normalized autonomous polynomial category. -/
theorem critical_holonomy_two_flow_factorization_impossible
    (factorization : CriticalHolonomyTwoFlowFactorization) : False := by
  apply critical_base_two_flow_impossible
    factorization.inner factorization.outer
    factorization.inner_ne_zero factorization.outer_ne_zero
    factorization.inner_constant factorization.inner_linear
    factorization.outer_constant factorization.outer_linear
    factorization.innerEndpoint factorization.outerEndpoint
    factorization.innerFlow factorization.outerFlow
  rw [factorization.endpointFactorization]
  exact baseCriticalHolonomy_subst_source

/-- Aggregated all-degree terminal certificate in the intrinsic holonomy
category. -/
theorem critical_holonomy_two_flow_exclusion_terminal_certificate :
    ¬ Nonempty CriticalHolonomyTwoFlowFactorization := by
  rintro ⟨factorization⟩
  exact critical_holonomy_two_flow_factorization_impossible factorization

/-- A critical factorization with the additional zero-generator law owned by
an actual exponential: a zero generator has the identity endpoint.  Unlike
the broader commutant category above, this object permits either critical
generator to vanish. -/
structure CriticalHolonomyTwoFlowExponentialFactorization where
  inner : ℝ[X]
  outer : ℝ[X]
  inner_constant : inner.coeff 0 = 0
  inner_linear : inner.coeff 1 = 0
  outer_constant : outer.coeff 0 = 0
  outer_linear : outer.coeff 1 = 0
  innerEndpoint : PS
  outerEndpoint : PS
  innerFlow : AutonomousSubstitutionTimeOne
    ((baseComplexifyPolynomial inner : ℂ[X]) : PS) innerEndpoint
  outerFlow : AutonomousSubstitutionTimeOne
    ((baseComplexifyPolynomial outer : ℂ[X]) : PS) outerEndpoint
  inner_zero_endpoint : inner = 0 → innerEndpoint = PowerSeries.X
  outer_zero_endpoint : outer = 0 → outerEndpoint = PowerSeries.X
  endpointFactorization :
    PowerSeries.subst innerEndpoint outerEndpoint = baseCriticalHolonomy

/-- Replace a zero critical generator by a fixed nonzero tangent generator.
The replacement is used only with an endpoint already proved to be `X`. -/
def padZeroGenerator (generator : ℝ[X]) : ℝ[X] :=
  if generator = 0 then Polynomial.X ^ 2 else generator

theorem padZeroGenerator_ne_zero (generator : ℝ[X]) :
    padZeroGenerator generator ≠ 0 := by
  by_cases hgenerator : generator = 0
  · simp [padZeroGenerator, hgenerator, Polynomial.X_ne_zero]
  · simpa [padZeroGenerator, hgenerator]

theorem padZeroGenerator_coeff_zero
    (generator : ℝ[X]) (hconstant : generator.coeff 0 = 0) :
    (padZeroGenerator generator).coeff 0 = 0 := by
  by_cases hgenerator : generator = 0
  · simp [padZeroGenerator, hgenerator]
  · simpa [padZeroGenerator, hgenerator] using hconstant

theorem padZeroGenerator_coeff_one
    (generator : ℝ[X]) (hlinear : generator.coeff 1 = 0) :
    (padZeroGenerator generator).coeff 1 = 0 := by
  by_cases hgenerator : generator = 0
  · simp [padZeroGenerator, hgenerator]
  · simpa [padZeroGenerator, hgenerator] using hlinear

/-- Identity padding preserves the normalized autonomous-substitution
record.  In the zero case the explicit exponential zero law supplies the
identity endpoint; in the nonzero case the original record is retained. -/
def paddedFlow
    (generator : ℝ[X]) (endpoint : PS)
    (flow : AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial generator : ℂ[X]) : PS) endpoint)
    (zeroEndpoint : generator = 0 → endpoint = PowerSeries.X) :
    AutonomousSubstitutionTimeOne
      ((baseComplexifyPolynomial (padZeroGenerator generator) : ℂ[X]) : PS)
      endpoint := by
  by_cases hgenerator : generator = 0
  · rw [zeroEndpoint hgenerator]
    exact AutonomousSubstitutionTimeOne.identity _
  · simpa [padZeroGenerator, hgenerator] using flow

/-- Identity padding embeds the zero-aware exponential category in the
already excluded nonzero commutant category without changing either
endpoint. -/
def CriticalHolonomyTwoFlowExponentialFactorization.toPaddedFactorization
    (factorization : CriticalHolonomyTwoFlowExponentialFactorization) :
    CriticalHolonomyTwoFlowFactorization where
  inner := padZeroGenerator factorization.inner
  outer := padZeroGenerator factorization.outer
  inner_ne_zero := padZeroGenerator_ne_zero factorization.inner
  outer_ne_zero := padZeroGenerator_ne_zero factorization.outer
  inner_constant := padZeroGenerator_coeff_zero factorization.inner
    factorization.inner_constant
  inner_linear := padZeroGenerator_coeff_one factorization.inner
    factorization.inner_linear
  outer_constant := padZeroGenerator_coeff_zero factorization.outer
    factorization.outer_constant
  outer_linear := padZeroGenerator_coeff_one factorization.outer
    factorization.outer_linear
  innerEndpoint := factorization.innerEndpoint
  outerEndpoint := factorization.outerEndpoint
  innerFlow := paddedFlow factorization.inner factorization.innerEndpoint
    factorization.innerFlow factorization.inner_zero_endpoint
  outerFlow := paddedFlow factorization.outer factorization.outerEndpoint
    factorization.outerFlow factorization.outer_zero_endpoint
  endpointFactorization := factorization.endpointFactorization

/-- The exact critical holonomy also excludes the zero-aware exponential
two-flow category. -/
theorem critical_holonomy_two_flow_exponential_factorization_impossible
    (factorization : CriticalHolonomyTwoFlowExponentialFactorization) :
    False :=
  critical_holonomy_two_flow_factorization_impossible
    factorization.toPaddedFactorization

/-- Aggregated all-degree certificate for the zero-aware category. -/
theorem critical_holonomy_two_flow_exponential_exclusion_terminal_certificate :
    ¬ Nonempty CriticalHolonomyTwoFlowExponentialFactorization := by
  rintro ⟨factorization⟩
  exact critical_holonomy_two_flow_exponential_factorization_impossible
    factorization

end

end AxiomPackJacobianCriticalHolonomyTwoFlowExclusion
