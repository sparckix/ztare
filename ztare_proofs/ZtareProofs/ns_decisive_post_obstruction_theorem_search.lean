import Mathlib.Tactic
import ZtareProofs.ns_route1_killer_theorem_search
import ZtareProofs.ns_route5_post_obstruction_theorem_search

namespace ZtareProofs

/-!
`ns_decisive_post_obstruction_theorem_search` is the smaller decisive NS fork
obtained after admitting the clean exponential route-5 obstruction.

At this stage, the live theorem search is:

1. route 1 pays its killer-theorem surface, or
2. route 5 pays one of the two remaining post-obstruction branches:
   periodic reset or microlocal leak.
-/

/-- Exact post-obstruction decisive fork. -/
def decisivePostObstructionNSTheoremSearchFrontier
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real) : Prop :=
  route1KillerTheoremSearchFrontier
      transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε ∨
    route5PostObstructionTheoremSearchFrontier
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget

theorem decisive_post_obstruction_frontier_projects
    {transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real}
    (h :
      decisivePostObstructionNSTheoremSearchFrontier
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget) :
    route1KillerTheoremSearchFrontier
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε ∨
      route5PostObstructionTheoremSearchFrontier
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget := by
  exact h

end ZtareProofs
