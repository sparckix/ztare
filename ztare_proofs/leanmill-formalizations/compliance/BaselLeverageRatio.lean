/-
LeanMill campaign provenance — leverage_backstop_subsumes_risk_weighted_floor
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=basel_uniq_0702T2350) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 295.4s launch→close = formalize 190.84s (theory+statement+firewall) + prove 104.56s (proof search) · prove p50 0s p95 209.11s
  compute     : cost-to-closure 42.96s mean · 85.85s total
  yield       : 2/4 attempts closed (2 failed)
  phases      : 203.9s leaf.dispatch · 66.8s formalize · 14.9s pool · 5.7s native · 0.1s govern.mnc · 0s consolidate
  reuse       : cited 1 banked rung(s) — iso_lemma1
  moves       : cache_reuse×1 · proposer_pool×1 · native_hammer×1 · claude_warm×1
  milestone   : campaign family 'basel_uniq' — 1 run(s) · REAL elapsed (launch→last) 301.3s (~5 min) = formalize 92.2s + prove/other · active-solve 85.8s · 2 closures [launch→last is the honest wall]
     - basel_uniq_0702T2350: 2/4 closed · elapsed 301.3s (~5.0 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/basel_leverage_ratio_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

/-!
# Basel III leverage ratio substrate

This file formalizes the Basel leverage ratio as a non-risk-based capital
backstop against low effective risk weights.

Typeclass note: this Mathlib build does not expose the blueprint name
`LinearOrderedField` to the checker.  Ordered-field quantities are therefore
stated using the local primitive bundle
`[Field K] [LinearOrder K] [IsStrictOrderedRing K]`.

Definition trial notes for this dispatch:
* Total exposure candidate A: a raw function
  `onBalance + creditConversion * offBalance` with side conditions on every
  lemma.  Rejected as the selected public substrate because the nonnegativity
  and `[0,1]` credit-conversion hypotheses are repeatedly needed.
* Total exposure candidate B: use `NNReal` for every monetary amount and
  conversion factor.  Rejected for this campaign because the blueprint asks
  for ordered-field real-valued quantities and exact Basel constants over that
  field.
* Total exposure candidate C: bundle the on-balance amount, off-balance amount,
  credit-conversion factor, and their range proofs in `ExposureComponents`,
  with `TotalExposureMeasure` definitionally equal to the Basel formula.
  Selected: the sanity lemmas prove nonnegativity and conservatism over
  on-balance assets immediately, and later rungs consume a single constructed
  exposure term instead of compatibility side conditions.
* Compliance candidate A: ratio predicates such as
  `tier1 / exposure ≥ 3 / 100`.  Rejected because zero exposure would require
  denominator side conditions and the exact regulatory constants become less
  direct.
* Compliance candidate B: cross-multiplied predicates
  `100 * tier1 ≥ 3 * exposure` and
  `100 * tier1 ≥ 8 * (w * exposure)`.  Selected: they are exactly the
  regulatory inequalities and prove the boundary, closure, and sharpness
  lemmas by linear arithmetic.
* Risk-weight candidate A: hard-code `w : Set.Icc (0 : K) 1`.  Rejected for
  public APIs because coercions obscure the numeric crossover statement.
* Risk-weight candidate B: keep `w : K` and define the range predicate
  `RiskWeightInRange w := 0 ≤ w ∧ w ≤ 1`.  Selected: range is explicit at the
  call site, while `LowRiskWeightCrossover w := 8 * w ≤ 3` records the genuine
  Basel 37.5% boundary.

No selected definition universally quantifies over membership in a constructed
set, so the vacuity guard is not triggered in this file.
-/

namespace BaselLeverage

variable {K : Type*} [Field K] [LinearOrder K] [IsStrictOrderedRing K]

/-! ## Exposure measure -/

/--
Exposure inputs for the Basel total exposure measure: on-balance-sheet assets,
off-balance-sheet notional, and a credit-conversion factor in `[0,1]`.
-/
structure ExposureComponents (K : Type*) [Field K] [LinearOrder K]
    [IsStrictOrderedRing K] where
  onBalance : K
  offBalance : K
  creditConversion : K
  onBalance_nonneg : 0 ≤ onBalance
  offBalance_nonneg : 0 ≤ offBalance
  creditConversion_nonneg : 0 ≤ creditConversion
  creditConversion_le_one : creditConversion ≤ 1

/--
Anchor (characterization): equality of exposure-component bundles is equality
of the three economic fields.  The remaining fields are proof data.
-/
theorem anchor_ExposureComponents_ext_iff
    (x y : ExposureComponents K) :
    x = y ↔
      x.onBalance = y.onBalance ∧
        x.offBalance = y.offBalance ∧
          x.creditConversion = y.creditConversion := by
  constructor
  · intro h
    subst h
    simp
  · intro h
    rcases x with ⟨on, off, ccf, hon, hoff, hccf0, hccf1⟩
    rcases y with ⟨on', off', ccf', hon', hoff', hccf0', hccf1'⟩
    rcases h with ⟨honEq, hoffEq, hccfEq⟩
    simp only at honEq hoffEq hccfEq
    subst honEq
    subst hoffEq
    subst hccfEq
    simp

/--
The Basel total exposure measure: on-balance-sheet assets plus
credit-converted off-balance-sheet exposure.
-/
def TotalExposureMeasure (x : ExposureComponents K) : K :=
  x.onBalance + x.creditConversion * x.offBalance

/-- Anchor (characterization): total exposure is exactly the Basel sum. -/
theorem anchor_TotalExposureMeasure_eq_add_mul
    (x : ExposureComponents K) :
    TotalExposureMeasure x =
      x.onBalance + x.creditConversion * x.offBalance := by
  rfl

/-- Sanity: the zero exposure-component bundle exists. -/
theorem exposureComponents_nonempty : Nonempty (ExposureComponents K) := by
  refine ⟨?_⟩
  exact
    { onBalance := 0
      offBalance := 0
      creditConversion := 0
      onBalance_nonneg := le_rfl
      offBalance_nonneg := le_rfl
      creditConversion_nonneg := le_rfl
      creditConversion_le_one := zero_le_one }

/-- Sanity: Basel total exposure is nonnegative. -/
theorem totalExposureMeasure_nonneg
    (x : ExposureComponents K) :
    0 ≤ TotalExposureMeasure x := by
  unfold TotalExposureMeasure
  exact add_nonneg x.onBalance_nonneg
    (mul_nonneg x.creditConversion_nonneg x.offBalance_nonneg)

/--
Sanity: total exposure is at least on-balance-sheet assets alone, because the
off-balance add-on is nonnegative.
-/
theorem totalExposureMeasure_ge_onBalance
    (x : ExposureComponents K) :
    x.onBalance ≤ TotalExposureMeasure x := by
  unfold TotalExposureMeasure
  exact le_add_of_nonneg_right
    (mul_nonneg x.creditConversion_nonneg x.offBalance_nonneg)

/-- Sanity: no off-balance notional leaves total exposure equal to on-balance assets. -/
theorem totalExposureMeasure_zero_offBalance
    {on ccf : K} (hon : 0 ≤ on) (hccf0 : 0 ≤ ccf) (hccf1 : ccf ≤ 1) :
    TotalExposureMeasure
      ({ onBalance := on
         offBalance := 0
         creditConversion := ccf
         onBalance_nonneg := hon
         offBalance_nonneg := le_rfl
         creditConversion_nonneg := hccf0
         creditConversion_le_one := hccf1 } : ExposureComponents K) = on := by
  simp [TotalExposureMeasure]

/-- Sanity: a zero credit-conversion factor ignores off-balance notional. -/
theorem totalExposureMeasure_zero_creditConversion
    {on off : K} (hon : 0 ≤ on) (hoff : 0 ≤ off) :
    TotalExposureMeasure
      ({ onBalance := on
         offBalance := off
         creditConversion := 0
         onBalance_nonneg := hon
         offBalance_nonneg := hoff
         creditConversion_nonneg := le_rfl
         creditConversion_le_one := zero_le_one } : ExposureComponents K) = on := by
  simp [TotalExposureMeasure]

/-- Sanity: a unit credit-conversion factor adds the full off-balance notional. -/
theorem totalExposureMeasure_one_creditConversion
    {on off : K} (hon : 0 ≤ on) (hoff : 0 ≤ off) :
    TotalExposureMeasure
      ({ onBalance := on
         offBalance := off
         creditConversion := 1
         onBalance_nonneg := hon
         offBalance_nonneg := hoff
         creditConversion_nonneg := zero_le_one
         creditConversion_le_one := le_rfl } : ExposureComponents K) =
        on + off := by
  simp [TotalExposureMeasure]

/-! ## Risk weights and capital floors -/

/-- Effective average risk weight lies in the Basel range `[0,1]`. -/
def RiskWeightInRange (w : K) : Prop :=
  0 ≤ w ∧ w ≤ 1

/-- Anchor (characterization): risk-weight range is exactly membership in `Set.Icc 0 1`. -/
theorem anchor_RiskWeightInRange_iff_mem_Icc (w : K) :
    RiskWeightInRange w ↔ w ∈ Set.Icc (0 : K) 1 := by
  rfl

/-- The crossover regime where the 8% risk-weighted floor does not dominate the 3% flat floor. -/
def LowRiskWeightCrossover (w : K) : Prop :=
  8 * w ≤ 3

/-- Anchor (characterization): the crossover is the equivalent `w ≤ 3/8` boundary. -/
theorem anchor_LowRiskWeightCrossover_iff_le_three_eighths
    (w : K) :
    LowRiskWeightCrossover w ↔ w ≤ (3 / 8 : K) := by
  unfold LowRiskWeightCrossover
  constructor <;> intro h <;> nlinarith

/-- Risk-weighted assets from total exposure and effective risk weight. -/
def RiskWeightedExposure (exposure w : K) : K :=
  w * exposure

/-- Anchor (characterization): risk-weighted exposure is Mathlib multiplication. -/
theorem anchor_RiskWeightedExposure_eq_mul
    (exposure w : K) :
    RiskWeightedExposure exposure w = w * exposure := by
  rfl

/-- Basel leverage-ratio compliance: Tier-1 capital is at least 3% of total exposure. -/
def LeverageCompliant (tier1 exposure : K) : Prop :=
  100 * tier1 ≥ 3 * exposure

/-- Anchor (characterization): leverage compliance is the cross-multiplied 3% floor. -/
theorem anchor_LeverageCompliant_iff
    (tier1 exposure : K) :
    LeverageCompliant tier1 exposure ↔ 100 * tier1 ≥ 3 * exposure := by
  rfl

/--
Risk-weighted capital floor: Tier-1 capital is at least 8% of risk-weighted
assets.
-/
def RiskWeightedCapitalFloor (tier1 exposure w : K) : Prop :=
  100 * tier1 ≥ 8 * RiskWeightedExposure exposure w

/-- Anchor (characterization): risk-weighted floor is the cross-multiplied 8% floor. -/
theorem anchor_RiskWeightedCapitalFloor_iff
    (tier1 exposure w : K) :
    RiskWeightedCapitalFloor tier1 exposure w ↔
      100 * tier1 ≥ 8 * (w * exposure) := by
  rfl

/-- Sanity: zero is a valid risk weight. -/
theorem riskWeightInRange_zero :
    RiskWeightInRange (0 : K) := by
  constructor <;> norm_num

/-- Sanity: one is a valid risk weight. -/
theorem riskWeightInRange_one :
    RiskWeightInRange (1 : K) := by
  constructor <;> norm_num

/-- Sanity: the Basel crossover boundary `3/8 = 37.5%` is in range. -/
theorem riskWeightInRange_three_eighths :
    RiskWeightInRange (3 / 8 : K) := by
  constructor <;> norm_num

/-- Sanity: zero risk weight is inside the low-risk crossover regime. -/
theorem lowRiskWeightCrossover_zero :
    LowRiskWeightCrossover (0 : K) := by
  unfold LowRiskWeightCrossover
  norm_num

/-- Sanity: the exact `3/8` boundary is inside the crossover regime. -/
theorem lowRiskWeightCrossover_three_eighths :
    LowRiskWeightCrossover (3 / 8 : K) := by
  rw [anchor_LowRiskWeightCrossover_iff_le_three_eighths]

/-- Sanity: zero risk weight gives zero risk-weighted exposure. -/
theorem riskWeightedExposure_zero_weight (exposure : K) :
    RiskWeightedExposure exposure (0 : K) = 0 := by
  simp [RiskWeightedExposure]

/-- Sanity: unit risk weight leaves exposure unchanged. -/
theorem riskWeightedExposure_one_weight (exposure : K) :
    RiskWeightedExposure exposure (1 : K) = exposure := by
  simp [RiskWeightedExposure]

/-- Sanity: in-range risk weights preserve exposure nonnegativity. -/
theorem riskWeightedExposure_nonneg
    {exposure w : K} (hexposure : 0 ≤ exposure)
    (hw : RiskWeightInRange w) :
    0 ≤ RiskWeightedExposure exposure w := by
  exact mul_nonneg hw.1 hexposure

/-! ## Basel leverage API -/

/--
The leverage requirement caps total exposure at `100/3` times Tier-1 capital.
-/
theorem leverage_compliant_exposure_le_cap
    {tier1 exposure : K} (h : LeverageCompliant tier1 exposure) :
    exposure ≤ (100 / 3 : K) * tier1 := by
  unfold LeverageCompliant at h
  nlinarith

/--
Consolidating two leverage-compliant books yields a leverage-compliant merged
book.
-/
theorem leverage_compliant_add
    {tier1A tier1B exposureA exposureB : K}
    (hA : LeverageCompliant tier1A exposureA)
    (hB : LeverageCompliant tier1B exposureB) :
    LeverageCompliant (tier1A + tier1B) (exposureA + exposureB) := by
  unfold LeverageCompliant at *
  nlinarith

/-- Raising Tier-1 capital while holding exposure fixed preserves compliance. -/
theorem leverage_compliant_raise_capital
    {tier1 tier1' exposure : K}
    (h : LeverageCompliant tier1 exposure) (hraise : tier1 ≤ tier1') :
    LeverageCompliant tier1' exposure := by
  unfold LeverageCompliant at *
  nlinarith

/-- Reducing total exposure while holding Tier-1 capital fixed preserves compliance. -/
theorem leverage_compliant_deleverage
    {tier1 exposure exposure' : K}
    (h : LeverageCompliant tier1 exposure) (hdelev : exposure' ≤ exposure) :
    LeverageCompliant tier1 exposure' := by
  unfold LeverageCompliant at *
  nlinarith

/-- The inclusive Basel 3% floor is sharp at equality. -/
theorem leverage_floor_sharp_equal
    {tier1 exposure : K} (h : 100 * tier1 = 3 * exposure) :
    LeverageCompliant tier1 exposure := by
  unfold LeverageCompliant
  nlinarith

/-- Any institution strictly below the 3% floor is not leverage-compliant. -/
theorem leverage_floor_sharp_strict
    {tier1 exposure : K} (h : 100 * tier1 < 3 * exposure) :
    ¬ LeverageCompliant tier1 exposure := by
  unfold LeverageCompliant
  nlinarith

/--
Backstop theorem, raw exposure form: under nonnegative exposure, an in-range
risk weight, and the crossover boundary `8*w ≤ 3`, leverage compliance
subsumes the 8% risk-weighted capital floor.
-/
theorem leverage_backstop_subsumes_risk_weighted_floor
    {tier1 exposure w : K}
    (hexposure : 0 ≤ exposure)
    (_hw : RiskWeightInRange w)
    (hcross : LowRiskWeightCrossover w)
    (hlev : LeverageCompliant tier1 exposure) :
    RiskWeightedCapitalFloor tier1 exposure w := by
  unfold LowRiskWeightCrossover at hcross
  unfold LeverageCompliant at hlev
  unfold RiskWeightedCapitalFloor RiskWeightedExposure
  nlinarith [mul_le_mul_of_nonneg_right hcross hexposure]

/--
Backstop theorem, constructed-exposure form: the total exposure measure supplies
the required nonnegativity hypothesis, and the same `8*w ≤ 3` crossover turns
leverage compliance into risk-weighted floor compliance.
-/
theorem leverage_backstop_subsumes_risk_weighted_floor_of_components
    {tier1 w : K} (x : ExposureComponents K)
    (_htier1 : 0 ≤ tier1)
    (hw : RiskWeightInRange w)
    (hcross : LowRiskWeightCrossover w)
    (hlev : LeverageCompliant tier1 (TotalExposureMeasure x)) :
    RiskWeightedCapitalFloor tier1 (TotalExposureMeasure x) w := by
  exact leverage_backstop_subsumes_risk_weighted_floor
    (totalExposureMeasure_nonneg x) hw hcross hlev

/--
Deep API statement for later solver work: in the low-risk regime, the leverage
floor is pointwise at least as demanding as the risk-weighted floor for every
nonnegative exposure.
-/
theorem leverage_floor_ge_risk_weighted_floor_under_crossover
    {exposure w : K} (hexposure : 0 ≤ exposure)
    (hw : RiskWeightInRange w)
    (hcross : LowRiskWeightCrossover w) :
    8 * RiskWeightedExposure exposure w ≤ 3 * exposure := by
  unfold LowRiskWeightCrossover at hcross
  unfold RiskWeightedExposure
  nlinarith [mul_le_mul_of_nonneg_right hcross hexposure,
    mul_nonneg hw.1 hexposure]

end BaselLeverage
