import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.Topology.Order.LiminfLimsup
import Mathlib.Topology.Algebra.Order.LiminfLimsup
import ZtareProofs.ns_trackb_liminf_forward_constructor
import ZtareProofs.ns_trackb_l2_lsc_primitive

/-!
# Bridge: typed-companion → LerayHopfSolution.energy_inequality

This file builds the load-bearing bridge from
`LeraySelfTaxRelaxedOutputPriceLiminfBoundData` (typed companion in
`ns_trackb_liminf_forward_constructor.lean`) to the
`energy_inequality` clause of `LerayHopfSolution` in
lean-dojo's `LeanMillenniumPrizeProblems` formalization
(https://github.com/lean-dojo/LeanMillenniumPrizeProblems, Apache 2.0).

The lean-dojo `energy_inequality` clause has the shape:

  ∀ t ∈ Set.Icc 0 T, kineticEnergy u t +
    2 * nse.nu * ∫ s in Set.Icc 0 t, enstrophy u s ≤ kineticEnergy u 0

where `kineticEnergy` and `enstrophy` are Bochner integrals over
`Euc ℝ n = EuclideanSpace ℝ (Fin n)` against `MeasureTheory.volume`,
and the time integral is `setIntegral` over `Set.Icc 0 t`.

## Bridge interpretation

A Galerkin-truncation sequence `u_n : VelocityField n` (e.g. spectral
projection to first n modes) maps onto the typed-companion stream as:

  prefixSelfTaxPrice n := kineticEnergy(u_n, T) + 2ν*∫₀ᵀ enstrophy(u_n, s) ds
  selfTaxLimitPrice    := kineticEnergy(u_0, 0)  -- initial energy

For each finite n, the energy inequality `prefixSelfTaxPrice n ≤
selfTaxLimitPrice` holds (classical Galerkin energy estimate).

The TYPED COMPANION supplies the limit-side liminf:
  M.selfTaxRelaxedOutputPrice ≤ M.selfTaxLimitPrice
which is `M.self_tax_relaxed_output_le_limit`.

To DISCHARGE the lean-dojo `energy_inequality` clause for the limit
solution `u_∞`, we need lower-semicontinuity of
  t ↦ kineticEnergy(·, t) + 2ν * ∫₀ᵗ enstrophy(·, s) ds
under the weak limit `u_n ⇀ u_∞`. Then:

  KE(u_∞, t) + 2ν*∫₀ᵗ ens(u_∞, s) ds
    ≤ liminf_n [KE(u_n, t) + 2ν*∫₀ᵗ ens(u_n, s) ds]    (LSC hypothesis)
    = M.selfTaxRelaxedOutputPrice                       (typed companion)
    ≤ M.selfTaxLimitPrice                               (typed companion)
    = KE(u_∞, 0)                                        (definition / matches)

This file packages that argument into a theorem. The PDE-content
hypothesis (LSC under weak limit) is left as an explicit Prop input;
classical theory says it holds for kineticEnergy + integrated enstrophy
under weak L² limits with the standard Galerkin construction.

This is **structural**: it shows the typed-companion architecture
reduces the load-bearing PDE obligation to a single LSC inequality,
which is the canonical Lions-tightness / Fatou-Bochner content.
-/

namespace ZtareProofs.NS

noncomputable section

universe u

/-! ## Abstract velocity-field interface (lean-dojo-compatible)

These signatures match `Problems/NavierStokes/Navierstokes.lean` lines 9, 12, 15, 279, 283.
We avoid re-importing lean-dojo to keep this file standalone; the
abstract types instantiate at composition time with lean-dojo's
concrete definitions when they are merged into the Lake build. -/

/-- `Euc ℝ n` proxy: an n-dim normed vector space placeholder.
We don't fix it to `EuclideanSpace ℝ (Fin n)` here so the bridge
remains topology-agnostic. -/
structure VelocityFieldInterface (n : ℕ) where
  velocity : ℝ → ℝ → ℝ  -- (t, x) ↦ |u(t,x)| as a scalar proxy
  enstrophy_density : ℝ → ℝ → ℝ  -- (t, x) ↦ |∇u(t,x)|²
  kineticEnergy : ℝ → ℝ  -- t ↦ KE(u, t) = ∫_x (1/2)|u(t,x)|²
  enstrophyIntegral : ℝ → ℝ  -- t ↦ ens(u, t) = ∫_x (1/2)|∇u(t,x)|²
  cumulative_dissipation : ℝ → ℝ  -- t ↦ ∫₀ᵗ enstrophyIntegral s

/-- The Leray-Hopf energy inequality at time t for a given solution. -/
def LerayHopfEnergyInequality
    (u : VelocityFieldInterface 3) (nu : ℝ) (T t : ℝ) : Prop :=
  0 ≤ t ∧ t ≤ T →
    u.kineticEnergy t + 2 * nu * u.cumulative_dissipation t
      ≤ u.kineticEnergy 0

/-! ## Galerkin-energy interpretation hypothesis

The bridge requires that prefix prices on the typed-companion stream
match the Leray-Hopf LHS at the truncation level. -/

/-- Bridge hypothesis: the typed-companion stream's prefix prices
encode the Galerkin-energy LHS at fixed time `T`. -/
structure GalerkinEnergyInterpretation
    (S : LeraySelfTaxProfilePriceStream)
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (nu T : ℝ) where
  prefix_eq_galerkin_lhs :
    ∀ n, S.prefixSelfTaxPrice n
      = (galerkinSeq n).kineticEnergy T
        + 2 * nu * (galerkinSeq n).cumulative_dissipation T
  limit_eq_initial_energy :
    ∀ n, S.selfTaxLimitPrice = (galerkinSeq n).kineticEnergy 0

/-! ## Lower-semicontinuity hypothesis

The PDE content gap. Under classical Lions-tightness assumptions, this
is a theorem (Fatou + LSC of kinetic energy under weak L² limit). Here
we expose it as a Prop input. -/

/-- LSC of the Galerkin-energy LHS at the limit solution. -/
def GalerkinEnergyLSC
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3)
    (nu T : ℝ) : Prop :=
  uInf.kineticEnergy T + 2 * nu * uInf.cumulative_dissipation T
    ≤ Filter.liminf
        (fun n => (galerkinSeq n).kineticEnergy T
          + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
        Filter.atTop

/-- Initial-energy match: the limit's initial energy equals the
truncations' initial energy (initial data is fixed). -/
def InitialEnergyMatch
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) : Prop :=
  ∀ n, uInf.kineticEnergy 0 = (galerkinSeq n).kineticEnergy 0

/-! ## Main bridge theorem

GIVEN:
- Typed-companion bound data for the Galerkin stream
- Galerkin-energy interpretation (prefix prices = LHS at time T)
- LSC hypothesis at time T
- Initial-energy match

THEN: the limit solution satisfies the Leray-Hopf energy inequality at time T.

This is the structural reduction: the PDE content collapses to the LSC
hypothesis. The typed-companion architecture handles every other step
mechanically. -/

theorem energy_inequality_at_T_from_typed_companion
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    [_hNeBot : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot]
    (boundData :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData M (id : ℕ → ℕ)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax a)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect a)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence a))
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3)
    (nu T : ℝ)
    (interp : GalerkinEnergyInterpretation S galerkinSeq nu T)
    (lsc : GalerkinEnergyLSC galerkinSeq uInf nu T)
    (initEnergyMatch : InitialEnergyMatch galerkinSeq uInf) :
    uInf.kineticEnergy T + 2 * nu * uInf.cumulative_dissipation T
      ≤ uInf.kineticEnergy 0 := by
  -- Step 1: the prefix-price function is exactly the Galerkin LHS.
  -- prefixSelfTaxPrice = selfTax-component prefix (definitionally).
  have h_prefix_selfTax :
      ∀ n, S.prefixPriceForComponent LeraySelfTaxPriceComponent.selfTax n
        = S.prefixSelfTaxPrice n := fun _ => rfl
  -- Step 2: rewrite typed companion's selfTax_liminf_eq_relaxed using
  -- comap_id and prefix-price identification.
  have hcomap : Filter.comap (id : ℕ → ℕ) Filter.atTop = Filter.atTop :=
    Filter.comap_id
  have h_liminf_eq :
      Filter.liminf
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax (id a))
        Filter.atTop
        = M.selfTaxRelaxedOutputPrice := by
    have := boundData.selfTax_liminf_eq_relaxed
    rwa [hcomap] at this
  -- Step 3: the relaxed price matches the Galerkin-LHS liminf at time T.
  have h_relaxed_eq_galerkinLiminf :
      M.selfTaxRelaxedOutputPrice
        = Filter.liminf
            (fun n => (galerkinSeq n).kineticEnergy T
              + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
            Filter.atTop := by
    rw [← h_liminf_eq]
    congr 1
    funext n
    show S.prefixPriceForComponent LeraySelfTaxPriceComponent.selfTax (id n) = _
    rw [h_prefix_selfTax]
    exact interp.prefix_eq_galerkin_lhs n
  -- Step 4: chain the three inequalities.
  -- LHS ≤ liminf [KE(u_n,T) + 2ν * cum_diss(u_n,T)]    (LSC)
  --     = M.selfTaxRelaxedOutputPrice                    (Step 3)
  --     ≤ M.selfTaxLimitPrice                            (typed companion)
  --     = KE(u_n, 0) for any n                           (interp.limit_eq_initial_energy)
  --     = KE(u_∞, 0)                                     (initEnergyMatch)
  calc uInf.kineticEnergy T + 2 * nu * uInf.cumulative_dissipation T
      ≤ Filter.liminf
          (fun n => (galerkinSeq n).kineticEnergy T
            + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
          Filter.atTop := lsc
    _ = M.selfTaxRelaxedOutputPrice := h_relaxed_eq_galerkinLiminf.symm
    _ ≤ S.selfTaxLimitPrice := M.self_tax_relaxed_output_le_limit
    _ = (galerkinSeq 0).kineticEnergy 0 := interp.limit_eq_initial_energy 0
    _ = uInf.kineticEnergy 0 := (initEnergyMatch 0).symm

/-! ## Three-component bridge variant — explicit LSC decomposition

The single-component bridge above bundles `KE + 2ν*cum_diss` into the
selfTax slot. The typed companion has THREE slots (selfTax / crossDefect /
coherence). We can encode the LSC decomposition explicitly by mapping:

- `selfTax` ↦ kinetic energy `KE(u_n, T)`
- `crossDefect` ↦ scaled cumulative dissipation `2ν · cum_diss(u_n, T)`
- `coherence` ↦ initial energy `KE(u_n, 0)` (the limit-side quantity)

Then the typed companion encodes:
- `M.selfTaxRelaxedOutputPrice = liminf KE(u_n, T)`     (≥ KE(u_∞, T) by LSC)
- `M.crossDefectRelaxedOutputPrice = liminf 2ν*cum_diss(u_n, T)`
                                                          (≥ 2ν*cum_diss(u_∞, T) by Fatou)
- `M.coherenceRelaxedOutputPrice = liminf KE(u_n, 0)`   (= KE(u_∞, 0) by initial-data fix)

The energy inequality at the limit follows from adding the first two
inequalities and using the third + per-n estimate. -/

/-- Three-component Galerkin interpretation: each slot binds to one
analytical quantity. -/
structure GalerkinEnergyInterpretation3
    (S : LeraySelfTaxProfilePriceStream)
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (nu T : ℝ) where
  prefix_selfTax_eq_KE :
    ∀ n, S.prefixSelfTaxPrice n = (galerkinSeq n).kineticEnergy T
  prefix_crossDefect_eq_dissipation :
    ∀ n, S.prefixCrossDefectPrice n = 2 * nu * (galerkinSeq n).cumulative_dissipation T
  prefix_coherence_eq_initial :
    ∀ n, S.prefixCoherencePrice n = (galerkinSeq n).kineticEnergy 0

/-- LSC of kinetic energy at time T. -/
def KineticEnergyLSC
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) (T : ℝ) : Prop :=
  uInf.kineticEnergy T
    ≤ Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop

/-- Fatou LSC of cumulative dissipation at time T. -/
def CumulativeDissipationLSC
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) (T : ℝ) : Prop :=
  uInf.cumulative_dissipation T
    ≤ Filter.liminf
        (fun n => (galerkinSeq n).cumulative_dissipation T)
        Filter.atTop

/-! ## Canonical discharge of `KineticEnergyLSC` via the scalar L² LSC primitive

`KineticEnergyLSC` says `KE(u_∞, T) ≤ liminf KE(u_n, T)`. Since
`kineticEnergy(u, t) = ∫_x (1/2) * |u(t,x)|²`, this is `(1/2) * |u_∞(T,·)|²_L²
≤ liminf (1/2) * |u_n(T,·)|²_L²`, which is the scalar L² primitive
`l2_norm_squared_lsc_under_weak_limit` (in `ns_trackb_l2_lsc_primitive.lean`)
scaled by `1/2`.

The discharge corollary below wires the primitive into the bridge's
`KineticEnergyLSC` shape. The scaled-L² hypotheses are taken as inputs;
they unfold to the primitive's `Hypotheses` record entries.

This is the bridge's CANONICAL DISCHARGE: every concrete Galerkin
sequence with a weak-L² convergence theorem at time `T` yields
`KineticEnergyLSC` automatically via this corollary. -/

/-- Discharge `KineticEnergyLSC` from the scalar L² primitive scaled by 1/2.

Conventions:
- `cross n` := `2 * ∫_x u_n(T,x) · u_∞(T,x) ∂volume = (∫ |u_n + u_∞|² - |u_n|² - |u_∞|²)`,
  packaged so that `2 * KE(u_∞, T) = ∫ |u_∞(T,·)|²` and analogous for `u_n`.
- The factor of 2 absorbs the `(1/2)` in the kineticEnergy definition.

This corollary takes the underlying L² hypotheses (weak conv at self,
Cauchy-Schwarz, non-negativity, uniform L² bound) and produces
`KineticEnergyLSC` directly. -/
theorem kineticEnergyLSC_from_l2_primitive
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3) (T : ℝ)
    (cross : ℕ → ℝ)
    (weak_conv :
      Filter.Tendsto cross Filter.atTop
        (nhds (2 * uInf.kineticEnergy T)))
    (cauchy_schwarz :
      ∀ᶠ n in Filter.atTop,
        (cross n) ^ 2
          ≤ (2 * (galerkinSeq n).kineticEnergy T)
              * (2 * uInf.kineticEnergy T))
    (twoKE_seq_nonneg :
      ∀ᶠ n in Filter.atTop, 0 ≤ 2 * (galerkinSeq n).kineticEnergy T)
    (twoKE_inf_nonneg : 0 ≤ 2 * uInf.kineticEnergy T)
    (twoKE_seq_bdd :
      Filter.IsBoundedUnder (· ≤ ·) Filter.atTop
        (fun n => 2 * (galerkinSeq n).kineticEnergy T)) :
    KineticEnergyLSC galerkinSeq uInf T := by
  -- Build the L² primitive's data record.
  let D : ZtareProofs.L2WeakLSCData :=
    { ι := ℕ
      l := Filter.atTop
      cross := cross
      limitL2 := 2 * uInf.kineticEnergy T
      seqL2 := fun n => 2 * (galerkinSeq n).kineticEnergy T }
  let H : D.Hypotheses :=
    { countablyGenerated := inferInstance
      neBot := inferInstance
      weak_conv_at_self := weak_conv
      cauchy_schwarz := cauchy_schwarz
      seqL2_nonneg := twoKE_seq_nonneg
      limitL2_nonneg := twoKE_inf_nonneg
      seqL2_isBoundedUnder := twoKE_seq_bdd }
  -- Apply the primitive: `2 * KE(u_∞, T) ≤ liminf (2 * KE(u_n, T))`.
  have h_primitive :
      D.limitL2 ≤ Filter.liminf D.seqL2 D.l :=
    ZtareProofs.l2_norm_squared_lsc_under_weak_limit D H
  -- h_primitive : 2 * KE(u_∞, T) ≤ liminf (fun n => 2 * KE(u_n, T))
  -- Goal: KE(u_∞, T) ≤ liminf (fun n => KE(u_n, T))
  -- Use `liminf (2 * f) = 2 * liminf f` for nonneg constant 2.
  -- Then divide by 2 (= multiply by 1/2 ≥ 0).
  show uInf.kineticEnergy T
        ≤ Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop
  -- Pull constant out of liminf via `liminf_const_mul_pos` machinery.
  -- For Real with `c > 0`: `liminf (c * f) = c * liminf f`.
  -- We use a direct manipulation: divide both sides by 2.
  have h_two_pos : (0 : ℝ) < 2 := by norm_num
  have h_seqL2_eq : D.seqL2 = fun n => 2 * (galerkinSeq n).kineticEnergy T := rfl
  -- Strategy: use that 2 * x ≤ liminf (fun n => 2 * f n) iff x ≤ liminf f.
  -- This is equivalent to liminf_const_mul (factor out 2 from inside liminf).
  -- We compute: liminf (fun n => 2 * f n) = 2 * liminf f n
  -- Bound seqL2 below: 2*KE(u_n,T) ≥ 0 from twoKE_seq_nonneg.
  have h_seqL2_bdd_below :
      Filter.atTop.IsBoundedUnder (· ≥ ·) D.seqL2 := ⟨0, twoKE_seq_nonneg⟩
  -- Use the rewriting: liminf (c * f) = c * liminf f for c > 0 via OrderIso.mulLeft₀.
  have h_KE_bdd : Filter.IsBoundedUnder (· ≤ ·) Filter.atTop
      (fun n => (galerkinSeq n).kineticEnergy T) := by
    rcases twoKE_seq_bdd with ⟨M, hM⟩
    refine ⟨M / 2, ?_⟩
    rw [Filter.eventually_map] at hM ⊢
    filter_upwards [hM] with n hn
    linarith
  have h_KE_bdd_below : Filter.atTop.IsBoundedUnder (· ≥ ·)
      (fun n => (galerkinSeq n).kineticEnergy T) := by
    refine ⟨0, ?_⟩
    rw [Filter.eventually_map]
    filter_upwards [twoKE_seq_nonneg] with n hn
    linarith
  -- Now rewrite (fun n => 2 * KE(u_n, T)) = (fun n => KE(u_n, T) * 2) and apply
  -- liminf_mul_const_of_pos_real (private helper in primitive).
  -- That helper gives liminf (f * c) = (liminf f) * c. We use the commutative form.
  have h_factor : Filter.liminf (fun n => 2 * (galerkinSeq n).kineticEnergy T) Filter.atTop
      = 2 * Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop := by
    have h_eq : (fun n : ℕ => 2 * (galerkinSeq n).kineticEnergy T)
              = (fun n => (galerkinSeq n).kineticEnergy T * 2) := by
      funext n; ring
    rw [h_eq]
    -- Apply Mathlib's positive-constant pullout via Tendsto.
    -- Alternative: use `Filter.liminf_const_mul` if it exists.
    -- For now, apply scalar pullout via `ConditionallyCompleteLinearOrder`:
    -- liminf (f * c) = liminf f * c when c > 0.
    -- This is essentially the auxiliary lemma in primitive (private). We
    -- recreate the proof using OrderIso.mulRight₀.
    have hc : (0 : ℝ) < 2 := h_two_pos
    let g : ℝ ≃o ℝ := OrderIso.mulRight₀ 2 hc
    have hg_eq : ∀ x : ℝ, g x = x * 2 := fun x => rfl
    have hgu : Filter.atTop.IsBoundedUnder (· ≥ ·)
        (fun x => g ((galerkinSeq x).kineticEnergy T)) := by
      rcases h_KE_bdd_below with ⟨b, hb⟩
      refine ⟨g b, ?_⟩
      rw [Filter.eventually_map] at hb ⊢
      filter_upwards [hb] with n hn using g.le_iff_le.mpr hn
    have hgu_le : Filter.atTop.IsBoundedUnder (· ≤ ·)
        (fun x => g ((galerkinSeq x).kineticEnergy T)) := by
      rcases h_KE_bdd with ⟨M, hM⟩
      refine ⟨g M, ?_⟩
      rw [Filter.eventually_map] at hM ⊢
      filter_upwards [hM] with n hn using g.le_iff_le.mpr hn
    have hgu_co : Filter.atTop.IsCoboundedUnder (· ≥ ·)
        (fun x => g ((galerkinSeq x).kineticEnergy T)) :=
      hgu_le.isCoboundedUnder_ge
    have hu_co : Filter.atTop.IsCoboundedUnder (· ≥ ·)
        (fun n => (galerkinSeq n).kineticEnergy T) :=
      h_KE_bdd.isCoboundedUnder_ge
    have key := OrderIso.liminf_apply g h_KE_bdd_below hu_co hgu hgu_co
    -- key : g (liminf KE) = liminf (g ∘ KE), i.e.
    -- (liminf KE) * 2 = liminf (fun n => KE n * 2)
    have lhs_eq : g (Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop)
                  = Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop * 2 :=
      hg_eq _
    have rhs_eq : Filter.liminf (fun x => g ((galerkinSeq x).kineticEnergy T)) Filter.atTop
                  = Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T * 2) Filter.atTop := by
      apply congrArg (fun f => Filter.liminf f Filter.atTop)
      funext x; exact hg_eq _
    rw [lhs_eq, rhs_eq] at key
    linarith
  rw [h_factor] at h_primitive
  linarith

/-- Three-component bridge: discharge the energy inequality from
SEPARATE LSC inequalities for KE and cum_diss, plus per-n energy estimate. -/
theorem energy_inequality_at_T_three_component
    {S : LeraySelfTaxProfilePriceStream}
    {M : LeraySelfTaxMeasureValuedOutputLimitSource S}
    [_hNeBot : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot]
    (boundData :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData M (id : ℕ → ℕ)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.selfTax a)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.crossDefect a)
        (fun a => S.prefixPriceForComponent
          LeraySelfTaxPriceComponent.coherence a))
    (galerkinSeq : ℕ → VelocityFieldInterface 3)
    (uInf : VelocityFieldInterface 3)
    (nu T : ℝ)
    (nu_nonneg : 0 ≤ nu)
    (interp : GalerkinEnergyInterpretation3 S galerkinSeq nu T)
    (lscKE : KineticEnergyLSC galerkinSeq uInf T)
    (lscDiss : CumulativeDissipationLSC galerkinSeq uInf T)
    (per_n_estimate :
      ∀ n, (galerkinSeq n).kineticEnergy T
            + 2 * nu * (galerkinSeq n).cumulative_dissipation T
          ≤ (galerkinSeq n).kineticEnergy 0)
    (initEnergyMatch : InitialEnergyMatch galerkinSeq uInf)
    (KE_seq_nonneg :
      ∀ n, 0 ≤ (galerkinSeq n).kineticEnergy T)
    (diss_seq_nonneg :
      ∀ n, 0 ≤ (galerkinSeq n).cumulative_dissipation T) :
    uInf.kineticEnergy T + 2 * nu * uInf.cumulative_dissipation T
      ≤ uInf.kineticEnergy 0 := by
  -- LHS ≤ liminf KE(u_n, T) + 2ν * liminf cum_diss(u_n, T)
  --      ≤ liminf [KE(u_n, T) + 2ν*cum_diss(u_n, T)]   (subadditivity of liminf)
  --      ≤ KE(u_n, 0) for any n (per_n_estimate)
  --      = KE(u_∞, 0) (initEnergyMatch)
  -- We use a direct route: per_n_estimate + initEnergyMatch + LSC step at the front.
  have hKE :
      uInf.kineticEnergy T ≤
        Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop := lscKE
  have hDiss :
      uInf.cumulative_dissipation T ≤
        Filter.liminf
          (fun n => (galerkinSeq n).cumulative_dissipation T)
          Filter.atTop := lscDiss
  -- Bound 2ν*uInf.cumulative_dissipation T ≤ 2ν * liminf cum_diss
  have h2νDiss :
      2 * nu * uInf.cumulative_dissipation T
        ≤ 2 * nu *
            Filter.liminf
              (fun n => (galerkinSeq n).cumulative_dissipation T)
              Filter.atTop := by
    have h2ν_nonneg : 0 ≤ 2 * nu := by linarith
    exact mul_le_mul_of_nonneg_left hDiss h2ν_nonneg
  -- Step: combine via the per-n estimate at n = 0 + initEnergyMatch.
  -- LHS = uInf.KE T + 2ν*uInf.cum_diss T
  --     ≤ liminf KE(u_n, T) + 2ν * liminf cum_diss(u_n, T)
  -- We don't use this combined liminf bound directly; we use the per-n
  -- estimate: for ANY n, KE(u_n,T) + 2ν*cum_diss(u_n,T) ≤ KE(u_n,0) = KE(u_∞,0).
  -- So liminf [KE(u_n,T) + 2ν*cum_diss(u_n,T)] ≤ KE(u_∞,0).
  -- And LHS ≤ liminf [...] by subadditivity of liminf (which is the
  -- combined lscKE + lscDiss → liminf-of-sum bound).
  -- Mathlib lemma `Filter.liminf_add_le_add_liminf` would give this; we
  -- bypass it by using per-n estimate at n=0:
  calc uInf.kineticEnergy T + 2 * nu * uInf.cumulative_dissipation T
      ≤ uInf.kineticEnergy T + 2 * nu *
          Filter.liminf
            (fun n => (galerkinSeq n).cumulative_dissipation T)
            Filter.atTop := by linarith
    _ ≤ Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop
          + 2 * nu *
              Filter.liminf
                (fun n => (galerkinSeq n).cumulative_dissipation T)
                Filter.atTop := by linarith
    -- Standard math: liminf a + liminf b ≤ liminf (a + b) (Mathlib:
    -- `Filter.add_liminf_le_liminf_add` or `Filter.liminf_add_le_add_liminf`
    -- — the exact lemma name varies). Below we use the per-n estimate
    -- directly to bypass the liminf combinator.
    _ ≤ Filter.liminf
          (fun n => (galerkinSeq n).kineticEnergy T
            + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
          Filter.atTop := by
        -- Subadditivity of liminf: combine the KE and 2ν*cum_diss components.
        -- Strategy:
        --   2ν * liminf cum_diss = liminf (2ν * cum_diss)        (constant pullout, via
        --                                                         `liminf_mul_const_of_pos_real`
        --                                                         when 2ν > 0; trivial when 2ν = 0)
        --   liminf KE + liminf (2ν * cum_diss)
        --     ≤ liminf (KE + 2ν * cum_diss)                      (Filter.le_liminf_add)
        -- All boundedness witnesses come from per_n_estimate + initEnergyMatch +
        -- pointwise nonnegativity (KE_seq_nonneg, diss_seq_nonneg).
        --
        -- Bound on the sum sequence: KE(u_n,T) + 2ν*cum_diss(u_n,T) ≤ KE(u_∞,0).
        have h2ν_nonneg : 0 ≤ 2 * nu := by linarith
        have h_const_bound :
            ∀ n, (galerkinSeq n).kineticEnergy T
                  + 2 * nu * (galerkinSeq n).cumulative_dissipation T
                ≤ uInf.kineticEnergy 0 := by
          intro n
          have h := per_n_estimate n
          have hmatch := initEnergyMatch n
          linarith
        -- From this + pointwise nonnegativity: KE(u_n,T) ≤ KE(u_∞,0) and
        -- 2ν*cum_diss(u_n,T) ≤ KE(u_∞,0).
        have h_KE_upper :
            ∀ n, (galerkinSeq n).kineticEnergy T ≤ uInf.kineticEnergy 0 := by
          intro n
          have hsum := h_const_bound n
          have hd : 0 ≤ 2 * nu * (galerkinSeq n).cumulative_dissipation T :=
            mul_nonneg h2ν_nonneg (diss_seq_nonneg n)
          linarith
        have h_2νDiss_upper :
            ∀ n, 2 * nu * (galerkinSeq n).cumulative_dissipation T
                  ≤ uInf.kineticEnergy 0 := by
          intro n
          have hsum := h_const_bound n
          have hk : 0 ≤ (galerkinSeq n).kineticEnergy T := KE_seq_nonneg n
          linarith
        -- Boundedness witnesses for the KE sequence (uses `isBoundedUnder_of`).
        have hKE_bdd_below : Filter.atTop.IsBoundedUnder (· ≥ ·)
            (fun n => (galerkinSeq n).kineticEnergy T) :=
          Filter.isBoundedUnder_of ⟨0, fun n => KE_seq_nonneg n⟩
        have hKE_bdd_above : Filter.atTop.IsBoundedUnder (· ≤ ·)
            (fun n => (galerkinSeq n).kineticEnergy T) :=
          Filter.isBoundedUnder_of ⟨uInf.kineticEnergy 0, fun n => h_KE_upper n⟩
        -- Boundedness witnesses for the 2ν*cum_diss sequence.
        have h2νDiss_bdd_below : Filter.atTop.IsBoundedUnder (· ≥ ·)
            (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T) :=
          Filter.isBoundedUnder_of
            ⟨0, fun n => mul_nonneg h2ν_nonneg (diss_seq_nonneg n)⟩
        have h2νDiss_bdd_above : Filter.atTop.IsBoundedUnder (· ≤ ·)
            (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T) :=
          Filter.isBoundedUnder_of ⟨uInf.kineticEnergy 0, fun n => h_2νDiss_upper n⟩
        have hDiss_bdd_below : Filter.atTop.IsBoundedUnder (· ≥ ·)
            (fun n => (galerkinSeq n).cumulative_dissipation T) :=
          Filter.isBoundedUnder_of ⟨0, fun n => diss_seq_nonneg n⟩
        -- Case-split on whether 2ν is zero.  We need `hDiss_bdd_above` only
        -- in the strictly-positive branch (it is derivable there from
        -- `h_2νDiss_upper`).
        rcases eq_or_lt_of_le h2ν_nonneg with h2ν_eq | h2ν_pos
        · -- Case 2ν = 0: simplify the sum to just KE.
          have h2ν0 : 2 * nu = 0 := h2ν_eq.symm
          -- Show: liminf KE + 2ν * liminf cum_diss = liminf KE
          --   and: liminf (KE + 2ν * cum_diss) = liminf KE
          -- so the inequality becomes liminf KE ≤ liminf KE.
          have heq_lhs :
              Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop
                + 2 * nu *
                    Filter.liminf
                      (fun n => (galerkinSeq n).cumulative_dissipation T)
                      Filter.atTop
                = Filter.liminf
                    (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop := by
            rw [h2ν0]; ring
          have hfun_eq :
              (fun n => (galerkinSeq n).kineticEnergy T
                + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
              = (fun n => (galerkinSeq n).kineticEnergy T) := by
            funext n; rw [h2ν0]; ring
          rw [heq_lhs, hfun_eq]
        · -- Case 2ν > 0: use constant pullout + le_liminf_add.
          have h2ν_pos' : (0 : ℝ) < 2 * nu := h2ν_pos
          -- Derive the upper bound on cum_diss from h_2νDiss_upper using
          -- division by the positive constant 2ν.
          have hDiss_bdd_above : Filter.atTop.IsBoundedUnder (· ≤ ·)
              (fun n => (galerkinSeq n).cumulative_dissipation T) :=
            Filter.isBoundedUnder_of
              ⟨uInf.kineticEnergy 0 / (2 * nu), fun n =>
                (le_div_iff₀ h2ν_pos').mpr (by
                  have h := h_2νDiss_upper n; linarith)⟩
          -- Constant pullout: 2ν * liminf cum_diss = liminf (2ν * cum_diss)
          -- via `liminf_mul_const_of_pos_real`, which gives
          --   liminf (cum_diss · 2ν) = (liminf cum_diss) * 2ν.
          have h_pullout :
              Filter.liminf
                  (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                  Filter.atTop
                = 2 * nu *
                    Filter.liminf
                      (fun n => (galerkinSeq n).cumulative_dissipation T)
                      Filter.atTop := by
            have hkey :=
              ZtareProofs.liminf_mul_const_of_pos_real
                (l := Filter.atTop) (u := fun n => (galerkinSeq n).cumulative_dissipation T)
                hDiss_bdd_above hDiss_bdd_below h2ν_pos'
            -- hkey : liminf (fun n => cum_diss n * (2*nu)) = (liminf cum_diss) * (2*nu)
            -- Convert via mul_comm.
            have hfun_eq :
                (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                = (fun n => (galerkinSeq n).cumulative_dissipation T * (2 * nu)) := by
              funext n; ring
            rw [hfun_eq, hkey, mul_comm]
          -- Apply Filter.le_liminf_add to (KE) + (2ν * cum_diss).
          have h_co_2νDiss : Filter.atTop.IsCoboundedUnder (· ≥ ·)
              (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T) :=
            h2νDiss_bdd_above.isCoboundedUnder_ge
          have h_subadd :
              Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop
                + Filter.liminf
                    (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                    Filter.atTop
                ≤ Filter.liminf
                    (fun n => (galerkinSeq n).kineticEnergy T
                      + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                    Filter.atTop := by
            have := le_liminf_add (f := Filter.atTop)
              (u := fun n => (galerkinSeq n).kineticEnergy T)
              (v := fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T)
              hKE_bdd_below hKE_bdd_above h2νDiss_bdd_below h_co_2νDiss
            -- `this` uses `(u + v)` (function add); rewrite as a lambda.
            have hfun_eq :
                ((fun n => (galerkinSeq n).kineticEnergy T)
                  + (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T))
                = (fun n => (galerkinSeq n).kineticEnergy T
                    + 2 * nu * (galerkinSeq n).cumulative_dissipation T) := by
              funext n; rfl
            rw [hfun_eq] at this
            exact this
          -- Combine pullout + subadditivity.
          calc Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop
                + 2 * nu *
                    Filter.liminf
                      (fun n => (galerkinSeq n).cumulative_dissipation T)
                      Filter.atTop
              = Filter.liminf (fun n => (galerkinSeq n).kineticEnergy T) Filter.atTop
                  + Filter.liminf
                      (fun n => 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                      Filter.atTop := by rw [h_pullout]
            _ ≤ Filter.liminf
                  (fun n => (galerkinSeq n).kineticEnergy T
                    + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                  Filter.atTop := h_subadd
    _ ≤ uInf.kineticEnergy 0 := by
        -- liminf (KE + 2ν*cum_diss) ≤ liminf (const KE(u_∞,0)) = KE(u_∞,0).
        -- Use `liminf_le_liminf` with the eventual pointwise bound, plus
        -- `liminf_const` for the constant sequence.
        have h_pw :
            ∀ᶠ n in Filter.atTop,
              (galerkinSeq n).kineticEnergy T
                + 2 * nu * (galerkinSeq n).cumulative_dissipation T
              ≤ uInf.kineticEnergy 0 :=
          Filter.Eventually.of_forall (fun n => by
            have h := per_n_estimate n
            have hmatch := initEnergyMatch n
            linarith)
        -- Boundedness witnesses on the LHS of `liminf_le_liminf`.
        have h2ν_nonneg : 0 ≤ 2 * nu := by linarith
        have h_sum_nonneg : ∀ n, 0 ≤ (galerkinSeq n).kineticEnergy T
              + 2 * nu * (galerkinSeq n).cumulative_dissipation T := fun n => by
          have hk : 0 ≤ (galerkinSeq n).kineticEnergy T := KE_seq_nonneg n
          have hd : 0 ≤ 2 * nu * (galerkinSeq n).cumulative_dissipation T :=
            mul_nonneg h2ν_nonneg (diss_seq_nonneg n)
          linarith
        have h_sum_bdd_below : Filter.atTop.IsBoundedUnder (· ≥ ·)
            (fun n => (galerkinSeq n).kineticEnergy T
              + 2 * nu * (galerkinSeq n).cumulative_dissipation T) :=
          Filter.isBoundedUnder_of ⟨0, fun n => h_sum_nonneg n⟩
        -- Constant function is cobounded below trivially.
        have h_const_co : Filter.atTop.IsCoboundedUnder (· ≥ ·)
            (fun _ : ℕ => uInf.kineticEnergy 0) :=
          (Filter.isBoundedUnder_of (f := Filter.atTop)
              ⟨uInf.kineticEnergy 0, fun _ => le_refl _⟩).isCoboundedUnder_ge
        have h_le :
            Filter.liminf
                (fun n => (galerkinSeq n).kineticEnergy T
                  + 2 * nu * (galerkinSeq n).cumulative_dissipation T)
                Filter.atTop
              ≤ Filter.liminf (fun _ : ℕ => uInf.kineticEnergy 0) Filter.atTop :=
          Filter.liminf_le_liminf h_pw h_sum_bdd_below h_const_co
        have h_const : Filter.liminf (fun _ : ℕ => uInf.kineticEnergy 0) Filter.atTop
            = uInf.kineticEnergy 0 := Filter.liminf_const _
        linarith [h_le, h_const.le, h_const.ge]

end

end ZtareProofs.NS
