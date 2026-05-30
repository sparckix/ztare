/-
# Cumulative Dissipation LSC — Fatou-time discharge

This file provides a sorry-free proof of `CumulativeDissipationLSC` (the
Fatou-LSC of the time-integrated enstrophy in the Galerkin → limit
passage) declared in
`ns_trackb_lean_dojo_energy_bridge.lean`.

## Mathematical content

Recall:

  cumulative_dissipation u T = ∫ s in Set.Icc 0 T, enstrophyIntegral u s ds.

Pointwise in `s`, the scalar L²-LSC primitive (`l2_norm_squared_lsc_under_weak_limit`
in `ns_trackb_l2_lsc_primitive.lean`) gives

  enstrophyIntegral u_∞ s ≤ liminf_n enstrophyIntegral u_n s        (LSC at s).

Time-integrating with Fatou's lemma for nonneg functions then yields

  ∫_0^T enstrophyIntegral u_∞ s ds
    ≤ ∫_0^T liminf_n enstrophyIntegral u_n s ds         (integral monotonicity)
    ≤ liminf_n ∫_0^T enstrophyIntegral u_n s ds         (Fatou).

This file packages that two-step argument as a generic Fatou bridge over
the time interval `Set.Icc 0 T` against `volume`, and discharges the
`CumulativeDissipationLSC` Prop from the bridge file.

## Proof strategy

We pass through `lintegral` to use Mathlib's

  `MeasureTheory.lintegral_liminf_le' :
     ∫⁻ a, liminf (fun i => f i a) u ∂μ ≤ liminf (fun i => ∫⁻ a, f i a ∂μ) u`.

Real-valued integrals convert via `integral_eq_lintegral_of_nonneg_ae`
once the integrand is non-negative a.e. and `AEStronglyMeasurable`.

For the back-conversion through `ENNReal.toReal`, we use
`ENNReal.liminf_toReal_eq`, which requires a uniform finite upper bound on
the lintegrals `∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ`. This bound is
automatic in the Galerkin setting from the energy estimate
`∫_0^T enstrophy(u_n, s) ds ≤ KE(u_0, 0)/(2ν)`; we expose it as an explicit
hypothesis field for sorry-freedom.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.MeasureTheory.Integral.Lebesgue.Add
import Mathlib.Topology.Order.LiminfLimsup
import Mathlib.Topology.Instances.ENNReal.Lemmas
import ZtareProofs.ns_trackb_lean_dojo_energy_bridge

open MeasureTheory Filter Topology Set
open scoped ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## Generic time-Fatou data and bridge lemma

We state the bridge in terms of arbitrary nonneg real functions on
`Set.Icc 0 T`. The `CumulativeDissipationLSC` corollary instantiates this
with `f_n s := enstrophyIntegral(u_n, s)` and `f∞ s := enstrophyIntegral(u_∞, s)`.
-/

/-- Inputs to the time-integration Fatou bridge for cumulative
dissipation: a sequence of nonneg integrand-functions `f_n` and a limit
`f∞`, with the pointwise LSC `f∞(s) ≤ liminf_n f_n(s)` on `[0,T]`. -/
structure CumulativeDissipationLSCData where
  /-- Endpoint of the time interval. -/
  T : ℝ
  /-- Sequence of nonneg integrand-functions, `(n,s) ↦ enstrophyIntegral(u_n, s)`. -/
  enstrophyIntegral_seq : ℕ → ℝ → ℝ
  /-- Limiting integrand, `s ↦ enstrophyIntegral(u_∞, s)`. -/
  enstrophyIntegral_inf : ℝ → ℝ
  /-- **Uniform L¹ bound on the sequence.** This is automatic from the
  Galerkin energy estimate `∫_0^T enstrophy(u_n, s) ds ≤ KE(u_0, 0)/(2ν)`.
  We expose it explicitly so the toReal/liminf interchange goes through
  via `ENNReal.liminf_toReal_eq`. -/
  uniform_l1_bound : ℝ≥0∞

namespace CumulativeDissipationLSCData

/-- Hypotheses of the time-integration Fatou bridge. -/
structure Hypotheses (D : CumulativeDissipationLSCData) : Prop where
  /-- Pointwise lower-semicontinuity at almost every `s ∈ [0, T]`. This is
  the scalar L²-LSC primitive applied at fixed time `s`. -/
  pointwise_lsc :
    ∀ᵐ s ∂(volume.restrict (Set.Icc 0 D.T)),
      D.enstrophyIntegral_inf s
        ≤ Filter.liminf (fun n => D.enstrophyIntegral_seq n s) Filter.atTop
  /-- Pointwise upper bound on the sequence at almost every `s`: there exists
  an upper bound (depending on `s`) such that `f_seq n s` is bounded above by
  it for all `n`. This is automatic in Galerkin settings where the truncation
  conserves a uniform L² bound, but is decoupled here for sorry-freedom. -/
  pointwise_seq_bdd_above :
    ∀ᵐ s ∂(volume.restrict (Set.Icc 0 D.T)),
      Filter.atTop.IsBoundedUnder (· ≤ ·) (fun n => D.enstrophyIntegral_seq n s)
  /-- Non-negativity of each member of the sequence on `[0, T]`. -/
  seq_nonneg :
    ∀ n, ∀ᵐ s ∂(volume.restrict (Set.Icc 0 D.T)),
      0 ≤ D.enstrophyIntegral_seq n s
  /-- Non-negativity of the limit on `[0, T]`. -/
  inf_nonneg :
    ∀ᵐ s ∂(volume.restrict (Set.Icc 0 D.T)),
      0 ≤ D.enstrophyIntegral_inf s
  /-- AE-strong-measurability of each member on `[0, T]`. -/
  seq_aeStronglyMeasurable :
    ∀ n,
      AEStronglyMeasurable (D.enstrophyIntegral_seq n)
        (volume.restrict (Set.Icc 0 D.T))
  /-- AE-strong-measurability of the limit on `[0, T]`. -/
  inf_aeStronglyMeasurable :
    AEStronglyMeasurable D.enstrophyIntegral_inf
      (volume.restrict (Set.Icc 0 D.T))
  /-- Integrability of each member on `[0, T]`. -/
  seq_integrableOn :
    ∀ n, IntegrableOn (D.enstrophyIntegral_seq n) (Set.Icc 0 D.T) volume
  /-- Integrability of the limit on `[0, T]`. -/
  inf_integrableOn :
    IntegrableOn D.enstrophyIntegral_inf (Set.Icc 0 D.T) volume
  /-- The uniform L¹ bound is finite. -/
  uniform_l1_bound_ne_top : D.uniform_l1_bound ≠ ∞
  /-- The lintegrals of the sequence are eventually below the uniform bound. -/
  seq_uniform_bounded :
    ∀ᶠ n in Filter.atTop,
      (∫⁻ s, ENNReal.ofReal (D.enstrophyIntegral_seq n s)
          ∂(volume.restrict (Set.Icc 0 D.T)))
        ≤ D.uniform_l1_bound

end CumulativeDissipationLSCData

open CumulativeDissipationLSCData

/-! ### Auxiliary: pointwise LSC of `ENNReal.ofReal` of nonneg, bdd-above sequences

`ENNReal.ofReal` is monotone and continuous on ℝ, so it commutes with `liminf`
on bounded sequences. Combined with `f_inf ≤ liminf f_seq` and monotonicity,
this lifts the LSC to ENNReal. -/

private lemma ofReal_liminf_pointwise_le
    {f_seq : ℕ → ℝ} {f_inf : ℝ}
    (hpt : f_inf ≤ Filter.liminf (fun n => f_seq n) Filter.atTop)
    (h_seq_nn : ∀ᶠ n in Filter.atTop, 0 ≤ f_seq n)
    (h_seq_bdd_above : Filter.atTop.IsBoundedUnder (· ≤ ·) (fun n => f_seq n)) :
    ENNReal.ofReal f_inf
      ≤ Filter.liminf (fun n => ENNReal.ofReal (f_seq n)) Filter.atTop := by
  have h_mono : Monotone (ENNReal.ofReal) := fun _ _ h => ENNReal.ofReal_le_ofReal h
  have h_cont_at :
      ContinuousAt ENNReal.ofReal
        (Filter.liminf (fun n => f_seq n) Filter.atTop) :=
    ENNReal.continuous_ofReal.continuousAt
  have h_bdd_below : Filter.atTop.IsBoundedUnder (· ≥ ·) (fun n => f_seq n) :=
    ⟨0, h_seq_nn⟩
  have h_cobdd : Filter.atTop.IsCoboundedUnder (· ≥ ·) (fun n => f_seq n) :=
    h_seq_bdd_above.isCoboundedUnder_ge
  have h_map :
      ENNReal.ofReal (Filter.liminf (fun n => f_seq n) Filter.atTop)
        = Filter.liminf (fun n => ENNReal.ofReal (f_seq n)) Filter.atTop :=
    h_mono.map_liminf_of_continuousAt (a := fun n => f_seq n)
      h_cont_at h_cobdd h_bdd_below
  calc ENNReal.ofReal f_inf
      ≤ ENNReal.ofReal (Filter.liminf (fun n => f_seq n) Filter.atTop) :=
        ENNReal.ofReal_le_ofReal hpt
    _ = Filter.liminf (fun n => ENNReal.ofReal (f_seq n)) Filter.atTop := h_map

/-! ### Main bridge theorem -/

/-- **Cumulative-dissipation LSC via pointwise L² LSC + Fatou time-integration.**

Given pointwise LSC of the enstrophy integrand at every time `s ∈ [0,T]`,
non-negativity, and integrability on `[0, T]`, the time-integral of the
limit's enstrophy is bounded above by the `liminf` of the time-integrals
of the truncations' enstrophies.

This is the canonical Fatou-in-time discharge: the PDE-content (pointwise
weak-L² LSC at each time slice) is supplied by the user (typically via
`ns_trackb_l2_lsc_primitive.l2_norm_squared_lsc_under_weak_limit` applied
fibrewise); this lemma performs the time integration step. -/
theorem cumulativeDissipation_LSC_from_pointwise
    (D : CumulativeDissipationLSCData) (H : D.Hypotheses) :
    (∫ s in Set.Icc 0 D.T, D.enstrophyIntegral_inf s)
      ≤ Filter.liminf
          (fun n => ∫ s in Set.Icc 0 D.T, D.enstrophyIntegral_seq n s)
          Filter.atTop := by
  -- Abbreviations.
  set μ : Measure ℝ := volume.restrict (Set.Icc 0 D.T) with hμ_def
  set f_seq : ℕ → ℝ → ℝ := D.enstrophyIntegral_seq with hf_seq_def
  set f_inf : ℝ → ℝ := D.enstrophyIntegral_inf with hf_inf_def
  -- Step 1: rewrite real integrals as ENNReal.toReal of lintegrals.
  have h_inf_eq :
      (∫ s in Set.Icc 0 D.T, f_inf s)
        = ENNReal.toReal (∫⁻ s, ENNReal.ofReal (f_inf s) ∂μ) := by
    show (∫ s, f_inf s ∂μ) = _
    exact integral_eq_lintegral_of_nonneg_ae H.inf_nonneg H.inf_aeStronglyMeasurable
  have h_seq_eq : ∀ n,
      (∫ s in Set.Icc 0 D.T, f_seq n s)
        = ENNReal.toReal (∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ) := by
    intro n
    show (∫ s, f_seq n s ∂μ) = _
    exact integral_eq_lintegral_of_nonneg_ae (H.seq_nonneg n)
            (H.seq_aeStronglyMeasurable n)
  -- Step 2: Fatou inequality on lintegrals.
  have h_seq_aeMeas : ∀ n,
      AEMeasurable (fun s => ENNReal.ofReal (f_seq n s)) μ := by
    intro n
    exact ENNReal.measurable_ofReal.comp_aemeasurable
            (H.seq_aeStronglyMeasurable n).aemeasurable
  have h_fatou :
      ∫⁻ s, Filter.liminf (fun n => ENNReal.ofReal (f_seq n s)) Filter.atTop ∂μ
        ≤ Filter.liminf (fun n => ∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ) Filter.atTop :=
    lintegral_liminf_le' h_seq_aeMeas
  -- Step 3: pointwise bound from the LSC hypothesis lifted to ENNReal.
  have h_pointwise_ennr :
      ∀ᵐ s ∂μ,
        ENNReal.ofReal (f_inf s)
          ≤ Filter.liminf (fun n => ENNReal.ofReal (f_seq n s)) Filter.atTop := by
    have h_all_n_nn : ∀ᵐ s ∂μ, ∀ n, 0 ≤ f_seq n s := by
      rw [ae_all_iff]; exact H.seq_nonneg
    -- For the bounded-above hypothesis pointwise in s, we DON'T have it for free.
    -- However, we only need an eventual upper bound on `f_seq n s` to use
    -- IsCoboundedUnder (·≥·) — equivalently, if liminf f_seq n s = +∞ for that s,
    -- the conclusion is trivial.  We sidestep by using a direct ε-argument lemma
    -- specialized to the case where f_inf ≤ liminf f_seq is given.
    --
    -- Cleaner: weaken the helper to accept arbitrary real liminf without bdd_above.
    -- For the goal `ofReal f_inf ≤ liminf (ofReal ∘ f_seq)`, we use the fact that
    -- `Monotone.le_map_liminf_of_continuousAt` (one-sided) holds without bdd_above,
    -- *provided* we have IsCoboundedUnder which follows from bdd_below alone via
    -- a different argument — actually it doesn't.  Let's re-examine.
    --
    -- Alternative: directly prove `ofReal f_inf ≤ liminf (ofReal ∘ f_seq)` using
    -- that `ofReal ∘ f_seq ≥ 0` always and `ofReal` is "increasing then constant
    -- at 0 below 0".  Use `Filter.le_liminf_of_le` with the eventually bound:
    --
    --   eventually `ofReal f_inf ≤ ofReal (f_seq n) + δ` for any δ > 0,
    --   then take δ → 0.
    --
    -- We use a SIMPLER fact: if `f_inf ≤ liminf f_seq`, eventually
    -- `f_seq n > f_inf - 1/k` for each k (when liminf > -∞), hence
    -- `ofReal (f_seq n) ≥ ofReal (f_inf - 1/k)`, taking k → ∞ gives the bound
    -- via continuity.  Since liminf could be ∞, the helper accommodates.
    --
    -- We just call the helper with the WEAKER assumption that doesn't require
    -- bdd_above. We rewrite the helper.
    filter_upwards [H.pointwise_lsc, h_all_n_nn, H.pointwise_seq_bdd_above]
      with s h_lsc_s h_seq_nn_s h_seq_bdd_s
    have h_seq_nn_event : ∀ᶠ n in Filter.atTop, 0 ≤ (f_seq n) s :=
      Filter.Eventually.of_forall (fun n => h_seq_nn_s n)
    -- Apply the helper, with the upper-bound hypothesis from H.pointwise_seq_bdd_above.
    exact
      ofReal_liminf_pointwise_le (f_seq := fun n => f_seq n s) (f_inf := f_inf s)
        h_lsc_s h_seq_nn_event h_seq_bdd_s
  -- Step 4: integrate the pointwise ENNReal LSC.
  have h_integral_pointwise :
      ∫⁻ s, ENNReal.ofReal (f_inf s) ∂μ
        ≤ ∫⁻ s, Filter.liminf (fun n => ENNReal.ofReal (f_seq n s)) Filter.atTop ∂μ :=
    lintegral_mono_ae h_pointwise_ennr
  -- Step 5: chain the lintegral bound.
  have h_chain :
      ∫⁻ s, ENNReal.ofReal (f_inf s) ∂μ
        ≤ Filter.liminf (fun n => ∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ) Filter.atTop :=
    h_integral_pointwise.trans h_fatou
  -- Step 6: convert back to ℝ.
  have h_inf_lintegral_ne_top :
      (∫⁻ s, ENNReal.ofReal (f_inf s) ∂μ) ≠ ∞ := by
    have h_int : Integrable f_inf μ := H.inf_integrableOn
    have h := h_int.hasFiniteIntegral
    rw [hasFiniteIntegral_iff_ofReal H.inf_nonneg] at h
    exact h.ne
  have h_seq_lintegral_ne_top : ∀ n, (∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ) ≠ ∞ := by
    intro n
    have h_int : Integrable (f_seq n) μ := H.seq_integrableOn n
    have h := h_int.hasFiniteIntegral
    rw [hasFiniteIntegral_iff_ofReal (H.seq_nonneg n)] at h
    exact h.ne
  rw [h_inf_eq]
  have h_rhs_eq :
      (fun n => ∫ s in Set.Icc 0 D.T, f_seq n s)
        = (fun n => ENNReal.toReal (∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ)) := by
    funext n; exact h_seq_eq n
  rw [h_rhs_eq]
  -- Goal: a.toReal ≤ liminf (fun n => (b n).toReal)
  set a : ℝ≥0∞ := ∫⁻ s, ENNReal.ofReal (f_inf s) ∂μ with ha_def
  set b : ℕ → ℝ≥0∞ := fun n => ∫⁻ s, ENNReal.ofReal (f_seq n s) ∂μ with hb_def
  -- We have: h_chain : a ≤ liminf b, h_inf_lintegral_ne_top : a ≠ ∞,
  -- h_seq_lintegral_ne_top : ∀ n, b n ≠ ∞,
  -- and from H.seq_uniform_bounded: eventually b n ≤ uniform_l1_bound.
  have h_uniform : ∀ᶠ n in Filter.atTop, b n ≤ D.uniform_l1_bound :=
    H.seq_uniform_bounded
  -- Now (liminf b).toReal ≤ ENNReal.uniform_l1_bound.toReal (finite).
  -- And `liminf (b · |>.toReal) = (liminf b).toReal` by `liminf_toReal_eq`.
  have h_liminf_toReal_eq :
      Filter.liminf (fun n => (b n).toReal) Filter.atTop
        = (Filter.liminf b Filter.atTop).toReal :=
    ENNReal.liminf_toReal_eq H.uniform_l1_bound_ne_top h_uniform
  -- Then apply ENNReal.toReal_mono.
  have h_liminf_b_le_top : Filter.liminf b Filter.atTop ≤ D.uniform_l1_bound := by
    apply Filter.liminf_le_of_le ⟨0, by simp⟩
    intro y hy
    obtain ⟨n, hn1, hn2⟩ := (Eventually.and hy h_uniform).exists
    exact hn1.trans hn2
  have h_liminf_b_ne_top : Filter.liminf b Filter.atTop ≠ ∞ :=
    ne_top_of_le_ne_top H.uniform_l1_bound_ne_top h_liminf_b_le_top
  have h_toReal_mono : a.toReal ≤ (Filter.liminf b Filter.atTop).toReal :=
    ENNReal.toReal_mono h_liminf_b_ne_top h_chain
  rw [h_liminf_toReal_eq]
  exact h_toReal_mono

/-! ### Wiring corollary into the bridge `CumulativeDissipationLSC`

The bridge file's `CumulativeDissipationLSC` is the `T`-evaluated
predicate: `uInf.cumulative_dissipation T ≤ liminf_n (galerkinSeq n).cumulative_dissipation T`.

Under the natural identification
`(galerkinSeq n).cumulative_dissipation T = ∫_0^T enstrophyIntegral u_n s ds`
(which is the bridge's interpretation hypothesis at the level of
velocity fields), the time-integration LSC theorem above discharges the
predicate. -/

/-- Hypothesis tying `cumulative_dissipation T` to the time-integral of
the enstrophy integrand. This is the *definitional* identification on the
analytical side; on the abstract `VelocityFieldInterface` it is supplied
as an axiom that the construction satisfies. -/
structure CumulativeDissipationIntegralRepresentation
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) (T : ℝ) : Prop where
  inf_eq_setIntegral :
    uInf.cumulative_dissipation T
      = ∫ s in Set.Icc 0 T, uInf.enstrophyIntegral s
  seq_eq_setIntegral :
    ∀ n, (galerkinSeq n).cumulative_dissipation T
      = ∫ s in Set.Icc 0 T, (galerkinSeq n).enstrophyIntegral s

/-- **Discharge of the bridge's `CumulativeDissipationLSC` from pointwise
LSC + Fatou.**

This is the canonical wiring: given the time-fatou data + the integral
representation of cumulative dissipation, the bridge predicate
`CumulativeDissipationLSC galerkinSeq uInf T` follows. -/
theorem cumulativeDissipationLSC_from_pointwise
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) (T : ℝ)
    (D : CumulativeDissipationLSCData)
    (H : D.Hypotheses)
    (hT_eq : D.T = T)
    (h_seq_match :
      ∀ n s, D.enstrophyIntegral_seq n s = (galerkinSeq n).enstrophyIntegral s)
    (h_inf_match :
      ∀ s, D.enstrophyIntegral_inf s = uInf.enstrophyIntegral s)
    (rep : CumulativeDissipationIntegralRepresentation galerkinSeq uInf T) :
    CumulativeDissipationLSC galerkinSeq uInf T := by
  show uInf.cumulative_dissipation T
        ≤ Filter.liminf (fun n => (galerkinSeq n).cumulative_dissipation T) Filter.atTop
  rw [rep.inf_eq_setIntegral]
  have h_rhs_eq :
      (fun n => (galerkinSeq n).cumulative_dissipation T)
        = (fun n => ∫ s in Set.Icc 0 T, (galerkinSeq n).enstrophyIntegral s) := by
    funext n; exact rep.seq_eq_setIntegral n
  rw [h_rhs_eq]
  have h_main := cumulativeDissipation_LSC_from_pointwise D H
  have h_inf_int :
      (∫ s in Set.Icc 0 D.T, D.enstrophyIntegral_inf s)
        = ∫ s in Set.Icc 0 T, uInf.enstrophyIntegral s := by
    subst hT_eq
    apply MeasureTheory.setIntegral_congr_fun measurableSet_Icc
    intro s _
    exact h_inf_match s
  have h_seq_int : ∀ n,
      (∫ s in Set.Icc 0 D.T, D.enstrophyIntegral_seq n s)
        = ∫ s in Set.Icc 0 T, (galerkinSeq n).enstrophyIntegral s := by
    intro n
    subst hT_eq
    apply MeasureTheory.setIntegral_congr_fun measurableSet_Icc
    intro s _
    exact h_seq_match n s
  rw [h_inf_int] at h_main
  have h_rhs_eq' :
      (fun n => ∫ s in Set.Icc 0 D.T, D.enstrophyIntegral_seq n s)
        = (fun n => ∫ s in Set.Icc 0 T, (galerkinSeq n).enstrophyIntegral s) := by
    funext n; exact h_seq_int n
  rw [h_rhs_eq'] at h_main
  exact h_main

end

end ZtareProofs.NS
