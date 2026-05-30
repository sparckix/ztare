import Mathlib.Tactic
import ZtareProofs.ns_exponential_metric_survivor_obstruction
import ZtareProofs.ns_exponential_metric_nontriviality_bar

namespace ZtareProofs

/-!
`ns_exponential_metric_capacity_deficit` is the first nontrivial theorem layer
beneath the exponential route-5 obstruction.

The previous obstruction target assumed failure of curvature-capacity matching.
This file replaces that assumption with a positive external deficit:

`capacityBudget * (hnorm + 1) < targetCurvature`.

That inequality is not the negation of the survivor clause. It is a concrete
upper-capacity-vs-required-curvature separation. Once it is paid from PDE-side
estimates, curvature-capacity matching fails automatically.
-/

/-- External capacity deficit: the maximum curvature that a bounded
exponential-metric generator can realize is strictly below the target
curvature. -/
def exponentialMetricCapacityDeficitTarget
    (targetCurvature hnorm capacityBudget : Real) : Prop :=
  capacityBudget * (hnorm + 1) < targetCurvature

/-- A positive capacity deficit rules out curvature-capacity matching. -/
theorem no_curvatureCapacityMatching_of_capacity_deficit
    {targetCurvature realizedCapacity hnorm capacityBudget : Real}
    (hdef :
      exponentialMetricCapacityDeficitTarget
        targetCurvature hnorm capacityBudget) :
    ¬ curvatureCapacityMatchingTarget
      targetCurvature realizedCapacity hnorm capacityBudget := by
  intro hmatch
  have hcap : realizedCapacity ≤ capacityBudget * (hnorm + 1) :=
    hmatch.2.2.2.2.1
  have htar : targetCurvature ≤ realizedCapacity :=
    hmatch.2.2.2.2.2
  unfold exponentialMetricCapacityDeficitTarget at hdef
  linarith

/-- Any successful curvature-capacity match forces the target curvature below
the bounded-generator capacity ceiling. This is the contrapositive pressure
that makes the obstruction scientifically useful: the survivor must actually
pay this capacity budget. -/
theorem capacity_ceiling_of_curvatureCapacityMatching
    {targetCurvature realizedCapacity hnorm capacityBudget : Real}
    (hmatch :
      curvatureCapacityMatchingTarget
        targetCurvature realizedCapacity hnorm capacityBudget) :
    targetCurvature ≤ capacityBudget * (hnorm + 1) := by
  have hcap : realizedCapacity ≤ capacityBudget * (hnorm + 1) :=
    hmatch.2.2.2.2.1
  have htar : targetCurvature ≤ realizedCapacity :=
    hmatch.2.2.2.2.2
  linarith

/-- If target curvature is at least `ratio` times the capacity budget and the
capacity budget is positive, the matching condition forces the generator norm
to be at least `ratio - 1`. This is the algebraic form of the transport-scale
stress observed in the saved audit. -/
def exponentialMetricGeneratorNormBurdenTarget
    (targetCurvature hnorm capacityBudget ratio : Real) : Prop :=
  0 < capacityBudget ∧
    0 ≤ ratio ∧
    ratio * capacityBudget ≤ targetCurvature ∧
    ratio - 1 ≤ hnorm

theorem generator_norm_burden_of_curvatureCapacityMatching
    {targetCurvature realizedCapacity hnorm capacityBudget ratio : Real}
    (hmatch :
      curvatureCapacityMatchingTarget
        targetCurvature realizedCapacity hnorm capacityBudget)
    (hcapPos : 0 < capacityBudget)
    (hratioNonneg : 0 ≤ ratio)
    (hratio : ratio * capacityBudget ≤ targetCurvature) :
    exponentialMetricGeneratorNormBurdenTarget
      targetCurvature hnorm capacityBudget ratio := by
  refine And.intro hcapPos ?_
  refine And.intro hratioNonneg ?_
  refine And.intro hratio ?_
  have hceil : targetCurvature ≤ capacityBudget * (hnorm + 1) :=
    capacity_ceiling_of_curvatureCapacityMatching hmatch
  have hbound : ratio * capacityBudget ≤ capacityBudget * (hnorm + 1) := by
    linarith
  have hboundRight : ratio * capacityBudget ≤ (hnorm + 1) * capacityBudget := by
    calc
      ratio * capacityBudget ≤ capacityBudget * (hnorm + 1) := hbound
      _ = (hnorm + 1) * capacityBudget := by ring
  nlinarith [hboundRight, hcapPos]

/-- Capacity deficit plus ellipticity yields the internal obstruction target
without directly assuming the survivor clause fails. -/
theorem exponentialMetricObstructionTarget_of_capacity_deficit
    {γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (hell : exponentialMetricEllipticityTarget hnorm lambdaMin)
    (hdef :
      exponentialMetricCapacityDeficitTarget
        targetCurvature hnorm capacityBudget) :
    exponentialMetricSurvivorObstructionTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget := by
  exact And.intro hell
    (no_curvatureCapacityMatching_of_capacity_deficit hdef)

/-- Capacity deficit is the current PDE-side nontriviality target for the
exponential route-5 obstruction. -/
def exponentialMetricCapacityDeficitNontrivialTarget
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget externalBurden : Real) :
    Prop :=
  externalBurden =
      targetCurvature - capacityBudget * (hnorm + 1) ∧
    0 < externalBurden ∧
    exponentialMetricEllipticityTarget hnorm lambdaMin

/-- The explicit deficit target implies the nontrivial obstruction target. -/
theorem nontrivial_obstruction_of_capacity_deficit
    {γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget externalBurden : Real}
    (h :
      exponentialMetricCapacityDeficitNontrivialTarget
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget externalBurden) :
    exponentialMetricNontrivialObstructionTarget
      γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget
      externalBurden := by
  refine And.intro h.2.1 ?_
  refine And.intro h.2.2 ?_
  apply no_curvatureCapacityMatching_of_capacity_deficit
  unfold exponentialMetricCapacityDeficitTarget
  linarith [h.1, h.2.1]

end ZtareProofs
