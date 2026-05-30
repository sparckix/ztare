import Mathlib.Tactic
import ZtareProofs.ns_route5_next_killer_hinges
import ZtareProofs.ns_exponential_metric_survivor_obstruction

namespace ZtareProofs

/-!
`ns_route5_killer_theorem_search` is the local theorem-search surface after the
post-run survivor branches have already been compressed to exact killer hinges.

At this stage, useful theorem search is not "geometry maybe helps." It is one
of a small number of exact theorem candidates:

1. periodic-reset orthogonality / debt control,
2. microlocal leak integrability,
3. exponential-metric infinite-time capacity floor,
4. exponential-metric obstruction if curvature-capacity matching fails.
-/

/-- Theorem-search target for periodic reset debt control. -/
def periodicResetDebtControlTheoremCandidate
    (jumpAlignment resetResidual debtBudget : Real) : Prop :=
  periodicResetOrthogonalityHinge
    jumpAlignment resetResidual debtBudget

/-- Theorem-search target for microlocal non-compact leak integrability. -/
def microlocalLeakIntegrabilityTheoremCandidate
    (localGain tailLeak globalBudget : Real) : Prop :=
  microlocalLeakIntegrabilityHinge
    localGain tailLeak globalBudget

/-- Theorem-search target for exponential-metric infinite-time drift control. -/
def exponentialCapacityFloorTheoremCandidate
    (finiteIntervalCapacity infiniteTimeFloor driftBudget : Real) : Prop :=
  exponentialCapacityDriftHinge
    finiteIntervalCapacity infiniteTimeFloor driftBudget

/-- Cheapest route-5 obstruction theorem currently visible from the local fork:
if curvature-capacity matching fails, the exponential-metric survivor dies. -/
def exponentialMetricObstructionTheoremCandidate
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  exponentialMetricSurvivorObstructionTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin
    hnorm targetCurvature realizedCapacity capacityBudget

/-- Exact theorem-search surface after branch compression and killer-hinge
compression are both complete. -/
def route5KillerTheoremSearchFrontier
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
    exponentialMetricObstructionTheoremCandidate
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget

theorem route5_killer_frontier_is_exact
    {jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      route5KillerTheoremSearchFrontier
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    periodicResetDebtControlTheoremCandidate
        jumpAlignment resetResidual debtBudget ∨
      microlocalLeakIntegrabilityTheoremCandidate
        localGain tailLeak globalBudget ∨
      exponentialCapacityFloorTheoremCandidate
        finiteIntervalCapacity infiniteTimeFloor driftBudget ∨
      exponentialMetricObstructionTheoremCandidate
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget := by
  exact h

end ZtareProofs
