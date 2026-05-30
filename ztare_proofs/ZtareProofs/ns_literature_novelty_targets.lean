import Mathlib.Tactic
import ZtareProofs.ns_decisive_ns_theorem_search
import ZtareProofs.ns_exponential_metric_survivor_obstruction
import ZtareProofs.ns_route1_frequency_collapse_obstruction

namespace ZtareProofs

/-!
`ns_literature_novelty_targets` records the smallest theorem classes that would
actually count as literature-level novelty from the current decisive fork.

This file is intentionally stricter than the internal proof-search files. It is
not about "what is next locally?" It is about "what would survive outside the
repo as a mathematically interesting new result?"
-/

/-- Route-1 obstruction / collapse theorem candidate. -/
def route1ObstructionTheoremCandidate
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real) : Prop :=
  route1FrequencyCollapseObstructionTarget
    δ lam amplitude ε

/-- Route-1 constructive / criterion theorem candidate. -/
def route1CriterionTheoremCandidate
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε : Real) : Prop :=
  route1KillerTheoremSearchFrontier
      transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε

/-- Route-5 obstruction theorem candidate: kill one exact branch on its own
native burden. -/
def route5ObstructionTheoremCandidate
    (jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  periodicResetDebtControlTheoremCandidate
      jumpAlignment resetResidual debtBudget ∨
    microlocalLeakIntegrabilityTheoremCandidate
      localGain tailLeak globalBudget ∨
    exponentialCapacityFloorTheoremCandidate
      finiteIntervalCapacity infiniteTimeFloor driftBudget ∨
    exponentialMetricSurvivorObstructionTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget

/-- Smallest theorem classes likely to clear the literature novelty bar from
the current branch. -/
def literatureNoveltyTarget
    (transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  route1ObstructionTheoremCandidate
      transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε ∨
    route1CriterionTheoremCandidate
      transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε ∨
    route5ObstructionTheoremCandidate
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget

theorem literature_novelty_target_is_exact_union
    {transportDefect commutatorResidual currentStep nextStep ratio
      δ lam amplitude ε
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      literatureNoveltyTarget
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    route1ObstructionTheoremCandidate
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε ∨
      route1CriterionTheoremCandidate
        transportDefect commutatorResidual currentStep nextStep ratio
        δ lam amplitude ε ∨
      route5ObstructionTheoremCandidate
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

end ZtareProofs
