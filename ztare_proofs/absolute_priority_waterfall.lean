import Mathlib

/-! # Absolute priority liquidation waterfall substrate -/

namespace AbsolutePriorityWaterfall

/-!
Definition trial notes for this dispatch:
* Claims/payments candidate A: use plain `ι → ℝ` with nonnegativity side
  conditions.  Rejected for the substrate because every theorem must then carry
  repetitive `0 ≤ ...` hypotheses.
* Claims/payments candidate B: use `ι → NNReal`.  Selected as
  `ClaimSchedule`/`PaymentSchedule`; nonnegativity is built into the type, and
  finite sums over payments use Mathlib's ordered additive API directly.
* Priority candidate A: require a total seniority chain everywhere.  Rejected
  for the APR predicate because the blueprint allows partial priority orders.
* Priority candidate B: use any `Preorder ι` for the APR relation and specialize
  the closed-form waterfall theorem statements to `LinearOrder ι`.  Selected:
  the predicate covers partial orders, while the first waterfall formula has a
  clear finite-chain proof target.
* Waterfall formula candidate A: recursive list processing.  Rejected for the
  general substrate because it bakes in a list order rather than the tranche
  priority relation.
* Waterfall formula candidate B: closed form
  `min claim_i (pool - senior_claims_before_i)`.  Selected for finite chains;
  it proves immediate cap sanity lemmas and exposes the remaining feasibility
  and APR proofs as clean solver work items.
-/

/-- Nonnegative face-value claims indexed by creditor tranche. -/
abbrev ClaimSchedule (ι : Type*) := ι → NNReal

/-- Nonnegative liquidation payments indexed by creditor tranche. -/
abbrev PaymentSchedule (ι : Type*) := ι → NNReal

/-- Anchor: claim schedules are exactly functions into Mathlib `NNReal`. -/
theorem anchor_ClaimSchedule_eq_function (ι : Type*) :
    ClaimSchedule ι = (ι → NNReal) := by
  rfl

/-- Anchor: payment schedules are exactly functions into Mathlib `NNReal`. -/
theorem anchor_PaymentSchedule_eq_function (ι : Type*) :
    PaymentSchedule ι = (ι → NNReal) := by
  rfl

/-- Feasibility of a liquidation distribution: no tranche receives above its
claim, and aggregate payments do not exceed the available pool.  Nonnegativity
is carried by `NNReal`. -/
def DistributionFeasible {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) : Prop :=
  (∀ i : ι, pay i ≤ claims i) ∧ (∑ i, pay i) ≤ pool

/-- Anchor: feasibility is the primitive cap plus Mathlib finite-sum budget
condition. -/
theorem anchor_DistributionFeasible_iff
    {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) :
    DistributionFeasible claims pool pay ↔
      (∀ i : ι, pay i ≤ claims i) ∧ (∑ i, pay i) ≤ pool := by
  rfl

/-- Absolute Priority Rule: if a tranche receives a positive payment, every
strictly senior tranche has been paid in full. -/
def AbsolutePriority {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) : Prop :=
  ∀ senior junior : ι, senior < junior → 0 < pay junior → pay senior = claims senior

/-- Anchor: APR is exactly the primitive senior-before-positive-junior
full-payment implication. -/
theorem anchor_AbsolutePriority_iff
    {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) :
    AbsolutePriority claims pay ↔
      ∀ senior junior : ι, senior < junior → 0 < pay junior → pay senior = claims senior := by
  rfl

/-- Anchor: under feasibility, APR is equivalent to the no-leapfrog
formulation: if a senior tranche is unfilled, every junior tranche receives
zero. -/
theorem anchor_AbsolutePriority_iff_no_junior_leapfrog_of_feasible
    {ι : Type*} [Fintype ι] [Preorder ι]
    {claims : ClaimSchedule ι} {pool : NNReal} {pay : PaymentSchedule ι}
    (hfeas : DistributionFeasible claims pool pay) :
    AbsolutePriority claims pay ↔
      ∀ senior junior : ι, senior < junior → pay senior < claims senior → pay junior = 0 := by
  constructor
  · intro hapr senior junior hsj hunfilled
    by_contra hne
    have hpos : 0 < pay junior := pos_iff_ne_zero.mpr hne
    have hfull : pay senior = claims senior := hapr senior junior hsj hpos
    exact (lt_irrefl (claims senior)) (by simpa [hfull] using hunfilled)
  · intro hno senior junior hsj hpos
    have hle : pay senior ≤ claims senior := hfeas.1 senior
    by_contra hne
    have hlt : pay senior < claims senior := lt_of_le_of_ne hle hne
    have hzero : pay junior = 0 := hno senior junior hsj hlt
    simpa [hzero] using hpos

/-- A live APR scenario: some junior tranche receives a positive payment. -/
def APRTriggered {ι : Type*} [Preorder ι] (pay : PaymentSchedule ι) : Prop :=
  ∃ senior junior : ι, senior < junior ∧ 0 < pay junior

/-- Anchor: triggering is just existence of an ordered senior/junior pair with
positive junior payment. -/
theorem anchor_APRTriggered_iff
    {ι : Type*} [Preorder ι] (pay : PaymentSchedule ι) :
    APRTriggered pay ↔ ∃ senior junior : ι, senior < junior ∧ 0 < pay junior := by
  rfl

/-- APR bundled with a proof that the priority implication is exercised by a
positive junior payment. -/
structure NonvacuousAbsolutePriority {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) : Prop where
  apr : AbsolutePriority claims pay
  triggered : APRTriggered pay

/-- Anchor: the nonvacuous APR bundle is exactly APR plus the trigger witness. -/
theorem anchor_NonvacuousAbsolutePriority_iff
    {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) :
    NonvacuousAbsolutePriority claims pay ↔ AbsolutePriority claims pay ∧ APRTriggered pay := by
  constructor
  · intro h
    exact ⟨h.apr, h.triggered⟩
  · intro h
    exact ⟨h.1, h.2⟩

/-- The zero liquidation payment schedule. -/
def ZeroPayment (ι : Type*) : PaymentSchedule ι :=
  fun _ => 0

/-- Anchor: the zero payment schedule is pointwise zero. -/
theorem anchor_ZeroPayment_apply (ι : Type*) (i : ι) :
    ZeroPayment ι i = 0 := by
  rfl

/-- Witness: zero payments are feasible for a zero pool. -/
theorem witness_DistributionFeasible_zero
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) :
    DistributionFeasible claims 0 (ZeroPayment ι) := by
  constructor
  · intro i
    exact zero_le (claims i)
  · simp [ZeroPayment]

/-- Witness: zero payments satisfy APR, but only vacuously. -/
theorem witness_AbsolutePriority_zero
    {ι : Type*} [Preorder ι] (claims : ClaimSchedule ι) :
    AbsolutePriority claims (ZeroPayment ι) := by
  intro senior junior hsj hpos
  exact False.elim (by simpa [ZeroPayment] using hpos)

-- @vacuity-scope: AbsolutePriority: `ZeroPayment` satisfies APR because no
-- junior tranche receives a positive distribution.  Use
-- `NonvacuousAbsolutePriority` or `APRTriggered` when a theorem must certify a
-- live positive junior-payment scenario rather than the zero-liquidation case.

def boolTwoTrancheClaims : ClaimSchedule Bool :=
  fun _ => 1

def boolTwoTrancheFullPay : PaymentSchedule Bool :=
  fun _ => 1

/-- Witness: APR is not merely a zero-pool artifact; in the two-tranche chain,
a positive junior payment is compatible with APR exactly because the senior
tranche is paid in full. -/
theorem witness_NonvacuousAbsolutePriority_bool_full :
    NonvacuousAbsolutePriority boolTwoTrancheClaims boolTwoTrancheFullPay := by
  constructor
  · intro senior junior hsj hpos
    rfl
  · exact ⟨false, true, by decide, by norm_num [boolTwoTrancheFullPay]⟩

/-- Witness: full payment of both Boolean tranches is feasible from a pool of
two units. -/
theorem witness_DistributionFeasible_bool_full :
    DistributionFeasible boolTwoTrancheClaims 2 boolTwoTrancheFullPay := by
  constructor
  · intro i
    rfl
  · norm_num [boolTwoTrancheFullPay]

/-- Claim mass senior to a tranche, for finite priority sets.  This is the
selected formula substrate for a total seniority chain; partial orders can use
the same senior-set expression, but feasibility of the min formula needs extra
no-double-counting hypotheses when incomparable tranches coexist. -/
noncomputable def SeniorClaimsBefore {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (i : ι) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => j < i), claims j

/-- Anchor: senior claims before a tranche are the Mathlib finite sum over the
filtered set of strictly senior tranches. -/
theorem anchor_SeniorClaimsBefore_eq_finset_sum
    {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (i : ι) :
    SeniorClaimsBefore claims i =
      (by classical
          exact ∑ j ∈ Finset.univ.filter (fun j : ι => j < i), claims j) := by
  rfl

/-- A closed-form seniority waterfall for a finite chain: tranche `i` receives
its claim capped by the residual pool after all senior claims. -/
noncomputable def WaterfallDistribution {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) : PaymentSchedule ι :=
  fun i => min (claims i) (pool - SeniorClaimsBefore claims i)

/-- Anchor: the closed-form waterfall is claim capped by residual value after
senior claims. -/
theorem anchor_WaterfallDistribution_apply
    {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (i : ι) :
    WaterfallDistribution claims pool i = min (claims i) (pool - SeniorClaimsBefore claims i) := by
  rfl

/-- Sanity: the closed-form waterfall never pays a tranche above its claim. -/
theorem waterfallDistribution_le_claim
    {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (i : ι) :
    WaterfallDistribution claims pool i ≤ claims i := by
  exact min_le_left _ _

/-- Sanity: with zero pool and no senior claims before a tranche, that tranche
receives zero. -/
theorem waterfallDistribution_zero_pool_zero_of_no_seniors
    {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) {i : ι} (hsenior : SeniorClaimsBefore claims i = 0) :
    WaterfallDistribution claims 0 i = 0 := by
  simp [WaterfallDistribution, hsenior]

/-- Target-shaped conclusion for a concrete liquidation distribution. -/
structure WaterfallConclusion {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) : Prop where
  feasible : DistributionFeasible claims pool pay
  absolute_priority : AbsolutePriority claims pay

/-- Anchor: the conclusion bundle is exactly feasibility plus APR. -/
theorem anchor_WaterfallConclusion_iff
    {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) :
    WaterfallConclusion claims pool pay ↔
      DistributionFeasible claims pool pay ∧ AbsolutePriority claims pay := by
  constructor
  · intro h
    exact ⟨h.feasible, h.absolute_priority⟩
  · intro h
    exact ⟨h.1, h.2⟩

/-- Witness: the zero payment schedule gives a feasible APR conclusion at zero
pool. -/
theorem witness_WaterfallConclusion_zero
    {ι : Type*} [Fintype ι] [Preorder ι] (claims : ClaimSchedule ι) :
    WaterfallConclusion claims 0 (ZeroPayment ι) := by
  constructor
  · exact witness_DistributionFeasible_zero claims
  · exact witness_AbsolutePriority_zero claims

/-- Solver work item: for a finite total seniority chain, the closed-form
waterfall is feasible. -/
theorem waterfallDistribution_feasible_of_linearOrder
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) :
    DistributionFeasible claims pool (WaterfallDistribution claims pool) := by
  sorry

/-- Solver work item: for a finite total seniority chain, the closed-form
waterfall satisfies APR. -/
theorem waterfallDistribution_absolutePriority_of_linearOrder
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) :
    AbsolutePriority claims (WaterfallDistribution claims pool) := by
  sorry

/-- Solver work item: target theorem for the selected finite-chain waterfall. -/
theorem waterfallDistribution_conclusion_of_linearOrder
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) :
    WaterfallConclusion claims pool (WaterfallDistribution claims pool) := by
  exact ⟨waterfallDistribution_feasible_of_linearOrder claims pool,
    waterfallDistribution_absolutePriority_of_linearOrder claims pool⟩

end AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma3__6d4d575f
theorem iso_lemma3__6d4d575f : ∀ (a b c pool : NNReal) (hsum : a + b ≤ c) (hc : c < pool), b ≤ pool - a := by
  intro a b c pool hsum hc
  have hle : b + a ≤ pool := by
    calc
      b + a = a + b := by rw [add_comm]
      _ ≤ c := hsum
      _ ≤ pool := le_of_lt hc
  have ha : a ≤ pool := by
    exact le_trans
      (by simpa [add_comm] using le_add_of_nonneg_left (show 0 ≤ b by exact zero_le b))
      hle
  exact (le_tsub_iff_right ha).2 hle

-- [family-lemma-library] banked: iso_lemma_exists_strict_rank__b9463cc6
theorem iso_lemma_exists_strict_rank__b9463cc6 : ∀ {ι : Type*} [Fintype ι] [Preorder ι], ∃ rank : ι → ℕ,
      ∀ senior junior : ι, senior < junior → rank senior < rank junior := by
  intro ι _ _
  classical
  refine ⟨fun i => (Finset.univ.filter fun j : ι => j < i).card, ?_⟩
  intro senior junior hsj
  apply Finset.card_lt_card
  rw [Finset.ssubset_iff_subset_ne]
  constructor
  · intro i hi
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hi ⊢
    exact lt_trans hi hsj
  · intro hsets
    have hmem_junior : senior ∈ Finset.univ.filter (fun j : ι => j < junior) := by
      simp [hsj]
    have hmem_senior : senior ∈ Finset.univ.filter (fun j : ι => j < senior) := by
      simpa [hsets] using hmem_junior
    have hself : senior < senior := by
      simpa using hmem_senior
    exact (lt_irrefl senior) hself

-- [family-lemma-library] banked: iso_lemma_exists_strict_rank__008eaae7
theorem iso_lemma_exists_strict_rank__008eaae7 {ι : Type*} [Fintype ι] [Preorder ι] :
    ∃ rank : ι → ℕ,
      ∀ senior junior : ι, senior < junior → rank senior < rank junior := by
  exact?

namespace AbsolutePriorityWaterfall

/-!
Pari-passu design trial notes for the ranked generalization:
* Candidate A: put `[LinearOrder ι]` on tranches and detect ties by equality.
  Rejected because equality of tranche indices is not equal seniority and cannot
  represent two distinct pari-passu claims.
* Candidate B: use an arbitrary preorder on `ι` and quotient incomparable
  elements into levels.  Rejected for the initial substrate because quotient
  bookkeeping obscures the finite-sum sanity checks.
* Candidate C: use a concrete seniority rank `rank : ι → ℕ`, where lower rank
  means stricter seniority and equal rank means pari-passu.  Selected: it admits
  ties without any order on `ι`, and all level totals are Mathlib finite sums.
-/

/-- Strict seniority induced by a ranked priority map.  Lower natural-number
rank means more senior. -/
def RankedStrictlySenior {ι : Type*} (rank : ι → ℕ) (senior junior : ι) : Prop :=
  rank senior < rank junior

/-- Anchor: ranked strict seniority is just Mathlib's strict order on the rank
values. -/
theorem anchor_RankedStrictlySenior_iff
    {ι : Type*} (rank : ι → ℕ) (senior junior : ι) :
    RankedStrictlySenior rank senior junior ↔ rank senior < rank junior := by
  rfl

/-- Total claims in the pari-passu level containing `i`. -/
noncomputable def PariPassuLevelClaimTotal
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j = rank i), claims j

/-- Anchor: level claim total is the Mathlib finite sum over tranches with the
same rank. -/
theorem anchor_PariPassuLevelClaimTotal_eq_finset_sum
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    PariPassuLevelClaimTotal claims rank i =
      (by classical
          exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j = rank i), claims j) := by
  rfl

/-- Claims strictly senior to the rank level of `i`. -/
noncomputable def RankedSeniorClaimsBefore
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j < rank i), claims j

/-- Anchor: ranked senior claims are the finite sum over lower-rank tranches. -/
theorem anchor_RankedSeniorClaimsBefore_eq_finset_sum
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    RankedSeniorClaimsBefore claims rank i =
      (by classical
          exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j < rank i), claims j) := by
  rfl

/-- Residual value available when the waterfall reaches `i`'s rank level. -/
noncomputable def PariPassuRankResidual
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) (i : ι) : NNReal :=
  pool - RankedSeniorClaimsBefore claims rank i

/-- Anchor: residual value is pool minus the Mathlib finite sum of strictly
senior ranked claims. -/
theorem anchor_PariPassuRankResidual_eq_tsub
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) (i : ι) :
    PariPassuRankResidual claims rank pool i =
      pool - RankedSeniorClaimsBefore claims rank i := by
  rfl

/-- Ranked pari-passu waterfall.  Each level receives the residual capped by
that level's aggregate claim; tranches inside the level share that level
payment pro-rata by claim size. -/
noncomputable def PariPassuWaterfallDistribution
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) : PaymentSchedule ι :=
  fun i =>
    let levelTotal := PariPassuLevelClaimTotal claims rank i
    let levelPayment := min (PariPassuRankResidual claims rank pool i) levelTotal
    if levelTotal = 0 then 0 else (claims i / levelTotal) * levelPayment

/-- Anchor: the pari-passu waterfall is the pro-rata share of the capped level
payment. -/
theorem anchor_PariPassuWaterfallDistribution_apply
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) (i : ι) :
    PariPassuWaterfallDistribution claims rank pool i =
      let levelTotal := PariPassuLevelClaimTotal claims rank i
      let levelPayment := min (PariPassuRankResidual claims rank pool i) levelTotal
      if levelTotal = 0 then 0 else (claims i / levelTotal) * levelPayment := by
  rfl

/-- APR for ranked seniority: only strictly lower ranks must be full before a
positive junior-rank payment. Equal-rank pari-passu tranches do not block one
another. -/
def RankedAbsolutePriority {ι : Type*} (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pay : PaymentSchedule ι) : Prop :=
  ∀ senior junior : ι,
    RankedStrictlySenior rank senior junior → 0 < pay junior → pay senior = claims senior

/-- Anchor: ranked APR is the primitive no-leapfrog implication over lower
rank values. -/
theorem anchor_RankedAbsolutePriority_iff
    {ι : Type*} (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pay : PaymentSchedule ι) :
    RankedAbsolutePriority claims rank pay ↔
      ∀ senior junior : ι,
        rank senior < rank junior → 0 < pay junior → pay senior = claims senior := by
  rfl

/-- Conclusion bundle for ranked pari-passu waterfalls. -/
structure RankedWaterfallConclusion {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal)
    (pay : PaymentSchedule ι) : Prop where
  feasible : DistributionFeasible claims pool pay
  absolute_priority : RankedAbsolutePriority claims rank pay

/-- Anchor: the ranked conclusion bundle is exactly feasibility plus ranked
APR. -/
theorem anchor_RankedWaterfallConclusion_iff
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) (pay : PaymentSchedule ι) :
    RankedWaterfallConclusion claims rank pool pay ↔
      DistributionFeasible claims pool pay ∧ RankedAbsolutePriority claims rank pay := by
  constructor
  · intro h
    exact ⟨h.feasible, h.absolute_priority⟩
  · intro h
    exact ⟨h.1, h.2⟩

/-- A nonvacuous equal-rank split: two distinct pari-passu tranches both
receive positive partial payment. -/
def GenuinePariPassuSplit {ι : Type*} (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pay : PaymentSchedule ι) : Prop :=
  ∃ i j : ι,
    i ≠ j ∧ rank i = rank j ∧ 0 < pay i ∧ pay i < claims i ∧
      0 < pay j ∧ pay j < claims j

/-- Anchor: a genuine pari-passu split is the primitive existence of two
distinct equal-rank tranches with positive, partial payments. -/
theorem anchor_GenuinePariPassuSplit_iff
    {ι : Type*} (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pay : PaymentSchedule ι) :
    GenuinePariPassuSplit claims rank pay ↔
      ∃ i j : ι,
        i ≠ j ∧ rank i = rank j ∧ 0 < pay i ∧ pay i < claims i ∧
          0 < pay j ∧ pay j < claims j := by
  rfl

def boolEqualRankClaims : ClaimSchedule Bool :=
  fun _ => 1

def boolEqualRank : Bool → ℕ :=
  fun _ => 0

theorem witness_PariPassuLevelClaimTotal_bool_false :
    PariPassuLevelClaimTotal boolEqualRankClaims boolEqualRank false = 2 := by
  norm_num [PariPassuLevelClaimTotal, boolEqualRankClaims, boolEqualRank]

theorem witness_RankedSeniorClaimsBefore_bool_false :
    RankedSeniorClaimsBefore boolEqualRankClaims boolEqualRank false = 0 := by
  norm_num [RankedSeniorClaimsBefore, boolEqualRank]

theorem witness_PariPassuWaterfallDistribution_bool_false :
    PariPassuWaterfallDistribution boolEqualRankClaims boolEqualRank 1 false = (1 / 2 : NNReal) := by
  norm_num [PariPassuWaterfallDistribution, PariPassuLevelClaimTotal,
    PariPassuRankResidual, RankedSeniorClaimsBefore, boolEqualRankClaims, boolEqualRank]

theorem witness_PariPassuWaterfallDistribution_bool_true :
    PariPassuWaterfallDistribution boolEqualRankClaims boolEqualRank 1 true = (1 / 2 : NNReal) := by
  norm_num [PariPassuWaterfallDistribution, PariPassuLevelClaimTotal,
    PariPassuRankResidual, RankedSeniorClaimsBefore, boolEqualRankClaims, boolEqualRank]

/-- Witness: the ranked substrate admits a genuine pari-passu case with two
equal-rank tranches splitting an insufficient pool pro-rata. -/
theorem witness_GenuinePariPassuSplit_bool_equal_rank :
    GenuinePariPassuSplit boolEqualRankClaims boolEqualRank
      (PariPassuWaterfallDistribution boolEqualRankClaims boolEqualRank 1) := by
  refine ⟨false, true, by decide, rfl, ?_, ?_, ?_, ?_⟩
  · rw [witness_PariPassuWaterfallDistribution_bool_false]
    norm_num
  · rw [witness_PariPassuWaterfallDistribution_bool_false]
    norm_num [boolEqualRankClaims]
  · rw [witness_PariPassuWaterfallDistribution_bool_true]
    norm_num
  · rw [witness_PariPassuWaterfallDistribution_bool_true]
    norm_num [boolEqualRankClaims]

/-- Solver work item: the ranked pari-passu waterfall never overpays an
individual claim and never distributes more than the pool. -/
theorem pariPassuWaterfallDistribution_feasible
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) :
    DistributionFeasible claims pool (PariPassuWaterfallDistribution claims rank pool) := by
  sorry

/-- Solver work item: the ranked pari-passu waterfall satisfies APR for
strictly lower-rank seniors. -/
theorem pariPassuWaterfallDistribution_rankedAbsolutePriority
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) :
    RankedAbsolutePriority claims rank (PariPassuWaterfallDistribution claims rank pool) := by
  sorry

/-- Solver work item: the ranked pari-passu waterfall has both feasibility and
ranked APR. -/
theorem pariPassuWaterfallDistribution_conclusion
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) :
    RankedWaterfallConclusion claims rank pool
      (PariPassuWaterfallDistribution claims rank pool) := by
  exact ⟨pariPassuWaterfallDistribution_feasible claims rank pool,
    pariPassuWaterfallDistribution_rankedAbsolutePriority claims rank pool⟩

/-- Anchor: the Bool pari-passu witness assigns unit claim to each tranche. -/
theorem anchor_boolEqualRankClaims_apply (i : Bool) :
    boolEqualRankClaims i = 1 := by
  rfl

/-- Anchor: the Bool pari-passu witness puts both tranches in the same rank. -/
theorem anchor_boolEqualRank_apply (i : Bool) :
    boolEqualRank i = 0 := by
  rfl

/-- Sanity: the existing strict-chain waterfall conclusion remains available
as the banked special case; the ranked pari-passu substrate is an extension,
not a replacement. -/
theorem witness_strictChainWaterfallConclusion_cites_banked
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) :
    WaterfallConclusion claims pool (WaterfallDistribution claims pool) := by
  exact waterfallDistribution_conclusion_of_linearOrder claims pool

end AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma2__e625874a
theorem iso_lemma2__e625874a : ∀ (claim total levelPayment : NNReal),
    claim ≤ total → levelPayment ≤ total → total ≠ 0 →
    (claim / total) * levelPayment ≤ claim := by
  intro claim total levelPayment hclaim hlevel htotal
  calc
    (claim / total) * levelPayment ≤ (claim / total) * total := by
      exact mul_le_mul_left' hlevel (claim / total)
    _ = claim := by
      rw [div_mul_cancel₀ claim htotal]

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: RankLevelClaim
noncomputable def RankLevelClaim
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (k : ℕ) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j = k), claims j

-- [family-lemma-library] banked: RankSeniorClaim
noncomputable def RankSeniorClaim
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (k : ℕ) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => rank j < k), claims j

-- [family-lemma-library] banked: levelTotal_eq_rankLevel
lemma levelTotal_eq_rankLevel {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) {i : ι} {k : ℕ}
    (hik : rank i = k) :
    PariPassuLevelClaimTotal claims rank i = RankLevelClaim claims rank k := by
  classical
  simp [PariPassuLevelClaimTotal, RankLevelClaim, hik]

-- [family-lemma-library] banked: seniorBefore_eq_rankSenior
lemma seniorBefore_eq_rankSenior {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) {i : ι} {k : ℕ}
    (hik : rank i = k) :
    RankedSeniorClaimsBefore claims rank i = RankSeniorClaim claims rank k := by
  classical
  simp [RankedSeniorClaimsBefore, RankSeniorClaim, hik]

-- [family-lemma-library] banked: inner_sum_eq_levelPayment
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

-- [family-lemma-library] banked: nnreal_pro_rata_le_claim
lemma nnreal_pro_rata_le_claim {c t p : NNReal} (hc : c ≤ t) (hp : p ≤ t) :
    c / t * p ≤ c := by
  by_cases ht : t = 0
  · have hc0 : c = 0 := le_antisymm (hc.trans (le_of_eq ht)) (zero_le c)
    simp [hc0]
  · calc
      c / t * p ≤ c / t * t := by exact mul_le_mul_left' hp (c / t)
      _ = c := div_mul_cancel₀ c ht

-- [family-lemma-library] banked: claim_le_level_total
lemma claim_le_level_total {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (i : ι) :
    claims i ≤ PariPassuLevelClaimTotal claims rank i := by
  classical
  unfold PariPassuLevelClaimTotal
  exact Finset.single_le_sum (fun x _ => zero_le (claims x)) (by simp)

-- [family-lemma-library] banked: pariPassu_payment_le_claim
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

-- [family-lemma-library] banked: sum_range_levelClaim_eq_senior
lemma sum_range_levelClaim_eq_senior {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (n : ℕ) :
    (∑ k ∈ Finset.range n, RankLevelClaim claims rank k) =
      RankSeniorClaim claims rank n := by
  classical
  simp [RankLevelClaim, RankSeniorClaim, Finset.sum_filter, Finset.sum_comm]

-- [family-lemma-library] banked: sum_range_fibers_eq_univ
lemma sum_range_fibers_eq_univ {ι : Type*} [Fintype ι]
    (rank : ι → ℕ) (N : ℕ) (f : ι → NNReal) (hN : ∀ i, rank i < N) :
    (∑ k ∈ Finset.range N,
      ∑ i ∈ Finset.univ.filter (fun i : ι => rank i = k), f i) =
      ∑ i, f i := by
  classical
  simp [Finset.sum_filter, Finset.sum_comm, hN]

-- [family-lemma-library] banked: nnreal_min_add_min_tsub
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

-- [family-lemma-library] banked: nnreal_sum_range_min_tsub_eq_min
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

-- [family-lemma-library] banked: pariPassu_payments_sum_le_pool
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

-- [family-lemma-library] banked: pariPassuWaterfallDistribution_feasible__6c5763bf
theorem pariPassuWaterfallDistribution_feasible__6c5763bf : ∀ {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal), DistributionFeasible claims pool (PariPassuWaterfallDistribution claims rank pool) := by
  intro ι _ claims rank pool
  exact ⟨pariPassu_payment_le_claim claims rank pool,
    pariPassu_payments_sum_le_pool claims rank pool⟩

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma_senior_level_lies_before_junior__0da84eff
theorem iso_lemma_senior_level_lies_before_junior__0da84eff : ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (senior junior : ι) (hsj : RankedStrictlySenior rank senior junior), RankedSeniorClaimsBefore claims rank senior +
      PariPassuLevelClaimTotal claims rank senior ≤
        RankedSeniorClaimsBefore claims rank junior := by
  intro ι _ claims rank senior junior hsj
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

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma_positive_payment_implies_prefix_lt_pool__679cf0a0
theorem iso_lemma_positive_payment_implies_prefix_lt_pool__679cf0a0 : ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) (junior : ι)
    (hpos : 0 < PariPassuWaterfallDistribution claims rank pool junior), RankedSeniorClaimsBefore claims rank junior < pool := by
  intro ι _ claims rank pool junior hpos
  by_contra hnot
  have hle : pool ≤ RankedSeniorClaimsBefore claims rank junior := le_of_not_gt hnot
  have hres : PariPassuRankResidual claims rank pool junior = 0 := by
    simp [PariPassuRankResidual, tsub_eq_zero_iff_le, hle]
  have hpay0 : PariPassuWaterfallDistribution claims rank pool junior = 0 := by
    simp [PariPassuWaterfallDistribution, hres]
  rw [hpay0] at hpos
  exact (lt_irrefl (0 : NNReal)) hpos

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma_positive_payment_implies_prefix_lt_pool__c1aae27a
theorem iso_lemma_positive_payment_implies_prefix_lt_pool__c1aae27a :
    ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
      (pool : NNReal) (junior : ι),
      0 < PariPassuWaterfallDistribution claims rank pool junior →
        RankedSeniorClaimsBefore claims rank junior < pool := by
  exact?

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma_senior_level_lies_before_junior__700e1846
theorem iso_lemma_senior_level_lies_before_junior__700e1846 :
    ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
      (senior junior : ι),
      RankedStrictlySenior rank senior junior →
        RankedSeniorClaimsBefore claims rank senior +
          PariPassuLevelClaimTotal claims rank senior ≤
            RankedSeniorClaimsBefore claims rank junior := by
  exact?

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma_full_level_pays_tranche__ce7a4f05
theorem iso_lemma_full_level_pays_tranche__ce7a4f05 : ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
      (pool : NNReal) (i : ι),
      RankedSeniorClaimsBefore claims rank i +
          PariPassuLevelClaimTotal claims rank i < pool →
        PariPassuWaterfallDistribution claims rank pool i = claims i := by
  classical
  intro ι inst claims rank pool i h
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

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: iso_lemma_feasible__6c5763bf
theorem iso_lemma_feasible__6c5763bf : ∀ {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (rank : ι → ℕ) (pool : NNReal),
    DistributionFeasible claims pool
      (PariPassuWaterfallDistribution claims rank pool) := by
  intro ι _ claims rank pool
  exact ⟨pariPassu_payment_le_claim claims rank pool,
    pariPassu_payments_sum_le_pool claims rank pool⟩

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open AbsolutePriorityWaterfall

-- [family-lemma-library] banked: pariPassuWaterfallDistribution_feasible_aux
lemma pariPassuWaterfallDistribution_feasible_aux
    {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
    (pool : NNReal) :
    DistributionFeasible claims pool (PariPassuWaterfallDistribution claims rank pool) := by
  exact ⟨pariPassu_payment_le_claim claims rank pool,
    pariPassu_payments_sum_le_pool claims rank pool⟩

-- [family-lemma-library] banked: senior_level_lies_before_junior
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

-- [family-lemma-library] banked: positive_payment_implies_prefix_lt_pool
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

-- [family-lemma-library] banked: full_level_pays_tranche
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

-- [family-lemma-library] banked: pariPassuWaterfallDistribution_feasible_and_ranked_absolutePriority__4ebb38ff
theorem pariPassuWaterfallDistribution_feasible_and_ranked_absolutePriority__4ebb38ff : ∀ {ι : Type*} [Fintype ι] (claims : ClaimSchedule ι) (rank : ι → ℕ)
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

end
