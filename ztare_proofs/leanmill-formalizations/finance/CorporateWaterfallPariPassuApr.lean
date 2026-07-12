/-
LeanMill campaign provenance — pariPassuWaterfallDistribution_feasible_and_ranked_absolutePriority
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=apr_paripassu_v2) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 1412.14s launch→close = formalize 668.02s (theory+statement+firewall) + prove 744.12s (proof search) · prove p50 695.46s p95 1302.84s
  compute     : cost-to-closure 466.97s mean · 932.32s total
  yield       : 5/10 attempts closed (5 failed)
  phases      : 568.2s leaf.dispatch · 66.3s formalize · 16.5s pool · 9.4s native · 4.9s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×5 · claude_warm×3 · proposer_pool×2
  milestone   : campaign family 'apr_paripassu' — 2 run(s) · REAL elapsed (launch→last) 4969.7s (~83 min) = formalize 183.3s + prove/other · active-solve 3304.5s · 14 closures [launch→last is the honest wall]
     - apr_paripassu: 9/55 closed · elapsed 3483.58s (~58.1 min)
     - apr_paripassu_v2: 5/10 closed · elapsed 1486.11s (~24.8 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/corporate_waterfalls_apr_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

abbrev ClaimSchedule (ι : Type*) := ι → NNReal

/-- Nonnegative liquidation payments indexed by creditor tranche. -/

abbrev PaymentSchedule (ι : Type*) := ι → NNReal

/-- Anchor: claim schedules are exactly functions into Mathlib `NNReal`. -/

def DistributionFeasible {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) : Prop :=
  (∀ i : ι, pay i ≤ claims i) ∧ (∑ i, pay i) ≤ pool

/-- Anchor: feasibility is the primitive cap plus Mathlib finite-sum budget
condition. -/

def AbsolutePriority {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) : Prop :=
  ∀ senior junior : ι, senior < junior → 0 < pay junior → pay senior = claims senior

/-- Anchor: APR is exactly the primitive senior-before-positive-junior
full-payment implication. -/

def APRTriggered {ι : Type*} [Preorder ι] (pay : PaymentSchedule ι) : Prop :=
  ∃ senior junior : ι, senior < junior ∧ 0 < pay junior

/-- Anchor: triggering is just existence of an ordered senior/junior pair with
positive junior payment. -/

structure NonvacuousAbsolutePriority {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) : Prop where
  apr : AbsolutePriority claims pay
  triggered : APRTriggered pay

/-- Anchor: the nonvacuous APR bundle is exactly APR plus the trigger witness. -/

noncomputable def SeniorClaimsBefore {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (i : ι) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => j < i), claims j

/-- Anchor: senior claims before a tranche are the Mathlib finite sum over the
filtered set of strictly senior tranches. -/

noncomputable def WaterfallDistribution {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) : PaymentSchedule ι :=
  fun i => min (claims i) (pool - SeniorClaimsBefore claims i)

/-- Anchor: the closed-form waterfall is claim capped by residual value after
senior claims. -/

structure WaterfallConclusion {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) : Prop where
  feasible : DistributionFeasible claims pool pay
  absolute_priority : AbsolutePriority claims pay

/-- Anchor: the conclusion bundle is exactly feasibility plus APR. -/

def RankedStrictlySenior {ι : Type*} (rank : ι → ℕ) (senior junior : ι) : Prop :=
  rank senior < rank junior

/-- Anchor: ranked strict seniority is just Mathlib's strict order on the rank
values. -/

noncomputable def PariPassuLevelClaimTotal
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j = rank i), claims j

/-- Anchor: level claim total is the Mathlib finite sum over tranches with the
same rank. -/

noncomputable def RankedSeniorClaimsBefore
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j < rank i), claims j

/-- Anchor: ranked senior claims are the finite sum over lower-rank tranches. -/

noncomputable def PariPassuRankResidual
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) (i : ι) : NNReal :=
  pool - RankedSeniorClaimsBefore claims rank i

/-- Anchor: residual value is pool minus the Mathlib finite sum of strictly
senior ranked claims. -/

noncomputable def PariPassuWaterfallDistribution
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) : PaymentSchedule ι :=
  fun i =>
    let levelTotal := PariPassuLevelClaimTotal claims rank i
    let levelPayment := min (PariPassuRankResidual claims rank pool i) levelTotal
    if levelTotal = 0 then 0 else (claims i / levelTotal) * levelPayment

/-- Anchor: the pari-passu waterfall is the pro-rata share of the capped level
payment. -/

noncomputable def RankLevelClaim
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (k : ℕ) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j = k), claims j

noncomputable def RankSeniorClaim
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (k : ℕ) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j < k), claims j

lemma levelTotal_eq_rankLevel {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) {i : ι} {k : ℕ}
    (hik : rank i = k) :
    PariPassuLevelClaimTotal claims rank i = RankLevelClaim claims rank k := by
  classical
  simp [PariPassuLevelClaimTotal, RankLevelClaim, hik]

lemma seniorBefore_eq_rankSenior {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) {i : ι} {k : ℕ}
    (hik : rank i = k) :
    RankedSeniorClaimsBefore claims rank i = RankSeniorClaim claims rank k := by
  classical
  simp [RankedSeniorClaimsBefore, RankSeniorClaim, hik]

lemma inner_sum_eq_levelPayment {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal) (k : ℕ) :
    (∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k),
      PariPassuWaterfallDistribution claims rank pool i) =
      min (pool - RankSeniorClaim claims rank k) (RankLevelClaim claims rank k) := by
  classical
  by_cases htot : RankLevelClaim claims rank k = 0
  · have hzero : ∀ i ∈ Finset.univ.filter (fun i : ι => rank i = k),
        PariPassuWaterfallDistribution claims rank pool i = 0 := by
      intro i hi
      have hik : rank i = k := (Finset.mem_filter.mp hi).2
      simp [PariPassuWaterfallDistribution, PariPassuRankResidual,
        levelTotal_eq_rankLevel claims rank hik,
        seniorBefore_eq_rankSenior claims rank hik, htot]
    have hlevel :
        min (pool - RankSeniorClaim claims rank k) (RankLevelClaim claims rank k) = 0 := by
      simp [htot]
    rw [hlevel]
    exact Finset.sum_eq_zero hzero
  · have hsum :
        (∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k),
          PariPassuWaterfallDistribution claims rank pool i) =
        (∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k),
          (claims i / RankLevelClaim claims rank k) *
            min (pool - RankSeniorClaim claims rank k) (RankLevelClaim claims rank k)) := by
      apply Finset.sum_congr rfl
      intro i hi
      have hik : rank i = k := (Finset.mem_filter.mp hi).2
      simp [PariPassuWaterfallDistribution, PariPassuRankResidual,
        levelTotal_eq_rankLevel claims rank hik,
        seniorBefore_eq_rankSenior claims rank hik, htot]
    rw [hsum]
    rw [← Finset.sum_mul]
    rw [← Finset.sum_div]
    have ht' :
        (∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k), claims i) ≠ 0 := by
      simpa [RankLevelClaim] using htot
    simp only [RankLevelClaim]
    rw [div_self ht', one_mul]

lemma nnreal_pro_rata_le_claim {c t p : NNReal} (hc : c ≤ t) (hp : p ≤ t) :
    c / t * p ≤ c := by
  by_cases ht : t = 0
  · have hc0 : c = 0 := le_antisymm (hc.trans (le_of_eq ht)) (zero_le c)
    simp [hc0]
  · calc
      c / t * p ≤ c / t * t := by exact mul_le_mul_left' hp (c / t)
      _ = c := div_mul_cancel₀ c ht

lemma claim_le_level_total {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    claims i ≤ PariPassuLevelClaimTotal claims rank i := by
  classical
  unfold PariPassuLevelClaimTotal
  exact Finset.single_le_sum (fun x _ => zero_le (claims x)) (by simp)

lemma pariPassu_payment_le_claim {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal) (i : ι) :
    PariPassuWaterfallDistribution claims rank pool i ≤ claims i := by
  classical
  unfold PariPassuWaterfallDistribution
  by_cases htot : PariPassuLevelClaimTotal claims rank i = 0
  · simp [htot]
  · simp [htot]
    apply nnreal_pro_rata_le_claim
    · exact claim_le_level_total claims rank i
    · exact min_le_right _ _

lemma sum_range_levelClaim_eq_senior {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (n : ℕ) :
    (∑ k ∈ Finset.range n, RankLevelClaim claims rank k) =
      RankSeniorClaim claims rank n := by
  classical
  simp [RankLevelClaim, RankSeniorClaim, Finset.sum_filter, Finset.sum_comm]

lemma sum_range_fibers_eq_univ {ι : Type*} [Fintype ι]
    (rank : ι → ℕ) (N : ℕ) (f : ι → NNReal) (hN : ∀ i, rank i < N) :
    (∑ k ∈ Finset.range N,
      ∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k), f i) =
      ∑ i, f i := by
  classical
  simp [Finset.sum_filter, Finset.sum_comm, hN]

lemma nnreal_min_add_min_tsub (pool s c : NNReal) :
    min pool s + min (pool - s) c = min pool (s + c) := by
  by_cases hs : s ≤ pool
  · have hleft : min pool s = s := min_eq_right hs
    rw [hleft]
    by_cases hc : c ≤ pool - s
    · have hright1 : min (pool - s) c = c := min_eq_right hc
      have hsp : s + c ≤ pool := by
        have := (le_tsub_iff_right hs).1 hc
        simpa [add_comm] using this
      have hright2 : min pool (s + c) = s + c := min_eq_right hsp
      rw [hright1, hright2]
    · have hcp : pool - s ≤ c := le_of_not_ge hc
      have hright1 : min (pool - s) c = pool - s := min_eq_left hcp
      have hright2 : min pool (s + c) = pool := by
        apply min_eq_left
        calc
          pool = s + (pool - s) := by rw [add_tsub_cancel_of_le hs]
          _ ≤ s + c := by simpa [add_comm] using add_le_add_left hcp s
      rw [hright1, hright2]
      rw [add_tsub_cancel_of_le hs]
  · have hps : pool ≤ s := le_of_not_ge hs
    have hleft : min pool s = pool := min_eq_left hps
    have hzero : pool - s = 0 := tsub_eq_zero_of_le hps
    have hright : min pool (s + c) = pool := by
      apply min_eq_left
      exact hps.trans (self_le_add_right s c)
    simp [hleft, hzero, hright]

lemma nnreal_sum_range_min_tsub_eq_min (c : ℕ → NNReal) (pool : NNReal) :
    ∀ n : ℕ,
      (∑ k ∈ Finset.range n, min (pool - ∑ l ∈ Finset.range k, c l) (c k)) =
        min pool (∑ k ∈ Finset.range n, c k) := by
  intro n
  induction n with
  | zero => simp
  | succ n ih =>
      rw [Finset.sum_range_succ, Finset.sum_range_succ, ih]
      exact nnreal_min_add_min_tsub pool (∑ k ∈ Finset.range n, c k) (c n)

lemma pariPassu_payments_sum_le_pool {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal) :
    (∑ i, PariPassuWaterfallDistribution claims rank pool i) ≤ pool := by
  classical
  let N : ℕ := (Finset.univ.image rank).sup (fun k : ℕ => k) + 1
  have hN : ∀ i : ι, rank i < N := by
    intro i
    have hmem : rank i ∈ Finset.univ.image rank := by simp
    have hle : rank i ≤ (Finset.univ.image rank).sup (fun k : ℕ => k) := by
      exact Finset.le_sup (s := Finset.univ.image rank) (f := fun k : ℕ => k) hmem
    exact Nat.lt_succ_of_le hle
  calc
    (∑ i, PariPassuWaterfallDistribution claims rank pool i)
        = (∑ k ∈ Finset.range N,
            ∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k),
              PariPassuWaterfallDistribution claims rank pool i) := by
          exact (sum_range_fibers_eq_univ rank N
            (PariPassuWaterfallDistribution claims rank pool) hN).symm
    _ = (∑ k ∈ Finset.range N,
            min (pool - RankSeniorClaim claims rank k) (RankLevelClaim claims rank k)) := by
          apply Finset.sum_congr rfl
          intro k hk
          exact inner_sum_eq_levelPayment claims rank pool k
    _ = (∑ k ∈ Finset.range N,
            min (pool - ∑ l ∈ Finset.range k, RankLevelClaim claims rank l)
              (RankLevelClaim claims rank k)) := by
          apply Finset.sum_congr rfl
          intro k hk
          rw [sum_range_levelClaim_eq_senior claims rank k]
    _ = min pool (∑ k ∈ Finset.range N, RankLevelClaim claims rank k) := by
          exact nnreal_sum_range_min_tsub_eq_min (RankLevelClaim claims rank) pool N
    _ ≤ pool := min_le_left _ _

lemma pariPassuWaterfallDistribution_feasible_aux
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) :
    DistributionFeasible claims pool (PariPassuWaterfallDistribution claims rank pool) := by
  exact ⟨pariPassu_payment_le_claim claims rank pool,
    pariPassu_payments_sum_le_pool claims rank pool⟩

lemma senior_level_lies_before_junior {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (senior junior : ι) (hsj : RankedStrictlySenior rank senior junior) :
    RankedSeniorClaimsBefore claims rank senior +
      PariPassuLevelClaimTotal claims rank senior ≤
        RankedSeniorClaimsBefore claims rank junior := by
  classical
  change rank senior < rank junior at hsj
  let lower := Finset.univ.filter (fun j : ι => rank j < rank senior)
  let level := Finset.univ.filter (fun j : ι => rank j = rank senior)
  let juniorPrefix := Finset.univ.filter (fun j : ι => rank j < rank junior)
  have hdisj : Disjoint lower level := by
    rw [Finset.disjoint_left]
    intro j hjLower hjLevel
    have hjlt : rank j < rank senior := (Finset.mem_filter.mp hjLower).2
    have hjeq : rank j = rank senior := (Finset.mem_filter.mp hjLevel).2
    exact (lt_irrefl (rank senior)) (by simpa [hjeq] using hjlt)
  have hsubset : lower ∪ level ⊆ juniorPrefix := by
    intro j hj
    rw [Finset.mem_union] at hj
    rw [Finset.mem_filter]
    constructor
    · exact Finset.mem_univ j
    · cases hj with
      | inl hjLower =>
          exact lt_trans (Finset.mem_filter.mp hjLower).2 hsj
      | inr hjLevel =>
          have hjeq : rank j = rank senior := (Finset.mem_filter.mp hjLevel).2
          simpa [hjeq] using hsj
  change (∑ j ∈ lower, claims j) + (∑ j ∈ level, claims j) ≤
    ∑ j ∈ juniorPrefix, claims j
  calc
    (∑ j ∈ lower, claims j) + (∑ j ∈ level, claims j) =
        ∑ j ∈ lower ∪ level, claims j := by
          exact (Finset.sum_union hdisj).symm
    _ ≤ ∑ j ∈ juniorPrefix, claims j := by
          exact Finset.sum_le_sum_of_subset hsubset

lemma positive_payment_implies_prefix_lt_pool {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal) (junior : ι)
    (hpos : 0 < PariPassuWaterfallDistribution claims rank pool junior) :
    RankedSeniorClaimsBefore claims rank junior < pool := by
  by_contra hnot
  have hle : pool ≤ RankedSeniorClaimsBefore claims rank junior := le_of_not_gt hnot
  have hres : PariPassuRankResidual claims rank pool junior = 0 := by
    simp [PariPassuRankResidual, tsub_eq_zero_iff_le, hle]
  have hpay0 : PariPassuWaterfallDistribution claims rank pool junior = 0 := by
    simp [PariPassuWaterfallDistribution, hres]
  rw [hpay0] at hpos
  exact (lt_irrefl (0 : NNReal)) hpos

lemma full_level_pays_tranche {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal) (i : ι) :
    RankedSeniorClaimsBefore claims rank i +
        PariPassuLevelClaimTotal claims rank i < pool →
      PariPassuWaterfallDistribution claims rank pool i = claims i := by
  classical
  intro h
  let S := RankedSeniorClaimsBefore claims rank i
  let T := PariPassuLevelClaimTotal claims rank i
  have hclaim_le : claims i ≤ T := by
    dsimp [T]
    unfold PariPassuLevelClaimTotal
    exact Finset.single_le_sum (fun x _ => zero_le (claims x)) (by simp)
  have hT_le_residual : T ≤ pool - S := by
    dsimp [T, S]
    exact le_tsub_of_add_le_left (le_of_lt h)
  by_cases hT : T = 0
  · have hclaim0 : claims i = 0 := by
      exact le_antisymm (hclaim_le.trans (le_of_eq hT)) (zero_le _)
    simp [PariPassuWaterfallDistribution, T, hT, hclaim0]
  · have hmin : min (pool - S) T = T := min_eq_right hT_le_residual
    simp [PariPassuWaterfallDistribution, PariPassuRankResidual, S, T, hT, hmin, div_mul_cancel₀]

theorem pariPassuWaterfallDistribution_feasible_and_ranked_absolutePriority : ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal), DistributionFeasible claims pool
        (PariPassuWaterfallDistribution claims rank pool) ∧
      (∀ senior junior : ι,
        RankedStrictlySenior rank senior junior →
          0 < PariPassuWaterfallDistribution claims rank pool junior →
            PariPassuWaterfallDistribution claims rank pool senior = claims senior) := by
  intro ι _ claims rank pool
  refine ⟨pariPassuWaterfallDistribution_feasible_aux claims rank pool, ?_⟩
  intro senior junior hsj hpos
  apply full_level_pays_tranche
  exact lt_of_le_of_lt
    (senior_level_lies_before_junior claims rank senior junior hsj)
    (positive_payment_implies_prefix_lt_pool claims rank pool junior hpos)

#print axioms pariPassuWaterfallDistribution_feasible_and_ranked_absolutePriority
