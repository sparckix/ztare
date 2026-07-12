/-
LeanMill campaign provenance — waterfallDistribution_feasible_of_linearOrder
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=apr_waterfall) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : finance
  time        : wall 4413.08s launch→close = formalize 1921.11s (theory+statement+firewall) + prove 2491.97s (proof search) · prove p50 2407.59s p95 3685.8s
  compute     : cost-to-closure 1724.5s mean · 3308.76s total
  yield       : 16/55 attempts closed (34 failed)
  phases      : 183.4s formalize · 145.1s pool · 44.1s native · 5.8s govern.mnc
  reuse       : cited 0 banked rung(s)
  moves       : native_hammer×27 · claude_warm×16 · proposer_pool×6 · conjecture_lemma×5 · cache_reuse×1
  milestone   : campaign family 'apr_waterfall' — 1 run(s) · REAL elapsed (launch→last) 4788.8s (~80 min) = formalize 0s + prove/other · active-solve 3308.8s · 16 closures [launch→last is the honest wall]
     - apr_waterfall: 16/55 closed · elapsed 4788.82s (~79.8 min)
-/
/-
Corporate-waterfall Absolute Priority Rule (APR) — the closed-form liquidation waterfall is
FEASIBLE and satisfies ABSOLUTE PRIORITY, for an arbitrary finite priority order of creditor
tranches and ANY available pool value.

Machine-checked end-to-end by the LeanMill harness (2026-06-24). Axiom-clean: every theorem
depends only on `[propext, Classical.choice, Quot.sound]` — no `sorryAx`, no `native_decide`.

  • WaterfallDistribution claims pool i := min (claims i) (pool − SeniorClaimsBefore claims i)
    — pay each tranche its claim, capped by the residual after all strictly-senior claims.
  • WaterfallConclusion bundles the full claim:
      feasible          : every tranche's payment ≤ its claim, and the total paid ≤ the pool;
      absolute_priority : whenever a tranche receives a strictly positive payment, every tranche
                          senior to it is paid its claim in full.

The headline theorem `waterfallDistribution_conclusion` is proved by composing the two banked
rungs `waterfallDistribution_feasible_of_linearOrder` + `waterfallDistribution_absolutePriority_of_linearOrder`
— a real dependency graph, not a re-derivation. The substantive content is the sorted-list mass
identity (`waterfall_sum_eq_min`: the waterfall distributes exactly `min pool (∑ claims)`) and the
senior-claims monotonicity (`seniorClaim_le_juniorSeniorClaims`).
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/corporate_waterfalls_apr_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

abbrev ClaimSchedule (ι : Type*) := ι → NNReal

abbrev PaymentSchedule (ι : Type*) := ι → NNReal

def DistributionFeasible {ι : Type*} [Fintype ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) : Prop :=
  (∀ i : ι, pay i ≤ claims i) ∧ (∑ i, pay i) ≤ pool

noncomputable def SeniorClaimsBefore {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (i : ι) : NNReal := by
  classical
  exact ∑ j ∈ Finset.univ.filter (fun j : ι => j < i), claims j

noncomputable def WaterfallDistribution {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) : PaymentSchedule ι :=
  fun i => min (claims i) (pool - SeniorClaimsBefore claims i)

def AbsolutePriority {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) : Prop :=
  ∀ senior junior : ι, senior < junior → 0 < pay junior → pay senior = claims senior

def APRTriggered {ι : Type*} [Preorder ι] (pay : PaymentSchedule ι) : Prop :=
  ∃ senior junior : ι, senior < junior ∧ 0 < pay junior

/-- The nonvacuous APR bundle is exactly APR plus the trigger witness. -/
structure NonvacuousAbsolutePriority {ι : Type*} [Preorder ι]
    (claims : ClaimSchedule ι) (pay : PaymentSchedule ι) : Prop where
  apr : AbsolutePriority claims pay
  triggered : APRTriggered pay

/-- The conclusion bundle is exactly feasibility plus APR. -/
structure WaterfallConclusion {ι : Type*} [Fintype ι] [Preorder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (pay : PaymentSchedule ι) : Prop where
  feasible : DistributionFeasible claims pool pay
  absolute_priority : AbsolutePriority claims pay

private theorem nnreal_min_add_min_tsub (x p y : NNReal) :
    min x p + min (p - x) y = min p (x + y) := by
  rcases le_total p x with hp | hx
  · have hpx : p - x = 0 := tsub_eq_zero_of_le hp
    rw [min_eq_right hp, hpx, min_eq_left (zero_le y), min_eq_left (le_add_right hp)]
    simp
  · have hpx : x + (p - x) = p := add_tsub_cancel_of_le hx
    rw [min_eq_left hx]
    rcases le_total y (p - x) with hy | hpy
    · have hxy : x + y ≤ p := by
        rw [← hpx]
        simpa [add_comm, add_left_comm, add_assoc] using add_le_add_left hy x
      rw [min_eq_right hy, min_eq_right hxy]
    · have hpxy : p ≤ x + y := by
        rw [← hpx]
        simpa [add_comm, add_left_comm, add_assoc] using add_le_add_left hpy x
      rw [min_eq_left hpy, min_eq_left hpxy, hpx]

private theorem sorted_list_waterfall_sum
    {ι : Type*} [LinearOrder ι] (claims : ClaimSchedule ι) :
    ∀ (l : List ι), l.Pairwise (fun a b => a < b) → ∀ pool : NNReal,
      (l.map fun i =>
        min (claims i) (pool - ((l.filter fun j => j < i).map claims).sum)).sum =
          min pool ((l.map claims).sum)
  | [], _, pool => by simp
  | a :: t, hs, pool => by
      cases hs with
      | cons hhead htail =>
          have hfilter_a : (t.filter fun j => j < a) = [] := by
            apply List.filter_eq_nil_iff.mpr
            intro b hb
            simpa using not_lt_of_ge (le_of_lt (hhead b hb))
          have htail_sum :
              (t.map fun i =>
                min (claims i)
                  (pool - (((a :: t).filter fun j => j < i).map claims).sum)).sum =
                (t.map fun i =>
                  min (claims i)
                    ((pool - claims a) - ((t.filter fun j => j < i).map claims).sum)).sum := by
            apply congrArg List.sum
            apply List.map_congr_left
            intro i hi
            have hai : a < i := hhead i hi
            simp [List.filter_cons, hai, tsub_add_eq_tsub_tsub]
          have ih := sorted_list_waterfall_sum claims t htail (pool - claims a)
          have hfilter_cons_a : ((a :: t).filter fun j => j < a) = [] := by
            simp [List.filter_cons, hfilter_a]
          simp only [List.map_cons, List.sum_cons]
          rw [hfilter_cons_a]
          simp only [List.map_nil, List.sum_nil, tsub_zero]
          rw [htail_sum, ih]
          exact nnreal_min_add_min_tsub (claims a) pool ((t.map claims).sum)

private theorem seniorClaimsBefore_eq_sorted_filter_sum
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (i : ι) :
    SeniorClaimsBefore claims i =
      (((Finset.univ.sort (fun a b : ι => a ≤ b)).filter fun j => j < i).map claims).sum := by
  classical
  let l := Finset.univ.sort (fun a b : ι => a ≤ b)
  have hfilter_toFinset :
      (l.filter fun j => j < i).toFinset = (Finset.univ.filter fun j : ι => j < i) := by
    apply Finset.ext
    intro j
    simp [l]
  have hnodup_filter : (l.filter fun j => j < i).Nodup := by
    simpa [l] using ((Finset.sort_nodup (s := (Finset.univ : Finset ι))
      (r := fun a b : ι => a ≤ b)).filter (p := fun j => decide (j < i)))
  calc
    SeniorClaimsBefore claims i =
        ∑ j ∈ Finset.univ.filter (fun j : ι => j < i), claims j := by
      unfold SeniorClaimsBefore
      apply Finset.sum_congr
      · ext j
        simp
      · intro j hj
        rfl
    _ = (l.filter fun j => j < i).toFinset.sum claims := by
      rw [hfilter_toFinset]
    _ = (((l.filter fun j => j < i).map claims).sum) := by
      rw [List.sum_toFinset claims hnodup_filter]

private theorem waterfall_sum_eq_min
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) :
    (∑ i, WaterfallDistribution claims pool i) = min pool (∑ i, claims i) := by
  classical
  let l := Finset.univ.sort (fun a b : ι => a ≤ b)
  have hpair : l.Pairwise (fun a b => a < b) := by
    simpa [l] using (Finset.sortedLT_sort (Finset.univ : Finset ι)).pairwise
  have hpay_list :
      (l.map fun i => WaterfallDistribution claims pool i).sum =
        (l.map fun i =>
          min (claims i) (pool - ((l.filter fun j => j < i).map claims).sum)).sum := by
    apply congrArg List.sum
    apply List.map_congr_left
    intro i hi
    rw [WaterfallDistribution, seniorClaimsBefore_eq_sorted_filter_sum]
  have hsum_pay :
      (∑ i, WaterfallDistribution claims pool i) =
        (l.map fun i => WaterfallDistribution claims pool i).sum := by
    rw [← List.sum_toFinset (fun i => WaterfallDistribution claims pool i)
      (Finset.sort_nodup (s := (Finset.univ : Finset ι)) (r := fun a b : ι => a ≤ b))]
    simp [l]
  have hsum_claims :
      (l.map claims).sum = ∑ i, claims i := by
    rw [← List.sum_toFinset claims
      (Finset.sort_nodup (s := (Finset.univ : Finset ι)) (r := fun a b : ι => a ≤ b))]
    simp [l]
  rw [hsum_pay, hpay_list, sorted_list_waterfall_sum claims l hpair pool, hsum_claims]

/-- FEASIBILITY: the closed-form waterfall pays each tranche at most its claim, and the total
distributed never exceeds the available pool. -/
theorem waterfallDistribution_feasible_of_linearOrder : ∀ {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal), DistributionFeasible claims pool (WaterfallDistribution claims pool) := by
  intro ι _ _ claims pool
  constructor
  · intro i
    exact min_le_left _ _
  · rw [waterfall_sum_eq_min claims pool]
    exact min_le_left _ _

theorem waterfall_positive_residual_of_positive_payment
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal) (junior : ι)
    (hpos : 0 < WaterfallDistribution claims pool junior) :
    SeniorClaimsBefore claims junior < pool := by
  have hmin :
      0 < min (claims junior) (pool - SeniorClaimsBefore claims junior) := by
    simpa [WaterfallDistribution] using hpos
  have hres : 0 < pool - SeniorClaimsBefore claims junior :=
    lt_of_lt_of_le hmin (min_le_right _ _)
  exact tsub_pos_iff_lt.mp hres

theorem seniorClaim_le_juniorSeniorClaims
    {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (senior junior : ι) (hsj : senior < junior) :
    SeniorClaimsBefore claims senior + claims senior ≤ SeniorClaimsBefore claims junior := by
  classical
  let s : Finset ι := Finset.univ.filter (fun j : ι => j < senior)
  let t : Finset ι := Finset.univ.filter (fun j : ι => j < junior)
  have hnot_mem : senior ∉ s := by
    simp [s]
  have hsubset : insert senior s ⊆ t := by
    intro x hx
    simp only [Finset.mem_insert] at hx
    simp only [t, Finset.mem_filter, Finset.mem_univ, true_and]
    rcases hx with rfl | hx
    · exact hsj
    · have hxlt : x < senior := by
        simpa [s] using hx
      exact lt_trans hxlt hsj
  have hsenior_eq : SeniorClaimsBefore claims senior = ∑ x ∈ s, claims x := by
    unfold SeniorClaimsBefore
    apply Finset.sum_congr
    · ext x
      simp [s]
    · intro x hx
      rfl
  have hjunior_eq : SeniorClaimsBefore claims junior = ∑ x ∈ t, claims x := by
    unfold SeniorClaimsBefore
    apply Finset.sum_congr
    · ext x
      simp [t]
    · intro x hx
      rfl
  calc
    SeniorClaimsBefore claims senior + claims senior =
        (∑ x ∈ s, claims x) + claims senior := by
          rw [hsenior_eq]
    _ = claims senior + ∑ x ∈ s, claims x := by
          rw [add_comm]
    _ = ∑ x ∈ insert senior s, claims x := by
          rw [Finset.sum_insert hnot_mem]
    _ ≤ ∑ x ∈ t, claims x := by
          exact Finset.sum_le_sum_of_subset_of_nonneg hsubset
            (fun x _ _ => zero_le (claims x))
    _ = SeniorClaimsBefore claims junior := by
          rw [hjunior_eq]

theorem nnreal_le_tsub_of_add_le_lt
    (a b c pool : NNReal) (hsum : a + b ≤ c) (hc : c < pool) :
    b ≤ pool - a := by
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

/-- ABSOLUTE PRIORITY: whenever a tranche receives a strictly positive payment, every tranche
senior to it is paid its claim in full. -/
theorem waterfallDistribution_absolutePriority_of_linearOrder : ∀ {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal), AbsolutePriority claims (WaterfallDistribution claims pool) := by
  intro ι _ _ claims pool
  intro senior junior hsj hpos
  have hjunior_lt_pool :
      SeniorClaimsBefore claims junior < pool :=
    waterfall_positive_residual_of_positive_payment claims pool junior hpos
  have hsum :
      SeniorClaimsBefore claims senior + claims senior ≤ SeniorClaimsBefore claims junior :=
    seniorClaim_le_juniorSeniorClaims claims senior junior hsj
  have hclaim_le_residual :
      claims senior ≤ pool - SeniorClaimsBefore claims senior :=
    nnreal_le_tsub_of_add_le_lt
      (SeniorClaimsBefore claims senior) (claims senior)
      (SeniorClaimsBefore claims junior) pool hsum hjunior_lt_pool
  simp [WaterfallDistribution, min_eq_left hclaim_le_residual]

/-- HEADLINE: the closed-form liquidation waterfall satisfies the full conclusion bundle —
feasibility AND absolute priority — for any finite priority order and any pool value. Proved by
composing the two rungs above (a genuine dependency graph). -/
theorem waterfallDistribution_conclusion : ∀ {ι : Type*} [Fintype ι] [LinearOrder ι]
    (claims : ClaimSchedule ι) (pool : NNReal), WaterfallConclusion claims pool (WaterfallDistribution claims pool) := by
  intro ι _ _ claims pool
  exact ⟨waterfallDistribution_feasible_of_linearOrder claims pool,
    waterfallDistribution_absolutePriority_of_linearOrder claims pool⟩

#print axioms waterfallDistribution_conclusion
