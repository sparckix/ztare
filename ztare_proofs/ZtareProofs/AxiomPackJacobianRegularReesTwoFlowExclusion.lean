import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalHolonomyTwoFlowExclusion

/-!
# Regular Rees two-flow specialization for the July Jacobian family

The Rees parameter is the coefficient variable and the spatial germ is the
outer power-series variable.  Constant-term evaluation in the Rees parameter
is a surjective ring homomorphism.  The general autonomous-flow
specialization theorem therefore transports normalized flow records and the
exact group composition to the critical face.

This module starts from a regular Rees contact carrier.  Construction of that
carrier from an arbitrary strict-subthreshold contact schedule remains a
separate adapter theorem.
-/

namespace AxiomPackJacobianRegularReesTwoFlowExclusion

open Polynomial PowerSeries
open FormalAutonomousFlow
open AxiomPackJacobianCriticalBaseLaurentCoordinate
open AxiomPackJacobianCriticalBaseTwoFlowExclusion
open AxiomPackJacobianCriticalHolonomyTwoFlowExclusion

noncomputable section

/-- Formal series in the Rees parameter. -/
abbrev ReesCoefficient := PowerSeries ℂ

/-- Spatial formal germs with regular Rees-series coefficients. -/
abbrev ReesGerm := PowerSeries ReesCoefficient

/-- Evaluation at the critical Rees face. -/
def criticalResidue : ReesCoefficient →+* ℂ :=
  PowerSeries.constantCoeff

/-- Every critical coefficient has a constant Rees lift. -/
theorem criticalResidue_surjective :
    Function.Surjective criticalResidue := by
  intro coefficient
  refine ⟨PowerSeries.C coefficient, ?_⟩
  simp [criticalResidue]

/-- Coefficientwise constant lift of a critical spatial germ. -/
def constantReesLift (germ : PowerSeries ℂ) : ReesGerm :=
  PowerSeries.map (PowerSeries.C : ℂ →+* ReesCoefficient) germ

/-- Critical evaluation retracts the coefficientwise constant lift. -/
theorem criticalResidue_constantReesLift (germ : PowerSeries ℂ) :
    PowerSeries.map criticalResidue (constantReesLift germ) = germ := by
  ext index
  simp [criticalResidue, constantReesLift, PowerSeries.coeff_map]

/-- A regular Rees contact whose critical generators are finite polynomial
vector fields in the exact July normalization. -/
structure RegularReesTwoFlowContact where
  innerGenerator : ReesGerm
  outerGenerator : ReesGerm
  innerEndpoint : ReesGerm
  outerEndpoint : ReesGerm
  innerFlow : AutonomousSubstitutionTimeOne innerGenerator innerEndpoint
  outerFlow : AutonomousSubstitutionTimeOne outerGenerator outerEndpoint
  innerCritical : ℝ[X]
  outerCritical : ℝ[X]
  innerCriticalBinding :
    PowerSeries.map criticalResidue innerGenerator =
      ((baseComplexifyPolynomial innerCritical : ℂ[X]) : PowerSeries ℂ)
  outerCriticalBinding :
    PowerSeries.map criticalResidue outerGenerator =
      ((baseComplexifyPolynomial outerCritical : ℂ[X]) : PowerSeries ℂ)
  inner_constant : innerCritical.coeff 0 = 0
  inner_linear : innerCritical.coeff 1 = 0
  outer_constant : outerCritical.coeff 0 = 0
  outer_linear : outerCritical.coeff 1 = 0
  inner_zero_endpoint :
    innerCritical = 0 →
      PowerSeries.map criticalResidue innerEndpoint = PowerSeries.X
  outer_zero_endpoint :
    outerCritical = 0 →
      PowerSeries.map criticalResidue outerEndpoint = PowerSeries.X
  completeResidual : ReesGerm
  completeEndpointFactorization :
    PowerSeries.subst innerEndpoint outerEndpoint = completeResidual
  criticalResidualBinding :
    PowerSeries.map criticalResidue completeResidual =
      baseCriticalHolonomy

/-- Critical specialization constructs the exact factorization object
excluded by the local July theorem. -/
def RegularReesTwoFlowContact.toCriticalFactorization
    (contact : RegularReesTwoFlowContact) :
    CriticalHolonomyTwoFlowExponentialFactorization := by
  have innerSpecialized := contact.innerFlow.map criticalResidue
  have outerSpecialized := contact.outerFlow.map criticalResidue
  rw [contact.innerCriticalBinding] at innerSpecialized
  rw [contact.outerCriticalBinding] at outerSpecialized
  have specializedFactorization :
      PowerSeries.subst
          (PowerSeries.map criticalResidue contact.innerEndpoint)
          (PowerSeries.map criticalResidue contact.outerEndpoint) =
        baseCriticalHolonomy := by
    calc
      PowerSeries.subst
          (PowerSeries.map criticalResidue contact.innerEndpoint)
          (PowerSeries.map criticalResidue contact.outerEndpoint) =
        PowerSeries.map criticalResidue contact.completeResidual :=
        map_endpoint_composition criticalResidue
          contact.innerFlow.hasSubst contact.completeEndpointFactorization
      _ = baseCriticalHolonomy := contact.criticalResidualBinding
  exact {
    inner := contact.innerCritical
    outer := contact.outerCritical
    inner_constant := contact.inner_constant
    inner_linear := contact.inner_linear
    outer_constant := contact.outer_constant
    outer_linear := contact.outer_linear
    innerEndpoint := PowerSeries.map criticalResidue contact.innerEndpoint
    outerEndpoint := PowerSeries.map criticalResidue contact.outerEndpoint
    innerFlow := innerSpecialized
    outerFlow := outerSpecialized
    inner_zero_endpoint := contact.inner_zero_endpoint
    outer_zero_endpoint := contact.outer_zero_endpoint
    endpointFactorization := specializedFactorization
  }

/-- No regular Rees contact can realize the exact July critical holonomy by
two finite normalized polynomial flows. -/
theorem regular_rees_two_flow_contact_impossible
    (contact : RegularReesTwoFlowContact) : False :=
  critical_holonomy_two_flow_exponential_factorization_impossible
    contact.toCriticalFactorization

/-- Aggregated all-degree terminal certificate for the regular Rees
two-flow category. -/
theorem regular_rees_two_flow_exclusion_terminal_certificate :
    ¬ Nonempty RegularReesTwoFlowContact := by
  rintro ⟨contact⟩
  exact regular_rees_two_flow_contact_impossible contact

end

end AxiomPackJacobianRegularReesTwoFlowExclusion
