import Mathlib.Tactic

namespace ZtareProofs

/-!
`ns_route5_periodic_metric_reset` records the first new survivor class exposed
by the survivor-theorem run.

The question is not whether periodic resets sound clever. The exact burden is:

* can exact absorption on disjoint intervals, interrupted by resets that
  restore ellipticity, avoid reconstructing the original route-1 debt?
-/

/-- Local absorption succeeds on each interval between resets. -/
def localResetIntervalAbsorptionTarget
    (γ t kappaMax : Real) : Prop :=
  0 ≤ γ ∧
    0 ≤ t ∧
    1 < kappaMax ∧
    Real.exp (2 * γ * t) ≤ kappaMax

/-- Global reset cost accumulated across all reset boundaries. -/
def periodicResetGlobalResidualTarget
    (totalStrain logResetCost resetCount globalResidual : Real) : Prop :=
  0 ≤ totalStrain ∧
    0 ≤ logResetCost ∧
    0 ≤ resetCount ∧
    globalResidual = logResetCost * resetCount ∧
    totalStrain ≤ globalResidual

/-- Exact survivor target for the periodic-metric-reset branch. -/
def periodicMetricResetSurvivorTarget
    (γ t kappaMax totalStrain logResetCost resetCount globalResidual : Real) : Prop :=
  localResetIntervalAbsorptionTarget γ t kappaMax ∧
    periodicResetGlobalResidualTarget
      totalStrain logResetCost resetCount globalResidual

end ZtareProofs
