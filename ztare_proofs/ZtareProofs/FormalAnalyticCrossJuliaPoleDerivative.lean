import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticCrossJuliaPoleChart
import ZtareProofs.FormalMeromorphicPoleDerivative

/-!
# Nonvanishing derivative of a nonremovable cross-Julia pole

The hidden branch furnished by cross-Julia elimination has a positive pole
order whenever it has no finite analytic extension.  Differentiation lowers
that finite integer order by one, so the derivative is eventually nonzero on
the punctured germ.
-/

namespace FormalAnalyticCrossJuliaPoleDerivative

open Filter
open scoped Topology
open FormalAnalyticCrossJuliaMeromorphic
open FormalAnalyticCrossJuliaPoleChart
open FormalAnalyticPuncturedExtension
open FormalMeromorphicPoleDerivative

/-- The derivative of a nonremovable cross-Julia hidden branch is nonzero on
a sufficiently small punctured neighborhood. -/
theorem AnalyticCrossJuliaCarrier.hiddenEndpoint_deriv_eventually_ne_zero
    (carrier : AnalyticCrossJuliaCarrier)
    (hnoExtension :
      ¬HasFiniteAnalyticExtension carrier.hiddenEndpoint carrier.center) :
    ∀ᶠ t in 𝓝[≠] carrier.center,
      deriv carrier.hiddenEndpoint t ≠ 0 := by
  obtain ⟨poleOrder, hpolePositive, hpoleOrder, _hreciprocal⟩ :=
    FormalAnalyticCrossJuliaPoleChart.AnalyticCrossJuliaCarrier.exists_poleOrder_reciprocalChart
      carrier hnoExtension
  have hderivativeOrder := meromorphicOrderAt_deriv_of_pole
    carrier.hiddenEndpoint carrier.center poleOrder
    carrier.hiddenEndpoint_meromorphicAt hpolePositive hpoleOrder
  have hfiniteDerivativeOrder :
      meromorphicOrderAt (deriv carrier.hiddenEndpoint) carrier.center ≠ ⊤ := by
    rw [hderivativeOrder]
    simp
  exact (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
    carrier.hiddenEndpoint_meromorphicAt.deriv).mp hfiniteDerivativeOrder

/-- Any carried derivative value agreeing with the analytic derivative on the
punctured germ inherits nonvanishing. -/
theorem AnalyticCrossJuliaCarrier.hiddenDerivative_eventually_ne_zero
    (carrier : AnalyticCrossJuliaCarrier)
    (hiddenDerivative : ℂ → ℂ)
    (hnoExtension :
      ¬HasFiniteAnalyticExtension carrier.hiddenEndpoint carrier.center)
    (hderivative : ∀ᶠ t in 𝓝[≠] carrier.center,
      HasDerivAt carrier.hiddenEndpoint (hiddenDerivative t) t) :
    ∀ᶠ t in 𝓝[≠] carrier.center, hiddenDerivative t ≠ 0 := by
  filter_upwards [
      AnalyticCrossJuliaCarrier.hiddenEndpoint_deriv_eventually_ne_zero
        carrier hnoExtension,
      hderivative] with t hnonzero hderivativeAt
  rw [← hderivativeAt.deriv]
  exact hnonzero

/-- Aggregated pole-derivative surface. -/
theorem analytic_cross_julia_pole_derivative_terminal_certificate :
    ∀ (carrier : AnalyticCrossJuliaCarrier),
      (¬HasFiniteAnalyticExtension carrier.hiddenEndpoint carrier.center) →
      ∀ᶠ t in 𝓝[≠] carrier.center,
        deriv carrier.hiddenEndpoint t ≠ 0 := by
  intro carrier hnoExtension
  exact AnalyticCrossJuliaCarrier.hiddenEndpoint_deriv_eventually_ne_zero
    carrier hnoExtension

end FormalAnalyticCrossJuliaPoleDerivative
