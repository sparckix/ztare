import Mathlib.Analysis.Meromorphic.Order
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticTwoJuliaAbelCollision
import ZtareProofs.FormalMeromorphicPoleDerivative

/-!
# Hidden-derivative nonvanishing from reciprocal order

On a two-Julia uniformizer sheet, a reciprocal germ of positive finite order
has a derivative of finite order one lower.  The carried reciprocal/hidden
derivative identity then forces the hidden derivative to be nonzero on the
punctured sheet.
-/

namespace FormalAnalyticTwoJuliaDerivativeNonvanishing

open Filter
open scoped Topology
open FormalAnalyticTwoJuliaAbelCollision
open FormalMeromorphicPoleDerivative

/-- Positive reciprocal order derives the hidden-derivative cancellation
premise used by proportional Julia composition. -/
theorem TwoJuliaAbelCarrier.hiddenDerivative_eventually_ne_zero_of_reciprocal_order
    (carrier : TwoJuliaAbelCarrier)
    (ramification : ℕ) (hramification : 0 < ramification)
    (hreciprocalOrder :
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ)) :
    ∀ᶠ t in 𝓝[≠] carrier.center,
      carrier.hiddenDerivative t ≠ 0 := by
  have hmeromorphicOrder :
      meromorphicOrderAt carrier.reciprocal carrier.center =
        ((ramification : ℤ) : WithTop ℤ) := by
    rw [carrier.reciprocal_analytic.meromorphicOrderAt_eq,
      hreciprocalOrder]
    simp
  have hderivativeOrder := meromorphicOrderAt_deriv_of_positive_order
    carrier.reciprocal carrier.center ramification
    carrier.reciprocal_analytic.meromorphicAt hramification
    hmeromorphicOrder
  have hderivativeFinite :
      meromorphicOrderAt (deriv carrier.reciprocal) carrier.center ≠ ⊤ := by
    rw [hderivativeOrder]
    simp
  have hderivativeNonzero :
      ∀ᶠ t in 𝓝[≠] carrier.center,
        deriv carrier.reciprocal t ≠ 0 :=
    (meromorphicOrderAt_ne_top_iff_eventually_ne_zero
      carrier.reciprocal_analytic.meromorphicAt.deriv).mp
        hderivativeFinite
  filter_upwards [carrier.punctured_mem, hderivativeNonzero] with
      t ht hderivative
  have hcarriedDerivative : carrier.reciprocalDerivative t ≠ 0 := by
    rw [← (carrier.reciprocal_derivative t ht).deriv]
    exact hderivative
  intro hhiddenDerivative
  apply hcarriedDerivative
  rw [carrier.reciprocal_derivative_eq t ht, hhiddenDerivative]
  simp

/-- Aggregated reciprocal-to-hidden derivative surface. -/
theorem analytic_two_julia_derivative_nonvanishing_terminal_certificate :
    ∀ (carrier : TwoJuliaAbelCarrier) (ramification : ℕ),
      0 < ramification →
      analyticOrderAt carrier.reciprocal carrier.center =
        (ramification : ℕ) →
      ∀ᶠ t in 𝓝[≠] carrier.center,
        carrier.hiddenDerivative t ≠ 0 := by
  intro carrier ramification hramification hreciprocalOrder
  exact TwoJuliaAbelCarrier.hiddenDerivative_eventually_ne_zero_of_reciprocal_order
    carrier ramification hramification hreciprocalOrder

end FormalAnalyticTwoJuliaDerivativeNonvanishing
