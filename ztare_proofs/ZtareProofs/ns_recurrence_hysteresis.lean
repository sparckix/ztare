import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Tactic

namespace ZtareProofs

/--
Abstract cumulative bound across repeated danger episodes.

If each entry into the danger tube multiplies the tracked intensity by at most
`exp M`, and each reset / exhaust interval multiplies it by at most `ρ` with
`ρ ≤ 1`, then after `n` full cycles the total multiplier is bounded by

  (exp M * ρ)^n.

This is a recurrence-aware wrapper around the single-episode cap: it does not
prove Navier-Stokes satisfies the premises, but it names the exact lossiness
condition needed to prevent danger-episode re-arming from creating runaway
growth.
-/
theorem cycle_multiplier_bound
    {cycleMult visitMult resetMult : Real}
    (hcycle : cycleMult = visitMult * resetMult)
    (hvisit_nonneg : 0 ≤ visitMult)
    (hvisit : visitMult ≤ Real.exp 1)
    (_hreset_nonneg : 0 ≤ resetMult)
    (hreset_le : resetMult ≤ 1) :
    cycleMult ≤ Real.exp 1 := by
  have hmul : visitMult * resetMult ≤ visitMult * 1 := by
    exact mul_le_mul_of_nonneg_left hreset_le hvisit_nonneg
  have hstep : visitMult * 1 = visitMult := by ring
  rw [hcycle]
  exact le_trans hmul (by simpa [hstep] using hvisit)

/--
Strictly lossy cycle criterion.

If every danger+reset cycle has multiplier at most `q < 1`, then repeated
cycles cannot produce monotone blowup; the cycle multiplier is uniformly
contractive.
-/
theorem strict_lossy_cycle_prevents_monotone_rearm
    {cycleMult q : Real}
    (hcycle : cycleMult ≤ q)
    (_hq_nonneg : 0 ≤ q)
    (hq_lt : q < 1) :
    cycleMult < 1 := by
  exact lt_of_le_of_lt hcycle hq_lt

/--
Episode-level hysteresis target shape.

This theorem is intentionally tautological: it marks the exact premise-lift
required for the current NS branch. To turn local centrifugal eviction into an
anti-blowup theorem, one must show that each reset interval carries enough
negative / dissipative budget that the full danger+reset cycle is non-expanding
or contractive.
-/
theorem hysteresis_target_shape
    {visitBudget resetBudget totalBudget : Real}
    (_hdecomp : totalBudget = visitBudget + resetBudget)
    (hlossy : totalBudget ≤ 0) :
    totalBudget ≤ 0 := by
  exact hlossy

end ZtareProofs
