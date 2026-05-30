import Mathlib.Tactic
import ZtareProofs.ns_route5_postrun_survivor_surface

namespace ZtareProofs

/-!
`ns_route5_survivor_theorem_search` is the constructive Newton-mode search
surface after the finished survivor-theorem run.

Useful search is now no longer "find some geometric survivor." It is:

1. generate a theorem candidate for periodic / pulsed metric reset,
2. generate a theorem candidate for micro-local global leak control,
3. generate a theorem candidate for exponential-metric curvature-capacity
   matching.
-/

/-- Candidate theorem surface for periodic / pulsed metric reset. -/
def periodicMetricResetTheoremCandidate
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual : Real) : Prop :=
  periodicMetricResetSurvivorTarget
    γ t kappaMax totalStrain logResetCost resetCount globalResidual

/-- Candidate theorem surface for micro-local diffusive absorption. -/
def microlocalGlobalLeakTheoremCandidate
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty
      globalResidual decayBudget horizon : Real) : Prop :=
  microlocalDiffusiveAbsorptionSurvivorTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin
    rawPenalty diffusiveScale smoothingOrder dilutedPenalty
    globalResidual decayBudget horizon

/-- Candidate theorem surface for exponential-metric curvature capacity. -/
def exponentialMetricCapacityTheoremCandidate
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  exponentialMetricSurvivorTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin
    hnorm targetCurvature realizedCapacity capacityBudget

/-- Exact theorem-generation frontier for the post-run route-5 survivor surface. -/
def route5SurvivorTheoremGenerationFrontier
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  periodicMetricResetTheoremCandidate
      γ t kappaMax totalStrain logResetCost resetCount globalResidual ∨
    microlocalGlobalLeakTheoremCandidate
      γ coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty
      globalResidual decayBudget horizon ∨
    exponentialMetricCapacityTheoremCandidate
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget

theorem route5_survivor_frontier_is_exact_postrun_surface
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      route5SurvivorTheoremGenerationFrontier
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        decayBudget horizon
        hnorm targetCurvature realizedCapacity capacityBudget) :
    route5PostrunSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

end ZtareProofs
