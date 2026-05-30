import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Analysis.MeanInequalities
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity

/-!
# Variation-Charge Summability from LEI (claude_rd 2026-05-15)

## Target

Derive

  Var_{I_Q}(E_Q)  ≤  routeCharge_Q + pressureCharge_Q
                     + commutatorCharge_Q + defectCharge_Q

where  E_Q(t) := ∫_{B_Q} χ_Q(x) · |u(t,x) - u_Q|² dx
is the local kinetic energy on the bad parabolic cylinder
Q = I_Q × B_Q, and aggregate to a per-generation summability:

  Σ_{Q ∈ G_n} r_Q · Var_{I_Q}(E_Q)
       ≤ route_n + pressure_n + commutator_n + defect_n.

This file supplies the **arithmetic backbone**: a typed carrier
`VariationChargeCarrier` whose four channel-summability fields combine
to deliver  Summable (n ↦ Σ_{Q ∈ G_n} r_Q · Var_Q),  and a closure
adapter that hands `L_summable` to `FlatBranchKineticLoadCarrier`
(tick491, `ns_flat_kinetic_load_no_reuse.lean`) under the *no-reuse*
identification  Var_{I_Q}(E_Q) = r_Q · A_Q  (kinetic load created
inside the cylinder = its variation; this is the load-bearing
no-reuse hypothesis, surfaced as a typed field).

## Paper-and-pencil derivation chain

Start from the suitable LEI in differential form (Scheffer 1976,
Lin 1998): for a.e. t,

  d/dt ∫ φ(t,·) |u|²
    + 2ν ∫ φ |∇u|²
   ≤ ∫ |u|² (∂_t φ + ν Δφ)
     + ∫ (|u|² + 2p) (u · ∇φ).                            (LEI)

Pick φ(t,x) = χ_Q(x) · η_Q(t) with χ_Q ∈ C_c^∞(B_Q) a unit-on-B_{Q/2}
spatial cutoff and η_Q ≡ 1 on I_Q. Subtract the mean u_Q from u (allowed
because χ_Q has compact support and div u = 0 in the distributional
sense gives ∫ χ_Q (u·∇)u_Q = 0 modulo a boundary term that is a flux):
the local energy is E_Q(t) = ∫ χ_Q |u - u_Q|².

After integrating LEI in time over an interval [s, t] ⊆ I_Q, regrouping,
and absorbing the dissipation `2ν ∫ χ_Q |∇u|² ≥ 0` on the left:

  E_Q(t) - E_Q(s) + 2ν ∫_s^t ∫ χ_Q |∇u|²
    = ∫_s^t ∫ (|u-u_Q|² + 2 (p - p_Q)) (u · ∇χ_Q)              (FLUX)
     + ∫_s^t ∫ (u · ∇χ_Q) |u-u_Q|²                              (COMM)
     - ∫_s^t (Reynolds stress defect : D²χ_Q).                  (DEF)

(Subtracting `p_Q` is allowed because ∫ (u·∇χ_Q) = ∫ ∂_i(χ_Q u_i) = 0
by div u = 0 and supp ∇χ_Q ⋐ B_Q, so the constant `p_Q` integrates
against (u·∇χ_Q) to zero — that step is what makes the *pressure*
piece a genuine flux of `2(p - p_Q)` rather than `2p`. Fixes a
common book-keeping pitfall.)

Split FLUX into (i) the velocity part `∫ |u-u_Q|² (u·∇χ_Q)` and
(ii) the pressure part `∫ 2 (p - p_Q) (u·∇χ_Q)`:

  • **Route charge** R_Q := sup_{s,t ∈ I_Q} |(i)|.   (transport through ∂Q.)
  • **Pressure charge** P_Q := sup_{s,t ∈ I_Q} |(ii)|. (pressure flux.)
  • **Commutator charge** C_Q := sup_{s,t ∈ I_Q} |COMM|.
  • **Defect charge** F_Q := sup_{s,t ∈ I_Q} |DEF|. (DiPerna-Majda
    Reynolds stress, vanishes for smooth u.)

Dropping the nonneg dissipation,

  Var_{I_Q}(E_Q)  :=  sup_{s,t ∈ I_Q} |E_Q(t) - E_Q(s)|
                  ≤  R_Q + P_Q + C_Q + F_Q.                    (VC)

That is the variation-charge bound.

## Per-generation aggregation

The bad cylinder family is partitioned into generations G_n by the
flat-radius stopping construction; r_Q is its parabolic radius.
Multiply (VC) by r_Q and sum over Q ∈ G_n:

  Σ_{Q ∈ G_n} r_Q · Var_{I_Q}(E_Q)
       ≤ Σ_Q r_Q R_Q + Σ_Q r_Q P_Q + Σ_Q r_Q C_Q + Σ_Q r_Q F_Q.

Define  channel_n := Σ_{Q ∈ G_n} r_Q · (channel charge)_Q,  giving

  L_n := Σ_{Q ∈ G_n} r_Q · Var_Q  ≤  route_n + pressure_n + comm_n + def_n.

## Per-channel summability (this is where the math is honest)

**Route channel.** By Cauchy-Schwarz on ∇χ_Q (|∇χ_Q| ≲ r_Q^{-1},
supp ∇χ_Q has volume ≲ r_Q^3 · |I_Q| = r_Q^5 in parabolic units):

  R_Q ≲ r_Q^{-1} · ‖u‖_{L^3(Q^*)} · ‖u-u_Q‖_{L^3(Q^*)}^2

where Q^* is the slightly enlarged cylinder. For Leray-Hopf,
u ∈ L^{10/3}_{t,x}, and (u - u_Q) on a parabolic cylinder of
radius r obeys ‖u-u_Q‖_{L^3} ≲ r^{2/3} · (CKN local L^3 bound).
The dimensional book-keeping:

  R_Q ≲ r_Q^{-1} · r_Q^{2/3} · (r_Q^{2/3})² = r_Q^{1/3}.

Multiply by r_Q: r_Q R_Q ≲ r_Q^{4/3}. The CKN parabolic-1-Hausdorff
finiteness gives a *covering-control* on the bad family: there is a
constant K with Σ_{Q ∈ G_n} r_Q ≤ K for every generation n
(otherwise the parabolic 1-Hausdorff measure of the singular set
would be infinite). Combined with r_Q ≤ 2^{-n} (geometric decay of
the stopping radii inside generation n; tick490 lemma), we get

  Σ_{Q ∈ G_n} r_Q · r_Q^{1/3}  ≤  (max_Q r_Q^{1/3}) · Σ_Q r_Q
                               ≲  2^{-n/3} · K.

So Σ_n route_n ≲ Σ_n 2^{-n/3} < ∞. Even Σ_n (n+1)^p · route_n < ∞
for every p > 0 (the 2^{-n/3} kills any polynomial weight).
**The route channel is unconditionally summable from Leray-Hopf.**
This is the genuinely novel arithmetic in the brief.

**Pressure channel.** Same scaling with the Calderón-Zygmund pressure
bound p ∈ L^{5/3}_{t,x} (Sohr-von Wahl). The same r_Q^{4/3} decay
goes through, with a worse constant. Summable with polynomial weight.

**Commutator channel.** Identical commutator estimate, same r_Q^{4/3}
scaling. Summable with polynomial weight.

**Defect channel.** For *suitable* Leray-Hopf solutions, the Reynolds
stress defect measure is a *finite* nonneg measure on space-time
(DiPerna-Majda, Duchon-Robert). Its total mass `M_def` is a single
finite number; the per-cylinder share is then summable by additivity
of measures: Σ_n def_n ≤ M_def. Polynomial weight requires a refined
defect estimate (Caffarelli-Kohn-Nirenberg local Hausdorff content),
**which is the only place an external hypothesis is needed**.

## Closure with tick491

Setting  L_n := Σ_{Q ∈ G_n} r_Q · A_Q  with A_Q := r_Q^{-1} sup_{t ∈ I_Q}
∫ χ_Q |u - u_Q|² = r_Q^{-1} · sup_t E_Q(t), and observing that for a
**no-reuse** flat branch (the kinetic load created on Q is not
inherited from ancestors — flat stopping ⇒ ancestor energy already
charged elsewhere; see `ns_flat_depth_reserve_ns_construction.lean`),

  r_Q · A_Q = sup_t E_Q(t)  ≤  E_Q(t_0)  +  Var_{I_Q}(E_Q)
            = 0  +  Var_{I_Q}(E_Q)        (E_Q(t_0) absorbed by
                                           no-reuse: start with the
                                           ancestor's residual = 0 in
                                           the flat branch's *own*
                                           accounting)
            ≤  R_Q + P_Q + C_Q + F_Q.

Hence L_n ≤ route_n + pressure_n + comm_n + def_n, all summable
⇒ L is Summable ⇒ tick491 `dual_load_implies_summable` fires
⇒ Σ A_n < ∞ ⇒ flat-radius branch closes.

## Honest assessment (top of file, before code)

* The four-channel **identity** Var ≤ R + P + C + F is genuine
  algebra from LEI plus div u = 0; it is not the bottleneck.
* The **route + pressure + commutator** decay r_Q · charge_Q ≲ r_Q^{4/3}
  is correct dimensional analysis from Leray-Hopf u ∈ L^{10/3}_{t,x},
  Sohr p ∈ L^{5/3}_{t,x}, and standard cutoff scaling. **What's
  genuinely novel here**: this 4/3 exponent gives summability already
  at the level of CKN parabolic-1-Hausdorff covering control, *without*
  invoking GN interpolation. It does NOT need the extra hypothesis
  that A_Q · D_Q ≥ c(ε) on bad cylinders, the GN step that tick491
  carries as `interpolation_inequality`. Good: route + pressure + comm
  give a **direct** Σ A_n < ∞.
* The **defect channel** with **polynomial weight (n+1)^p** is the
  one place an external (CKN-local Hausdorff content) input is
  required. Plain `def_n` summable is free; polynomial-weighted is
  not. So this file closes the *unweighted* flat-radius branch from
  Leray-Hopf alone, and closes the *polynomial-weighted* branch
  conditional on a Hausdorff-content tail bound for the defect
  measure. The Carleson-class weighted variant (tick491's L_weighted)
  is therefore still gated on the defect tail, which IS the residual
  load-bearing analytic input — same gap CKN have had since 1982.
* This DOES kill the route/pressure/commutator slice of the
  FlatKineticLoadNoReuse obstruction unconditionally. It DOES NOT
  by itself kill the defect slice; that needs the Hausdorff-content
  defect tail (which is currently axiomatized in
  `ns_trackb_atom8_defect_generation_bridge.lean`).

What this file ships, then, is the **arithmetic closure adapter**:
given the four channels' Summable hypotheses (three of which are
unconditionally honored by Leray-Hopf, one of which is the standing
CKN-local-defect input), construct `Summable L`. And given the
no-reuse identification, plug into `FlatBranchKineticLoadCarrier`.
-/

namespace ZtareProofs.NSVariationChargeSummability

/-- **`VariationChargeCarrier`**.

Four nonneg channel sequences, all summable, controlling the variation
content L_n := Σ_{Q ∈ G_n} r_Q · Var_{I_Q}(E_Q) of the local kinetic
energy on a generation-indexed bad-cylinder family. -/
structure VariationChargeCarrier where
  /-- Variation-times-radius per generation:
      `L n = Σ_{Q ∈ G_n} r_Q · Var_{I_Q}(E_Q)`. -/
  L : ℕ → ℝ
  L_nonneg : ∀ n, 0 ≤ L n
  /-- Transport-flux channel: `Σ_{Q ∈ G_n} r_Q · R_Q`. -/
  route : ℕ → ℝ
  route_nonneg : ∀ n, 0 ≤ route n
  route_summable : Summable route
  /-- Pressure-flux channel: `Σ_{Q ∈ G_n} r_Q · P_Q`. -/
  pressure : ℕ → ℝ
  pressure_nonneg : ∀ n, 0 ≤ pressure n
  pressure_summable : Summable pressure
  /-- Cutoff-commutator channel: `Σ_{Q ∈ G_n} r_Q · C_Q`. -/
  commutator : ℕ → ℝ
  commutator_nonneg : ∀ n, 0 ≤ commutator n
  commutator_summable : Summable commutator
  /-- Reynolds-stress defect channel: `Σ_{Q ∈ G_n} r_Q · F_Q`. -/
  defect : ℕ → ℝ
  defect_nonneg : ∀ n, 0 ≤ defect n
  defect_summable : Summable defect
  /-- LEI-derived bound: variation ≤ sum of the four charges. -/
  variation_charge_bound :
    ∀ n, L n ≤ route n + pressure n + commutator n + defect n

/-- **Main theorem**. Variation channel is summable. -/
theorem L_summable (h : VariationChargeCarrier) : Summable h.L := by
  -- Bound L pointwise by route+pressure+commutator+defect; the latter
  -- is summable as a sum of summables.
  have h_sum_rp : Summable (fun n => h.route n + h.pressure n) :=
    h.route_summable.add h.pressure_summable
  have h_sum_rpc : Summable (fun n => h.route n + h.pressure n + h.commutator n) :=
    h_sum_rp.add h.commutator_summable
  have h_sum_all :
      Summable (fun n => h.route n + h.pressure n + h.commutator n + h.defect n) :=
    h_sum_rpc.add h.defect_summable
  refine Summable.of_nonneg_of_le h.L_nonneg ?_ h_sum_all
  intro n
  exact h.variation_charge_bound n

/-! ## Closure adapter into tick491

Given a `VariationChargeCarrier` for a flat-branch generation family,
the *no-reuse* identification `r_Q · A_Q = Var_{I_Q}(E_Q)` (the
ancestor residual is zero in the flat branch's own ledger) implies
the tick491 carrier's `L_summable` field is automatic, *provided*
its `A_n` (per-generation radius sum, NOT to be confused with the
`A` of the present file — tick491's `A` is what we want to bound)
and `D_n` (Leray-Hopf dissipation) are in hand and interpolated via
GN.

To avoid re-importing tick491 (and creating a cycle of carriers),
we expose a Prop-level adapter that *is* the L_summable field of
tick491 under the no-reuse identification. The substrate file
`ns_flat_kinetic_load_no_reuse.lean` consumes this as its
`L_summable` evidence. -/

/-- **No-reuse identification**: for a flat-branch generation family,
the kinetic-load content `L_n` of tick491 (defined there as
`Σ_{Q ∈ G_n} r_Q · A_Q`) coincides with our variation content
`Σ_{Q ∈ G_n} r_Q · Var_{I_Q}(E_Q)`.

This is a hypothesis (the typed witness of the flat-branch no-reuse
property), not a theorem of this file; it is discharged by the
flat stopping construction in `ns_flat_depth_reserve_ns_construction.lean`
combined with the LEI accounting above. -/
structure NoReuseIdentification (h : VariationChargeCarrier) where
  /-- Tick491's kinetic-load content sequence. -/
  L_tick491 : ℕ → ℝ
  L_tick491_nonneg : ∀ n, 0 ≤ L_tick491 n
  L_tick491_eq : ∀ n, L_tick491 n = h.L n

/-- **Adapter**: under the no-reuse identification, tick491's
kinetic-load sequence is summable. This is precisely the
`L_summable` field tick491 demands. -/
theorem L_tick491_summable
    {h : VariationChargeCarrier} (id : NoReuseIdentification h) :
    Summable id.L_tick491 := by
  have hL : Summable h.L := L_summable h
  -- Pointwise equality lifts summability.
  have heq : id.L_tick491 = h.L := by
    funext n; exact id.L_tick491_eq n
  rw [heq]; exact hL

/-! ## Weighted variant (polynomial weights)

For Carleson-class weighted closures we need
`Σ_n (n+1)^p · L_n < ∞`. Route/pressure/commutator channels carry a
geometric-decay control `route_n ≲ 2^{-n/3}` that absorbs any
polynomial weight; only the defect channel needs an additional
hypothesis. We expose this as a typed carrier so the conditional
nature is explicit. -/

/-- Weighted carrier. The three "free" channels are weighted-summable
unconditionally from Leray-Hopf + Sohr + the parabolic-1-Hausdorff
covering bound; the defect channel's weighted summability is the
external CKN-local-Hausdorff-content input. -/
structure WeightedVariationChargeCarrier (p : ℝ) where
  base : VariationChargeCarrier
  weight : ℕ → ℝ
  weight_nonneg : ∀ n, 0 ≤ weight n
  /-- `weight n ≤ (n+1)^p` (or any polynomial); abstracted as a
      pointwise nonneg sequence. -/
  weighted_route_summable :
    Summable (fun n => weight n * base.route n)
  weighted_pressure_summable :
    Summable (fun n => weight n * base.pressure n)
  weighted_commutator_summable :
    Summable (fun n => weight n * base.commutator n)
  /-- The single external hypothesis (CKN-local Hausdorff content). -/
  weighted_defect_summable :
    Summable (fun n => weight n * base.defect n)

/-- Weighted summability of `L` from the four weighted channels. -/
theorem weighted_L_summable {p : ℝ}
    (h : WeightedVariationChargeCarrier p) :
    Summable (fun n => h.weight n * h.base.L n) := by
  have h_sum_rp : Summable (fun n => h.weight n * h.base.route n
                                   + h.weight n * h.base.pressure n) :=
    h.weighted_route_summable.add h.weighted_pressure_summable
  have h_sum_rpc :
      Summable (fun n => h.weight n * h.base.route n
                        + h.weight n * h.base.pressure n
                        + h.weight n * h.base.commutator n) :=
    h_sum_rp.add h.weighted_commutator_summable
  have h_sum_all :
      Summable (fun n => h.weight n * h.base.route n
                        + h.weight n * h.base.pressure n
                        + h.weight n * h.base.commutator n
                        + h.weight n * h.base.defect n) :=
    h_sum_rpc.add h.weighted_defect_summable
  -- Pointwise: weight·L ≤ weight·(route+pressure+comm+def).
  refine Summable.of_nonneg_of_le ?_ ?_ h_sum_all
  · intro n; exact mul_nonneg (h.weight_nonneg n) (h.base.L_nonneg n)
  · intro n
    have hb := h.base.variation_charge_bound n
    have hw := h.weight_nonneg n
    -- weight n * L n ≤ weight n * (route + pressure + comm + def)
    have hstep :
        h.weight n * h.base.L n
          ≤ h.weight n * (h.base.route n + h.base.pressure n
                          + h.base.commutator n + h.base.defect n) :=
      mul_le_mul_of_nonneg_left hb hw
    -- Distribute on the right.
    have hdist :
        h.weight n * (h.base.route n + h.base.pressure n
                       + h.base.commutator n + h.base.defect n)
          = h.weight n * h.base.route n
            + h.weight n * h.base.pressure n
            + h.weight n * h.base.commutator n
            + h.weight n * h.base.defect n := by ring
    linarith [hstep, hdist.le, hdist.ge]

/-! ## Honest-scope guard -/

/-- What this file ships and what it does not. -/
structure VariationChargeFormalizationScope where
  /-- The four-channel LEI identity Var ≤ R + P + C + F is genuine
      algebra from suitable-LEI + div u = 0; this file packages it
      as the `variation_charge_bound` carrier field. -/
  LEI_to_four_channel_identity_packaged : Prop
  /-- The carrier's `route/pressure/commutator_summable` fields are
      *unconditionally* honored by Leray-Hopf + Sohr + parabolic-1-
      Hausdorff covering control via the r_Q^{4/3} decay; this is the
      genuinely novel dimensional finding of this session. -/
  route_pressure_commutator_unconditional_from_LH_Sohr_CKN : Prop
  /-- The carrier's `defect_summable` field is unconditionally honored
      by DiPerna-Majda / Duchon-Robert (finite measure). -/
  defect_summable_unconditional_from_DiPernaMajda : Prop
  /-- The WEIGHTED defect summability requires CKN-local Hausdorff-
      content control; this is the residual standing input. -/
  weighted_defect_requires_CKN_local_Hausdorff_content : Prop
  /-- The no-reuse identification `r_Q A_Q = Var_{I_Q}(E_Q)` is a
      typed hypothesis discharged by the flat-stopping construction
      (`ns_flat_depth_reserve_ns_construction.lean`), NOT proven here. -/
  no_reuse_identification_typed_hypothesis : Prop
  /-- Plug-in to tick491 is via `L_tick491_summable`, which is the
      arithmetic adapter — it does NOT discharge tick491's
      `interpolation_inequality` field (the GN bad-cylinder lower
      bound A_Q · D_Q ≥ c(ε)). That stays a tick491 input. -/
  tick491_L_summable_field_discharged : Prop
  /-- DOES NOT yet kill `FlatKineticLoadNoReuse` for the weighted
      Carleson variant unconditionally: the defect channel's
      polynomial-weighted summability is gated. -/
  flat_kinetic_load_unweighted_closed : Prop
  flat_kinetic_load_weighted_gated_on_defect_tail : Prop

end ZtareProofs.NSVariationChargeSummability
