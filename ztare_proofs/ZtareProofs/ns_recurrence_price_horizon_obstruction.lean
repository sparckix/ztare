import Mathlib.Tactic
import ZtareProofs.ns_low_frequency_lipschitz_control_bridge

/-!
# Recurrence-price horizon obstruction

Phase 5HQ killed a tempting shortcut: the finite projection square-law tax
cannot be lifted into a positive log-normalized recurrence horizon merely by
integrating a bounded `B^-3` deficit over finite blowup time.

This file records the scalar theorem behind that kill.  If the charged tax
prefix is bounded by total recurrence time, then any unbounded normalizer
(for example `log N`) drives the normalized tax horizon to zero.  A future
Navier-Stokes proof must therefore supply an additional physical lower
envelope: amplitude, dwell, recurrence, or critical-space price.  The finite
square-law deficit is not that envelope by itself.
-/

namespace ZtareProofs.NS

/-- Abstract finite-time horizon ledger.

`tax j` is the proposed per-stage charged tax contribution, `cycleTime j` is
the recurrence time spent in that stage, and `normalizer N` is the scale used
to claim a positive horizon.  The key anti-overclaim condition is
`tax_entry_le_cycle_time`: if the tax is only a bounded normalized deficit
integrated over the cycle, it cannot exceed the cycle-time mass. -/
structure FiniteTimeNormalizedHorizonLedger where
  tax : Nat -> Real
  cycleTime : Nat -> Real
  normalizer : Nat -> Real
  totalTime : Real
  tax_entry_le_cycle_time : forall n : Nat, tax n <= cycleTime n
  cycle_time_prefix_le_total : forall N : Nat, nsPrefixSum cycleTime N <= totalTime
  total_time_nonnegative : 0 <= totalTime
  normalizer_positive : forall N : Nat, 0 < normalizer N
  normalizer_eventually_above :
    forall B : Real, exists N0 : Nat, forall N : Nat, N0 <= N -> B < normalizer N

/-- The tax prefix is bounded by total recurrence time. -/
theorem finite_time_tax_prefix_le_total
    (H : FiniteTimeNormalizedHorizonLedger)
    (N : Nat) :
    nsPrefixSum H.tax N <= H.totalTime := by
  have hprefix :
      nsPrefixSum H.tax N <= nsPrefixSum H.cycleTime N :=
    ns_prefix_sum_le_of_pointwise H.tax H.cycleTime H.tax_entry_le_cycle_time N
  exact hprefix.trans (H.cycle_time_prefix_le_total N)

/-- Finite-time domination drives any unbounded-normalizer tax horizon below
every positive threshold eventually.

This is the formal version of the Phase 5HQ sanity check:

`tax_prefix(N) / normalizer(N) -> 0`

whenever the prefix is bounded by finite recurrence time and the normalizer
eventually exceeds every constant. -/
theorem normalized_tax_horizon_eventually_below
    (H : FiniteTimeNormalizedHorizonLedger)
    (c : Real)
    (hc : 0 < c) :
    exists N0 : Nat,
      forall N : Nat,
        N0 <= N -> nsPrefixSum H.tax N / H.normalizer N < c := by
  obtain ⟨N0, hN0⟩ := H.normalizer_eventually_above (H.totalTime / c)
  refine ⟨N0, ?_⟩
  intro N hN
  have hnorm_gt : H.totalTime / c < H.normalizer N := hN0 N hN
  have hnorm_pos : 0 < H.normalizer N := H.normalizer_positive N
  have hT_lt : H.totalTime < c * H.normalizer N := by
    have hmul : c * (H.totalTime / c) < c * H.normalizer N :=
      mul_lt_mul_of_pos_left hnorm_gt hc
    have hcancel : c * (H.totalTime / c) = H.totalTime := by
      field_simp [hc.ne']
    linarith
  have hprefix_le : nsPrefixSum H.tax N <= H.totalTime :=
    finite_time_tax_prefix_le_total H N
  have hprefix_lt : nsPrefixSum H.tax N < c * H.normalizer N := by
    exact lt_of_le_of_lt hprefix_le hT_lt
  exact (div_lt_iff₀ hnorm_pos).2 hprefix_lt

/-- A claimed eventual positive normalized horizon is incompatible with the
finite-time bounded-tax ledger. -/
theorem no_eventual_positive_normalized_horizon
    (H : FiniteTimeNormalizedHorizonLedger)
    (c : Real)
    (hc : 0 < c) :
    Not (exists N0 : Nat,
      forall N : Nat,
        N0 <= N -> c <= nsPrefixSum H.tax N / H.normalizer N) := by
  intro hclaim
  rcases hclaim with ⟨Nclaim, hclaim⟩
  rcases normalized_tax_horizon_eventually_below H c hc with ⟨Nsmall, hsmall⟩
  let N := max Nclaim Nsmall
  have hge_claim : Nclaim <= N := by
    exact le_max_left Nclaim Nsmall
  have hge_small : Nsmall <= N := by
    exact le_max_right Nclaim Nsmall
  have hlo : nsPrefixSum H.tax N / H.normalizer N < c :=
    hsmall N hge_small
  have hhi : c <= nsPrefixSum H.tax N / H.normalizer N :=
    hclaim N hge_claim
  exact not_lt_of_ge hhi hlo

end ZtareProofs.NS
