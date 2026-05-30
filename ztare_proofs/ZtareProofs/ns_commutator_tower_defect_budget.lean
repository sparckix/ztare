import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_contraction_bridge

namespace ZtareProofs

/-!
`ns_commutator_tower_defect_budget` isolates the exact PDE-facing budget object
that sits between the current pressure transport defect and the route-1
contraction bridge.

The point is to stop saying "the defect should feed the tower somehow." This
file names the smallest honest intermediate obligation:

1. decompose the transport defect into a controlled local budget;
2. require that budget to dominate the next tower step;
3. only then ask for strict contraction.
-/

/-- Local budget extracted from the pressure-transport side. -/
def transportDefectBudget
    (transportDefect localQuadratic advectedPressure commutatorResidual budget : Real) : Prop :=
  0 ≤ transportDefect ∧
    0 ≤ localQuadratic ∧
    0 ≤ advectedPressure ∧
    0 ≤ commutatorResidual ∧
    budget = transportDefect + localQuadratic + advectedPressure + commutatorResidual

/--
The next tower step is admissible if the pressure-side defect budget already
dominates it before any contraction claim is made.
-/
def defectBudgetFeedsNextTowerStep
    (budget nextStep : Real) : Prop :=
  0 ≤ budget ∧
    0 ≤ nextStep ∧
    nextStep ≤ budget

/--
The exact route-1 intermediate target: a pressure-transport budget exists and
it already feeds the next commutator level.
-/
def route1DefectBudgetTarget
    (transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep : Real) : Prop :=
  transportDefectBudget
    transportDefect localQuadratic advectedPressure commutatorResidual budget ∧
    defectBudgetFeedsNextTowerStep budget nextStep

/--
If the current pressure-side transport defect is controlled and the resulting
budget already feeds the next tower step, then the contraction bridge reduces
to the single remaining strict-ratio question.
-/
theorem budget_feeds_towerStep_of_route1DefectBudgetTarget
    {transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep : Real}
    (h :
      route1DefectBudgetTarget
        transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep) :
    transportResidualFeedsTowerStep
      budget 0 nextStep := by
  rcases h with ⟨hbudget, hfeed⟩
  rcases hbudget with ⟨ht, hl, ha, hc, hsum⟩
  rcases hfeed with ⟨hb, hn, hle⟩
  refine ⟨hb, by positivity, ?_⟩
  simpa [hsum] using hle

/--
Budget-facing contraction target.

This separates the two route-1 moves cleanly:
1. build the pressure-side budget;
2. contract the next tower step relative to the current one.
-/
def budgetFacingContractionTarget
    (budget currentStep nextStep ratio : Real) : Prop :=
  transportResidualFeedsTowerStep budget 0 nextStep ∧
    0 ≤ ratio ∧ ratio < 1 ∧
    nextStep ≤ ratio * currentStep

/--
PDE-facing reduction of the route-1 next target.

This is the sharpest honest state of the branch:
first pay the pressure-transport budget target, then pay strict contraction.
-/
def route1ExactNextTarget
    (stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio : Real) : Prop :=
  pressureL2TransportDefectObligation
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual ∧
    route1DefectBudgetTarget
      transportDefect localQuadratic advectedPressure commutatorResidual budget nextStep ∧
    budgetFacingContractionTarget budget currentStep nextStep ratio

/--
If the exact route-1 next target is paid, then the branch reaches the
contraction bridge object without any hidden extra architecture.
-/
theorem budgetFacingContractionTarget_of_route1ExactNextTarget
    {stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual
      budget currentStep nextStep ratio : Real}
    (h :
      route1ExactNextTarget
        stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
        transportDefect localQuadratic advectedPressure commutatorResidual
        budget currentStep nextStep ratio) :
    pressureL2TransportDefectObligation
      stretch pressureL2 vorticitySq radialGrade Λ0 C0 decayProfile
      transportDefect localQuadratic advectedPressure commutatorResidual ∧
    budgetFacingContractionTarget budget currentStep nextStep ratio := by
  rcases h with ⟨htransport, _, hbudgetFacing⟩
  exact ⟨htransport, hbudgetFacing⟩

end ZtareProofs
