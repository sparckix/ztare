import Mathlib.Tactic
import ZtareProofs.FormalAnalyticCrossJuliaPoleChart
import ZtareProofs.FormalRamifiedJuliaValuationBalance

/-!
# Two-flow ramified balance from local analytic cross-Julia data

For a nonremovable hidden endpoint, analytic cross-Julia elimination supplies
a meromorphic pole and reciprocal chart.  The two individual Julia identities
then become the inner and outer valuation carriers.  When source and target
have the same positive ramification order, the two polynomial generators have
equal degree.
-/

namespace FormalAnalyticTwoFlowRamifiedBalance

open Filter Polynomial
open scoped Topology
open FormalAnalyticPuncturedExtension
open FormalMeromorphicInfinityChart
open FormalAnalyticCrossJuliaMeromorphic
open FormalAnalyticCrossJuliaPoleChart
open FormalRamifiedJuliaValuationBalance

/-- Local two-flow data on one ramified parameter germ.  Pole order,
reciprocal chart, regularity of the endpoint centers, and equal generator
degree are absent and will be derived. -/
structure TwoFlowRamifiedCrossCarrier where
  cross : AnalyticCrossJuliaCarrier
  sourceCenter : ℂ
  targetCenter : ℂ
  ramificationOrder : ℕ
  sourceDisplacement : ℂ → ℂ
  endpointDisplacement : ℂ → ℂ
  firstDegree : ℕ
  secondDegree : ℕ
  first_nonzero : cross.firstGenerator ≠ 0
  second_nonzero : cross.secondGenerator ≠ 0
  first_degree : cross.firstGenerator.natDegree = firstDegree
  second_degree : cross.secondGenerator.natDegree = secondDegree
  first_degree_at_least_two : 2 ≤ firstDegree
  second_degree_at_least_two : 2 ≤ secondDegree
  ramificationOrder_positive : 0 < ramificationOrder
  source_analytic : AnalyticAt ℂ sourceDisplacement cross.center
  source_zero : sourceDisplacement cross.center = 0
  source_order :
    meromorphicOrderAt sourceDisplacement cross.center =
      ((ramificationOrder : ℤ) : WithTop ℤ)
  endpoint_analytic : AnalyticAt ℂ endpointDisplacement cross.center
  endpoint_zero : endpointDisplacement cross.center = 0
  endpoint_order :
    meromorphicOrderAt endpointDisplacement cross.center =
      ((ramificationOrder : ℤ) : WithTop ℤ)
  source_binding : cross.sourceValue = fun t ↦ sourceCenter + sourceDisplacement t
  endpoint_binding : cross.endpointValue = fun t ↦ targetCenter + endpointDisplacement t
  inner_julia :
    (fun t ↦ deriv cross.hiddenEndpoint t *
      cross.firstGenerator.eval (cross.sourceValue t)) =ᶠ[𝓝[≠] cross.center]
      (fun t ↦ deriv sourceDisplacement t *
        cross.firstGenerator.eval (cross.hiddenEndpoint t))
  outer_julia :
    (fun t ↦ deriv endpointDisplacement t *
      cross.secondGenerator.eval (cross.hiddenEndpoint t)) =ᶠ[𝓝[≠] cross.center]
      (fun t ↦ deriv cross.hiddenEndpoint t *
        cross.secondGenerator.eval (cross.endpointValue t))
  no_finite_extension :
    ¬HasFiniteAnalyticExtension cross.hiddenEndpoint cross.center

/-- The cross-Julia pole chart constructs both valuation carriers on the same
positive pole sheet. -/
theorem TwoFlowRamifiedCrossCarrier.exists_valuationCarriers
    (carrier : TwoFlowRamifiedCrossCarrier) :
    carrier.cross.firstGenerator.rootMultiplicity carrier.sourceCenter = 0 ∧
      carrier.cross.secondGenerator.rootMultiplicity carrier.targetCenter = 0 ∧
      ∃ poleOrder : ℕ,
        0 < poleOrder ∧
        poleOrder * (carrier.firstDegree - 1) = carrier.ramificationOrder ∧
        poleOrder * (carrier.secondDegree - 1) = carrier.ramificationOrder ∧
        carrier.firstDegree = carrier.secondDegree := by
  obtain ⟨poleOrder, hpolePositive, hpoleOrder,
      reciprocal, hreciprocalEq, hreciprocalAnalytic, hreciprocalZero⟩ :=
    AnalyticCrossJuliaCarrier.exists_poleOrder_reciprocalChart
      carrier.cross carrier.no_finite_extension
  have hinnerJulia := carrier.inner_julia
  rw [carrier.source_binding] at hinnerJulia
  have houterJulia := carrier.outer_julia
  rw [carrier.endpoint_binding] at houterJulia
  let innerCarrier : InnerJuliaPoleCarrier carrier.cross.firstGenerator :=
    { degree := carrier.firstDegree
      center := carrier.sourceCenter
      parameterCenter := carrier.cross.center
      baseOrder := carrier.ramificationOrder
      poleOrder := poleOrder
      sourceDisplacement := carrier.sourceDisplacement
      inner := carrier.cross.hiddenEndpoint
      reciprocal := reciprocal
      polynomial_nonzero := carrier.first_nonzero
      polynomial_degree := carrier.first_degree
      degree_at_least_two := carrier.first_degree_at_least_two
      baseOrder_positive := carrier.ramificationOrder_positive
      poleOrder_positive := hpolePositive
      source_analytic := carrier.source_analytic
      source_zero := carrier.source_zero
      source_order := carrier.source_order
      inner_meromorphic := carrier.cross.hiddenEndpoint_meromorphicAt
      inner_order := hpoleOrder
      reciprocal_analytic := hreciprocalAnalytic
      reciprocal_zero := hreciprocalZero
      reciprocal_eq_inverse := hreciprocalEq.symm
      julia := hinnerJulia }
  let outerCarrier : OuterJuliaReturnCarrier carrier.cross.secondGenerator :=
    { degree := carrier.secondDegree
      targetCenter := carrier.targetCenter
      parameterCenter := carrier.cross.center
      endpointOrder := carrier.ramificationOrder
      poleOrder := poleOrder
      endpointDisplacement := carrier.endpointDisplacement
      inner := carrier.cross.hiddenEndpoint
      reciprocal := reciprocal
      polynomial_nonzero := carrier.second_nonzero
      polynomial_degree := carrier.second_degree
      degree_at_least_two := carrier.second_degree_at_least_two
      endpointOrder_positive := carrier.ramificationOrder_positive
      poleOrder_positive := hpolePositive
      endpoint_analytic := carrier.endpoint_analytic
      endpoint_zero := carrier.endpoint_zero
      endpoint_order := carrier.endpoint_order
      inner_meromorphic := carrier.cross.hiddenEndpoint_meromorphicAt
      inner_order := hpoleOrder
      reciprocal_analytic := hreciprocalAnalytic
      reciprocal_zero := hreciprocalZero
      reciprocal_eq_inverse := hreciprocalEq.symm
      julia := houterJulia }
  obtain ⟨hfirstRegular, hfirstBalance⟩ :=
    innerCarrier.regular_and_natural_balance
  obtain ⟨hsecondRegular, hsecondBalance⟩ :=
    outerCarrier.regular_and_natural_balance
  have hfirstRegular' :
      carrier.cross.firstGenerator.rootMultiplicity carrier.sourceCenter = 0 := by
    simpa [innerCarrier] using hfirstRegular
  have hsecondRegular' :
      carrier.cross.secondGenerator.rootMultiplicity carrier.targetCenter = 0 := by
    simpa [outerCarrier] using hsecondRegular
  have hfirstBalance' :
      poleOrder * (carrier.firstDegree - 1) = carrier.ramificationOrder := by
    simpa [innerCarrier] using hfirstBalance
  have hsecondBalance' :
      poleOrder * (carrier.secondDegree - 1) = carrier.ramificationOrder := by
    simpa [outerCarrier] using hsecondBalance
  have hdegrees := equal_degree_of_common_ramified_order
    hpolePositive carrier.first_degree_at_least_two
    carrier.second_degree_at_least_two hfirstBalance' hsecondBalance'
  exact ⟨hfirstRegular', hsecondRegular', poleOrder, hpolePositive,
    hfirstBalance', hsecondBalance', hdegrees⟩

/-- Both finite centers are regular for their generators, both ramification
balances hold, and the generator degrees agree. -/
theorem TwoFlowRamifiedCrossCarrier.regular_balances_and_equal_degree
    (carrier : TwoFlowRamifiedCrossCarrier) :
    carrier.cross.firstGenerator.rootMultiplicity carrier.sourceCenter = 0 ∧
      carrier.cross.secondGenerator.rootMultiplicity carrier.targetCenter = 0 ∧
      ∃ poleOrder : ℕ,
        0 < poleOrder ∧
        poleOrder * (carrier.firstDegree - 1) = carrier.ramificationOrder ∧
        poleOrder * (carrier.secondDegree - 1) = carrier.ramificationOrder ∧
        carrier.firstDegree = carrier.secondDegree := by
  exact carrier.exists_valuationCarriers

/-- Aggregated local two-flow ramified-balance surface. -/
theorem analytic_two_flow_ramified_balance_terminal_certificate :
    ∀ carrier : TwoFlowRamifiedCrossCarrier,
      carrier.cross.firstGenerator.rootMultiplicity carrier.sourceCenter = 0 ∧
      carrier.cross.secondGenerator.rootMultiplicity carrier.targetCenter = 0 ∧
      ∃ poleOrder : ℕ,
        0 < poleOrder ∧
        poleOrder * (carrier.firstDegree - 1) = carrier.ramificationOrder ∧
        poleOrder * (carrier.secondDegree - 1) = carrier.ramificationOrder ∧
        carrier.firstDegree = carrier.secondDegree := by
  intro carrier
  exact carrier.regular_balances_and_equal_degree

end FormalAnalyticTwoFlowRamifiedBalance
