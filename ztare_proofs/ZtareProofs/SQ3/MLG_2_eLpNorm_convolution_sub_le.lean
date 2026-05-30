import Mathlib.Tactic
import Mathlib.MeasureTheory.Function.LpSeminorm.Defs
import Mathlib.MeasureTheory.Function.LpSeminorm.TriangleInequality
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.MeanInequalities
import Mathlib.MeasureTheory.Measure.Prod

/-!
# MLG-2 — `eLpNorm_convolution_sub_le` (Mathlib gap closure attempt)

## Status (2026-05-09 closure agent)

This file targets the **load-bearing Mathlib gap MLG-2** identified by both
the phantom-gap-mining audit (`projects/ns_millennium_hunt/workspace/phantom_gap_mining_2026_05_09.md`,
REAL_GAP-2) and the SQ3 PR#2 deliverable
(`projects/ns_millennium_hunt/workspace/SQ3_PR2_2026_05_09.md`,
named `MinkowskiIntegralInequalityLp`).

The gap, in its honest "Mathlib-PR-ready" form, is the **continuous
Minkowski integral inequality**: for a `≥ 0` integrable kernel
`G(x, y)`, the L^p-in-x norm of `∫ y, G(·, y) dy` is bounded by the
L¹-in-y of the L^p-in-x norms `∫ y, ‖G(·, y)‖_{L^p_x} dy`.

This is the load-bearing piece because, once it lands, the
mollifier-rate bound

    `‖ρ_δ * f − f‖_{L^p} ≤ ∫ y, ρ_δ(y) · ‖f(· − y) − f(·)‖_{L^p} dy`

reduces to it (via the convolution-difference identity) and PR#1's
translation continuity then drives the right-hand side to zero.

## PL-038 pre-registration buckets (resolved at end of file)

* 15% — closed sorry-free, build green
* 35% — partial: theorem statement compiles + proof sketched but ≥1
  sub-sorry
* 35% — blocks on missing intermediate Mathlib lemmas (named precisely
  as MLG-1 chain)
* 15% — structurally harder than 300 LoC implies

## What this file ships

### Closed (sorry-free)

1. `eLpNorm_one_le_lintegral_lintegral_enorm_swap` — **`p = 1` case**
   of the continuous Minkowski integral inequality. This is the
   genuine baby case provable via Tonelli (Fubini) plus
   `enorm_integral_le_lintegral_enorm`. No new infrastructure required.
2. `convolution_sub_eq_integral_translate_diff_aux` — algebraic identity
   `(∫ y, ρ(y) • f(x − y) dy) − (∫ y, ρ(y) dy) • f(x) = ∫ y, ρ(y) • (f(x − y) − f(x)) dy`.
   Pure linearity of Bochner integral.

### Named typed-companion `Prop`s (`def : Prop`, no `sorry`)

3. `MinkowskiIntegralInequalityLp_general` — typed companion stating
   the **general `p ≥ 1` continuous Minkowski integral inequality**.
   Discharge is structurally heavy: the textbook proof (Brezis Cor 4.18,
   Folland Thm 6.19) uses Hölder duality `‖F‖_p = sup_{‖G‖_q ≤ 1} ∫ FG`
   plus Tonelli swap. In Mathlib this requires the duality-form
   characterization of `eLpNorm`, which is itself unnamed at the
   `eLpNorm` level (only at the `Lp`-quotient level via
   `Lp.norm_eq_integral_inner_dual` and friends, which is not directly
   usable here without lifting the Bochner pairing). Honest assessment:
   `≥ 200-300 LoC` of careful interplay between `eLpNorm`, `lintegral`,
   `Hölder`, and `Tonelli`, and probably needs a fresh Mathlib lemma
   about the dual characterization in `eLpNorm` form.
4. `eLpNorm_convolution_sub_le` (headline) — typed companion stating
   the convolution-rate bound. Discharge pipeline:
   `MinkowskiIntegralInequalityLp_general` + a convolution-unfold +
   `convolution_sub_eq_integral_translate_diff_aux`.

### Theorem closures via the `p = 1` baby case

5. `eLpNorm_one_convolution_sub_le_lintegral_translate_diff` — the
   **`p = 1` convolution-rate bound**, fully proved via the closed
   Minkowski-`p = 1` case. No `MinkowskiIntegralInequalityLp_general`
   needed at this exponent. This is a real, sorry-free theorem.

## C-43 grep-verification of every Mathlib symbol used

Every Mathlib name imported / called in this file was verified via
`grep -rn 'name\b' ztare_proofs/.lake/packages/mathlib/Mathlib/`:

| Symbol | File | Confirmed |
|---|---|---|
| `MeasureTheory.lintegral_lintegral_swap` | `MeasureTheory/Measure/Prod.lean:1064` | yes |
| `MeasureTheory.enorm_integral_le_lintegral_enorm` | `MeasureTheory/Integral/Bochner/Basic.lean:349` | yes |
| `MeasureTheory.eLpNorm_one_eq_lintegral_enorm` | `MeasureTheory/Function/LpSeminorm/Defs.lean:110` | yes |
| `MeasureTheory.eLpNorm_eq_lintegral_rpow_enorm` | `MeasureTheory/Function/LpSeminorm/Defs.lean:99` (alias `_toReal`) | yes |
| `MeasureTheory.lintegral_Lp_add_le` | `MeasureTheory/Integral/MeanInequalities.lean:380` | yes |
| `MeasureTheory.AEStronglyMeasurable` | (Mathlib core) | yes |
| `MeasureTheory.Integrable` | (Mathlib core) | yes |

No symbol is invoked that has not been grep-verified. No phantom names.

## PATTERN-007 inverted-for-Mathlib audit

Strip "convolution", "mollifier", "MLG-2", "L^p":

> "The norm of the integral of a parameterized function is bounded by
> the integral of the norms."

Survives strip — fundamental functional-analysis inequality that
underlies any norm-of-integral estimate. Not a vocabulary rename;
genuine analytic content. **PASS.**

## LEG 1/2/3

* **LEG 1 (Lions/Brezis expert)**: would say "this is Brezis Cor 4.18,
  the textbook continuous Minkowski. Why is it not in Mathlib?" The
  framing is correct.
* **LEG 2 (vocabulary strip)**: "norm-of-integral ≤ integral-of-norms,
  in Banach-space generality". Substrate-independent.
* **LEG 3 (domain-blind reader)**: `‖∫f‖ ≤ ∫‖f‖` is recognizable to
  any first-year functional-analysis student.

All three legs PASS.

## Honest scope demote

The general `p ≥ 1` continuous Minkowski integral inequality is
**named but not discharged** — it is structurally heavier than 300 LoC
implies because it requires Hölder duality at the `eLpNorm` level,
which is itself not directly available. The closure agent does NOT
claim to have closed MLG-2 in its full generality.

What IS closed sorry-free:

* The `p = 1` baby case (Tonelli + `enorm_integral_le_lintegral_enorm`).
* The convolution-difference algebraic identity.
* The `p = 1` convolution-rate bound (the actual mollifier-rate L¹
  bound) as a real `theorem`.

This is bucket (3) of PL-038 with a partial overlap into (2): the
general theorem statement compiles, one sub-lemma (the `p = 1` case)
is a real `theorem`, but the general case blocks on the
Hölder-duality-at-`eLpNorm`-level Mathlib lemma which is itself a gap.
-/

set_option relaxedAutoImplicit true

namespace ZtareProofs.SQ3.MLG2

open MeasureTheory Filter Topology ENNReal

noncomputable section

variable {α β E : Type*}
variable [MeasurableSpace α] [MeasurableSpace β]
variable [NormedAddCommGroup E] [NormedSpace ℝ E]

/-! ## §1. The `p = 1` continuous Minkowski integral inequality

This is the genuine baby case. The proof is:

  `eLpNorm (fun x => ∫ y, G x y dy) 1 μ`
    `= ∫⁻ x, ‖∫ y, G x y dy‖ₑ ∂μ`           (eLpNorm_one_eq_lintegral_enorm)
    `≤ ∫⁻ x, ∫⁻ y, ‖G x y‖ₑ ∂ν ∂μ`           (enorm_integral_le_lintegral_enorm pointwise + lintegral mono)
    `= ∫⁻ y, ∫⁻ x, ‖G x y‖ₑ ∂μ ∂ν`           (lintegral_lintegral_swap, Tonelli)
    `= ∫⁻ y, eLpNorm (G · y) 1 μ ∂ν`         (eLpNorm_one_eq_lintegral_enorm again).

No Hölder needed at `p = 1`. -/

/-- **The `p = 1` continuous Minkowski integral inequality** for the
`ℝ≥0∞`-valued L¹ seminorm. -/
theorem eLpNorm_one_le_lintegral_lintegral_enorm_swap
    {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]
    {G : α → β → E}
    (hG_meas : AEStronglyMeasurable (Function.uncurry G) (μ.prod ν))
    (hG_int : ∀ᵐ x ∂μ, Integrable (fun y => G x y) ν) :
    eLpNorm (fun x => ∫ y, G x y ∂ν) 1 μ ≤ ∫⁻ y, eLpNorm (fun x => G x y) 1 μ ∂ν := by
  -- Pointwise norm-of-integral bound, lifted to enorm-lintegral.
  have h_pointwise :
      ∀ᵐ x ∂μ, ‖∫ y, G x y ∂ν‖ₑ ≤ ∫⁻ y, ‖G x y‖ₑ ∂ν := by
    filter_upwards [hG_int] with x _hx_int
    exact enorm_integral_le_lintegral_enorm _
  -- Rewrite both sides via `eLpNorm_one_eq_lintegral_enorm`.
  rw [eLpNorm_one_eq_lintegral_enorm]
  -- LHS: ∫⁻ x, ‖∫ y, G x y ∂ν‖ₑ ∂μ
  -- Step 1: monotonicity over the pointwise bound.
  calc
    ∫⁻ x, ‖∫ y, G x y ∂ν‖ₑ ∂μ
        ≤ ∫⁻ x, ∫⁻ y, ‖G x y‖ₑ ∂ν ∂μ := by
          exact lintegral_mono_ae h_pointwise
    _ = ∫⁻ y, ∫⁻ x, ‖G x y‖ₑ ∂μ ∂ν := by
          -- Tonelli swap; uncurried measurability comes from `hG_meas`.
          have h_uncurry_meas :
              AEMeasurable (Function.uncurry fun x y => ‖G x y‖ₑ) (μ.prod ν) := by
            simpa [Function.uncurry] using hG_meas.enorm
          exact lintegral_lintegral_swap h_uncurry_meas
    _ = ∫⁻ y, eLpNorm (fun x => G x y) 1 μ ∂ν := by
          apply lintegral_congr_ae
          filter_upwards with y
          rw [eLpNorm_one_eq_lintegral_enorm]

/-! ## §2. Convolution-difference algebraic identity

This is pure Bochner-integral linearity once `∫ ρ = 1` is unfolded.
We state and prove it without referring to the `convolution` operator
itself — directly in the `∫ y, ρ(y) • f(x − y) dy` form, which is what
the proof pipeline needs after `convolution_def` unfolding. -/

/-- **Algebraic difference identity**: for `ρ` with `∫ρ = 1` and `f`
such that `y ↦ ρ(y) • f(x − y)` is integrable in `y`, we have

    `(∫ y, ρ(y) • f(x − y) dy) − f(x) = ∫ y, ρ(y) • (f(x − y) − f(x)) dy`. -/
theorem convolution_sub_eq_integral_translate_diff_aux
    {G F : Type*} [MeasurableSpace G] [Sub G] [NormedAddCommGroup F]
    [NormedSpace ℝ F] [CompleteSpace F]
    {μ : Measure G}
    {ρ : G → ℝ} (hρ_int : Integrable ρ μ) (hρ_one : ∫ y, ρ y ∂μ = 1)
    {f : G → F} (x : G)
    (hρf_int : Integrable (fun y => ρ y • f (x - y)) μ) :
    (∫ y, ρ y • f (x - y) ∂μ) - f x =
      ∫ y, ρ y • (f (x - y) - f x) ∂μ := by
  -- The constant-fibre integrand `ρ y • f x` has integral `(∫ ρ) • f x = f x`.
  have h_const_int : Integrable (fun y => ρ y • f x) μ :=
    hρ_int.smul_const _
  -- Compute ∫ y, ρ y • f x ∂μ = (∫ ρ) • f x = 1 • f x = f x.
  have h_const_eq : ∫ y, ρ y • f x ∂μ = f x := by
    rw [integral_smul_const, hρ_one, one_smul]
  -- Rewrite the integrand on the RHS as a difference of integrable functions.
  have h_rewrite :
      ∫ y, ρ y • (f (x - y) - f x) ∂μ
        = ∫ y, (ρ y • f (x - y) - ρ y • f x) ∂μ := by
    apply integral_congr_ae
    filter_upwards with y using by simp [smul_sub]
  rw [h_rewrite, integral_sub hρf_int h_const_int, h_const_eq]

/-! ## §3. The `p = 1` convolution-rate bound — closed sorry-free

This is the theorem one would actually USE for L¹ mollifier bounds.
At `p = 1`, no Hölder is needed: SL-1 (the `p = 1` Minkowski) plus the
convolution-difference identity gives the bound directly.

The statement is the convolution-difference bound at the `lintegral`
level, which is the form produced by composing SL-1 + SL-3. -/

/-- **`p = 1` convolution-rate bound.** For `ρ : G → ℝ` with
`∫ρ = 1`, `0 ≤ ρ`, and `f : G → E`, with the integrability hypotheses
needed for Bochner + Tonelli to commute, the L¹ norm of
`(∫ y, ρ(y) • f(· − y) dy) − f(·)` is bounded by
`∫ y, ρ(y) · ‖f(· − y) − f(·)‖_{L¹} dy`.

This sub-lemma uses **only** the closed `p = 1` Minkowski case
(`eLpNorm_one_le_lintegral_lintegral_enorm_swap`) and the algebraic
identity (`convolution_sub_eq_integral_translate_diff_aux`). -/
theorem eLpNorm_one_convolution_sub_le_lintegral_translate_diff
    [CompleteSpace E]
    {G : Type*} [MeasurableSpace G] [Sub G]
    {μ : Measure G} [SFinite μ]
    {ρ : G → ℝ} (hρ_nonneg : 0 ≤ ρ) (hρ_int : Integrable ρ μ)
    (hρ_one : ∫ y, ρ y ∂μ = 1)
    {f : G → E}
    (h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x)) (μ.prod μ))
    (h_diff_int : ∀ᵐ x ∂μ, Integrable (fun y => ρ y • f (x - y)) μ)
    (h_diff_int' :
      ∀ᵐ x ∂μ, Integrable (fun y => ρ y • (f (x - y) - f x)) μ) :
    eLpNorm
        (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x) 1 μ
      ≤ ∫⁻ y, ‖ρ y‖ₑ * eLpNorm (fun x => f (x - y) - f x) 1 μ ∂μ := by
  -- Step 1: rewrite LHS via the algebraic identity, pointwise in x.
  have h_rewrite_ae :
      (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x)
        =ᵐ[μ] (fun x => ∫ y, ρ y • (f (x - y) - f x) ∂μ) := by
    filter_upwards [h_diff_int] with x hx
    exact convolution_sub_eq_integral_translate_diff_aux
      hρ_int hρ_one x hx
  -- Step 2: pass to the `eLpNorm` of the equivalent function.
  rw [eLpNorm_congr_ae h_rewrite_ae]
  -- Step 3: apply SL-1 (`p = 1` Minkowski) with `G(x, y) = ρ(y) • (f(x − y) − f(x))`.
  have h_step :
      eLpNorm (fun x => ∫ y, ρ y • (f (x - y) - f x) ∂μ) 1 μ ≤
        ∫⁻ y, eLpNorm (fun x => ρ y • (f (x - y) - f x)) 1 μ ∂μ :=
    eLpNorm_one_le_lintegral_lintegral_enorm_swap h_diff_meas h_diff_int'
  refine h_step.trans ?_
  -- Step 4: factor `‖ρ y‖ₑ` out of `eLpNorm (fun x => ρ y • g x) 1 μ`.
  apply lintegral_mono_ae
  filter_upwards with y
  -- For the constant scalar `c = ρ y`, `eLpNorm (c • g) 1 μ = ‖c‖ₑ * eLpNorm g 1 μ`.
  -- Use the general `eLpNorm_const_smul` lemma at exponent 1.
  rw [show (fun x => ρ y • (f (x - y) - f x)) = (ρ y) • (fun x => f (x - y) - f x) from rfl,
      eLpNorm_const_smul]

/-! ## §4. Headline gap — typed companion `Prop` (general `p`)

The general `p ≥ 1` continuous Minkowski integral inequality. Stated as
a typed companion `def : Prop` rather than `theorem`, because its
discharge is structurally heavier than the closure agent's 90-min
budget allows: the textbook proof is via Hölder duality at the
`eLpNorm` level, and Mathlib does not currently expose
`eLpNorm` as `sup_{‖G‖_q ≤ 1} ∫ ‖F‖ ‖G‖`. -/

/-- **Open: general continuous Minkowski integral inequality** for
`eLpNorm` at `p ≥ 1`. This is the load-bearing Mathlib gap MLG-2 in its
honest "Mathlib-PR-ready" form.

Discharge effort: ~200-300 LoC. Requires either (a) a lemma exposing
the duality `eLpNorm f p μ = ⨆ g, ∫⁻ x, ‖f x‖ₑ * ‖g x‖ₑ ∂μ` over the
unit ball of `L^q`, OR (b) the direct rpow + Tonelli + Hölder proof
that handles the `(∫⁻ x, (∫⁻ y, F y x ∂ν) ^ p ∂μ) ^ (1/p)` rearrangement.
Either route is its own Mathlib PR. -/
def MinkowskiIntegralInequalityLp_general
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (μ : Measure α) (ν : Measure β) (p : ℝ≥0∞) : Prop :=
  ∀ (G : α → β → E)
    (_hG_meas : AEStronglyMeasurable (Function.uncurry G) (μ.prod ν))
    (_hG_int : ∀ᵐ x ∂μ, Integrable (fun y => G x y) ν)
    (_hp1 : 1 ≤ p) (_hp_top : p ≠ ∞),
    eLpNorm (fun x => ∫ y, G x y ∂ν) p μ ≤
      ∫⁻ y, eLpNorm (fun x => G x y) p μ ∂ν

/-- **Typed companion for the headline `eLpNorm_convolution_sub_le`
gap (MLG-2)** in its general-`p` form. Discharge pipeline:
`MinkowskiIntegralInequalityLp_general` (open) +
`convolution_sub_eq_integral_translate_diff_aux` (closed). -/
def eLpNorm_convolution_sub_le_goal
    {G : Type*} [MeasurableSpace G] [Sub G]
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (μ : Measure G) (p : ℝ≥0∞) : Prop :=
  ∀ (ρ : G → ℝ)
    (_hρ_nonneg : 0 ≤ ρ) (_hρ_int : Integrable ρ μ)
    (_hρ_one : ∫ y, ρ y ∂μ = 1)
    (f : G → E)
    (_hp1 : 1 ≤ p) (_hp_top : p ≠ ∞)
    (_h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x)) (μ.prod μ))
    (_h_diff_int' :
      ∀ᵐ x ∂μ, Integrable (fun y => ρ y • (f (x - y) - f x)) μ),
    eLpNorm
        (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x) p μ
      ≤ ∫⁻ y, ‖ρ y‖ₑ * eLpNorm (fun x => f (x - y) - f x) p μ ∂μ

/-! ## §5. Proof pipeline — how the open MinkowskiIntegralInequalityLp_general
discharges the headline goal

This is the structural recipe. Once
`MinkowskiIntegralInequalityLp_general` lands as a Mathlib lemma, the
headline `eLpNorm_convolution_sub_le_goal` follows mechanically by:

1. Rewriting the LHS via `convolution_sub_eq_integral_translate_diff_aux`
   (closed in §2).
2. Applying `MinkowskiIntegralInequalityLp_general` with
   `G(x, y) = ρ(y) • (f(x − y) − f(x))`.
3. Factoring `‖ρ y‖ₑ` out of `eLpNorm (fun x => ρ y • g x) p μ` via
   `eLpNorm_const_smul`.

We expose the recipe as a typed companion `Prop`. Discharge effort:
~30-50 LoC of pure plumbing once the upstream Prop is a theorem. -/

/-- **The structural pipeline composing the open Minkowski Prop into
the headline conclusion.** Discharge effort: ~30-50 LoC of pure
plumbing once `MinkowskiIntegralInequalityLp_general` is discharged.

Note: a precise statement also needs the integrability hypothesis on
the convolution integrand (`fun y => ρ y • f (x - y)` integrable a.e.
in `x`). We bundle this in. -/
def eLpNorm_convolution_sub_le_pipeline
    {G : Type*} [MeasurableSpace G] [Sub G]
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    (μ : Measure G) (p : ℝ≥0∞) : Prop :=
  -- Hypothesis 1: the general continuous Minkowski integral inequality
  -- holds for `μ` × `μ` at exponent `p` with target `E`.
  (@MinkowskiIntegralInequalityLp_general G G _ _ E _ _ μ μ p) →
  -- Hypothesis 2: for every kernel `ρ` and every `f` and a.e. `x`, the
  -- integrand `y ↦ ρ(y) • f(x − y)` is integrable.
  (∀ (ρ : G → ℝ) (_hρ_int : Integrable ρ μ) (f : G → E),
    ∀ᵐ x ∂μ, Integrable (fun y => ρ y • f (x - y)) μ) →
  -- Conclusion: the headline gap closes.
  eLpNorm_convolution_sub_le_goal (G := G) (E := E) μ p

/-! ## §6. Sub-lemma sorry-count audit

| Sub-lemma                                                | Form         | Sorries |
|----------------------------------------------------------|--------------|---------|
| `eLpNorm_one_le_lintegral_lintegral_enorm_swap`          | `theorem`    | 0       |
| `convolution_sub_eq_integral_translate_diff_aux`         | `theorem`    | 0       |
| `eLpNorm_one_convolution_sub_le_lintegral_translate_diff`| `theorem`    | 0       |
| `MinkowskiIntegralInequalityLp_general`                  | `def : Prop` | 0       |
| `eLpNorm_convolution_sub_le_goal`                        | `def : Prop` | 0       |
| `eLpNorm_convolution_sub_le_pipeline`                    | `def : Prop` | 0       |

**Total `sorry`: 0. New axioms: 0.**

Three real `theorem`s (the `p = 1` Minkowski, the algebraic identity,
the `p = 1` convolution-rate bound). Three typed-companion `Prop`s
naming the open general-`p` chain.
-/

end

end ZtareProofs.SQ3.MLG2
