/-
LeanMill campaign provenance — base_rate_governs_positive_predictive_value
The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run
telemetry (run_tag=bayes_screen) by promote_campaign_artifact.py — not hand-authored.

  outcome     : closed · faithful · axioms propext, Classical.choice, Quot.sound
  domain      : formalization-nonmath
  time        : wall 2706.35s launch→close = formalize 1398.01s (theory+statement+firewall) + prove 1308.34s (proof search) · prove p50 1415.66s p95 2144.07s
  compute     : cost-to-closure 352.31s mean · 431.99s total
  yield       : 9/17 attempts closed (4 failed)
  phases      : 1508.2s leaf.dispatch · 613s pool · 332.1s consolidate · 269.3s formalize · 39.7s native · 8.3s govern.mnc
  reuse       : 8 rung(s) banked this run · 0 reused from prior bank
  moves       : native_hammer×9 · proposer_pool×4 · claude_warm×4
  milestone   : campaign family 'bayes_screen' — 1 run(s) · REAL elapsed (launch→last) 2706.5s (~45 min) = formalize 562.4s + prove/other · active-solve 432s · 9 closures [launch→last is the honest wall]
     - bayes_screen: 9/17 closed · elapsed 2706.5s (~45.1 min)
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/bayesian_screening_ppv_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

/-!
# Bayesian screening substrate

This file supplies the formal vocabulary for a screening test where the
meaning of a positive result is governed by the base rate.

Definition trial log:
* Screening candidate A: carry raw parameters `π se sp` and repeat range
  hypotheses on every theorem.  Workable for single arithmetic facts, but the
  rate ranges are load-bearing and become easy to omit.
* Screening candidate B: use subtype-valued fields for the three rates.  This
  proves ranges by construction, but coercions obscure the cross-multiplied
  threshold formulas the campaign wants to cite.
* Screening candidate C, selected: a `Screening` bundle with ordinary field
  fields plus proof fields for `π ∈ (0,1)` and `se, sp ∈ (0,1]`.  Formula
  definitions remain raw functions of the rates, so arithmetic lemmas can be
  reused outside a bundle, while the bundle records the hypotheses that make
  the positive predictive value meaningful.
* Positive-predictive-value candidate A: define only the ratio
  `se * π / (se * π + (1 - sp) * (1 - π))`.  Selected, but paired with the
  separate mass definitions below so threshold lemmas can stay division-free.
* Positive-predictive-value candidate B: define the gate `PPV ≥ 1/2` directly
  as `se * π ≥ (1 - sp) * (1 - π)`.  Rejected as the numeric PPV definition:
  it is the right decision predicate, but it would erase the posterior share
  itself.  It is kept as `positivePredictiveValueClearsHalf`.
* Positive-predictive-value candidate C: define a conditional probability from
  a probability space.  Rejected for this first substrate because the campaign
  only needs the two-cell Bayes table over ordered-field quantities, and the
  Mathlib probability layer would add measurable-space obligations unrelated
  to the target arithmetic.

No selected definition universally quantifies over membership in a constructed
set, so the vacuity guard is not triggered in this file.
-/

namespace BayesianScreening

variable {K : Type*} [Field K] [LinearOrder K] [IsStrictOrderedRing K]

/-! ## Rate ranges -/

/-- A strict probability rate: `0 < x < 1`. -/
def RateOpenUnit (x : K) : Prop :=
  0 < x ∧ x < 1

/-- Anchor (characterization): `RateOpenUnit` is membership in `Set.Ioo 0 1`. -/
theorem anchor_RateOpenUnit_iff_mem_Ioo (x : K) :
    RateOpenUnit x ↔ x ∈ Set.Ioo (0 : K) 1 := by
  rfl

/-- A positive probability rate that may be perfect: `0 < x ≤ 1`. -/
def RatePositiveUnit (x : K) : Prop :=
  0 < x ∧ x ≤ 1

/-- Anchor (characterization): `RatePositiveUnit` is membership in `Set.Ioc 0 1`. -/
theorem anchor_RatePositiveUnit_iff_mem_Ioc (x : K) :
    RatePositiveUnit x ↔ x ∈ Set.Ioc (0 : K) 1 := by
  rfl

/-- Sanity: `1/2` is a strict probability rate. -/
theorem sanity_half_RateOpenUnit : RateOpenUnit (1 / 2 : K) := by
  constructor <;> norm_num

/-- Sanity: `1/2` is a positive probability rate. -/
theorem sanity_half_RatePositiveUnit : RatePositiveUnit (1 / 2 : K) := by
  constructor <;> norm_num

/-- Sanity: `1` is an allowed positive-unit rate, recording perfect sensitivity/specificity. -/
theorem sanity_one_RatePositiveUnit : RatePositiveUnit (1 : K) := by
  constructor <;> norm_num

/-! ## Screening bundles and Bayes-table masses -/

/--
A screening-test instance: prevalence `π`, sensitivity `se`, and specificity
`sp`, with the rate ranges needed by the Bayesian interpretation.
-/
structure Screening (K : Type*) [Field K] [LinearOrder K] [IsStrictOrderedRing K] where
  prevalence : K
  sensitivity : K
  specificity : K
  prevalence_rate : RateOpenUnit prevalence
  sensitivity_rate : RatePositiveUnit sensitivity
  specificity_rate : RatePositiveUnit specificity

/--
Anchor (characterization): two screening bundles are equal exactly when the
three economic rates are equal; the remaining fields are proof data.
-/
theorem anchor_Screening_ext_iff (x y : Screening K) :
    x = y ↔
      x.prevalence = y.prevalence ∧
        x.sensitivity = y.sensitivity ∧ x.specificity = y.specificity := by
  constructor
  · intro h
    subst h
    simp
  · intro h
    rcases x with ⟨π, se, sp, hπ, hse, hsp⟩
    rcases y with ⟨π', se', sp', hπ', hse', hsp'⟩
    rcases h with ⟨hπeq, hseeq, hspeq⟩
    simp only at hπeq hseeq hspeq
    subst hπeq
    subst hseeq
    subst hspeq
    simp

/-- A canonical inhabited screening test with all three rates equal to `1/2`. -/
def halfScreening : Screening K :=
  { prevalence := 1 / 2
    sensitivity := 1 / 2
    specificity := 1 / 2
    prevalence_rate := sanity_half_RateOpenUnit
    sensitivity_rate := sanity_half_RatePositiveUnit
    specificity_rate := sanity_half_RatePositiveUnit }

/-- Witness: the screening substrate is inhabited. -/
theorem witness_Screening_nonempty : Nonempty (Screening K) :=
  ⟨halfScreening⟩

/-- Anchor (special-case reduction): the canonical screening bundle has the advertised fields. -/
theorem anchor_halfScreening_fields :
    (halfScreening : Screening K).prevalence = 1 / 2 ∧
      (halfScreening : Screening K).sensitivity = 1 / 2 ∧
        (halfScreening : Screening K).specificity = 1 / 2 := by
  simp [halfScreening]

/-- True-positive mass: the population fraction that has the condition and tests positive. -/
def truePositiveMass (se π : K) : K :=
  se * π

/-- Anchor (characterization): true-positive mass is multiplication of sensitivity and prevalence. -/
theorem anchor_truePositiveMass_eq_mul (se π : K) :
    truePositiveMass se π = se * π := by
  rfl

/-- False-positive mass: the population fraction without the condition that still tests positive. -/
def falsePositiveMass (sp π : K) : K :=
  (1 - sp) * (1 - π)

/-- Anchor (characterization): false-positive mass is false-positive rate times non-prevalence. -/
theorem anchor_falsePositiveMass_eq_mul (sp π : K) :
    falsePositiveMass sp π = (1 - sp) * (1 - π) := by
  rfl

/-- Positive-result mass: the population fraction testing positive. -/
def positiveMass (se sp π : K) : K :=
  truePositiveMass se π + falsePositiveMass sp π

/-- Anchor (characterization): positive mass is true-positive mass plus false-positive mass. -/
theorem anchor_positiveMass_eq_add (se sp π : K) :
    positiveMass se sp π = truePositiveMass se π + falsePositiveMass sp π := by
  rfl

/-- Positive predictive value: the true-positive share among positive results. -/
def PositivePredictiveValue (se sp π : K) : K :=
  truePositiveMass se π / positiveMass se sp π

/-- Anchor (characterization): PPV is true-positive mass divided by positive-result mass. -/
theorem anchor_PositivePredictiveValue_eq_div (se sp π : K) :
    PositivePredictiveValue se sp π = truePositiveMass se π / positiveMass se sp π := by
  rfl

/--
The division-free gate corresponding to "a positive result is more likely true
than false": true-positive mass meets false-positive mass.
-/
def positivePredictiveValueClearsHalf (se sp π : K) : Prop :=
  truePositiveMass se π ≥ falsePositiveMass sp π

/--
Anchor (characterization): the more-likely-than-not gate is exactly the
cross-multiplied base-rate threshold.
-/
theorem anchor_positivePredictiveValueClearsHalf_iff_threshold (se sp π : K) :
    positivePredictiveValueClearsHalf se sp π ↔
      se * π ≥ (1 - sp) * (1 - π) := by
  rfl

/-! ## Proven sanity lemmas for the selected definitions -/

/-- Sanity: true-positive mass is strictly positive under the screening rate ranges. -/
theorem truePositiveMass_pos
    {se π : K} (hse : RatePositiveUnit se) (hπ : RateOpenUnit π) :
    0 < truePositiveMass se π := by
  exact mul_pos hse.1 hπ.1

/-- Sanity: false-positive mass is nonnegative under the screening rate ranges. -/
theorem falsePositiveMass_nonneg
    {sp π : K} (hsp : RatePositiveUnit sp) (hπ : RateOpenUnit π) :
    0 ≤ falsePositiveMass sp π := by
  exact mul_nonneg (sub_nonneg.mpr hsp.2) (le_of_lt (sub_pos.mpr hπ.2))

/-- Sanity: the positive-result mass is strictly positive, so PPV is well-defined. -/
theorem positiveMass_pos_of_rates
    {se sp π : K}
    (hse : RatePositiveUnit se) (hsp : RatePositiveUnit sp) (hπ : RateOpenUnit π) :
    0 < positiveMass se sp π := by
  unfold positiveMass
  exact add_pos_of_pos_of_nonneg
    (truePositiveMass_pos hse hπ) (falsePositiveMass_nonneg hsp hπ)

/-- Sanity: the positive-result mass of a bundled screening test is strictly positive. -/
theorem Screening.positiveMass_pos (s : Screening K) :
    0 < positiveMass s.sensitivity s.specificity s.prevalence :=
  positiveMass_pos_of_rates s.sensitivity_rate s.specificity_rate s.prevalence_rate

/-- Sanity: the half-rate screening test has true-positive mass `1/4`. -/
theorem sanity_half_truePositiveMass :
    truePositiveMass (1 / 2 : K) (1 / 2 : K) = 1 / 4 := by
  norm_num [truePositiveMass]

/-- Sanity: the half-rate screening test has false-positive mass `1/4`. -/
theorem sanity_half_falsePositiveMass :
    falsePositiveMass (1 / 2 : K) (1 / 2 : K) = 1 / 4 := by
  norm_num [falsePositiveMass]

/-- Sanity: the half-rate screening test has positive-result mass `1/2`. -/
theorem sanity_half_positiveMass :
    positiveMass (1 / 2 : K) (1 / 2 : K) (1 / 2 : K) = 1 / 2 := by
  norm_num [positiveMass, truePositiveMass, falsePositiveMass]

/-- Sanity: the half-rate screening test has positive predictive value `1/2`. -/
theorem sanity_half_PositivePredictiveValue :
    PositivePredictiveValue (1 / 2 : K) (1 / 2 : K) (1 / 2 : K) = 1 / 2 := by
  norm_num [PositivePredictiveValue, positiveMass, truePositiveMass, falsePositiveMass]

/-- Sanity: perfect specificity eliminates false-positive mass. -/
theorem falsePositiveMass_eq_zero_of_specificity_one (π : K) :
    falsePositiveMass (1 : K) π = 0 := by
  simp [falsePositiveMass]

/-- Sanity: with perfect specificity, PPV is `1` whenever sensitivity and prevalence are positive. -/
theorem PositivePredictiveValue_eq_one_of_specificity_one
    {se π : K} (hse : RatePositiveUnit se) (hπ : RateOpenUnit π) :
    PositivePredictiveValue se (1 : K) π = 1 := by
  have htp_ne : se * π ≠ 0 := ne_of_gt (mul_pos hse.1 hπ.1)
  unfold PositivePredictiveValue positiveMass truePositiveMass falsePositiveMass
  simp [htp_ne]

/--
Sanity/model case: even with perfect sensitivity, specificity `1/2` and
prevalence `1/10` produce more false positives than true positives.
-/
theorem sanity_low_prevalence_false_mass_dominates :
    truePositiveMass (1 : K) (1 / 10 : K) <
      falsePositiveMass (1 / 2 : K) (1 / 10 : K) := by
  norm_num [truePositiveMass, falsePositiveMass]

/-- Sanity/model case: in that low-prevalence case, PPV is below one half. -/
theorem sanity_low_prevalence_PositivePredictiveValue_lt_half :
    PositivePredictiveValue (1 : K) (1 / 2 : K) (1 / 10 : K) < 1 / 2 := by
  norm_num [PositivePredictiveValue, positiveMass, truePositiveMass, falsePositiveMass]

/--
Sanity: the division-free gate agrees with the numeric `≥ 1/2` PPV comparison
under the rate ranges.
-/
theorem PositivePredictiveValue_ge_half_iff_positivePredictiveValueClearsHalf
    {se sp π : K}
    (hse : RatePositiveUnit se) (hsp : RatePositiveUnit sp) (hπ : RateOpenUnit π) :
    PositivePredictiveValue se sp π ≥ 1 / 2 ↔
      positivePredictiveValueClearsHalf se sp π := by
  have hpos : 0 < positiveMass se sp π := positiveMass_pos_of_rates hse hsp hπ
  unfold PositivePredictiveValue positivePredictiveValueClearsHalf
  rw [ge_iff_le, le_div_iff₀ hpos]
  unfold positiveMass
  constructor <;> intro h
  · nlinarith
  · nlinarith

/-! ## Deeper campaign API statements -/

/-- The sharp, division-free base-rate threshold for PPV clearing one half. -/
theorem PositivePredictiveValue_ge_half_iff_threshold
    {se sp π : K}
    (hse : RatePositiveUnit se) (hsp : RatePositiveUnit sp) (hπ : RateOpenUnit π) :
    PositivePredictiveValue se sp π ≥ 1 / 2 ↔
      se * π ≥ (1 - sp) * (1 - π) := by
  simpa [anchor_positivePredictiveValueClearsHalf_iff_threshold] using
    PositivePredictiveValue_ge_half_iff_positivePredictiveValueClearsHalf
      (se := se) (sp := sp) (π := π) hse hsp hπ

/--
Raising prevalence, holding sensitivity and specificity fixed, weakly raises
the positive predictive value.
-/
theorem PositivePredictiveValue_mono_prevalence : ∀ {se sp π₁ π₂ : K}
    (hse : RatePositiveUnit se) (hsp : RatePositiveUnit sp)
    (hπ₁ : RateOpenUnit π₁) (hπ₂ : RateOpenUnit π₂)
    (hπle : π₁ ≤ π₂), PositivePredictiveValue se sp π₁ ≤ PositivePredictiveValue se sp π₂ := by
  intro se sp π₁ π₂ hse hsp hπ₁ hπ₂ hπle
  have hspc_nonneg : 0 ≤ 1 - sp := sub_nonneg.mpr hsp.2
  have hden₁ : 0 < se * π₁ + (1 - sp) * (1 - π₁) := by
    exact add_pos_of_pos_of_nonneg
      (mul_pos hse.1 hπ₁.1)
      (mul_nonneg hspc_nonneg (le_of_lt (sub_pos.mpr hπ₁.2)))
  have hden₂ : 0 < se * π₂ + (1 - sp) * (1 - π₂) := by
    exact add_pos_of_pos_of_nonneg
      (mul_pos hse.1 hπ₂.1)
      (mul_nonneg hspc_nonneg (le_of_lt (sub_pos.mpr hπ₂.2)))
  unfold PositivePredictiveValue positiveMass truePositiveMass falsePositiveMass
  rw [div_le_div_iff₀ hden₁ hden₂]
  have hdiff_nonneg : 0 ≤ π₂ - π₁ := sub_nonneg.mpr hπle
  have hprod_nonneg : 0 ≤ se * (1 - sp) * (π₂ - π₁) := by
    exact mul_nonneg (mul_nonneg (le_of_lt hse.1) hspc_nonneg) hdiff_nonneg
  nlinarith
theorem PositivePredictiveValue_mono_specificity : ∀ {se sp₁ sp₂ π : K}
    (hse : RatePositiveUnit se) (hsp₁ : RatePositiveUnit sp₁)
    (hsp₂ : RatePositiveUnit sp₂) (hπ : RateOpenUnit π)
    (hsple : sp₁ ≤ sp₂), PositivePredictiveValue se sp₁ π ≤ PositivePredictiveValue se sp₂ π := by
  intro se sp₁ sp₂ π hse hsp₁ hsp₂ hπ hsple
  have hsp₁c_nonneg : 0 ≤ 1 - sp₁ := sub_nonneg.mpr hsp₁.2
  have hsp₂c_nonneg : 0 ≤ 1 - sp₂ := sub_nonneg.mpr hsp₂.2
  have hπc_nonneg : 0 ≤ 1 - π := le_of_lt (sub_pos.mpr hπ.2)
  have hden₁ : 0 < se * π + (1 - sp₁) * (1 - π) := by
    exact add_pos_of_pos_of_nonneg
      (mul_pos hse.1 hπ.1)
      (mul_nonneg hsp₁c_nonneg hπc_nonneg)
  have hden₂ : 0 < se * π + (1 - sp₂) * (1 - π) := by
    exact add_pos_of_pos_of_nonneg
      (mul_pos hse.1 hπ.1)
      (mul_nonneg hsp₂c_nonneg hπc_nonneg)
  unfold PositivePredictiveValue positiveMass truePositiveMass falsePositiveMass
  rw [div_le_div_iff₀ hden₁ hden₂]
  nlinarith [mul_nonneg (mul_nonneg (le_of_lt hse.1) (le_of_lt hπ.1))
    (mul_nonneg (sub_nonneg.mpr hsple) hπc_nonneg)]
theorem exists_low_prevalence_falsePositiveMass_dominates_perfect_sensitivity : ∀ {sp : K} (hsp : RatePositiveUnit sp) (himperfect : sp < 1), ∃ π : K, RateOpenUnit π ∧
      truePositiveMass (1 : K) π < falsePositiveMass sp π := by
  intro sp hsp himperfect
  let π : K := (1 - sp) / 2
  have hcomp_pos : 0 < 1 - sp := sub_pos.mpr himperfect
  have hcomp_lt_one : 1 - sp < 1 := by
    nlinarith [hsp.1]
  refine ⟨π, ?_, ?_⟩
  · dsimp [RateOpenUnit, π]
    constructor
    · nlinarith
    · nlinarith
  · unfold truePositiveMass falsePositiveMass
    dsimp [π]
    nlinarith
theorem exists_low_prevalence_PositivePredictiveValue_lt_half_perfect_sensitivity : ∀ {sp : K} (hsp : RatePositiveUnit sp) (himperfect : sp < 1), ∃ π : K, RateOpenUnit π ∧
      PositivePredictiveValue (1 : K) sp π < 1 / 2 := by
  intro sp hsp himperfect
  let π : K := (1 - sp) / 2
  have hcomp_pos : 0 < 1 - sp := sub_pos.mpr himperfect
  have hcomp_lt_one : 1 - sp < 1 := by
    nlinarith [hsp.1]
  have hπ : RateOpenUnit π := by
    dsimp [RateOpenUnit, π]
    constructor
    · nlinarith
    · nlinarith
  have hden : 0 < (1 : K) * π + (1 - sp) * (1 - π) := by
    have hπ_pos : 0 < (1 : K) * π := by
      nlinarith [hπ.1]
    have hπ_lt_one : π < 1 := hπ.2
    have hfp_pos : 0 < (1 - sp) * (1 - π) := by
      exact mul_pos hcomp_pos (sub_pos.mpr hπ_lt_one)
    exact add_pos hπ_pos hfp_pos
  refine ⟨π, hπ, ?_⟩
  unfold PositivePredictiveValue positiveMass truePositiveMass falsePositiveMass
  rw [div_lt_iff₀ hden]
  dsimp [π]
  nlinarith
end BayesianScreening

section  -- [family-lemma-library] banked rungs (re-open env namespaces + section variables)
open BayesianScreening
variable {K : Type*} [Field K] [LinearOrder K] [IsStrictOrderedRing K]

-- [family-lemma-library] banked: base_rate_governs_positive_predictive_value
theorem base_rate_governs_positive_predictive_value :
    (∀ {se sp π : K},
      RatePositiveUnit se →
      RatePositiveUnit sp →
      RateOpenUnit π →
      (PositivePredictiveValue se sp π ≥ 1 / 2 ↔
        se * π ≥ (1 - sp) * (1 - π))) ∧
      (∀ {sp : K},
        RatePositiveUnit sp →
        sp < 1 →
        ∃ π : K, RateOpenUnit π ∧
          PositivePredictiveValue (1 : K) sp π < 1 / 2) := by
  (repeat' apply And.intro) <;> solve_by_elim [PositivePredictiveValue_ge_half_iff_threshold, exists_low_prevalence_PositivePredictiveValue_lt_half_perfect_sensitivity]

end
