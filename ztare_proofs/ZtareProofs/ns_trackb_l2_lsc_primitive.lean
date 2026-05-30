/-
# L² LSC under weak convergence — scalar primitive

This file proves the scalar version of:

  If `f n ⇀ f∞` weakly in L²(μ) (i.e., `∫ (f n) g → ∫ f∞ g` for every L² test
  `g`), and `∫ f∞²` is finite, then

      ∫ f∞² ≤ liminf (∫ (f n)²)                              (*)

This is the only PDE-content obligation in
`ns_trackb_lean_dojo_energy_bridge.lean` once the kineticEnergy /
enstrophy LSC obligation is reduced to the L² norm-squared LSC under
weak limits via Bochner integration.

## Proof strategy (Hilbert-space)

  Test `g := f∞` in the weak-convergence hypothesis:
      lim_n  C n = A,
  where  C n := ∫ (f n) · f∞   and   A := ∫ f∞ · f∞ = ∫ f∞².

  Cauchy–Schwarz on the bilinear pairing:
      C n ^ 2 ≤ B n · A,    where   B n := ∫ (f n)².

  Therefore (after squaring `Tendsto`):
      A^2 = lim_n (C n)^2  ≤  liminf_n (B n · A)  =  A · liminf_n B n.
  If `A = 0`, the conclusion is trivial.  If `A > 0`, divide to obtain
  `A ≤ liminf B`.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.Topology.Order.LiminfLimsup
import Mathlib.Order.LiminfLimsup
import Mathlib.Analysis.SpecialFunctions.Pow.NNReal

open MeasureTheory Filter Topology
open scoped ENNReal NNReal

namespace ZtareProofs

/-! ### Auxiliary lemma: positive-constant pullout for `liminf` over `ℝ`

The identity `liminf_n (u n * c) = (liminf_n u n) * c` for `c > 0` on a
countably-generated `NeBot` filter, proved via `OrderIso.liminf_apply`
applied to the order isomorphism `OrderIso.mulRight₀ c hc : ℝ ≃o ℝ`.
Sorry-free. -/

lemma liminf_mul_const_of_pos_real
    {ι : Type*} {l : Filter ι} [IsCountablyGenerated l] [l.NeBot]
    {u : ι → ℝ} (hu : l.IsBoundedUnder (· ≤ ·) u)
    (hu' : l.IsBoundedUnder (· ≥ ·) u)
    {c : ℝ} (hc : 0 < c) :
    Filter.liminf (fun n => u n * c) l = (Filter.liminf u l) * c := by
  -- Multiplication by `c > 0` is the order iso `OrderIso.mulRight₀ c hc`.
  let g : ℝ ≃o ℝ := OrderIso.mulRight₀ c hc
  -- The two boundedness side-conditions for `g ∘ u` follow from those for
  -- `u`, because `g` is an order iso (hence `IsBoundedUnder`-preserving in
  -- both directions).  We package those as plain monotonicity uses.
  have hgu : l.IsBoundedUnder (· ≥ ·) fun x => g (u x) := by
    rcases hu' with ⟨b, hb⟩
    refine ⟨g b, ?_⟩
    rw [Filter.eventually_map] at hb ⊢
    filter_upwards [hb] with n hn using g.le_iff_le.mpr hn
  have hgu_co : l.IsCoboundedUnder (· ≥ ·) fun x => g (u x) := by
    -- Bounded above ⇒ cobounded below for ℝ.  We need `IsBoundedUnder (·≤·)`
    -- on `g ∘ u`, which follows from `hu` via `g`'s monotonicity.
    have hgu_le : l.IsBoundedUnder (· ≤ ·) fun x => g (u x) := by
      rcases hu with ⟨M, hM⟩
      refine ⟨g M, ?_⟩
      rw [Filter.eventually_map] at hM ⊢
      filter_upwards [hM] with n hn using g.le_iff_le.mpr hn
    exact hgu_le.isCoboundedUnder_ge
  have hu_co : l.IsCoboundedUnder (· ≥ ·) u := hu.isCoboundedUnder_ge
  have key : g (Filter.liminf u l) = Filter.liminf (fun x => g (u x)) l :=
    OrderIso.liminf_apply g hu' hu_co hgu hgu_co
  -- Unpack: `g x = x * c`.  Both sides become explicit.
  have hg_eq : ∀ x : ℝ, g x = x * c := by
    intro x
    show OrderIso.mulRight₀ c hc x = x * c
    rfl
  -- Rewrite the LHS and RHS of `key` using hg_eq.
  have lhs_eq : g (Filter.liminf u l) = (Filter.liminf u l) * c := hg_eq _
  have rhs_eq : Filter.liminf (fun x => g (u x)) l
                  = Filter.liminf (fun n => u n * c) l := by
    apply congrArg (fun f => Filter.liminf f l)
    funext x; exact hg_eq (u x)
  rw [lhs_eq, rhs_eq] at key
  exact key.symm

/-- Inputs to the scalar L² lower-semicontinuity primitive. -/
structure L2WeakLSCData where
  /-- Index sequence (will be `ℕ` or any countably-generated filter). -/
  ι : Type*
  /-- Filter on `ι`. -/
  l : Filter ι
  /-- The cross-term `C n := ∫ (f n) · f∞ ∂μ`. -/
  cross : ι → ℝ
  /-- The L² norm² of the limit `A := ∫ f∞² ∂μ`. -/
  limitL2 : ℝ
  /-- The L² norm² of `f n`, `B n := ∫ (f n)² ∂μ`. -/
  seqL2 : ι → ℝ

namespace L2WeakLSCData

/-- Hypotheses of the scalar primitive, packaged as a record so that the
algebraic core of the proof is decoupled from concrete Mathlib lemma calls.

Discharge with the obvious Mathlib companions:
* `weak_conv_at_self` — supplied by the user (this *is* the weak-convergence
  hypothesis applied with the test function `g := f∞`).
* `cauchy_schwarz` — `(∫ f g)² ≤ (∫ f²) · (∫ g²)`.  Direct corollary of
  `MeasureTheory.integral_mul_le_Lp_mul_Lq_of_nonneg` with `p = q = 2`
  applied to `|f n|`, `|f∞|`, then squared, and finally upgraded from
  `(∫ |f g|)² ≤ …` to `(∫ f g)² ≤ …` via Jensen / `abs_integral_le_integral_abs`.
* `seqL2_nonneg` — `∫ (f n)² ≥ 0` is `MeasureTheory.integral_nonneg`.
* `limitL2_nonneg` — `∫ f∞² ≥ 0` is `MeasureTheory.integral_nonneg`.
* `seqL2_isBoundedUnder` — uniform L² bound, comes from energy estimate.
-/
structure Hypotheses (D : L2WeakLSCData) : Prop where
  /-- Filter is countably generated (e.g. `atTop` on `ℕ`). -/
  countablyGenerated : IsCountablyGenerated D.l
  /-- Filter is `NeBot` (e.g. `atTop` on `ℕ`). -/
  neBot : D.l.NeBot
  /-- Weak convergence applied to the test `g := f∞`:  `C n → A`. -/
  weak_conv_at_self :
    Tendsto D.cross D.l (𝓝 D.limitL2)
  /-- Cauchy–Schwarz for the cross term: `C n² ≤ B n · A`. -/
  cauchy_schwarz :
    ∀ᶠ n in D.l, (D.cross n) ^ 2 ≤ D.seqL2 n * D.limitL2
  /-- `B n ≥ 0`. -/
  seqL2_nonneg : ∀ᶠ n in D.l, 0 ≤ D.seqL2 n
  /-- `A ≥ 0`. -/
  limitL2_nonneg : 0 ≤ D.limitL2
  /-- Eventual upper bound on `B n` to keep the `liminf` finite-valued.
  Discharge with the uniform L² bound that comes from the energy estimate. -/
  seqL2_isBoundedUnder :
    D.l.IsBoundedUnder (· ≤ ·) D.seqL2

end L2WeakLSCData

open L2WeakLSCData

/--  **Scalar L² LSC under weak limits.**

If `f n ⇀ f∞` weakly in L²(μ) (encoded as `weak_conv_at_self`: the cross
pairing against the limit converges to the limit's own L² norm), and the
sequence is uniformly L²-bounded, then

  `∫ f∞² ≤ liminf (∫ (f n)²)`.

The proof is the Hilbert-space "square the weak inner product" trick;
Cauchy–Schwarz is supplied as a structural hypothesis (see the `Hypotheses`
record for the Mathlib lemmas that discharge each side-condition). -/
theorem l2_norm_squared_lsc_under_weak_limit
    (D : L2WeakLSCData) (H : D.Hypotheses) :
    D.limitL2 ≤ Filter.liminf D.seqL2 D.l := by
  haveI : D.l.NeBot := H.neBot
  haveI : IsCountablyGenerated D.l := H.countablyGenerated
  -- Local abbreviations.
  set A : ℝ := D.limitL2 with hA_def
  set B : D.ι → ℝ := D.seqL2 with hB_def
  set C : D.ι → ℝ := D.cross with hC_def
  -- Unfolded versions of the hypotheses, in terms of A, B, C.
  have hA_nn : 0 ≤ A := H.limitL2_nonneg
  have hB_nn : ∀ᶠ n in D.l, 0 ≤ B n := H.seqL2_nonneg
  have hCS : ∀ᶠ n in D.l, (C n) ^ 2 ≤ B n * A := H.cauchy_schwarz
  have hC_to_A : Tendsto C D.l (𝓝 A) := H.weak_conv_at_self
  have hB_bdd : D.l.IsBoundedUnder (· ≤ ·) B := H.seqL2_isBoundedUnder
  ----------------------------------------------------------------------------
  -- Step 1.  `(C n) ^ 2 → A^2`.
  ----------------------------------------------------------------------------
  have hC2_to_A2 : Tendsto (fun n => (C n) ^ 2) D.l (𝓝 (A ^ 2)) := by
    have := hC_to_A.mul hC_to_A
    simpa [pow_two] using this
  have h_liminf_C2 : Filter.liminf (fun n => (C n) ^ 2) D.l = A ^ 2 :=
    hC2_to_A2.liminf_eq
  ----------------------------------------------------------------------------
  -- Step 2.  Eventually `0 ≤ B n * A`.
  ----------------------------------------------------------------------------
  have hBA_nn : ∀ᶠ n in D.l, 0 ≤ B n * A :=
    hB_nn.mono fun n hn => mul_nonneg hn hA_nn
  ----------------------------------------------------------------------------
  -- Step 3.  `liminf (C n)^2 ≤ liminf (B n · A)` by monotonicity.
  -- We must supply `IsBoundedUnder (· ≥ ·) (C^2)` (lower bound on C²) and
  -- `IsCoboundedUnder (· ≥ ·) (B · A)`  (frequent lower bound on B·A).
  ----------------------------------------------------------------------------
  -- Lower bound on (C n)^2:  always ≥ 0.
  have hC2_bdd_below : D.l.IsBoundedUnder (· ≥ ·) (fun n => (C n) ^ 2) := by
    refine ⟨0, ?_⟩
    rw [Filter.eventually_map]
    exact Filter.Eventually.of_forall fun n => sq_nonneg (C n)
  -- B · A is `≥ 0` eventually (from `hBA_nn`), so any `a` satisfying
  -- `∀ᶠ n, a ≤ B n * A` must also satisfy `a ≤ 0`?  No — actually we need
  -- a witness `b` such that any "frequent lower bound" `a` of `B · A`
  -- satisfies `b ≥ a`.  Pick `b := 0` does NOT work because some `a` might
  -- be positive (e.g. if B·A is eventually ≥ 1).  The right witness: any
  -- value of `B n * A` (since the filter is `NeBot`).  We use `Eventually.exists`
  -- against `hBA_nn` to produce a single witness, then let `b := B n₀ * A`.
  --
  -- Cleaner: the *standard* discharge for `IsCoboundedUnder (· ≥ ·)` on a
  -- `NeBot` filter into ℝ is via `IsBoundedUnder.isCoboundedUnder_ge`
  -- when the sequence is bounded above (which we have via `hB_bdd` and
  -- `0 ≤ A`, so `B · A` is bounded above by `M * A`).
  have hBA_bdd_above : D.l.IsBoundedUnder (· ≤ ·) (fun n => B n * A) := by
    rcases hB_bdd with ⟨M, hM⟩
    refine ⟨M * A, ?_⟩
    rw [Filter.eventually_map]
    -- hM : ∀ᶠ x in map B l, x ≤ M.  Convert via eventually_map.
    rw [Filter.eventually_map] at hM
    filter_upwards [hM] with n hn using
      mul_le_mul_of_nonneg_right hn hA_nn
  have hBA_cobdd : D.l.IsCoboundedUnder (· ≥ ·) (fun n => B n * A) :=
    hBA_bdd_above.isCoboundedUnder_ge
  have h_liminf_le :
      Filter.liminf (fun n => (C n) ^ 2) D.l
        ≤ Filter.liminf (fun n => B n * A) D.l :=
    Filter.liminf_le_liminf hCS hC2_bdd_below hBA_cobdd
  -- Hence `A^2 ≤ liminf (B · A)`.
  have h_step3 : A ^ 2 ≤ Filter.liminf (fun n => B n * A) D.l := by
    rw [← h_liminf_C2]; exact h_liminf_le
  ----------------------------------------------------------------------------
  -- Step 4.  Cancel `A` (split on `A = 0` vs `A > 0`).
  ----------------------------------------------------------------------------
  rcases lt_or_eq_of_le hA_nn with hA_pos | hA_zero
  · -- A > 0:  liminf (B · A) = (liminf B) · A, then divide by A.
    have hB_bdd_below : D.l.IsBoundedUnder (· ≥ ·) B := ⟨0, hB_nn⟩
    have h_factor :
        Filter.liminf (fun n => B n * A) D.l
          = (Filter.liminf B D.l) * A :=
      liminf_mul_const_of_pos_real hB_bdd hB_bdd_below hA_pos
    rw [h_factor] at h_step3
    have hAA : A * A ≤ Filter.liminf B D.l * A := by
      simpa [pow_two] using h_step3
    exact le_of_mul_le_mul_right hAA hA_pos
  · -- A = 0: target is `0 ≤ liminf B`.  This is the constant-0 lower bound.
    -- `hA_zero : 0 = A`, so we need `0 ≤ liminf B`.
    have h_zero_le : (0 : ℝ) ≤ Filter.liminf B D.l := by
      -- liminf of a sequence eventually ≥ 0 is ≥ 0.
      have h0 : Filter.liminf (fun _ : D.ι => (0 : ℝ)) D.l = 0 :=
        (tendsto_const_nhds : Tendsto (fun _ : D.ι => (0 : ℝ)) D.l (𝓝 0)).liminf_eq
      have h_const_bdd_below :
          D.l.IsBoundedUnder (· ≥ ·) (fun _ : D.ι => (0 : ℝ)) := by
        refine ⟨0, ?_⟩
        rw [Filter.eventually_map]
        exact Filter.Eventually.of_forall fun _ => le_refl (0 : ℝ)
      have hB_cobdd : D.l.IsCoboundedUnder (· ≥ ·) B :=
        hB_bdd.isCoboundedUnder_ge
      have h_le : Filter.liminf (fun _ : D.ι => (0 : ℝ)) D.l
                    ≤ Filter.liminf B D.l :=
        Filter.liminf_le_liminf hB_nn h_const_bdd_below hB_cobdd
      simpa [h0] using h_le
    -- Conclude.
    rw [← hA_zero]
    exact h_zero_le

/-!
## Closure summary

The main theorem `l2_norm_squared_lsc_under_weak_limit` is **closed
sorry-free** modulo the four explicit `Hypotheses` fields, which are
themselves the standard Mathlib companion lemmas listed in the
`Hypotheses` docstring:

* `weak_conv_at_self`        ← weak L² convergence applied with `g := f∞`
* `cauchy_schwarz`           ← `MeasureTheory.integral_mul_le_Lp_mul_Lq_of_nonneg`
* `seqL2_nonneg`,
  `limitL2_nonneg`           ← `MeasureTheory.integral_nonneg`
* `seqL2_isBoundedUnder`     ← uniform L² energy estimate

The auxiliary `liminf_mul_const_of_pos_real` is also sorry-free, built
from `OrderIso.liminf_apply` applied to `OrderIso.mulRight₀ c hc`.

Every other step of the main argument — the squaring of `Tendsto`,
the `liminf` monotonicity under the `cauchy_schwarz` hypothesis, the
cancellation under positivity, and the `A = 0` degenerate branch — is
sorry-free and discharged by structural Mathlib lemmas alone.

The discharge plan for the four `Hypotheses` fields at any concrete call
site is documented in the `Hypotheses` docstring; in particular,
`cauchy_schwarz` is `MeasureTheory.integral_mul_le_Lp_mul_Lq_of_nonneg`
with `p = q = 2`, applied to `|f n|` and `|f∞|`, then squared and then
upgraded from `|·|` to signed via `abs_integral_le_integral_abs` /
`sq_abs`.

The vector-valued lift to `EuclideanSpace ℝ (Fin n)` is the bridge file's
job: apply this scalar primitive coordinatewise, sum, and use linearity of
`liminf` under `Tendsto` (or, equivalently, finite-sum-of-liminfs).
-/

end ZtareProofs
