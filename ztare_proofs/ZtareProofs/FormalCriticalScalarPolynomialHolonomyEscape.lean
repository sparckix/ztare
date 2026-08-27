import Mathlib.Analysis.Analytic.Polynomial
import ZtareProofs.FormalAnalyticContinuation
import ZtareProofs.FormalCriticalHolonomyLoop
import ZtareProofs.FormalFinitePolynomialCoverOrbitEscape

/-!
# Scalar polynomial continuation into the critical holonomy orbit

The endpoint component of an existing coordinate-aware analytic continuation
transports a local polynomial identity to every terminal chart.  Binding a
terminal chart for each natural turn to the explicit critical scalar loop
therefore derives return-root membership and contradicts the injective orbit
of any nonzero specialized polynomial.
-/

namespace FormalCriticalScalarPolynomialHolonomyEscape

open Filter Polynomial Set
open scoped Topology

open FormalAnalyticContinuation
open FormalCriticalHolonomyLoop
open FormalFinitePolynomialCoverOrbitEscape

/-- Polynomial evaluation on the endpoint represented by one continuation
chart. -/
noncomputable def endpointPolynomialValue
    (polynomial : ℂ[X]) (chart : IdentityChart) : ℂ → ℂ :=
  fun z => aeval (chart.endpoint z) polynomial

theorem endpointPolynomialValue_analyticOnNhd
    (polynomial : ℂ[X]) (chart : IdentityChart) :
    AnalyticOnNhd ℂ (endpointPolynomialValue polynomial chart) chart.domain := by
  exact chart.analytic_endpoint.aeval_polynomial polynomial

/-- Endpoint compatibility across an existing continuation edge transports
polynomial evaluation as an eventual equality. -/
theorem endpointPolynomialValue_eventuallyEq_of_edge
    {left right : IdentityChart} (edge : IdentityEdge left right)
    (polynomial : ℂ[X]) :
    endpointPolynomialValue polynomial right =ᶠ[𝓝 edge.point]
      endpointPolynomialValue polynomial left ∘ edge.transition := by
  filter_upwards [edge.endpoint_compatible] with z hendpoint
  simp only [endpointPolynomialValue, Function.comp_apply]
  rw [hendpoint]
  rfl

/-- A polynomial identity on the endpoint germ propagates across one
coordinate-aware continuation edge by the analytic identity theorem. -/
theorem propagate_endpointPolynomial_zero_of_edge
    {left right : IdentityChart} (edge : IdentityEdge left right)
    (polynomial : ℂ[X])
    (hleft : EqOn (endpointPolynomialValue polynomial left) 0 left.domain) :
    EqOn (endpointPolynomialValue polynomial right) 0 right.domain := by
  have hnear : endpointPolynomialValue polynomial right =ᶠ[𝓝 edge.point] 0 := by
    filter_upwards [endpointPolynomialValue_eventuallyEq_of_edge edge polynomial,
      edge.transition_mem_left] with z hcompat hmem
    rw [hcompat]
    exact hleft hmem
  exact
    (endpointPolynomialValue_analyticOnNhd polynomial right).eqOn_of_preconnected_of_eventuallyEq
      analyticOnNhd_const right.isPreconnected_domain edge.point_mem_right hnear

/-- A local polynomial endpoint identity propagates through every edge of an
existing finite analytic continuation chain. -/
theorem propagate_endpointPolynomial_zero
    {first last : IdentityChart}
    (continuation : IdentityContinuation first last)
    (polynomial : ℂ[X])
    (hfirst : EqOn (endpointPolynomialValue polynomial first) 0 first.domain) :
    EqOn (endpointPolynomialValue polynomial last) 0 last.domain := by
  induction continuation with
  | refl => exact hfirst
  | step edge tail inductionHypothesis =>
      exact inductionHypothesis
        (propagate_endpointPolynomial_zero_of_edge edge polynomial hfirst)

/-- The terminal endpoint of a continued local polynomial identity is a root.
Return-root membership is a conclusion, not carrier data. -/
theorem terminal_endpoint_isRoot
    {first last : IdentityChart}
    (continuation : IdentityContinuation first last)
    (polynomial : ℂ[X])
    (hfirst : EqOn (endpointPolynomialValue polynomial first) 0 first.domain) :
    polynomial.IsRoot (last.endpoint last.center) := by
  have hterminal :=
    propagate_endpointPolynomial_zero continuation polynomial hfirst
      last.center_mem
  rw [Polynomial.IsRoot.def]
  simpa [endpointPolynomialValue, Polynomial.aeval_def] using hterminal

/-- A nonzero local polynomial identity cannot continue to return charts
whose terminal endpoints are all the explicit injective critical-loop
endpoints. -/
theorem no_critical_holonomy_loop_of_continued_polynomial_identity
    (realization : CriticalLoopRealization)
    (initial : ℂ) (hinitial : initial ≠ 0)
    (polynomial : ℂ[X]) (hpolynomial : polynomial ≠ 0)
    (first : IdentityChart) (returnChart : ℕ → IdentityChart)
    (continuation : ∀ order : ℕ,
      IdentityContinuation first (returnChart order))
    (hfirst : EqOn
      (endpointPolynomialValue polynomial first) 0 first.domain)
    (return_endpoint : ∀ order : ℕ,
      (returnChart order).endpoint (returnChart order).center =
        realization.carrier.continuedValue initial
          ((order : ℝ) * (2 * Real.pi))) :
    False := by
  have horbit := realization.explicit_critical_orbit initial hinitial
  let endpoint : ℕ → ℂ := fun order =>
    realization.carrier.continuedValue initial
      ((order : ℝ) * (2 * Real.pi))
  have hroot : ∀ order : ℕ, polynomial.IsRoot (endpoint order) := by
    intro order
    have hterminal :=
      terminal_endpoint_isRoot (continuation order) polynomial hfirst
    simpa only [endpoint, return_endpoint order] using hterminal
  exact no_injective_orbit_over_finite_polynomial_cover
    (sheetIndex := Unit) (fun _ => polynomial) endpoint horbit.2.2
    (fun _ => ()) (fun _ => hpolynomial) (fun order => by simpa using hroot order)

/-- Aggregated scalar polynomial/critical-holonomy composition. -/
theorem critical_scalar_polynomial_holonomy_escape_terminal_certificate
    (realization : CriticalLoopRealization)
    (initial : ℂ) (hinitial : initial ≠ 0)
    (polynomial : ℂ[X]) (hpolynomial : polynomial ≠ 0)
    (first : IdentityChart) (returnChart : ℕ → IdentityChart)
    (continuation : ∀ order : ℕ,
      IdentityContinuation first (returnChart order))
    (hfirst : EqOn
      (endpointPolynomialValue polynomial first) 0 first.domain)
    (return_endpoint : ∀ order : ℕ,
      (returnChart order).endpoint (returnChart order).center =
        realization.carrier.continuedValue initial
          ((order : ℝ) * (2 * Real.pi))) :
    False := by
  exact no_critical_holonomy_loop_of_continued_polynomial_identity
    realization initial hinitial polynomial hpolynomial first returnChart
      continuation hfirst return_endpoint

end FormalCriticalScalarPolynomialHolonomyEscape
