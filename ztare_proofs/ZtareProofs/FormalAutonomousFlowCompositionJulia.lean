import Mathlib.Tactic
import ZtareProofs.FormalAutonomousFlow

/-!
# Parameterized Julia rows from normalized autonomous substitutions

Julia's coordinate identity is transported through an arbitrary
zero-constant source germ.  The chain rule then gives the division-free
parameterized row used by differential-germ elimination.  Applying the same
theorem first to the inner flow and then to the outer flow constructs both
rows of a two-flow composition.
-/

namespace FormalAutonomousFlowCompositionJulia

open PowerSeries
open FormalAutonomousFlow

variable {k : Type*} [Field k]

/-- Reparameterizing a normalized autonomous flow by any fixed-origin germ
constructs its division-free Julia row. -/
theorem parameterized_julia
    (generator endpoint source : k⟦X⟧)
    (flow : AutonomousSubstitutionTimeOne generator endpoint)
    (hsource : HasSubst source) :
    d⁄dX k source * generator.subst (endpoint.subst source) =
      d⁄dX k (endpoint.subst source) * generator.subst source := by
  have hjulia :
      PowerSeries.subst source (PowerSeries.subst endpoint generator) =
        PowerSeries.subst source (d⁄dX k endpoint * generator) :=
    congrArg (fun germ : k⟦X⟧ ↦ PowerSeries.subst source germ)
      (julia_identity generator endpoint flow)
  rw [PowerSeries.subst_comp_subst_apply flow.hasSubst hsource,
    PowerSeries.subst_mul hsource] at hjulia
  have hchain := PowerSeries.derivative_subst k hsource
    (f := endpoint)
  rw [hjulia, hchain]
  ring

/-- Substitution composition identifies the visible two-flow endpoint after
source reparameterization. -/
theorem composition_subst
    (innerEndpoint outerEndpoint source : k⟦X⟧)
    (hinner : HasSubst innerEndpoint)
    (hsource : HasSubst source) :
    PowerSeries.subst source
        (PowerSeries.subst innerEndpoint outerEndpoint) =
      PowerSeries.subst (PowerSeries.subst source innerEndpoint)
        outerEndpoint := by
  simpa only using
    (PowerSeries.subst_comp_subst_apply hinner hsource outerEndpoint)

/-- Both parameterized Julia rows of a normalized two-flow composition are
conclusions of the two flow objects and a fixed-origin source germ. -/
theorem two_flow_parameterized_julia
    (innerGenerator outerGenerator innerEndpoint outerEndpoint source :
      k⟦X⟧)
    (innerFlow :
      AutonomousSubstitutionTimeOne innerGenerator innerEndpoint)
    (outerFlow :
      AutonomousSubstitutionTimeOne outerGenerator outerEndpoint)
    (hsourceConstant : constantCoeff source = 0) :
    let hidden := PowerSeries.subst source innerEndpoint
    let visible := PowerSeries.subst hidden outerEndpoint
    d⁄dX k source * innerGenerator.subst hidden =
        d⁄dX k hidden * innerGenerator.subst source ∧
      outerGenerator.subst visible * d⁄dX k hidden =
        d⁄dX k visible * outerGenerator.subst hidden := by
  dsimp only
  have hsource : HasSubst source :=
    HasSubst.of_constantCoeff_zero' hsourceConstant
  have hhiddenConstant :
      constantCoeff (PowerSeries.subst source innerEndpoint) = 0 := by
    exact PowerSeries.constantCoeff_subst_eq_zero hsourceConstant
      innerEndpoint innerFlow.endpoint_constantCoeff
  have hhidden : HasSubst (PowerSeries.subst source innerEndpoint) :=
    HasSubst.of_constantCoeff_zero' hhiddenConstant
  exact ⟨parameterized_julia innerGenerator innerEndpoint source
      innerFlow hsource,
    by
      have houter := parameterized_julia outerGenerator outerEndpoint
        (innerEndpoint.subst source) outerFlow hhidden
      simpa only [mul_comm] using houter⟩

end FormalAutonomousFlowCompositionJulia
