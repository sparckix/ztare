import Mathlib.Tactic
import ZtareProofs.ns_route5_survivor_elimination

namespace ZtareProofs

/-!
`ns_route5_remaining_survivors` records the current smallest route-5 survivor
surface after integrating the cheapest explicit obstruction now on-graph.

Once the exponential-metric obstruction target is paid, route 5 no longer has
three serious branches. It has exactly two:

1. periodic / pulsed metric reset,
2. microlocal diffusive absorption with global leak control.
-/

/-- Route-5 remaining survivor surface after paying the exponential obstruction
target. -/
def route5RemainingSurvivorSurface
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  exponentialMetricSurvivorObstructionTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget ∧
    (periodicMetricResetSurvivorTarget
        γ t kappaMax totalStrain logResetCost resetCount globalResidual ∨
      microlocalDiffusiveAbsorptionSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon)

/-- If the post-run route-5 surface is alive and the exponential obstruction is
paid, the remaining live surface is exactly the periodic-or-microlocal fork. -/
theorem route5_remaining_survivors_of_exponential_obstruction
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (hsurf :
      route5PostrunSurvivorSurface
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        decayBudget horizon
        hnorm targetCurvature realizedCapacity capacityBudget)
    (hobs :
      exponentialMetricSurvivorObstructionTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    route5RemainingSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget := by
  refine And.intro hobs ?_
  exact route5_postrun_surface_eliminates_exponential_branch hsurf hobs

/-- If both remaining survivor branches fail after the exponential obstruction
is paid, route 5 is dead on the current proof graph. -/
theorem no_route5_survivor_after_exponential_obstruction
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (hobs :
      exponentialMetricSurvivorObstructionTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget)
    (hreset :
      ¬ periodicMetricResetSurvivorTarget
        γ t kappaMax totalStrain logResetCost resetCount globalResidual)
    (hmicro :
      ¬ microlocalDiffusiveAbsorptionSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon) :
    ¬ route5RemainingSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget := by
  intro h
  rcases h.2 with hsurv | hsurv
  · exact hreset hsurv
  · exact hmicro hsurv

end ZtareProofs
