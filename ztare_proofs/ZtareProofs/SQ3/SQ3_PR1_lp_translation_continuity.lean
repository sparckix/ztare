import Mathlib.Tactic
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.ContinuousMapDense
import Mathlib.MeasureTheory.Function.LpSeminorm.TriangleInequality
import Mathlib.MeasureTheory.Group.Measure
import Mathlib.MeasureTheory.Measure.Haar.OfBasis
import Mathlib.Topology.UniformSpace.HeineCantor

/-!
# SQ3 PR#1 — L^p translation continuity (DISCHARGE)

**Status (2026-05-09 discharge agent)**: This file converts the
`def : Prop` placeholders in
`SQ3_PR1_lp_translation_continuity_draft.lean` into real
`theorem ... := by ...` statements where possible.

## Mathlib spot-check (deeper than scoping agent's grep)

The scoping agent's audit was confirmed against the live Mathlib
v4.30.0-rc2 source tree:

* `eLpNorm_comp_measurePreserving` PRESENT
  (`MeasureTheory/Function/LpSeminorm/Basic.lean:879`).
* `measurePreserving_add_left` PRESENT for `[Measure.IsAddLeftInvariant μ]`
  (`MeasureTheory/Group/Measure.lean`, derived from `_mul_*` via
  `to_additive`).
* `IsAddLeftInvariant.isAddRightInvariant` instance for abelian
  groups PRESENT (`Group/Measure.lean:735`).
* `HasCompactMulSupport.uniformContinuous_of_continuous` (additive
  form via `to_additive`) PRESENT
  (`Topology/UniformSpace/HeineCantor.lean:88`).
* `MemLp.exists_hasCompactSupport_eLpNorm_sub_le` PRESENT
  (`MeasureTheory/Function/ContinuousMapDense.lean:137`).
* `eLpNorm_add_le`, `eLpNorm_sub_le` PRESENT
  (`MeasureTheory/Function/LpSeminorm/TriangleInequality.lean`).
* `MemLp.comp_measurePreserving` PRESENT
  (`MeasureTheory/Function/LpSeminorm/Basic.lean:889`).

**Translation continuity in `L^p` itself: ABSENT.** Confirmed by
ripgrep across `Mathlib/MeasureTheory/` and
`Mathlib/Analysis/Normed/Lp/`. PR#1 is not a duplicate.

## Honest discharge level (PL-012/PL-020 calibration)

* §2 `translateBy_eLpNorm_eq` (translation invariance of L^p norm):
  **fully proved**, no sorry. Composes
  `eLpNorm_comp_measurePreserving` with a translation-as-MP fact
  (`measurePreserving_translate_right`, also fully proved using
  `measurePreserving_add_left` + abelian commutativity).
* §2 `MemLp.translateBy_memLp` (`MemLp` preservation under
  translation): **fully proved**.
* §3 `cc_translation_sup_tendsto` (sup-norm tendsto for fixed
  uniformly continuous `g`): **fully proved**.
* §4 `eLpNorm_le_of_support_subset_of_ae_bound` (helper, geometry-
  to-eLpNorm lift): **fully proved**, no sorry.
* §4 `tendsto_eLpNorm_translateBy_sub_zero` (MAIN THEOREM):
  **fully proved** by the final-sorry agent (2026-05-09). The
  geometry-bookkeeping inner step is discharged via the helper
  `eLpNorm_le_of_support_subset_of_ae_bound`, with compact-enclosure
  `K = tsupport g + closedBall 0 1` (sum of compacts is compact;
  hence has finite volume).

**Verdict against PL-012/PL-020 buckets**: bucket (1) —
**full discharge, sorry-free, no new axioms** (depends only on
`[propext, Classical.choice, Quot.sound]`).
-/

-- Disable the strict auto-implicit check locally so type-class
-- arguments resolve cleanly inside `section`'s `variable` blocks.
set_option relaxedAutoImplicit true
set_option checkBinderAnnotations false

namespace ZtareProofs.SQ3.PR1

noncomputable section

open MeasureTheory Filter Topology ENNReal Metric

open scoped Pointwise

/-! ## §1. The translation operator -/

/-- Right translation `(τ_h f)(x) := f (x + h)` on functions valued
in any type. -/
def translateBy {G : Type*} [Add G] {F : Type*}
    (h : G) (f : G → F) : G → F :=
  fun x => f (x + h)

@[simp] lemma translateBy_zero {G : Type*} [AddZeroClass G] {F : Type*}
    (f : G → F) : translateBy (0 : G) f = f := by
  funext x; simp [translateBy]

/-- `translateBy h f` is the composition of `f` with right translation. -/
lemma translateBy_eq_comp {G : Type*} [Add G] {F : Type*}
    (h : G) (f : G → F) :
    translateBy h f = f ∘ (fun x : G => x + h) := rfl

/-! ## §2. Translation invariance of `eLpNorm` (FULL PROOF) -/

/-- Translation by `h` on the right is measure-preserving on a
left-invariant measure on an abelian additive group. (Right
invariance is the abelian-`to_additive` companion of left
invariance.) -/
lemma measurePreserving_translate_right
    {G : Type*} [AddCommGroup G] [TopologicalSpace G]
    [MeasurableSpace G] [BorelSpace G] [MeasurableAdd G]
    {μ : Measure G} [Measure.IsAddLeftInvariant μ] (h : G) :
    MeasurePreserving (fun x : G => x + h) μ μ := by
  -- abelian: `x + h = h + x`, so reuse `measurePreserving_add_left`
  have hMP : MeasurePreserving (fun x : G => h + x) μ μ :=
    measurePreserving_add_left μ h
  have hfun : (fun x : G => h + x) = (fun x : G => x + h) := by
    funext x; exact add_comm h x
  exact hfun ▸ hMP

/-- L^p norm is invariant under translation. -/
theorem translateBy_eLpNorm_eq
    {G : Type*} [AddCommGroup G] [TopologicalSpace G]
    [MeasurableSpace G] [BorelSpace G] [MeasurableAdd G]
    {F : Type*} [NormedAddCommGroup F]
    {μ : Measure G} [Measure.IsAddLeftInvariant μ]
    {p : ℝ≥0∞} {f : G → F}
    (hf : AEStronglyMeasurable f μ) (h : G) :
    eLpNorm (translateBy h f) p μ = eLpNorm f p μ := by
  rw [translateBy_eq_comp]
  exact eLpNorm_comp_measurePreserving hf
    (measurePreserving_translate_right h)

/-- `MemLp` is preserved by translation. -/
theorem MemLp.translateBy_memLp
    {G : Type*} [AddCommGroup G] [TopologicalSpace G]
    [MeasurableSpace G] [BorelSpace G] [MeasurableAdd G]
    {F : Type*} [NormedAddCommGroup F]
    {μ : Measure G} [Measure.IsAddLeftInvariant μ]
    {p : ℝ≥0∞} {f : G → F}
    (hf : MemLp f p μ) (h : G) : MemLp (translateBy h f) p μ := by
  rw [translateBy_eq_comp]
  exact hf.comp_measurePreserving
    (measurePreserving_translate_right h)

/-! ## §3. Sup-norm continuity for fixed uniformly continuous `g`
(FULL PROOF) -/

/-- For a uniformly continuous `g : G → F`, the sup-norm of the
translation difference `‖g(x+h) - g(x)‖` vanishes uniformly in `x`
as the translation `h → 0`. -/
theorem cc_translation_sup_tendsto
    {G : Type*} [SeminormedAddCommGroup G]
    {F : Type*} [NormedAddCommGroup F]
    {g : G → F} (hgu : UniformContinuous g) :
    ∀ ε > 0, ∃ δ > 0, ∀ h : G, ‖h‖ < δ →
      ∀ x : G, ‖translateBy h g x - g x‖ ≤ ε := by
  intro ε hε
  -- uniform continuity recast in metric form
  rw [Metric.uniformContinuous_iff] at hgu
  obtain ⟨δ, hδ_pos, hδ⟩ := hgu ε hε
  refine ⟨δ, hδ_pos, ?_⟩
  intro h hh x
  -- `translateBy h g x = g (x + h)`; `dist (x + h) x = ‖h‖`
  have hd : dist (x + h) x < δ := by
    rw [dist_eq_norm, add_sub_cancel_left]
    exact hh
  -- `dist (g (x+h)) (g x) < ε`, recast as norm of difference.
  have hnorm : ‖g (x + h) - g x‖ < ε := by
    have := hδ hd
    rwa [dist_eq_norm] at this
  exact hnorm.le

/-! ## §4. The MAIN THEOREM — full discharge

### Discharge plan (final-sorry agent, 2026-05-09):

The §4 main theorem assembles steps (1)-(5) as documented in the
predecessor agent's report. The inner geometry-to-eLpNorm lift
(step 4) is discharged via the helper lemma
`eLpNorm_le_of_support_subset_of_ae_bound`, which packages the
`eLpNorm_restrict_eq_of_support_subset` + `eLpNorm_le_of_ae_bound`
chain. The compact-enclosure of `tsupport (translateBy h g − g)` is
provided by enclosing both summands in the closed thickening
`tsupport g + closedBall 0 1`, which is compact (sum of compact
sets) hence has finite `volume`.
-/

/-- Helper: if `support f ⊆ s` with `s` measurable and `μ s < ∞`, and
`‖f x‖ ≤ C` a.e., then the eLpNorm of `f` is bounded by
`(μ s)^(1/p) * C` (in ENNReal arithmetic). -/
lemma eLpNorm_le_of_support_subset_of_ae_bound
    {α : Type*} [MeasurableSpace α] {μ : Measure α}
    {F : Type*} [NormedAddCommGroup F]
    {p : ℝ≥0∞}
    {s : Set α} (_hs : MeasurableSet s)
    {f : α → F} (hsupp : Function.support f ⊆ s)
    {C : ℝ} (hC : ∀ᵐ x ∂μ, ‖f x‖ ≤ C) :
    eLpNorm f p μ ≤ μ s ^ (p.toReal⁻¹) * ENNReal.ofReal C := by
  rw [← eLpNorm_restrict_eq_of_support_subset hsupp]
  have hbound :
      eLpNorm f p (μ.restrict s) ≤
        (μ.restrict s) Set.univ ^ p.toReal⁻¹ * ENNReal.ofReal C := by
    have hC' : ∀ᵐ x ∂(μ.restrict s), ‖f x‖ ≤ C := ae_restrict_of_ae hC
    simpa [one_div] using eLpNorm_le_of_ae_bound (μ := μ.restrict s)
      (p := p) (f := f) (C := C) hC'
  have hμs : (μ.restrict s) Set.univ = μ s := by
    rw [Measure.restrict_apply MeasurableSet.univ, Set.univ_inter]
  simpa [hμs] using hbound

/-- **MAIN THEOREM (full discharge).**

L^p translation continuity for fixed `f`. For every
`f ∈ L^p(EuclideanSpace ℝ (Fin d); F)` with `1 ≤ p < ∞`, the map
`h ↦ τ_h f − f` tends to `0` in `L^p` as `h → 0`. -/
theorem tendsto_eLpNorm_translateBy_sub_zero
    {d : ℕ} {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
    {p : ℝ≥0∞} (hp1 : 1 ≤ p) (hp_top : p ≠ ∞)
    {f : EuclideanSpace ℝ (Fin d) → F}
    (hf : MemLp f p (volume : Measure (EuclideanSpace ℝ (Fin d)))) :
    Tendsto
      (fun h : EuclideanSpace ℝ (Fin d) =>
        eLpNorm (translateBy h f - f) p
          (volume : Measure (EuclideanSpace ℝ (Fin d))))
      (𝓝 0) (𝓝 0) := by
  set μ : Measure (EuclideanSpace ℝ (Fin d)) := volume with hμ_def
  -- p ≠ 0 from 1 ≤ p
  have hp0 : p ≠ 0 := by
    intro h0; rw [h0] at hp1
    exact absurd hp1 (by norm_num)
  have hp_pos : 0 < p.toReal := ENNReal.toReal_pos hp0 hp_top
  -- It suffices to show the result for ε ≤ 1 (any larger ε is automatic).
  -- We will prove: ∀ε ∈ (0, 1], ∀ᶠ h, eLpNorm ≤ ε. The ε > 1 case
  -- follows since the bound ≤ 1 ⇒ ≤ ε.
  rw [ENNReal.tendsto_nhds_zero]
  intro ε hε_pos
  -- Replace ε by min ε 1 to ensure finiteness.
  suffices H : ∀ᶠ h : EuclideanSpace ℝ (Fin d) in 𝓝 0,
      eLpNorm (translateBy h f - f) p μ ≤ min ε 1 by
    exact H.mono fun h hh => hh.trans (min_le_left _ _)
  -- Now ε' := min ε 1 ∈ (0, 1] in ENNReal.
  set ε' : ℝ≥0∞ := min ε 1 with hε'_def
  have hε'_pos : 0 < ε' := lt_min hε_pos zero_lt_one
  have hε'_ne_zero : ε' ≠ 0 := hε'_pos.ne'
  have hε'_ne_top : ε' ≠ ∞ := by
    rw [hε'_def]; exact ne_top_of_le_ne_top ENNReal.one_ne_top (min_le_right _ _)
  -- Subdivide ε' into 3 pieces (use ε'/3 for each leg of the triangle).
  set ε3 : ℝ≥0∞ := ε' / 3 with hε3_def
  have h3_ne_top : (3 : ℝ≥0∞) ≠ ∞ := by norm_num
  have h3_ne_zero : (3 : ℝ≥0∞) ≠ 0 := by norm_num
  have hε3_pos : 0 < ε3 := ENNReal.div_pos hε'_ne_zero h3_ne_top
  have hε3_ne_zero : ε3 ≠ 0 := hε3_pos.ne'
  have hε3_ne_top : ε3 ≠ ∞ := ENNReal.div_ne_top hε'_ne_top h3_ne_zero
  -- Step (1): Cc approximant g with eLpNorm (f − g) p μ ≤ ε/3.
  obtain ⟨g, g_supp, hfg, g_cont, g_mem⟩ :=
    hf.exists_hasCompactSupport_eLpNorm_sub_le hp_top hε3_ne_zero
  -- g uniformly continuous (Mathlib: HasCompactSupport + Continuous → UC)
  have g_uc : UniformContinuous g :=
    g_supp.uniformContinuous_of_continuous g_cont
  -- Step (3): sup-norm tendsto for g.
  have g_sup_tend := cc_translation_sup_tendsto (g := g) g_uc
  -- Compact enclosure: tsupport g ⊆ K₀ compact. Set
  -- K := K₀ + closedBall 0 1, compact, hence μ K < ∞.
  set K₀ : Set (EuclideanSpace ℝ (Fin d)) := tsupport g with hK₀_def
  have hK₀_compact : IsCompact K₀ := g_supp
  set K : Set (EuclideanSpace ℝ (Fin d)) :=
    K₀ + Metric.closedBall (0 : EuclideanSpace ℝ (Fin d)) 1 with hK_def
  have hK_compact : IsCompact K :=
    hK₀_compact.add (isCompact_closedBall _ _)
  have hK_meas : MeasurableSet K := hK_compact.isClosed.measurableSet
  have hμK_lt_top : μ K < ∞ := hK_compact.measure_lt_top
  have hμK_ne_top : μ K ≠ ∞ := hμK_lt_top.ne
  have hμK_pow_ne_top : μ K ^ p.toReal⁻¹ ≠ ∞ :=
    ENNReal.rpow_ne_top_of_nonneg (inv_nonneg.mpr hp_pos.le) hμK_ne_top
  -- Define MK as a finite ENNReal upper-bound on μ K ^ (1/p) so that
  -- (1/MK) is positive and finite.
  set MK : ℝ≥0∞ := μ K ^ p.toReal⁻¹ + 1 with hMK_def
  have hMK_ne_top : MK ≠ ∞ := by
    rw [hMK_def]
    exact ENNReal.add_ne_top.mpr ⟨hμK_pow_ne_top, ENNReal.one_ne_top⟩
  have hMK_pos : 0 < MK := lt_of_lt_of_le zero_lt_one (le_add_self)
  have hMK_ne_zero : MK ≠ 0 := hMK_pos.ne'
  -- ε_sup := ε3 / MK as ENNReal, finite and positive.
  set ε_sup : ℝ≥0∞ := ε3 / MK with hε_sup_def
  have hε_sup_pos : 0 < ε_sup := ENNReal.div_pos hε3_ne_zero hMK_ne_top
  have hε_sup_ne_zero : ε_sup ≠ 0 := hε_sup_pos.ne'
  have hε_sup_ne_top : ε_sup ≠ ∞ := ENNReal.div_ne_top hε3_ne_top hMK_ne_zero
  -- Convert ε_sup to a positive real for the sup-norm step.
  set ε_sup_real : ℝ := ε_sup.toReal with hε_sup_real_def
  have hε_sup_real_pos : 0 < ε_sup_real := by
    rw [hε_sup_real_def]
    exact ENNReal.toReal_pos hε_sup_ne_zero hε_sup_ne_top
  have hε_sup_ofReal : ENNReal.ofReal ε_sup_real = ε_sup := by
    rw [hε_sup_real_def, ENNReal.ofReal_toReal hε_sup_ne_top]
  -- Apply step (3) for ε_sup_real to get δ.
  obtain ⟨δ, hδ_pos, hδ⟩ := g_sup_tend ε_sup_real hε_sup_real_pos
  -- The neighborhood of 0: {h : ‖h‖ < δ}.
  refine Filter.eventually_iff_exists_mem.mpr ?_
  refine ⟨Metric.ball (0 : EuclideanSpace ℝ (Fin d)) (min δ 1),
    Metric.ball_mem_nhds 0 (lt_min hδ_pos zero_lt_one), ?_⟩
  intro h hh
  rw [Metric.mem_ball, dist_zero_right] at hh
  have hh_norm_lt_δ : ‖h‖ < δ := lt_of_lt_of_le hh (min_le_left _ _)
  have hh_norm_le_one : ‖h‖ ≤ 1 := le_of_lt (lt_of_lt_of_le hh (min_le_right _ _))
  -- Step (3) result: ‖translateBy h g x - g x‖ ≤ ε_sup_real for all x.
  have h_sup : ∀ x, ‖translateBy h g x - g x‖ ≤ ε_sup_real :=
    hδ h hh_norm_lt_δ
  -- Step (4): support of `translateBy h g - g` ⊆ K.
  have h_supp_sub : Function.support (translateBy h g - g) ⊆ K := by
    intro x hx
    -- If x ∉ K then x ∉ tsupport g and x + h ∉ tsupport g, so g x = 0
    -- and (translateBy h g) x = g (x + h) = 0, contradicting x ∈ support.
    by_contra hxK
    apply hx
    -- Show x ∉ tsupport g and x + h ∉ tsupport g
    have hx_notin_K₀ : x ∉ K₀ := by
      intro hxK₀
      apply hxK
      rw [hK_def]
      refine ⟨x, hxK₀, 0, ?_, ?_⟩
      · simp only [Metric.mem_closedBall, dist_zero_right, norm_zero]
        exact zero_le_one
      · simp
    have hxh_notin_K₀ : x + h ∉ K₀ := by
      intro hxhK₀
      apply hxK
      rw [hK_def]
      refine ⟨x + h, hxhK₀, -h, ?_, ?_⟩
      · simp only [Metric.mem_closedBall, dist_zero_right, norm_neg]
        exact hh_norm_le_one
      · abel_nf
    have hgx : g x = 0 := image_eq_zero_of_notMem_tsupport hx_notin_K₀
    have hgxh : g (x + h) = 0 := image_eq_zero_of_notMem_tsupport hxh_notin_K₀
    change (translateBy h g - g) x = 0
    simp [translateBy, hgx, hgxh, Pi.sub_apply]
  -- Step (4) bound via the helper lemma.
  have h_eLp_bound :
      eLpNorm (translateBy h g - g) p μ ≤
        μ K ^ p.toReal⁻¹ * ENNReal.ofReal ε_sup_real := by
    apply eLpNorm_le_of_support_subset_of_ae_bound hK_meas h_supp_sub
    exact ae_of_all _ h_sup
  -- The bound is ≤ MK * ε_sup = (μ K ^ (1/p) + 1) * (ε3 / MK) ≤ ε3.
  have h_eLp_bound' : eLpNorm (translateBy h g - g) p μ ≤ ε3 := by
    refine h_eLp_bound.trans ?_
    rw [hε_sup_ofReal, hε_sup_def, hMK_def]
    -- (μK^(1/p)) * (ε3 / (μK^(1/p) + 1))
    --   ≤ (μK^(1/p) + 1) * (ε3 / (μK^(1/p) + 1)) = ε3
    have hle : μ K ^ p.toReal⁻¹ ≤ μ K ^ p.toReal⁻¹ + 1 :=
      le_self_add
    calc μ K ^ p.toReal⁻¹ * (ε3 / (μ K ^ p.toReal⁻¹ + 1))
        ≤ (μ K ^ p.toReal⁻¹ + 1) * (ε3 / (μ K ^ p.toReal⁻¹ + 1)) := by
          gcongr
      _ ≤ ε3 := ENNReal.mul_div_le
  -- Translation invariance of f − g:
  have hMemLp_fg : MemLp (f - g) p μ := hf.sub g_mem
  have h_invariance :
      eLpNorm (translateBy h f - translateBy h g) p μ = eLpNorm (f - g) p μ := by
    have : translateBy h f - translateBy h g = translateBy h (f - g) := by
      funext x; simp [translateBy, Pi.sub_apply]
    rw [this]
    exact translateBy_eLpNorm_eq hMemLp_fg.aestronglyMeasurable h
  -- Triangle: eLpNorm (τ_h f − f) p μ
  --   ≤ eLpNorm (τ_h f − τ_h g) p μ + eLpNorm (τ_h g − g) p μ + eLpNorm (g − f) p μ
  -- The first ≤ ε3 (invariance), middle ≤ ε3 (step 4), third = eLpNorm(f - g) ≤ ε3
  -- (note eLpNorm_neg gives g - f = -(f - g) same eLpNorm).
  have h_tri1 :
      eLpNorm (translateBy h f - f) p μ ≤
        eLpNorm (translateBy h f - translateBy h g) p μ +
          eLpNorm (translateBy h g - g) p μ +
          eLpNorm (g - f) p μ := by
    have htriangle1 :
        eLpNorm (translateBy h f - f) p μ ≤
          eLpNorm (translateBy h f - translateBy h g) p μ +
            eLpNorm (translateBy h g - f) p μ := by
      have heq : translateBy h f - f =
          (translateBy h f - translateBy h g) + (translateBy h g - f) := by
        ext x; simp [Pi.sub_apply, Pi.add_apply]
      rw [heq]
      have hLp1 : MemLp (translateBy h f - translateBy h g) p μ :=
        (MemLp.translateBy_memLp hf h).sub (MemLp.translateBy_memLp g_mem h)
      have hLp2 : MemLp (translateBy h g - f) p μ :=
        (MemLp.translateBy_memLp g_mem h).sub hf
      exact eLpNorm_add_le hLp1.aestronglyMeasurable hLp2.aestronglyMeasurable hp1
    have htriangle2 :
        eLpNorm (translateBy h g - f) p μ ≤
          eLpNorm (translateBy h g - g) p μ + eLpNorm (g - f) p μ := by
      have heq : translateBy h g - f =
          (translateBy h g - g) + (g - f) := by
        ext x; simp [Pi.sub_apply, Pi.add_apply]
      rw [heq]
      have hLp1 : MemLp (translateBy h g - g) p μ :=
        (MemLp.translateBy_memLp g_mem h).sub g_mem
      have hLp2 : MemLp (g - f) p μ := g_mem.sub hf
      exact eLpNorm_add_le hLp1.aestronglyMeasurable hLp2.aestronglyMeasurable hp1
    calc eLpNorm (translateBy h f - f) p μ
        ≤ eLpNorm (translateBy h f - translateBy h g) p μ +
            eLpNorm (translateBy h g - f) p μ := htriangle1
      _ ≤ eLpNorm (translateBy h f - translateBy h g) p μ +
            (eLpNorm (translateBy h g - g) p μ + eLpNorm (g - f) p μ) := by
          exact add_le_add le_rfl htriangle2
      _ = eLpNorm (translateBy h f - translateBy h g) p μ +
            eLpNorm (translateBy h g - g) p μ + eLpNorm (g - f) p μ := by
          rw [add_assoc]
  -- eLpNorm (g - f) p μ = eLpNorm (f - g) p μ
  have hgf_eq_fg : eLpNorm (g - f) p μ = eLpNorm (f - g) p μ := by
    have : g - f = -(f - g) := by funext x; simp [Pi.sub_apply, Pi.neg_apply]
    rw [this, eLpNorm_neg]
  -- Combine: each leg ≤ ε3, total ≤ 3 * ε3 = ε'.
  have h_total :
      eLpNorm (translateBy h f - f) p μ ≤ ε3 + ε3 + ε3 := by
    refine h_tri1.trans ?_
    have h1 : eLpNorm (translateBy h f - translateBy h g) p μ ≤ ε3 := by
      rw [h_invariance]; exact hfg
    have h2 : eLpNorm (translateBy h g - g) p μ ≤ ε3 := h_eLp_bound'
    have h3 : eLpNorm (g - f) p μ ≤ ε3 := by rw [hgf_eq_fg]; exact hfg
    exact add_le_add (add_le_add h1 h2) h3
  -- 3 * ε3 = 3 * (ε' / 3) = ε' (since ε' ≠ ∞).
  have h3ε3 : ε3 + ε3 + ε3 = ε' := by
    rw [hε3_def]
    -- 3 * (ε'/3) = ε' for ε' ≠ ∞ and ε' ≠ 0 (we have both).
    have hcancel : (3 : ℝ≥0∞) * (ε' / 3) = ε' :=
      ENNReal.mul_div_cancel h3_ne_zero h3_ne_top
    -- ε'/3 + ε'/3 + ε'/3 = 3 * (ε'/3)
    have h_three_add : ε' / 3 + ε' / 3 + ε' / 3 = (3 : ℝ≥0∞) * (ε' / 3) := by
      have : (3 : ℝ≥0∞) = 1 + 1 + 1 := by norm_num
      rw [this, add_mul, add_mul, one_mul]
    rw [h_three_add, hcancel]
  rw [h3ε3] at h_total
  exact h_total

/-! ## §5. PATTERN-007 inverted-for-Mathlib audit (this file)

Strip "L^p", "translation", "ε", "fixed `f`", "Cc-density":

> "On a homogeneous space, the action of a continuous group on a
> finite-norm function space is strongly continuous at the identity."

The principle survives strip — this is the Banach-space version of
the standard fact that group actions on suitable function spaces
are strongly continuous. **Adds genuine analytic content.**

What this file's discharge contributes vs the scaffold:
* §2: `translateBy_eLpNorm_eq` and `MemLp.translateBy_memLp` are
  real theorems with full proofs. (Composition of
  `eLpNorm_comp_measurePreserving` with translation-as-MP.)
* §3: `cc_translation_sup_tendsto` is a fully-proved unfolding of
  uniform continuity into the metric `Tendsto` form needed by §4.
* §4: `eLpNorm_le_of_support_subset_of_ae_bound` packages the
  `eLpNorm_restrict_eq_of_support_subset` + `eLpNorm_le_of_ae_bound`
  chain — fully proved.
* §4: `tendsto_eLpNorm_translateBy_sub_zero` (main theorem) is
  fully proved (final-sorry agent, 2026-05-09). All five steps of
  the 3-ε argument are closed, with the compact-enclosure lift
  `K := tsupport g + closedBall 0 1`.

**Verdict against PL-012/PL-020 buckets**: bucket (1) —
**full discharge, sorry-free**.

## Anti-laundering self-demote

The proof is now complete. No `sorry`, no new axioms (`#print axioms`
shows only `[propext, Classical.choice, Quot.sound]`). The proof
sequence (translation invariance → Cc-density → uniform continuity
→ compact-enclosure indicator bound → triangle) is the textbook
Folland/Rudin argument; it is genuine Lean glue around existing
Mathlib primitives, not a laundered rename. The helper
`eLpNorm_le_of_support_subset_of_ae_bound` is reusable and would
be a natural Mathlib PR target.
-/

end

end ZtareProofs.SQ3.PR1
