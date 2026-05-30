import Mathlib.Tactic
import ZtareProofs.ns_exponential_metric_capacity_deficit
import ZtareProofs.ns_exponential_metric_survivor_obstruction
import ZtareProofs.ns_route5_survivor_elimination
import ZtareProofs.ns_route5_post_obstruction_theorem_search

namespace ZtareProofs

/-!
`ns_exponential_metric_obstruction_stack` packages the paper-grade proposition
stack for the current cheapest route-5 obstruction target.

This file is not a new branch. It is a compressed mathematical narrative:

1. the exponential metric survivor requires ellipticity;
2. it also requires curvature-capacity matching;
3. a positive capacity deficit obstructs curvature-capacity matching;
4. paying that obstruction removes the exponential branch from the post-run
   route-5 surface;
5. the remaining route-5 theorem search is then only periodic reset or
   microlocal leak.
-/

/-- Paper-grade proposition stack for the exponential route-5 obstruction. -/
def exponentialMetricObstructionStack
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real) : Prop :=
  exponentialMetricSurvivorObstructionTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget ∧
    route5PostObstructionTheoremSearchFrontier
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget

theorem exponential_metric_obstruction_stack_projects
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real}
    (h :
      exponentialMetricObstructionStack
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget) :
    exponentialMetricSurvivorObstructionTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget ∧
      (periodicResetDebtControlTheoremCandidate
          jumpAlignment resetResidual debtBudget ∨
        microlocalLeakIntegrabilityTheoremCandidate
          localGain tailLeak globalBudget) := by
  refine And.intro h.1 ?_
  exact route5_post_obstruction_search_is_two_branch h.2

/-- Nontrivial paper-grade proposition stack: the obstruction is sourced by an
explicit positive capacity deficit rather than by assuming the survivor clause
fails. -/
def exponentialMetricNontrivialObstructionStack
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget externalBurden
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real) : Prop :=
  exponentialMetricCapacityDeficitNontrivialTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget externalBurden ∧
    route5PostObstructionTheoremSearchFrontier
      γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget

theorem nontrivial_exponential_metric_obstruction_stack_projects
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget externalBurden
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget : Real}
    (h :
      exponentialMetricNontrivialObstructionStack
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon hnorm targetCurvature realizedCapacity capacityBudget
        externalBurden jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget) :
    exponentialMetricNontrivialObstructionTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget
        externalBurden ∧
      (periodicResetDebtControlTheoremCandidate
          jumpAlignment resetResidual debtBudget ∨
        microlocalLeakIntegrabilityTheoremCandidate
          localGain tailLeak globalBudget) := by
  refine And.intro (nontrivial_obstruction_of_capacity_deficit h.1) ?_
  exact route5_post_obstruction_search_is_two_branch h.2

end ZtareProofs
