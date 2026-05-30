import Mathlib.Tactic
import ZtareProofs.ns_route5_exponential_metric_curvature_capacity

namespace ZtareProofs

/-!
`ns_exponential_metric_survivor_obstruction` records the current cheapest
plausible literature-level novelty theorem target identified by independent
cold-shot review:

kill the exponential-metric route-5 survivor by showing that without a real
curvature-capacity match, strict ellipticity alone does not rescue the branch.
-/

/-- Canonical obstruction shape: ellipticity without curvature-capacity
matching is not enough to keep the exponential-metric survivor alive. -/
theorem exponentialMetricSurvivor_obstructed_of_noCurvatureCapacityMatching
    {γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (hell :
      exponentialMetricEllipticityTarget hnorm lambdaMin)
    (hfail :
      ¬ curvatureCapacityMatchingTarget
        targetCurvature realizedCapacity hnorm capacityBudget) :
    ¬ exponentialMetricSurvivorTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget := by
  intro hsurv
  exact hfail hsurv.2.2

/-- Repo-native theorem target name for the same obstruction. -/
def exponentialMetricSurvivorObstructionTarget
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  exponentialMetricEllipticityTarget hnorm lambdaMin ∧
    ¬ curvatureCapacityMatchingTarget
      targetCurvature realizedCapacity hnorm capacityBudget

theorem no_exponential_metric_survivor_of_obstructionTarget
    {γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      exponentialMetricSurvivorObstructionTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    ¬ exponentialMetricSurvivorTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget := by
  exact exponentialMetricSurvivor_obstructed_of_noCurvatureCapacityMatching
    h.1 h.2

end ZtareProofs
