import Mathlib.Tactic
import ZtareProofs.ns_route5_tensor_absorption_ellipticity

namespace ZtareProofs

/-!
`ns_route5_exponential_metric_curvature_capacity` promotes the theorem burden
exposed by the exponential-metric variant.

The useful content is narrow:

* strict ellipticity can be paid by exponential parametrization for bounded
  generators `H`;
* but the live burden becomes curvature-capacity matching: can the required
  commutator / holonomy be realized without forcing `‖H‖ -> ∞`?
-/

/-- Exponential metric keeps ellipticity for bounded generator norm. -/
def exponentialMetricEllipticityTarget (hnorm lambdaMin : Real) : Prop :=
  0 ≤ hnorm ∧
    lambdaMin = Real.exp (-hnorm) ∧
    0 < lambdaMin

/-- Curvature-capacity matching burden for bounded generator norm. -/
def curvatureCapacityMatchingTarget
    (targetCurvature realizedCapacity hnorm capacityBudget : Real) : Prop :=
  0 ≤ targetCurvature ∧
    0 ≤ realizedCapacity ∧
    0 ≤ hnorm ∧
    0 ≤ capacityBudget ∧
    realizedCapacity ≤ capacityBudget * (hnorm + 1) ∧
    targetCurvature ≤ realizedCapacity

/-- Exact branch target for the exponential-metric survivor. -/
def exponentialMetricSurvivorTarget
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  route5TensorAbsorptionNextDiscriminator
      γ coerciveBudget pressureBurden residual offset lambdaMin ∧
    exponentialMetricEllipticityTarget hnorm lambdaMin ∧
    curvatureCapacityMatchingTarget
      targetCurvature realizedCapacity hnorm capacityBudget

end ZtareProofs
