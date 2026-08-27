import Mathlib.Analysis.Analytic.Order
import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Complex.HasPrimitives
import Mathlib.Tactic

/-!
# Analytic time coordinate at a regular point of a polynomial vector field

At a point where a polynomial vector field does not vanish, the Abel
integrand `1 / p` is analytic.  Its normalized local primitive has derivative
`1 / p` and exact analytic order one.
-/

namespace FormalPolynomialFiniteTimeCoordinate

open Filter Metric Polynomial Set
open scoped Topology

/-- The finite-chart differential `dt/dx` for `x' = p(x)`. -/
noncomputable def finiteTimeIntegrand (p : ℂ[X]) : ℂ → ℂ :=
  fun x ↦ (p.eval x)⁻¹

/-- The finite time integrand is analytic at every regular point. -/
theorem finiteTimeIntegrand_analyticAt
    {p : ℂ[X]} {center : ℂ}
    (hregular : p.eval center ≠ 0) :
    AnalyticAt ℂ (finiteTimeIntegrand p) center := by
  have hpolynomial : AnalyticAt ℂ (fun x : ℂ ↦ p.eval x) center :=
    (AnalyticOnNhd.eval_polynomial p) center (by simp)
  exact hpolynomial.inv hregular

/-- A regular point of a polynomial vector field has a normalized analytic
finite time coordinate of exact order one. -/
theorem polynomial_finite_time_coordinate_terminal_certificate :
    ∀ (p : ℂ[X]) (center : ℂ),
      p.eval center ≠ 0 →
      ∃ timeCoordinate : ℂ → ℂ,
        AnalyticAt ℂ timeCoordinate center ∧
        timeCoordinate center = 0 ∧
        (∀ᶠ x in nhds center,
          HasDerivAt timeCoordinate (finiteTimeIntegrand p x) x) ∧
        deriv timeCoordinate center = (p.eval center)⁻¹ ∧
        analyticOrderAt timeCoordinate center = (1 : ℕ) := by
  intro p center hregular
  have hintegrandAnalytic := finiteTimeIntegrand_analyticAt hregular
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp
      hintegrandAnalytic.eventually_analyticAt
  have hdifferentiableOn :
      DifferentiableOn ℂ (finiteTimeIntegrand p) (ball center radius) := by
    intro x hx
    exact (hball x hx).differentiableAt.differentiableWithinAt
  obtain ⟨timeCoordinate, htimeZero, hderivative⟩ :=
    hdifferentiableOn.isExactOn_ball.with_val_at center 0
  have hballNhd : ball center radius ∈ nhds center :=
    isOpen_ball.mem_nhds (mem_ball_self hradius)
  have htimeAnalytic : AnalyticAt ℂ timeCoordinate center := by
    have htimeDifferentiableOn :
        DifferentiableOn ℂ timeCoordinate (ball center radius) := by
      intro x hx
      exact (hderivative x hx).differentiableAt.differentiableWithinAt
    exact htimeDifferentiableOn.analyticAt hballNhd
  have hderivativeEventually :
      ∀ᶠ x in nhds center,
        HasDerivAt timeCoordinate (finiteTimeIntegrand p x) x := by
    filter_upwards [hballNhd] with x hx
    exact hderivative x hx
  have hderivativeCenter :
      deriv timeCoordinate center = (p.eval center)⁻¹ := by
    have hhas := hderivativeEventually.self_of_nhds
    simpa only [finiteTimeIntegrand] using hhas.deriv
  have hderivativeNonzero : deriv timeCoordinate center ≠ 0 := by
    rw [hderivativeCenter]
    exact inv_ne_zero hregular
  have htimeOrder : analyticOrderAt timeCoordinate center = (1 : ℕ) :=
    htimeAnalytic.analyticOrderAt_eq_one_of_zero_deriv_ne_zero
      htimeZero hderivativeNonzero
  exact ⟨timeCoordinate, htimeAnalytic, htimeZero,
    hderivativeEventually, hderivativeCenter, htimeOrder⟩

end FormalPolynomialFiniteTimeCoordinate
