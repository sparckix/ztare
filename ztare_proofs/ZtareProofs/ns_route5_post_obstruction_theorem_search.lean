import Mathlib.Tactic
import ZtareProofs.ns_route5_remaining_survivors
import ZtareProofs.ns_route5_killer_theorem_search

namespace ZtareProofs

/-!
`ns_route5_post_obstruction_theorem_search` packages the smaller route-5
theorem surface that remains after the exponential obstruction target is paid.

At that stage, route 5 is no longer a three-branch theorem search. It is only:

1. periodic reset debt control,
2. microlocal leak integrability.
-/

/-- Exact post-obstruction theorem-search surface for the remaining route-5
branches. -/
def route5PostObstructionTheoremSearchFrontier
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real) : Prop :=
  route5RemainingSurvivorSurface
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget ∧
    (periodicResetDebtControlTheoremCandidate
        jumpAlignment resetResidual debtBudget ∨
      microlocalLeakIntegrabilityTheoremCandidate
        localGain tailLeak globalBudget)

/-- If the exponential obstruction is paid and the post-obstruction theorem
surface is active, route 5 is searching only over the periodic/microlocal
fork. -/
theorem route5_post_obstruction_search_is_two_branch
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real}
    (h :
      route5PostObstructionTheoremSearchFrontier
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget) :
    periodicResetDebtControlTheoremCandidate
        jumpAlignment resetResidual debtBudget ∨
      microlocalLeakIntegrabilityTheoremCandidate
        localGain tailLeak globalBudget := by
  exact h.2

end ZtareProofs
