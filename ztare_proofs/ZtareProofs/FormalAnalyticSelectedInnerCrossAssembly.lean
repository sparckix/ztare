import Mathlib.Tactic
import ZtareProofs.FormalAnalyticContinuation
import ZtareProofs.FormalAnalyticTwoFlowRamifiedBalance
import ZtareProofs.FormalPolynomialMeromorphicOrder

/-!
# A selected inner Julia continuation reconstructs the outer Julia row

A cross-Julia eliminant and one continued factor identity already determine
the second factor identity.  The cancellation factor is the first generator
evaluated on a positive-order analytic source germ; its exact polynomial
substitution order makes it eventually nonzero.

The selected-continuation input contains a finite chain of analytic identity
charts.  It contains neither the outer Julia row nor a completed
`TwoFlowRamifiedCrossCarrier`.
-/

namespace FormalAnalyticSelectedInnerCrossAssembly

open Filter Polynomial Set
open scoped Topology

open FormalAnalyticContinuation
open FormalAnalyticCrossJuliaMeromorphic
open FormalAnalyticPuncturedExtension
open FormalAnalyticTwoFlowRamifiedBalance
open FormalPolynomialMeromorphicOrder

/-- Ramified source/target data around one analytic cross-Julia carrier,
before either parameterized Julia row is attached. -/
structure RamifiedCrossFrame where
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
  source_binding :
    cross.sourceValue = fun t ↦ sourceCenter + sourceDisplacement t
  endpoint_binding :
    cross.endpointValue = fun t ↦ targetCenter + endpointDisplacement t

/-- A selected continuation of the inner factor's Julia identity to the
punctured terminal chart.  The two derivative bindings are chain rules for
the hidden factor and the complete endpoint. -/
structure SelectedInnerJuliaContinuation (frame : RamifiedCrossFrame) where
  firstChart : IdentityChart
  terminalChart : IdentityChart
  continuation : IdentityContinuation firstChart terminalChart
  initial_julia :
    EqOn (juliaResidual frame.cross.firstGenerator firstChart) 0
      firstChart.domain
  terminal_punctured_mem :
    terminalChart.domain ∈ 𝓝[≠] frame.cross.center
  terminal_base_binding :
    terminalChart.base =ᶠ[𝓝[≠] frame.cross.center]
      frame.cross.sourceValue
  terminal_hidden_binding :
    terminalChart.endpoint =ᶠ[𝓝[≠] frame.cross.center]
      frame.cross.hiddenEndpoint
  hidden_derivative_binding :
    (fun t ↦ deriv frame.cross.hiddenEndpoint t) =ᶠ[
        𝓝[≠] frame.cross.center]
      (fun t ↦ terminalChart.derivativeFactor t *
        deriv frame.sourceDisplacement t)
  endpoint_derivative_binding :
    (fun t ↦ deriv frame.endpointDisplacement t) =ᶠ[
        𝓝[≠] frame.cross.center]
      (fun t ↦ frame.cross.endpointDerivative t *
        deriv frame.sourceDisplacement t)
  no_finite_extension :
    ¬HasFiniteAnalyticExtension frame.cross.hiddenEndpoint frame.cross.center

/-- Polynomial evaluation on the positive-order analytic source germ is
eventually nonzero.  Root multiplicity may be arbitrary. -/
theorem RamifiedCrossFrame.firstGenerator_source_eventually_ne_zero
    (frame : RamifiedCrossFrame) :
    ∀ᶠ t in 𝓝[≠] frame.cross.center,
      frame.cross.firstGenerator.eval (frame.cross.sourceValue t) ≠ 0 := by
  have horderRaw :=
    meromorphicOrderAt_polynomial_eval_at_finite_center
      frame.cross.firstGenerator frame.first_nonzero frame.sourceCenter
      frame.sourceDisplacement frame.cross.center frame.ramificationOrder
      frame.source_analytic frame.source_zero frame.source_order
  have horder :
      meromorphicOrderAt
          (fun t ↦ frame.cross.firstGenerator.eval
            (frame.cross.sourceValue t))
          frame.cross.center =
        (((frame.ramificationOrder *
          frame.cross.firstGenerator.rootMultiplicity frame.sourceCenter : ℕ) : ℤ) :
          WithTop ℤ) := by
    rw [frame.source_binding]
    exact horderRaw
  have hmeromorphic :
      MeromorphicAt
        (fun t ↦ frame.cross.firstGenerator.eval
          (frame.cross.sourceValue t))
        frame.cross.center :=
    meromorphicAt_eval_polynomial frame.cross.source_analytic.meromorphicAt
      frame.cross.firstGenerator
  apply (meromorphicOrderAt_ne_top_iff_eventually_ne_zero hmeromorphic).mp
  rw [horder]
  exact WithTop.coe_ne_top

/-- Pointwise algebra: the cross eliminant, inner Julia row, and complete
endpoint chain rule force the outer Julia row after one cancellable source
factor. -/
theorem outer_julia_of_cross_and_inner
    (firstGenerator secondGenerator : ℂ[X])
    (source hidden endpoint sourceDerivative hiddenDerivative
      endpointDerivative spatialDerivative : ℂ)
    (hcross :
      secondGenerator.eval endpoint * firstGenerator.eval hidden =
        spatialDerivative * firstGenerator.eval source *
          secondGenerator.eval hidden)
    (hinner :
      hiddenDerivative * firstGenerator.eval source =
        sourceDerivative * firstGenerator.eval hidden)
    (hendpointDerivative :
      endpointDerivative = spatialDerivative * sourceDerivative)
    (hsourceNonzero : firstGenerator.eval source ≠ 0) :
    endpointDerivative * secondGenerator.eval hidden =
      hiddenDerivative * secondGenerator.eval endpoint := by
  apply mul_left_cancel₀ hsourceNonzero
  calc
    firstGenerator.eval source *
          (endpointDerivative * secondGenerator.eval hidden) =
        firstGenerator.eval source *
          ((spatialDerivative * sourceDerivative) *
            secondGenerator.eval hidden) := by rw [hendpointDerivative]
    _ = sourceDerivative *
          (spatialDerivative * firstGenerator.eval source *
            secondGenerator.eval hidden) := by ring
    _ = sourceDerivative *
          (secondGenerator.eval endpoint *
            firstGenerator.eval hidden) := by rw [← hcross]
    _ = (sourceDerivative * firstGenerator.eval hidden) *
          secondGenerator.eval endpoint := by ring
    _ = (hiddenDerivative * firstGenerator.eval source) *
          secondGenerator.eval endpoint := by rw [← hinner]
    _ = firstGenerator.eval source *
          (hiddenDerivative * secondGenerator.eval endpoint) := by ring

/-- Identity transport through the selected chart chain gives the
parameterized inner Julia row on the punctured terminal germ. -/
theorem SelectedInnerJuliaContinuation.inner_julia
    {frame : RamifiedCrossFrame}
    (selected : SelectedInnerJuliaContinuation frame) :
    (fun t ↦ deriv frame.cross.hiddenEndpoint t *
      frame.cross.firstGenerator.eval (frame.cross.sourceValue t)) =ᶠ[
        𝓝[≠] frame.cross.center]
      (fun t ↦ deriv frame.sourceDisplacement t *
        frame.cross.firstGenerator.eval (frame.cross.hiddenEndpoint t)) := by
  have hterminal := selected.continuation.propagate_julia
    frame.cross.firstGenerator selected.initial_julia
  filter_upwards [selected.terminal_punctured_mem,
      selected.terminal_base_binding, selected.terminal_hidden_binding,
      selected.hidden_derivative_binding] with t htDomain hbase hhidden
      hhiddenDerivative
  have hzero := hterminal htDomain
  have hjulia :
      frame.cross.firstGenerator.eval (selected.terminalChart.endpoint t) =
        selected.terminalChart.derivativeFactor t *
          frame.cross.firstGenerator.eval
            (selected.terminalChart.base t) := by
    exact sub_eq_zero.mp (by simpa [juliaResidual] using hzero)
  rw [hbase, hhidden] at hjulia
  rw [hhiddenDerivative, hjulia]
  ring

/-- The outer parameterized Julia row is reconstructed; it is absent from
the selected-continuation input. -/
theorem SelectedInnerJuliaContinuation.outer_julia
    {frame : RamifiedCrossFrame}
    (selected : SelectedInnerJuliaContinuation frame) :
    (fun t ↦ deriv frame.endpointDisplacement t *
      frame.cross.secondGenerator.eval (frame.cross.hiddenEndpoint t)) =ᶠ[
        𝓝[≠] frame.cross.center]
      (fun t ↦ deriv frame.cross.hiddenEndpoint t *
        frame.cross.secondGenerator.eval (frame.cross.endpointValue t)) := by
  filter_upwards [frame.cross.cross_identity, selected.inner_julia,
      selected.endpoint_derivative_binding,
      frame.firstGenerator_source_eventually_ne_zero] with t hcross hinner
      hendpointDerivative hsourceNonzero
  exact outer_julia_of_cross_and_inner frame.cross.firstGenerator
    frame.cross.secondGenerator (frame.cross.sourceValue t)
    (frame.cross.hiddenEndpoint t) (frame.cross.endpointValue t)
    (deriv frame.sourceDisplacement t)
    (deriv frame.cross.hiddenEndpoint t)
    (deriv frame.endpointDisplacement t)
    (frame.cross.endpointDerivative t) hcross hinner
    hendpointDerivative hsourceNonzero

/-- Construct the established two-row carrier from a selected continuation
of only the inner Julia identity. -/
def SelectedInnerJuliaContinuation.toTwoFlowRamifiedCrossCarrier
    {frame : RamifiedCrossFrame}
    (selected : SelectedInnerJuliaContinuation frame) :
    TwoFlowRamifiedCrossCarrier where
  cross := frame.cross
  sourceCenter := frame.sourceCenter
  targetCenter := frame.targetCenter
  ramificationOrder := frame.ramificationOrder
  sourceDisplacement := frame.sourceDisplacement
  endpointDisplacement := frame.endpointDisplacement
  firstDegree := frame.firstDegree
  secondDegree := frame.secondDegree
  first_nonzero := frame.first_nonzero
  second_nonzero := frame.second_nonzero
  first_degree := frame.first_degree
  second_degree := frame.second_degree
  first_degree_at_least_two := frame.first_degree_at_least_two
  second_degree_at_least_two := frame.second_degree_at_least_two
  ramificationOrder_positive := frame.ramificationOrder_positive
  source_analytic := frame.source_analytic
  source_zero := frame.source_zero
  source_order := frame.source_order
  endpoint_analytic := frame.endpoint_analytic
  endpoint_zero := frame.endpoint_zero
  endpoint_order := frame.endpoint_order
  source_binding := frame.source_binding
  endpoint_binding := frame.endpoint_binding
  inner_julia := selected.inner_julia
  outer_julia := selected.outer_julia
  no_finite_extension := selected.no_finite_extension

/-- Aggregated kernel surface.  Its input has one continued Julia identity;
the second row and the completed ramified cross carrier are conclusions. -/
theorem analytic_selected_inner_cross_assembly_terminal_certificate :
    ∀ (frame : RamifiedCrossFrame)
      (selected : SelectedInnerJuliaContinuation frame),
      ((fun t ↦ deriv frame.endpointDisplacement t *
        frame.cross.secondGenerator.eval
          (frame.cross.hiddenEndpoint t)) =ᶠ[
            𝓝[≠] frame.cross.center]
        (fun t ↦ deriv frame.cross.hiddenEndpoint t *
          frame.cross.secondGenerator.eval
            (frame.cross.endpointValue t))) ∧
      ∃ carrier : TwoFlowRamifiedCrossCarrier,
        carrier = selected.toTwoFlowRamifiedCrossCarrier := by
  intro frame selected
  exact ⟨selected.outer_julia,
    selected.toTwoFlowRamifiedCrossCarrier, rfl⟩

end FormalAnalyticSelectedInnerCrossAssembly
