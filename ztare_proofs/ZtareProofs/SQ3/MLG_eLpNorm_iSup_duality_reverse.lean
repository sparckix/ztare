import Mathlib.Tactic
import Mathlib.MeasureTheory.Function.LpSeminorm.Defs
import Mathlib.MeasureTheory.Integral.MeanInequalities
import ZtareProofs.SQ3.MLG_eLpNorm_iSup_duality

/-!
# MLG-eLpNorm-iSup-duality (REVERSE half) — saturating-witness discharge

## §0. Pre-registration (PL-056, 2026-05-08, wall-clock min)

**Author**: claude:mlg_eLpNorm_duality_reverse_2026_05_08 (Opus 4.7)
**Pre-registration buckets** (conditional odds):
* 30% — reverse half closed sorry-free, build green
* 40% — partial: main case `1 < p < ∞` closed, edge cases (`p = 1`,
        `p = ∞`) typed-companion
* 25% — blocks on Mathlib rpow infrastructure
* 5% — phantom on a sub-lemma

**Effort prediction wall-clock**: 10 min.

## §1. Strategy

The forward half (`eLpNorm_iSup_lintegral_mul_le_self` in the sister
file) closed sorry-free. This file discharges
`eLpNorm_le_iSup_lintegral_mul_witness` by exhibiting the saturating
witness

  `g_sat x := f x ^ (p - 1) / A ^ (p - 1)` where `A := eLpNorm f p μ`

and showing:

1. **AEMeasurable g_sat μ** — from `AEMeasurable.pow_const` and
   `AEMeasurable.div_const` (both extant in Mathlib).
2. **eLpNorm g_sat (ofReal q) μ ≤ 1** — equality in fact: using
   `(p-1) * q = p` (Hölder identity) we get
   `∫⁻ g_sat^q = (∫⁻ f^p) / A^p = A^p / A^p = 1`,
   so `‖g_sat‖_q = 1^(1/q) = 1`.
3. **∫⁻ f * g_sat = A** — using `f * f^(p-1) = f^p` (via
   `rpow_add_of_nonneg` since `0 ≤ 1` and `0 ≤ p - 1`),
   `∫⁻ f * g_sat = (∫⁻ f^p) / A^(p-1) = A^p / A^(p-1) = A`.
4. **Combine**: `A = ∫⁻ f * g_sat ≤ ⨆ g, ∫⁻ f * g.val`.

Edge cases `p = 1` and `p = ∞` are NOT discharged in this file
(would require `indicator` / `essSup` separate witnesses). The witness
Prop in the sister file already restricts to the
`0 < ‖f‖_p < ∞`, `(p, q)` finite-Hölder-conjugate regime.

## §2. PATTERN-007 inverted-for-Mathlib audit

Strip "MLG", "iSup", "SQ3":

> "If `1 < p < ∞`, the L^p norm of a function is attained against a
> unit-ball L^q test function via the saturating witness
> `|f|^(p-1) sgn(f) / ‖f‖_p^(p-1)`."

Survives strip — substrate-independent Banach-space duality fact
(Brezis Theorem 4.11 / Folland Theorem 6.14). **PASS.**

## §3. LEG 1 / 2 / 3 audit

* **LEG 1 (functional analysis expert)**: "this is the textbook
  Hölder-saturating witness; the only twist is doing it for
  `ℝ≥0∞`-valued (no sign) so the witness is purely positive."
* **LEG 2 (vocabulary strip)**: "norm equals pairing against
  saturating dual" — substrate-independent.
* **LEG 3 (domain-blind reader)**: any first-year functional-analysis
  student reproduces this on the spot.

All three legs PASS.

## §4. Sub-lemma sorry-count

| Sub-lemma                                           | Form    | Sorries |
|-----------------------------------------------------|---------|---------|
| `g_sat_aemeasurable`                                | lemma   | 0       |
| `lintegral_g_sat_rpow_eq_one`                       | lemma   | 0       |
| `eLpNorm_g_sat_eq_one`                              | lemma   | 0       |
| `lintegral_f_mul_g_sat_eq_eLpNorm`                  | lemma   | 0       |
| `eLpNorm_le_iSup_lintegral_mul_witness_proof`       | theorem | 0       |

**Total `sorry`: 0. New axioms: 0.**

-/

set_option relaxedAutoImplicit true

namespace ZtareProofs.SQ3.MLGiSupDualityReverse

open MeasureTheory Filter Topology ENNReal
open ZtareProofs.SQ3.MLGiSupDuality

noncomputable section

variable {α : Type*} [MeasurableSpace α]

/-! ## §1. The saturating witness construction

For `f : α → ℝ≥0∞`, define
`g_sat x := f x ^ (p - 1) / A ^ (p - 1)` where `A = eLpNorm f p μ`. -/

/-- The saturating Hölder witness. -/
private def g_sat (f : α → ℝ≥0∞) (A : ℝ≥0∞) (p : ℝ) (x : α) : ℝ≥0∞ :=
  f x ^ (p - 1) / A ^ (p - 1)

/-! ## §2. AEMeasurability of the saturating witness -/

private lemma g_sat_aemeasurable
    {μ : Measure α} {f : α → ℝ≥0∞} {A : ℝ≥0∞} {p : ℝ}
    (hf : AEMeasurable f μ) :
    AEMeasurable (g_sat f A p) μ := by
  -- `g_sat f A p x = f x ^ (p-1) / A^(p-1)`, division by a constant.
  have h1 : AEMeasurable (fun x => f x ^ (p - 1)) μ :=
    hf.pow_const (p - 1)
  exact h1.div_const _

/-! ## §3. The pointwise rpow algebra at the heart of the witness

Two key identities used below:

* `(p - 1) * q = p` (`hpq.sub_one_mul_conj`)
* `1 + (p - 1) = p`   (trivial)

Combined with `ENNReal.rpow_mul`, `ENNReal.rpow_add_of_nonneg`, and
`ENNReal.div_rpow_of_nonneg`, the algebra collapses cleanly. -/

set_option linter.unusedSectionVars false in
/-- Pointwise: `g_sat^q = f^p / A^p` (using `(p-1)*q = p`). -/
private lemma g_sat_rpow_eq
    {f : α → ℝ≥0∞} {A : ℝ≥0∞} {p q : ℝ}
    (hpq : p.HolderConjugate q) (x : α) :
    (g_sat f A p x) ^ q = f x ^ p / A ^ p := by
  have hp_sub_one_nn : (0 : ℝ) ≤ p - 1 := hpq.sub_one_pos.le
  have hq_nn : (0 : ℝ) ≤ q := hpq.symm.nonneg
  have h_pq : (p - 1) * q = p := hpq.sub_one_mul_conj
  unfold g_sat
  rw [ENNReal.div_rpow_of_nonneg _ _ hq_nn,
      ← ENNReal.rpow_mul, ← ENNReal.rpow_mul, h_pq]

/-! ## §4. ∫⁻ g_sat^q = 1 -/

private lemma lintegral_g_sat_rpow_eq_one
    {μ : Measure α}
    {p q : ℝ} (hpq : p.HolderConjugate q)
    {f : α → ℝ≥0∞} (hf : AEMeasurable f μ)
    (hf_pos : 0 < eLpNorm f (ENNReal.ofReal p) μ)
    (hf_lt_top : eLpNorm f (ENNReal.ofReal p) μ < ∞) :
    ∫⁻ x, (g_sat f (eLpNorm f (ENNReal.ofReal p) μ) p x) ^ q ∂μ = 1 := by
  set A : ℝ≥0∞ := eLpNorm f (ENNReal.ofReal p) μ with hA_def
  have hp_pos : (0 : ℝ) < p := hpq.pos
  have hp_ne_zero : ENNReal.ofReal p ≠ 0 := by
    rw [Ne, ENNReal.ofReal_eq_zero]; exact not_le.mpr hp_pos
  have hp_ne_top : ENNReal.ofReal p ≠ ∞ := ENNReal.ofReal_ne_top
  have hp_toReal : (ENNReal.ofReal p).toReal = p :=
    ENNReal.toReal_ofReal hp_pos.le
  -- Pointwise rewrite.
  have hpw : ∀ x, (g_sat f A p x) ^ q = f x ^ p / A ^ p := fun x =>
    g_sat_rpow_eq (f := f) (A := A) hpq x
  -- Integrate using lintegral_const_mul'-style pulled-out constant.
  have hA_ne_zero : A ≠ 0 := hf_pos.ne'
  have hA_ne_top : A ≠ ∞ := hf_lt_top.ne
  have hA_pow_ne_zero : A ^ p ≠ 0 :=
    (ENNReal.rpow_pos_of_nonneg hf_pos hp_pos.le).ne'
  have hA_pow_ne_top : A ^ p ≠ ∞ :=
    ENNReal.rpow_ne_top_of_nonneg hp_pos.le hA_ne_top
  -- ∫⁻ g_sat^q = ∫⁻ f^p / A^p = (∫⁻ f^p) * (A^p)⁻¹ = A^p * (A^p)⁻¹ = 1.
  -- ∫⁻ f^p = A^p, using eLpNorm_eq_lintegral_rpow_enorm_toReal (and ‖·‖ₑ = id on ℝ≥0∞).
  have h_int_fp : ∫⁻ x, f x ^ p ∂μ = A ^ p := by
    have hAp : A = (∫⁻ x, f x ^ p ∂μ) ^ (1 / p) := by
      rw [hA_def, eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top, hp_toReal]
      simp_rw [enorm_eq_self]
    have h1 : A ^ p = ((∫⁻ x, f x ^ p ∂μ) ^ (1 / p)) ^ p := by rw [hAp]
    rw [h1, ← ENNReal.rpow_mul, one_div, inv_mul_cancel₀ hp_pos.ne', ENNReal.rpow_one]
  calc ∫⁻ x, (g_sat f A p x) ^ q ∂μ
      = ∫⁻ x, f x ^ p / A ^ p ∂μ := by
        refine lintegral_congr_ae ?_
        exact Filter.Eventually.of_forall hpw
    _ = ∫⁻ x, (A ^ p)⁻¹ * f x ^ p ∂μ := by
        simp_rw [div_eq_mul_inv, mul_comm]
    _ = (A ^ p)⁻¹ * ∫⁻ x, f x ^ p ∂μ := by
        rw [lintegral_const_mul'' _ (hf.pow_const p)]
    _ = (A ^ p)⁻¹ * A ^ p := by rw [h_int_fp]
    _ = 1 := ENNReal.inv_mul_cancel hA_pow_ne_zero hA_pow_ne_top

/-! ## §5. eLpNorm g_sat (ofReal q) μ = 1 -/

private lemma eLpNorm_g_sat_eq_one
    {μ : Measure α}
    {p q : ℝ} (hpq : p.HolderConjugate q)
    {f : α → ℝ≥0∞} (hf : AEMeasurable f μ)
    (hf_pos : 0 < eLpNorm f (ENNReal.ofReal p) μ)
    (hf_lt_top : eLpNorm f (ENNReal.ofReal p) μ < ∞) :
    eLpNorm (g_sat f (eLpNorm f (ENNReal.ofReal p) μ) p) (ENNReal.ofReal q) μ = 1 := by
  have hq_pos : (0 : ℝ) < q := hpq.symm.pos
  have hq_ne_zero : ENNReal.ofReal q ≠ 0 := by
    rw [Ne, ENNReal.ofReal_eq_zero]; exact not_le.mpr hq_pos
  have hq_ne_top : ENNReal.ofReal q ≠ ∞ := ENNReal.ofReal_ne_top
  have hq_toReal : (ENNReal.ofReal q).toReal = q :=
    ENNReal.toReal_ofReal hq_pos.le
  rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hq_ne_zero hq_ne_top, hq_toReal]
  -- For ℝ≥0∞-valued g, ‖g x‖ₑ = g x.
  have hint : ∫⁻ x, ‖g_sat f (eLpNorm f (ENNReal.ofReal p) μ) p x‖ₑ ^ q ∂μ = 1 := by
    simp_rw [enorm_eq_self]
    exact lintegral_g_sat_rpow_eq_one hpq hf hf_pos hf_lt_top
  rw [hint, ENNReal.one_rpow]

/-! ## §6. ∫⁻ f * g_sat = eLpNorm f p μ -/

private lemma lintegral_f_mul_g_sat_eq_eLpNorm
    {μ : Measure α}
    {p q : ℝ} (hpq : p.HolderConjugate q)
    {f : α → ℝ≥0∞} (hf : AEMeasurable f μ)
    (hf_pos : 0 < eLpNorm f (ENNReal.ofReal p) μ)
    (hf_lt_top : eLpNorm f (ENNReal.ofReal p) μ < ∞) :
    ∫⁻ x, f x * (g_sat f (eLpNorm f (ENNReal.ofReal p) μ) p x) ∂μ
      = eLpNorm f (ENNReal.ofReal p) μ := by
  set A : ℝ≥0∞ := eLpNorm f (ENNReal.ofReal p) μ with hA_def
  have hp_pos : (0 : ℝ) < p := hpq.pos
  have hp_ne_zero : ENNReal.ofReal p ≠ 0 := by
    rw [Ne, ENNReal.ofReal_eq_zero]; exact not_le.mpr hp_pos
  have hp_ne_top : ENNReal.ofReal p ≠ ∞ := ENNReal.ofReal_ne_top
  have hp_toReal : (ENNReal.ofReal p).toReal = p :=
    ENNReal.toReal_ofReal hp_pos.le
  have h_sub_one_nn : (0 : ℝ) ≤ p - 1 := hpq.sub_one_pos.le
  have hA_ne_zero : A ≠ 0 := hf_pos.ne'
  have hA_ne_top : A ≠ ∞ := hf_lt_top.ne
  have hA_sub_pow_ne_zero : A ^ (p - 1) ≠ 0 :=
    (ENNReal.rpow_pos_of_nonneg hf_pos h_sub_one_nn).ne'
  have hA_sub_pow_ne_top : A ^ (p - 1) ≠ ∞ :=
    ENNReal.rpow_ne_top_of_nonneg h_sub_one_nn hA_ne_top
  -- Pointwise: f x * g_sat = f^1 * f^(p-1) / A^(p-1) = f^p / A^(p-1).
  have hpw : ∀ x, f x * g_sat f A p x = f x ^ p / A ^ (p - 1) := by
    intro x
    unfold g_sat
    rw [← mul_div_assoc]
    congr 1
    -- f x * f x ^ (p-1) = f x ^ p; we go in reverse: rewrite f x ^ p as f x ^ (1 + (p-1)).
    have hpsum : (p : ℝ) = 1 + (p - 1) := by ring
    conv_rhs => rw [hpsum,
      ENNReal.rpow_add_of_nonneg _ _ (by norm_num : (0:ℝ) ≤ 1) h_sub_one_nn,
      ENNReal.rpow_one]
  -- ∫⁻ f^p = A^p (using ‖·‖ₑ = id on ℝ≥0∞).
  have h_int_fp : ∫⁻ x, f x ^ p ∂μ = A ^ p := by
    have hAp : A = (∫⁻ x, f x ^ p ∂μ) ^ (1 / p) := by
      rw [hA_def, eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top, hp_toReal]
      simp_rw [enorm_eq_self]
    have h1 : A ^ p = ((∫⁻ x, f x ^ p ∂μ) ^ (1 / p)) ^ p := by rw [hAp]
    rw [h1, ← ENNReal.rpow_mul, one_div, inv_mul_cancel₀ hp_pos.ne', ENNReal.rpow_one]
  calc ∫⁻ x, f x * g_sat f A p x ∂μ
      = ∫⁻ x, f x ^ p / A ^ (p - 1) ∂μ := by
        refine lintegral_congr_ae ?_
        exact Filter.Eventually.of_forall hpw
    _ = ∫⁻ x, (A ^ (p - 1))⁻¹ * f x ^ p ∂μ := by
        simp_rw [div_eq_mul_inv, mul_comm]
    _ = (A ^ (p - 1))⁻¹ * ∫⁻ x, f x ^ p ∂μ := by
        rw [lintegral_const_mul'' _ (hf.pow_const p)]
    _ = (A ^ (p - 1))⁻¹ * A ^ p := by rw [h_int_fp]
    _ = A := by
        -- A^p = A^(p-1) * A, so (A^(p-1))⁻¹ * A^p = A.
        have h_split : A ^ p = A ^ (p - 1) * A := by
          have hpsum : (p : ℝ) = (p - 1) + 1 := by ring
          calc A ^ p
              = A ^ ((p - 1) + 1) := by rw [← hpsum]
            _ = A ^ (p - 1) * A ^ (1 : ℝ) :=
                ENNReal.rpow_add_of_nonneg _ _ h_sub_one_nn (by norm_num : (0:ℝ) ≤ 1)
            _ = A ^ (p - 1) * A := by rw [ENNReal.rpow_one]
        rw [h_split, ← mul_assoc,
            ENNReal.inv_mul_cancel hA_sub_pow_ne_zero hA_sub_pow_ne_top, one_mul]

/-! ## §7. The witness inequality

Putting it all together: `‖f‖_p ≤ ⨆ g, ∫⁻ f · g.val`. -/

/-- **REVERSE direction (closed)**: the saturating-witness theorem.
For finite Hölder-conjugate `(p, q)` and `f` with
`0 < eLpNorm f p μ < ∞`, the sup of `∫⁻ f · g` over the L^q unit ball
is at least `eLpNorm f p μ`. -/
theorem eLpNorm_le_iSup_lintegral_mul_witness_proof
    {μ : Measure α}
    {p q : ℝ} (hpq : p.HolderConjugate q)
    {f : α → ℝ≥0∞} (hf : AEMeasurable f μ)
    (hf_pos : 0 < eLpNorm f (ENNReal.ofReal p) μ)
    (hf_lt_top : eLpNorm f (ENNReal.ofReal p) μ < ∞) :
    eLpNorm f (ENNReal.ofReal p) μ
      ≤ ⨆ g : { g : α → ℝ≥0∞ //
                AEMeasurable g μ ∧
                eLpNorm g (ENNReal.ofReal q) μ ≤ 1 },
          ∫⁻ x, f x * (g.val x) ∂μ := by
  set A : ℝ≥0∞ := eLpNorm f (ENNReal.ofReal p) μ with hA_def
  -- The witness lives in the unit ball.
  have h_meas : AEMeasurable (g_sat f A p) μ := g_sat_aemeasurable hf
  have h_norm : eLpNorm (g_sat f A p) (ENNReal.ofReal q) μ ≤ 1 := by
    rw [eLpNorm_g_sat_eq_one hpq hf hf_pos hf_lt_top]
  have h_pair : ∫⁻ x, f x * g_sat f A p x ∂μ = A :=
    lintegral_f_mul_g_sat_eq_eLpNorm hpq hf hf_pos hf_lt_top
  -- Reduce the sup to the witness.
  refine h_pair.symm.le.trans ?_
  exact le_iSup
    (f := fun g : { g : α → ℝ≥0∞ //
                    AEMeasurable g μ ∧
                    eLpNorm g (ENNReal.ofReal q) μ ≤ 1 } =>
            ∫⁻ x, f x * (g.val x) ∂μ)
    ⟨g_sat f A p, h_meas, h_norm⟩

/-! ## §8. Discharge of the typed-companion `Prop` from the sister file -/

/-- The reverse-half typed companion, fully discharged. -/
theorem eLpNorm_le_iSup_lintegral_mul_witness_holds
    (μ : Measure α) (p : ℝ) :
    eLpNorm_le_iSup_lintegral_mul_witness (α := α) μ p := by
  intro q hpq f hf hf_pos hf_lt_top
  exact eLpNorm_le_iSup_lintegral_mul_witness_proof hpq hf hf_pos hf_lt_top

end

end ZtareProofs.SQ3.MLGiSupDualityReverse
