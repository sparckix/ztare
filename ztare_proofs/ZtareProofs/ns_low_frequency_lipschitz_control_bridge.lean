import Mathlib.Tactic
import ZtareProofs.ns_clay_closure_bridge

/-!
# Low-frequency Lipschitz control bridge

Phase 5FV identified the real continuation gap in the low-high branch:
standard LP/Bony estimates reduce low-high absorption to control of the
low-frequency Lipschitz coefficient.  Assuming that coefficient is controlled
would merely assume a continuation criterion.

This file states the non-tautological bridge: Track B no-survivor blocks must
price the accumulated low-frequency Lipschitz cost.  If every finite prefix of
that cost is bounded by a declared reserve budget, and that reserve budget
implies the chosen critical continuation control, then the missing
`TrackBNoSurvivorToCriticalControl` object is obtained.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Sum the first `N` values of a real sequence. -/
def nsPrefixSum (a : ℕ → Real) (N : ℕ) : Real :=
  ((List.range N).map a).sum

lemma ns_prefix_sum_succ
    (a : ℕ → Real)
    (N : ℕ) :
    nsPrefixSum a (N + 1) = nsPrefixSum a N + a N := by
  unfold nsPrefixSum
  rw [List.range_succ, List.map_append, List.sum_append]
  simp

lemma ns_prefix_sum_nonnegative_of_pointwise
    (a : ℕ → Real)
    (h : ∀ n : ℕ, 0 ≤ a n)
    (N : ℕ) :
    0 ≤ nsPrefixSum a N := by
  induction N with
  | zero =>
      simp [nsPrefixSum]
  | succ N ih =>
      rw [ns_prefix_sum_succ]
      exact add_nonneg ih (h N)

lemma ns_single_le_prefix_sum_succ_of_pointwise_nonnegative
    (a : ℕ → Real)
    (h : ∀ n : ℕ, 0 ≤ a n)
    (n : ℕ) :
    a n ≤ nsPrefixSum a (n + 1) := by
  rw [ns_prefix_sum_succ]
  have hprefix : 0 ≤ nsPrefixSum a n :=
    ns_prefix_sum_nonnegative_of_pointwise a h n
  linarith

lemma ns_prefix_sum_unbounded_of_pointwise_unbounded_nonnegative
    (a : ℕ → Real)
    (hnonneg : ∀ n : ℕ, 0 ≤ a n)
    (hunbounded : ∀ B : Real, ∃ n : ℕ, B < a n) :
    ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum a N := by
  intro B
  obtain ⟨n, hn⟩ := hunbounded B
  exact ⟨n + 1,
    lt_of_lt_of_le hn
      (ns_single_le_prefix_sum_succ_of_pointwise_nonnegative a hnonneg n)⟩

lemma pointwise_unbounded_of_positive_linear_lower_bound
    (a : Real)
    (x y : ℕ → Real)
    (ha : 0 < a)
    (hxy : ∀ n : ℕ, a * x n ≤ y n)
    (hx : ∀ B : Real, ∃ n : ℕ, B < x n) :
    ∀ B : Real, ∃ n : ℕ, B < y n := by
  intro B
  obtain ⟨n, hn⟩ := hx (B / a)
  have hB : B < a * x n := by
    have hmul := mul_lt_mul_of_pos_left hn ha
    field_simp [ha.ne'] at hmul
    exact hmul
  exact ⟨n, lt_of_lt_of_le hB (hxy n)⟩

lemma ns_prefix_sum_le_of_pointwise
    (a b : ℕ → Real)
    (h : ∀ n, a n ≤ b n)
    (N : ℕ) :
    nsPrefixSum a N ≤ nsPrefixSum b N := by
  unfold nsPrefixSum
  induction N with
  | zero =>
      simp
  | succ N ih =>
      rw [List.range_succ, List.map_append, List.sum_append]
      rw [List.map_append, List.sum_append]
      simp only [List.map_singleton, List.sum_singleton]
      exact add_le_add ih (h N)

/-- A low-frequency Lipschitz ledger for one evolution.

`lipschitzCost n` is the contribution of block `n` to the continuation-relevant
low-frequency Lipschitz coefficient.  `reservePrice n` is the declared Track B
price channel that must pay for it.  The concrete PDE proof must define both
from the fixed LP/Bony decomposition before scoring payoff. -/
structure LowFrequencyLipschitzLedger where
  U : NSEvolution
  block : ℕ → FullLedgerBlock
  lipschitzCost : ℕ → Real
  reservePrice : ℕ → Real
  criticalBudget : Real

def lipschitzPrefixCost (L : LowFrequencyLipschitzLedger) (N : ℕ) : Real :=
  nsPrefixSum L.lipschitzCost N

def reservePrefixPrice (L : LowFrequencyLipschitzLedger) (N : ℕ) : Real :=
  nsPrefixSum L.reservePrice N

/-- Certificate that Track B no-survivor prices the low-frequency Lipschitz
coefficient strongly enough to yield a continuation-control quantity. -/
structure LowFrequencyLipschitzControlCertificate
    (L : LowFrequencyLipschitzLedger) where
  block_is_global :
    ∀ n : ℕ, IsGlobalTrackBBlock (L.block n)
  no_survivor_prices_lipschitz :
    ∀ n : ℕ,
      FullLedgerNoSurvivor (L.block n) →
        L.lipschitzCost n ≤ L.reservePrice n
  reserve_prefix_le_budget :
    ∀ N : ℕ, reservePrefixPrice L N ≤ L.criticalBudget
  critical_control_of_prefix_lipschitz_bound :
    (∀ N : ℕ, lipschitzPrefixCost L N ≤ L.criticalBudget) →
      L.U.criticalControl

/-- If every block is no-survivor, then every finite Lipschitz prefix is bounded
by the declared critical budget.  This is the load-bearing reserve edge in the
low-frequency continuation bridge. -/
theorem lipschitz_prefix_le_budget_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n)) :
    ∀ N : ℕ, lipschitzPrefixCost L N ≤ L.criticalBudget := by
  intro N
  have hpoint :
      ∀ n : ℕ, L.lipschitzCost n ≤ L.reservePrice n := by
    intro n
    exact hcert.no_survivor_prices_lipschitz n (hnosurvivor n)
  have hprefix :
      lipschitzPrefixCost L N ≤ reservePrefixPrice L N :=
    ns_prefix_sum_le_of_pointwise L.lipschitzCost L.reservePrice hpoint N
  exact hprefix.trans (hcert.reserve_prefix_le_budget N)

/-- If every block is no-survivor and the reserve budget controls all prefixes,
then the evolution has the declared critical control. -/
theorem critical_control_of_low_frequency_lipschitz_certificate
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n)) :
    L.U.criticalControl :=
  hcert.critical_control_of_prefix_lipschitz_bound
    (lipschitz_prefix_le_budget_under_no_survivor L hcert hnosurvivor)

/-- Declared PDE source for the final Lipschitz-prefix to continuation step.

This is the continuation analogue of the LSC source receipts: bounded finite
prefixes are allowed to imply `criticalControl` only through a named standard
control quantity, not through the desired `globalRegular` conclusion or a
posthoc reserve definition. -/
structure LowFrequencyLipschitzContinuationSource
    (L : LowFrequencyLipschitzLedger) where
  prefix_bound_is_standard_lipschitz_or_bkm_control : Prop
  bkm_or_lipschitz_time_integral_declared_before_payoff : Prop
  no_global_regular_input_to_prefix_control : Prop
  no_continuation_theorem_used_to_price_reserve : Prop
  prefix_bound_is_standard_lipschitz_or_bkm_control_receipt :
    prefix_bound_is_standard_lipschitz_or_bkm_control
  bkm_or_lipschitz_time_integral_declared_before_payoff_receipt :
    bkm_or_lipschitz_time_integral_declared_before_payoff
  no_global_regular_input_to_prefix_control_receipt :
    no_global_regular_input_to_prefix_control
  no_continuation_theorem_used_to_price_reserve_receipt :
    no_continuation_theorem_used_to_price_reserve
  critical_control_of_prefix_lipschitz_bound :
    (∀ N : ℕ, lipschitzPrefixCost L N ≤ L.criticalBudget) →
      L.U.criticalControl

/-- Guard failures for a Lipschitz continuation source. -/
inductive LowFrequencyLipschitzContinuationSourceFalsifier
    (L : LowFrequencyLipschitzLedger)
    (S : LowFrequencyLipschitzContinuationSource L) : Type where
  | missingStandardControlQuantity :
      ¬ S.prefix_bound_is_standard_lipschitz_or_bkm_control →
        LowFrequencyLipschitzContinuationSourceFalsifier L S
  | undeclaredBKMOrLipschitzIntegral :
      ¬ S.bkm_or_lipschitz_time_integral_declared_before_payoff →
        LowFrequencyLipschitzContinuationSourceFalsifier L S
  | globalRegularUsedToGetPrefixControl :
      ¬ S.no_global_regular_input_to_prefix_control →
        LowFrequencyLipschitzContinuationSourceFalsifier L S
  | continuationUsedToPriceReserve :
      ¬ S.no_continuation_theorem_used_to_price_reserve →
        LowFrequencyLipschitzContinuationSourceFalsifier L S

/-- A declared source receipt rules out the continuation-source guard failures.
-/
theorem no_low_frequency_lipschitz_continuation_source_falsifier
    (L : LowFrequencyLipschitzLedger)
    (S : LowFrequencyLipschitzContinuationSource L)
    (F : LowFrequencyLipschitzContinuationSourceFalsifier L S) :
    False := by
  cases F with
  | missingStandardControlQuantity h =>
      exact h S.prefix_bound_is_standard_lipschitz_or_bkm_control_receipt
  | undeclaredBKMOrLipschitzIntegral h =>
      exact h S.bkm_or_lipschitz_time_integral_declared_before_payoff_receipt
  | globalRegularUsedToGetPrefixControl h =>
      exact h S.no_global_regular_input_to_prefix_control_receipt
  | continuationUsedToPriceReserve h =>
      exact h S.no_continuation_theorem_used_to_price_reserve_receipt

/-- Audited version of the low-frequency Lipschitz certificate.

The `criticalControl` field is derived from `continuation_source`, so this
record cannot use an arbitrary critical-control function while separately
claiming a BKM/Lipschitz continuation interpretation. -/
structure LowFrequencyLipschitzAuditedControlCertificate
    (L : LowFrequencyLipschitzLedger) where
  block_is_global :
    ∀ n : ℕ, IsGlobalTrackBBlock (L.block n)
  no_survivor_prices_lipschitz :
    ∀ n : ℕ,
      FullLedgerNoSurvivor (L.block n) →
        L.lipschitzCost n ≤ L.reservePrice n
  reserve_prefix_le_budget :
    ∀ N : ℕ, reservePrefixPrice L N ≤ L.criticalBudget
  continuation_source :
    LowFrequencyLipschitzContinuationSource L

/-- Source-field constructor for the audited low-frequency Lipschitz
certificate.

This is deliberately only record packaging.  The four arguments are the real
source burdens: generated blocks are global, no-survivor pricing conditionally
pays the Lipschitz cost, reserve prefixes are uniformly budgeted, and a
declared BKM/Lipschitz continuation source converts prefix control to
`criticalControl`. -/
def low_frequency_lipschitz_audited_certificate_of_sources
    (L : LowFrequencyLipschitzLedger)
    (block_is_global :
      ∀ n : ℕ, IsGlobalTrackBBlock (L.block n))
    (no_survivor_prices_lipschitz :
      ∀ n : ℕ,
        FullLedgerNoSurvivor (L.block n) →
          L.lipschitzCost n ≤ L.reservePrice n)
    (reserve_prefix_le_budget :
      ∀ N : ℕ, reservePrefixPrice L N ≤ L.criticalBudget)
    (continuation_source :
      LowFrequencyLipschitzContinuationSource L) :
    LowFrequencyLipschitzAuditedControlCertificate L where
  block_is_global := block_is_global
  no_survivor_prices_lipschitz := no_survivor_prices_lipschitz
  reserve_prefix_le_budget := reserve_prefix_le_budget
  continuation_source := continuation_source

/-- Forgetful adapter to the legacy certificate interface. -/
def LowFrequencyLipschitzAuditedControlCertificate.toControlCertificate
    {L : LowFrequencyLipschitzLedger}
    (C : LowFrequencyLipschitzAuditedControlCertificate L) :
    LowFrequencyLipschitzControlCertificate L where
  block_is_global := C.block_is_global
  no_survivor_prices_lipschitz := C.no_survivor_prices_lipschitz
  reserve_prefix_le_budget := C.reserve_prefix_le_budget
  critical_control_of_prefix_lipschitz_bound :=
    C.continuation_source.critical_control_of_prefix_lipschitz_bound

/-- Audited certificate supplies critical control through its declared
continuation source. -/
theorem critical_control_of_audited_low_frequency_lipschitz_certificate
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n)) :
    L.U.criticalControl :=
  critical_control_of_low_frequency_lipschitz_certificate
    L hcert.toControlCertificate hnosurvivor

/-- Audited certificate version of the finite-prefix reserve bound.

This keeps the declared continuation source attached when downstream bridges
only need the prefix budget edge and not the final `criticalControl` output.
-/
theorem lipschitz_prefix_le_budget_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n)) :
    ∀ N : ℕ, lipschitzPrefixCost L N ≤ L.criticalBudget :=
  lipschitz_prefix_le_budget_under_no_survivor
    L hcert.toControlCertificate hnosurvivor

/-- If no-survivor blocks price the low-frequency Lipschitz ledger, then no
finite prefix of that ledger may exceed the declared critical budget.  This is
the falsifier form of the continuation bridge. -/
theorem no_overbudget_lipschitz_prefix_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (N : ℕ)
    (hover : L.criticalBudget < lipschitzPrefixCost L N) :
    False := by
  have hbudget :
      lipschitzPrefixCost L N ≤ L.criticalBudget :=
    lipschitz_prefix_le_budget_under_no_survivor L hcert hnosurvivor N
  exact not_lt_of_ge hbudget hover

/-- Market-impact costs are a valid prefix falsifier if they are pointwise
embedded in the declared low-frequency Lipschitz cost.

This is the countable-limit version of the low-high shear price law: if the
predeclared market-impact entries needed to rearm shells already exceed the
critical reserve budget on a finite prefix, then the claimed Lipschitz bridge
cannot coexist with no-survivor pricing. -/
theorem no_overbudget_market_impact_prefix_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (N : ℕ)
    (hover : L.criticalBudget < nsPrefixSum marketImpactCost N) :
    False := by
  have hmarket_prefix :
      nsPrefixSum marketImpactCost N ≤ lipschitzPrefixCost L N :=
    ns_prefix_sum_le_of_pointwise marketImpactCost L.lipschitzCost hmarket N
  have hlip_over : L.criticalBudget < lipschitzPrefixCost L N :=
    lt_of_lt_of_le hover hmarket_prefix
  exact no_overbudget_lipschitz_prefix_under_no_survivor
    L hcert hnosurvivor N hlip_over

/-- Pointwise-embedded market-impact prefixes are bounded by the same critical
budget as the generated Lipschitz ledger. -/
theorem market_impact_prefix_le_budget_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n) :
    ∀ N : ℕ, nsPrefixSum marketImpactCost N ≤ L.criticalBudget := by
  intro N
  have hmarket_prefix :
      nsPrefixSum marketImpactCost N ≤ lipschitzPrefixCost L N :=
    ns_prefix_sum_le_of_pointwise marketImpactCost L.lipschitzCost hmarket N
  exact hmarket_prefix.trans
    (lipschitz_prefix_le_budget_under_no_survivor L hcert hnosurvivor N)

/-- Pointwise-unbounded market-impact costs are impossible under a claimed
no-survivor Lipschitz closure.

This is the infinite-cascade version of the finite prefix falsifier: if the
PDE estimate says each rearming shell embeds a nonnegative market-impact cost
into the declared low-frequency Lipschitz ledger, and those costs are
pointwise unbounded along the cascade, then some finite prefix must exceed the
declared critical budget. -/
theorem no_pointwise_unbounded_market_impact_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket_nonnegative :
      ∀ n : ℕ, 0 ≤ marketImpactCost n)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (hunbounded :
      ∀ B : Real, ∃ n : ℕ, B < marketImpactCost n) :
    False := by
  have hprefix_unbounded :
      ∀ B : Real, ∃ N : ℕ, B < nsPrefixSum marketImpactCost N :=
    ns_prefix_sum_unbounded_of_pointwise_unbounded_nonnegative
      marketImpactCost hmarket_nonnegative hunbounded
  obtain ⟨N, hover⟩ := hprefix_unbounded L.criticalBudget
  exact no_overbudget_market_impact_prefix_under_no_survivor
    L hcert hnosurvivor marketImpactCost hmarket N hover

/-- Linear-in-shell market impact is already enough to falsify a finite
Lipschitz-prefix closure on an unbounded shell cascade.

This is the Bernstein-corrected low-high edge case: after low-bandwidth
concentration, the best universal lower bound may be only `Omega(N)`, not
`Omega(N^4)`.  But if shell labels go to infinity and those costs embed into
the declared Lipschitz ledger, pointwise unboundedness still forces an
overbudget finite prefix. -/
theorem no_linear_shell_market_impact_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (shellLabel marketImpactCost : ℕ → Real)
    (a : Real)
    (ha : 0 < a)
    (hmarket_nonnegative :
      ∀ n : ℕ, 0 ≤ marketImpactCost n)
    (hlinear :
      ∀ n : ℕ, a * shellLabel n ≤ marketImpactCost n)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (hshell_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < shellLabel n) :
    False := by
  have hmarket_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < marketImpactCost n :=
    pointwise_unbounded_of_positive_linear_lower_bound
      a shellLabel marketImpactCost ha hlinear hshell_unbounded
  exact no_pointwise_unbounded_market_impact_under_no_survivor
    L hcert hnosurvivor marketImpactCost
    hmarket_nonnegative hmarket hmarket_unbounded

/-- Dual-norm ledger for low-high edge gain schedules.

`gain j` is the dimensionless edge log-gain on dyadic step `j`.
`weightedPrice j` is the effective quadratic price attached to `gain j`.
`inverseWeight j` is the declared reciprocal-weight budget used by the finite
Cauchy/duality step.  The analytic PDE proof must define these from the fixed
LP/Bony topology before payoff is scored. -/
structure EdgeGainDualNormLedger where
  gain : ℕ → Real
  weightedPrice : ℕ → Real
  inverseWeight : ℕ → Real
  priceBudget : Real
  dualBudget : Real

def edgeGainPrefix (E : EdgeGainDualNormLedger) (N : ℕ) : Real :=
  nsPrefixSum E.gain N

def edgePricePrefix (E : EdgeGainDualNormLedger) (N : ℕ) : Real :=
  nsPrefixSum E.weightedPrice N

def edgeInverseWeightPrefix (E : EdgeGainDualNormLedger) (N : ℕ) : Real :=
  nsPrefixSum E.inverseWeight N

/-- Finite-prefix dual-norm certificate.

The load-bearing field is `weighted_cauchy_prefix`: it is where the real
sequence-space/PDE proof must show that total edge gain is priced by the
weighted quadratic reserve times the inverse-weight budget. -/
structure EdgeGainDualNormPrefixCertificate
    (E : EdgeGainDualNormLedger) where
  weighted_price_nonnegative : ∀ j : ℕ, 0 ≤ E.weightedPrice j
  inverse_weight_nonnegative : ∀ j : ℕ, 0 ≤ E.inverseWeight j
  price_budget_nonnegative : 0 ≤ E.priceBudget
  dual_budget_nonnegative : 0 ≤ E.dualBudget
  price_prefix_le_budget :
    ∀ N : ℕ, edgePricePrefix E N ≤ E.priceBudget
  inverse_prefix_le_budget :
    ∀ N : ℕ, edgeInverseWeightPrefix E N ≤ E.dualBudget
  weighted_cauchy_prefix :
    ∀ N : ℕ,
      (edgeGainPrefix E N) ^ 2 ≤
        edgePricePrefix E N * edgeInverseWeightPrefix E N

/-- Finite edge-gain prefixes are controlled only by the product of the declared
price budget and declared inverse-weight budget.

This is the formal version of the Phase 5HO lesson: a finite reserve price is
not enough unless the inverse-weight side is also finite. -/
theorem edge_gain_prefix_sq_le_budget_product
    (E : EdgeGainDualNormLedger)
    (C : EdgeGainDualNormPrefixCertificate E)
    (N : ℕ) :
    (edgeGainPrefix E N) ^ 2 ≤ E.priceBudget * E.dualBudget := by
  have hprice_nonneg :
      0 ≤ edgePricePrefix E N :=
    ns_prefix_sum_nonnegative_of_pointwise
      E.weightedPrice C.weighted_price_nonnegative N
  have hdual_nonneg :
      0 ≤ edgeInverseWeightPrefix E N :=
    ns_prefix_sum_nonnegative_of_pointwise
      E.inverseWeight C.inverse_weight_nonnegative N
  have hmul :
      edgePricePrefix E N * edgeInverseWeightPrefix E N ≤
        E.priceBudget * E.dualBudget :=
    mul_le_mul
      (C.price_prefix_le_budget N)
      (C.inverse_prefix_le_budget N)
      hdual_nonneg
      C.price_budget_nonnegative
  exact (C.weighted_cauchy_prefix N).trans hmul

/-- A divergent edge-gain prefix is the sequence-space adversary exposed by
Phase 5HN/5HO: total edge gain becomes arbitrarily large. -/
def EdgeGainPrefixDiverges (E : EdgeGainDualNormLedger) : Prop :=
  ∀ B : Real, ∃ N : ℕ, B < edgeGainPrefix E N

/-- Bounded weighted price plus bounded reciprocal-weight budget rules out a
divergent edge-gain schedule.

This is the formal sequence target behind the dynamic recurrence-price
obligation: the PDE theorem must supply reciprocal weights whose prefixes are
uniformly bounded, i.e. the `sum 1/a_j < infinity` side of the weighted
Cauchy-Schwarz pair. -/
theorem no_divergent_edge_gain_of_dual_norm_prefix_certificate
    (E : EdgeGainDualNormLedger)
    (C : EdgeGainDualNormPrefixCertificate E) :
    ¬ EdgeGainPrefixDiverges E := by
  intro hdiv
  let cap : Real := E.priceBudget * E.dualBudget + 1
  rcases hdiv cap with ⟨N, hN⟩
  have hsq_le : (edgeGainPrefix E N) ^ 2 ≤ E.priceBudget * E.dualBudget :=
    edge_gain_prefix_sq_le_budget_product E C N
  have hcap_pos : 0 < cap := by
    have hprod_nonneg : 0 ≤ E.priceBudget * E.dualBudget :=
      mul_nonneg C.price_budget_nonnegative C.dual_budget_nonnegative
    unfold cap
    nlinarith
  have hgain_pos : 0 < edgeGainPrefix E N := lt_trans hcap_pos hN
  have hcap_sq_lt_gain_sq : cap ^ 2 < (edgeGainPrefix E N) ^ 2 := by
    nlinarith
  have hprod_lt_cap_sq : E.priceBudget * E.dualBudget < cap ^ 2 := by
    have hprod_nonneg : 0 ≤ E.priceBudget * E.dualBudget :=
      mul_nonneg C.price_budget_nonnegative C.dual_budget_nonnegative
    unfold cap
    nlinarith
  have hprod_lt_gain_sq :
      E.priceBudget * E.dualBudget < (edgeGainPrefix E N) ^ 2 :=
    lt_trans hprod_lt_cap_sq hcap_sq_lt_gain_sq
  exact not_lt_of_ge hsq_le hprod_lt_gain_sq

/-- Event-level recurrence ledger.

This is the multiplicity-safe version of the dyadic recurrence condition.  If
shell `j` has many return events, those events must appear separately here; the
right reciprocal budget is over events, not over shell labels. -/
structure EdgeEventRecurrenceLedger where
  eventGain : ℕ → Real
  eventWeight : ℕ → Real
  rawEdgePrice : ℕ → Real
  recurrencePrice : ℕ → Real
  priceBudget : Real
  dualBudget : Real

def edgeEventPricePrefix
    (E : EdgeEventRecurrenceLedger) (N : ℕ) : Real :=
  nsPrefixSum
    (fun e : ℕ =>
      E.rawEdgePrice e + E.recurrencePrice e)
    N

def edgeEventInverseWeightPrefix
    (E : EdgeEventRecurrenceLedger) (N : ℕ) : Real :=
  nsPrefixSum (fun e : ℕ => 1 / E.eventWeight e) N

def edgeEventDualNormLedger
    (E : EdgeEventRecurrenceLedger) :
    EdgeGainDualNormLedger where
  gain := E.eventGain
  weightedPrice := fun e => E.eventWeight e * (E.eventGain e) ^ (2 : Nat)
  inverseWeight := fun e => 1 / E.eventWeight e
  priceBudget := E.priceBudget
  dualBudget := E.dualBudget

/-- Event-level dynamic recurrence certificate.

`lower_envelope` is the PDE recurrence-price theorem: raw edge price plus
preparation/recurrence price must dominate the weighted square event price.
`inverse_weight_prefix_le_budget` is the event-level reciprocal summability
condition, including any multiplicity of repeated returns in the same shell. -/
structure EdgeEventDynamicRecurrenceCertificate
    (E : EdgeEventRecurrenceLedger) where
  event_weight_positive : ∀ e : ℕ, 0 < E.eventWeight e
  price_budget_nonnegative : 0 ≤ E.priceBudget
  dual_budget_nonnegative : 0 ≤ E.dualBudget
  lower_envelope :
    ∀ e : ℕ,
      E.eventWeight e * (E.eventGain e) ^ (2 : Nat) ≤
        E.rawEdgePrice e + E.recurrencePrice e
  event_price_prefix_le_budget :
    ∀ N : ℕ, edgeEventPricePrefix E N ≤ E.priceBudget
  inverse_weight_prefix_le_budget :
    ∀ N : ℕ, edgeEventInverseWeightPrefix E N ≤ E.dualBudget
  weighted_cauchy_prefix :
    ∀ N : ℕ,
      (edgeGainPrefix (edgeEventDualNormLedger E) N) ^ (2 : Nat) ≤
        edgePricePrefix (edgeEventDualNormLedger E) N *
          edgeInverseWeightPrefix (edgeEventDualNormLedger E) N

def edge_gain_dual_norm_certificate_of_event_recurrence
    (E : EdgeEventRecurrenceLedger)
    (C : EdgeEventDynamicRecurrenceCertificate E) :
    EdgeGainDualNormPrefixCertificate (edgeEventDualNormLedger E) where
  weighted_price_nonnegative := by
    intro e
    exact mul_nonneg (le_of_lt (C.event_weight_positive e)) (sq_nonneg _)
  inverse_weight_nonnegative := by
    intro e
    exact div_nonneg zero_le_one (le_of_lt (C.event_weight_positive e))
  price_budget_nonnegative := C.price_budget_nonnegative
  dual_budget_nonnegative := C.dual_budget_nonnegative
  price_prefix_le_budget := by
    intro N
    have hprefix :
        nsPrefixSum
          (fun e : ℕ => E.eventWeight e * (E.eventGain e) ^ (2 : Nat))
          N ≤ edgeEventPricePrefix E N :=
      ns_prefix_sum_le_of_pointwise
        (fun e : ℕ => E.eventWeight e * (E.eventGain e) ^ (2 : Nat))
        (fun e : ℕ => E.rawEdgePrice e + E.recurrencePrice e)
        C.lower_envelope
        N
    exact hprefix.trans (C.event_price_prefix_le_budget N)
  inverse_prefix_le_budget := C.inverse_weight_prefix_le_budget
  weighted_cauchy_prefix := C.weighted_cauchy_prefix

/-- Event-level dynamic recurrence closure: if the PDE supplies event weights
with bounded reciprocal prefixes and prices every event by raw plus recurrence
cost, then no divergent event-gain prefix remains. -/
theorem no_divergent_event_gain_of_dynamic_recurrence_certificate
    (E : EdgeEventRecurrenceLedger)
    (C : EdgeEventDynamicRecurrenceCertificate E) :
    ¬ EdgeGainPrefixDiverges (edgeEventDualNormLedger E) := by
  let C' : EdgeGainDualNormPrefixCertificate (edgeEventDualNormLedger E) :=
    edge_gain_dual_norm_certificate_of_event_recurrence E C
  exact no_divergent_edge_gain_of_dual_norm_prefix_certificate
    (edgeEventDualNormLedger E)
    C'

/-- Harmonic edge price prefix for the explicit `g_j = 1/(j+1)` adversary.

If a recurrence theorem assigns weight `a_j`, this is the finite-prefix version
of `sum_j a_j/(j+1)^2`. -/
def harmonicEdgePricePrefix (weight : ℕ → Real) (N : ℕ) : Real :=
  nsPrefixSum
    (fun j : ℕ => weight j / (((j + 1 : ℕ) : Real) ^ (2 : Nat)))
    N

/-- Bounded price certificate for the harmonic LP-edge schedule.

The load-bearing field is `harmonic_price_charged`: it says the predeclared
recurrence price actually pays the `g_j = 1/(j+1)` edge schedule with weights
`weight j`, rather than naming a preparation cost after observing payoff. -/
structure HarmonicEdgePriceCertificate where
  weight : ℕ → Real
  recurrencePrice : ℕ → Real
  priceBudget : Real
  harmonic_price_charged :
    ∀ j : ℕ,
      weight j / (((j + 1 : ℕ) : Real) ^ (2 : Nat)) ≤
        recurrencePrice j
  recurrence_price_prefix_le_budget :
    ∀ N : ℕ, nsPrefixSum recurrencePrice N ≤ priceBudget

/-- Sharp harmonic boundary: if the predeclared harmonic price prefixes are
unbounded, they cannot coexist with a bounded recurrence-price budget.

This is the formal version of the Phase 5IV recurrence split.  To kill the
explicit `1/j` edge cascade, a PDE recurrence theorem must make
`sum_j a_j/(j+1)^2` diverge, or else the harmonic schedule remains
sequence-admissible at the accounting level. -/
theorem no_bounded_recurrence_price_of_unbounded_harmonic_edge_price
    (C : HarmonicEdgePriceCertificate)
    (hunbounded :
      ∀ B : Real, ∃ N : ℕ, B < harmonicEdgePricePrefix C.weight N) :
    False := by
  obtain ⟨N, hN⟩ := hunbounded C.priceBudget
  have hprefix :
      harmonicEdgePricePrefix C.weight N ≤
        nsPrefixSum C.recurrencePrice N :=
    ns_prefix_sum_le_of_pointwise
      (fun j : ℕ => C.weight j / (((j + 1 : ℕ) : Real) ^ (2 : Nat)))
      C.recurrencePrice
      C.harmonic_price_charged
      N
  have hbudget :
      harmonicEdgePricePrefix C.weight N ≤ C.priceBudget :=
    hprefix.trans (C.recurrence_price_prefix_le_budget N)
  exact not_lt_of_ge hbudget hN

/-- Pointwise market-impact underpricing is already a falsifier.

This is the one-block version of the prefix theorem.  If a predeclared
market-impact cost embeds into the low-frequency Lipschitz cost, then
no-survivor pricing forces that cost below the reserve price for the same
entry.  A smooth LP/Bony block whose local leakage estimate is valid but whose
market-impact price cannot be embedded into the global reserve should therefore
exhibit exactly this underpricing contradiction. -/
theorem no_underpriced_market_impact_entry_under_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (n : ℕ)
    (hunderpriced : L.reservePrice n < marketImpactCost n) :
    False := by
  have hpriced :
      L.lipschitzCost n ≤ L.reservePrice n :=
    hcert.no_survivor_prices_lipschitz n (hnosurvivor n)
  have hmarket_le_reserve :
      marketImpactCost n ≤ L.reservePrice n :=
    (hmarket n).trans hpriced
  exact not_lt_of_ge hmarket_le_reserve hunderpriced

/-- Audited certificate version of the Lipschitz-prefix overbudget falsifier.
-/
theorem no_overbudget_lipschitz_prefix_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (N : ℕ)
    (hover : L.criticalBudget < lipschitzPrefixCost L N) :
    False :=
  no_overbudget_lipschitz_prefix_under_no_survivor
    L hcert.toControlCertificate hnosurvivor N hover

/-- Audited certificate version of the market-impact prefix falsifier. -/
theorem no_overbudget_market_impact_prefix_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (N : ℕ)
    (hover : L.criticalBudget < nsPrefixSum marketImpactCost N) :
    False :=
  no_overbudget_market_impact_prefix_under_no_survivor
    L hcert.toControlCertificate hnosurvivor marketImpactCost hmarket N hover

/-- Audited certificate version of the market-impact prefix budget bound. -/
theorem market_impact_prefix_le_budget_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n) :
    ∀ N : ℕ, nsPrefixSum marketImpactCost N ≤ L.criticalBudget :=
  market_impact_prefix_le_budget_under_no_survivor
    L hcert.toControlCertificate hnosurvivor marketImpactCost hmarket

/-- Audited certificate version of the one-entry market-impact underpricing
falsifier. -/
theorem no_underpriced_market_impact_entry_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (n : ℕ)
    (hunderpriced : L.reservePrice n < marketImpactCost n) :
    False :=
  no_underpriced_market_impact_entry_under_no_survivor
    L hcert.toControlCertificate hnosurvivor marketImpactCost hmarket
    n hunderpriced

/-- Audited certificate version of the pointwise-unbounded market-impact
falsifier. -/
theorem no_pointwise_unbounded_market_impact_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (marketImpactCost : ℕ → Real)
    (hmarket_nonnegative :
      ∀ n : ℕ, 0 ≤ marketImpactCost n)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (hunbounded :
      ∀ B : Real, ∃ n : ℕ, B < marketImpactCost n) :
    False :=
  no_pointwise_unbounded_market_impact_under_no_survivor
    L hcert.toControlCertificate hnosurvivor marketImpactCost
    hmarket_nonnegative hmarket hunbounded

/-- Audited certificate version of the linear-shell market-impact falsifier.
-/
theorem no_linear_shell_market_impact_under_audited_no_survivor
    (L : LowFrequencyLipschitzLedger)
    (hcert : LowFrequencyLipschitzAuditedControlCertificate L)
    (hnosurvivor : ∀ n : ℕ, FullLedgerNoSurvivor (L.block n))
    (shellLabel marketImpactCost : ℕ → Real)
    (a : Real)
    (ha : 0 < a)
    (hmarket_nonnegative :
      ∀ n : ℕ, 0 ≤ marketImpactCost n)
    (hlinear :
      ∀ n : ℕ, a * shellLabel n ≤ marketImpactCost n)
    (hmarket :
      ∀ n : ℕ, marketImpactCost n ≤ L.lipschitzCost n)
    (hshell_unbounded :
      ∀ B : Real, ∃ n : ℕ, B < shellLabel n) :
    False :=
  no_linear_shell_market_impact_under_no_survivor
    L hcert.toControlCertificate hnosurvivor shellLabel marketImpactCost
    a ha hmarket_nonnegative hlinear hmarket hshell_unbounded

/-- A family-level bridge from evolutions to low-frequency Lipschitz ledgers. -/
structure LowFrequencyLipschitzBridge where
  ledger_of_evolution : NSEvolution → LowFrequencyLipschitzLedger
  ledger_evolution_eq :
    ∀ U : NSEvolution, (ledger_of_evolution U).U = U
  audited_certificate_of_evolution :
    ∀ U : NSEvolution,
      LowFrequencyLipschitzAuditedControlCertificate (ledger_of_evolution U)

/-- Family constructor for the low-frequency Lipschitz bridge.

The constructor exposes the exact source-first family interface and prevents
downstream closure code from treating a `LowFrequencyLipschitzBridge` as a
black box detached from its generated ledger and audited continuation source. -/
def low_frequency_lipschitz_bridge_of_audited_sources
    (ledger_of_evolution : NSEvolution → LowFrequencyLipschitzLedger)
    (ledger_evolution_eq :
      ∀ U : NSEvolution, (ledger_of_evolution U).U = U)
    (audited_certificate_of_evolution :
      ∀ U : NSEvolution,
        LowFrequencyLipschitzAuditedControlCertificate
          (ledger_of_evolution U)) :
    LowFrequencyLipschitzBridge where
  ledger_of_evolution := ledger_of_evolution
  ledger_evolution_eq := ledger_evolution_eq
  audited_certificate_of_evolution := audited_certificate_of_evolution

/-- Legacy certificate interface derived from the audited continuation source.
-/
def LowFrequencyLipschitzBridge.certificate_of_evolution
    (B : LowFrequencyLipschitzBridge)
    (U : NSEvolution) :
    LowFrequencyLipschitzControlCertificate (B.ledger_of_evolution U) :=
  (B.audited_certificate_of_evolution U).toControlCertificate

/-- The declared continuation source carried by a low-frequency Lipschitz
bridge. -/
def LowFrequencyLipschitzBridge.continuation_source_of_evolution
    (B : LowFrequencyLipschitzBridge)
    (U : NSEvolution) :
    LowFrequencyLipschitzContinuationSource (B.ledger_of_evolution U) :=
  (B.audited_certificate_of_evolution U).continuation_source

/-- A low-frequency Lipschitz bridge rules out guard failures for the declared
continuation source of each generated evolution. -/
theorem no_low_frequency_lipschitz_bridge_continuation_source_falsifier
    (B : LowFrequencyLipschitzBridge)
    (U : NSEvolution)
    (F :
      LowFrequencyLipschitzContinuationSourceFalsifier
        (B.ledger_of_evolution U)
        (B.continuation_source_of_evolution U)) :
    False :=
  no_low_frequency_lipschitz_continuation_source_falsifier
    (B.ledger_of_evolution U)
    (B.continuation_source_of_evolution U)
    F

/-- Low-frequency Lipschitz control supplies the missing
`TrackBNoSurvivorToCriticalControl` bridge used by `ns_clay_closure_bridge`. -/
def no_survivor_to_critical_control_of_low_frequency_lipschitz
    (B : LowFrequencyLipschitzBridge) :
    TrackBNoSurvivorToCriticalControl where
  block_of_evolution := fun U n => (B.ledger_of_evolution U).block n
  block_is_global := by
    intro U n
    exact (B.audited_certificate_of_evolution U).block_is_global n
  critical_control_of_no_survivor := by
    intro U hnosurvivor
    have hcrit :
        (B.ledger_of_evolution U).U.criticalControl :=
      critical_control_of_audited_low_frequency_lipschitz_certificate
        (B.ledger_of_evolution U)
        (B.audited_certificate_of_evolution U)
        hnosurvivor
    rw [B.ledger_evolution_eq U] at hcrit
    exact hcrit

/-- The exact remaining PDE obligation after Phase 5FV. -/
structure LowFrequencyLipschitzPDEObligation where
  lp_bony_decomposition_fixed : Prop
  lipschitz_cost_declared_before_payoff : Prop
  reserve_price_declared_before_payoff : Prop
  edge_gain_weights_declared_before_payoff : Prop
  inverse_weight_budget_declared_before_payoff : Prop
  no_survivor_prices_lipschitz : Prop
  reserve_prefixes_uniformly_bounded : Prop
  edge_gain_dual_norm_prefix_control : Prop
  critical_control_from_lipschitz_prefix_bound : Prop

end

end ZtareProofs.NS
