import Mathlib.Tactic
import ZtareProofs.ns_exponential_metric_survivor_obstruction

namespace ZtareProofs

/-!
`ns_exponential_metric_nontriviality_bar` records the exact boundary between a
useful internal obstruction package and a genuinely nontrivial mathematical
result.

The current obstruction target is honest and useful, but it is still close to a
definitional branch kill: it stipulates ellipticity and failure of
curvature-capacity matching, then concludes the survivor fails. For literature
novelty, the missing step is to derive the curvature-capacity failure (or an
equivalent impossible-burden statement) from a PDE-side hypothesis that does not
already negate the survivor by definition.
-/

/-- Current internal obstruction package: enough to kill the branch on-graph,
not yet enough to count as a nontrivial theorem outside the repo. -/
def exponentialMetricInternalObstructionPackage
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real) : Prop :=
  exponentialMetricSurvivorObstructionTarget
    γ coerciveBudget pressureBurden residual offset lambdaMin
    hnorm targetCurvature realizedCapacity capacityBudget

/-- Nontriviality bar: the obstruction becomes mathematically substantial only
when the missing curvature-capacity burden is itself derived from an external
PDE-side hypothesis rather than inserted as the negation of a survivor clause. -/
def exponentialMetricNontrivialObstructionTarget
    (γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget
      externalBurden : Real) : Prop :=
  externalBurden > 0 ∧
    exponentialMetricEllipticityTarget hnorm lambdaMin ∧
    ¬ curvatureCapacityMatchingTarget
      targetCurvature realizedCapacity hnorm capacityBudget

/-- Once the obstruction is only available through the internal package, we
have branch compression but not yet the stronger nontriviality license. -/
theorem internal_obstruction_package_is_not_yet_nontriviality_bar
    {γ coerciveBudget pressureBurden residual offset lambdaMin
      hnorm targetCurvature realizedCapacity capacityBudget : Real}
    (h :
      exponentialMetricInternalObstructionPackage
        γ coerciveBudget pressureBurden residual offset lambdaMin
        hnorm targetCurvature realizedCapacity capacityBudget) :
    ¬ ∀ externalBurden : Real,
        exponentialMetricNontrivialObstructionTarget
          γ coerciveBudget pressureBurden residual offset lambdaMin
          hnorm targetCurvature realizedCapacity capacityBudget
          externalBurden := by
  intro hall
  have hbad :=
    hall 0
  exact lt_irrefl 0 hbad.1

end ZtareProofs
