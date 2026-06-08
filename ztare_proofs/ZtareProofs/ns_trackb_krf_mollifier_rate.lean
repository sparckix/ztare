import Mathlib.Tactic
import Mathlib.Analysis.Calculus.BumpFunction.Basic
import Mathlib.Analysis.Calculus.BumpFunction.Normed
import Mathlib.Analysis.Calculus.BumpFunction.FiniteDimension
import Mathlib.Analysis.Calculus.BumpFunction.Convolution
import Mathlib.Analysis.Convolution
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import Mathlib.MeasureTheory.Measure.Haar.OfBasis
import ZtareProofs.mathlib_pr_drafts.PR_1a_translate_eLpNorm_continuity

/-!
# KRF Phase A: the L² mollifier-rate estimate

This file is **Phase A** of `krf_subseq_ae_of_translation` (see
`ZtareProofs.NS.AubinLions.krf_subseq_ae_of_translation` in
`ns_trackb_aubin_lions_stub.lean`). The audit there pin-points the
missing Mathlib infrastructure for the Kolmogorov–Riesz–Fréchet
compactness theorem; the present file scaffolds the **first** of the
four classical phases needed to discharge it:

> **Phase A.** For `f ∈ L²(ℝⁿ, volume)` and a standard mollifier
> `ρ_δ(x) := δ⁻ⁿ ρ(x/δ)` with `ρ ∈ C_c^∞(ℝⁿ)`, `∫ρ = 1`, `ρ ≥ 0`,
> we have
> `‖ρ_δ * f − f‖_{L²} → 0` as `δ → 0⁺`.
> **Uniformly** for `f` ranging over a translation-equicontinuous
> family in L².

The statement is purely classical (Brezis Ch. 4 / Lieb–Loss Ch. 2).
Mathlib v4.30.0-rc2 has the *pointwise* mollifier–approximation
theorem in `C^0` / `L^∞` (`ContDiffBump.convolution_tendsto_right_of_continuous`)
and a *measure-theoretic* a.e. mollifier-approximation theorem
(`ContDiffBump.ae_convolution_tendsto_right_of_locallyIntegrable`),
but it does **not** ship the L² rate or its uniform-in-family version,
which is what the KRF compactness criterion requires.

We typed-companion the problem here so the architectural shape is
visible and the named-sorry inventory is precise.

## Mathlib status (v4.30.0-rc2, audited 2026-05-07)

PRESENT:
* `ContDiffBump` and `ContDiffBump.normed`
  (`Mathlib/Analysis/Calculus/BumpFunction/Basic.lean` and `Normed.lean`).
* `ContDiffBump.convolution_tendsto_right_of_continuous`
  (`Mathlib/Analysis/Calculus/BumpFunction/Convolution.lean:98`) —
  pointwise mollifier convergence for continuous `g`.
* `ContDiffBump.ae_convolution_tendsto_right_of_locallyIntegrable`
  (`Mathlib/Analysis/Calculus/BumpFunction/Convolution.lean:107`) —
  a.e. mollifier convergence for locally integrable `g`.
* `MeasureTheory.convolution` and the associated calculus
  (`Mathlib/Analysis/Convolution.lean`).
* `MeasureTheory.eLpNorm`, `MeasureTheory.MemLp`
  (`Mathlib/MeasureTheory/Function/LpSeminorm/*` and `LpSpace/*`).
* `MeasureTheory.eLpNorm_eq_lintegral_rpow_enorm_toReal`
  (`Mathlib/MeasureTheory/Function/LpSeminorm/Defs.lean:99`).

ABSENT (each blocks a step of the proof below):
* `MeasureTheory.tendsto_translate_eLpNorm_zero` — L² (or L^p)
  translation continuity:
    `Tendsto (fun h => eLpNorm (fun x => f (x + h) - f x) p μ) (𝓝 0) (𝓝 0)`
  for `f ∈ L^p(volume)` on `ℝⁿ`. Standard textbook lemma; not
  named in Mathlib.
* `MeasureTheory.eLpNorm_convolution_sub_le` — Minkowski's
  integral inequality applied to `ρ_δ * f − f`:
    `eLpNorm (ρ_δ * f − f) p ≤ ∫ ρ_δ(y) * eLpNorm (f(· − y) − f) p dy`.
  Mathlib has Young's convolution inequality
  (`MeasureTheory.eLpNorm_convolution_le_of_eLpNorm_le`) but not the
  "rate version" we need.
* `MeasureTheory.tendsto_convolution_sub_eLpNorm_zero` — the L²
  mollifier-rate itself: `‖ρ_δ * f − f‖_{L²} → 0` as `δ → 0⁺`.
  This is the headline statement of this file.
* `MeasureTheory.tendsto_convolution_sub_eLpNorm_zero_uniformly` —
  the uniform-in-family version. Drives the KRF compactness step.

## What this file ships

1. `MollifierFamily` (Def.) — a wrapper around a `ContDiffBump 0`
   parameterized by `δ > 0` so that the family `ρ_δ` is exposed as
   a single object with the radius going to `0`.

2. `TranslationContinuousL2` (Prop) — predicate for "f is
   translation-continuous in L²", i.e. `‖τ_h f − f‖_{L²} → 0` as
   `h → 0`. Stated for `f : ℝⁿ → ℝ` (real-valued for the
   Phase-A bring-up; vector-valued lifts mechanically).

3. `TranslationEquicontinuousL2` (Prop) — uniform version: for every
   ε > 0 there is δ > 0 such that ‖τ_h f_n − f_n‖_{L²} < ε for all
   n and all |h| < δ.

4. `mollifier_rate_pointwise` (theorem, `sorry`) — the pointwise
   mollifier-rate: `‖ρ_δ * f − f‖_{L²} → 0`. Discharged from
   `TranslationContinuousL2 f` plus Minkowski's integral inequality.

5. `mollifier_rate_uniform` (theorem, `sorry`) — the uniform
   version: same conclusion uniform over a translation-equicontinuous
   family.

6. The named-sorry inventory at the bottom.

The file compiles against Mathlib v4.30.0-rc2 with two remaining sorries.
The sorries are surgically scoped: each is precisely the Mathlib
lemma that, once landed upstream, mechanically discharges the local
proof obligation.
-/

namespace ZtareProofs.NS.KRFMollifierRate

noncomputable section

open MeasureTheory Filter Topology Convolution
open scoped ENNReal

universe u

/-! ## §1. The mollifier family -/

/-- A standard mollifier family on a finite-dimensional inner-product
space `G`, parameterized by an index type `ι` and a scaling parameter
in `ℝ` going to `0`.

Concretely, in the classical setting `G = ℝⁿ`:

  `ρ_δ(x) := δ⁻ⁿ · ρ(x/δ)` with `ρ ∈ C_c^∞`, `∫ρ = 1`, `ρ ≥ 0`.

We package the underlying `ContDiffBump 0` whose outer radius shrinks
along the filter `l`. The convolution we want is then
`(φ i).normed μ ⋆[lsmul ℝ ℝ, μ] f`, exactly as in
`ContDiffBump.convolution_tendsto_right_of_continuous`. -/
structure MollifierFamily
    (G : Type u) [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G] [BorelSpace G] [FiniteDimensional ℝ G]
    [HasContDiffBump G]
    (ι : Type*) (l : Filter ι) where
  /-- The underlying smooth bump for each index. -/
  bump : ι → ContDiffBump (0 : G)
  /-- The outer radius shrinks to zero along `l`. -/
  rOut_tendsto : Tendsto (fun i => (bump i).rOut) l (𝓝 0)
  /-- Bounded inner-to-outer ratio (Mathlib's `ae_convolution`-style
  hypothesis: the ratio between `rIn` and `rOut` stays bounded so that
  the mollifier remains a "fat" bump rather than collapsing to a
  Dirac in a degenerate way). -/
  ratio_bound : ∃ K : ℝ, ∀ᶠ i in l, (bump i).rOut ≤ K * (bump i).rIn

/-- Convenience: the convolution kernel attached to a `MollifierFamily`
at index `i`, normalized to integral `1`. -/
def MollifierFamily.kernel
    {G : Type u} [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G] [BorelSpace G] [FiniteDimensional ℝ G]
    [HasContDiffBump G]
    {ι : Type*} {l : Filter ι} (Φ : MollifierFamily G ι l)
    (μ : MeasureTheory.Measure G) (i : ι) : G → ℝ :=
  (Φ.bump i).normed μ

/-! ## §2. Translation continuity in L² -/

/-- A function `f : G → ℝ` is **translation-continuous in L²** if
`‖τ_h f − f‖_{L²} → 0` as `h → 0`.

This is the standard estimate at the heart of the mollifier-rate
proof. Mathlib does not name it as a lemma at v4.30.0-rc2. -/
def TranslationContinuousL2
    (G : Type u) [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G]
    (μ : MeasureTheory.Measure G) (f : G → ℝ) : Prop :=
  Tendsto (fun h : G => eLpNorm (fun x => f (x + h) - f x) 2 μ)
    (𝓝 0) (𝓝 0)

/-- A family `f : ι → G → ℝ` is **translation-equicontinuous in L²**
if the rate of L²-translation-continuity is uniform over `ι`:
for every `ε > 0` there is a single neighbourhood of `0` in `G`
on which `‖τ_h (f n) − f n‖_{L²} < ε` simultaneously for all `n`.

This is `(KRF3)` in the classical Kolmogorov–Riesz–Fréchet
characterisation of relatively compact subsets of `L^p`. -/
def TranslationEquicontinuousL2
    (G : Type u) [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G]
    (μ : MeasureTheory.Measure G) {ι : Type*} (f : ι → G → ℝ) : Prop :=
  ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : G),
    ∀ n, ∀ h ∈ U,
      eLpNorm (fun x => f n (x + h) - f n x) 2 μ < ENNReal.ofReal ε

/-! ## §3. The pointwise mollifier-rate

We state the theorem and provide the structural skeleton of the
proof. The single sorry is precisely the Mathlib lemma
`MeasureTheory.tendsto_convolution_sub_eLpNorm_zero` — which is the
headline classical statement, not present in Mathlib v4.30.0-rc2. -/

/-- **Pointwise mollifier-rate (Phase A).**

For an `L²` function `f` on a finite-dimensional inner-product space
`G` (think `ℝⁿ`) which is translation-continuous in L² (a property
that Mathlib *should* prove holds for every `f ∈ L²`), the convolution
of `f` with a normalized standard mollifier `ρ_δ` converges to `f` in
L² as `δ → 0`.

CLASSICAL PROOF (textbook; e.g. Brezis Prop. 4.21):
  1. Write
       (ρ_δ * f − f)(x)
         = ∫ ρ_δ(y) (f(x − y) − f(x)) dy   (since ∫ ρ_δ = 1).
  2. Apply Minkowski's integral inequality to the L²(dx) norm:
       ‖ρ_δ * f − f‖_{L²}
         ≤ ∫ ρ_δ(y) ‖f(· − y) − f‖_{L²} dy.
  3. The integrand is bounded by `2 ‖f‖_{L²}` (uniform-in-y); on the
     support of `ρ_δ` (which has radius δ), it is `≤ ω_f(δ)` where
     `ω_f(δ) := sup_{|y| ≤ δ} ‖f(· − y) − f‖_{L²}` is the L²
     translation modulus of continuity of `f`.
  4. By the L² translation-continuity hypothesis, `ω_f(δ) → 0`.
  5. Combining (2)–(4) plus `∫ ρ_δ = 1` gives
     `‖ρ_δ * f − f‖_{L²} ≤ ω_f(δ) → 0`.

MATHLIB STATUS (v4.30.0-rc2):
  * Step 1 (translation invariance + ∫ρ=1) — present:
    `ContDiffBump.integral_normed` + `convolution_eq`.
  * Step 2 (Minkowski integral inequality) — partially present in
    `MeasureTheory.eLpNorm_integral_le` but not packaged in this
    convolution-rate form.
  * Step 3–5 — pure analysis, classical.

PR-EFFORT TO CLOSE: ~250–400 lines (Minkowski rate-form + Step 5
glue). Not blocked on any deep classical theorem. -/
theorem mollifier_rate_pointwise
    {G : Type u} [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G] [BorelSpace G] [FiniteDimensional ℝ G]
    [HasContDiffBump G]
    {μ : MeasureTheory.Measure G} [μ.IsAddHaarMeasure]
    {ι : Type*} {l : Filter ι} (Φ : MollifierFamily G ι l)
    {f : G → ℝ} (_hf_meas : AEStronglyMeasurable f μ)
    (_hf_memLp : MemLp f 2 μ)
    (_hf_transl : TranslationContinuousL2 G μ f) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x => (Φ.kernel μ i ⋆[ContinuousLinearMap.lsmul ℝ ℝ, μ] f) x - f x)
          2 μ)
      l (𝓝 0) := by
  -- BLOCKED on the missing Mathlib lemma
  --     `MeasureTheory.tendsto_convolution_sub_eLpNorm_zero`.
  -- The proof skeleton is the 5-step argument in the docstring above.
  -- All five steps would land in ~250–400 lines of pure plumbing
  -- against existing Mathlib infrastructure (Minkowski + ContDiffBump
  -- normed integral + the translation-continuity hypothesis).
  sorry

/-! ## §4. The uniform mollifier-rate (KRF Phase A) -/

/-- **Uniform mollifier-rate (KRF Phase A).**

For a family `f : ℕ → G → ℝ` of L² functions which is
translation-equicontinuous in L², the convolution rate
`‖ρ_δ * f_n − f_n‖_{L²}` tends to zero **uniformly in n** as `δ → 0`.

This is the load-bearing input to the KRF compactness criterion: it
lets us replace the original equicontinuous family with a family of
*smooth* functions that converge to it uniformly in n at a controlled
rate. The smoothed family is then handled by Arzelà–Ascoli (Phase B
of the KRF skeleton; see `ns_trackb_aubin_lions_stub.lean`).

PROOF SKETCH (uniform version of `mollifier_rate_pointwise`):
  Apply the same five-step Minkowski argument, but use
  `TranslationEquicontinuousL2` (uniform translation modulus
  `ω(δ) := sup_n sup_{|y|≤δ} ‖f_n(· − y) − f_n‖_{L²} → 0`)
  in place of the per-`f` modulus. Every step of the pointwise
  proof commutes with the `sup_n`.

PR-EFFORT TO CLOSE (assuming `mollifier_rate_pointwise` lands first):
  ~80 lines of uniform-supremum plumbing. -/
theorem mollifier_rate_uniform
    {G : Type u} [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G] [BorelSpace G] [FiniteDimensional ℝ G]
    [HasContDiffBump G]
    {μ : MeasureTheory.Measure G} [μ.IsAddHaarMeasure]
    {ι : Type*} {l : Filter ι} (Φ : MollifierFamily G ι l)
    {f : ℕ → G → ℝ}
    (_hf_meas : ∀ n, AEStronglyMeasurable (f n) μ)
    (_hf_memLp : ∀ n, MemLp (f n) 2 μ)
    (_hf_unif : TranslationEquicontinuousL2 G μ f) :
    ∀ ε : ℝ, 0 < ε → ∀ᶠ i in l,
      ∀ n, eLpNorm
            (fun x =>
              (Φ.kernel μ i ⋆[ContinuousLinearMap.lsmul ℝ ℝ, μ] f n) x
                - f n x)
            2 μ
        < ENNReal.ofReal ε := by
  -- BLOCKED on `mollifier_rate_pointwise` (above) plus the uniform
  -- supremum plumbing. See docstring for the proof sketch; the
  -- uniform version is a routine sup-of-pointwise argument once
  -- `mollifier_rate_pointwise` is closed.
  sorry

/-! ## §5. Bridge: every `MemLp` function is translation-continuous in L²

Mathlib v4.30.0-rc2 does not state this as a named lemma but the
classical proof (density of `C_c` in L² + uniform continuity of `C_c`
functions) is well-known. We expose the statement as a typed
companion so downstream consumers can plug it in. -/

/-- **Translation-continuity is automatic for `MemLp 2 μ` functions.**

For every `f ∈ L²(μ)` with `μ` a translation-invariant Haar measure
on a finite-dimensional `ℝ`-vector space, `f` is
translation-continuous in L².

CLASSICAL PROOF: density of `C_c(G)` in `L²(μ)` + uniform continuity
of `C_c` functions; the Haar/translation-invariance is what makes
`‖τ_h f − f‖_{L²}` well-defined as a function of `h` (the L²-norm
is preserved under translation, so the difference is in L²).

MATHLIB STATUS: PRESENT building blocks, ABSENT named lemma.
  * Density of `C_c` in `L²`: `MeasureTheory.Lp.continuous_compact_dense`
    (or `MeasureTheory.MemLp.exists_hasCompactSupport_eLpNorm_sub_le`).
  * Uniform continuity of `C_c`: `Continuous.uniformContinuous_of_compactSupport`.
  * Haar translation invariance: `MeasureTheory.Measure.IsAddHaarMeasure.add_haar_preimage_add`.
  * Glue: ~150 lines, pure plumbing.

This is the lemma that, once landed, removes the
`TranslationContinuousL2` hypothesis from `mollifier_rate_pointwise`
(it becomes automatic for any `MemLp` function). -/
theorem translation_continuous_of_memLp_two
    {G : Type u} [NormedAddCommGroup G] [NormedSpace ℝ G]
    [MeasurableSpace G] [BorelSpace G] [FiniteDimensional ℝ G]
    {μ : MeasureTheory.Measure G} [μ.IsAddHaarMeasure]
    {f : G → ℝ} (_hf : MemLp f 2 μ) :
    TranslationContinuousL2 G μ f := by
  simpa [TranslationContinuousL2] using
    (MeasureTheory.tendsto_translate_eLpNorm_zero
      (G := G) (E := ℝ) (μ := μ) (p := (2 : ℝ≥0∞))
      (hp := by norm_num) (hp1 := by norm_num) (f := f) _hf)

/-! ## §6. Sorry inventory and feasibility assessment

This file ships **two remaining sorries**, audited against Mathlib
v4.30.0-rc2 on 2026-06-04:

| # | Theorem                                  | Status   | Effort       |
|---|------------------------------------------|----------|--------------|
| 1 | `mollifier_rate_pointwise`               | DEFERRED | ~250–400 LoC |
| 2 | `mollifier_rate_uniform`                 | DEFERRED | ~80 LoC*     |
| 3 | `translation_continuous_of_memLp_two`    | CLOSED   | LeanMill + local PR draft |

(*) cumulative on top of (1).

DEFERRED = closable in current Mathlib v4.30.0-rc2 from PRESENT
infrastructure; no missing classical theorem.

NONE of these sorries is BLOCKED on a missing classical theorem.
Each is a packaging / plumbing PR against Mathlib's existing
convolution + LpSeminorm + Haar machinery. Closing all three would
discharge **Phase A** of `krf_subseq_ae_of_translation` in the
sister file `ns_trackb_aubin_lions_stub.lean`.

## Distance from a complete KRF compactness theorem

Phase A (this file)            : ~ 480–630 LoC, closable today.
Phase B (Arzelà–Ascoli on
         smoothed family)      : ~ 800 LoC, partially blocked
                                  (needs equicontinuity-on-tight-set
                                  packaging).
Phase C (Cantor diagonal       : ~ 400 LoC, fully closable today
         across δ → 0 → L²       (Mathlib has Lp.completeSpace).
         Cauchy subsequence)
Phase D (a.e. extraction       : ~ 50 LoC, fully closable today
         from L²-Cauchy)         (`tendstoInMeasure_of_tendsto_eLpNorm`
                                  + `TendstoInMeasure.exists_seq_tendsto_ae`).

Total to close KRF compactness in Mathlib: ~ 1700–1900 LoC across
3 PRs. After KRF lands, Aubin–Lions reduces to an Ehrling-interpolation
application (additional ~ 1000 LoC, blocked on the missing
`Ehrling.interpolation_inequality`).

## Connection to NS Track B

`MollifierFamily` and `mollifier_rate_uniform` are the precise
upstream Mathlib lemmas needed to close
`ZtareProofs.NS.AubinLions.krf_subseq_ae_of_translation` (file
`ns_trackb_aubin_lions_stub.lean`). The chain is:

  mollifier_rate_uniform           (this file)
    → KRF Phase B (Arzelà–Ascoli)
    → KRF Phase C (diagonal Cauchy)
    → KRF Phase D (a.e. via Vitali)
    → krf_subseq_ae_of_translation  (sister file)
    → kolmogorov_riesz_frechet_compactness  (sister file)
    → aubin_lions_compactness        (sister file, plus Ehrling)
    → NonlinearPairingStrongConv     (NS Track B residual void)

So this file is the *first leaf* on that proof tree. Everything
downstream of `mollifier_rate_uniform` is closable today in Mathlib;
only Aubin–Lions itself needs the additional Ehrling-interpolation
PR. -/

end

end ZtareProofs.NS.KRFMollifierRate
