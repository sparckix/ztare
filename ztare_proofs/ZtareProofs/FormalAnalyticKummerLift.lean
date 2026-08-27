import Mathlib.Algebra.Ring.GeomSum
import Mathlib.Analysis.Analytic.Order
import Mathlib.Tactic

/-!
# Analytic Kummer classification of a lifted power scaling

An analytic local automorphism fixing the ramification center and lifting
`z^e ↦ lambda * z^e` is multiplication by one `e`-th root of `lambda`.
The multiplier and its root equation are conclusions, not input data.
-/

namespace FormalAnalyticKummerLift

open Filter
open scoped Topology

/-- An analytic nonvanishing unit whose positive power is locally constant is
itself locally constant. The geometric-sum factor chooses the root already
present at the center, without supplying a branch of the root function. -/
theorem analytic_unit_eventuallyEq_const_of_power
    {unit : ℂ → ℂ} {center : ℂ} {order : ℕ}
    (hanalytic : AnalyticAt ℂ unit center)
    (hunit : unit center ≠ 0)
    (horder : order ≠ 0)
    (hpower : (fun z ↦ unit z ^ order) =ᶠ[𝓝 center]
      fun _ ↦ unit center ^ order) :
    unit =ᶠ[𝓝 center] fun _ ↦ unit center := by
  let ratio : ℂ → ℂ := fun z ↦ unit z / unit center
  have hratioAnalytic : AnalyticAt ℂ ratio center := by
    exact hanalytic.div analyticAt_const hunit
  have hratioCenter : ratio center = 1 := by
    simp [ratio, hunit]
  have hratioPower : (fun z ↦ ratio z ^ order) =ᶠ[𝓝 center]
      fun _ ↦ 1 := by
    filter_upwards [hpower] with z hz
    rw [show ratio z = unit z / unit center by rfl, div_pow, hz]
    exact div_self (pow_ne_zero order hunit)
  let geometricFactor : ℂ → ℂ := fun z ↦
    ∑ i ∈ Finset.range order, ratio z ^ i
  have hgeometricAnalytic : AnalyticAt ℂ geometricFactor center := by
    exact Finset.analyticAt_fun_sum _ fun i _ ↦ hratioAnalytic.pow i
  have hgeometricCenter : geometricFactor center = (order : ℂ) := by
    simp [geometricFactor, hratioCenter]
  have hgeometricCenterNe : geometricFactor center ≠ 0 := by
    rw [hgeometricCenter]
    exact Nat.cast_ne_zero.mpr horder
  have hgeometricEventuallyNe :
      ∀ᶠ z in 𝓝 center, geometricFactor z ≠ 0 :=
    hgeometricAnalytic.continuousAt.eventually_ne hgeometricCenterNe
  filter_upwards [hratioPower, hgeometricEventuallyNe] with z hz hfactor
  have hproduct :
      (ratio z - 1) * geometricFactor z = 0 := by
    rw [show geometricFactor z =
      ∑ i ∈ Finset.range order, ratio z ^ i by rfl]
    rw [mul_geom_sum, hz, sub_self]
  have hratioOne : ratio z = 1 := by
    exact sub_eq_zero.mp ((mul_eq_zero.mp hproduct).resolve_right hfactor)
  rw [show ratio z = unit z / unit center by rfl] at hratioOne
  exact (div_eq_one_iff_eq hunit).mp hratioOne

/-- A normalized analytic lift of a positive power scaling is a Kummer
multiplier. In particular, nonlinear analytic corrections cannot occur. -/
theorem exists_kummer_multiplier
    (lifted : ℂ → ℂ) (order : ℕ) (lambda : ℂ)
    (hanalytic : AnalyticAt ℂ lifted 0)
    (hzero : lifted 0 = 0)
    (hderivative : deriv lifted 0 ≠ 0)
    (horder : order ≠ 0)
    (hlambda : lambda ≠ 0)
    (hpower : (fun z ↦ lifted z ^ order) =ᶠ[𝓝 0]
      fun z ↦ lambda * z ^ order) :
    ∃ mu : ℂ,
      mu ≠ 0 ∧
      mu ^ order = lambda ∧
      lifted =ᶠ[𝓝 0] fun z ↦ mu * z := by
  have hliftedOrder : analyticOrderAt lifted 0 = 1 :=
    hanalytic.analyticOrderAt_eq_one_of_zero_deriv_ne_zero
      hzero hderivative
  obtain ⟨unit, hunitAnalytic, hunitZero, hliftedFactor⟩ :=
    hanalytic.analyticOrderAt_eq_natCast.mp hliftedOrder
  have hliftedFactor' : lifted =ᶠ[𝓝 0] fun z ↦ z * unit z := by
    filter_upwards [hliftedFactor] with z hz
    simpa only [sub_zero, pow_one, smul_eq_mul] using hz
  have hunitPowerPunctured :
      (fun z ↦ unit z ^ order) =ᶠ[𝓝[≠] 0] fun _ ↦ lambda := by
    filter_upwards [hliftedFactor'.filter_mono nhdsWithin_le_nhds,
      hpower.filter_mono nhdsWithin_le_nhds, self_mem_nhdsWithin]
      with z hzFactor hzPower hzNe
    have hz : z ≠ 0 := by simpa only [Set.mem_compl_iff, Set.mem_singleton_iff]
        using hzNe
    have hcancel : z ^ order * unit z ^ order = z ^ order * lambda := by
      rw [hzFactor, mul_pow] at hzPower
      simpa only [mul_comm lambda, mul_assoc] using hzPower
    exact mul_left_cancel₀ (pow_ne_zero order hz) hcancel
  have hunitPower :
      (fun z ↦ unit z ^ order) =ᶠ[𝓝 0] fun _ ↦ lambda := by
    exact (ContinuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
      (hunitAnalytic.pow order).continuousAt continuousAt_const).mp
        hunitPowerPunctured
  let mu : ℂ := unit 0
  have hmuPower : mu ^ order = lambda := by
    exact hunitPower.self_of_nhds
  have hmu : mu ≠ 0 := by
    intro hmuZero
    apply hlambda
    rw [← hmuPower, hmuZero, zero_pow horder]
  have hunitPowerAtMu :
      (fun z ↦ unit z ^ order) =ᶠ[𝓝 0]
        fun _ ↦ unit 0 ^ order := by
    filter_upwards [hunitPower] with z hz
    simpa only [mu, hmuPower] using hz
  have hunitConstant : unit =ᶠ[𝓝 0] fun _ ↦ unit 0 :=
    analytic_unit_eventuallyEq_const_of_power hunitAnalytic hmu horder
      hunitPowerAtMu
  refine ⟨mu, hmu, hmuPower, ?_⟩
  filter_upwards [hliftedFactor', hunitConstant] with z hz hu
  rw [hz, hu]
  exact mul_comm z mu

/-- Aggregated theorem used by formal-coverage consumers. -/
theorem analytic_kummer_lift_terminal_certificate :
    ∀ (lifted : ℂ → ℂ) (order : ℕ) (lambda : ℂ),
      AnalyticAt ℂ lifted 0 →
      lifted 0 = 0 →
      deriv lifted 0 ≠ 0 →
      order ≠ 0 →
      lambda ≠ 0 →
      ((fun z ↦ lifted z ^ order) =ᶠ[𝓝 0]
        fun z ↦ lambda * z ^ order) →
      ∃ mu : ℂ,
        mu ≠ 0 ∧
        mu ^ order = lambda ∧
        lifted =ᶠ[𝓝 0] fun z ↦ mu * z := by
  exact exists_kummer_multiplier

end FormalAnalyticKummerLift
