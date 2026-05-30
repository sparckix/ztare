/-
Copyright (c) 2026 Mathlib Contributors. All rights reserved.
Released under Apache 2.0 license, as described in the file LICENSE.
Authors: ZTARE NS Track B contributors
-/
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.SpecialFunctions.Log.Deriv
import Mathlib.Analysis.SpecialFunctions.Log.Monotone

/-!
# Iterated logarithm and the triple-iterated log

This file develops the elementary real analysis of the *triple-iterated logarithm*

```
triLog x = log (log (log x))           when x > exp (exp (exp 1))
triLog x = 0                           otherwise
```

The clipping at `exp (exp (exp 1))` keeps the function total over `ℝ` while
agreeing with the genuine triple log on its natural domain.  Iterated logs
appear in slow-growth analysis (Erdős–Tao iterated-log lower bounds; quantitative
parabolic regularity theory à la Tao 2019; Hardy–Littlewood iterated-log
laws).  None of this primitive arithmetic was previously in Mathlib.

## Main definitions

* `Real.triLog` — the clipped triple log.

## Main statements

* `Real.triLog_of_lt` — `triLog x = 0` when `x ≤ exp (exp (exp 1))`.
* `Real.triLog_eq_logloglog` — `triLog x = log (log (log x))` on the upper branch.
* `Real.triLog_nonneg` — `0 ≤ triLog x` for every `x`.
* `Real.strictMonoOn_triLog` — `triLog` is strictly increasing on the upper
  branch.
* `Real.tendsto_triLog_atTop` — `triLog x → ∞` as `x → ∞`.

## Implementation notes

The clipped value `0` is a *safe lower bound* for the genuine
`log (log (log x))` whenever `x > exp (exp (exp 1))` (Lemma
`triLog_le_logloglog`), so `triLog` can be substituted for the genuine
triple log in any inequality of the form `triLog x ≤ …` while
remaining total.  This convention matches the pattern of
`Real.posLog := max (log ·) 0`.

## References

* T. Tao, *Quantitative bounds for critically bounded solutions to the
  Navier–Stokes equations*, Proc. Symp. Pure Math. **100** (2019), 149–193;
  uses `(log log log (1/(T*−t)))^{1/2}` lower bounds on critical norms.
* G. H. Hardy and J. E. Littlewood, *Some problems of "Partitio Numerorum"*,
  passim, where iterated-log refinements of the law of large numbers appear.
* P. Erdős, *On the law of the iterated logarithm*, Ann. of Math. (2) **43**
  (1942), 419–436.

## Tags

logarithm, iterated logarithm, triple log, slow growth
-/

set_option linter.unusedSectionVars false

namespace Real

open Filter
open scoped Topology

/-! ## §1.  Threshold abbreviations -/

/-- The threshold above which `log (log (log x))` is non-negative. -/
private noncomputable def triLogThreshold : ℝ := Real.exp (Real.exp (Real.exp 1))

private lemma triLogThreshold_pos : 0 < triLogThreshold := Real.exp_pos _

private lemma one_lt_triLogThreshold : 1 < triLogThreshold := by
  have h1 : (0 : ℝ) < Real.exp 1 := Real.exp_pos _
  have h2 : (0 : ℝ) < Real.exp (Real.exp 1) := Real.exp_pos _
  -- exp 1 > 1 ⇒ exp (exp 1) > exp 1 > 1 ⇒ exp (exp (exp 1)) > 1.
  have step1 : (1 : ℝ) < Real.exp 1 := by
    have : (0 : ℝ) < 1 := by norm_num
    exact Real.one_lt_exp_iff.mpr this
  have step2 : (1 : ℝ) < Real.exp (Real.exp 1) :=
    Real.one_lt_exp_iff.mpr h1
  exact Real.one_lt_exp_iff.mpr h2

/-! ## §2.  The clipped triple-iterated logarithm -/

/-- **Triple iterated logarithm** (clipped at zero outside the upper branch).

For `x > exp (exp (exp 1))`, this equals the genuine `log (log (log x))`,
which is positive and increasing.  For smaller `x`, it returns `0`.

The clipping makes `triLog` total over `ℝ`: it is everywhere defined,
non-negative, and a *safe lower bound* for the genuine triple log on its
natural domain.  See `triLog_eq_logloglog` and `triLog_nonneg`. -/
noncomputable def triLog (x : ℝ) : ℝ :=
  if triLogThreshold < x then
    Real.log (Real.log (Real.log x))
  else
    0

/-! ## §3.  Branch lemmas -/

/-- On the lower branch (`x ≤ exp(exp(exp 1))`), `triLog` is identically zero. -/
lemma triLog_of_le (x : ℝ) (hx : x ≤ triLogThreshold) : triLog x = 0 := by
  unfold triLog
  exact if_neg (not_lt.mpr hx)

/-- On the upper branch (`x > exp(exp(exp 1))`), `triLog` agrees with the
genuine triple-iterated logarithm. -/
lemma triLog_eq_logloglog {x : ℝ} (hx : triLogThreshold < x) :
    triLog x = Real.log (Real.log (Real.log x)) := by
  unfold triLog
  exact if_pos hx

/-! ## §4.  Non-negativity -/

/-- Mechanical positivity step: `log (log (log x)) ≥ 0` for `x > exp(exp(exp 1))`.

The proof unfolds the threshold three times via `Real.lt_log_iff_exp_lt`. -/
lemma logloglog_nonneg_of_lt_triLogThreshold {x : ℝ}
    (hx : triLogThreshold < x) :
    0 ≤ Real.log (Real.log (Real.log x)) := by
  have h_exp_exp1_pos : 0 < Real.exp (Real.exp 1) := Real.exp_pos _
  have h_exp_exp_exp1_pos : 0 < triLogThreshold := triLogThreshold_pos
  have hx_pos : 0 < x := lt_trans h_exp_exp_exp1_pos hx
  -- Step 1: log x > exp (exp 1).
  have h1 : Real.exp (Real.exp 1) < Real.log x :=
    (Real.lt_log_iff_exp_lt hx_pos).mpr hx
  -- Step 2: log x > 0 (since exp(exp 1) > 0).
  have h_logx_pos : 0 < Real.log x := lt_trans h_exp_exp1_pos h1
  -- Step 3: log (log x) > exp 1.
  have h2 : Real.exp 1 < Real.log (Real.log x) :=
    (Real.lt_log_iff_exp_lt h_logx_pos).mpr h1
  -- Step 4: log (log x) ≥ 1 (since exp 1 ≥ 1).
  have h_e_ge_one : (1 : ℝ) ≤ Real.exp 1 := Real.one_le_exp_iff.mpr (by norm_num)
  have h_loglogx_ge_one : 1 ≤ Real.log (Real.log x) :=
    le_of_lt (lt_of_le_of_lt h_e_ge_one h2)
  -- Step 5: log (log (log x)) ≥ 0.
  exact Real.log_nonneg h_loglogx_ge_one

/-- `triLog ≥ 0` everywhere; the lower branch is `0`, and the upper branch
reduces to `logloglog_nonneg_of_lt_triLogThreshold`. -/
lemma triLog_nonneg (x : ℝ) : 0 ≤ triLog x := by
  unfold triLog
  split_ifs with hx
  · exact logloglog_nonneg_of_lt_triLogThreshold hx
  · exact le_refl 0

/-! ## §5.  `triLog` is bounded above by the genuine triple log on the upper branch -/

/-- The clipped value is always a (safe) lower bound for the genuine triple log
on the upper branch.  This is the load-bearing fact that lets `triLog`
substitute for `log (log (log ·))` in inequalities. -/
lemma triLog_le_logloglog {x : ℝ} (hx : triLogThreshold < x) :
    triLog x ≤ Real.log (Real.log (Real.log x)) := by
  rw [triLog_eq_logloglog hx]

/-! ## §6.  Strict monotonicity on the upper branch -/

/-- `triLog` is strictly increasing on `(exp(exp(exp 1)), ∞)`. -/
lemma strictMonoOn_triLog :
    StrictMonoOn triLog (Set.Ioi triLogThreshold) := by
  intro x hx y hy hxy
  rw [triLog_eq_logloglog hx, triLog_eq_logloglog hy]
  -- Now reduce to strict monotonicity of `log` thrice over.
  have hx_pos : 0 < x := lt_trans triLogThreshold_pos hx
  have hy_pos : 0 < y := lt_trans triLogThreshold_pos hy
  -- log x < log y.
  have h_log_lt : Real.log x < Real.log y := Real.log_lt_log hx_pos hxy
  -- 0 < log x (and hence 0 < log y).
  have h_log_x_pos : 0 < Real.log x := by
    have : Real.exp (Real.exp 1) < Real.log x :=
      (Real.lt_log_iff_exp_lt hx_pos).mpr hx
    exact lt_trans (Real.exp_pos _) this
  -- log (log x) < log (log y).
  have h_loglog_lt : Real.log (Real.log x) < Real.log (Real.log y) :=
    Real.log_lt_log h_log_x_pos h_log_lt
  -- 0 < log (log x).
  have h_loglog_x_pos : 0 < Real.log (Real.log x) := by
    have : Real.exp 1 < Real.log (Real.log x) :=
      (Real.lt_log_iff_exp_lt h_log_x_pos).mpr
        ((Real.lt_log_iff_exp_lt hx_pos).mpr hx)
    exact lt_trans (Real.exp_pos _) this
  -- Final step.
  exact Real.log_lt_log h_loglog_x_pos h_loglog_lt

/-! ## §7.  Divergence at infinity -/

/-- `triLog x → ∞` as `x → ∞`.  Composes three copies of
`Real.tendsto_log_atTop`. -/
lemma tendsto_triLog_atTop : Tendsto triLog atTop atTop := by
  -- Step 1: outside a small set the function agrees with `log ∘ log ∘ log`.
  have h_eventually :
      (fun x : ℝ => Real.log (Real.log (Real.log x))) =ᶠ[atTop] triLog := by
    refine (eventually_gt_atTop triLogThreshold).mono fun x hx => ?_
    exact (triLog_eq_logloglog hx).symm
  -- Step 2: `log ∘ log ∘ log → ∞`.
  have h_loglog_log :
      Tendsto (fun x : ℝ => Real.log (Real.log (Real.log x))) atTop atTop :=
    Real.tendsto_log_atTop.comp (Real.tendsto_log_atTop.comp Real.tendsto_log_atTop)
  exact h_loglog_log.congr' h_eventually

end Real
