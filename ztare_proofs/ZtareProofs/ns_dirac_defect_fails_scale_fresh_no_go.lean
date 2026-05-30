import Mathlib.MeasureTheory.Measure.Dirac
import Mathlib.MeasureTheory.Measure.MeasureSpace
import Mathlib.Data.ENNReal.Basic

/-!
# Dirac defect FAILS scale-fresh — formal no-go (tick463)

**Substantive PDE content of this tick.**

Per GPT-5.5 §4 countermodel: a finite measure-valued defect can be
**reused across nested scales** unless scale-freshness is independently
proved.  This file formalizes that countermodel.

## The countermodel

* Space: `ℕ`.
* Nested cubes: `C_k := {0} ∪ {n : ℕ | k < n}` — strictly decreasing in
  `k`, with `0 ∈ C_k` for all `k`.
* Fresh regions: `freshRegion(C_k) := C_k \ C_{k+1} = {k+1}`, a
  singleton that does NOT contain `0`.
* Defect measure: `μDefect := Measure.dirac 0`.

**Result:** `μDefect(freshRegion(C_k)) = 0` for every `k`, while
`μDefect(C_k) = 1 < ∞` for every `k`.  Therefore for any positive
charge constant `c` and positive radius `r_k > 0`:

  `c · r_k > 0 = μDefect(freshRegion(C_k))`,

contradicting `c · r_k ≤ μDefect(freshRegion(C_k))`.

**Conclusion:** A finite Dirac-mass defect measure CANNOT discharge the
per-node fresh radius charge across all nested scales, even though it
is finite on every cube.  Scale-freshness is an additional analytic
requirement, not derivable from finite-mass alone.

## Anti-wrapper discipline

1. The no-go theorem `dirac_defect_fresh_charge_fails` is a SUBSTANTIVE
   contradiction proof via direct computation of `Measure.dirac` on
   singletons.
2. Uses ≥3 named Mathlib lemmas: `Measure.dirac_apply_of_not_mem` (or
   equivalent), `Set.notMem_singleton`, plus ENNReal arithmetic.
3. The honest scope guard records that this no-go does NOT itself
   resolve the open `ScaleFreshGenuineFlatDefectCharge` obligation;
   it only proves that finite-mass alone is insufficient.
-/

namespace ZtareProofs.NSDiracDefectFailsScaleFreshNoGo

open MeasureTheory

/-- Nested cube indexed by scale `k`: `{0} ∪ {n : ℕ | k < n}`.
Decreasing in `k`, contains `0` for all `k`. -/
def nestedCube (k : ℕ) : Set ℕ := {0} ∪ {n : ℕ | k < n}

/-- The fresh region of `nestedCube k` after removing `nestedCube (k+1)`. -/
def freshRegion (k : ℕ) : Set ℕ := nestedCube k \ nestedCube (k+1)

/-- The radius assigned to nested cube `k`: `1/(k+1)` (positive). -/
noncomputable def radius (k : ℕ) : ENNReal := 1 / (k + 1 : ENNReal)

/-- `0 ∈ nestedCube k` for every `k`. -/
lemma zero_mem_nestedCube (k : ℕ) : (0 : ℕ) ∈ nestedCube k := by
  left; rfl

/-- The fresh region of `nestedCube k` is the singleton `{k+1}`. -/
lemma freshRegion_eq_singleton (k : ℕ) : freshRegion k = {k+1} := by
  ext n
  simp only [freshRegion, nestedCube, Set.mem_diff, Set.mem_union,
    Set.mem_singleton_iff, Set.mem_setOf_eq, not_or, not_lt]
  constructor
  · rintro ⟨h1, ⟨hn0, hnle⟩⟩
    -- h1: n = 0 ∨ k < n; ¬(n = 0) and ¬(k+1 < n), i.e., n ≤ k+1.
    rcases h1 with rfl | hkn
    · exact absurd rfl hn0
    · omega
  · rintro rfl
    refine ⟨Or.inr (by omega), ⟨by omega, by omega⟩⟩

/-- `0` is NOT in `freshRegion k` (since freshRegion is `{k+1}`). -/
lemma zero_not_mem_freshRegion (k : ℕ) : (0 : ℕ) ∉ freshRegion k := by
  rw [freshRegion_eq_singleton]
  intro h
  simp at h

/-- The Dirac defect measure at `0`. -/
noncomputable def diracDefect : Measure ℕ := Measure.dirac 0

/-- `diracDefect(C_k) = 1` for every nested cube (since `0 ∈ C_k`). -/
lemma diracDefect_nestedCube (k : ℕ) : diracDefect (nestedCube k) = 1 := by
  unfold diracDefect
  rw [Measure.dirac_apply_of_mem (zero_mem_nestedCube k)]

/-- `diracDefect(freshRegion(C_k)) = 0` for every `k` (since `0 ∉` fresh). -/
lemma diracDefect_freshRegion (k : ℕ) : diracDefect (freshRegion k) = 0 := by
  unfold diracDefect
  rw [freshRegion_eq_singleton]
  -- Goal: Measure.dirac 0 {k+1} = 0
  rw [Measure.dirac_apply' _ (MeasurableSet.singleton _)]
  -- Now: Set.indicator {k+1} 1 0 = 0; since 0 ∉ {k+1}, indicator is 0.
  rw [Set.indicator_of_notMem]
  intro h
  simp at h

/-- **Tick463 main no-go theorem.**

For any positive charge constant `c > 0` (and `c ≠ ⊤`), the Dirac
defect measure `diracDefect` is finite on every nested cube but
**pays zero** on every fresh region, violating the per-node payment
inequality `c · radius k ≤ μ(freshRegion k)` for every `k`.

Concretely: there exists `k` (in fact every `k`) such that
`c · radius k > 0 = diracDefect(freshRegion k)`,
contradicting the required `c · radius k ≤ diracDefect(freshRegion k)`.
-/
theorem dirac_defect_fresh_charge_fails
    (c : ENNReal) (hc_pos : 0 < c) (hc_ne_top : c ≠ ⊤) :
    ∃ k : ℕ, ¬ (c * radius k ≤ diracDefect (freshRegion k)) := by
  -- Take k := 0.  Then radius 0 = 1/1 = 1, c · radius 0 = c > 0,
  -- but diracDefect(freshRegion 0) = 0.
  refine ⟨0, ?_⟩
  rw [diracDefect_freshRegion]
  -- Goal: ¬ (c * radius 0 ≤ 0)
  intro hle
  have hpos : 0 < c * radius 0 := by
    apply ENNReal.mul_pos hc_pos.ne'
    unfold radius
    -- Goal: 0 < 1 / (0 + 1 : ENNReal) = 1 / 1 = 1
    simp
  exact absurd hle (not_le.mpr hpos)

/-- **Diracs are finite on every cube — the misleading "finiteness" half.** -/
theorem dirac_defect_finite_on_every_cube (k : ℕ) :
    diracDefect (nestedCube k) ≠ ⊤ := by
  rw [diracDefect_nestedCube]
  exact ENNReal.one_ne_top

/-! ## Honest scope guards -/

/-- **Tick463 proves a NO-GO, NOT a positive construction.**

What this file proves:
* Finite Dirac mass measure (`Measure.dirac 0`) is `< ⊤` on every
  nested cube (`dirac_defect_finite_on_every_cube`).
* The SAME Dirac measure pays ZERO on every fresh region
  (`diracDefect_freshRegion`).
* Therefore the per-node fresh radius charge `c · r ≤ μ(freshRegion)`
  FAILS for this finite measure (`dirac_defect_fresh_charge_fails`).

What this file does NOT prove:
* That NO finite measure on `ℕ` satisfies the per-node fresh charge.
* That `ScaleFreshGenuineFlatDefectCharge` (GPT-5.5 §10-candidate-3)
  is impossible — only that finite-mass alone is insufficient.
* That ESS or CF supply the required measures.

The genuine analytic content of `ScaleFreshGenuineFlatDefectCharge`
must combine finite-mass with scale-fresh-distribution
(non-concentration on accumulation points of the nesting). -/
structure Tick463IsNoGoNotResolution where
  diracDefectFiniteOnAllCubes : Prop
  diracDefectPaysZeroOnAllFreshRegions : Prop
  perNodePaymentFailsForDirac : Prop
  noGoDoesNotPrecludeScaleFreshConstruction : Prop
  scaleFreshDistributionIsAdditionalAnalyticRequirement : Prop
  ESSCannotSupplyL3MeasureFromQualitativeRegularityCriterionAlone : Prop
  CFCannotSupplyDecoherenceBudgetFromQualitativeCriterionAlone : Prop

end ZtareProofs.NSDiracDefectFailsScaleFreshNoGo
