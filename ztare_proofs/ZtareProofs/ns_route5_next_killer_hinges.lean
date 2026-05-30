import Mathlib.Tactic
import ZtareProofs.ns_route5_postrun_survivor_surface

namespace ZtareProofs

/-!
`ns_route5_next_killer_hinges` records the exact next hostile-referee payment
for each surviving route-5 rescue branch.

The point is not to add more survivor prose. It is to prevent each branch from
remaining alive without naming the single next theorem that kills or rescues it.
-/

/-- Periodic resets only survive if reset jumps can be chosen orthogonal
enough that global residuals do not rebuild the route-1 debt. -/
def periodicResetOrthogonalityHinge
    (jumpAlignment resetResidual debtBudget : Real) : Prop :=
  0 ≤ jumpAlignment ∧
    0 ≤ resetResidual ∧
    0 ≤ debtBudget ∧
    resetResidual ≤ jumpAlignment * debtBudget

/-- Micro-local diffusion only survives if the global leak is integrable on the
non-compact domain rather than merely small locally. -/
def microlocalLeakIntegrabilityHinge
    (localGain tailLeak globalBudget : Real) : Prop :=
  0 ≤ localGain ∧
    0 ≤ tailLeak ∧
    0 ≤ globalBudget ∧
    tailLeak ≤ globalBudget ∧
    tailLeak ≤ localGain

/-- Exponential metrics only survive if the curvature-capacity match does not
drift to zero over arbitrarily long finite-energy trajectories. -/
def exponentialCapacityDriftHinge
    (finiteIntervalCapacity infiniteTimeFloor driftBudget : Real) : Prop :=
  0 ≤ finiteIntervalCapacity ∧
    0 ≤ infiniteTimeFloor ∧
    0 ≤ driftBudget ∧
    driftBudget ≤ finiteIntervalCapacity ∧
    infiniteTimeFloor ≤ finiteIntervalCapacity - driftBudget

/-- Exact next killer surface for the three post-run route-5 survivors. -/
def route5NextKillerHinges
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget : Real) : Prop :=
  (periodicMetricResetSurvivorTarget
      γ t kappaMax totalStrain logResetCost resetCount globalResidual ∧
    periodicResetOrthogonalityHinge jumpAlignment resetResidual debtBudget) ∨
  (microlocalDiffusiveAbsorptionSurvivorTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty
      globalResidual decayBudget horizon ∧
    microlocalLeakIntegrabilityHinge localGain tailLeak globalBudget) ∨
  (exponentialMetricSurvivorTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget ∧
    exponentialCapacityDriftHinge
      finiteIntervalCapacity infiniteTimeFloor driftBudget)

/-- Any surviving post-run branch must eventually present one of the three
exact killer hinges. -/
theorem route5_postrun_survivor_requires_killer_hinge
    {γ t kappaMax totalStrain logResetCost resetCount globalResidual
      coerciveBudget pressureBurden residual offset lambdaMin
      rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget horizon
      hnorm targetCurvature realizedCapacity capacityBudget
      jumpAlignment resetResidual debtBudget
      localGain tailLeak globalBudget
      finiteIntervalCapacity infiniteTimeFloor driftBudget : Real}
    (hbranch :
      route5NextKillerHinges
        γ t kappaMax totalStrain logResetCost resetCount globalResidual
        coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty decayBudget
        horizon
        hnorm targetCurvature realizedCapacity capacityBudget
        jumpAlignment resetResidual debtBudget
        localGain tailLeak globalBudget
        finiteIntervalCapacity infiniteTimeFloor driftBudget) :
    (periodicMetricResetSurvivorTarget
        γ t kappaMax totalStrain logResetCost resetCount globalResidual ∧
      periodicResetOrthogonalityHinge jumpAlignment resetResidual debtBudget) ∨
    (microlocalDiffusiveAbsorptionSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        rawPenalty diffusiveScale smoothingOrder dilutedPenalty
        globalResidual decayBudget horizon ∧
      microlocalLeakIntegrabilityHinge localGain tailLeak globalBudget) ∨
    (exponentialMetricSurvivorTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget ∧
      exponentialCapacityDriftHinge
        finiteIntervalCapacity infiniteTimeFloor driftBudget) := by
  exact hbranch

end ZtareProofs
