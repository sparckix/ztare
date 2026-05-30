import Mathlib.Tactic
import ZtareProofs.ns_route5_periodic_metric_reset
import ZtareProofs.ns_route5_microlocal_global_leak
import ZtareProofs.ns_route5_exponential_metric_curvature_capacity

namespace ZtareProofs

/-!
`ns_route5_postrun_survivor_surface` is the compressed read of the finished
survivor-theorem run.

The run did not leave a vague geometry branch. It left three exact unpaid
theorem burdens:

1. periodic/pulsed metric resets,
2. micro-local diffusion with global leak control,
3. exponential metric with curvature-capacity matching.
-/

def route5PostrunSurvivorSurface
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  periodicMetricResetSurvivorTarget
      γ t kappaMax totalStrain logResetCost resetCount globalResidual ∨
    microlocalDiffusiveAbsorptionSurvivorTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty
      globalResidual decayBudget horizon ∨
    exponentialMetricSurvivorTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget

theorem route5_postrun_surface_has_three_exact_branches
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      route5PostrunSurvivorSurface
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        decayBudget horizon
        hnorm targetCurvature realizedCapacity capacityBudget) :
    periodicMetricResetSurvivorTarget
        γ t kappaMax totalStrain logResetCost resetCount globalResidual ∨
      microlocalDiffusiveAbsorptionSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon ∨
      exponentialMetricSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

end ZtareProofs
