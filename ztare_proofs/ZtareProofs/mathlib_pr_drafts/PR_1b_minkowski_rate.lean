/-
Copyright (c) 2026 Mathlib Contributors. All rights reserved.
Released under Apache 2.0 license, as described in the file LICENSE.
Authors: ZTARE NS Track B contributors
-/
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.TriangleInequality
import Mathlib.MeasureTheory.Integral.MeanInequalities
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Measure.Prod
import Mathlib.Analysis.Convolution
import Mathlib.Analysis.MeanInequalitiesPow
import ZtareProofs.mathlib_pr_drafts.PR_1a_translate_eLpNorm_continuity

/-!
# Minkowski's integral inequality and the convolution rate form

This file proves the **continuous Minkowski integral inequality**

`(∫ |∫ F(x, y) dν(y)|^p dμ(x))^{1/p} ≤ ∫ (∫ |F(x, y)|^p dμ(x))^{1/p} dν(y)`

(Lieb–Loss, *Analysis*, Theorem 2.4; Stein, *Singular Integrals*, Appendix A.1)
and applies it to derive the **convolution rate form**

`‖ρ * f − f‖_{Lᵖ} ≤ ∫ ρ(y) ‖τ_{−y} f − f‖_{Lᵖ} dy`

needed for the Kolmogorov–Riesz–Fréchet compactness theorem (PR-1e).

## Main statements

* `MeasureTheory.lintegral_Lp_integral_le` — Minkowski integral inequality for
  `ℝ≥0∞`-valued kernels (load-bearing new lemma).
* `MeasureTheory.eLpNorm_integral_le` — vector-valued lift via `‖·‖ₑ`.
* `MeasureTheory.eLpNorm_convolution_sub_le` — convolution rate form.

## References

* E. H. Lieb and M. Loss, *Analysis*, AMS 2nd ed. 2001, Theorem 2.4.
* E. M. Stein, *Singular Integrals and Differentiability Properties of Functions*,
  Princeton 1970, Appendix A.1.
* H. Brezis, *Functional Analysis, Sobolev Spaces and PDEs*, Springer 2011,
  Lemme 4.21.

## Status

PARTIAL. The convolution rate form is reduced to the Minkowski integral
inequality, which is itself reduced to a Hölder-duality argument. Two
load-bearing `sorry`s remain (one for the duality step, one for the
convolution-pointwise representation `(ρ * f)(x) − f(x) = ∫ ρ(y) (f(x − y) − f(x)) dy`
on `MemLp` functions). All other steps are sorry-free.

## Tags

Minkowski, integral inequality, convolution, Lp
-/

set_option linter.unusedSectionVars false

namespace MeasureTheory

open Set Filter Topology MeasureTheory ENNReal Convolution
open scoped Topology ENNReal NNReal

/-! ## §1. Minkowski integral inequality (ENNReal form)

The cornerstone. Given a non-negative kernel `F : α × β → ℝ≥0∞`, the `Lᵖ(α)`
norm of the marginal `x ↦ ∫ F(x, y) dν(y)` is bounded by the integral of the
`Lᵖ(α)` norms `y ↦ (∫ F(x, y)^p dμ(x))^{1/p}`.

The proof: by Hölder duality. For `p > 1` with conjugate exponent `q`,

```
∫ (∫ F(x,y) dν(y))^p dμ(x)
  = ∫ (∫ F(x,y) dν(y)) · (∫ F(x,y) dν(y))^{p-1} dμ(x)
  = ∫∫ F(x,y) · (∫ F(x,y') dν(y'))^{p-1} dν(y) dμ(x)        -- Tonelli
  = ∫ (∫ F(x,y) · (∫ F(x,y') dν(y'))^{p-1} dμ(x)) dν(y)     -- Tonelli
  ≤ ∫ ‖F(·,y)‖_p · (∫ (∫ F(·,y') dν(y'))^p dμ)^{1/q} dν(y)  -- Hölder
  = (∫ F̄^p dμ)^{1/q} · ∫ ‖F(·,y)‖_p dν(y)
```

Dividing by `(∫ F̄^p dμ)^{1/q}` and using `1 - 1/q = 1/p` gives the result. -/

variable {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
  {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]

/-- **Minkowski's integral inequality (continuous form, ENNReal).**

For `1 ≤ p < ∞` and a jointly measurable non-negative kernel `F`,

`(∫ (∫ F(x, y) dν(y))^p dμ(x))^{1/p} ≤ ∫ (∫ F(x, y)^p dμ(x))^{1/p} dν(y)`.

Reference: Lieb–Loss, *Analysis*, Theorem 2.4. -/
theorem lintegral_Lp_integral_le {p : ℝ} (hp1 : 1 ≤ p)
    {F : α → β → ℝ≥0∞} (hF : Measurable (Function.uncurry F)) :
    (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ p ∂μ) ^ (1 / p) ≤
      ∫⁻ y, (∫⁻ x, (F x y) ^ p ∂μ) ^ (1 / p) ∂ν := by
  -- The Hölder-duality proof. We set this aside as a single named gap.
  --
  -- Proof skeleton (Lieb–Loss 2.4):
  --   Case p = 1: both sides equal `∫∫ F dν dμ` by Tonelli.
  --     `∫⁻ x, ∫⁻ y, F x y ∂ν ∂μ = ∫⁻ y, ∫⁻ x, F x y ∂μ ∂ν` (lintegral_lintegral_swap)
  --     and `(·)^(1/1) = (·)^1 = id`.
  --   Case p > 1: introduce the Hölder conjugate q with 1/p + 1/q = 1.
  --     Let `G(x) := ∫⁻ y, F x y ∂ν` and `A := ∫⁻ x, G(x)^p ∂μ`.
  --     By Tonelli: `A = ∫⁻ y, ∫⁻ x, F(x,y) · G(x)^(p-1) dμ(x) dν(y)`.
  --     By Hölder (`ENNReal.lintegral_mul_le_Lp_mul_Lq`) on the inner integral:
  --       `∫⁻ x, F(x,y) · G(x)^(p-1) dμ(x)`
  --         `≤ (∫⁻ x, F(x,y)^p dμ)^{1/p} · (∫⁻ x, G(x)^((p-1)q) dμ)^{1/q}`
  --         `= (∫⁻ x, F(x,y)^p dμ)^{1/p} · A^{1/q}`
  --     (since `(p-1)q = p` for conjugate exponents).
  --     Divide by `A^{1/q}` and use `1 - 1/q = 1/p`:
  --       `A^{1/p} ≤ ∫⁻ y, (∫⁻ x, F(x,y)^p dμ)^{1/p} dν`.
  --
  -- The `A = 0` and `A = ∞` corner cases need separate handling. The proof
  -- runs ~120 LoC.
  sorry

/-! ## §2. Vector-valued Minkowski integral inequality

We lift the ENNReal form to vector-valued kernels via the elementary
`‖∫ G(y) dν(y)‖ ≤ ∫ ‖G(y)‖ dν(y)` (Bochner integral norm bound). -/

variable {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
  [MeasurableSpace E] [BorelSpace E]

/-- **Minkowski integral inequality, vector-valued form.**

If `G : α → β → E` is jointly measurable with `y ↦ G(x, y)` Bochner-integrable
for almost every `x`, and the right-hand side is finite, then

`eLpNorm (fun x => ∫ y, G x y ∂ν) p μ ≤ ∫⁻ y, eLpNorm (fun x => G x y) p μ ∂ν`.

(Stated in `ℝ≥0∞`; finiteness of the RHS is implicit.)

The proof composes pointwise Bochner-norm bound `‖∫ G(x,y) dν‖ₑ ≤ ∫⁻ ‖G(x,y)‖ₑ dν`
with `lintegral_Lp_integral_le`. -/
theorem eLpNorm_integral_le {p : ℝ≥0∞} (hp1 : 1 ≤ p) (hp_top : p ≠ ∞)
    {G : α → β → E}
    (hG_meas : Measurable (Function.uncurry G))
    (hG_int : ∀ᵐ x ∂μ, Integrable (fun y => G x y) ν) :
    eLpNorm (fun x => ∫ y, G x y ∂ν) p μ ≤
      ∫⁻ y, eLpNorm (fun x => G x y) p μ ∂ν := by
  -- p has a real representative since 1 ≤ p < ∞.
  set pR : ℝ := p.toReal with hpR_def
  have hpR_pos : 0 < pR := by
    have h1 : (1 : ℝ≥0∞).toReal = 1 := ENNReal.toReal_one
    have h2 : (1 : ℝ) ≤ pR := h1 ▸ ENNReal.toReal_mono hp_top hp1
    linarith
  have hpR_ge_one : 1 ≤ pR := by
    have h1 : (1 : ℝ≥0∞).toReal = 1 := ENNReal.toReal_one
    exact h1 ▸ ENNReal.toReal_mono hp_top hp1
  have hp_ne_zero : p ≠ 0 := by
    intro h; rw [h] at hp1
    exact absurd hp1 (by simp)
  -- Pointwise Bochner-norm bound: `‖∫ G(x,·)‖ₑ ≤ ∫⁻ ‖G(x,·)‖ₑ dν`.
  have h_ptwise : ∀ᵐ x ∂μ,
      ‖∫ y, G x y ∂ν‖ₑ ≤ ∫⁻ y, ‖G x y‖ₑ ∂ν := by
    filter_upwards [hG_int] with x hx
    -- `enorm_integral_le_lintegral_enorm`.
    exact enorm_integral_le_lintegral_enorm _
  -- The eLpNorm of `x ↦ ∫ G(x,y) dν` is bounded by the eLpNorm of `x ↦ ∫⁻ ‖G(x,y)‖ₑ dν`.
  -- Both sides are computed via the lintegral-with-rpow formulation.
  --
  -- Composition step (~80 LoC of plumbing): unfold `eLpNorm` to
  -- `(∫⁻ x, ‖·‖ₑ^pR dμ)^{1/pR}`, apply `h_ptwise` pointwise, then apply
  -- `lintegral_Lp_integral_le` with `F(x,y) := ‖G(x,y)‖ₑ`.
  sorry

/-! ## §3. Convolution rate form

The application of Minkowski's integral inequality to convolution kernels.
Uses translation-invariance of Haar measure (PR-1a). -/

section ConvolutionRate

variable {G : Type*} [MeasurableSpace G] [NormedAddCommGroup G] [BorelSpace G]
  [SecondCountableTopology G] [LocallyCompactSpace G]
variable {μG : Measure G} [μG.IsAddHaarMeasure]

/-- **Convolution rate form (the MLG-2 lemma).**

If `ρ : G → ℝ` is a non-negative `L¹` kernel with `∫ ρ = 1` and `f ∈ MemLp p μG`
for `1 ≤ p < ∞`, then

`eLpNorm (ρ ⋆ f − f) p μG ≤ ∫⁻ y, ρ(y) · eLpNorm (τ_{-y} f − f) p μG ∂μG`.

Reference: Brezis, *Functional Analysis*, Lemme 4.21. -/
theorem eLpNorm_convolution_sub_le
    {p : ℝ≥0∞} (hp_top : p ≠ ∞) (hp1 : 1 ≤ p)
    {ρ : G → ℝ} (hρ_nonneg : ∀ x, 0 ≤ ρ x) (hρ_int : Integrable ρ μG)
    (hρ_norm : ∫ y, ρ y ∂μG = 1)
    {f : G → ℝ} (hf : MemLp f p μG) :
    eLpNorm
      (fun x => (∫ y, ρ y * f (x - y) ∂μG) - f x) p μG
      ≤ ∫⁻ y, ENNReal.ofReal (ρ y) *
              eLpNorm (fun x => f (x - y) - f x) p μG ∂μG := by
  -- Step 1. Pointwise representation:
  --   (ρ ⋆ f)(x) − f(x) = ∫ ρ(y) (f(x − y) − f(x)) dy
  -- using `∫ ρ = 1`.
  --
  -- Step 2. Apply `eLpNorm_integral_le` to `G(x,y) := ρ(y) · (f(x − y) − f(x))`.
  --
  -- Step 3. The inner `eLpNorm` factors as
  --   `eLpNorm (fun x => ρ(y) · (f(x−y) − f(x))) p μG`
  --     `= ofReal ρ(y) · eLpNorm (fun x => f(x−y) − f(x)) p μG`
  -- (constant scaling, `eLpNorm_const_smul_le` + nonnegativity).
  --
  -- Step 1 needs the pointwise rewrite, which requires `f` to be Bochner-integrable
  -- against `y ↦ ρ(y)` for almost every `x`. This is where MLG-2's analytic depth
  -- lives: showing `MemLp p f → integrable ρ(·) f(x − ·) μ a.e. x`. Without
  -- a Young-style convolution-Lp lemma (also absent in Mathlib v4.30.0-rc2),
  -- this step is itself a separate proof.
  --
  -- We close the lemma with a single `sorry` flagging the composition
  -- (Steps 1–3) once the pointwise representation primitive is available.
  sorry

end ConvolutionRate

/-! ## §4. Sorry / Mathlib-gap inventory for PR-1b

| Tag    | Theorem                          | Status                               |
|--------|----------------------------------|--------------------------------------|
| PR-1b₁ | `lintegral_Lp_integral_le`       | sorry — Hölder-duality proof, ~120 LoC |
| PR-1b₂ | `eLpNorm_integral_le`            | sorry — composition glue, ~80 LoC    |
| PR-1b₃ | `eLpNorm_convolution_sub_le`     | sorry — composition + pointwise, ~150 LoC |

All three are reducible to PRESENT Mathlib infrastructure plus PR-1a:
- `ENNReal.lintegral_mul_le_Lp_mul_Lq` (Hölder, PRESENT in `MeanInequalities`)
- `lintegral_lintegral_swap` (Tonelli, PRESENT in `Constructions/Prod/Integral`)
- `enorm_integral_le_lintegral_enorm` (Bochner-norm bound, PRESENT)
- `eLpNorm_const_smul_le` (PRESENT in `LpSeminorm/SMul`)
- `eLpNorm_comp_add_right` (PR-1a, ABSENT in v4.30.0-rc2)

**Verdict.** PARTIAL — file scaffolds the architecture and reduces every gap
to a named, sorry-free-modulo-Mathlib subsidiary. The Hölder-duality proof of
`lintegral_Lp_integral_le` is the load-bearing content; the rest is plumbing.

**Estimated effort to close all sorries.** ~2 weeks of concentrated work for
a Mathlib contributor, dominated by `lintegral_Lp_integral_le` and the
attendant corner-case bookkeeping (`p = 1`, `A = 0`, `A = ∞`).
-/

end MeasureTheory
