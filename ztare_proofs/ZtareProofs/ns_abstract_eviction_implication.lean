import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Tactic
import ZtareProofs.ns_bounded_state_eviction

namespace ZtareProofs

/--
Generic single-visit cap:
if a positive-production episode is bounded by `exp (χmax * dwell)` and the
per-visit budget obeys `χmax * dwell ≤ M`, then the episode multiplier is
bounded by `exp M`.
-/
theorem visit_multiplier_cap
    {ω_enter ω_exit χmax dwell M : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (χmax * dwell))
    (hbudget : χmax * dwell ≤ M) :
    ω_exit ≤ ω_enter * Real.exp M := by
  have hexp : Real.exp (χmax * dwell) ≤ Real.exp M := by
    exact Real.exp_le_exp.mpr hbudget
  have hmul : ω_enter * Real.exp (χmax * dwell) ≤ ω_enter * Real.exp M := by
    exact mul_le_mul_of_nonneg_left hexp hω_nonneg
  exact le_trans hgrowth hmul

/--
Generic anti-threshold implication:
if a single visit is capped by `exp M`, then it cannot reach any threshold
strictly above that cap during the same visit.
-/
theorem cannot_reach_threshold_in_single_visit
    {ω_enter ω_exit M ω_target : Real}
    (hcap : ω_exit ≤ ω_enter * Real.exp M)
    (hthreshold : ω_enter * Real.exp M < ω_target) :
    ¬ ω_target ≤ ω_exit := by
  intro hreach
  have : ω_target ≤ ω_enter * Real.exp M := le_trans hreach hcap
  exact (not_lt_of_ge this) hthreshold

/-- Real-valued copy of the observed Phase 5o redistribution timescale proxy. -/
noncomputable def tauRedistR : Real := (1 : Real) / 20

/-- Real-valued copy of the observed Phase 5o consolidation timescale proxy. -/
noncomputable def tauConsProxyR : Real := (7540645060705461 : Real) / 1000000000000000

/-- Earned numerical bound imported from the certified empirical seed. -/
theorem observed_ratio_lt_one_hundredth_real :
    tauRedistR / tauConsProxyR < (1 : Real) / 100 := by
  norm_num [tauRedistR, tauConsProxyR]

/--
NS-specific abstract implication:
if a single danger-state visit obeys the observed Phase 5o ratio bound, then
its multiplier is capped by `exp (1/100)`.
-/
theorem ns_observed_visit_cap
    {ω_enter ω_exit : Real}
    (hω_nonneg : 0 ≤ ω_enter)
    (hgrowth : ω_exit ≤ ω_enter * Real.exp (tauRedistR / tauConsProxyR)) :
    ω_exit ≤ ω_enter * Real.exp ((1 : Real) / 100) := by
  apply visit_multiplier_cap hω_nonneg hgrowth
  exact le_of_lt observed_ratio_lt_one_hundredth_real

end ZtareProofs
