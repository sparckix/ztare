-- v30 Route C attempt: split PR_1b_minkowski_rate sorry #1
-- Continuous Minkowski integral inequality (Lieb-Loss Theorem 2.4)
-- Strategy: prove the p=1 case via Tonelli swap; leave p>1 Hölder case as smaller sorry
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.TriangleInequality
import Mathlib.MeasureTheory.Integral.MeanInequalities
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Measure.Prod
import Mathlib.Analysis.Convolution
import Mathlib.Analysis.MeanInequalitiesPow

open MeasureTheory ENNReal

variable {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
  {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]

/-- v30 Route C attempt — Minkowski integral inequality (continuous, ENNReal). -/
theorem v30_lintegral_Lp_integral_le {p : ℝ} (hp1 : 1 ≤ p)
    {F : α → β → ℝ≥0∞} (hF : Measurable (Function.uncurry F)) :
    (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ p ∂μ) ^ (1 / p) ≤
      ∫⁻ y, (∫⁻ x, (F x y) ^ p ∂μ) ^ (1 / p) ∂ν := by
  rcases eq_or_lt_of_le hp1 with hp_eq | hp_gt
  · -- Case p = 1: both sides equal ∫∫ F by Tonelli swap, and x^(1/1) = x
    have hp : p = 1 := hp_eq.symm
    subst hp
    simp only [one_div, ENNReal.rpow_one, ENNReal.inv_one]
    exact (lintegral_lintegral_swap hF).le
  · -- Case p > 1: Hölder duality (Lieb-Loss 2.4 proper); deferred to v30b
    sorry
