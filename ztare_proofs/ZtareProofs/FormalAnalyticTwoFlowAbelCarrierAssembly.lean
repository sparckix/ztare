import Mathlib.Tactic
import ZtareProofs.FormalAnalyticTwoFlowRamifiedBalance
import ZtareProofs.FormalAnalyticTwoJuliaAbelCollision
import ZtareProofs.FormalPolynomialFiniteTimeCoordinate
import ZtareProofs.FormalPolynomialInfinityTimeCoordinate
import ZtareProofs.FormalPolynomialRamifiedTrajectorySheet

/-!
# Assembly of a two-Julia Abel carrier from a ramified cross-Julia germ

The ramified cross-Julia carrier already owns the source, target, hidden
branch, and both Julia rows.  This file constructs the reciprocal chart and
the four normalized Abel coordinates, then restricts all eventual identities
to one punctured complex ball.  No global continuation or route-exhaustion
statement is asserted here.
-/

namespace FormalAnalyticTwoFlowAbelCarrierAssembly

open Filter Metric Polynomial Set
open scoped Topology

open FormalAnalyticCrossJuliaMeromorphic
open FormalAnalyticCrossJuliaPoleChart
open FormalAnalyticTwoFlowRamifiedBalance
open FormalAnalyticTwoJuliaAbelCollision
open FormalMeromorphicInfinityChart
open FormalPolynomialFiniteTimeCoordinate
open FormalPolynomialInfinityTimeCoordinate
open FormalPolynomialRamifiedTrajectorySheet
open FormalRamifiedJuliaValuationBalance

private structure AbelPointData
    (input : TwoFlowRamifiedCrossCarrier)
    (reciprocal firstFinite secondFinite firstInfinity secondInfinity :
      ℂ → ℂ)
    (t : ℂ) : Prop where
  sourceDisplacement_analytic :
    AnalyticAt ℂ input.sourceDisplacement t
  endpointDisplacement_analytic :
    AnalyticAt ℂ input.endpointDisplacement t
  hidden_differentiable :
    DifferentiableAt ℂ input.cross.hiddenEndpoint t
  reciprocal_analytic : AnalyticAt ℂ reciprocal t
  reciprocal_eq :
    (input.cross.hiddenEndpoint t)⁻¹ = reciprocal t
  inner_julia :
    deriv input.cross.hiddenEndpoint t *
        input.cross.firstGenerator.eval (input.cross.sourceValue t) =
      deriv input.sourceDisplacement t *
        input.cross.firstGenerator.eval (input.cross.hiddenEndpoint t)
  outer_julia :
    deriv input.cross.hiddenEndpoint t *
        input.cross.secondGenerator.eval (input.cross.endpointValue t) =
      deriv input.endpointDisplacement t *
        input.cross.secondGenerator.eval (input.cross.hiddenEndpoint t)
  firstFinite_derivative :
    HasDerivAt firstFinite
      (finiteTimeIntegrand input.cross.firstGenerator
        (input.cross.sourceValue t))
      (input.cross.sourceValue t)
  secondFinite_derivative :
    HasDerivAt secondFinite
      (finiteTimeIntegrand input.cross.secondGenerator
        (input.cross.endpointValue t))
      (input.cross.endpointValue t)
  firstInfinity_derivative :
    HasDerivAt firstInfinity
      (reciprocalTimeIntegrand input.cross.firstGenerator
        input.firstDegree (reciprocal t))
      (reciprocal t)
  secondInfinity_derivative :
    HasDerivAt secondInfinity
      (reciprocalTimeIntegrand input.cross.secondGenerator
        input.secondDegree (reciprocal t))
      (reciprocal t)
  source_regular :
    input.cross.firstGenerator.eval (input.cross.sourceValue t) ≠ 0
  target_regular :
    input.cross.secondGenerator.eval (input.cross.endpointValue t) ≠ 0
  hidden_nonzero : input.cross.hiddenEndpoint t ≠ 0
  first_reverse_nonzero :
    input.cross.firstGenerator.reverse.eval (reciprocal t) ≠ 0
  second_reverse_nonzero :
    input.cross.secondGenerator.reverse.eval (reciprocal t) ≠ 0

/-- A centered ramified cross-Julia germ constructs the complete local
two-Julia Abel carrier.  The returned pole order is tied simultaneously to
the reciprocal analytic order and both polynomial degree balances. -/
theorem TwoFlowRamifiedCrossCarrier.exists_twoJuliaAbelCarrier
    (input : TwoFlowRamifiedCrossCarrier)
    (hcenter : input.cross.center = 0) :
    ∃ (poleOrder : ℕ) (carrier : TwoJuliaAbelCarrier),
      0 < poleOrder ∧
      carrier.firstGenerator = input.cross.firstGenerator ∧
      carrier.secondGenerator = input.cross.secondGenerator ∧
      carrier.firstDegree = input.firstDegree ∧
      carrier.secondDegree = input.secondDegree ∧
      carrier.center = input.cross.center ∧
      carrier.source = input.cross.sourceValue ∧
      carrier.target = input.cross.endpointValue ∧
      carrier.hidden = input.cross.hiddenEndpoint ∧
      analyticOrderAt carrier.reciprocal carrier.center =
        (poleOrder : ℕ) ∧
      poleOrder * (input.firstDegree - 1) = input.ramificationOrder ∧
      poleOrder * (input.secondDegree - 1) = input.ramificationOrder ∧
      input.firstDegree = input.secondDegree := by
  obtain ⟨poleOrder, hpolePositive, hhiddenOrder, reciprocal,
      hreciprocalEq, hreciprocalAnalytic, hreciprocalZero⟩ :=
    AnalyticCrossJuliaCarrier.exists_poleOrder_reciprocalChart
      input.cross input.no_finite_extension
  have hinnerJulia := input.inner_julia
  rw [input.source_binding] at hinnerJulia
  have houterJulia := input.outer_julia
  rw [input.endpoint_binding] at houterJulia
  let innerCarrier : InnerJuliaPoleCarrier input.cross.firstGenerator :=
    { degree := input.firstDegree
      center := input.sourceCenter
      parameterCenter := input.cross.center
      baseOrder := input.ramificationOrder
      poleOrder := poleOrder
      sourceDisplacement := input.sourceDisplacement
      inner := input.cross.hiddenEndpoint
      reciprocal := reciprocal
      polynomial_nonzero := input.first_nonzero
      polynomial_degree := input.first_degree
      degree_at_least_two := input.first_degree_at_least_two
      baseOrder_positive := input.ramificationOrder_positive
      poleOrder_positive := hpolePositive
      source_analytic := input.source_analytic
      source_zero := input.source_zero
      source_order := input.source_order
      inner_meromorphic := input.cross.hiddenEndpoint_meromorphicAt
      inner_order := hhiddenOrder
      reciprocal_analytic := hreciprocalAnalytic
      reciprocal_zero := hreciprocalZero
      reciprocal_eq_inverse := hreciprocalEq.symm
      julia := hinnerJulia }
  let outerCarrier : OuterJuliaReturnCarrier input.cross.secondGenerator :=
    { degree := input.secondDegree
      targetCenter := input.targetCenter
      parameterCenter := input.cross.center
      endpointOrder := input.ramificationOrder
      poleOrder := poleOrder
      endpointDisplacement := input.endpointDisplacement
      inner := input.cross.hiddenEndpoint
      reciprocal := reciprocal
      polynomial_nonzero := input.second_nonzero
      polynomial_degree := input.second_degree
      degree_at_least_two := input.second_degree_at_least_two
      endpointOrder_positive := input.ramificationOrder_positive
      poleOrder_positive := hpolePositive
      endpoint_analytic := input.endpoint_analytic
      endpoint_zero := input.endpoint_zero
      endpoint_order := input.endpoint_order
      inner_meromorphic := input.cross.hiddenEndpoint_meromorphicAt
      inner_order := hhiddenOrder
      reciprocal_analytic := hreciprocalAnalytic
      reciprocal_zero := hreciprocalZero
      reciprocal_eq_inverse := hreciprocalEq.symm
      julia := houterJulia }
  obtain ⟨hfirstMultiplicity, hfirstBalance⟩ :=
    innerCarrier.regular_and_natural_balance
  obtain ⟨hsecondMultiplicity, hsecondBalance⟩ :=
    outerCarrier.regular_and_natural_balance
  have hdegrees : input.firstDegree = input.secondDegree :=
    equal_degree_of_common_ramified_order hpolePositive
      input.first_degree_at_least_two input.second_degree_at_least_two
      hfirstBalance hsecondBalance
  have hfirstRegular :
      input.cross.firstGenerator.eval input.sourceCenter ≠ 0 := by
    intro hzero
    have hroot : input.cross.firstGenerator.IsRoot input.sourceCenter := hzero
    have hpositive :=
      (rootMultiplicity_pos input.first_nonzero).2 hroot
    rw [show input.cross.firstGenerator.rootMultiplicity
      input.sourceCenter = 0 by simpa [innerCarrier] using hfirstMultiplicity]
      at hpositive
    omega
  have hsecondRegular :
      input.cross.secondGenerator.eval input.targetCenter ≠ 0 := by
    intro hzero
    have hroot : input.cross.secondGenerator.IsRoot input.targetCenter := hzero
    have hpositive :=
      (rootMultiplicity_pos input.second_nonzero).2 hroot
    rw [show input.cross.secondGenerator.rootMultiplicity
      input.targetCenter = 0 by simpa [outerCarrier] using hsecondMultiplicity]
      at hpositive
    omega
  obtain ⟨firstFinite, hfirstFiniteAnalytic, hfirstFiniteZero,
      hfirstFiniteDerivative, _hfirstFiniteDerivativeCenter,
      _hfirstFiniteOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate
      input.cross.firstGenerator input.sourceCenter hfirstRegular
  obtain ⟨secondFinite, hsecondFiniteAnalytic, hsecondFiniteZero,
      hsecondFiniteDerivative, _hsecondFiniteDerivativeCenter,
      _hsecondFiniteOrder⟩ :=
    polynomial_finite_time_coordinate_terminal_certificate
      input.cross.secondGenerator input.targetCenter hsecondRegular
  obtain ⟨firstInfinity, hfirstInfinityAnalytic, hfirstInfinityZero,
      hfirstInfinityDerivative, _hfirstInfinityOrder,
      _hfirstInfinityNonzeroOrder⟩ :=
    polynomial_infinity_time_coordinate_terminal_certificate
      input.cross.firstGenerator input.firstDegree input.first_degree
      input.first_degree_at_least_two
  obtain ⟨secondInfinity, hsecondInfinityAnalytic, hsecondInfinityZero,
      hsecondInfinityDerivative, _hsecondInfinityOrder,
      _hsecondInfinityNonzeroOrder⟩ :=
    polynomial_infinity_time_coordinate_terminal_certificate
      input.cross.secondGenerator input.secondDegree input.second_degree
      input.second_degree_at_least_two
  have hsourceCenter :
      input.cross.sourceValue input.cross.center = input.sourceCenter := by
    rw [input.source_binding]
    simp [input.source_zero]
  have htargetCenter :
      input.cross.endpointValue input.cross.center = input.targetCenter := by
    rw [input.endpoint_binding]
    simp [input.endpoint_zero]
  have hsourceTendsto :
      Tendsto input.cross.sourceValue (𝓝 input.cross.center)
        (𝓝 input.sourceCenter) := by
    rw [← hsourceCenter]
    exact input.cross.source_analytic.continuousAt
  have htargetTendsto :
      Tendsto input.cross.endpointValue (𝓝 input.cross.center)
        (𝓝 input.targetCenter) := by
    rw [← htargetCenter]
    exact input.cross.endpoint_analytic.continuousAt
  have hreciprocalTendsto :
      Tendsto reciprocal (𝓝 input.cross.center) (𝓝 0) := by
    rw [← hreciprocalZero]
    exact hreciprocalAnalytic.continuousAt
  have hfirstFinitePulled := hsourceTendsto hfirstFiniteDerivative
  have hsecondFinitePulled := htargetTendsto hsecondFiniteDerivative
  have hfirstInfinityPulled :=
    hreciprocalTendsto hfirstInfinityDerivative
  have hsecondInfinityPulled :=
    hreciprocalTendsto hsecondInfinityDerivative
  have hsourceRegularEventually :
      ∀ᶠ t in 𝓝 input.cross.center,
        input.cross.firstGenerator.eval (input.cross.sourceValue t) ≠ 0 :=
    (input.cross.source_analytic.aeval_polynomial
      input.cross.firstGenerator).continuousAt.eventually_ne
        (by simpa only [hsourceCenter] using hfirstRegular)
  have htargetRegularEventually :
      ∀ᶠ t in 𝓝 input.cross.center,
        input.cross.secondGenerator.eval (input.cross.endpointValue t) ≠ 0 :=
    (input.cross.endpoint_analytic.aeval_polynomial
      input.cross.secondGenerator).continuousAt.eventually_ne
        (by simpa only [htargetCenter] using hsecondRegular)
  have hhiddenNonzero :
      ∀ᶠ t in 𝓝[≠] input.cross.center,
        input.cross.hiddenEndpoint t ≠ 0 := by
    apply (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
      input.cross.hiddenEndpoint_meromorphicAt).mp
    rw [hhiddenOrder]
    simp
  have hfirstLeading : input.cross.firstGenerator.leadingCoeff ≠ 0 :=
    leadingCoeff_ne_zero.mpr input.first_nonzero
  have hsecondLeading : input.cross.secondGenerator.leadingCoeff ≠ 0 :=
    leadingCoeff_ne_zero.mpr input.second_nonzero
  have hfirstReverseEventually :
      ∀ᶠ t in 𝓝 input.cross.center,
        input.cross.firstGenerator.reverse.eval (reciprocal t) ≠ 0 :=
    (hreciprocalAnalytic.aeval_polynomial
      input.cross.firstGenerator.reverse).continuousAt.eventually_ne
        (by
          simpa [Polynomial.aeval_def, hreciprocalZero,
            coeff_zero_reverse] using hfirstLeading)
  have hsecondReverseEventually :
      ∀ᶠ t in 𝓝 input.cross.center,
        input.cross.secondGenerator.reverse.eval (reciprocal t) ≠ 0 :=
    (hreciprocalAnalytic.aeval_polynomial
      input.cross.secondGenerator.reverse).continuousAt.eventually_ne
        (by
          simpa [Polynomial.aeval_def, hreciprocalZero,
            coeff_zero_reverse] using hsecondLeading)
  have hpoint : ∀ᶠ t in 𝓝[≠] input.cross.center,
      AbelPointData input reciprocal firstFinite secondFinite
        firstInfinity secondInfinity t := by
    filter_upwards [
      eventually_nhdsWithin_of_eventually_nhds
        input.source_analytic.eventually_analyticAt,
      eventually_nhdsWithin_of_eventually_nhds
        input.endpoint_analytic.eventually_analyticAt,
      input.cross.hidden_differentiable,
      eventually_nhdsWithin_of_eventually_nhds
        hreciprocalAnalytic.eventually_analyticAt,
      hreciprocalEq, input.inner_julia, input.outer_julia,
      eventually_nhdsWithin_of_eventually_nhds hfirstFinitePulled,
      eventually_nhdsWithin_of_eventually_nhds hsecondFinitePulled,
      eventually_nhdsWithin_of_eventually_nhds hfirstInfinityPulled,
      eventually_nhdsWithin_of_eventually_nhds hsecondInfinityPulled,
      eventually_nhdsWithin_of_eventually_nhds hsourceRegularEventually,
      eventually_nhdsWithin_of_eventually_nhds htargetRegularEventually,
      hhiddenNonzero,
      eventually_nhdsWithin_of_eventually_nhds hfirstReverseEventually,
      eventually_nhdsWithin_of_eventually_nhds hsecondReverseEventually]
      with t hsourceAnalytic htargetAnalytic hhiddenDifferentiable
        hreciprocalAnalyticAt hreciprocalEqAt hinner houter
        hfirstFiniteAt hsecondFiniteAt hfirstInfinityAt hsecondInfinityAt
        hsourceRegularAt htargetRegularAt hhiddenNonzeroAt
        hfirstReverseAt hsecondReverseAt
    exact {
      sourceDisplacement_analytic := hsourceAnalytic
      endpointDisplacement_analytic := htargetAnalytic
      hidden_differentiable := hhiddenDifferentiable
      reciprocal_analytic := hreciprocalAnalyticAt
      reciprocal_eq := hreciprocalEqAt
      inner_julia := hinner
      outer_julia := houter.symm
      firstFinite_derivative := hfirstFiniteAt
      secondFinite_derivative := hsecondFiniteAt
      firstInfinity_derivative := hfirstInfinityAt
      secondInfinity_derivative := hsecondInfinityAt
      source_regular := hsourceRegularAt
      target_regular := htargetRegularAt
      hidden_nonzero := hhiddenNonzeroAt
      first_reverse_nonzero := hfirstReverseAt
      second_reverse_nonzero := hsecondReverseAt }
  rw [hcenter] at hpoint hreciprocalAnalytic hreciprocalZero
  obtain ⟨radius, hradius, hball⟩ := Metric.eventually_nhds_iff_ball.mp
    (eventually_nhdsWithin_iff.mp hpoint)
  let domain : Set ℂ := Metric.ball (0 : ℂ) radius \ {0}
  let anchor : ℂ := (radius / 2 : ℝ)
  have hpointOn : ∀ t ∈ domain,
      AbelPointData input reciprocal firstFinite secondFinite
        firstInfinity secondInfinity t := by
    intro t ht
    exact hball t ht.1 ht.2
  have hhalfPositive : 0 < radius / 2 := by positivity
  have hhalfLt : radius / 2 < radius := by linarith
  have hanchorBall : anchor ∈ Metric.ball (0 : ℂ) radius := by
    simpa [anchor, Metric.mem_ball, abs_of_pos hradius] using hhalfLt
  have hanchorNonzero : anchor ≠ 0 := by
    change ((radius / 2 : ℝ) : ℂ) ≠ 0
    exact_mod_cast ne_of_gt hhalfPositive
  have hanchor : anchor ∈ domain := ⟨hanchorBall, by simpa⟩
  have hopen : IsOpen domain :=
    Metric.isOpen_ball.sdiff isClosed_singleton
  let assembled : TwoJuliaAbelCarrier := {
    firstGenerator := input.cross.firstGenerator
    secondGenerator := input.cross.secondGenerator
    firstDegree := input.firstDegree
    secondDegree := input.secondDegree
    center := 0
    sourceCenter := input.sourceCenter
    targetCenter := input.targetCenter
    domain := domain
    anchor := anchor
    source := input.cross.sourceValue
    target := input.cross.endpointValue
    hidden := input.cross.hiddenEndpoint
    reciprocal := reciprocal
    sourceDerivative := deriv input.sourceDisplacement
    targetDerivative := deriv input.endpointDisplacement
    hiddenDerivative := deriv input.cross.hiddenEndpoint
    reciprocalDerivative := fun t ↦
      -deriv input.cross.hiddenEndpoint t /
        input.cross.hiddenEndpoint t ^ 2
    firstFiniteTime := firstFinite
    secondFiniteTime := secondFinite
    firstInfinityTime := firstInfinity
    secondInfinityTime := secondInfinity
    first_degree := input.first_degree
    second_degree := input.second_degree
    first_degree_at_least_two := input.first_degree_at_least_two
    second_degree_at_least_two := input.second_degree_at_least_two
    isOpen_domain := hopen
    isPreconnected_domain :=
      isPreconnected_complex_puncturedBall radius
    anchor_mem := hanchor
    punctured_mem := diff_mem_nhdsWithin_compl
      (Metric.ball_mem_nhds (0 : ℂ) hradius) {0}
    source_analytic := by simpa only [hcenter] using input.cross.source_analytic
    target_analytic := by simpa only [hcenter] using input.cross.endpoint_analytic
    reciprocal_analytic := hreciprocalAnalytic
    source_center := by simpa only [hcenter] using hsourceCenter
    target_center := by simpa only [hcenter] using htargetCenter
    reciprocal_zero := hreciprocalZero
    firstFinite_analytic := hfirstFiniteAnalytic
    secondFinite_analytic := hsecondFiniteAnalytic
    firstInfinity_analytic := hfirstInfinityAnalytic
    secondInfinity_analytic := hsecondInfinityAnalytic
    firstFinite_zero := hfirstFiniteZero
    secondFinite_zero := hsecondFiniteZero
    firstInfinity_zero := hfirstInfinityZero
    secondInfinity_zero := hsecondInfinityZero
    firstFinite_derivative := fun t ht => (hpointOn t ht).firstFinite_derivative
    secondFinite_derivative := fun t ht => (hpointOn t ht).secondFinite_derivative
    firstInfinity_derivative := fun t ht =>
      (hpointOn t ht).firstInfinity_derivative
    secondInfinity_derivative := fun t ht =>
      (hpointOn t ht).secondInfinity_derivative
    source_derivative := by
      intro t ht
      have hderiv :=
        (hpointOn t ht).sourceDisplacement_analytic.differentiableAt.hasDerivAt
      have hsum := (hasDerivAt_const t input.sourceCenter).add hderiv
      have hbinding :
          input.cross.sourceValue =
            fun z ↦ input.sourceCenter + input.sourceDisplacement z :=
        input.source_binding
      rw [hbinding]
      simpa only [Pi.add_apply, zero_add] using hsum
    target_derivative := by
      intro t ht
      have hderiv :=
        (hpointOn t ht).endpointDisplacement_analytic.differentiableAt.hasDerivAt
      have hsum := (hasDerivAt_const t input.targetCenter).add hderiv
      have hbinding :
          input.cross.endpointValue =
            fun z ↦ input.targetCenter + input.endpointDisplacement z :=
        input.endpoint_binding
      rw [hbinding]
      simpa only [Pi.add_apply, zero_add] using hsum
    hidden_derivative := fun t ht =>
      (hpointOn t ht).hidden_differentiable.hasDerivAt
    reciprocal_derivative := by
      intro t ht
      have hinverse :=
        (hpointOn t ht).hidden_differentiable.hasDerivAt.inv
          (hpointOn t ht).hidden_nonzero
      have hlocal : input.cross.hiddenEndpoint⁻¹ =ᶠ[𝓝 t] reciprocal := by
        filter_upwards [hopen.mem_nhds ht] with z hz
        exact (hpointOn z hz).reciprocal_eq
      have hcarried := hinverse.congr_of_eventuallyEq hlocal.symm
      exact hcarried
    reciprocal_derivative_eq := by intros; rfl
    reciprocal_eq_inverse := fun t ht => (hpointOn t ht).reciprocal_eq.symm
    inner_julia := fun t ht => (hpointOn t ht).inner_julia
    outer_julia := fun t ht => (hpointOn t ht).outer_julia
    source_regular := fun t ht => (hpointOn t ht).source_regular
    target_regular := fun t ht => (hpointOn t ht).target_regular
    hidden_nonzero := fun t ht => (hpointOn t ht).hidden_nonzero
    first_reverse_nonzero := fun t ht =>
      (hpointOn t ht).first_reverse_nonzero
    second_reverse_nonzero := fun t ht =>
      (hpointOn t ht).second_reverse_nonzero }
  have hreciprocalMeromorphicOrder :
      meromorphicOrderAt reciprocal 0 =
        ((poleOrder : ℤ) : WithTop ℤ) := by
    have hreciprocalEqZero :
        input.cross.hiddenEndpoint⁻¹ =ᶠ[𝓝[≠] (0 : ℂ)] reciprocal := by
      simpa only [hcenter] using hreciprocalEq
    have hhiddenOrderZero :
        meromorphicOrderAt input.cross.hiddenEndpoint 0 =
          ((-(poleOrder : ℤ) : ℤ) : WithTop ℤ) := by
      simpa only [hcenter] using hhiddenOrder
    calc
      meromorphicOrderAt reciprocal 0 =
          meromorphicOrderAt input.cross.hiddenEndpoint⁻¹ 0 := by
        exact (meromorphicOrderAt_congr hreciprocalEqZero).symm
      _ = ((poleOrder : ℤ) : WithTop ℤ) := by
        rw [meromorphicOrderAt_inv, hhiddenOrderZero]
        simp
  have hreciprocalOrder :
      analyticOrderAt reciprocal 0 = (poleOrder : ℕ) := by
    have hmeromorphicAnalytic := hreciprocalAnalytic.meromorphicOrderAt_eq
    rw [hreciprocalMeromorphicOrder] at hmeromorphicAnalytic
    cases horder : analyticOrderAt reciprocal 0
    · rw [horder, ENat.map_top] at hmeromorphicAnalytic
      simp at hmeromorphicAnalytic
    · rename_i order
      rw [horder, ENat.map_coe] at hmeromorphicAnalytic
      have horderNat : order = poleOrder := by
        exact_mod_cast hmeromorphicAnalytic.symm
      simp only [horder, horderNat]
  refine ⟨poleOrder, assembled, hpolePositive, rfl, rfl, rfl, rfl,
    hcenter.symm, rfl, rfl, rfl, ?_, hfirstBalance, hsecondBalance,
    hdegrees⟩
  simpa only [assembled] using hreciprocalOrder

/-- Aggregated cross-Julia-germ to Abel-carrier construction surface. -/
theorem analytic_two_flow_abel_carrier_assembly_terminal_certificate :
    ∀ input : TwoFlowRamifiedCrossCarrier,
      input.cross.center = 0 →
      ∃ (poleOrder : ℕ) (carrier : TwoJuliaAbelCarrier),
        0 < poleOrder ∧
        carrier.firstGenerator = input.cross.firstGenerator ∧
        carrier.secondGenerator = input.cross.secondGenerator ∧
        carrier.firstDegree = input.firstDegree ∧
        carrier.secondDegree = input.secondDegree ∧
        carrier.center = input.cross.center ∧
        carrier.source = input.cross.sourceValue ∧
        carrier.target = input.cross.endpointValue ∧
        carrier.hidden = input.cross.hiddenEndpoint ∧
        analyticOrderAt carrier.reciprocal carrier.center =
          (poleOrder : ℕ) ∧
        poleOrder * (input.firstDegree - 1) = input.ramificationOrder ∧
        poleOrder * (input.secondDegree - 1) = input.ramificationOrder ∧
        input.firstDegree = input.secondDegree := by
  intro input hcenter
  exact
    FormalAnalyticTwoFlowAbelCarrierAssembly.TwoFlowRamifiedCrossCarrier.exists_twoJuliaAbelCarrier
      input hcenter

end FormalAnalyticTwoFlowAbelCarrierAssembly
