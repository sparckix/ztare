import Mathlib.Tactic
import ZtareProofs.ns_route5_postrun_survivor_surface
import ZtareProofs.ns_exponential_metric_survivor_obstruction

namespace ZtareProofs

/-!
`ns_route5_survivor_elimination` turns the cheapest route-5 obstruction target
into an actual shrinkage statement on the post-run survivor surface.

This matters because otherwise the exponential-metric obstruction remains a
detached literature-novelty candidate instead of a branch-killing theorem on
the live NS proof graph.
-/

/-- If the exponential-metric obstruction target is paid, the route-5 post-run
surface can survive only through periodic reset or microlocal leak branches. -/
theorem route5_postrun_surface_eliminates_exponential_branch
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
    periodicMetricResetSurvivorTarget
        γ t kappaMax totalStrain logResetCost resetCount globalResidual ∨
      microlocalDiffusiveAbsorptionSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon := by
  rcases hsurf with hreset | hmicro | hexp
  · exact Or.inl hreset
  · exact Or.inr hmicro
  · exfalso
    exact no_exponential_metric_survivor_of_obstructionTarget hobs hexp

/-- Equivalent branch-killer phrasing: under the obstruction target, the
exponential route-5 survivor branch is no longer admissible on the live
post-run surface. -/
theorem route5_exponential_survivor_not_admissible_on_postrun_surface
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (hobs :
      exponentialMetricSurvivorObstructionTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    ¬ (route5PostrunSurvivorSurface
          γ t kappaMax totalStrain logResetCost resetCount globalResidual
          coerciveBudget pressureBurden residual offset lambdaMin
          rawPenalty diffusiveScale smoothingOrder dilutedPenalty
          decayBudget horizon
          hnorm targetCurvature realizedCapacity capacityBudget ∧
        exponentialMetricSurvivorTarget
          γ coerciveBudget pressureBurden residual offset lambdaMin
          hnorm targetCurvature realizedCapacity capacityBudget) := by
  intro h
  exact no_exponential_metric_survivor_of_obstructionTarget hobs h.2

end ZtareProofs
