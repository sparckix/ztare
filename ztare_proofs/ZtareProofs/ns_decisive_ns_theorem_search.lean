import Mathlib.Tactic
import ZtareProofs.ns_route1_killer_theorem_search
import ZtareProofs.ns_route5_killer_theorem_search

namespace ZtareProofs

/-!
`ns_decisive_ns_theorem_search` is the current smallest honest theorem-search
surface for the Navier–Stokes branch.

At this point there are only two live constructive destinations:

1. route 1 pays its exact killer-theorem surface;
2. route 5 pays one of its exact killer-theorem or obstruction candidates.
-/

/-- Current exact theorem-search fork for the NS proof-facing branch. -/
def decisiveNSTheoremSearchFrontier
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  route1KillerTheoremSearchFrontier
      transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε ∨
    route5KillerTheoremSearchFrontier
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget

theorem decisive_ns_frontier_projects_to_live_search
    {transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      decisiveNSTheoremSearchFrontier
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    route1KillerTheoremSearchFrontier
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε ∨
      route5KillerTheoremSearchFrontier
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

end ZtareProofs
