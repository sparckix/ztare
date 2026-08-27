import Mathlib.Analysis.Analytic.Order
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticTaylorAlgebra
import ZtareProofs.FormalPolynomialFlowAtInfinity
import ZtareProofs.FormalPolynomialInfinityTimeCoordinate

/-!
# Canonical Taylor series of polynomial Abel coordinates

For a monic polynomial generator, the analytic reciprocal-time integrand and
its zero-normalized primitive have exactly the formal series used by the
all-order polynomial infinity-collision calculation.
-/

namespace FormalAnalyticPolynomialTimeTaylor

open Filter Polynomial PowerSeries
open scoped Topology

open FormalAnalyticTaylorAlgebra
open FormalPolynomialFlowAtInfinity
open FormalPolynomialInfinityTimeCoordinate

/-- Analytic vanishing order is the order of the canonical scalar Taylor
power series. -/
theorem order_taylorPowerSeries_eq_analyticOrderAt
    {f : ℂ → ℂ} {center : ℂ} (hf : AnalyticAt ℂ f center) :
    PowerSeries.order (taylorPowerSeries f center) =
      analyticOrderAt f center := by
  apply ENat.eq_of_forall_natCast_le_iff
  intro n
  rw [natCast_le_analyticOrderAt_iff_iteratedDeriv_eq_zero hf]
  constructor
  · intro hn i hi
    have hilt : ((i : ℕ) : ℕ∞) < (n : ℕ∞) := by
      exact_mod_cast hi
    have hcoeff := PowerSeries.coeff_of_lt_order
      (φ := taylorPowerSeries f center) i (lt_of_lt_of_le hilt hn)
    rw [coeff_taylorPowerSeries] at hcoeff
    have hfactorial : ((i.factorial : ℕ) : ℂ) ≠ 0 := by
      exact_mod_cast Nat.factorial_ne_zero i
    simpa [hfactorial] using hcoeff
  · intro hderivatives
    apply PowerSeries.nat_le_order
    intro i hi
    rw [coeff_taylorPowerSeries, hderivatives i hi]
    simp

/-- Polynomial reversal, interpreted as a power series, is the reciprocal
denominator of the exact natural degree. -/
theorem reverse_toPowerSeries_eq_reciprocalDenominator
    (p : ℂ[X]) (degree : ℕ) (hdegree : p.natDegree = degree) :
    (p.reverse : ℂ⟦X⟧) = reciprocalDenominator degree p := by
  apply PowerSeries.ext
  intro n
  rw [Polynomial.coeff_coe, coeff_reciprocalDenominator]
  by_cases hn : n ≤ degree
  · rw [if_pos hn, Polynomial.coeff_reverse, hdegree,
      Polynomial.revAt_le hn]
  · rw [if_neg hn]
    apply Polynomial.coeff_eq_zero_of_natDegree_lt
    apply lt_of_le_of_lt (Polynomial.reverse_natDegree_le p)
    rw [hdegree]
    exact Nat.lt_of_not_ge hn

/-- The Taylor series of the reversed-polynomial evaluation is its formal
reciprocal denominator. -/
theorem taylorPowerSeries_reverse_eval
    (p : ℂ[X]) (degree : ℕ) (hdegree : p.natDegree = degree) :
    taylorPowerSeries (fun z : ℂ ↦ p.reverse.eval z) 0 =
      reciprocalDenominator degree p := by
  change taylorPowerSeries
    (fun z : ℂ ↦ Polynomial.aeval z p.reverse) 0 = _
  have hseries := taylorPowerSeries_aeval_polynomial
    (f := fun z : ℂ ↦ z) (center := 0) analyticAt_id p.reverse
  rw [hseries, taylorPowerSeries_id_zero]
  calc
    Polynomial.aeval (PowerSeries.X : ℂ⟦X⟧) p.reverse =
        (p.reverse : ℂ⟦X⟧) := by
      simpa [Polynomial.aeval_def] using
        (Polynomial.eval₂_C_X_eq_coe (φ := p.reverse))
    _ = reciprocalDenominator degree p :=
      reverse_toPowerSeries_eq_reciprocalDenominator p degree hdegree

/-- The analytic reciprocal-time integrand has the signed formal Laurent-end
series dictated by polynomial reversal. -/
theorem taylorPowerSeries_reciprocalTimeIntegrand
    (p : ℂ[X]) (degree : ℕ)
    (hmonic : p.IsMonicOfDegree degree) (_htwo : 2 ≤ degree) :
    taylorPowerSeries (reciprocalTimeIntegrand p degree) 0 =
      -((PowerSeries.X : ℂ⟦X⟧) ^ (degree - 2) *
        (reciprocalDenominator degree p)⁻¹) := by
  have hdegree : p.natDegree = degree := hmonic.natDegree_eq
  have hreverseAnalytic :
      AnalyticAt ℂ (fun z : ℂ ↦ p.reverse.eval z) 0 :=
    (AnalyticOnNhd.eval_polynomial p.reverse) 0 (by simp)
  have hreverseZero : p.reverse.eval 0 ≠ 0 := by
    rw [← Polynomial.coeff_zero_eq_eval_zero,
      Polynomial.coeff_zero_reverse, hmonic.leadingCoeff_eq]
    norm_num
  have hpowerAnalytic :
      AnalyticAt ℂ (fun z : ℂ ↦ z ^ (degree - 2)) 0 :=
    analyticAt_id.pow (degree - 2)
  have hinverseAnalytic :
      AnalyticAt ℂ (fun z : ℂ ↦ (p.reverse.eval z)⁻¹) 0 :=
    hreverseAnalytic.inv hreverseZero
  have hnegativeInverseAnalytic :
      AnalyticAt ℂ (fun z : ℂ ↦ -(p.reverse.eval z)⁻¹) 0 :=
    hinverseAnalytic.neg
  change taylorPowerSeries
      (fun z : ℂ ↦ z ^ (degree - 2) * (-(p.reverse.eval z)⁻¹)) 0 = _
  change taylorPowerSeries
      ((fun z : ℂ ↦ z ^ (degree - 2)) *
        (fun z : ℂ ↦ -(p.reverse.eval z)⁻¹)) 0 = _
  have hpowerSeries := taylorPowerSeries_pow
    (f := fun z : ℂ ↦ z) (center := 0) analyticAt_id (degree - 2)
  rw [taylorPowerSeries_mul hpowerAnalytic hnegativeInverseAnalytic,
    hpowerSeries, taylorPowerSeries_id_zero,
    show taylorPowerSeries (fun z : ℂ ↦ -(p.reverse.eval z)⁻¹) 0 =
        -taylorPowerSeries (fun z : ℂ ↦ (p.reverse.eval z)⁻¹) 0 by
      exact taylorPowerSeries_neg _ _,
    taylorPowerSeries_inv hreverseAnalytic hreverseZero,
    taylorPowerSeries_reverse_eval p degree hdegree]
  ring

private theorem derivative_zeroConstantPrimitive (series : ℂ⟦X⟧) :
    d⁄dX ℂ (zeroConstantPrimitive series) = series := by
  apply PowerSeries.ext
  intro n
  rw [PowerSeries.coeff_derivative,
    coeff_succ_zeroConstantPrimitive]
  have hcast : (((n + 1 : ℕ) : ℂ)) ≠ 0 := by
    exact_mod_cast Nat.succ_ne_zero n
  field_simp

private theorem powerSeries_eq_of_derivative_eq_constantCoeff_eq
    {left right : ℂ⟦X⟧}
    (hderivative : d⁄dX ℂ left = d⁄dX ℂ right)
    (hconstant : PowerSeries.constantCoeff left =
      PowerSeries.constantCoeff right) :
    left = right := by
  apply PowerSeries.ext
  intro n
  cases n with
  | zero =>
      simpa only [PowerSeries.coeff_zero_eq_constantCoeff] using hconstant
  | succ n =>
      have hcoeff := congrArg (PowerSeries.coeff n) hderivative
      simp only [PowerSeries.coeff_derivative] at hcoeff
      have hcast : (((n + 1 : ℕ) : ℂ)) ≠ 0 := by
        exact_mod_cast Nat.succ_ne_zero n
      have hcast' : (n : ℂ) + 1 ≠ 0 := by
        simpa [Nat.cast_add, Nat.cast_one] using hcast
      exact mul_right_cancel₀ hcast' hcoeff

/-- Every analytic zero-normalized primitive of the reciprocal-time
integrand has the signed normalized formal time coordinate as its canonical
Taylor series. -/
theorem taylorPowerSeries_infinityTime_eq_neg_normalizedTimeCoordinate
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate : ℂ → ℂ}
    (hmonic : p.IsMonicOfDegree degree) (htwo : 2 ≤ degree)
    (htimeAnalytic : AnalyticAt ℂ timeCoordinate 0)
    (htimeZero : timeCoordinate 0 = 0)
    (htimeDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt timeCoordinate (reciprocalTimeIntegrand p degree z) z) :
    taylorPowerSeries timeCoordinate 0 =
      -normalizedTimeCoordinate degree (reciprocalDenominator degree p) := by
  have hintegrandAnalytic :
      AnalyticAt ℂ (reciprocalTimeIntegrand p degree) 0 :=
    reciprocalTimeIntegrand_analyticAt hmonic.natDegree_eq htwo
  have hderivEq : deriv timeCoordinate =ᶠ[𝓝 0]
      reciprocalTimeIntegrand p degree := by
    filter_upwards [htimeDerivative] with z hz
    exact hz.deriv
  have htaylorDeriv := taylorPowerSeries_eq_of_eventuallyEq
    htimeAnalytic.deriv hintegrandAnalytic hderivEq
  rw [taylorPowerSeries_deriv,
    taylorPowerSeries_reciprocalTimeIntegrand p degree hmonic htwo]
      at htaylorDeriv
  apply powerSeries_eq_of_derivative_eq_constantCoeff_eq
  · rw [map_neg, normalizedTimeCoordinate,
      derivative_zeroConstantPrimitive]
    exact htaylorDeriv
  · simp [constantCoeff_taylorPowerSeries, htimeZero,
      constantCoeff_normalizedTimeCoordinate]

/-- The difference of two analytic infinity-time primitives has exactly the
formal collision sign used by `monic_tangent_time_coordinate_alternative`. -/
theorem taylorPowerSeries_infinityTime_collision
    (p q : ℂ[X]) (degree : ℕ)
    {firstInfinityTime secondInfinityTime : ℂ → ℂ}
    (hp : p.IsMonicOfDegree degree)
    (hq : q.IsMonicOfDegree degree)
    (htwo : 2 ≤ degree)
    (hfirstAnalytic : AnalyticAt ℂ firstInfinityTime 0)
    (hsecondAnalytic : AnalyticAt ℂ secondInfinityTime 0)
    (hfirstZero : firstInfinityTime 0 = 0)
    (hsecondZero : secondInfinityTime 0 = 0)
    (hfirstDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt firstInfinityTime
        (reciprocalTimeIntegrand p degree z) z)
    (hsecondDerivative : ∀ᶠ z in 𝓝 0,
      HasDerivAt secondInfinityTime
        (reciprocalTimeIntegrand q degree z) z) :
    taylorPowerSeries
        (fun z ↦ secondInfinityTime z - firstInfinityTime z) 0 =
      normalizedTimeCoordinate degree (reciprocalDenominator degree p) -
        normalizedTimeCoordinate degree (reciprocalDenominator degree q) := by
  change taylorPowerSeries
      (secondInfinityTime - firstInfinityTime) 0 = _
  rw [taylorPowerSeries_sub hsecondAnalytic hfirstAnalytic,
    taylorPowerSeries_infinityTime_eq_neg_normalizedTimeCoordinate
      q degree hq htwo hsecondAnalytic hsecondZero hsecondDerivative,
    taylorPowerSeries_infinityTime_eq_neg_normalizedTimeCoordinate
      p degree hp htwo hfirstAnalytic hfirstZero hfirstDerivative]
  ring

/-- Aggregated canonical infinity-time Taylor binding. -/
theorem analytic_polynomial_time_taylor_terminal_certificate :
    (∀ (f : ℂ → ℂ) (center : ℂ),
      AnalyticAt ℂ f center →
      PowerSeries.order (taylorPowerSeries f center) =
        analyticOrderAt f center) ∧
    (∀ (p : ℂ[X]) (degree : ℕ) (timeCoordinate : ℂ → ℂ),
      p.IsMonicOfDegree degree →
      2 ≤ degree →
      AnalyticAt ℂ timeCoordinate 0 →
      timeCoordinate 0 = 0 →
      (∀ᶠ z in 𝓝 0,
        HasDerivAt timeCoordinate (reciprocalTimeIntegrand p degree z) z) →
      taylorPowerSeries timeCoordinate 0 =
        -normalizedTimeCoordinate degree (reciprocalDenominator degree p)) := by
  refine ⟨?_, ?_⟩
  · intro f center hf
    exact order_taylorPowerSeries_eq_analyticOrderAt hf
  · intro p degree timeCoordinate hmonic htwo htimeAnalytic htimeZero
      htimeDerivative
    exact taylorPowerSeries_infinityTime_eq_neg_normalizedTimeCoordinate
      p degree hmonic htwo htimeAnalytic htimeZero htimeDerivative

end FormalAnalyticPolynomialTimeTaylor
