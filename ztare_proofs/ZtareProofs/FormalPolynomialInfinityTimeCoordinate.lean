import Mathlib.Algebra.Polynomial.Reverse
import Mathlib.Analysis.Analytic.Order
import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Complex.HasPrimitives
import Mathlib.Tactic

/-!
# Analytic time coordinate of a polynomial vector field at infinity

For a polynomial of exact degree at least two, the reciprocal time
integrand is analytic at zero with order `degree - 2`.  A normalized local
primitive therefore has exact order `degree - 1`.
-/

namespace FormalPolynomialInfinityTimeCoordinate

open Filter Metric Polynomial Set
open scoped Topology

/-- The reciprocal-coordinate differential `dt/dz` for `x' = p(x)` and
`z = 1/x`. -/
noncomputable def reciprocalTimeIntegrand
    (p : ℂ[X]) (degree : ℕ) : ℂ → ℂ :=
  fun z ↦ z ^ (degree - 2) * (-(p.reverse.eval z)⁻¹)

/-- The reciprocal time integrand is analytic at infinity's reciprocal
origin. -/
theorem reciprocalTimeIntegrand_analyticAt
    {p : ℂ[X]} {degree : ℕ}
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree) :
    AnalyticAt ℂ (reciprocalTimeIntegrand p degree) 0 := by
  have hp : p ≠ 0 := by
    intro hpzero
    simp [hpzero] at hdegree
    omega
  have hleading : p.leadingCoeff ≠ 0 := leadingCoeff_ne_zero.mpr hp
  have hreverseZero : p.reverse.eval 0 ≠ 0 := by
    simpa only [← Polynomial.coeff_zero_eq_eval_zero,
      Polynomial.coeff_zero_reverse] using hleading
  have hreverseAnalytic :
      AnalyticAt ℂ (fun z : ℂ ↦ p.reverse.eval z) 0 :=
    (AnalyticOnNhd.eval_polynomial p.reverse) 0 (by simp)
  exact (analyticAt_id.pow (degree - 2)).mul
    (hreverseAnalytic.inv hreverseZero).neg

/-- The reciprocal time integrand has the exact zero order dictated by the
polynomial degree. -/
theorem reciprocalTimeIntegrand_analyticOrderAt
    {p : ℂ[X]} {degree : ℕ}
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree) :
    analyticOrderAt (reciprocalTimeIntegrand p degree) 0 =
      (degree - 2 : ℕ) := by
  have hp : p ≠ 0 := by
    intro hpzero
    simp [hpzero] at hdegree
    omega
  have hleading : p.leadingCoeff ≠ 0 := leadingCoeff_ne_zero.mpr hp
  have hreverseZero : p.reverse.eval 0 ≠ 0 := by
    simpa only [← Polynomial.coeff_zero_eq_eval_zero,
      Polynomial.coeff_zero_reverse] using hleading
  let unit : ℂ → ℂ := fun z ↦ -(p.reverse.eval z)⁻¹
  have hreverseAnalytic :
      AnalyticAt ℂ (fun z : ℂ ↦ p.reverse.eval z) 0 :=
    (AnalyticOnNhd.eval_polynomial p.reverse) 0 (by simp)
  have hunitAnalytic : AnalyticAt ℂ unit 0 := by
    exact (hreverseAnalytic.inv hreverseZero).neg
  have hunitZero : unit 0 ≠ 0 := by
    simp [unit, hreverseZero]
  rw [(reciprocalTimeIntegrand_analyticAt hdegree htwo).analyticOrderAt_eq_natCast]
  exact ⟨unit, hunitAnalytic, hunitZero, by
    filter_upwards [] with z
    simp [reciprocalTimeIntegrand, unit]⟩

/-- A polynomial of exact degree `d >= 2` has a normalized analytic infinity
time coordinate of exact order `d - 1`. -/
theorem polynomial_infinity_time_coordinate_terminal_certificate :
    ∀ (p : ℂ[X]) (degree : ℕ),
      p.natDegree = degree →
      2 ≤ degree →
      ∃ timeCoordinate : ℂ → ℂ,
        AnalyticAt ℂ timeCoordinate 0 ∧
        timeCoordinate 0 = 0 ∧
        (∀ᶠ z in 𝓝 0,
          HasDerivAt timeCoordinate
            (reciprocalTimeIntegrand p degree z) z) ∧
        analyticOrderAt timeCoordinate 0 = (degree - 1 : ℕ) ∧
        degree - 1 ≠ 0 := by
  intro p degree hdegree htwo
  have hintegrandAnalytic :=
    reciprocalTimeIntegrand_analyticAt hdegree htwo
  obtain ⟨radius, hradius, hball⟩ :=
    Metric.eventually_nhds_iff_ball.mp
      hintegrandAnalytic.eventually_analyticAt
  have hdifferentiableOn :
      DifferentiableOn ℂ (reciprocalTimeIntegrand p degree)
        (ball 0 radius) := by
    intro z hz
    exact (hball z hz).differentiableAt.differentiableWithinAt
  obtain ⟨timeCoordinate, htimeZero, hderivative⟩ :=
    hdifferentiableOn.isExactOn_ball.with_val_at 0 0
  have hballNhd : ball (0 : ℂ) radius ∈ 𝓝 0 :=
    isOpen_ball.mem_nhds (mem_ball_self hradius)
  have htimeAnalytic : AnalyticAt ℂ timeCoordinate 0 := by
    have htimeDifferentiableOn :
        DifferentiableOn ℂ timeCoordinate (ball 0 radius) := by
      intro z hz
      exact (hderivative z hz).differentiableAt.differentiableWithinAt
    exact htimeDifferentiableOn.analyticAt hballNhd
  have hderivativeEventually :
      ∀ᶠ z in 𝓝 0,
        HasDerivAt timeCoordinate
          (reciprocalTimeIntegrand p degree z) z := by
    filter_upwards [hballNhd] with z hz
    exact hderivative z hz
  have hderivEq :
      deriv timeCoordinate =ᶠ[𝓝 0]
        reciprocalTimeIntegrand p degree := by
    filter_upwards [hderivativeEventually] with z hz
    exact hz.deriv
  have hderivOrder : analyticOrderAt (deriv timeCoordinate) 0 =
      (degree - 2 : ℕ) := by
    rw [analyticOrderAt_congr hderivEq]
    exact reciprocalTimeIntegrand_analyticOrderAt hdegree htwo
  have htimeOrder : analyticOrderAt timeCoordinate 0 =
      (degree - 1 : ℕ) := by
    have horderIdentity := htimeAnalytic.analyticOrderAt_deriv_add_one
    rw [hderivOrder] at horderIdentity
    have hsub : (fun z ↦ timeCoordinate z - timeCoordinate 0) =
        timeCoordinate := by
      funext z
      simp [htimeZero]
    rw [hsub] at horderIdentity
    calc
      analyticOrderAt timeCoordinate 0 =
          ((degree - 2 : ℕ) : ℕ∞) + 1 := horderIdentity.symm
      _ = ((degree - 1 : ℕ) : ℕ∞) := by
        rw [← ENat.coe_one, ← ENat.coe_add]
        congr 1
        omega
  exact ⟨timeCoordinate, htimeAnalytic, htimeZero,
    hderivativeEventually, htimeOrder, by omega⟩

end FormalPolynomialInfinityTimeCoordinate
