import Mathlib.Tactic
import Mathlib.Analysis.Convolution
import Mathlib.MeasureTheory.Function.LpSeminorm.Defs
import Mathlib.MeasureTheory.Function.LpSeminorm.TriangleInequality
import Mathlib.MeasureTheory.Function.LocallyIntegrable
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.MeanInequalities
import Mathlib.MeasureTheory.Group.Prod
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic
import Mathlib.MeasureTheory.Measure.Lebesgue.Integral
import Mathlib.MeasureTheory.Measure.Prod
import ZtareProofs.SQ3.MLG_eLpNorm_iSup_duality
import ZtareProofs.SQ3.SQ3_PR1_lp_translation_continuity

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
6. `eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_product_meas` —
   a **`p = 2` nonnegative lintegral slice** of the continuous
   Minkowski inequality under product `AEMeasurable`, with the a.e.
   fibre measurability discharged by Mathlib's product-section API.
7. `eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_ae_fiber_meas` —
   a **`p = 2` nonnegative lintegral slice** of the continuous
   Minkowski inequality with the fibre measurability hypothesis reduced
   to the a.e. condition actually used by the proof.
8. `eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_lintegral_rpow_ne_zero_ne_top` —
   a **`p = 2` nonnegative lintegral slice** of the continuous
   Minkowski inequality. It consumes the p=2 eLpNorm-duality equality
   and Tonelli. This all-fibre variant is a convenience corollary of
   the a.e.-fibre theorem.
9. `eLpNorm_two_integral_le_lintegral_eLpNorm_of_product_meas` —
   a **`p = 2` Bochner/vector slice** obtained by comparing the
   Bochner integral to its `lintegral` norm majorant and applying the
   nonnegative slice.
10. `eLpNorm_two_convolution_sub_le_lintegral_translate_diff` —
    a **`p = 2` convolution-rate specialization** of the vector slice,
    with the kernel measurability, fibre integrability, and positive
    finite majorant hypotheses explicit.
11. `aestronglyMeasurable_convolution_diff_kernel_of_map_sub` —
    a source-obligation helper paying product measurability of the
    convolution-difference kernel from measurable `ρ`, measurable `f`,
    and the subtraction-pushforward measurability of `f`.
12. `aestronglyMeasurable_convolution_diff_kernel_of_sub_pushforward_ac` —
    the same source obligation discharged from the abstract transport
    condition `Measure.map (fun p => p.1 - p.2) (μ.prod μ) ≪ μ`.
13. `sub_pushforward_prod_absolutelyContinuous_of_isAddLeftInvariant` —
    the general additive left-invariant transport theorem, using
    Mathlib's product-group quasi-measure-preservation theorem.
14. `aestronglyMeasurable_convolution_diff_kernel_of_add_left_invariant_measure` —
    the direct product-measurability source corollary for additive
    left-invariant `SFinite` measures.
15. `map_sub_prod_volume_absolutelyContinuous_real` — the real
    Lebesgue subtraction-pushforward transport theorem:
    `(x, y) ↦ x - y` sends null sets to product-null preimages, so the
    pushforward of `volume.prod volume` is absolutely continuous with
    respect to `volume`.
16. `aestronglyMeasurable_convolution_diff_kernel_real_volume` —
    the real-volume product-measurability corollary for the
    convolution-difference kernel, discharging the subtraction-pushforward
    hypothesis from ordinary `AEStronglyMeasurable f volume`.
17. `locallyIntegrable_sub_left_const_real` — local integrability of
    the fibre difference `y ↦ f (x - y) - f x` from local integrability
    of `f`, using Mathlib's one-variable subtraction transport theorem.
18. `integrable_fibre_convolution_diff_kernel_real_of_locallyIntegrable` —
    Bochner integrability of each real-volume convolution-difference
    fibre from a continuous compactly supported kernel and locally
    integrable `f`.
19. `integrable_fibre_convolution_diff_kernel_real_of_memLp_two` —
    the `MemLp p=2` corollary for the same fibre integrability source.
20. `eLpNorm_two_lintegral_finiteness_bridge_of_minkowski_inequality` —
    the exact reduction from the no-side-condition p=2 nonnegative
    continuous-Minkowski inequality to the finiteness-only bridge needed
    by the real convolution-difference left-majorant source.
21. `eLpNorm_two_lintegral_minkowski_inequality_of_top_edge` —
    the exact reduction from the p=2 top-edge theorem to the
    no-side-condition p=2 nonnegative continuous-Minkowski inequality.
22. `eLpNorm_two_lintegral_minkowski_top_edge_of_duality_top_edge` —
    the exact reduction from the p=2 `eLpNorm` duality infinite-edge theorem
    to the continuous-Minkowski top-edge theorem.
23. `eLpNorm_two_duality_top_edge_of_finite_piece_exhaustion` —
    finite-piece exhaustion under `f` implies the p=2 `eLpNorm` duality
    infinite-edge theorem.
24. `eLpNorm_two_finite_piece_exhaustion_of_square_lintegral_exhaustion` —
    pure square-lintegral finite-subpiece exhaustion implies p=2 finite-piece
    eLpNorm exhaustion.
25. `eLpNorm_two_finite_piece_exhaustion_sigmaFinite` — sigma-finite
    p=2 finite-piece exhaustion, discharged by LeanMill using Mathlib's
    simple-function approximation API.
26. `eLpNorm_two_duality_top_edge_sigmaFinite` — p=2 duality infinite edge
    on sigma-finite measure spaces.
27. `eLpNorm_two_lintegral_minkowski_top_edge_sigmaFinite` — p=2
    continuous-Minkowski top edge on sigma-finite left measure spaces.
28. `eLpNorm_two_lintegral_minkowski_inequality_sigmaFinite` — no-side-
    condition p=2 nonnegative continuous-Minkowski inequality on sigma-finite
    left measure spaces.
29. `eLpNorm_two_lintegral_finiteness_bridge_sigmaFinite` — finiteness-only
    p=2 continuous-Minkowski bridge on sigma-finite left measure spaces.
30. `left_majorant_nontop_convolution_diff_kernel_real` — real-line
    convolution-difference left-majorant source obligation from `MemLp f 2`.
31. `eLpNorm_two_integral_le_lintegral_eLpNorm_sigmaFinite` — no-side-
    condition p=2 Bochner/vector continuous-Minkowski slice on sigma-finite
    left measure spaces.
32. `eLpNorm_two_convolution_sub_le_lintegral_translate_diff_sigmaFinite` —
    no-side-condition p=2 convolution-rate specialization.
33. `eLpNorm_two_convolution_sub_le_lintegral_translate_diff_real` — real
    p=2 convolution-rate theorem for continuous compactly supported kernels.
34. `eLpNorm_two_real_mollifier_limit_of_rhs_tendsto_zero` — p=2 real
    mollifier-limit reduction from RHS majorant convergence to convolution
    error convergence.
35. `eLpNorm_two_translate_diff_le_real_of_memLp_two` — uniform p=2
    real-line translation-difference bound from `MemLp f 2`.
36. `tendsto_eLpNorm_translate_diff_sub_zero_real_of_translateBy` —
    orientation bridge from PR1-style `translateBy h f - f` continuity to
    the convolution RHS convention `f(x - y) - f(x)`.
37. `eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_concentration` —
    RHS majorant convergence from an abstract near/far concentration
    functional.
38. `eLpNorm_two_real_mollifier_limit_of_concentration` — p=2 real
    mollifier-limit theorem from the abstract concentration source.
39. `mollifier_concentration_near_far_enorm_real` — concrete near/far
    concentration theorem for bounded ENNReal moduli and weighted tails,
    discharged by LeanMill's agentic leaf.
40. `eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far` — actual
    RHS majorant convergence from total-mass and tail-mass hypotheses.
41. `eLpNorm_two_real_mollifier_limit_of_near_far` — p=2 real mollifier
    limit from the checked convolution-rate theorem and concrete near/far
    weight hypotheses.
42. `tendsto_eLpNorm_translate_diff_sub_zero_real_of_memLp_two` —
    real-line p=2 translation-modulus continuity from PR1 via the
    one-dimensional Euclidean bridge.
43. `eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far_memLp` —
    RHS convergence from near/far hypotheses with the PR1 modulus supplied.
44. `eLpNorm_two_real_mollifier_limit_of_near_far_memLp` — p=2 real
    mollifier limit from compact kernels, near/far mass/tail hypotheses,
    and PR1.
45. `lintegral_enorm_eq_one_of_nonneg_integral_one` — total variation
    mass equals one for nonnegative unit-mass real kernels.
46. `mollifier_total_mass_bound_one_of_nonneg_unit` — the `B = 1`
    mass-bound source for nonnegative unit-mass kernel families.
47. `eLpNorm_two_real_mollifier_limit_of_nonneg_unit_tail_memLp` —
    p=2 real mollifier limit from nonnegative unit mass, PR1, and tail
    concentration.
48. `mollifier_tail_tendsto_zero_of_eventually_zero_off_ball` — tail
    concentration from eventual support inside every fixed ball.
49. `eLpNorm_two_real_mollifier_limit_of_nonneg_unit_support_memLp` —
    p=2 real mollifier limit from nonnegative unit mass and support
    concentration.

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
| `MeasureTheory.locallyIntegrable_map_homeomorph` | `MeasureTheory/Function/LocallyIntegrable.lean:371` | yes |
| `MeasureTheory.LocallyIntegrable.integrable_smul_left_of_hasCompactSupport` | `MeasureTheory/Function/LocallyIntegrable.lean:415` | yes |
| `MeasureTheory.MemLp.locallyIntegrable` | `MeasureTheory/Function/LocallyIntegrable.lean:334` | yes |
| `MeasureTheory.Measure.map_sub_left_eq_self` | `MeasureTheory/Group/Measure.lean:394` (`to_additive`) | yes |
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
* A nonnegative `p = 2` lintegral slice in the positive finite regime,
  assuming only product `AEMeasurable` for the integrand.
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
open ZtareProofs.SQ3.MLGiSupDuality

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

/-! ## §3a. A `p = 2` nonnegative lintegral Minkowski slice

This closes a genuine part of the continuous Minkowski gap using the
new p=2 eLpNorm-duality equality from `MLG_eLpNorm_iSup_duality`.

Scope is deliberately honest:

* the integrand is `ℝ≥0∞`-valued and integrated with `lintegral`;
* the left-hand p=2 norm is assumed positive and finite;
* the natural product `AEMeasurable` assumption now discharges the a.e.
  fibre-measurability input via Mathlib section measurability.

The remaining MLG-2 work is to lift from this nonnegative `lintegral`
slice to the Bochner/vector convolution-rate statement. -/

/-- **`p = 2` nonnegative continuous Minkowski slice with a.e. fibre
measurability.** In the positive finite regime, the p=2 `eLpNorm` of
the `lintegral` in `y` is bounded by the `lintegral` in `y` of the p=2
`eLpNorm` fibres. -/
theorem eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_ae_fiber_meas
    {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]
    {F : α → β → ℝ≥0∞}
    (hF_meas : AEMeasurable (Function.uncurry F) (μ.prod ν))
    (hF_fiber_meas : ∀ᵐ y ∂ν, AEMeasurable (fun x => F x y) μ)
    (h_left_nonzero : (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) ≠ 0)
    (h_left_nontop : (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) ≠ ⊤) :
    eLpNorm (fun x => ∫⁻ y, F x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
  have h_left_meas : AEMeasurable (fun x => ∫⁻ y, F x y ∂ν) μ :=
    hF_meas.lintegral_prod_right
  rw [eLpNorm_two_eq_iSup_lintegral_mul_of_lintegral_rpow_ne_zero_ne_top
    h_left_meas h_left_nonzero h_left_nontop]
  refine iSup_le ?_
  rintro ⟨g, hg_meas, hg_norm⟩
  have h_prod_meas :
      AEMeasurable (Function.uncurry fun x y => F x y * g x) (μ.prod ν) := by
    exact hF_meas.mul hg_meas.comp_fst
  calc
    ∫⁻ x, (∫⁻ y, F x y ∂ν) * g x ∂μ
        ≤ ∫⁻ x, ∫⁻ y, F x y * g x ∂ν ∂μ := by
          apply lintegral_mono
          intro x
          exact lintegral_mul_const_le (g x) (fun y => F x y)
    _ = ∫⁻ y, ∫⁻ x, F x y * g x ∂μ ∂ν := by
          exact lintegral_lintegral_swap h_prod_meas
    _ ≤ ∫⁻ y, eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
          apply lintegral_mono_ae
          filter_upwards [hF_fiber_meas] with y hy
          have h_pair :
              ∫⁻ x, F x y * g x ∂μ
                ≤ eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ *
                    eLpNorm g (ENNReal.ofReal (2 : ℝ)) μ :=
            lintegral_mul_le_eLpNorm_mul_eLpNorm_ennreal
              Real.HolderConjugate.two_two hy hg_meas
          calc
            ∫⁻ x, F x y * g x ∂μ
                ≤ eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ *
                    eLpNorm g (ENNReal.ofReal (2 : ℝ)) μ := h_pair
            _ ≤ eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ * 1 := by
                  exact mul_le_mul' le_rfl hg_norm
            _ = eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ := by
                  rw [mul_one]

/-- **All-fibre convenience corollary** of
`eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_ae_fiber_meas`. -/
theorem eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_lintegral_rpow_ne_zero_ne_top
    {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]
    {F : α → β → ℝ≥0∞}
    (hF_meas : AEMeasurable (Function.uncurry F) (μ.prod ν))
    (hF_fiber_meas : ∀ y, AEMeasurable (fun x => F x y) μ)
    (h_left_nonzero : (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) ≠ 0)
    (h_left_nontop : (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) ≠ ⊤) :
    eLpNorm (fun x => ∫⁻ y, F x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν :=
  eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_ae_fiber_meas
    hF_meas (Filter.Eventually.of_forall hF_fiber_meas) h_left_nonzero h_left_nontop

/-- **Product-measurable `p = 2` nonnegative continuous Minkowski slice.**
This is the natural product-measurable form of the nonnegative
`lintegral` theorem. The a.e. fibre-measurability input is obtained
from `hF_meas` by converting to `AEStronglyMeasurable`, applying
Mathlib's `prodMk_right` section theorem, and converting the fibres
back to `AEMeasurable`. -/
theorem eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_product_meas
    {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]
    {F : α → β → ℝ≥0∞}
    (hF_meas : AEMeasurable (Function.uncurry F) (μ.prod ν))
    (h_left_nonzero : (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) ≠ 0)
    (h_left_nontop : (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) ≠ ⊤) :
    eLpNorm (fun x => ∫⁻ y, F x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
  have hF_fiber_meas : ∀ᵐ y ∂ν, AEMeasurable (fun x => F x y) μ := by
    filter_upwards [hF_meas.aestronglyMeasurable.prodMk_right] with y hy
    simpa [Function.uncurry] using hy.aemeasurable
  exact eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_ae_fiber_meas
    hF_meas hF_fiber_meas h_left_nonzero h_left_nontop

/-- **Product-measurable `p = 2` Bochner/vector continuous Minkowski slice.**
This lifts the nonnegative `lintegral` slice to vector-valued Bochner
integrals by the pointwise majorization
`‖∫ y, G x y ∂ν‖ₑ ≤ ∫⁻ y, ‖G x y‖ₑ ∂ν`, monotonicity of `eLpNorm`, and
`eLpNorm_enorm` on the fibres. -/
theorem eLpNorm_two_integral_le_lintegral_eLpNorm_of_product_meas
    {μ : Measure α} {ν : Measure β} [SFinite μ] [SFinite ν]
    {G : α → β → E}
    (hG_meas : AEStronglyMeasurable (Function.uncurry G) (μ.prod ν))
    (hG_int : ∀ᵐ x ∂μ, Integrable (fun y => G x y) ν)
    (h_left_nonzero :
      (∫⁻ x, (∫⁻ y, ‖G x y‖ₑ ∂ν) ^ (2 : ℝ) ∂μ) ≠ 0)
    (h_left_nontop :
      (∫⁻ x, (∫⁻ y, ‖G x y‖ₑ ∂ν) ^ (2 : ℝ) ∂μ) ≠ ⊤) :
    eLpNorm (fun x => ∫ y, G x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, eLpNorm (fun x => G x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
  have h_pointwise :
      ∀ᵐ x ∂μ, ‖∫ y, G x y ∂ν‖ₑ ≤ ∫⁻ y, ‖G x y‖ₑ ∂ν := by
    filter_upwards [hG_int] with x _hx
    exact enorm_integral_le_lintegral_enorm (fun y => G x y)
  have h_pointwise_enorm :
      ∀ᵐ x ∂μ,
        ‖∫ y, G x y ∂ν‖ₑ ≤ ‖(∫⁻ y, ‖G x y‖ₑ ∂ν)‖ₑ := by
    filter_upwards [h_pointwise] with x hx
    simpa [enorm_eq_self] using hx
  have h_lhs_bound :
      eLpNorm (fun x => ∫ y, G x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
        ≤ eLpNorm (fun x => ∫⁻ y, ‖G x y‖ₑ ∂ν)
            (ENNReal.ofReal (2 : ℝ)) μ :=
    eLpNorm_mono_enorm_ae h_pointwise_enorm
  have hF_meas :
      AEMeasurable (Function.uncurry fun x y => ‖G x y‖ₑ) (μ.prod ν) := by
    simpa [Function.uncurry] using hG_meas.enorm
  have h_nonneg :
      eLpNorm (fun x => ∫⁻ y, ‖G x y‖ₑ ∂ν)
          (ENNReal.ofReal (2 : ℝ)) μ
        ≤ ∫⁻ y, eLpNorm (fun x => ‖G x y‖ₑ)
            (ENNReal.ofReal (2 : ℝ)) μ ∂ν :=
    eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_product_meas
      hF_meas h_left_nonzero h_left_nontop
  have h_rhs_eq :
      (∫⁻ y, eLpNorm (fun x => ‖G x y‖ₑ)
          (ENNReal.ofReal (2 : ℝ)) μ ∂ν)
        = ∫⁻ y, eLpNorm (fun x => G x y)
          (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
    apply lintegral_congr_ae
    filter_upwards with y
    rw [eLpNorm_enorm]
  exact h_lhs_bound.trans (h_nonneg.trans_eq h_rhs_eq)

/-- **`p = 2` convolution-rate specialization.** This composes the
Bochner/vector `p = 2` continuous-Minkowski slice with the closed
convolution-difference identity, then factors the scalar `ρ y` out of
the fibre `eLpNorm`. The remaining source obligations are stated
explicitly: product measurability of the kernel, a.e. Bochner
integrability of both kernel forms, and positive/finite left majorant
mass for the p=2 vector slice. -/
theorem eLpNorm_two_convolution_sub_le_lintegral_translate_diff
    [CompleteSpace E]
    {G : Type*} [MeasurableSpace G] [Sub G]
    {μ : Measure G} [SFinite μ]
    {ρ : G → ℝ} (hρ_int : Integrable ρ μ)
    (hρ_one : ∫ y, ρ y ∂μ = 1)
    {f : G → E}
    (h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x)) (μ.prod μ))
    (h_conv_int : ∀ᵐ x ∂μ, Integrable (fun y => ρ y • f (x - y)) μ)
    (h_diff_int :
      ∀ᵐ x ∂μ, Integrable (fun y => ρ y • (f (x - y) - f x)) μ)
    (h_left_nonzero :
      (∫⁻ x,
          (∫⁻ y, ‖ρ y • (f (x - y) - f x)‖ₑ ∂μ) ^ (2 : ℝ) ∂μ) ≠ 0)
    (h_left_nontop :
      (∫⁻ x,
          (∫⁻ y, ‖ρ y • (f (x - y) - f x)‖ₑ ∂μ) ^ (2 : ℝ) ∂μ) ≠ ⊤) :
    eLpNorm
        (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x)
        (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, ‖ρ y‖ₑ *
          eLpNorm (fun x => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) μ ∂μ := by
  have h_rewrite_ae :
      (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x)
        =ᵐ[μ] (fun x => ∫ y, ρ y • (f (x - y) - f x) ∂μ) := by
    filter_upwards [h_conv_int] with x hx
    exact convolution_sub_eq_integral_translate_diff_aux
      hρ_int hρ_one x hx
  rw [eLpNorm_congr_ae h_rewrite_ae]
  have h_step :
      eLpNorm
          (fun x => ∫ y, ρ y • (f (x - y) - f x) ∂μ)
          (ENNReal.ofReal (2 : ℝ)) μ
        ≤ ∫⁻ y,
            eLpNorm (fun x => ρ y • (f (x - y) - f x))
              (ENNReal.ofReal (2 : ℝ)) μ ∂μ :=
    eLpNorm_two_integral_le_lintegral_eLpNorm_of_product_meas
      h_diff_meas h_diff_int h_left_nonzero h_left_nontop
  refine h_step.trans ?_
  apply lintegral_mono_ae
  filter_upwards with y
  rw [show (fun x => ρ y • (f (x - y) - f x)) =
      (ρ y) • (fun x => f (x - y) - f x) from rfl,
      eLpNorm_const_smul]

/-- **Product measurability source for the convolution-difference kernel.**
If `ρ` is a.e. measurable, `f` is a.e. measurable, and `f` is ae strongly
measurable after pushing `μ.prod μ` forward along subtraction, then
`(x, y) ↦ ρ y • (f (x - y) - f x)` is product-ae-strongly-measurable.

The subtraction-pushforward hypothesis is intentionally explicit: it is the
real source obligation for the `x - y` occurrence, and should not be silently
identified with measurability of `f` under `μ` unless a measure-preserving or
quasi-measure-preserving transport lemma has been paid. -/
theorem aestronglyMeasurable_convolution_diff_kernel_of_map_sub
    {G : Type*} [MeasurableSpace G] [Sub G] [MeasurableSub₂ G]
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {μ : Measure G} {ρ : G → ℝ} {f : G → E}
    (hρ : AEMeasurable ρ μ)
    (hf : AEMeasurable f μ)
    (hf_sub :
      AEStronglyMeasurable f
        (Measure.map (fun p : G × G => p.1 - p.2) (μ.prod μ))) :
    AEStronglyMeasurable
      (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
      (μ.prod μ) := by
  have hρ_snd :
      AEStronglyMeasurable (fun p : G × G => ρ p.2) (μ.prod μ) :=
    (hρ.comp_snd (μ := μ)).aestronglyMeasurable
  have hf_sub_prod :
      AEStronglyMeasurable (fun p : G × G => f (p.1 - p.2)) (μ.prod μ) := by
    simpa [Function.comp_def] using hf_sub.comp_measurable (μ := μ.prod μ) measurable_sub
  have hf_fst :
      AEStronglyMeasurable (fun p : G × G => f p.1) (μ.prod μ) :=
    (hf.comp_fst (ν := μ)).aestronglyMeasurable
  have hdiff :
      AEStronglyMeasurable (fun p : G × G => f (p.1 - p.2) - f p.1) (μ.prod μ) :=
    hf_sub_prod.sub hf_fst
  simpa [Function.uncurry] using hρ_snd.smul hdiff

/-- **Product measurability from abstract subtraction transport.**
If the subtraction pushforward of `μ.prod μ` is absolutely continuous with
respect to `μ`, then ordinary `AEStronglyMeasurable f μ` is enough to
pay the shifted `f (x - y)` source in the convolution-difference kernel. -/
theorem aestronglyMeasurable_convolution_diff_kernel_of_sub_pushforward_ac
    {G : Type*} [MeasurableSpace G] [Sub G] [MeasurableSub₂ G]
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {μ : Measure G} {ρ : G → ℝ} {f : G → E}
    (hsub_ac :
      Measure.map (fun p : G × G => p.1 - p.2) (μ.prod μ) ≪ μ)
    (hρ : AEMeasurable ρ μ)
    (hf : AEStronglyMeasurable f μ) :
    AEStronglyMeasurable
      (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
      (μ.prod μ) :=
  aestronglyMeasurable_convolution_diff_kernel_of_map_sub
    hρ hf.aemeasurable (hf.mono_ac hsub_ac)

/-- **Subtraction-pushforward absolute continuity for additive
left-invariant measures.**  This is the general Haar-style transport
behind the concrete Euclidean source obligation. -/
theorem sub_pushforward_prod_absolutelyContinuous_of_isAddLeftInvariant
    {G : Type*} [MeasurableSpace G] [AddGroup G]
    [MeasurableAdd₂ G] [MeasurableNeg G]
    {μ ν : Measure G} [SFinite μ] [SFinite ν] [Measure.IsAddLeftInvariant μ] :
    Measure.map (fun p : G × G => p.1 - p.2) (μ.prod ν) ≪ μ :=
  (quasiMeasurePreserving_sub (μ := μ) (ν := ν)).absolutelyContinuous

/-- **Product measurability source for additive left-invariant measures.**
This removes the abstract subtraction-pushforward hypothesis in the common
Haar/Lebesgue setting where `μ` is additive left-invariant and s-finite. -/
theorem aestronglyMeasurable_convolution_diff_kernel_of_add_left_invariant_measure
    {G : Type*} [MeasurableSpace G] [AddGroup G]
    [MeasurableAdd₂ G] [MeasurableNeg G] [MeasurableSub₂ G]
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {μ : Measure G} [SFinite μ] [Measure.IsAddLeftInvariant μ]
    {ρ : G → ℝ} {f : G → E}
    (hρ : AEMeasurable ρ μ)
    (hf : AEStronglyMeasurable f μ) :
    AEStronglyMeasurable
      (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
      (μ.prod μ) :=
  aestronglyMeasurable_convolution_diff_kernel_of_sub_pushforward_ac
    (sub_pushforward_prod_absolutelyContinuous_of_isAddLeftInvariant (μ := μ) (ν := μ))
    hρ hf

/-- **Real Lebesgue subtraction-pushforward transport.**
For Lebesgue measure on `ℝ`, the pushforward of `volume.prod volume`
under subtraction is absolutely continuous with respect to `volume`.

The proof is the exact source obligation behind the `x - y` occurrence:
if `s` is null, then every section `{y | x - y ∈ s}` is a translated
reflected copy of `s`, hence null, and product-null follows by the
product null-section theorem. -/
theorem map_sub_prod_volume_absolutelyContinuous_real :
    Measure.map (fun p : ℝ × ℝ => p.1 - p.2)
        ((volume : Measure ℝ).prod (volume : Measure ℝ))
      ≪ (volume : Measure ℝ) := by
  refine Measure.AbsolutelyContinuous.mk fun s hs hs_zero => ?_
  rw [Measure.map_apply measurable_sub hs]
  let t : Set (ℝ × ℝ) := (fun p : ℝ × ℝ => p.1 - p.2) ⁻¹' s
  have ht : MeasurableSet t := hs.preimage measurable_sub
  change (volume : Measure ℝ).prod (volume : Measure ℝ) t = 0
  exact Measure.measure_prod_null_of_ae_null ht <|
    Filter.Eventually.of_forall fun x => by
      have hsection :
          (volume : Measure ℝ) ((fun y : ℝ => x - y) ⁻¹' s) = 0 := by
        have htrans :
            (volume : Measure ℝ) ((fun z : ℝ => x + z) ⁻¹' s) = 0 := by
          exact (measure_preimage_add (volume : Measure ℝ) x s).trans hs_zero
        have hneg :
            (volume : Measure ℝ)
                ((fun y : ℝ => -y) ⁻¹' ((fun z : ℝ => x + z) ⁻¹' s)) = 0 :=
          (quasiMeasurePreserving_neg (volume : Measure ℝ)).preimage_null htrans
        convert hneg using 1
      simpa [t] using hsection

/-- **Real-volume product measurability source for the convolution-difference
kernel.**  This discharges the subtraction-pushforward hypothesis in
`aestronglyMeasurable_convolution_diff_kernel_of_map_sub` from the
Lebesgue transport theorem above. -/
theorem aestronglyMeasurable_convolution_diff_kernel_real_volume
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (hρ : AEMeasurable ρ (volume : Measure ℝ))
    (hf : AEStronglyMeasurable f (volume : Measure ℝ)) :
    AEStronglyMeasurable
      (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
      ((volume : Measure ℝ).prod (volume : Measure ℝ)) :=
  aestronglyMeasurable_convolution_diff_kernel_of_map_sub
    hρ hf.aemeasurable (hf.mono_ac map_sub_prod_volume_absolutelyContinuous_real)

/-- **Local-integrability source for the real convolution-difference fibre.**
If `f` is locally integrable, then for every fixed `x`, the fibre
`y ↦ f (x - y) - f x` is locally integrable.  The shifted term is paid
by Mathlib's real Lebesgue subtraction transport and homeomorphism transport
for local integrability; the constant term is locally integrable under the
locally finite real-volume measure. -/
theorem locallyIntegrable_sub_left_const_real
    {E : Type*} [NormedAddCommGroup E] [MeasurableSpace E] [BorelSpace E]
    {f : ℝ → E} (hf : LocallyIntegrable f (volume : Measure ℝ)) (x : ℝ) :
    LocallyIntegrable (fun y : ℝ => f (x - y) - f x) (volume : Measure ℝ) := by
  have hcomp : LocallyIntegrable (fun y : ℝ => f (x - y)) (volume : Measure ℝ) := by
    have hf_map : LocallyIntegrable f (Measure.map (Homeomorph.subLeft x) volume) := by
      rw [show Measure.map (Homeomorph.subLeft x : ℝ → ℝ) (volume : Measure ℝ) =
          (volume : Measure ℝ) by
        simpa using Measure.map_sub_left_eq_self (volume : Measure ℝ) x]
      exact hf
    simpa using (locallyIntegrable_map_homeomorph (Homeomorph.subLeft x)).1 hf_map
  exact hcomp.sub (locallyIntegrable_const (f x))

/-- **Real-volume fibre integrability for continuous compactly supported kernels.**
For a continuous compactly supported scalar kernel `ρ`, local integrability
of `f` is enough to prove Bochner integrability of every fibre
`y ↦ ρ y • (f (x - y) - f x)`. -/
theorem integrable_fibre_convolution_diff_kernel_real_of_locallyIntegrable
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : Continuous ρ) (hρ_comp : HasCompactSupport ρ)
    (hf : LocallyIntegrable f (volume : Measure ℝ)) (x : ℝ) :
    Integrable (fun y : ℝ => ρ y • (f (x - y) - f x)) (volume : Measure ℝ) :=
  (locallyIntegrable_sub_left_const_real hf x).integrable_smul_left_of_hasCompactSupport
    hρ_cont hρ_comp

/-- **`MemLp p=2` fibre-integrability corollary.**
On real volume, `MemLp f 2` implies local integrability, so the compactly
supported-kernel fibre integrability source above applies pointwise in `x`. -/
theorem integrable_fibre_convolution_diff_kernel_real_of_memLp_two
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : Continuous ρ) (hρ_comp : HasCompactSupport ρ)
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)) (x : ℝ) :
    Integrable (fun y : ℝ => ρ y • (f (x - y) - f x)) (volume : Measure ℝ) :=
  integrable_fibre_convolution_diff_kernel_real_of_locallyIntegrable
    hρ_cont hρ_comp (hf.locallyIntegrable (by norm_num)) x

/-- **Right-hand p=2 majorant finiteness for real convolution differences.**
For `ρ ∈ L¹(volume)` and `f ∈ L²(volume)`, the right-hand side of the
p=2 convolution-rate estimate is finite:
`∫ ‖ρ y‖ * ‖f(· - y) - f‖₂ dy < ∞`.

This is a non-circular source reduction: it proves finiteness of the
translation-difference majorant on the right of the rate inequality, but it
does not by itself prove finiteness of the left majorant required by the
p=2 duality-based continuous-Minkowski slice. That remaining implication is
the Young/Minkowski source theorem. -/
theorem rhs_lintegral_translate_diff_lt_top_real_of_memLp_two
    {E : Type*} [NormedAddCommGroup E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (hρ_int : Integrable ρ (volume : Measure ℝ))
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)) :
    (∫⁻ y : ℝ,
        ‖ρ y‖ₑ *
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume) < ∞ := by
  let C : ℝ≥0∞ :=
    eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
      eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
  have hC_ne_top : C ≠ ∞ := by
    exact ENNReal.add_ne_top.2 ⟨hf.eLpNorm_ne_top, hf.eLpNorm_ne_top⟩
  have h_point :
      ∀ y : ℝ,
        eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ≤ C := by
    intro y
    have h_translate :
        MemLp (ZtareProofs.SQ3.PR1.translateBy (-y) f)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) :=
      ZtareProofs.SQ3.PR1.MemLp.translateBy_memLp hf (-y)
    have h_eq :
        (fun x : ℝ => f (x - y)) =
          ZtareProofs.SQ3.PR1.translateBy (-y) f := by
      ext x
      simp [ZtareProofs.SQ3.PR1.translateBy, sub_eq_add_neg]
    have h_sub :
        eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
          ≤ eLpNorm (fun x : ℝ => f (x - y))
              (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
            eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := by
      have htwo : 1 ≤ ENNReal.ofReal (2 : ℝ) := by norm_num
      exact eLpNorm_sub_le (h_eq.symm ▸ h_translate.aestronglyMeasurable)
        hf.aestronglyMeasurable htwo
    have h_trans_norm :
        eLpNorm (fun x : ℝ => f (x - y))
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) =
          eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := by
      rw [h_eq]
      exact ZtareProofs.SQ3.PR1.translateBy_eLpNorm_eq
        hf.aestronglyMeasurable (-y)
    calc
      eLpNorm (fun x : ℝ => f (x - y) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
          ≤ eLpNorm (fun x : ℝ => f (x - y))
              (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
            eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := h_sub
      _ = eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
            eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := by
          rw [h_trans_norm]
      _ = C := rfl
  calc
    (∫⁻ y : ℝ,
        ‖ρ y‖ₑ *
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume)
        ≤ ∫⁻ y : ℝ, ‖ρ y‖ₑ * C ∂volume := by
          apply lintegral_mono
          intro y
          exact mul_le_mul_right (h_point y) ‖ρ y‖ₑ
    _ = (∫⁻ y : ℝ, ‖ρ y‖ₑ ∂volume) * C := by
          rw [lintegral_mul_const' _ _ hC_ne_top]
    _ < ∞ := by
          exact ENNReal.mul_lt_top
            (by
              rw [← hasFiniteIntegral_iff_enorm]
              exact hρ_int.hasFiniteIntegral)
            (lt_top_iff_ne_top.2 hC_ne_top)

/-- **Uniform p=2 translation-difference bound on the real line.**
For `f ∈ L²(volume)`, every real translation difference is bounded by the
sum of the two endpoint `L²` seminorms. -/
theorem eLpNorm_two_translate_diff_le_real_of_memLp_two
    {E : Type*} [NormedAddCommGroup E]
    {f : ℝ → E}
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)) :
    ∀ y : ℝ,
      eLpNorm (fun x : ℝ => f (x - y) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
        ≤ eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
          eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := by
  intro y
  have h_translate :
      MemLp (ZtareProofs.SQ3.PR1.translateBy (-y) f)
        (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) :=
    ZtareProofs.SQ3.PR1.MemLp.translateBy_memLp hf (-y)
  have h_eq :
      (fun x : ℝ => f (x - y)) =
        ZtareProofs.SQ3.PR1.translateBy (-y) f := by
    ext x
    simp [ZtareProofs.SQ3.PR1.translateBy, sub_eq_add_neg]
  have h_sub :
      eLpNorm (fun x : ℝ => f (x - y) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
        ≤ eLpNorm (fun x : ℝ => f (x - y))
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
          eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := by
    have htwo : 1 ≤ ENNReal.ofReal (2 : ℝ) := by norm_num
    exact eLpNorm_sub_le (h_eq.symm ▸ h_translate.aestronglyMeasurable)
      hf.aestronglyMeasurable htwo
  have h_trans_norm :
      eLpNorm (fun x : ℝ => f (x - y))
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) =
        eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) := by
    rw [h_eq]
    exact ZtareProofs.SQ3.PR1.translateBy_eLpNorm_eq
      hf.aestronglyMeasurable (-y)
  exact h_sub.trans_eq (by rw [h_trans_norm])

/-- **Orientation bridge for the real-line translation modulus.**
PR1-style continuity is usually stated for `translateBy h f - f`, i.e.
`x ↦ f (x + h) - f x`.  The convolution RHS uses the equivalent
`x ↦ f (x - y) - f x`; this lemma composes the PR1-style statement with
`y ↦ -y`. -/
theorem tendsto_eLpNorm_translate_diff_sub_zero_real_of_translateBy
    {E : Type*} [NormedAddCommGroup E]
    {p : ℝ≥0∞} {f : ℝ → E}
    (h_translate :
      Tendsto
        (fun h : ℝ =>
          eLpNorm (ZtareProofs.SQ3.PR1.translateBy h f - f) p
            (volume : Measure ℝ))
        (𝓝 0) (𝓝 0)) :
    Tendsto
      (fun y : ℝ =>
        eLpNorm (fun x : ℝ => f (x - y) - f x) p
          (volume : Measure ℝ))
      (𝓝 0) (𝓝 0) := by
  have h_neg : Tendsto (fun y : ℝ => -y) (𝓝 0) (𝓝 0) := by
    simpa using (continuous_neg.tendsto (0 : ℝ))
  have h_comp := h_translate.comp h_neg
  simpa [ZtareProofs.SQ3.PR1.translateBy, sub_eq_add_neg, Pi.sub_apply] using h_comp

/-! ### One-dimensional PR1 bridge

PR1 is stated over `EuclideanSpace ℝ (Fin d)`.  The real-line compact-kernel
mollifier theorem above uses bare `ℝ`, so the next lemmas transport the
one-dimensional Euclidean PR1 theorem across the singleton-coordinate
measure-preserving equivalence. -/

abbrev RealBridgeR1 : Type := EuclideanSpace ℝ (Fin 1)

abbrev p2 : ℝ≥0∞ := ENNReal.ofReal (2 : ℝ)

noncomputable def realBridgeCoord (x : RealBridgeR1) : ℝ :=
  WithLp.ofLp x 0

noncomputable def realBridgeEmbed (y : ℝ) : RealBridgeR1 :=
  WithLp.toLp 2 (fun _ : Fin 1 => y)

noncomputable def realBridgePull {E : Type*} (f : ℝ → E) :
    RealBridgeR1 → E :=
  fun x => f (realBridgeCoord x)

def realBridgeDiff {E : Type*} [Sub E] (f : ℝ → E) (y : ℝ) :
    ℝ → E :=
  fun x => f (x - y) - f x

noncomputable def euclideanBridgeDiff {E : Type*} [Sub E] (f : ℝ → E)
    (y : ℝ) : RealBridgeR1 → E :=
  ZtareProofs.SQ3.PR1.translateBy (realBridgeEmbed (-y))
    (realBridgePull f) - realBridgePull f

theorem realBridgeCoord_measurePreserving :
    MeasurePreserving realBridgeCoord
      (volume : Measure RealBridgeR1) (volume : Measure ℝ) := by
  have hmp :
      MeasurePreserving
        (fun x : RealBridgeR1 =>
          MeasurableEquiv.funUnique (Fin 1) ℝ (WithLp.ofLp x))
        (volume : Measure RealBridgeR1) (volume : Measure ℝ) :=
    (MeasureTheory.volume_preserving_funUnique (Fin 1) ℝ).comp
      (PiLp.volume_preserving_ofLp (ι := Fin 1))
  simpa [realBridgeCoord, RealBridgeR1] using hmp

theorem tendsto_realBridgeEmbed_neg_zero :
    Tendsto (fun y : ℝ => realBridgeEmbed (-y))
      (𝓝 0) (𝓝 (0 : RealBridgeR1)) := by
  have hcont : Continuous (fun y : ℝ => realBridgeEmbed (-y)) := by
    have hconst : Continuous (fun y : ℝ => (fun _ : Fin 1 => -y)) := by
      exact continuous_pi fun _ => continuous_neg
    exact
      (PiLp.continuous_toLp (p := (2 : ℝ≥0∞))
        (β := fun _ : Fin 1 => ℝ)).comp hconst
  simpa [realBridgeEmbed] using hcont.tendsto 0

theorem memLp_realBridgePull {E : Type*}
    [NormedAddCommGroup E] [MeasurableSpace E] [BorelSpace E]
    {f : ℝ → E}
    (hf : MemLp f p2 (volume : Measure ℝ)) :
    MemLp (realBridgePull f) p2 (volume : Measure RealBridgeR1) :=
  hf.comp_measurePreserving realBridgeCoord_measurePreserving

theorem euclideanBridgeDiff_eq_realBridgeDiff_comp {E : Type*} [Sub E]
    (f : ℝ → E) (y : ℝ) :
    euclideanBridgeDiff f y =
      fun x : RealBridgeR1 => realBridgeDiff f y (realBridgeCoord x) := by
  funext x
  simp [euclideanBridgeDiff, realBridgeDiff, realBridgePull,
    ZtareProofs.SQ3.PR1.translateBy, realBridgeCoord, realBridgeEmbed,
    sub_eq_add_neg]

theorem eLpNorm_realBridgePull_eq {E : Type*}
    [NormedAddCommGroup E] [MeasurableSpace E]
    {g : ℝ → E}
    (hg : AEStronglyMeasurable g (volume : Measure ℝ)) :
    eLpNorm (fun x : RealBridgeR1 => g (realBridgeCoord x)) p2
        (volume : Measure RealBridgeR1) =
      eLpNorm g p2 (volume : Measure ℝ) :=
  eLpNorm_comp_measurePreserving hg realBridgeCoord_measurePreserving

set_option maxHeartbeats 400000 in
-- The singleton-coordinate transport equality unfolds several measure-
-- preserving and `WithLp` wrappers; the factored proof is small but needs a
-- slightly larger elaboration budget.
theorem eLpNorm_realBridgeDiff_eq {E : Type*}
    [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E]
    {f : ℝ → E}
    (hf : MemLp f p2 (volume : Measure ℝ)) (y : ℝ) :
    eLpNorm (euclideanBridgeDiff f y) p2 (volume : Measure RealBridgeR1) =
      eLpNorm (realBridgeDiff f y) p2 (volume : Measure ℝ) := by
  have htarget_mem : MemLp (realBridgeDiff f y) p2 (volume : Measure ℝ) := by
    have htranslate :
        MemLp (ZtareProofs.SQ3.PR1.translateBy (-y) f)
          p2 (volume : Measure ℝ) :=
      ZtareProofs.SQ3.PR1.MemLp.translateBy_memLp hf (-y)
    convert htranslate.sub hf using 1
  rw [euclideanBridgeDiff_eq_realBridgeDiff_comp]
  exact eLpNorm_realBridgePull_eq htarget_mem.aestronglyMeasurable

/-- **Real-line p=2 translation-modulus continuity from PR1.**
This discharges the one-dimensional bridge from the Euclidean PR1 theorem to
the real-line modulus used by the compact-kernel mollifier theorem. -/
theorem tendsto_eLpNorm_translate_diff_sub_zero_real_of_memLp_two
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E]
    {f : ℝ → E}
    (hf : MemLp f p2 (volume : Measure ℝ)) :
    Tendsto
      (fun y : ℝ =>
        eLpNorm (fun x : ℝ => f (x - y) - f x)
          p2 (volume : Measure ℝ))
      (𝓝 0) (𝓝 0) := by
  have hE :
      Tendsto
        (fun h : RealBridgeR1 =>
          eLpNorm
            (ZtareProofs.SQ3.PR1.translateBy h (realBridgePull f) -
              realBridgePull f)
            p2 (volume : Measure RealBridgeR1))
        (𝓝 0) (𝓝 0) :=
    ZtareProofs.SQ3.PR1.tendsto_eLpNorm_translateBy_sub_zero
      (p := p2) (by norm_num [p2]) (by simp [p2])
      (memLp_realBridgePull hf)
  have hcomp := hE.comp tendsto_realBridgeEmbed_neg_zero
  exact hcomp.congr' (Filter.Eventually.of_forall fun y => by
    simpa [euclideanBridgeDiff, realBridgeDiff] using
      eLpNorm_realBridgeDiff_eq (f := f) hf y)

/-- **Near/far concentration source lemma for real mollifier weights.**
If a bounded modulus vanishes at zero, the kernel weights have eventually
bounded total mass, and their tails outside every fixed ball vanish, then the
weighted modulus integral vanishes.  This is the concrete source theorem behind
the abstract concentration functional used below. -/
theorem mollifier_concentration_near_far_enorm_real
    {ι : Type*} {l : Filter ι} {w : ι → ℝ → ℝ≥0∞} {ω : ℝ → ℝ≥0∞}
    {M B : ℝ≥0∞}
    (hω : Tendsto ω (𝓝 0) (𝓝 0))
    (hω_bound : ∀ y : ℝ, ω y ≤ M)
    (hM_ne_top : M ≠ ∞)
    (h_mass_bound : ∀ᶠ i in l, (∫⁻ y : ℝ, w i y ∂volume) ≤ B)
    (hB_ne_top : B ≠ ∞)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, w i y ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i : ι => ∫⁻ y : ℝ, w i y * ω y ∂volume)
      l (𝓝 0) := by
  refine ENNReal.tendsto_nhds_zero.2 ?_
  intro ε hε
  by_cases hε_top : ε = ∞
  · simp [hε_top]
  have hε_ne_zero : ε ≠ 0 := ne_of_gt hε
  let C : ℝ := max B.toReal M.toReal + 1
  have hC_pos : 0 < C := by
    dsimp [C]
    linarith [(ENNReal.toReal_nonneg : 0 ≤ B.toReal), le_max_left B.toReal M.toReal]
  have hε_toReal_pos : 0 < ε.toReal :=
    ENNReal.toReal_pos hε_ne_zero hε_top
  let ηR : ℝ := ε.toReal / (2 * C)
  let η : ℝ≥0∞ := ENNReal.ofReal ηR
  let q : ℝ≥0∞ := ENNReal.ofReal (ε.toReal / 2)
  have hηR_pos : 0 < ηR := by
    dsimp [ηR]
    exact div_pos hε_toReal_pos (mul_pos (by norm_num) hC_pos)
  have hη_pos : 0 < η := by
    exact ENNReal.ofReal_pos.mpr hηR_pos
  have hη_ne_top : η ≠ ∞ := by
    exact ENNReal.ofReal_ne_top
  have hB_le_C : B ≤ ENNReal.ofReal C := by
    calc
      B = ENNReal.ofReal B.toReal := (ENNReal.ofReal_toReal hB_ne_top).symm
      _ ≤ ENNReal.ofReal C := by
        apply ENNReal.ofReal_le_ofReal
        dsimp [C]
        exact le_trans (le_max_left _ _) (by linarith)
  have hM_le_C : M ≤ ENNReal.ofReal C := by
    calc
      M = ENNReal.ofReal M.toReal := (ENNReal.ofReal_toReal hM_ne_top).symm
      _ ≤ ENNReal.ofReal C := by
        apply ENNReal.ofReal_le_ofReal
        dsimp [C]
        exact le_trans (le_max_right _ _) (by linarith)
  have hη_mul_C : η * ENNReal.ofReal C = q := by
    rw [← ENNReal.ofReal_mul (le_of_lt hηR_pos)]
    congr 1
    dsimp [ηR, q]
    field_simp [ne_of_gt hC_pos]
  have hBη_le_q : B * η ≤ q := by
    calc
      B * η ≤ ENNReal.ofReal C * η := mul_le_mul_left hB_le_C η
      _ = η * ENNReal.ofReal C := by rw [mul_comm]
      _ = q := hη_mul_C
  have hηM_le_q : η * M ≤ q := by
    calc
      η * M ≤ η * ENNReal.ofReal C := mul_le_mul_right hM_le_C η
      _ = q := hη_mul_C
  have hq_add_q_le : q + q ≤ ε := by
    have hq_add :
        q + q = ENNReal.ofReal ε.toReal := by
      dsimp [q]
      rw [← ENNReal.ofReal_add (by positivity : 0 ≤ ε.toReal / 2)
        (by positivity : 0 ≤ ε.toReal / 2)]
      congr 1
      ring
    rw [hq_add, ENNReal.ofReal_toReal hε_top]
  have hω_small_eventually : ∀ᶠ y in 𝓝 (0 : ℝ), ω y ≤ η :=
    (ENNReal.tendsto_nhds_zero.1 hω) η hη_pos
  rcases Metric.mem_nhds_iff.1 hω_small_eventually with ⟨δ, hδ_pos, hδ_subset⟩
  let far : Set ℝ := {y : ℝ | δ ≤ ‖y‖}
  have hfar_meas : MeasurableSet far := by
    dsimp [far]
    exact (isClosed_le continuous_const continuous_norm).measurableSet
  have hnear_small : ∀ y ∈ farᶜ, ω y ≤ η := by
    intro y hy
    have hy_lt : ‖y‖ < δ := by
      simpa [far] using hy
    exact hδ_subset (by simpa [Metric.mem_ball, dist_eq_norm] using hy_lt)
  have htail_eventually :
      ∀ᶠ i in l, (∫⁻ y in far, w i y ∂volume) ≤ η := by
    have htailη :=
      (ENNReal.tendsto_nhds_zero.1 (h_tail δ hδ_pos)) η hη_pos
    simpa [far] using htailη
  filter_upwards [h_mass_bound, htail_eventually] with i hmass htail_i
  have hnear_bound :
      (∫⁻ y in farᶜ, w i y * ω y ∂volume) ≤ q := by
    calc
      (∫⁻ y in farᶜ, w i y * ω y ∂volume)
          ≤ ∫⁻ y in farᶜ, w i y * η ∂volume := by
            exact setLIntegral_mono' hfar_meas.compl
              (fun y hy => mul_le_mul_right (hnear_small y hy) (w i y))
      _ ≤ ∫⁻ y : ℝ, w i y * η ∂volume := setLIntegral_le_lintegral farᶜ _
      _ = (∫⁻ y : ℝ, w i y ∂volume) * η := by
            rw [lintegral_mul_const' η (fun y : ℝ => w i y) hη_ne_top]
      _ ≤ B * η := mul_le_mul_left hmass η
      _ ≤ q := hBη_le_q
  have hfar_bound :
      (∫⁻ y in far, w i y * ω y ∂volume) ≤ q := by
    have htailM_le : (∫⁻ y in far, w i y ∂volume) * M ≤ η * M :=
      mul_le_mul_left htail_i M
    calc
      (∫⁻ y in far, w i y * ω y ∂volume)
          ≤ ∫⁻ y in far, w i y * M ∂volume := by
            exact setLIntegral_mono' hfar_meas
              (fun y _hy => mul_le_mul_right (hω_bound y) (w i y))
      _ = (∫⁻ y in far, w i y ∂volume) * M := by
            rw [lintegral_mul_const' M (fun y : ℝ => w i y) hM_ne_top]
      _ ≤ η * M := htailM_le
      _ ≤ q := hηM_le_q
  calc
    (∫⁻ y : ℝ, w i y * ω y ∂volume)
        = (∫⁻ y in far, w i y * ω y ∂volume) +
            (∫⁻ y in farᶜ, w i y * ω y ∂volume) := by
          exact (lintegral_add_compl (fun y : ℝ => w i y * ω y) hfar_meas).symm
    _ ≤ q + q := add_le_add hfar_bound hnear_bound
    _ ≤ ε := hq_add_q_le

/-- **Finiteness-only p=2 continuous Minkowski bridge.**
This is the exact source theorem needed to turn finite fibre-L2 majorant
control into the `h_left_nontop` hypothesis of the p=2 convolution-rate
specialization.  It is weaker than the full inequality statement:
it asks only for finiteness of the left nested `lintegral` square from
finiteness of the `lintegral` of p=2 fibre `eLpNorm`s. -/
def eLpNorm_two_lintegral_finiteness_bridge
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SFinite μ] [SFinite ν] : Prop :=
  ∀ {F : α → β → ℝ≥0∞},
    AEMeasurable (Function.uncurry F) (μ.prod ν) →
    (∫⁻ y, eLpNorm (fun x => F x y)
      (ENNReal.ofReal (2 : ℝ)) μ ∂ν) < ∞ →
    (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) < ∞

/-- **No-side-condition p=2 nonnegative continuous-Minkowski inequality.**
This is the sharper source theorem behind
`eLpNorm_two_lintegral_finiteness_bridge`: once this inequality is proved,
the finiteness-only bridge follows by the standard `eLpNorm < top` iff
`lintegral`-of-square `< top` conversion. -/
def eLpNorm_two_lintegral_minkowski_inequality
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SFinite μ] [SFinite ν] : Prop :=
  ∀ {F : α → β → ℝ≥0∞},
    AEMeasurable (Function.uncurry F) (μ.prod ν) →
    eLpNorm (fun x => ∫⁻ y, F x y ∂ν)
      (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, eLpNorm (fun x => F x y)
        (ENNReal.ofReal (2 : ℝ)) μ ∂ν

/-- **Top-edge p=2 nonnegative continuous-Minkowski source theorem.**
The finite nonzero case is already checked by
`eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_product_meas`.
Thus the only remaining edge for the no-side-condition inequality is:
if the left square integral is infinite, then the RHS fibre-eLpNorm
integral is also infinite. -/
def eLpNorm_two_lintegral_minkowski_top_edge
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SFinite μ] [SFinite ν] : Prop :=
  ∀ {F : α → β → ℝ≥0∞},
    AEMeasurable (Function.uncurry F) (μ.prod ν) →
    (∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ) = ∞ →
    (∫⁻ y, eLpNorm (fun x => F x y)
      (ENNReal.ofReal (2 : ℝ)) μ ∂ν) = ∞

/-- **p=2 `eLpNorm` duality infinite-edge theorem.**
This is the precise duality edge needed by the continuous-Minkowski top-edge:
if the p=2 `eLpNorm` of a nonnegative function is infinite, then the
supremum of pairings against the p=2 unit ball is infinite. -/
def eLpNorm_two_duality_top_edge
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ] : Prop :=
  ∀ {f : α → ℝ≥0∞},
    AEMeasurable f μ →
    eLpNorm f (ENNReal.ofReal (2 : ℝ)) μ = ∞ →
    (⨆ g : { g : α → ℝ≥0∞ //
              AEMeasurable g μ ∧
              eLpNorm g (ENNReal.ofReal (2 : ℝ)) μ ≤ 1 },
        ∫⁻ x, f x * (g.val x) ∂μ) = ∞

/-- **Finite-piece exhaustion for the p=2 duality top edge.**
This is the exact truncation/localization source theorem needed to turn the
checked positive finite p=2 duality equality into the infinite-edge theorem:
an infinite p=2 function admits finite p=2 subfunctions with arbitrarily large
p=2 eLpNorm. -/
def eLpNorm_two_finite_piece_exhaustion
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ] : Prop :=
  ∀ {f : α → ℝ≥0∞},
    AEMeasurable f μ →
    eLpNorm f (ENNReal.ofReal (2 : ℝ)) μ = ∞ →
    ∀ {B : ℝ≥0∞}, B < ∞ →
      ∃ u : α → ℝ≥0∞,
        AEMeasurable u μ ∧
        (∀ᵐ x ∂μ, u x ≤ f x) ∧
        (∫⁻ x, u x ^ (2 : ℝ) ∂μ) ≠ 0 ∧
        (∫⁻ x, u x ^ (2 : ℝ) ∂μ) ≠ ∞ ∧
        B < eLpNorm u (ENNReal.ofReal (2 : ℝ)) μ

/-- **Pure square-lintegral finite-subpiece exhaustion.**
This strips the p=2 finite-piece target down to the remaining measure-theory
core: from infinite square integral, extract dominated finite-square pieces
with arbitrarily large square integral. -/
def square_lintegral_finite_subpiece_exhaustion
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ] : Prop :=
  ∀ {f : α → ℝ≥0∞},
    AEMeasurable f μ →
    (∫⁻ x, f x ^ (2 : ℝ) ∂μ) = ∞ →
    ∀ {L : ℝ≥0∞}, L < ∞ →
      ∃ u : α → ℝ≥0∞,
        AEMeasurable u μ ∧
        (∀ᵐ x ∂μ, u x ≤ f x) ∧
        (∫⁻ x, u x ^ (2 : ℝ) ∂μ) ≠ 0 ∧
        (∫⁻ x, u x ^ (2 : ℝ) ∂μ) ≠ ∞ ∧
        L < ∫⁻ x, u x ^ (2 : ℝ) ∂μ

/-- The p=2 finite-piece eLpNorm exhaustion follows from the pure
square-lintegral finite-subpiece exhaustion. -/
theorem eLpNorm_two_finite_piece_exhaustion_of_square_lintegral_exhaustion
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ]
    (h_square : square_lintegral_finite_subpiece_exhaustion μ) :
    eLpNorm_two_finite_piece_exhaustion μ := by
  intro f hf hf_top B hB
  have hp_ne_zero : ENNReal.ofReal (2 : ℝ) ≠ 0 := by norm_num
  have hp_ne_top : ENNReal.ofReal (2 : ℝ) ≠ ∞ := by simp
  have hp_toReal : (ENNReal.ofReal (2 : ℝ)).toReal = (2 : ℝ) := by norm_num
  have hf_square_top : (∫⁻ x, f x ^ (2 : ℝ) ∂μ) = ∞ := by
    have h_norm :
        (∫⁻ x, ‖f x‖ₑ ^ (2 : ℝ) ∂μ) = ∫⁻ x, f x ^ (2 : ℝ) ∂μ := by
      simp [enorm_eq_self]
    rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top,
        hp_toReal, h_norm] at hf_top
    by_contra h_ne_top
    have h_rpow_ne_top :
        (∫⁻ x, f x ^ (2 : ℝ) ∂μ) ^ (1 / (2 : ℝ)) ≠ ∞ :=
      ENNReal.rpow_ne_top_of_nonneg (by norm_num) h_ne_top
    exact h_rpow_ne_top hf_top
  have hB_sq_lt_top : B ^ (2 : ℕ) < ∞ := by
    simpa [pow_two] using ENNReal.mul_lt_top hB hB
  rcases h_square hf hf_square_top hB_sq_lt_top with
    ⟨u, hu_meas, hu_le_f, hu_sq_ne_zero, hu_sq_ne_top, hB_sq_lt_u_sq⟩
  refine ⟨u, hu_meas, hu_le_f, hu_sq_ne_zero, hu_sq_ne_top, ?_⟩
  rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top, hp_toReal]
  have h_norm_u :
      (∫⁻ x, ‖u x‖ₑ ^ (2 : ℝ) ∂μ) = ∫⁻ x, u x ^ (2 : ℝ) ∂μ := by
    simp [enorm_eq_self]
  rw [h_norm_u]
  have hB_sq_rpow_lt :
      (B ^ (2 : ℕ) : ℝ≥0∞) ^ (1 / (2 : ℝ))
        < (∫⁻ x, u x ^ (2 : ℝ) ∂μ) ^ (1 / (2 : ℝ)) :=
    ENNReal.rpow_lt_rpow hB_sq_lt_u_sq (by norm_num : (0 : ℝ) < 1 / 2)
  refine lt_of_le_of_lt ?_ hB_sq_rpow_lt
  by_cases hB_zero : B = 0
  · simp [hB_zero]
  · have hB_ne_top : B ≠ ∞ := hB.ne
    calc
      B = (B ^ (2 : ℕ)) ^ (1 / (2 : ℝ)) := by
            rw [pow_two, ENNReal.mul_rpow_of_nonneg _ _ (by norm_num : (0 : ℝ) ≤ 1 / 2),
                ← ENNReal.rpow_add]
            · norm_num
            · exact hB_zero
            · exact hB_ne_top
      _ ≤ (B ^ (2 : ℕ)) ^ (1 / (2 : ℝ)) := le_rfl

/-- **Finite-piece exhaustion on sigma-finite measure spaces.**
LeanMill discharged this Mathlib-absent formalization-bound frontier from
Mathlib's simple-function approximation API.  The proof extracts a finite
simple lower approximant of `f ^ 2`, takes its square root, and transports the
large finite square integral back to the p=2 `eLpNorm` threshold. -/
theorem eLpNorm_two_finite_piece_exhaustion_sigmaFinite
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ] :
    eLpNorm_two_finite_piece_exhaustion μ := by
  dsimp [eLpNorm_two_finite_piece_exhaustion]
  intro f hf htop B hB
  let v : α → ℝ≥0∞ := fun x => f x ^ (2 : ℝ)
  have hv : AEMeasurable v μ := hf.pow_const (2 : ℝ)
  have hp_ne_zero : ENNReal.ofReal (2 : ℝ) ≠ 0 := by norm_num
  have hp_ne_top : ENNReal.ofReal (2 : ℝ) ≠ ∞ := by simp
  have h_int_top : (∫⁻ x, v x ∂μ) = ∞ := by
    have hnorm :
        (∫⁻ x, ‖f x‖ₑ ^ (ENNReal.ofReal (2 : ℝ)).toReal ∂μ)
          = ∫⁻ x, v x ∂μ := by
      simp [v, enorm_eq_self]
    rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top] at htop
    rw [hnorm] at htop
    by_contra hne
    have hpow_lt_top :
        (∫⁻ x, v x ∂μ) ^ (1 / (ENNReal.ofReal (2 : ℝ)).toReal) < ∞ :=
      ENNReal.rpow_lt_top_of_nonneg (by positivity) hne
    rw [htop] at hpow_lt_top
    exact not_top_lt hpow_lt_top
  let L : ℝ≥0∞ := B ^ (2 : ℝ)
  have hL_top : L < ∞ :=
    ENNReal.rpow_lt_top_of_nonneg (by norm_num) hB.ne
  have h_eapprox_sup :
      (⨆ n, (SimpleFunc.eapprox (hv.mk v) n).lintegral μ) = ∞ := by
    simpa [h_int_top] using (lintegral_eq_iSup_eapprox_lintegral' hv).symm
  obtain ⟨n, hn⟩ : ∃ n, L < (SimpleFunc.eapprox (hv.mk v) n).lintegral μ := by
    simpa [h_eapprox_sup] using (iSup_eq_top _).1 h_eapprox_sup L hL_top
  let φ : SimpleFunc α ℝ≥0∞ := SimpleFunc.eapprox (hv.mk v) n
  let φn : SimpleFunc α NNReal := φ.map ENNReal.toNNReal
  have hφ_ne_top : ∀ x, φ x ≠ ∞ :=
    fun x => (SimpleFunc.eapprox_lt_top (hv.mk v) n x).ne
  have hφn_coe : (fun x => ((φn x : NNReal) : ℝ≥0∞)) = φ := by
    ext x
    simp [φn, SimpleFunc.coe_map, ENNReal.coe_toNNReal (hφ_ne_top x)]
  have hn_lintegral : L < ∫⁻ x, ((φn x : NNReal) : ℝ≥0∞) ∂μ := by
    rw [hφn_coe, SimpleFunc.lintegral_eq_lintegral]
    simpa [φ] using hn
  rcases exists_lt_lintegral_simpleFunc_of_lt_lintegral hn_lintegral with
    ⟨g, hg_le, hg_int_lt_top, hL_lt_g⟩
  let u : α → ℝ≥0∞ := fun x => ((g x : ℝ≥0∞) ^ (1 / (2 : ℝ)))
  have hu_sq :
      (∫⁻ x, u x ^ (2 : ℝ) ∂μ) = ∫⁻ x, (g x : ℝ≥0∞) ∂μ := by
    apply lintegral_congr
    intro x
    simp [u, one_div, ENNReal.rpow_inv_rpow (by norm_num : (2 : ℝ) ≠ 0)]
  refine ⟨u, ?_, ?_, ?_, ?_, ?_⟩
  · exact (g.measurable.coe_nnreal_ennreal.aemeasurable.pow_const (1 / (2 : ℝ)))
  · filter_upwards [hv.ae_eq_mk] with x hx
    have hφ_le_v : φ x ≤ v x := by
      calc
        φ x ≤ hv.mk v x := by
          rw [← SimpleFunc.iSup_eapprox_apply hv.measurable_mk x]
          exact le_iSup (fun n => (SimpleFunc.eapprox (hv.mk v) n) x) n
        _ = v x := hx.symm
    have hg_le_v : (g x : ℝ≥0∞) ≤ v x := by
      calc
        (g x : ℝ≥0∞) ≤ (φn x : ℝ≥0∞) := by exact_mod_cast hg_le x
        _ = φ x := congr_fun hφn_coe x
        _ ≤ v x := hφ_le_v
    simpa [u, v, one_div] using
      (ENNReal.rpow_inv_le_iff (by norm_num : (0 : ℝ) < 2)).2 hg_le_v
  · intro hzero
    have hzero_g : (∫⁻ x, (g x : ℝ≥0∞) ∂μ) = 0 := by
      rw [hu_sq] at hzero
      exact hzero
    have hL_zero : L < 0 := by
      rw [hzero_g] at hL_lt_g
      exact hL_lt_g
    exact (not_lt_of_ge (zero_le L)) hL_zero
  · rw [hu_sq]
    exact hg_int_lt_top.ne
  · have h_eLpNorm_u :
        eLpNorm u (ENNReal.ofReal (2 : ℝ)) μ
          = (∫⁻ x, (g x : ℝ≥0∞) ∂μ) ^ (1 / (2 : ℝ)) := by
      rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top]
      simp [u, enorm_eq_self, one_div,
        ENNReal.rpow_inv_rpow (by norm_num : (2 : ℝ) ≠ 0)]
    rw [h_eLpNorm_u]
    by_contra hnot
    have hroot_le : (∫⁻ x, (g x : ℝ≥0∞) ∂μ) ^ (1 / (2 : ℝ)) ≤ B :=
      le_of_not_gt hnot
    have hint_le : (∫⁻ x, (g x : ℝ≥0∞) ∂μ) ≤ B ^ (2 : ℝ) :=
      (ENNReal.rpow_inv_le_iff (by norm_num : (0 : ℝ) < 2)).1 (by
        simpa [one_div] using hroot_le)
    exact (not_lt_of_ge hint_le) (by simpa [L] using hL_lt_g)

/-- The p=2 duality top edge follows from finite-piece exhaustion.  The proof
uses the checked positive finite p=2 duality equality on each finite piece, then
monotonicity of the pairing under `u ≤ f` to lift arbitrarily large witnesses
to the original infinite-norm function. -/
theorem eLpNorm_two_duality_top_edge_of_finite_piece_exhaustion
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ]
    (h_exhaust : eLpNorm_two_finite_piece_exhaustion μ) :
    eLpNorm_two_duality_top_edge μ := by
  intro f hf htop
  refine (iSup_eq_top _).2 ?_
  intro B hB
  rcases h_exhaust hf htop hB with
    ⟨u, hu_meas, hu_le_f, hu_sq_ne_zero, hu_sq_ne_top, hB_lt_u⟩
  have h_dual_u :=
    eLpNorm_two_eq_iSup_lintegral_mul_of_lintegral_rpow_ne_zero_ne_top
      (μ := μ) (f := u) hu_meas hu_sq_ne_zero hu_sq_ne_top
  have hB_lt_sup_u :
      B <
        (⨆ g : { g : α → ℝ≥0∞ //
                  AEMeasurable g μ ∧
                  eLpNorm g (ENNReal.ofReal (2 : ℝ)) μ ≤ 1 },
            ∫⁻ x, u x * (g.val x) ∂μ) := by
    simpa [← h_dual_u] using hB_lt_u
  rw [lt_iSup_iff] at hB_lt_sup_u
  rcases hB_lt_sup_u with ⟨g, hB_lt_pair_u⟩
  refine ⟨g, hB_lt_pair_u.trans_le ?_⟩
  exact lintegral_mono_ae <| hu_le_f.mono fun x hx =>
    mul_le_mul' hx (le_refl (g.val x))

/-- The p=2 duality top edge holds on sigma-finite measure spaces. -/
theorem eLpNorm_two_duality_top_edge_sigmaFinite
    {α : Type*} [MeasurableSpace α] (μ : Measure α) [SigmaFinite μ] :
    eLpNorm_two_duality_top_edge μ :=
  eLpNorm_two_duality_top_edge_of_finite_piece_exhaustion μ
    (eLpNorm_two_finite_piece_exhaustion_sigmaFinite μ)

/-- The continuous-Minkowski top-edge follows from the p=2 `eLpNorm`
duality infinite-edge theorem.  The proof is the top-edge analogue of the
finite p=2 slice: dualize the left function `x ↦ ∫⁻ y, F x y`, swap the
pairing through Tonelli, then apply the checked Hölder/eLpNorm forward bound
to each fibre. -/
theorem eLpNorm_two_lintegral_minkowski_top_edge_of_duality_top_edge
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SigmaFinite μ] [SFinite ν]
    (h_dual_top : eLpNorm_two_duality_top_edge μ) :
    eLpNorm_two_lintegral_minkowski_top_edge μ ν := by
  intro F hF h_left_top
  let f0 : α → ℝ≥0∞ := fun x => ∫⁻ y, F x y ∂ν
  have hf0_meas : AEMeasurable f0 μ := by
    simpa [f0] using hF.lintegral_prod_right
  have hp_ne_zero : ENNReal.ofReal (2 : ℝ) ≠ 0 := by norm_num
  have hp_ne_top : ENNReal.ofReal (2 : ℝ) ≠ ∞ := by simp
  have h_toReal : (ENNReal.ofReal (2 : ℝ)).toReal = (2 : ℝ) := by norm_num
  have hf0_top : eLpNorm f0 (ENNReal.ofReal (2 : ℝ)) μ = ∞ := by
    rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top, h_toReal]
    have h_inner :
        (∫⁻ x, ‖f0 x‖ₑ ^ (2 : ℝ) ∂μ)
          = ∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ := by
      simp [f0, enorm_eq_self]
    rw [h_inner, h_left_top]
    exact ENNReal.top_rpow_of_pos (by norm_num : (0 : ℝ) < 1 / 2)
  have h_sup_top :
      (⨆ g : { g : α → ℝ≥0∞ //
              AEMeasurable g μ ∧
              eLpNorm g (ENNReal.ofReal (2 : ℝ)) μ ≤ 1 },
        ∫⁻ x, f0 x * (g.val x) ∂μ) = ∞ :=
    h_dual_top hf0_meas hf0_top
  have h_fiber_meas : ∀ᵐ y ∂ν, AEMeasurable (fun x => F x y) μ := by
    filter_upwards [hF.aestronglyMeasurable.prodMk_right] with y hy
    simpa [Function.uncurry] using hy.aemeasurable
  have h_sup_le :
      (⨆ g : { g : α → ℝ≥0∞ //
              AEMeasurable g μ ∧
              eLpNorm g (ENNReal.ofReal (2 : ℝ)) μ ≤ 1 },
        ∫⁻ x, f0 x * (g.val x) ∂μ)
        ≤ ∫⁻ y, eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
    refine iSup_le ?_
    intro g
    have hg_meas : AEMeasurable g.val μ := g.property.1
    have hg_norm : eLpNorm g.val (ENNReal.ofReal (2 : ℝ)) μ ≤ 1 := g.property.2
    have h_prod_meas :
        AEMeasurable (Function.uncurry fun x y => F x y * g.val x) (μ.prod ν) := by
      exact hF.mul hg_meas.comp_fst
    calc
      ∫⁻ x, f0 x * g.val x ∂μ
          ≤ ∫⁻ x, ∫⁻ y, F x y * g.val x ∂ν ∂μ := by
            apply lintegral_mono
            intro x
            simpa [f0] using lintegral_mul_const_le (g.val x) (fun y => F x y)
      _ = ∫⁻ y, ∫⁻ x, F x y * g.val x ∂μ ∂ν := by
            exact lintegral_lintegral_swap h_prod_meas
      _ ≤ ∫⁻ y, eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
            apply lintegral_mono_ae
            filter_upwards [h_fiber_meas] with y hy
            have h_pair :
                ∫⁻ x, F x y * g.val x ∂μ
                  ≤ eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ *
                      eLpNorm g.val (ENNReal.ofReal (2 : ℝ)) μ :=
              lintegral_mul_le_eLpNorm_mul_eLpNorm_ennreal
                Real.HolderConjugate.two_two hy hg_meas
            calc
              ∫⁻ x, F x y * g.val x ∂μ
                  ≤ eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ *
                      eLpNorm g.val (ENNReal.ofReal (2 : ℝ)) μ := h_pair
              _ ≤ eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ * 1 := by
                    exact mul_le_mul' le_rfl hg_norm
              _ = eLpNorm (fun x => F x y) (ENNReal.ofReal (2 : ℝ)) μ := by
                    rw [mul_one]
  exact top_unique (h_sup_top ▸ h_sup_le)

/-- The continuous-Minkowski top edge holds whenever the left measure is
sigma-finite and the parameter measure is s-finite. -/
theorem eLpNorm_two_lintegral_minkowski_top_edge_sigmaFinite
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SigmaFinite μ] [SFinite ν] :
    eLpNorm_two_lintegral_minkowski_top_edge μ ν :=
  eLpNorm_two_lintegral_minkowski_top_edge_of_duality_top_edge μ ν
    (eLpNorm_two_duality_top_edge_sigmaFinite μ)

/-- The no-side-condition p=2 nonnegative continuous-Minkowski inequality
follows from its top-edge theorem.  The finite nonzero case is the already
checked p=2 product-measurable slice; the zero case is paid by unfolding
`eLpNorm`; the infinite case is exactly `h_top`. -/
theorem eLpNorm_two_lintegral_minkowski_inequality_of_top_edge
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SFinite μ] [SFinite ν]
    (h_top : eLpNorm_two_lintegral_minkowski_top_edge μ ν) :
    eLpNorm_two_lintegral_minkowski_inequality μ ν := by
  intro F hF
  let A : ℝ≥0∞ := ∫⁻ x, (∫⁻ y, F x y ∂ν) ^ (2 : ℝ) ∂μ
  by_cases hA_top : A = ∞
  · have h_rhs_top :
        (∫⁻ y, eLpNorm (fun x => F x y)
          (ENNReal.ofReal (2 : ℝ)) μ ∂ν) = ∞ :=
      h_top hF (by simpa [A] using hA_top)
    rw [h_rhs_top]
    exact le_top
  · by_cases hA_zero : A = 0
    · have hp_ne_zero : ENNReal.ofReal (2 : ℝ) ≠ 0 := by norm_num
      have hp_ne_top : ENNReal.ofReal (2 : ℝ) ≠ ∞ := by simp
      have h_eLpNorm_zero :
          eLpNorm (fun x => ∫⁻ y, F x y ∂ν)
            (ENNReal.ofReal (2 : ℝ)) μ = 0 := by
        rw [eLpNorm_eq_lintegral_rpow_enorm_toReal hp_ne_zero hp_ne_top]
        have h_inner :
            (∫⁻ x,
              ‖(∫⁻ y, F x y ∂ν)‖ₑ ^
                (ENNReal.ofReal (2 : ℝ)).toReal ∂μ) = A := by
          simp [A, enorm_eq_self]
        rw [h_inner, hA_zero]
        simp
      rw [h_eLpNorm_zero]
      exact zero_le _
    · exact
        eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_product_meas
          hF (by simpa [A] using hA_zero) (by simpa [A] using hA_top)

/-- The no-side-condition p=2 nonnegative continuous-Minkowski inequality holds
on sigma-finite left measure spaces and s-finite parameter measure spaces. -/
theorem eLpNorm_two_lintegral_minkowski_inequality_sigmaFinite
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SigmaFinite μ] [SFinite ν] :
    eLpNorm_two_lintegral_minkowski_inequality μ ν :=
  eLpNorm_two_lintegral_minkowski_inequality_of_top_edge μ ν
    (eLpNorm_two_lintegral_minkowski_top_edge_sigmaFinite μ ν)

/-- The finiteness-only bridge follows immediately from the corresponding
no-side-condition p=2 nonnegative continuous-Minkowski inequality. -/
theorem eLpNorm_two_lintegral_finiteness_bridge_of_minkowski_inequality
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SFinite μ] [SFinite ν]
    (hM : eLpNorm_two_lintegral_minkowski_inequality μ ν) :
    eLpNorm_two_lintegral_finiteness_bridge μ ν := by
  intro F hF h_rhs
  have h_eLpNorm :
      eLpNorm (fun x => ∫⁻ y, F x y ∂ν)
        (ENNReal.ofReal (2 : ℝ)) μ < ∞ :=
    lt_of_le_of_lt (hM hF) h_rhs
  have hp_ne_zero : ENNReal.ofReal (2 : ℝ) ≠ 0 := by norm_num
  have hp_ne_top : ENNReal.ofReal (2 : ℝ) ≠ ∞ := by simp
  have h_lintegral :
      (∫⁻ x,
        ‖(∫⁻ y, F x y ∂ν)‖ₑ ^
          (ENNReal.ofReal (2 : ℝ)).toReal ∂μ) < ∞ :=
    (eLpNorm_lt_top_iff_lintegral_rpow_enorm_lt_top
      hp_ne_zero hp_ne_top).1 h_eLpNorm
  simpa [enorm_eq_self] using h_lintegral

/-- The finiteness-only p=2 continuous-Minkowski bridge holds on sigma-finite
left measure spaces and s-finite parameter measure spaces. -/
theorem eLpNorm_two_lintegral_finiteness_bridge_sigmaFinite
    {α β : Type*} [MeasurableSpace α] [MeasurableSpace β]
    (μ : Measure α) (ν : Measure β) [SigmaFinite μ] [SFinite ν] :
    eLpNorm_two_lintegral_finiteness_bridge μ ν :=
  eLpNorm_two_lintegral_finiteness_bridge_of_minkowski_inequality μ ν
    (eLpNorm_two_lintegral_minkowski_inequality_sigmaFinite μ ν)

/-- **Conditional discharge of the real-line `h_left_nontop` source
obligation from the finiteness-only p=2 continuous Minkowski bridge.**
Together with `rhs_lintegral_translate_diff_lt_top_real_of_memLp_two`,
this theorem pins the remaining source obligation exactly: prove
`eLpNorm_two_lintegral_finiteness_bridge`, and the left majorant finiteness
needed by `eLpNorm_two_convolution_sub_le_lintegral_translate_diff` follows. -/
theorem left_majorant_nontop_convolution_diff_kernel_real_of_finiteness_bridge
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (h_bridge :
      eLpNorm_two_lintegral_finiteness_bridge
        (volume : Measure ℝ) (volume : Measure ℝ))
    (hρ_int : Integrable ρ (volume : Measure ℝ))
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
        ((volume : Measure ℝ).prod (volume : Measure ℝ))) :
    (∫⁻ x : ℝ,
      (∫⁻ y : ℝ, ‖ρ y • (f (x - y) - f x)‖ₑ ∂volume) ^ (2 : ℝ)
        ∂volume) ≠ ⊤ := by
  let F : ℝ → ℝ → ℝ≥0∞ :=
    fun x y => ‖ρ y • (f (x - y) - f x)‖ₑ
  have hF_meas : AEMeasurable (Function.uncurry F)
      ((volume : Measure ℝ).prod (volume : Measure ℝ)) := by
    simpa [F, Function.uncurry] using h_diff_meas.enorm
  have h_rhs :
      (∫⁻ y : ℝ, eLpNorm (fun x : ℝ => F x y)
        (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume) < ∞ := by
    have h_base :=
      rhs_lintegral_translate_diff_lt_top_real_of_memLp_two
        (E := E) (ρ := ρ) (f := f) hρ_int hf
    have h_eq :
        (∫⁻ y : ℝ, eLpNorm (fun x : ℝ => F x y)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume)
        =
        (∫⁻ y : ℝ,
          ‖ρ y‖ₑ *
            eLpNorm (fun x : ℝ => f (x - y) - f x)
              (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume) := by
      apply lintegral_congr
      intro y
      rw [show (fun x : ℝ => F x y) =
          (fun x : ℝ => ‖ρ y • (f (x - y) - f x)‖ₑ) from rfl,
        eLpNorm_enorm]
      rw [show (fun x : ℝ => ρ y • (f (x - y) - f x)) =
          (ρ y) • (fun x : ℝ => f (x - y) - f x) from rfl,
        eLpNorm_const_smul]
    rwa [h_eq]
  exact (h_bridge (F := F) hF_meas h_rhs).ne

/-- **Real-line `h_left_nontop` source obligation.**
The p=2 continuous-Minkowski finiteness bridge is now available from the
sigma-finite top-edge chain, so the real convolution-difference left majorant
finiteness condition follows directly from `MemLp f 2` and the existing RHS
majorant theorem. -/
theorem left_majorant_nontop_convolution_diff_kernel_real
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (hρ_int : Integrable ρ (volume : Measure ℝ))
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
        ((volume : Measure ℝ).prod (volume : Measure ℝ))) :
    (∫⁻ x : ℝ,
      (∫⁻ y : ℝ, ‖ρ y • (f (x - y) - f x)‖ₑ ∂volume) ^ (2 : ℝ)
        ∂volume) ≠ ⊤ :=
  left_majorant_nontop_convolution_diff_kernel_real_of_finiteness_bridge
    (eLpNorm_two_lintegral_finiteness_bridge_sigmaFinite
      (volume : Measure ℝ) (volume : Measure ℝ))
    hρ_int hf h_diff_meas

/-- **No-side-condition p=2 Bochner/vector continuous-Minkowski slice.**
The sigma-finite top-edge chain removes the old positive/finite side
conditions from the vector-valued p=2 slice. -/
theorem eLpNorm_two_integral_le_lintegral_eLpNorm_sigmaFinite
    {α β E : Type*} [MeasurableSpace α] [MeasurableSpace β]
    [NormedAddCommGroup E] [NormedSpace ℝ E]
    {μ : Measure α} {ν : Measure β} [SigmaFinite μ] [SFinite ν]
    {G : α → β → E}
    (hG_meas : AEStronglyMeasurable (Function.uncurry G) (μ.prod ν))
    (hG_int : ∀ᵐ x ∂μ, Integrable (fun y => G x y) ν) :
    eLpNorm (fun x => ∫ y, G x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, eLpNorm (fun x => G x y) (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
  have h_pointwise :
      ∀ᵐ x ∂μ, ‖∫ y, G x y ∂ν‖ₑ ≤ ∫⁻ y, ‖G x y‖ₑ ∂ν := by
    filter_upwards [hG_int] with x _hx
    exact enorm_integral_le_lintegral_enorm (fun y => G x y)
  have h_pointwise_enorm :
      ∀ᵐ x ∂μ,
        ‖∫ y, G x y ∂ν‖ₑ ≤ ‖(∫⁻ y, ‖G x y‖ₑ ∂ν)‖ₑ := by
    filter_upwards [h_pointwise] with x hx
    simpa [enorm_eq_self] using hx
  have h_lhs_bound :
      eLpNorm (fun x => ∫ y, G x y ∂ν) (ENNReal.ofReal (2 : ℝ)) μ
        ≤ eLpNorm (fun x => ∫⁻ y, ‖G x y‖ₑ ∂ν)
            (ENNReal.ofReal (2 : ℝ)) μ :=
    eLpNorm_mono_enorm_ae h_pointwise_enorm
  have hF_meas :
      AEMeasurable (Function.uncurry fun x y => ‖G x y‖ₑ) (μ.prod ν) := by
    simpa [Function.uncurry] using hG_meas.enorm
  have h_nonneg :
      eLpNorm (fun x => ∫⁻ y, ‖G x y‖ₑ ∂ν)
          (ENNReal.ofReal (2 : ℝ)) μ
        ≤ ∫⁻ y, eLpNorm (fun x => ‖G x y‖ₑ)
            (ENNReal.ofReal (2 : ℝ)) μ ∂ν :=
    eLpNorm_two_lintegral_minkowski_inequality_sigmaFinite μ ν hF_meas
  have h_rhs_eq :
      (∫⁻ y, eLpNorm (fun x => ‖G x y‖ₑ)
          (ENNReal.ofReal (2 : ℝ)) μ ∂ν)
        = ∫⁻ y, eLpNorm (fun x => G x y)
          (ENNReal.ofReal (2 : ℝ)) μ ∂ν := by
    apply lintegral_congr_ae
    filter_upwards with y
    rw [eLpNorm_enorm]
  exact h_lhs_bound.trans (h_nonneg.trans_eq h_rhs_eq)

/-- **No-side-condition p=2 convolution-rate specialization.**
This consumes the no-side-condition vector slice, so no positive/finite
left-majorant hypotheses remain in the theorem statement. -/
theorem eLpNorm_two_convolution_sub_le_lintegral_translate_diff_sigmaFinite
    [CompleteSpace E]
    {G : Type*} [MeasurableSpace G] [Sub G]
    {μ : Measure G} [SigmaFinite μ]
    {ρ : G → ℝ} (hρ_int : Integrable ρ μ)
    (hρ_one : ∫ y, ρ y ∂μ = 1)
    {f : G → E}
    (h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x)) (μ.prod μ))
    (h_conv_int : ∀ᵐ x ∂μ, Integrable (fun y => ρ y • f (x - y)) μ)
    (h_diff_int :
      ∀ᵐ x ∂μ, Integrable (fun y => ρ y • (f (x - y) - f x)) μ) :
    eLpNorm
        (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x)
        (ENNReal.ofReal (2 : ℝ)) μ
      ≤ ∫⁻ y, ‖ρ y‖ₑ *
          eLpNorm (fun x => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) μ ∂μ := by
  have h_rewrite_ae :
      (fun x => (∫ y, ρ y • f (x - y) ∂μ) - f x)
        =ᵐ[μ] (fun x => ∫ y, ρ y • (f (x - y) - f x) ∂μ) := by
    filter_upwards [h_conv_int] with x hx
    exact convolution_sub_eq_integral_translate_diff_aux
      hρ_int hρ_one x hx
  rw [eLpNorm_congr_ae h_rewrite_ae]
  have h_step :
      eLpNorm
          (fun x => ∫ y, ρ y • (f (x - y) - f x) ∂μ)
          (ENNReal.ofReal (2 : ℝ)) μ
        ≤ ∫⁻ y,
            eLpNorm (fun x => ρ y • (f (x - y) - f x))
              (ENNReal.ofReal (2 : ℝ)) μ ∂μ :=
    eLpNorm_two_integral_le_lintegral_eLpNorm_sigmaFinite
      h_diff_meas h_diff_int
  refine h_step.trans ?_
  apply lintegral_mono_ae
  filter_upwards with y
  rw [show (fun x => ρ y • (f (x - y) - f x)) =
      (ρ y) • (fun x => f (x - y) - f x) from rfl,
      eLpNorm_const_smul]

/-- **Real-volume p=2 convolution-rate theorem for compact kernels.**
This composes all paid real source obligations: product measurability, fibre
integrability, and the no-side-condition p=2 continuous-Minkowski chain. -/
theorem eLpNorm_two_convolution_sub_le_lintegral_translate_diff_real
    {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : Continuous ρ) (hρ_comp : HasCompactSupport ρ)
    (hρ_int : Integrable ρ (volume : Measure ℝ))
    (hρ_one : ∫ y, ρ y ∂volume = 1)
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)) :
    eLpNorm
        (fun x : ℝ => (∫ y, ρ y • f (x - y) ∂volume) - f x)
        (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
      ≤ ∫⁻ y : ℝ, ‖ρ y‖ₑ *
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume := by
  have h_diff_meas :
      AEStronglyMeasurable
        (Function.uncurry fun x y => ρ y • (f (x - y) - f x))
        ((volume : Measure ℝ).prod (volume : Measure ℝ)) :=
    aestronglyMeasurable_convolution_diff_kernel_real_volume
      hρ_int.aemeasurable hf.aestronglyMeasurable
  have h_diff_int :
      ∀ᵐ x : ℝ ∂volume,
        Integrable (fun y : ℝ => ρ y • (f (x - y) - f x)) (volume : Measure ℝ) :=
    Filter.Eventually.of_forall fun x =>
      integrable_fibre_convolution_diff_kernel_real_of_memLp_two
        hρ_cont hρ_comp hf x
  have h_conv_int :
      ∀ᵐ x : ℝ ∂volume,
        Integrable (fun y : ℝ => ρ y • f (x - y)) (volume : Measure ℝ) := by
    filter_upwards [h_diff_int] with x hx_diff
    have hx_const : Integrable (fun y : ℝ => ρ y • f x) (volume : Measure ℝ) :=
      hρ_int.smul_const (f x)
    refine (hx_diff.add hx_const).congr ?_
    filter_upwards with y
    simp [smul_sub]
  exact
    eLpNorm_two_convolution_sub_le_lintegral_translate_diff_sigmaFinite
      (μ := (volume : Measure ℝ)) hρ_int hρ_one
      h_diff_meas h_conv_int h_diff_int

/-- **p=2 real mollifier-limit reduction.**
For any family of continuous compactly supported unit-mass kernels, if the
checked convolution-rate right-hand side tends to zero, then the corresponding
p=2 convolution error tends to zero.  This is the exact limit-passage consumer
of the real compact-kernel convolution-rate theorem; the remaining source
problem is proving the RHS tends to zero from approximate-identity hypotheses
and PR1 translation continuity. -/
theorem eLpNorm_two_real_mollifier_limit_of_rhs_tendsto_zero
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : ∀ i, Continuous (ρ i))
    (hρ_comp : ∀ i, HasCompactSupport (ρ i))
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1)
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_rhs :
      Tendsto
        (fun i =>
          ∫⁻ y : ℝ, ‖ρ i y‖ₑ *
            eLpNorm (fun x : ℝ => f (x - y) - f x)
              (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume)
        l (𝓝 0)) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ => (∫ y, ρ i y • f (x - y) ∂volume) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
      l (𝓝 0) := by
  refine tendsto_of_tendsto_of_tendsto_of_le_of_le
    (g := fun _ : ι => (0 : ℝ≥0∞))
    (h := fun i =>
      ∫⁻ y : ℝ, ‖ρ i y‖ₑ *
        eLpNorm (fun x : ℝ => f (x - y) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume)
    tendsto_const_nhds h_rhs (fun i => ?_) (fun i => ?_)
  · exact zero_le _
  · exact
      eLpNorm_two_convolution_sub_le_lintegral_translate_diff_real
        (hρ_cont i) (hρ_comp i) (hρ_int i) (hρ_one i) hf

/-- **p=2 real RHS convergence from an abstract concentration functional.**
This is the exact `RHS -> 0` source surface for the real compact-kernel
convolution-rate theorem.  The hypothesis `h_concentration` is deliberately
abstract: it is the near/far approximate-identity statement that remains to be
proved from concrete tail-mass assumptions. -/
theorem eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_concentration
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E}
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_mod :
      Tendsto
        (fun y : ℝ =>
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
        (𝓝 0) (𝓝 0))
    (h_concentration :
      ∀ ω : ℝ → ℝ≥0∞,
        Tendsto ω (𝓝 0) (𝓝 0) →
        (∃ M : ℝ≥0∞, M ≠ ∞ ∧ ∀ y : ℝ, ω y ≤ M) →
        Tendsto
          (fun i : ι => ∫⁻ y : ℝ, ‖ρ i y‖ₑ * ω y ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i : ι =>
        ∫⁻ y : ℝ, ‖ρ i y‖ₑ *
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume)
      l (𝓝 0) := by
  let ω : ℝ → ℝ≥0∞ := fun y =>
    eLpNorm (fun x : ℝ => f (x - y) - f x)
      (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
  have hω_tendsto : Tendsto ω (𝓝 0) (𝓝 0) := h_mod
  have hω_bound : ∃ M : ℝ≥0∞, M ≠ ∞ ∧ ∀ y : ℝ, ω y ≤ M := by
    refine
      ⟨eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
          eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ), ?_, ?_⟩
    · exact ENNReal.add_ne_top.2 ⟨hf.eLpNorm_ne_top, hf.eLpNorm_ne_top⟩
    · exact eLpNorm_two_translate_diff_le_real_of_memLp_two hf
  exact h_concentration ω hω_tendsto hω_bound

/-- **p=2 real mollifier-limit theorem from abstract concentration.**
This composes the checked real compact-kernel convolution-rate theorem with
the exact RHS concentration source above.  The remaining formalization-bound
target is to prove `h_concentration` from explicit approximate-identity
tail-mass hypotheses. -/
theorem eLpNorm_two_real_mollifier_limit_of_concentration
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : ∀ i, Continuous (ρ i))
    (hρ_comp : ∀ i, HasCompactSupport (ρ i))
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1)
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_mod :
      Tendsto
        (fun y : ℝ =>
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
        (𝓝 0) (𝓝 0))
    (h_concentration :
      ∀ ω : ℝ → ℝ≥0∞,
        Tendsto ω (𝓝 0) (𝓝 0) →
        (∃ M : ℝ≥0∞, M ≠ ∞ ∧ ∀ y : ℝ, ω y ≤ M) →
        Tendsto
          (fun i : ι => ∫⁻ y : ℝ, ‖ρ i y‖ₑ * ω y ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ => (∫ y, ρ i y • f (x - y) ∂volume) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
      l (𝓝 0) :=
  eLpNorm_two_real_mollifier_limit_of_rhs_tendsto_zero
    hρ_cont hρ_comp hρ_int hρ_one hf
    (eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_concentration
      hf h_mod h_concentration)

/-- **p=2 real RHS convergence from concrete near/far weight hypotheses.**
This instantiates the abstract concentration source with weights
`w_i(y) = ‖ρ_i(y)‖ₑ`.  The remaining analytic input is only the real RHS
modulus continuity `h_mod`. -/
theorem eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E} {B : ℝ≥0∞}
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_mod :
      Tendsto
        (fun y : ℝ =>
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
        (𝓝 0) (𝓝 0))
    (h_mass_bound :
      ∀ᶠ i in l, (∫⁻ y : ℝ, ‖ρ i y‖ₑ ∂volume) ≤ B)
    (hB_ne_top : B ≠ ∞)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i : ι =>
        ∫⁻ y : ℝ, ‖ρ i y‖ₑ *
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) ∂volume)
      l (𝓝 0) := by
  let M : ℝ≥0∞ :=
    eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ) +
      eLpNorm f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ)
  have hM_ne_top : M ≠ ∞ :=
    ENNReal.add_ne_top.2 ⟨hf.eLpNorm_ne_top, hf.eLpNorm_ne_top⟩
  exact
    mollifier_concentration_near_far_enorm_real
      (w := fun i y => ‖ρ i y‖ₑ)
      (ω := fun y : ℝ =>
        eLpNorm (fun x : ℝ => f (x - y) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
      (M := M) (B := B)
      h_mod (eLpNorm_two_translate_diff_le_real_of_memLp_two hf)
      hM_ne_top h_mass_bound hB_ne_top h_tail

/-- **p=2 real mollifier-limit theorem from concrete near/far weight hypotheses.**
This composes the checked real compact-kernel convolution-rate theorem with the
near/far concentration source theorem. -/
theorem eLpNorm_two_real_mollifier_limit_of_near_far
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E} {B : ℝ≥0∞}
    (hρ_cont : ∀ i, Continuous (ρ i))
    (hρ_comp : ∀ i, HasCompactSupport (ρ i))
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1)
    (hf : MemLp f (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
    (h_mod :
      Tendsto
        (fun y : ℝ =>
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
        (𝓝 0) (𝓝 0))
    (h_mass_bound :
      ∀ᶠ i in l, (∫⁻ y : ℝ, ‖ρ i y‖ₑ ∂volume) ≤ B)
    (hB_ne_top : B ≠ ∞)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ => (∫ y, ρ i y • f (x - y) ∂volume) - f x)
          (ENNReal.ofReal (2 : ℝ)) (volume : Measure ℝ))
      l (𝓝 0) :=
  eLpNorm_two_real_mollifier_limit_of_rhs_tendsto_zero
    hρ_cont hρ_comp hρ_int hρ_one hf
    (eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far
      hf h_mod h_mass_bound hB_ne_top h_tail)

/-- **p=2 real RHS convergence from near/far hypotheses and PR1.**
This is the first fully-assembled real-line RHS source: the translation
modulus is supplied by PR1 through the one-dimensional bridge above. -/
theorem eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far_memLp
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E]
    [MeasurableSpace E] [BorelSpace E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E} {B : ℝ≥0∞}
    (hf : MemLp f p2 (volume : Measure ℝ))
    (h_mass_bound :
      ∀ᶠ i in l, (∫⁻ y : ℝ, ‖ρ i y‖ₑ ∂volume) ≤ B)
    (hB_ne_top : B ≠ ∞)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i : ι =>
        ∫⁻ y : ℝ, ‖ρ i y‖ₑ *
          eLpNorm (fun x : ℝ => f (x - y) - f x)
            p2 (volume : Measure ℝ) ∂volume)
      l (𝓝 0) :=
  eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far
    hf (tendsto_eLpNorm_translate_diff_sub_zero_real_of_memLp_two hf)
    h_mass_bound hB_ne_top h_tail

/-- **p=2 real mollifier limit from near/far hypotheses and PR1.**
This composes the checked compact-kernel convolution-rate theorem, PR1
translation continuity on the real line, and the concrete near/far
concentration source. -/
theorem eLpNorm_two_real_mollifier_limit_of_near_far_memLp
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E} {B : ℝ≥0∞}
    (hρ_cont : ∀ i, Continuous (ρ i))
    (hρ_comp : ∀ i, HasCompactSupport (ρ i))
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1)
    (hf : MemLp f p2 (volume : Measure ℝ))
    (h_mass_bound :
      ∀ᶠ i in l, (∫⁻ y : ℝ, ‖ρ i y‖ₑ ∂volume) ≤ B)
    (hB_ne_top : B ≠ ∞)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ => (∫ y, ρ i y • f (x - y) ∂volume) - f x)
          p2 (volume : Measure ℝ))
      l (𝓝 0) :=
  eLpNorm_two_real_mollifier_limit_of_near_far
    hρ_cont hρ_comp hρ_int hρ_one hf
    (tendsto_eLpNorm_translate_diff_sub_zero_real_of_memLp_two hf)
    h_mass_bound hB_ne_top h_tail

/-- **Total variation mass of a nonnegative unit-mass real kernel.**
For nonnegative real kernels, the weighted mass appearing in the near/far
theorem is exactly the Bochner integral mass. -/
theorem lintegral_enorm_eq_one_of_nonneg_integral_one
    {ρ : ℝ → ℝ}
    (hρ_int : Integrable ρ (volume : Measure ℝ))
    (hρ_nonneg : ∀ y : ℝ, 0 ≤ ρ y)
    (hρ_one : ∫ y, ρ y ∂volume = 1) :
    (∫⁻ y : ℝ, ‖ρ y‖ₑ ∂volume) = 1 := by
  rw [lintegral_enorm_of_nonneg hρ_nonneg]
  rw [← ofReal_integral_eq_lintegral_ofReal
    hρ_int (Filter.Eventually.of_forall hρ_nonneg), hρ_one]
  norm_num

/-- **Eventual total-mass bound from nonnegative unit-mass kernels.**
This pays the `B = 1` mass hypothesis in the near/far concentration theorem. -/
theorem mollifier_total_mass_bound_one_of_nonneg_unit
    {ι : Type*} {l : Filter ι} {ρ : ι → ℝ → ℝ}
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_nonneg : ∀ i y, 0 ≤ ρ i y)
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1) :
    ∀ᶠ i in l, (∫⁻ y : ℝ, ‖ρ i y‖ₑ ∂volume) ≤ (1 : ℝ≥0∞) :=
  Filter.Eventually.of_forall fun i =>
    le_of_eq (lintegral_enorm_eq_one_of_nonneg_integral_one
      (hρ_int i) (hρ_nonneg i) (hρ_one i))

/-- **p=2 real mollifier limit from nonnegative unit mass and tail concentration.**
The remaining approximate-identity input is now only the tail concentration
outside every fixed ball. -/
theorem eLpNorm_two_real_mollifier_limit_of_nonneg_unit_tail_memLp
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : ∀ i, Continuous (ρ i))
    (hρ_comp : ∀ i, HasCompactSupport (ρ i))
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_nonneg : ∀ i y, 0 ≤ ρ i y)
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1)
    (hf : MemLp f p2 (volume : Measure ℝ))
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          l (𝓝 0)) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ => (∫ y, ρ i y • f (x - y) ∂volume) - f x)
          p2 (volume : Measure ℝ))
      l (𝓝 0) :=
  eLpNorm_two_real_mollifier_limit_of_near_far_memLp
    hρ_cont hρ_comp hρ_int hρ_one hf
    (mollifier_total_mass_bound_one_of_nonneg_unit hρ_int hρ_nonneg hρ_one)
    (by simp) h_tail

/-- **Tail concentration from eventual support inside every fixed ball.**
If the kernels are eventually zero outside each fixed ball around the origin,
then their ENNReal tail mass outside that ball tends to zero. -/
theorem mollifier_tail_tendsto_zero_of_eventually_zero_off_ball
    {ι : Type*} {l : Filter ι} {ρ : ι → ℝ → ℝ}
    (h_support :
      ∀ δ : ℝ, 0 < δ →
        ∀ᶠ i in l, ∀ y : ℝ, δ ≤ ‖y‖ → ρ i y = 0) :
    ∀ δ : ℝ, 0 < δ →
      Tendsto
        (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
        l (𝓝 0) := by
  intro δ hδ
  have h_zero :
      ∀ᶠ i in l,
        (∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume) = 0 := by
    filter_upwards [h_support δ hδ] with i hi
    calc
      (∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          = (∫⁻ _y in {y : ℝ | δ ≤ ‖y‖}, (0 : ℝ≥0∞) ∂volume) := by
            apply lintegral_congr_ae
            filter_upwards
              [ae_restrict_mem (by measurability :
                MeasurableSet {y : ℝ | δ ≤ ‖y‖})] with y hy
            rw [hi y hy]
            simp
      _ = 0 := by simp
  exact tendsto_nhds_of_eventually_eq h_zero

/-- **p=2 real mollifier limit from support concentration.**
This is the strongest current KRF-facing consumer in this file: nonnegative
unit-mass compact kernels with eventual support inside every fixed ball form an
approximate identity for every `L²` function. -/
theorem eLpNorm_two_real_mollifier_limit_of_nonneg_unit_support_memLp
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    {ρ : ι → ℝ → ℝ} {f : ℝ → E}
    (hρ_cont : ∀ i, Continuous (ρ i))
    (hρ_comp : ∀ i, HasCompactSupport (ρ i))
    (hρ_int : ∀ i, Integrable (ρ i) (volume : Measure ℝ))
    (hρ_nonneg : ∀ i y, 0 ≤ ρ i y)
    (hρ_one : ∀ i, ∫ y, ρ i y ∂volume = 1)
    (hf : MemLp f p2 (volume : Measure ℝ))
    (h_support :
      ∀ δ : ℝ, 0 < δ →
        ∀ᶠ i in l, ∀ y : ℝ, δ ≤ ‖y‖ → ρ i y = 0) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ => (∫ y, ρ i y • f (x - y) ∂volume) - f x)
          p2 (volume : Measure ℝ))
      l (𝓝 0) :=
  eLpNorm_two_real_mollifier_limit_of_nonneg_unit_tail_memLp
    hρ_cont hρ_comp hρ_int hρ_nonneg hρ_one hf
    (mollifier_tail_tendsto_zero_of_eventually_zero_off_ball h_support)

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
| `eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_product_meas` | `theorem` | 0 |
| `eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_ae_fiber_meas` | `theorem` | 0 |
| `eLpNorm_two_lintegral_lintegral_le_lintegral_eLpNorm_of_lintegral_rpow_ne_zero_ne_top` | `theorem` | 0 |
| `eLpNorm_two_integral_le_lintegral_eLpNorm_of_product_meas` | `theorem` | 0 |
| `eLpNorm_two_convolution_sub_le_lintegral_translate_diff` | `theorem` | 0 |
| `aestronglyMeasurable_convolution_diff_kernel_of_map_sub` | `theorem` | 0 |
| `aestronglyMeasurable_convolution_diff_kernel_of_sub_pushforward_ac` | `theorem` | 0 |
| `sub_pushforward_prod_absolutelyContinuous_of_isAddLeftInvariant` | `theorem` | 0 |
| `aestronglyMeasurable_convolution_diff_kernel_of_add_left_invariant_measure` | `theorem` | 0 |
| `map_sub_prod_volume_absolutelyContinuous_real` | `theorem` | 0 |
| `aestronglyMeasurable_convolution_diff_kernel_real_volume` | `theorem` | 0 |
| `locallyIntegrable_sub_left_const_real` | `theorem` | 0 |
| `integrable_fibre_convolution_diff_kernel_real_of_locallyIntegrable` | `theorem` | 0 |
| `integrable_fibre_convolution_diff_kernel_real_of_memLp_two` | `theorem` | 0 |
| `rhs_lintegral_translate_diff_lt_top_real_of_memLp_two` | `theorem` | 0 |
| `eLpNorm_two_lintegral_minkowski_top_edge_of_duality_top_edge` | `theorem` | 0 |
| `eLpNorm_two_duality_top_edge_of_finite_piece_exhaustion` | `theorem` | 0 |
| `eLpNorm_two_finite_piece_exhaustion_of_square_lintegral_exhaustion` | `theorem` | 0 |
| `eLpNorm_two_finite_piece_exhaustion_sigmaFinite` | `theorem` | 0 |
| `eLpNorm_two_duality_top_edge_sigmaFinite` | `theorem` | 0 |
| `eLpNorm_two_lintegral_minkowski_top_edge_sigmaFinite` | `theorem` | 0 |
| `eLpNorm_two_lintegral_minkowski_inequality_of_top_edge` | `theorem` | 0 |
| `eLpNorm_two_lintegral_minkowski_inequality_sigmaFinite` | `theorem` | 0 |
| `eLpNorm_two_lintegral_finiteness_bridge_of_minkowski_inequality` | `theorem` | 0 |
| `eLpNorm_two_lintegral_finiteness_bridge_sigmaFinite` | `theorem` | 0 |
| `left_majorant_nontop_convolution_diff_kernel_real_of_finiteness_bridge` | `theorem` | 0 |
| `left_majorant_nontop_convolution_diff_kernel_real` | `theorem` | 0 |
| `eLpNorm_two_integral_le_lintegral_eLpNorm_sigmaFinite` | `theorem` | 0 |
| `eLpNorm_two_convolution_sub_le_lintegral_translate_diff_sigmaFinite` | `theorem` | 0 |
| `eLpNorm_two_convolution_sub_le_lintegral_translate_diff_real` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_limit_of_rhs_tendsto_zero` | `theorem` | 0 |
| `eLpNorm_two_translate_diff_le_real_of_memLp_two` | `theorem` | 0 |
| `tendsto_eLpNorm_translate_diff_sub_zero_real_of_translateBy` | `theorem` | 0 |
| `mollifier_concentration_near_far_enorm_real` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_concentration` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_limit_of_concentration` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_limit_of_near_far` | `theorem` | 0 |
| `tendsto_eLpNorm_translate_diff_sub_zero_real_of_memLp_two` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_rhs_tendsto_zero_of_near_far_memLp` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_limit_of_near_far_memLp` | `theorem` | 0 |
| `lintegral_enorm_eq_one_of_nonneg_integral_one` | `theorem` | 0 |
| `mollifier_total_mass_bound_one_of_nonneg_unit` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_limit_of_nonneg_unit_tail_memLp` | `theorem` | 0 |
| `mollifier_tail_tendsto_zero_of_eventually_zero_off_ball` | `theorem` | 0 |
| `eLpNorm_two_real_mollifier_limit_of_nonneg_unit_support_memLp` | `theorem` | 0 |
| `eLpNorm_two_lintegral_finiteness_bridge` | `def : Prop` | 0 |
| `eLpNorm_two_lintegral_minkowski_inequality` | `def : Prop` | 0 |
| `eLpNorm_two_lintegral_minkowski_top_edge` | `def : Prop` | 0 |
| `eLpNorm_two_duality_top_edge` | `def : Prop` | 0 |
| `eLpNorm_two_finite_piece_exhaustion` | `def : Prop` | 0 |
| `square_lintegral_finite_subpiece_exhaustion` | `def : Prop` | 0 |
| `MinkowskiIntegralInequalityLp_general`                  | `def : Prop` | 0       |
| `eLpNorm_convolution_sub_le_goal`                        | `def : Prop` | 0       |
| `eLpNorm_convolution_sub_le_pipeline`                    | `def : Prop` | 0       |

**Total `sorry`: 0. New axioms: 0.**

The real `theorem` closures (the `p = 1` Minkowski, the algebraic identity,
the `p = 1` convolution-rate bound, the nonnegative `p = 2`
Minkowski slice under product measurability, its a.e.-fibre variant,
its all-fibre corollary, the `p = 2` Bochner/vector slice, and the
`p = 2` convolution-rate specialization, plus the product-measurability
source helper for the convolution-difference kernel, its abstract
subtraction-pushforward corollary, the general additive left-invariant
transport theorem, the additive left-invariant kernel corollary, the real
Lebesgue subtraction-pushforward transport theorem, and its real-volume
kernel measurability corollary, the real fibre local-integrability source,
the compact-kernel fibre-integrability theorem, its `MemLp p=2` corollary,
the p=2 RHS-majorant finiteness theorem, the reduction from the p=2 top-edge
duality theorem to the continuous-Minkowski top edge, the reduction from
finite-piece exhaustion to the p=2 duality top edge, the reduction from the
continuous-Minkowski top edge to the no-side-condition p=2 nonnegative
continuous-Minkowski
inequality, the reduction from that inequality to the finiteness bridge, the
conditional left-majorant discharge theorem, the pure square-lintegral
finite-subpiece reduction, the LeanMill-discovered sigma-finite finite-piece
theorem, its sigma-finite duality/top-edge/Minkowski/finiteness corollaries,
the direct real-line left-majorant source discharge, the no-side-condition
p=2 vector and convolution wrappers, and the real compact-kernel p=2
convolution-rate theorem, plus the p=2 real mollifier-limit reduction from
RHS majorant convergence to convolution-error convergence). Nine typed-companion `Prop`s
naming the remaining general-`p` and p=2 duality/top-edge bridge chains.
-/

end

end ZtareProofs.SQ3.MLG2
