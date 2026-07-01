/-
LeanMill campaign provenance — vcg_dsic_pivot_independence_and_twoUnit_witness
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=notes_vcg_dsic_blueprint_0701T0201) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : time-to-closure 362.15s (first 201.54s · p50 350.58s · p95 730.51s) · campaign span 730.51s (lead 1335.87s)
  compute     : cost-to-closure 84.53s mean · 337.86s total
  yield       : 9/13 attempts closed (4 failed)
  phases      : 844.9s leaf.dispatch · 168.9s pool · 128.1s formalize · 70.1s native · 7.4s govern.mnc
  reuse       : 9 rung(s) banked this run · 0 reused from prior bank
  moves       : native_hammer×9 · proposer_pool×2 · claude_warm×2
-/
import Mathlib

/-!
VCG dominant-strategy truthfulness substrate.

Definition trial log:
* Candidate A: set-valued argmax. Rejected for the core mechanism because every use needed a
  nonemptiness side condition.
* Candidate B: deterministic allocation chosen from Mathlib's finite maximum theorem. Selected:
  the nonvacuity and maximality sanity lemmas below compile directly.
* Candidate C: complete-lattice `⨆`. Rejected because an ordered value type only needs finite
  maxima over a nonempty finite outcome space.

Typeclass note: this Mathlib build does not expose the blueprint names `LinearOrderedField` or
`LinearOrderedAddCommGroup` to the warm checker. The order-compatible additive assumption is
therefore stated in Mathlib's primitive form:
`[LinearOrder K] [AddCommGroup K] [CovariantClass K K (fun x y => x + y) (· ≤ ·)]`.
This is intentionally stronger than a bare `[LinearOrder K] [AddCommGroup K]`.
-/

open BigOperators
open scoped BigOperators

namespace VCG

-- SUPERSEDE: any bare `[LinearOrder K] [AddCommGroup K]` DSIC theorem:
-- DSIC needs order-compatible addition for the Clarke-payment cancellation.

abbrev Valuation (Outcome K : Type*) := Outcome → K

abbrev ValuationProfile (Agent Outcome K : Type*) := Agent → Valuation Outcome K

noncomputable def finiteMax
    {α β : Type*} [Fintype α] [Nonempty α] [LinearOrder β] (f : α → β) : β :=
  Finset.univ.sup' Finset.univ_nonempty f

theorem anchor_finiteMax_eq_finset_sup'
    {α β : Type*} [Fintype α] [Nonempty α] [LinearOrder β] (f : α → β) :
    finiteMax f = Finset.univ.sup' Finset.univ_nonempty f := rfl

theorem finiteMax_ge
    {α β : Type*} [Fintype α] [Nonempty α] [LinearOrder β] (f : α → β) (a : α) :
    f a ≤ finiteMax f := by
  exact Finset.le_sup' (s := Finset.univ) (f := f) (Finset.mem_univ a)

theorem finiteMax_le
    {α β : Type*} [Fintype α] [Nonempty α] [LinearOrder β] {f : α → β} {b : β}
    (h : ∀ a : α, f a ≤ b) : finiteMax f ≤ b := by
  exact Finset.sup'_le Finset.univ_nonempty f (by intro a _; exact h a)

theorem finiteMax_congr
    {α β : Type*} [Fintype α] [Nonempty α] [LinearOrder β] {f g : α → β}
    (h : ∀ a : α, f a = g a) :
    finiteMax f = finiteMax g := by
  simp [finiteMax, h]

theorem anchor_orderCompatible_add_left
    {K : Type*} [AddCommGroup K] [LinearOrder K]
    [CovariantClass K K (fun x y => x + y) (· ≤ ·)]
    {a b c : K} (h : a ≤ b) : a + c ≤ b + c := by
  simpa [add_comm, add_left_comm, add_assoc] using add_le_add_left h c

def socialWelfare
    {Agent Outcome K : Type*} [Fintype Agent] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (a : Outcome) : K :=
  ∑ i : Agent, r i a

theorem anchor_socialWelfare_singleton
    {Outcome K : Type*} [AddCommMonoid K] (r : ValuationProfile PUnit Outcome K)
    (a : Outcome) :
    socialWelfare r a = r PUnit.unit a := by
  simp [socialWelfare]

def othersWelfare
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (a : Outcome) : K :=
  Finset.sum (Finset.univ.erase i) (fun j => r j a)

theorem anchor_othersWelfare_eq_sum_erase
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (a : Outcome) :
    othersWelfare r i a = Finset.sum (Finset.univ.erase i) (fun j => r j a) := rfl

def updateReport
    {Agent Outcome K : Type*} [DecidableEq Agent]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K) :
    ValuationProfile Agent Outcome K :=
  fun j => if j = i then vi else r j

@[simp] theorem updateReport_self
    {Agent Outcome K : Type*} [DecidableEq Agent]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K) :
    updateReport r i vi i = vi := by
  simp [updateReport]

@[simp] theorem updateReport_other
    {Agent Outcome K : Type*} [DecidableEq Agent]
    (r : ValuationProfile Agent Outcome K) {i j : Agent} (vi : Valuation Outcome K)
    (hji : j ≠ i) :
    updateReport r i vi j = r j := by
  simp [updateReport, hji]

theorem othersWelfare_update_self
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K)
    (a : Outcome) :
    othersWelfare (updateReport r i vi) i a = othersWelfare r i a := by
  unfold othersWelfare
  refine Finset.sum_congr rfl ?_
  intro j hj
  have hji : j ≠ i := (Finset.mem_erase.mp hj).1
  simp [updateReport, hji]

noncomputable def pivotBenchmark
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) : K :=
  finiteMax (fun a : Outcome => othersWelfare r i a)

theorem anchor_pivotBenchmark_eq_finiteMax
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) :
    pivotBenchmark r i = finiteMax (fun a : Outcome => othersWelfare r i a) := rfl

theorem pivotBenchmark_update_self
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K) :
    pivotBenchmark (updateReport r i vi) i = pivotBenchmark r i := by
  simp [pivotBenchmark, othersWelfare_update_self]

theorem pivotBenchmark_i_independent
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommMonoid K]
    {r r' : ValuationProfile Agent Outcome K} {i : Agent}
    (h : ∀ j : Agent, j ≠ i → r j = r' j) :
    pivotBenchmark r i = pivotBenchmark r' i := by
  unfold pivotBenchmark
  apply finiteMax_congr
  intro a
  unfold othersWelfare
  refine Finset.sum_congr rfl ?_
  intro j hj
  have hji : j ≠ i := (Finset.mem_erase.mp hj).1
  exact congrFun (h j hji) a

def IsWelfareMaximizer
    {Agent Outcome K : Type*} [Fintype Agent] [AddCommMonoid K] [LE K]
    (r : ValuationProfile Agent Outcome K) (a : Outcome) : Prop :=
  ∀ b : Outcome, socialWelfare r b ≤ socialWelfare r a

theorem exists_welfareMaximizer
    {Agent Outcome K : Type*} [Fintype Agent] [AddCommMonoid K] [LinearOrder K]
    [Fintype Outcome] [Nonempty Outcome] (r : ValuationProfile Agent Outcome K) :
    ∃ a : Outcome, IsWelfareMaximizer r a := by
  classical
  rcases Finset.exists_max_image (s := Finset.univ)
      (f := fun a : Outcome => socialWelfare r a) Finset.univ_nonempty with
    ⟨a, _ha, hmax⟩
  exact ⟨a, by intro b; exact hmax b (Finset.mem_univ b)⟩

theorem witness_welfareMaximizer_nonvacuous
    {Agent Outcome K : Type*} [Fintype Agent] [AddCommMonoid K] [LinearOrder K]
    [Fintype Outcome] [Nonempty Outcome] (r : ValuationProfile Agent Outcome K) :
    (Set.univ : Set {a : Outcome // IsWelfareMaximizer r a}).Nonempty := by
  rcases exists_welfareMaximizer r with ⟨a, ha⟩
  exact ⟨⟨a, ha⟩, by simp⟩

noncomputable def vcgAllocation
    {Agent Outcome K : Type*} [Fintype Agent] [AddCommMonoid K] [LinearOrder K]
    [Fintype Outcome] [Nonempty Outcome] (r : ValuationProfile Agent Outcome K) : Outcome :=
  Classical.choose (exists_welfareMaximizer r)

theorem vcgAllocation_isWelfareMaximizer
    {Agent Outcome K : Type*} [Fintype Agent] [AddCommMonoid K] [LinearOrder K]
    [Fintype Outcome] [Nonempty Outcome] (r : ValuationProfile Agent Outcome K) :
    IsWelfareMaximizer r (vcgAllocation r) :=
  Classical.choose_spec (exists_welfareMaximizer r)

noncomputable def clarkePivotPayment
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) : K :=
  pivotBenchmark r i - othersWelfare r i (vcgAllocation r)

theorem anchor_clarkePivotPayment_eq_externality
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) :
    clarkePivotPayment r i =
      pivotBenchmark r i - othersWelfare r i (vcgAllocation r) := rfl

noncomputable def quasilinearUtility
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    (trueVal : Valuation Outcome K) (r : ValuationProfile Agent Outcome K) (i : Agent) : K :=
  trueVal (vcgAllocation r) - clarkePivotPayment r i

theorem anchor_quasilinearUtility_eq_value_minus_payment
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    (trueVal : Valuation Outcome K) (r : ValuationProfile Agent Outcome K) (i : Agent) :
    quasilinearUtility trueVal r i = trueVal (vcgAllocation r) - clarkePivotPayment r i := rfl

def DominantStrategyTruthful
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    [CovariantClass K K (fun x y => x + y) (· ≤ ·)] : Prop :=
  ∀ (i : Agent) (trueVal : Valuation Outcome K)
    (othersReports : ValuationProfile Agent Outcome K) (misreport : Valuation Outcome K),
    quasilinearUtility trueVal (updateReport othersReports i trueVal) i ≥
      quasilinearUtility trueVal (updateReport othersReports i misreport) i

theorem anchor_DominantStrategyTruthful_characterization
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    [CovariantClass K K (fun x y => x + y) (· ≤ ·)] :
    DominantStrategyTruthful Agent Outcome K ↔
      ∀ (i : Agent) (trueVal : Valuation Outcome K)
        (othersReports : ValuationProfile Agent Outcome K) (misreport : Valuation Outcome K),
        quasilinearUtility trueVal (updateReport othersReports i trueVal) i ≥
          quasilinearUtility trueVal (updateReport othersReports i misreport) i := by
  rfl

structure VCGMechanism
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    [CovariantClass K K (fun x y => x + y) (· ≤ ·)] where
  allocation : ValuationProfile Agent Outcome K → Outcome
  payment : ValuationProfile Agent Outcome K → Agent → K
  welfare_maximizing :
    ∀ r : ValuationProfile Agent Outcome K, IsWelfareMaximizer r (allocation r)
  payment_is_clarke_pivot :
    ∀ (r : ValuationProfile Agent Outcome K) (i : Agent),
      payment r i = clarkePivotPayment r i

noncomputable def vcgMechanism
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    [CovariantClass K K (fun x y => x + y) (· ≤ ·)] :
    VCGMechanism Agent Outcome K where
  allocation := vcgAllocation
  payment := fun r i => clarkePivotPayment r i
  welfare_maximizing := vcgAllocation_isWelfareMaximizer
  payment_is_clarke_pivot := by intro r i; rfl

theorem socialWelfare_updateReport__c1af565a
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K)
    (a : Outcome) :
    socialWelfare (updateReport r i vi) a = vi a + othersWelfare r i a := by
  classical
  unfold socialWelfare othersWelfare
  rw [← Finset.add_sum_erase Finset.univ
    (fun j : Agent => updateReport r i vi j a) (Finset.mem_univ i)]
  congr 1
  · simp [updateReport]
  · refine Finset.sum_congr rfl ?_
    intro j hj
    have hji : j ≠ i := (Finset.mem_erase.mp hj).1
    simp [updateReport, hji]

theorem othersWelfare_updateReport_self__2aa855d9
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K)
    (a : Outcome) :
    othersWelfare (updateReport r i vi) i a = othersWelfare r i a := by
  unfold othersWelfare
  refine Finset.sum_congr rfl ?_
  intro j hj
  have hji : j ≠ i := (Finset.mem_erase.mp hj).1
  simp [updateReport, hji]

theorem pivotBenchmark_updateReport_self__04530a39
    {Agent Outcome K : Type*} [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommMonoid K]
    (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K) :
    pivotBenchmark (updateReport r i vi) i = pivotBenchmark r i := by
  simp [pivotBenchmark, othersWelfare_updateReport_self__2aa855d9]

theorem vcg_dominantStrategyTruthful : ∀ (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [LinearOrder K] [AddCommGroup K]
    [CovariantClass K K (fun x y => x + y) (· ≤ ·)], DominantStrategyTruthful Agent Outcome K := by
  classical
  intro Agent Outcome K _ _ _ _ _ _ _
  intro i trueVal othersReports misreport
  let truthfulReports := updateReport othersReports i trueVal
  let deviatingReports := updateReport othersReports i misreport
  let truthfulOutcome := vcgAllocation truthfulReports
  let deviatingOutcome := vcgAllocation deviatingReports
  have hmax :
      socialWelfare truthfulReports deviatingOutcome ≤
        socialWelfare truthfulReports truthfulOutcome :=
    vcgAllocation_isWelfareMaximizer truthfulReports deviatingOutcome
  have hwelfare :
      trueVal deviatingOutcome + othersWelfare othersReports i deviatingOutcome ≤
        trueVal truthfulOutcome + othersWelfare othersReports i truthfulOutcome := by
    simpa [truthfulReports, truthfulOutcome, deviatingOutcome, socialWelfare_updateReport__c1af565a] using hmax
  have hwithBenchmark :
      trueVal deviatingOutcome + othersWelfare othersReports i deviatingOutcome +
          -(pivotBenchmark othersReports i) ≤
        trueVal truthfulOutcome + othersWelfare othersReports i truthfulOutcome +
          -(pivotBenchmark othersReports i) := by
    simpa [add_assoc, add_left_comm, add_comm] using
      add_le_add_right hwelfare (-(pivotBenchmark othersReports i))
  simpa [DominantStrategyTruthful, quasilinearUtility, clarkePivotPayment,
    truthfulReports, deviatingReports, truthfulOutcome, deviatingOutcome,
    pivotBenchmark_updateReport_self__04530a39, othersWelfare_updateReport_self__2aa855d9,
    sub_eq_add_neg, add_assoc, add_left_comm, add_comm] using hwithBenchmark
structure TwoUnitMarginals (K : Type*) where
  first : K
  second : K

def DecreasingMarginals {K : Type*} [LE K] (m : TwoUnitMarginals K) : Prop :=
  m.second ≤ m.first

def twoUnitStepValue {K : Type*} [Zero K] [Add K] (m : TwoUnitMarginals K) (q : Nat) : K :=
  if q = 0 then 0 else if q = 1 then m.first else m.first + m.second

@[simp] theorem twoUnitStepValue_zero
    {K : Type*} [Zero K] [Add K] (m : TwoUnitMarginals K) :
    twoUnitStepValue m 0 = 0 := by
  simp [twoUnitStepValue]

@[simp] theorem twoUnitStepValue_one
    {K : Type*} [Zero K] [Add K] (m : TwoUnitMarginals K) :
    twoUnitStepValue m 1 = m.first := by
  simp [twoUnitStepValue]

@[simp] theorem twoUnitStepValue_two
    {K : Type*} [Zero K] [Add K] (m : TwoUnitMarginals K) :
    twoUnitStepValue m 2 = m.first + m.second := by
  simp [twoUnitStepValue]

theorem anchor_twoUnitStepValue_two_eq_sum_marginals
    {K : Type*} [AddCommMonoid K] (m : TwoUnitMarginals K) :
    twoUnitStepValue m 2 = ∑ t : Fin 2, if (t : Nat) = 0 then m.first else m.second := by
  simp [twoUnitStepValue, Fin.sum_univ_two]

abbrev TwoAgent := Fin 2

abbrev TwoUnitAllocation := Fin 3

def unitsForAgent0 (a : TwoUnitAllocation) : Nat := a.val

def unitsForAgent1 (a : TwoUnitAllocation) : Nat := 2 - a.val

def twoUnitProfile
    {K : Type*} [Zero K] [Add K]
    (m0 m1 : TwoUnitMarginals K) : ValuationProfile TwoAgent TwoUnitAllocation K :=
  fun i a =>
    if i = 0 then
      twoUnitStepValue m0 (unitsForAgent0 a)
    else
      twoUnitStepValue m1 (unitsForAgent1 a)

theorem twoUnitProfile_agent0
    {K : Type*} [Zero K] [Add K]
    (m0 m1 : TwoUnitMarginals K) (a : TwoUnitAllocation) :
    twoUnitProfile m0 m1 (0 : TwoAgent) a = twoUnitStepValue m0 (unitsForAgent0 a) := by
  simp [twoUnitProfile]

theorem twoUnitProfile_agent1
    {K : Type*} [Zero K] [Add K]
    (m0 m1 : TwoUnitMarginals K) (a : TwoUnitAllocation) :
    twoUnitProfile m0 m1 (1 : TwoAgent) a = twoUnitStepValue m1 (unitsForAgent1 a) := by
  simp [twoUnitProfile]

def twoUnitWitnessTrue0Marginals : TwoUnitMarginals ℚ where
  first := 10
  second := 1

def twoUnitWitnessOtherMarginals : TwoUnitMarginals ℚ where
  first := 6
  second := 5

def twoUnitWitnessMis0Marginals : TwoUnitMarginals ℚ where
  first := 12
  second := 12

theorem twoUnitWitnessTrue0_decreasing :
    DecreasingMarginals twoUnitWitnessTrue0Marginals := by
  norm_num [DecreasingMarginals, twoUnitWitnessTrue0Marginals]

theorem twoUnitWitnessOther_decreasing :
    DecreasingMarginals twoUnitWitnessOtherMarginals := by
  norm_num [DecreasingMarginals, twoUnitWitnessOtherMarginals]

theorem twoUnitWitnessMis0_decreasing :
    DecreasingMarginals twoUnitWitnessMis0Marginals := by
  norm_num [DecreasingMarginals, twoUnitWitnessMis0Marginals]

def twoUnitWitnessTrue0 : Valuation TwoUnitAllocation ℚ :=
  fun a => twoUnitStepValue twoUnitWitnessTrue0Marginals (unitsForAgent0 a)

def twoUnitWitnessMis0 : Valuation TwoUnitAllocation ℚ :=
  fun a => twoUnitStepValue twoUnitWitnessMis0Marginals (unitsForAgent0 a)

def twoUnitWitnessBaseProfile : ValuationProfile TwoAgent TwoUnitAllocation ℚ :=
  twoUnitProfile twoUnitWitnessTrue0Marginals twoUnitWitnessOtherMarginals

end VCG

namespace VCG

abbrev twoUnitA0 : TwoUnitAllocation := ⟨0, by decide⟩

abbrev twoUnitA1 : TwoUnitAllocation := ⟨1, by decide⟩

abbrev twoUnitA2 : TwoUnitAllocation := ⟨2, by decide⟩

abbrev twoUnitTruthfulReport : ValuationProfile TwoAgent TwoUnitAllocation ℚ :=
  updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0

abbrev twoUnitMisReport : ValuationProfile TwoAgent TwoUnitAllocation ℚ :=
  updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0

theorem twoUnitTruthful_allocation_closed : vcgAllocation twoUnitTruthfulReport = twoUnitA1 := by
  have hmax := vcgAllocation_isWelfareMaximizer twoUnitTruthfulReport
  generalize ha : vcgAllocation twoUnitTruthfulReport = a
  fin_cases a
  · have hle := hmax twoUnitA1
    have hcontra : ¬ socialWelfare twoUnitTruthfulReport twoUnitA1 ≤
        socialWelfare twoUnitTruthfulReport twoUnitA0 := by native_decide
    exact False.elim (hcontra (by simpa [ha, twoUnitA0, twoUnitA1] using hle))
  · rfl
  · have hle := hmax twoUnitA1
    have hcontra : ¬ socialWelfare twoUnitTruthfulReport twoUnitA1 ≤
        socialWelfare twoUnitTruthfulReport twoUnitA2 := by native_decide
    exact False.elim (hcontra (by simpa [ha, twoUnitA1, twoUnitA2] using hle))

theorem twoUnitMis_allocation_closed : vcgAllocation twoUnitMisReport = twoUnitA2 := by
  have hmax := vcgAllocation_isWelfareMaximizer twoUnitMisReport
  generalize ha : vcgAllocation twoUnitMisReport = a
  fin_cases a
  · have hle := hmax twoUnitA2
    have hcontra : ¬ socialWelfare twoUnitMisReport twoUnitA2 ≤
        socialWelfare twoUnitMisReport twoUnitA0 := by native_decide
    exact False.elim (hcontra (by simpa [ha, twoUnitA0, twoUnitA2] using hle))
  · have hle := hmax twoUnitA2
    have hcontra : ¬ socialWelfare twoUnitMisReport twoUnitA2 ≤
        socialWelfare twoUnitMisReport twoUnitA1 := by native_decide
    exact False.elim (hcontra (by simpa [ha, twoUnitA1, twoUnitA2] using hle))
  · rfl

theorem twoUnitTruthful_pivot_closed :
    pivotBenchmark twoUnitTruthfulReport (0 : TwoAgent) = 11 := by
  apply le_antisymm
  · unfold pivotBenchmark
    apply finiteMax_le
    intro a
    fin_cases a <;> native_decide
  · have h := finiteMax_ge
      (fun a : TwoUnitAllocation => othersWelfare twoUnitTruthfulReport (0 : TwoAgent) a)
      twoUnitA0
    change othersWelfare twoUnitTruthfulReport (0 : TwoAgent) (0 : TwoUnitAllocation) ≤
      pivotBenchmark twoUnitTruthfulReport (0 : TwoAgent) at h
    have ho : othersWelfare twoUnitTruthfulReport (0 : TwoAgent)
        (0 : TwoUnitAllocation) = 11 := by native_decide
    simpa [ho] using h

theorem twoUnitMis_pivot_closed :
    pivotBenchmark twoUnitMisReport (0 : TwoAgent) = 11 := by
  apply le_antisymm
  · unfold pivotBenchmark
    apply finiteMax_le
    intro a
    fin_cases a <;> native_decide
  · have h := finiteMax_ge
      (fun a : TwoUnitAllocation => othersWelfare twoUnitMisReport (0 : TwoAgent) a)
      twoUnitA0
    change othersWelfare twoUnitMisReport (0 : TwoAgent) (0 : TwoUnitAllocation) ≤
      pivotBenchmark twoUnitMisReport (0 : TwoAgent) at h
    have ho : othersWelfare twoUnitMisReport (0 : TwoAgent)
        (0 : TwoUnitAllocation) = 11 := by native_decide
    simpa [ho] using h

theorem twoUnitTruthful_utility_closed :
    quasilinearUtility twoUnitWitnessTrue0 twoUnitTruthfulReport (0 : TwoAgent) = 5 := by
  rw [quasilinearUtility, clarkePivotPayment, twoUnitTruthful_allocation_closed,
    twoUnitTruthful_pivot_closed]
  native_decide

theorem twoUnitMis_utility_closed :
    quasilinearUtility twoUnitWitnessTrue0 twoUnitMisReport (0 : TwoAgent) = 0 := by
  rw [quasilinearUtility, clarkePivotPayment, twoUnitMis_allocation_closed,
    twoUnitMis_pivot_closed]
  native_decide

theorem twoUnitTruthful_payment_closed :
    clarkePivotPayment twoUnitTruthfulReport (0 : TwoAgent) = 5 := by
  rw [clarkePivotPayment, twoUnitTruthful_allocation_closed, twoUnitTruthful_pivot_closed]
  native_decide

theorem vcg_twoUnit_nontrivial_misreport_witness_closed :
    vcgAllocation (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0) ≠
        vcgAllocation (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0) ∧
      quasilinearUtility twoUnitWitnessTrue0
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0)
          (0 : TwoAgent) ≥
        quasilinearUtility twoUnitWitnessTrue0
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0)
          (0 : TwoAgent) ∧
      clarkePivotPayment
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0)
          (0 : TwoAgent) ≠ 0 := by
  constructor
  · rw [show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0 =
        twoUnitTruthfulReport by rfl,
      show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0 =
        twoUnitMisReport by rfl,
      twoUnitTruthful_allocation_closed, twoUnitMis_allocation_closed]
    native_decide
  · constructor
    · rw [show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0 =
          twoUnitTruthfulReport by rfl,
        show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0 =
          twoUnitMisReport by rfl,
        twoUnitTruthful_utility_closed, twoUnitMis_utility_closed]
      norm_num
    · rw [show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0 =
          twoUnitTruthfulReport by rfl,
        twoUnitTruthful_payment_closed]
      norm_num

end VCG

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_dsic__485057d3
theorem iso_lemma_dsic__485057d3
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [Field K] [LinearOrder K] [IsStrictOrderedRing K] :
    DominantStrategyTruthful Agent Outcome K := by
  (repeat' apply And.intro) <;> (first | assumption | exact?)

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_mechanism_welfare__60ccfe51
theorem iso_lemma_mechanism_welfare__60ccfe51
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [Field K] [LinearOrder K] [IsStrictOrderedRing K] :
    ∀ r : ValuationProfile Agent Outcome K,
      IsWelfareMaximizer r ((vcgMechanism Agent Outcome K).allocation r) := by
  (repeat' apply And.intro) <;> (first | assumption | exact?)

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_mechanism_payment__fec3071b
theorem iso_lemma_mechanism_payment__fec3071b
    (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [Field K] [LinearOrder K] [IsStrictOrderedRing K] :
    ∀ (r : ValuationProfile Agent Outcome K) (i : Agent),
      (vcgMechanism Agent Outcome K).payment r i = clarkePivotPayment r i := by
  tauto

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_pivot_independent__ff66be29
theorem iso_lemma_pivot_independent__ff66be29 : ∀ (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [Field K] [LinearOrder K] [IsStrictOrderedRing K], ∀ (i : Agent) (othersReports : ValuationProfile Agent Outcome K)
        (trueVal misreport : Valuation Outcome K),
      pivotBenchmark (updateReport othersReports i trueVal) i =
        pivotBenchmark (updateReport othersReports i misreport) i := by
  intro Agent Outcome K _ _ _ _ _ _ _ i othersReports trueVal misreport
  apply congrArg finiteMax
  funext a
  unfold othersWelfare
  refine Finset.sum_congr rfl ?_
  intro j hj
  have hji : j ≠ i := (Finset.mem_erase.mp hj).1
  simp [updateReport, hji]

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_true0_decreasing__2ead5523
theorem iso_lemma_true0_decreasing__2ead5523 :
    DecreasingMarginals twoUnitWitnessTrue0Marginals := by
  rfl

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_other_decreasing__126d9db5
theorem iso_lemma_other_decreasing__126d9db5 :
    DecreasingMarginals twoUnitWitnessOtherMarginals := by
  rfl

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_mis0_decreasing__324f1454
theorem iso_lemma_mis0_decreasing__324f1454 :
    DecreasingMarginals twoUnitWitnessMis0Marginals := by
  rfl

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: iso_lemma_twoUnit_witness__ae76456e
theorem iso_lemma_twoUnit_witness__ae76456e :
    vcgAllocation (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0) ≠
        vcgAllocation (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0) ∧
      quasilinearUtility twoUnitWitnessTrue0
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0)
          (0 : TwoAgent) ≥
        quasilinearUtility twoUnitWitnessTrue0
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0)
          (0 : TwoAgent) ∧
      clarkePivotPayment
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0)
          (0 : TwoAgent) ≠ 0 := by
  exact?

end

section  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)
open VCG

-- [family-lemma-library] banked: vcg_dsic_pivot_independence_and_twoUnit_witness__a8cfdaac
theorem vcg_dsic_pivot_independence_and_twoUnit_witness__a8cfdaac : ∀ (Agent Outcome K : Type*) [Fintype Agent] [DecidableEq Agent] [Fintype Outcome]
    [Nonempty Outcome] [Field K] [LinearOrder K] [IsStrictOrderedRing K], (∀ r : ValuationProfile Agent Outcome K,
        IsWelfareMaximizer r ((vcgMechanism Agent Outcome K).allocation r)) ∧
      (∀ (r : ValuationProfile Agent Outcome K) (i : Agent),
        (vcgMechanism Agent Outcome K).payment r i = clarkePivotPayment r i) ∧
      DominantStrategyTruthful Agent Outcome K ∧
      (∀ (i : Agent) (othersReports : ValuationProfile Agent Outcome K)
          (trueVal misreport : Valuation Outcome K),
        pivotBenchmark (updateReport othersReports i trueVal) i =
          pivotBenchmark (updateReport othersReports i misreport) i) ∧
      DecreasingMarginals twoUnitWitnessTrue0Marginals ∧
      DecreasingMarginals twoUnitWitnessOtherMarginals ∧
      DecreasingMarginals twoUnitWitnessMis0Marginals ∧
      vcgAllocation (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0) ≠
          vcgAllocation (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0) ∧
      quasilinearUtility twoUnitWitnessTrue0
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0)
          (0 : TwoAgent) ≥
        quasilinearUtility twoUnitWitnessTrue0
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0)
          (0 : TwoAgent) ∧
      clarkePivotPayment
          (updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0)
          (0 : TwoAgent) ≠ 0 := by
  classical
  intro Agent Outcome K _ _ _ _ _ _ _
  have socialWelfare_updateReport :
      ∀ (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K)
        (a : Outcome),
        socialWelfare (updateReport r i vi) a = vi a + othersWelfare r i a := by
    intro r i vi a
    unfold socialWelfare othersWelfare
    rw [← Finset.add_sum_erase Finset.univ
      (fun j : Agent => updateReport r i vi j a) (Finset.mem_univ i)]
    congr 1
    · simp [updateReport]
    · refine Finset.sum_congr rfl ?_
      intro j hj
      have hji : j ≠ i := (Finset.mem_erase.mp hj).1
      simp [updateReport, hji]
  have othersWelfare_update_self :
      ∀ (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K)
        (a : Outcome),
        othersWelfare (updateReport r i vi) i a = othersWelfare r i a := by
    intro r i vi a
    unfold othersWelfare
    refine Finset.sum_congr rfl ?_
    intro j hj
    have hji : j ≠ i := (Finset.mem_erase.mp hj).1
    simp [updateReport, hji]
  have pivotBenchmark_update_self :
      ∀ (r : ValuationProfile Agent Outcome K) (i : Agent) (vi : Valuation Outcome K),
        pivotBenchmark (updateReport r i vi) i = pivotBenchmark r i := by
    intro r i vi
    simp [pivotBenchmark, othersWelfare_update_self]
  constructor
  · intro r
    exact (vcgMechanism Agent Outcome K).welfare_maximizing r
  constructor
  · intro r i
    exact (vcgMechanism Agent Outcome K).payment_is_clarke_pivot r i
  constructor
  · intro i trueVal othersReports misreport
    let truthfulReports := updateReport othersReports i trueVal
    let deviatingReports := updateReport othersReports i misreport
    let truthfulOutcome := vcgAllocation truthfulReports
    let deviatingOutcome := vcgAllocation deviatingReports
    have hmax :
        socialWelfare truthfulReports deviatingOutcome ≤
          socialWelfare truthfulReports truthfulOutcome :=
      vcgAllocation_isWelfareMaximizer truthfulReports deviatingOutcome
    have hwelfare :
        trueVal deviatingOutcome + othersWelfare othersReports i deviatingOutcome ≤
          trueVal truthfulOutcome + othersWelfare othersReports i truthfulOutcome := by
      simpa [truthfulReports, truthfulOutcome, deviatingOutcome, socialWelfare_updateReport] using hmax
    have hwithBenchmark :
        trueVal deviatingOutcome + othersWelfare othersReports i deviatingOutcome +
            -(pivotBenchmark othersReports i) ≤
          trueVal truthfulOutcome + othersWelfare othersReports i truthfulOutcome +
            -(pivotBenchmark othersReports i) := by
      simpa [add_assoc, add_left_comm, add_comm] using
        add_le_add_right hwelfare (-(pivotBenchmark othersReports i))
    simpa [DominantStrategyTruthful, quasilinearUtility, clarkePivotPayment,
      truthfulReports, deviatingReports, truthfulOutcome, deviatingOutcome,
      pivotBenchmark_update_self, othersWelfare_update_self,
      sub_eq_add_neg, add_assoc, add_left_comm, add_comm] using hwithBenchmark
  constructor
  · intro i othersReports trueVal misreport
    unfold pivotBenchmark
    congr 1
    funext a
    unfold othersWelfare
    refine Finset.sum_congr rfl ?_
    intro j hj
    have hji : j ≠ i := (Finset.mem_erase.mp hj).1
    simp [updateReport, hji]
  constructor
  · norm_num [DecreasingMarginals, twoUnitWitnessTrue0Marginals]
  constructor
  · norm_num [DecreasingMarginals, twoUnitWitnessOtherMarginals]
  constructor
  · norm_num [DecreasingMarginals, twoUnitWitnessMis0Marginals]
  · let twoUnitA0 : TwoUnitAllocation := ⟨0, by decide⟩
    let twoUnitA1 : TwoUnitAllocation := ⟨1, by decide⟩
    let twoUnitA2 : TwoUnitAllocation := ⟨2, by decide⟩
    let twoUnitTruthfulReport : ValuationProfile TwoAgent TwoUnitAllocation ℚ :=
      updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0
    let twoUnitMisReport : ValuationProfile TwoAgent TwoUnitAllocation ℚ :=
      updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0
    have finiteMax_ge_rat :
        ∀ (f : TwoUnitAllocation → ℚ) (a : TwoUnitAllocation), f a ≤ finiteMax f := by
      intro f a
      exact Finset.le_sup' (s := Finset.univ) (f := f) (Finset.mem_univ a)
    have finiteMax_le_rat :
        ∀ {f : TwoUnitAllocation → ℚ} {b : ℚ},
          (∀ a : TwoUnitAllocation, f a ≤ b) → finiteMax f ≤ b := by
      intro f b h
      exact Finset.sup'_le Finset.univ_nonempty f (by intro a _; exact h a)
    have twoUnitTruthful_allocation_closed : vcgAllocation twoUnitTruthfulReport = twoUnitA1 := by
      have hmax := vcgAllocation_isWelfareMaximizer twoUnitTruthfulReport
      generalize ha : vcgAllocation twoUnitTruthfulReport = a
      fin_cases a
      · have hle := hmax twoUnitA1
        have hcontra : ¬ socialWelfare twoUnitTruthfulReport twoUnitA1 ≤
            socialWelfare twoUnitTruthfulReport twoUnitA0 := by
          norm_num [socialWelfare, twoUnitTruthfulReport, twoUnitWitnessBaseProfile,
            twoUnitProfile, twoUnitWitnessTrue0, twoUnitStepValue, unitsForAgent0,
            unitsForAgent1, twoUnitA0, twoUnitA1, updateReport, twoUnitWitnessTrue0Marginals,
            twoUnitWitnessOtherMarginals]
        exact False.elim (hcontra (by simpa [ha, twoUnitA0, twoUnitA1] using hle))
      · rfl
      · have hle := hmax twoUnitA1
        have hcontra : ¬ socialWelfare twoUnitTruthfulReport twoUnitA1 ≤
            socialWelfare twoUnitTruthfulReport twoUnitA2 := by
          norm_num [socialWelfare, twoUnitTruthfulReport, twoUnitWitnessBaseProfile,
            twoUnitProfile, twoUnitWitnessTrue0, twoUnitStepValue, unitsForAgent0,
            unitsForAgent1, twoUnitA1, twoUnitA2, updateReport, twoUnitWitnessTrue0Marginals,
            twoUnitWitnessOtherMarginals]
        exact False.elim (hcontra (by simpa [ha, twoUnitA1, twoUnitA2] using hle))
    have twoUnitMis_allocation_closed : vcgAllocation twoUnitMisReport = twoUnitA2 := by
      have hmax := vcgAllocation_isWelfareMaximizer twoUnitMisReport
      generalize ha : vcgAllocation twoUnitMisReport = a
      fin_cases a
      · have hle := hmax twoUnitA2
        have hcontra : ¬ socialWelfare twoUnitMisReport twoUnitA2 ≤
            socialWelfare twoUnitMisReport twoUnitA0 := by
          norm_num [socialWelfare, twoUnitMisReport, twoUnitWitnessBaseProfile,
            twoUnitProfile, twoUnitWitnessMis0, twoUnitStepValue, unitsForAgent0,
            unitsForAgent1, twoUnitA0, twoUnitA2, updateReport, twoUnitWitnessMis0Marginals,
            twoUnitWitnessOtherMarginals]
        exact False.elim (hcontra (by simpa [ha, twoUnitA0, twoUnitA2] using hle))
      · have hle := hmax twoUnitA2
        have hcontra : ¬ socialWelfare twoUnitMisReport twoUnitA2 ≤
            socialWelfare twoUnitMisReport twoUnitA1 := by
          norm_num [socialWelfare, twoUnitMisReport, twoUnitWitnessBaseProfile,
            twoUnitProfile, twoUnitWitnessMis0, twoUnitStepValue, unitsForAgent0,
            unitsForAgent1, twoUnitA1, twoUnitA2, updateReport, twoUnitWitnessMis0Marginals,
            twoUnitWitnessOtherMarginals]
        exact False.elim (hcontra (by simpa [ha, twoUnitA1, twoUnitA2] using hle))
      · rfl
    have twoUnitTruthful_pivot_closed :
        pivotBenchmark twoUnitTruthfulReport (0 : TwoAgent) = 11 := by
      apply le_antisymm
      · unfold pivotBenchmark
        apply finiteMax_le_rat
        intro a
        fin_cases a <;> norm_num [othersWelfare, twoUnitTruthfulReport, twoUnitWitnessBaseProfile,
          twoUnitProfile, twoUnitWitnessTrue0, twoUnitStepValue, unitsForAgent0, unitsForAgent1,
          updateReport, twoUnitWitnessTrue0Marginals, twoUnitWitnessOtherMarginals]
      · have h := finiteMax_ge_rat
          (fun a : TwoUnitAllocation => othersWelfare twoUnitTruthfulReport (0 : TwoAgent) a)
          twoUnitA0
        change othersWelfare twoUnitTruthfulReport (0 : TwoAgent) twoUnitA0 ≤
          pivotBenchmark twoUnitTruthfulReport (0 : TwoAgent) at h
        have ho : othersWelfare twoUnitTruthfulReport (0 : TwoAgent) twoUnitA0 = 11 := by
          norm_num [othersWelfare, twoUnitTruthfulReport, twoUnitWitnessBaseProfile,
            twoUnitProfile, twoUnitWitnessTrue0, twoUnitStepValue, unitsForAgent0, unitsForAgent1,
            updateReport, twoUnitWitnessTrue0Marginals, twoUnitWitnessOtherMarginals, twoUnitA0]
        simpa [ho] using h
    have twoUnitMis_pivot_closed :
        pivotBenchmark twoUnitMisReport (0 : TwoAgent) = 11 := by
      apply le_antisymm
      · unfold pivotBenchmark
        apply finiteMax_le_rat
        intro a
        fin_cases a <;> norm_num [othersWelfare, twoUnitMisReport, twoUnitWitnessBaseProfile,
          twoUnitProfile, twoUnitWitnessMis0, twoUnitStepValue, unitsForAgent0, unitsForAgent1,
          updateReport, twoUnitWitnessMis0Marginals, twoUnitWitnessOtherMarginals]
      · have h := finiteMax_ge_rat
          (fun a : TwoUnitAllocation => othersWelfare twoUnitMisReport (0 : TwoAgent) a)
          twoUnitA0
        change othersWelfare twoUnitMisReport (0 : TwoAgent) twoUnitA0 ≤
          pivotBenchmark twoUnitMisReport (0 : TwoAgent) at h
        have ho : othersWelfare twoUnitMisReport (0 : TwoAgent) twoUnitA0 = 11 := by
          norm_num [othersWelfare, twoUnitMisReport, twoUnitWitnessBaseProfile,
            twoUnitProfile, twoUnitWitnessMis0, twoUnitStepValue, unitsForAgent0, unitsForAgent1,
            updateReport, twoUnitWitnessMis0Marginals, twoUnitWitnessOtherMarginals, twoUnitA0]
        simpa [ho] using h
    have twoUnitTruthful_utility_closed :
        quasilinearUtility twoUnitWitnessTrue0 twoUnitTruthfulReport (0 : TwoAgent) = 5 := by
      rw [quasilinearUtility, clarkePivotPayment, twoUnitTruthful_allocation_closed,
        twoUnitTruthful_pivot_closed]
      norm_num [othersWelfare, twoUnitTruthfulReport, twoUnitWitnessBaseProfile,
        twoUnitProfile, twoUnitWitnessTrue0, twoUnitStepValue, unitsForAgent0, unitsForAgent1,
        updateReport, twoUnitWitnessTrue0Marginals, twoUnitWitnessOtherMarginals, twoUnitA1]
    have twoUnitMis_utility_closed :
        quasilinearUtility twoUnitWitnessTrue0 twoUnitMisReport (0 : TwoAgent) = 0 := by
      rw [quasilinearUtility, clarkePivotPayment, twoUnitMis_allocation_closed,
        twoUnitMis_pivot_closed]
      norm_num [othersWelfare, twoUnitMisReport, twoUnitWitnessBaseProfile,
        twoUnitProfile, twoUnitWitnessTrue0, twoUnitWitnessMis0, twoUnitStepValue, unitsForAgent0,
        unitsForAgent1, updateReport, twoUnitWitnessTrue0Marginals, twoUnitWitnessMis0Marginals,
        twoUnitWitnessOtherMarginals, twoUnitA2]
    have twoUnitTruthful_payment_closed :
        clarkePivotPayment twoUnitTruthfulReport (0 : TwoAgent) = 5 := by
      rw [clarkePivotPayment, twoUnitTruthful_allocation_closed, twoUnitTruthful_pivot_closed]
      norm_num [othersWelfare, twoUnitTruthfulReport, twoUnitWitnessBaseProfile,
        twoUnitProfile, twoUnitWitnessTrue0, twoUnitStepValue, unitsForAgent0, unitsForAgent1,
        updateReport, twoUnitWitnessTrue0Marginals, twoUnitWitnessOtherMarginals, twoUnitA1]
    constructor
    · rw [show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0 =
          twoUnitTruthfulReport by rfl,
        show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0 =
          twoUnitMisReport by rfl,
        twoUnitTruthful_allocation_closed, twoUnitMis_allocation_closed]
      norm_num [twoUnitA1, twoUnitA2]
    · constructor
      · rw [show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0 =
            twoUnitTruthfulReport by rfl,
          show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessMis0 =
            twoUnitMisReport by rfl,
          twoUnitTruthful_utility_closed, twoUnitMis_utility_closed]
        norm_num
      · rw [show updateReport twoUnitWitnessBaseProfile (0 : TwoAgent) twoUnitWitnessTrue0 =
            twoUnitTruthfulReport by rfl,
          twoUnitTruthful_payment_closed]
        norm_num

end

#print axioms vcg_dsic_pivot_independence_and_twoUnit_witness__a8cfdaac
