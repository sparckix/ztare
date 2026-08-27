import Mathlib.Data.Finset.Sigma
import Mathlib.Order.Filter.AtTopBot.CountablyGenerated
import Mathlib.Analysis.Asymptotics.LinearGrowth
import Mathlib.Tactic

/-!
# Finite support at a critical filtration face

This module isolates the substrate-neutral compactness step used by filtered
obstruction arguments.  Each coefficient row has finite support.  If all
atoms in sufficiently late rows have strictly negative grade, only finitely
many atoms in the complete schedule can have grade zero.

No nonpositive-grade hypothesis is needed here.  Such a hypothesis governs
regularity of a specialization, while this theorem governs finiteness of its
critical face.
-/

namespace ZtareProofs.FilteredCriticalSupport

open Filter

variable {Atom : Type*}

/-- The atoms occurring in coefficient rows with filtration grade zero. -/
def criticalSupport
    (rows : ℕ → Finset Atom)
    (grade : ℕ → Atom → ℤ) : Set (Sigma fun _ : ℕ => Atom) :=
  {point | point.2 ∈ rows point.1 ∧ grade point.1 point.2 = 0}

/-- Eventual strict negativity and rowwise finite support make the complete
grade-zero face finite. -/
theorem criticalSupport_finite
    (rows : ℕ → Finset Atom)
    (grade : ℕ → Atom → ℤ)
    (eventually_negative :
      ∀ᶠ row in atTop, ∀ atom ∈ rows row, grade row atom < 0) :
    (criticalSupport rows grade).Finite := by
  classical
  obtain ⟨cutoff, after_cutoff⟩ :=
    (eventually_atTop.1 eventually_negative)
  let earlySupport : Finset (Sigma fun _ : ℕ => Atom) :=
    (Finset.range cutoff).sigma rows
  refine earlySupport.finite_toSet.subset ?_
  intro point point_mem
  have point_row : point.2 ∈ rows point.1 := point_mem.1
  have point_grade : grade point.1 point.2 = 0 := point_mem.2
  have before_cutoff : point.1 < cutoff := by
    by_contra not_before
    have cutoff_le : cutoff ≤ point.1 := Nat.le_of_not_gt not_before
    have negative := after_cutoff point.1 cutoff_le point.2 point_row
    omega
  exact Finset.mem_coe.mpr <|
    Finset.mem_sigma.mpr ⟨Finset.mem_range.mpr before_cutoff, point_row⟩

/-- A named terminal certificate for downstream proof-identity binding. -/
theorem finite_critical_support_terminal_certificate
    (rows : ℕ → Finset Atom)
    (grade : ℕ → Atom → ℤ)
    (eventually_negative :
      ∀ᶠ row in atTop, ∀ atom ∈ rows row, grade row atom < 0) :
    (criticalSupport rows grade).Finite :=
  criticalSupport_finite rows grade eventually_negative

/-! ## Row-predicate support charged by a cost function -/

/-- A row carrying a critical coefficient cannot survive inside a strict
subthreshold tail once survival is charged at the threshold. -/
theorem not_rowSupport_of_strict_tail
    (support : ℕ → Prop) (cost : ℕ → ℕ) (slope cutoff row : ℕ)
    (strictTail : ∀ n, cutoff ≤ n → cost n < slope * n)
    (supportCosts : ∀ n, support n → slope * n ≤ cost n)
    (hrow : cutoff ≤ row) :
    ¬ support row := by
  intro hsupport
  exact (Nat.not_lt_of_ge (supportCosts row hsupport))
    (strictTail row hrow)

/-- The typed support-to-cost charge upgrades an eventual strict tail to
finite critical row support. -/
theorem rowSupport_finite_of_strict_tail
    (support : ℕ → Prop) (cost : ℕ → ℕ) (slope cutoff : ℕ)
    (strictTail : ∀ n, cutoff ≤ n → cost n < slope * n)
    (supportCosts : ∀ n, support n → slope * n ≤ cost n) :
    {n : ℕ | support n}.Finite := by
  apply (Set.finite_Iio cutoff).subset
  intro row hsupport
  simp only [Set.mem_setOf_eq, Set.mem_Iio] at hsupport ⊢
  by_contra hnotBefore
  have hrow : cutoff ≤ row := Nat.le_of_not_gt hnotBefore
  exact not_rowSupport_of_strict_tail support cost slope cutoff row
    strictTail supportCosts hrow hsupport

/-- Infinite critical row support and a support-to-cost charge produce
threshold-paying rows past every cutoff. -/
theorem infinite_rowSupport_forces_late_charge
    (support : ℕ → Prop) (cost : ℕ → ℕ) (slope : ℕ)
    (supportInfinite : {n : ℕ | support n}.Infinite)
    (supportCosts : ∀ n, support n → slope * n ≤ cost n) :
    ∀ cutoff, ∃ row, cutoff < row ∧ support row ∧
      slope * row ≤ cost row := by
  intro cutoff
  obtain ⟨row, hsupport, hlate⟩ := supportInfinite.exists_gt cutoff
  exact ⟨row, hlate, hsupport, supportCosts row hsupport⟩

/-- Negative control: strict positive-slope cost bounds alone do not make an
unrelated support finite. -/
theorem cheap_infinite_rowSupport_negative_control :
    (∀ row : ℕ, 1 ≤ row → 0 < 2 * row) ∧
      (Set.univ : Set ℕ).Infinite := by
  constructor
  · intro row hrow
    omega
  · simpa using (Set.infinite_univ : (Set.univ : Set ℕ).Infinite)

/-- A uniform positive asymptotic margin absorbs the affine shift between
critical row `row` and logarithmic order `row + 1`. -/
theorem strict_affine_tail_of_positive_margin
    (cost : ℕ → ℕ) (slope margin denominator cutoff : ℕ)
    (margin_pos : 0 < margin)
    (marginTail : ∀ row, cutoff ≤ row →
      denominator * cost (row + 1) + margin * (row + 1) ≤
        denominator * slope * (row + 1)) :
    ∀ row, max cutoff (denominator * slope) ≤ row →
      cost (row + 1) < slope * row := by
  intro row hrow
  have hcutoff : cutoff ≤ row :=
    (Nat.le_max_left cutoff (denominator * slope)).trans hrow
  have hthreshold : denominator * slope ≤ row :=
    (Nat.le_max_right cutoff (denominator * slope)).trans hrow
  have htail := marginTail row hcutoff
  nlinarith

/-- Positive-margin subcriticality and the shifted critical charge make the
critical row support finite. -/
theorem rowSupport_finite_of_positive_margin
    (support : ℕ → Prop) (cost : ℕ → ℕ)
    (slope margin denominator cutoff : ℕ)
    (margin_pos : 0 < margin)
    (marginTail : ∀ row, cutoff ≤ row →
      denominator * cost (row + 1) + margin * (row + 1) ≤
        denominator * slope * (row + 1))
    (supportCosts : ∀ row, support row →
      slope * row ≤ cost (row + 1)) :
    {row : ℕ | support row}.Finite := by
  exact rowSupport_finite_of_strict_tail support (fun row => cost (row + 1))
    slope (max cutoff (denominator * slope))
    (strict_affine_tail_of_positive_margin cost slope margin denominator
      cutoff margin_pos marginTail)
    supportCosts

/-! ## Ordinary linear growth and the affine row/order shift -/

/-- A strict upper linear-growth bound on the unshifted cost sequence absorbs
the affine change from logarithmic order `row + 1` to critical row `row`.
No separate rational margin or shifted-growth hypothesis is required. -/
theorem strict_affine_tail_of_linearGrowthSup_lt
    (cost : ℕ → ℕ) (slope : ℕ)
    (subcritical :
      LinearGrowth.linearGrowthSup (fun order => (cost order : EReal)) <
        (slope : EReal)) :
    ∃ cutoff, ∀ row, cutoff ≤ row →
      cost (row + 1) < slope * row := by
  have growth_nonnegative :
      (0 : EReal) ≤
        LinearGrowth.linearGrowthSup (fun order => (cost order : EReal)) := by
    exact Frequently.le_linearGrowthSup <|
      Frequently.of_forall fun order => by
        simpa only [zero_mul] using (cost order).cast_nonneg'
  obtain ⟨rate : ℝ, growth_lt_rate, rate_lt_slope⟩ :=
    EReal.exists_between_coe_real subcritical
  have rate_pos : 0 < rate := by
    have : (0 : EReal) < (rate : EReal) :=
      growth_nonnegative.trans_lt growth_lt_rate
    exact EReal.coe_lt_coe_iff.mp <| by
      simpa only [EReal.coe_zero] using this
  have rate_lt_slope_real : rate < (slope : ℝ) := by
    simpa only [← EReal.coe_coe_eq_natCast,
      EReal.coe_lt_coe_iff] using rate_lt_slope
  have eventual_cost :
      ∀ᶠ order : ℕ in atTop,
        (cost order : EReal) ≤ (rate : EReal) * order :=
    LinearGrowth.eventually_le_mul growth_lt_rate
  obtain ⟨tailCutoff, afterTailCutoff⟩ :=
    eventually_atTop.1 eventual_cost
  have gap_pos : 0 < (slope : ℝ) - rate :=
    sub_pos.mpr rate_lt_slope_real
  obtain ⟨shiftCutoff : ℕ, shiftCutoff_large⟩ :=
    exists_nat_gt (rate / ((slope : ℝ) - rate))
  refine ⟨max tailCutoff shiftCutoff, ?_⟩
  intro row hrow
  have tailCutoff_le : tailCutoff ≤ row + 1 :=
    (Nat.le_max_left tailCutoff shiftCutoff).trans hrow |>.trans
      (Nat.le_succ row)
  have cost_bound_ereal :=
    afterTailCutoff (row + 1) tailCutoff_le
  have cost_bound_real :
      (cost (row + 1) : ℝ) ≤ rate * (row + 1 : ℕ) := by
    simpa only [← EReal.coe_coe_eq_natCast, ← EReal.coe_mul,
      EReal.coe_le_coe_iff] using cost_bound_ereal
  have shiftCutoff_le : shiftCutoff ≤ row :=
    (Nat.le_max_right tailCutoff shiftCutoff).trans hrow
  have shiftCutoff_le_real : (shiftCutoff : ℝ) ≤ row := by
    exact_mod_cast shiftCutoff_le
  have rate_lt_gap_mul_shift :
      rate < ((slope : ℝ) - rate) * shiftCutoff :=
    by simpa only [mul_comm] using
      (div_lt_iff₀ gap_pos).mp shiftCutoff_large
  have rate_lt_gap_mul_row :
      rate < ((slope : ℝ) - rate) * row :=
    rate_lt_gap_mul_shift.trans_le <|
      mul_le_mul_of_nonneg_left shiftCutoff_le_real gap_pos.le
  have shifted_bound_real :
      (cost (row + 1) : ℝ) < (slope * row : ℕ) := by
    calc
      (cost (row + 1) : ℝ) ≤ rate * (row + 1 : ℕ) :=
        cost_bound_real
      _ = rate * row + rate := by push_cast; ring
      _ < rate * row + ((slope : ℝ) - rate) * row :=
        by simpa only [add_comm] using
          add_lt_add_right rate_lt_gap_mul_row (rate * (row : ℝ))
      _ = (slope * row : ℕ) := by push_cast; ring
  exact_mod_cast shifted_bound_real

/-- Strict ordinary upper linear growth plus the exact critical support charge
makes the shifted critical support finite. -/
theorem rowSupport_finite_of_linearGrowthSup_lt
    (support : ℕ → Prop) (cost : ℕ → ℕ) (slope : ℕ)
    (subcritical :
      LinearGrowth.linearGrowthSup (fun order => (cost order : EReal)) <
        (slope : EReal))
    (supportCosts : ∀ row, support row →
      slope * row ≤ cost (row + 1)) :
    {row : ℕ | support row}.Finite := by
  obtain ⟨cutoff, strictTail⟩ :=
    strict_affine_tail_of_linearGrowthSup_lt cost slope subcritical
  exact rowSupport_finite_of_strict_tail support
    (fun row => cost (row + 1)) slope cutoff strictTail supportCosts

/-- Named terminal binding the unshifted statistic to both its shifted strict
tail and the charged-support consequence. -/
theorem linear_growth_affine_shift_terminal_certificate :
    (∀ (cost : ℕ → ℕ) (slope : ℕ),
      LinearGrowth.linearGrowthSup (fun order => (cost order : EReal)) <
          (slope : EReal) →
      ∃ cutoff, ∀ row, cutoff ≤ row →
        cost (row + 1) < slope * row) ∧
    (∀ (support : ℕ → Prop) (cost : ℕ → ℕ) (slope : ℕ),
      LinearGrowth.linearGrowthSup (fun order => (cost order : EReal)) <
          (slope : EReal) →
      (∀ row, support row → slope * row ≤ cost (row + 1)) →
      {row : ℕ | support row}.Finite) := by
  exact ⟨strict_affine_tail_of_linearGrowthSup_lt,
    rowSupport_finite_of_linearGrowthSup_lt⟩

/-- Zero-margin control: a pointwise strict bound at logarithmic order
`row + 1` is compatible with threshold-paying support in every critical row.
Thus strict pointwise inequalities cannot replace a uniform asymptotic
margin. -/
theorem zero_margin_affine_shift_negative_control :
    (∀ row : ℕ, 0 < row + 1 →
      2 * ((row + 1) - 1) < 2 * (row + 1)) ∧
    (∀ row : ℕ, 2 * row ≤ 2 * ((row + 1) - 1)) ∧
    (Set.univ : Set ℕ).Infinite := by
  constructor
  · intro row _
    omega
  constructor
  · intro row
    omega
  · exact Set.infinite_univ

/-- Consolidated support-to-cost and affine-margin certificate. -/
theorem support_to_cost_affine_margin_terminal_certificate :
    (∀ (support : ℕ → Prop) (cost : ℕ → ℕ) (slope cutoff : ℕ),
      (∀ n, cutoff ≤ n → cost n < slope * n) →
      (∀ n, support n → slope * n ≤ cost n) →
      {n : ℕ | support n}.Finite) ∧
    (∀ (support : ℕ → Prop) (cost : ℕ → ℕ) (slope : ℕ),
      {n : ℕ | support n}.Infinite →
      (∀ n, support n → slope * n ≤ cost n) →
      ∀ cutoff, ∃ row, cutoff < row ∧ support row ∧
        slope * row ≤ cost row) ∧
    (∀ (support : ℕ → Prop) (cost : ℕ → ℕ)
        (slope margin denominator cutoff : ℕ),
      0 < margin → 0 < denominator →
      (∀ row, cutoff ≤ row →
        denominator * cost (row + 1) + margin * (row + 1) ≤
          denominator * slope * (row + 1)) →
      (∀ row, support row → slope * row ≤ cost (row + 1)) →
      {row : ℕ | support row}.Finite) ∧
    ((∀ row : ℕ, 0 < row + 1 →
        2 * ((row + 1) - 1) < 2 * (row + 1)) ∧
      (∀ row : ℕ, 2 * row ≤ 2 * ((row + 1) - 1)) ∧
      (Set.univ : Set ℕ).Infinite) := by
  refine ⟨rowSupport_finite_of_strict_tail,
    infinite_rowSupport_forces_late_charge, ?_,
    zero_margin_affine_shift_negative_control⟩
  intro support cost slope margin denominator cutoff margin_pos
    _denominator_pos marginTail supportCosts
  exact rowSupport_finite_of_positive_margin support cost slope margin
    denominator cutoff margin_pos marginTail supportCosts

end ZtareProofs.FilteredCriticalSupport
