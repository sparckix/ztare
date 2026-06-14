/-
Copyright (c) 2026 Mathlib Contributors. All rights reserved.
Released under Apache 2.0 license, as described in the file LICENSE.
Authors: Daniel Alami
-/
import Mathlib.MeasureTheory.Function.ContinuousMapDense
import Mathlib.MeasureTheory.Function.LpSeminorm.TriangleInequality
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Indicator
import Mathlib.MeasureTheory.Group.Measure
import Mathlib.MeasureTheory.Measure.Haar.OfBasis
import Mathlib.Topology.UniformSpace.HeineCantor
import Mathlib.Topology.MetricSpace.Thickening

/-!
# Translation continuity in `Lᵖ`

This file proves that, for `f ∈ Lᵖ(G; E)` on a locally compact second-countable
abelian topological group `G` carrying an `IsAddHaarMeasure`, translation by `h`
converges to the identity in `Lᵖ` as `h → 0`. Concretely:

`tendsto_translate_eLpNorm_zero` :
  if `f : G → E` is `MemLp p μ`, then
  `Tendsto (fun h => eLpNorm (fun x => f (x + h) - f x) p μ) (𝓝 0) (𝓝 0)`.

This is sometimes called *strong continuity of translation* (continuity of the
regular representation); see Lieb–Loss, *Analysis*, Theorem 2.16, or Brezis,
*Functional Analysis*, Lemme 4.3.

## Proof outline

The classical 3-step density argument:

1. **(density)** Approximate `f` by a compactly supported continuous `g`,
   using `MeasureTheory.MemLp.exists_hasCompactSupport_eLpNorm_sub_le`.
2. **(uniform continuity)** A compactly supported continuous function is
   uniformly continuous, by `HasCompactSupport.uniformContinuous_of_continuous`,
   and translation is `Lᵖ`-continuous on it by dominated convergence.
3. **(triangle inequality)** Combine via translation invariance of the Haar
   measure (`MeasureTheory.measurePreserving_add_left`).

## Main statement

* `MeasureTheory.tendsto_translate_eLpNorm_zero`

## References

* H. Brezis, *Functional Analysis, Sobolev Spaces and Partial Differential Equations*,
  Springer, 2011, Lemme 4.3.
* E. H. Lieb and M. Loss, *Analysis*, AMS, 2nd ed., 2001, Theorem 2.16.

## Tags

Lp, translation, continuity, Haar measure
-/

set_option linter.unusedSectionVars false

namespace MeasureTheory

open Set Filter Topology MeasureTheory ENNReal
open scoped Topology ENNReal NNReal

variable {G : Type*} [NormedAddCommGroup G] [MeasurableSpace G] [BorelSpace G]
  [SecondCountableTopology G]
variable {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
variable {μ : Measure G} {p : ℝ≥0∞}

/-! ## Translation invariance of `eLpNorm` on a left-invariant Haar measure -/

/-- For an additive Haar measure `μ` on an abelian group `G`, the right-translation
`x ↦ x + h` preserves `μ`. The (built-in) `IsAddLeftInvariant` of an
`IsAddHaarMeasure` together with commutativity yields right-invariance. -/
private lemma measurePreserving_add_right_of_isAddHaarMeasure
    [μ.IsAddLeftInvariant] (h : G) :
    MeasurePreserving (fun x : G => x + h) μ μ := by
  -- `(· + h) = (h + ·)` because `G` is abelian.
  have hfun : (fun x : G => x + h) = (fun x : G => h + x) := by
    funext x; exact add_comm x h
  rw [hfun]
  exact measurePreserving_add_left μ h

/-- Translation invariance of the `Lᵖ` seminorm under an `IsAddLeftInvariant`
measure on an abelian group. -/
lemma eLpNorm_comp_add_right [μ.IsAddLeftInvariant]
    {f : G → E} (hf : AEStronglyMeasurable f μ) (h : G) :
    eLpNorm (fun x => f (x + h)) p μ = eLpNorm f p μ :=
  eLpNorm_comp_measurePreserving hf
    (measurePreserving_add_right_of_isAddHaarMeasure h)

/-- AE-strong-measurability is preserved by right translation under
`IsAddLeftInvariant`. -/
lemma _root_.MeasureTheory.AEStronglyMeasurable.comp_add_right
    [μ.IsAddLeftInvariant] {f : G → E}
    (hf : AEStronglyMeasurable f μ) (h : G) :
    AEStronglyMeasurable (fun x => f (x + h)) μ :=
  hf.comp_measurePreserving (measurePreserving_add_right_of_isAddHaarMeasure h)

/-! ## The compact-support case -/

section CompactSupportCase

variable [LocallyCompactSpace G] [μ.IsAddHaarMeasure]

/-- **Translation continuity in `Lᵖ` for compactly supported continuous functions.**

If `g : G → E` is continuous with compact support and lies in `Lᵖ`, then
`eLpNorm (fun x => g (x + h) - g x) p μ → 0` as `h → 0`.

Proof: by uniform continuity of `g` on the compact `tsupport g + closedBall 0 1`
plus dominated convergence; the integrand is supported in a fixed compact set
for `‖h‖ ≤ 1` and is uniformly small there.

**Mathlib gap MLG-1a**: while every analytic ingredient is present in Mathlib
(uniform continuity from `HasCompactSupport.uniformContinuous_of_continuous`,
support inflation, dominated convergence on a finite-measure compact), the
~80 LoC of plumbing has not been packaged. See the proof skeleton in the
file body. -/
theorem tendsto_translate_eLpNorm_zero_of_hasCompactSupport
    (_hp : p ≠ ∞) (hp1 : 1 ≤ p)
    {g : G → E} (g_cs : HasCompactSupport g) (g_cont : Continuous g)
    (_g_mem : MemLp g p μ) :
    Tendsto (fun h : G => eLpNorm (fun x => g (x + h) - g x) p μ) (𝓝 0) (𝓝 0) := by
  -- `g` is uniformly continuous (Heine–Cantor on its compact support).
  have g_uc : UniformContinuous g :=
    g_cs.uniformContinuous_of_continuous g_cont
  -- Inflate the compact `tsupport g` to a compact neighborhood.
  obtain ⟨δK, δK_pos, K_compact⟩ :
      ∃ δ, 0 < δ ∧ IsCompact (Metric.cthickening δ (tsupport g)) :=
    g_cs.exists_isCompact_cthickening
  set K : Set G := Metric.cthickening δK (tsupport g) with hK_def
  -- Haar measure is finite on compacts.
  have μK_lt : μ K < ∞ := K_compact.measure_lt_top
  have μK_ne : μ K ≠ ∞ := μK_lt.ne
  -- Convenient bookkeeping for `1 / p.toReal`.
  have hp_pos : 0 < p := lt_of_lt_of_le (by norm_num) hp1
  have hp_ne_zero : p ≠ 0 := hp_pos.ne'
  -- Reformulate "tends to zero" in `ℝ≥0∞`.
  rw [ENNReal.tendsto_nhds_zero]
  intro ε hε_pos
  -- If `ε = ∞`, the inequality `_ ≤ ε` is trivial; reduce to finite ε.
  by_cases hε_top : ε = ∞
  · subst hε_top
    exact Filter.Eventually.of_forall fun _ => le_top
  have hε_ne_top : ε ≠ ∞ := hε_top
  -- A nonzero finite real upper bound `M` for `μ K ^ (1 / p.toReal)`.
  set M : ℝ≥0∞ := μ K ^ (1 / p.toReal) + 1 with hM_def
  have M_lt_top : M < ∞ := by
    refine ENNReal.add_lt_top.mpr ⟨?_, by simp⟩
    exact ENNReal.rpow_lt_top_of_nonneg (by positivity) μK_ne
  have M_ne_top : M ≠ ∞ := M_lt_top.ne
  have M_pos : 0 < M := by
    refine lt_of_lt_of_le ?_ (le_add_self)
    exact zero_lt_one
  have M_ne_zero : M ≠ 0 := M_pos.ne'
  -- Pick a "real ε'" so that `ENNReal.ofReal ε' * M ≤ ε`.
  -- We work in ℝ≥0∞ and translate the `eLpNorm_le_of_ae_bound` bound.
  set ε' : ℝ≥0∞ := ε / M with hε'_def
  have ε'_pos : 0 < ε' := by
    rw [hε'_def]
    exact ENNReal.div_pos hε_pos.ne' M_ne_top
  have ε'_lt_top : ε' < ∞ := by
    rw [hε'_def]
    exact ENNReal.div_lt_top hε_ne_top M_ne_zero
  have ε'_ne_top : ε' ≠ ∞ := ε'_lt_top.ne
  -- Choose a real representative `c` of `ε'` (so `ENNReal.ofReal c = ε'` and `0 < c`).
  set c : ℝ := ε'.toReal with hc_def
  have c_pos : 0 < c := ENNReal.toReal_pos ε'_pos.ne' ε'_ne_top
  have hc_ofReal : ENNReal.ofReal c = ε' := ENNReal.ofReal_toReal ε'_ne_top
  -- Uniform continuity in metric form.
  rw [Metric.uniformContinuous_iff] at g_uc
  obtain ⟨δu, δu_pos, h_unif⟩ := g_uc c c_pos
  -- Take δ := min(δK, δu) to control both support inclusion and the `c` bound.
  set δ : ℝ := min δK δu with hδ_def
  have δ_pos : 0 < δ := lt_min δK_pos δu_pos
  -- Eventually for `‖h‖ < δ`, the eLpNorm bound holds.
  rw [Metric.eventually_nhds_iff]
  refine ⟨δ, δ_pos, fun h hh => ?_⟩
  have hh_norm : ‖h‖ < δ := by
    rw [dist_zero_right] at hh; exact hh
  have hh_norm_K : ‖h‖ < δK := lt_of_lt_of_le hh_norm (min_le_left _ _)
  have hh_norm_u : ‖h‖ < δu := lt_of_lt_of_le hh_norm (min_le_right _ _)
  -- Pointwise bound: `‖g (x+h) - g x‖ ≤ c` everywhere.
  have h_pt_bound : ∀ x : G, ‖g (x + h) - g x‖ ≤ c := by
    intro x
    have hd : dist (x + h) x < δu := by
      rw [dist_eq_norm, add_sub_cancel_left]; exact hh_norm_u
    have := (h_unif hd).le
    rwa [dist_eq_norm] at this
  -- Support of `fun x => g (x+h) - g x` is contained in `K = cthickening δK (tsupport g)`.
  have h_supp_subset :
      Function.support (fun x => g (x + h) - g x) ⊆ K := by
    intro x hx
    -- if `x ∉ K`, then both `g x = 0` (since `tsupport g ⊆ K`) and `g (x+h) = 0`.
    by_contra hxK
    -- `tsupport g ⊆ K`.
    have h_tsup_sub_K : tsupport g ⊆ K := Metric.self_subset_cthickening _
    have hx_notin_tsup : x ∉ tsupport g := fun hh' => hxK (h_tsup_sub_K hh')
    have hg_x : g x = 0 := image_eq_zero_of_notMem_tsupport hx_notin_tsup
    -- `x + h ∉ tsupport g` since otherwise `x = (x + h) - h ∈ cthickening δK (tsupport g) = K`.
    have hxh_notin_tsup : x + h ∉ tsupport g := by
      intro hxh
      apply hxK
      -- `x ∈ cthickening δK (tsupport g)`: take `y = x + h ∈ tsupport g`,
      -- `dist x y = dist x (x+h) = ‖h‖ ≤ δK`.
      refine Metric.mem_cthickening_of_dist_le x (x + h) δK (tsupport g) hxh ?_
      rw [dist_eq_norm, sub_add_eq_sub_sub, sub_self, zero_sub, norm_neg]
      exact hh_norm_K.le
    have hg_xh : g (x + h) = 0 := image_eq_zero_of_notMem_tsupport hxh_notin_tsup
    -- Contradiction: `(g (x+h) - g x) = 0` but `x` is in `support`.
    apply hx
    simp [hg_x, hg_xh]
  -- Measurability of the translated difference.
  have h_meas : AEStronglyMeasurable (fun x => g (x + h) - g x) μ :=
    ((g_cont.comp (continuous_id.add continuous_const)).sub g_cont).aestronglyMeasurable
  -- Compute the eLpNorm bound: split via `eLpNorm_indicator_eq_eLpNorm_restrict`.
  have hK_meas : MeasurableSet K := K_compact.isClosed.measurableSet
  -- Step A: `eLpNorm (· ) p μ = eLpNorm (K.indicator (·)) p μ` since `(·)` vanishes outside K.
  have h_indic_eq :
      (fun x => g (x + h) - g x) = K.indicator (fun x => g (x + h) - g x) := by
    funext x
    by_cases hxK : x ∈ K
    · simp [Set.indicator_of_mem hxK]
    · have : g (x + h) - g x = 0 := by
        by_contra hne
        exact hxK (h_supp_subset (by simpa [Function.mem_support] using hne))
      simp [Set.indicator_of_notMem hxK, this]
  -- Now bound: `eLpNorm (K.indicator …) p μ = eLpNorm (…) p (μ.restrict K)`.
  rw [h_indic_eq]
  rw [eLpNorm_indicator_eq_eLpNorm_restrict hK_meas]
  -- A.e.‐bound on `μ.restrict K` becomes the universal pointwise `c` bound.
  have h_ae_bound : ∀ᵐ x ∂(μ.restrict K), ‖g (x + h) - g x‖ ≤ c :=
    Filter.Eventually.of_forall h_pt_bound
  have h_bound :=
    eLpNorm_le_of_ae_bound (μ := μ.restrict K) (p := p) h_ae_bound
  -- Convert to ENNReal arithmetic and chain to `≤ ε`.
  have h_meas_K : (μ.restrict K) Set.univ = μ K := by
    rw [Measure.restrict_apply MeasurableSet.univ, Set.univ_inter]
  rw [h_meas_K] at h_bound
  -- Now `h_bound : eLpNorm … p (μ.restrict K) ≤ μ K ^ (1/p.toReal) * ENNReal.ofReal c`.
  refine h_bound.trans ?_
  -- It remains to show `μ K ^ p.toReal⁻¹ * ENNReal.ofReal c ≤ ε`.
  -- Using `ENNReal.ofReal c = ε' = ε / M` and `μ K ^ p.toReal⁻¹ ≤ M`:
  rw [hc_ofReal]
  -- mul ≤ M * (ε / M) = ε (using `M ≠ 0, M ≠ ∞`).
  have h_mu_le_M : μ K ^ p.toReal⁻¹ ≤ M := by
    rw [hM_def, one_div]; exact le_self_add
  calc μ K ^ p.toReal⁻¹ * ε'
      ≤ M * ε' := by gcongr
    _ = M * (ε / M) := by rw [hε'_def]
    _ = ε := ENNReal.mul_div_cancel M_ne_zero M_ne_top

end CompactSupportCase

/-! ## The main result -/

section MainResult

variable [LocallyCompactSpace G] [μ.IsAddHaarMeasure]

/-- **Translation continuity in `Lᵖ`.**

If `f ∈ Lᵖ(G; E)` for `1 ≤ p < ∞`, then translating `f` by `h` converges to `f`
in `Lᵖ` as `h → 0`. Concretely,
`eLpNorm (fun x => f (x + h) - f x) p μ → 0` as `h → 0`.

Density (`exists_hasCompactSupport_eLpNorm_sub_le`) reduces to the compactly
supported continuous case, which is `tendsto_translate_eLpNorm_zero_of_hasCompactSupport`. -/
theorem tendsto_translate_eLpNorm_zero
    (hp : p ≠ ∞) (hp1 : 1 ≤ p)
    {f : G → E} (hf : MemLp f p μ) :
    Tendsto (fun h : G => eLpNorm (fun x => f (x + h) - f x) p μ) (𝓝 0) (𝓝 0) := by
  -- Reduce to: for every `ε > 0`, eventually `eLpNorm (·) p μ ≤ ε`.
  rw [ENNReal.tendsto_nhds_zero]
  intro ε hε
  -- Split `ε` into thirds for the triangle inequality.
  have hε3_pos : (0 : ℝ≥0∞) < ε / 3 := by
    rw [ENNReal.div_pos_iff]
    exact ⟨hε.ne', by norm_num⟩
  have hε3_ne : ε / 3 ≠ 0 := hε3_pos.ne'
  -- Step 1 (density): pick a compactly supported continuous `g` with
  -- `eLpNorm (f - g) p μ ≤ ε/3`.
  obtain ⟨g, g_cs, hfg, g_cont, g_mem⟩ :=
    hf.exists_hasCompactSupport_eLpNorm_sub_le hp hε3_ne
  -- Strong-measurability shorthands.
  have hf_aesm : AEStronglyMeasurable f μ := hf.aestronglyMeasurable
  have hg_aesm : AEStronglyMeasurable g μ := g_cont.aestronglyMeasurable
  -- Step 2 (compact-support case): `eLpNorm (τ_h g - g) p μ → 0`.
  have h_g_translate :
      Tendsto (fun h : G => eLpNorm (fun x => g (x + h) - g x) p μ) (𝓝 0) (𝓝 0) :=
    tendsto_translate_eLpNorm_zero_of_hasCompactSupport hp hp1 g_cs g_cont g_mem
  rw [ENNReal.tendsto_nhds_zero] at h_g_translate
  -- Eventually pick `h` with the middle term `≤ ε/3`.
  filter_upwards [h_g_translate (ε / 3) hε3_pos] with h hh
  -- Step 3: triangle inequality.
  -- Decompose: `f(x+h) - f(x) = [f(x+h) - g(x+h)] + [g(x+h) - g(x)] + [g(x) - f(x)]`.
  set A : G → E := fun x => f (x + h) - g (x + h) with hA_def
  set B : G → E := fun x => g (x + h) - g x with hB_def
  set C : G → E := fun x => g x - f x with hC_def
  have decomp : (fun x => f (x + h) - f x)
      = (fun x => A x + B x + C x) := by
    funext x
    simp only [hA_def, hB_def, hC_def]
    abel
  rw [decomp]
  -- AE-strong-measurability of the three summands.
  have hf_trans_aesm : AEStronglyMeasurable (fun x => f (x + h)) μ :=
    hf_aesm.comp_add_right h
  have hg_trans_aesm : AEStronglyMeasurable (fun x => g (x + h)) μ :=
    hg_aesm.comp_add_right h
  have hA_aesm : AEStronglyMeasurable A μ := hf_trans_aesm.sub hg_trans_aesm
  have hB_aesm : AEStronglyMeasurable B μ := hg_trans_aesm.sub hg_aesm
  have hC_aesm : AEStronglyMeasurable C μ := hg_aesm.sub hf_aesm
  have hAB_aesm : AEStronglyMeasurable (fun x => A x + B x) μ := hA_aesm.add hB_aesm
  -- Triangle: `‖A + B + C‖_p ≤ ‖A + B‖_p + ‖C‖_p ≤ ‖A‖_p + ‖B‖_p + ‖C‖_p`.
  have step_outer :
      eLpNorm ((fun x => A x + B x) + C) p μ
        ≤ eLpNorm (fun x => A x + B x) p μ + eLpNorm C p μ := by
    have := eLpNorm_add_le (μ := μ) (p := p)
      (f := fun x => A x + B x) (g := C) hAB_aesm hC_aesm hp1
    simpa using this
  have step_inner :
      eLpNorm (A + B) p μ
        ≤ eLpNorm A p μ + eLpNorm B p μ := by
    have := eLpNorm_add_le (μ := μ) (p := p)
      (f := A) (g := B) hA_aesm hB_aesm hp1
    simpa using this
  -- Bound each summand by `ε / 3`.
  -- `A`: `‖f(·+h) - g(·+h)‖_p = ‖f - g‖_p` by translation invariance.
  have hA_le : eLpNorm A p μ ≤ ε / 3 := by
    have hAeq : A = (fun x => (f - g) (x + h)) := by
      funext x; simp [hA_def, Pi.sub_apply]
    rw [hAeq, eLpNorm_comp_add_right (hf_aesm.sub hg_aesm) h]
    exact hfg
  -- `B` is bounded by `ε/3` by hypothesis (already filtered_upward).
  have hB_le : eLpNorm B p μ ≤ ε / 3 := hh
  -- `C = -(f - g)`, so `‖C‖_p = ‖f - g‖_p ≤ ε/3`.
  have hC_le : eLpNorm C p μ ≤ ε / 3 := by
    have hCeq : C = -(f - g) := by
      funext x; simp [hC_def, Pi.sub_apply, Pi.neg_apply, neg_sub]
    rw [hCeq, eLpNorm_neg]
    exact hfg
  -- Sum:  ε/3 + ε/3 + ε/3 = ε.
  have triple_third : (ε / 3 + ε / 3 + ε / 3 : ℝ≥0∞) = ε := by
    have h3_ne : (3 : ℝ≥0∞) ≠ 0 := by norm_num
    have h3_top : (3 : ℝ≥0∞) ≠ ∞ := by norm_num
    rw [← ENNReal.add_div, ← ENNReal.add_div]
    rw [show (ε + ε + ε : ℝ≥0∞) = ε * 3 by ring]
    rw [ENNReal.mul_div_cancel_right h3_ne h3_top]
  have hABC :
      eLpNorm (fun x => A x + B x + C x) p μ =
        eLpNorm ((fun x => A x + B x) + C) p μ := by
    congr
  have hAB :
      eLpNorm (fun x => A x + B x) p μ =
        eLpNorm (A + B) p μ := by
    congr
  calc eLpNorm (fun x => A x + B x + C x) p μ
      = eLpNorm ((fun x => A x + B x) + C) p μ := hABC
    _ ≤ eLpNorm (fun x => A x + B x) p μ + eLpNorm C p μ := step_outer
    _ = eLpNorm (A + B) p μ + eLpNorm C p μ := by rw [hAB]
    _ ≤ (eLpNorm A p μ + eLpNorm B p μ) + eLpNorm C p μ := by gcongr
    _ ≤ (ε / 3 + ε / 3) + ε / 3 := by gcongr
    _ = ε := triple_third

end MainResult

end MeasureTheory
