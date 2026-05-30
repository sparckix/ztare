import Mathlib.Tactic
import ZtareProofs.ns_exponential_metric_capacity_deficit

namespace ZtareProofs

/-!
RESOURCE INCIDENT / QUARANTINE:

This module is intentionally excluded from `ZtareProofs.lean` after a
2026-05-02 local Lean elaboration attempt consumed roughly 90GB RAM and crashed
the laptop. Do not add it back to the umbrella build or run it locally as an
unknown target.

The scientific invariant is the capacity-deficit target in
`ns_exponential_metric_capacity_deficit.lean`. This file is only the intended
bridge from transport-ratio stress plus bounded-generator cap into that target.
It must be refactored into smaller lemmas and checked under a hard time/memory
envelope before being cited as a verified Lean bridge.

`ns_exponential_metric_transport_ratio_obstruction` converts the capacity
deficit into the most concrete PDE-facing shape currently available.

If a transport-scale ratio says the target curvature is at least `ratio` times
the available capacity budget, and the bounded exponential generator can only
pay `hnorm <= hmax`, then the exponential branch dies whenever
`hmax < ratio - 1`.

This is not a proof that the Navier-Stokes branch supplies those hypotheses.
It is the exact theorem-shaped discriminator that future PDE work or ZTARE must
pay or falsify.
-/

/-- Transport-scale stress: target curvature dominates the available capacity
budget by a ratio. -/
def exponentialTransportRatioStressTarget
    (targetCurvature capacityBudget ratio : Real) : Prop :=
  0 < capacityBudget ∧
    0 ≤ ratio ∧
    ratio * capacityBudget ≤ targetCurvature

/-- Generator cap: the exponential metric generator is bounded by `hmax`. -/
def exponentialGeneratorCapTarget
    (hnorm hmax : Real) : Prop :=
  hnorm ≤ hmax

/-- Ratio/generator separation: the observed or proved ratio is too large for
the admissible generator cap. -/
def exponentialRatioBeatsGeneratorCapTarget
    (ratio hmax : Real) : Prop :=
  hmax < ratio - 1

/-- Transport-ratio stress plus a bounded-generator cap implies the capacity
deficit that obstructs curvature-capacity matching. -/
theorem capacity_deficit_of_transport_ratio_and_generator_cap
    {targetCurvature hnorm capacityBudget ratio hmax : Real}
    (hstress :
      exponentialTransportRatioStressTarget
        targetCurvature capacityBudget ratio)
    (hcap : exponentialGeneratorCapTarget hnorm hmax)
    (hgap : exponentialRatioBeatsGeneratorCapTarget ratio hmax) :
    exponentialMetricCapacityDeficitTarget
      targetCurvature hnorm capacityBudget := by
  unfold exponentialMetricCapacityDeficitTarget
  unfold exponentialTransportRatioStressTarget at hstress
  unfold exponentialGeneratorCapTarget at hcap
  unfold exponentialRatioBeatsGeneratorCapTarget at hgap
  have hcapPos : 0 < capacityBudget := hstress.1
  have hratio : ratio * capacityBudget ≤ targetCurvature := hstress.2.2
  have hhnorm : hnorm + 1 < ratio := by
    linarith
  have hscaled : (hnorm + 1) * capacityBudget < ratio * capacityBudget := by
    exact (mul_lt_mul_right hcapPos).mpr hhnorm
  have hscaled' : capacityBudget * (hnorm + 1) < ratio * capacityBudget := by
    calc
      capacityBudget * (hnorm + 1) = (hnorm + 1) * capacityBudget := by ring
      _ < ratio * capacityBudget := hscaled
  linarith

/-- Full route-5 exponential obstruction from the transport-ratio/generator-cap
discriminator. -/
theorem exponential_obstruction_of_transport_ratio_and_generator_cap
    {γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget ratio hmax : Real}
    (hell : exponentialMetricEllipticityTarget hnorm lambdaMin)
    (hstress :
      exponentialTransportRatioStressTarget
        targetCurvature capacityBudget ratio)
    (hcap : exponentialGeneratorCapTarget hnorm hmax)
    (hgap : exponentialRatioBeatsGeneratorCapTarget ratio hmax) :
    exponentialMetricSurvivorObstructionTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget := by
  apply exponentialMetricObstructionTarget_of_capacity_deficit hell
  exact capacity_deficit_of_transport_ratio_and_generator_cap
    hstress hcap hgap

end ZtareProofs
