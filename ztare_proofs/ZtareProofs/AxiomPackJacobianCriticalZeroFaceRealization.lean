import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalHolonomyTwoFlowExclusion

/-!
# Critical zero-face realization from coordinate Julia rows

The filtered/Rees adapter exposes each finite critical logarithm through its
polynomial generator, normalized endpoint, and coordinate Julia equation.
This file upgrades those coordinate equations to the complete autonomous
time-one objects used by the all-degree critical-holonomy exclusion.

It does not infer that every strict-subthreshold zero-face schedule supplies
the two Julia rows or endpoint composition.  Those three equations remain
the exact substrate-specialization obligation.
-/

namespace AxiomPackJacobianCriticalZeroFaceRealization

open Polynomial PowerSeries

open AxiomPackJacobianCriticalBaseLaurentCoordinate
open AxiomPackJacobianCriticalBaseTwoFlowExclusion
open AxiomPackJacobianCriticalHolonomyTwoFlowExclusion
open FormalAutonomousFlow

noncomputable section

abbrev PS := PowerSeries ℂ

/-- Coordinate-level output required from a zero-positive-face Rees
specialization.  This object carries neither all-germ commutation nor an
autonomous flow witness. -/
structure CriticalZeroFaceTwoJuliaRealization where
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
  inner_endpoint_constant : constantCoeff innerEndpoint = 0
  inner_endpoint_linear : coeff 1 innerEndpoint = 1
  outer_endpoint_constant : constantCoeff outerEndpoint = 0
  outer_endpoint_linear : coeff 1 outerEndpoint = 1
  inner_julia :
    ((baseComplexifyPolynomial inner : ℂ[X]) : PS).subst innerEndpoint =
      d⁄dX ℂ innerEndpoint *
        ((baseComplexifyPolynomial inner : ℂ[X]) : PS)
  outer_julia :
    ((baseComplexifyPolynomial outer : ℂ[X]) : PS).subst outerEndpoint =
      d⁄dX ℂ outerEndpoint *
        ((baseComplexifyPolynomial outer : ℂ[X]) : PS)
  endpointFactorization :
    PowerSeries.subst innerEndpoint outerEndpoint = baseCriticalHolonomy

/-- Coordinate Julia upgrades both specialized endpoints to the exact v94
factorization category. -/
def CriticalZeroFaceTwoJuliaRealization.toHolonomyFactorization
    (realization : CriticalZeroFaceTwoJuliaRealization) :
    CriticalHolonomyTwoFlowFactorization where
  inner := realization.inner
  outer := realization.outer
  inner_ne_zero := realization.inner_ne_zero
  outer_ne_zero := realization.outer_ne_zero
  inner_constant := realization.inner_constant
  inner_linear := realization.inner_linear
  outer_constant := realization.outer_constant
  outer_linear := realization.outer_linear
  innerEndpoint := realization.innerEndpoint
  outerEndpoint := realization.outerEndpoint
  innerFlow := AutonomousSubstitutionTimeOne.of_julia _ _
    realization.inner_endpoint_constant realization.inner_endpoint_linear
    realization.inner_julia
  outerFlow := AutonomousSubstitutionTimeOne.of_julia _ _
    realization.outer_endpoint_constant realization.outer_endpoint_linear
    realization.outer_julia
  endpointFactorization := realization.endpointFactorization

/-- Every exact coordinate-Julia zero-face realization is impossible. -/
theorem critical_zero_face_two_julia_realization_impossible
    (realization : CriticalZeroFaceTwoJuliaRealization) : False :=
  critical_holonomy_two_flow_factorization_impossible
    realization.toHolonomyFactorization

/-- Aggregated all-degree certificate for the narrowed realization category. -/
theorem critical_zero_face_two_julia_realization_terminal_certificate :
    ¬ Nonempty CriticalZeroFaceTwoJuliaRealization := by
  rintro ⟨realization⟩
  exact critical_zero_face_two_julia_realization_impossible realization

end

end AxiomPackJacobianCriticalZeroFaceRealization
