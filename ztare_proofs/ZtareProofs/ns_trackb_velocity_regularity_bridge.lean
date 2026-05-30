/-
# Bridge: typed companion → lean-dojo `WeakSolution.velocity_regularity`

This file builds the structural bridge from a Galerkin truncation
sequence (with uniform L² bounds from the energy estimate, supplied by
`ns_trackb_finite_galerkin_energy_estimate.lean` / workstream #3) to
the `velocity_regularity` clause of lean-dojo's `WeakSolution`
structure.

## The lean-dojo clause

From `Problems/NavierStokes/Navierstokes.lean` (lines 354-359):

  velocity_regularity : ∀ t ∈ Set.Icc 0 T,
    HasFiniteIntegral (fun x => ∑ i : Fin n, (u (pairToEuc t x) i)^2) ∧
    HasFiniteIntegral (fun x => ∑ i : Fin n, ∑ j : Fin n,
      (partialDeriv (j.succ) (λ y => u y i) (pairToEuc t x))^2)

i.e. for every time `t ∈ [0, T]`, both the squared-velocity density
`|u(t,·)|²` and the squared-gradient density `|∇u(t,·)|²` have finite
integrals (i.e. are L¹ as nonneg functions on `ℝⁿ`).

## Bridge mathematics

Energy estimate (workstream #3) gives, for every `n` and every
`t ∈ [0, T]`:

  ∫ |u_n(t,x)|² dx ≤ M_kin    (uniform L² bound)
  ∫ |∇u_n(t,x)|² dx ≤ M_ens   (uniform enstrophy bound)

The L² norm-squared is weakly lower-semicontinuous under weak L²
limits.  The scalar version of this fact is shipped sorry-free in
`ns_trackb_l2_lsc_primitive.lean` as

  `ZtareProofs.l2_norm_squared_lsc_under_weak_limit`,

and the vector lift to `EuclideanSpace ℝ (Fin d)` lives in
`ns_trackb_l2_lsc_vector_lift.lean` as

  `ZtareProofs.l2_vector_norm_squared_lsc_under_weak_limit`.

So for the limit solution `u_∞`:

  ∫ |u_∞(t,x)|² dx ≤ liminf_n ∫ |u_n(t,x)|² dx ≤ M_kin   < ∞,
  ∫ |∇u_∞(t,x)|² dx ≤ liminf_n ∫ |∇u_n(t,x)|² dx ≤ M_ens < ∞.

The two `HasFiniteIntegral` clauses follow from the bound on the
lower (Lebesgue) integral of the nonneg density function being
strictly less than `∞`.

## Architecture

We define two typed-companion records:

* `VelocityRegularityData` — packages the per-n L² and H¹ data plus
  the LSC-derived bounds at every `t ∈ [0, T]`.
* `velocityRegularity_from_typed_companion` — discharges the
  lean-dojo `velocity_regularity` clause from the typed companion.

The PDE-content gap is encapsulated as the LSC inputs
(`limit_squaredVelocity_le_M`, `limit_squaredGradient_le_M`); these
are the canonical outputs of the L² LSC primitive applied at each `t`.

## Composition with sibling bridges

This bridge is one of three structural bridges that together discharge
the lean-dojo `WeakSolution` predicate from a Leray-Hopf typed-companion
construction:

1. `ns_trackb_lean_dojo_energy_bridge.lean` →
   `LerayHopfSolution.energy_inequality`
2. `ns_trackb_velocity_regularity_bridge.lean` (this file) →
   `WeakSolution.velocity_regularity`
3. `ns_trackb_weak_initial_condition_bridge.lean` (sibling) →
   `WeakSolution.weak_initial_condition`

All three reduce to the same kernel obligation: weak L² convergence
of the Galerkin sequence to the limit, which is the standard Leray-
Hopf compactness output.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.L1Space.HasFiniteIntegral
import Mathlib.Analysis.InnerProductSpace.PiL2
import ZtareProofs.ns_trackb_l2_lsc_primitive
import ZtareProofs.ns_trackb_l2_lsc_vector_lift

open MeasureTheory Filter Topology
open scoped ENNReal NNReal BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## Typed-companion data for `velocity_regularity`

The companion carries:

* `n` — spatial dimension (matches lean-dojo's `n`).
* `T` — terminal time, with `T_pos : 0 < T`.
* `squaredVelocity n t x` — pointwise `∑ i, (u_n(t,x) i)²`, the density
  whose finiteness is asserted by clause 1.
* `squaredGradient n t x` — pointwise `∑ i j, (∂_j u_n(t,x) i)²`, the
  density whose finiteness is asserted by clause 2.
* `limit_squaredVelocity t x` and `limit_squaredGradient t x` — the
  same densities for the limit `u_∞`.
* `M_kin`, `M_ens` — uniform bounds (from energy estimate).
* `lintegral_squaredVelocity_limit_le_M` / `..._gradient_..._le_M` —
  bound on the lower-integral of the limit's density.  This is the
  output of the L² LSC primitive applied at time `t` and pulled into
  `ℝ≥0∞` form via `ENNReal.ofReal`.
-/

structure VelocityRegularityData where
  /-- Spatial dimension. -/
  n : ℕ
  /-- Terminal time. -/
  T : ℝ
  /-- The squared-velocity density `|u_n(t, ·)|²`, kept abstract as a
  family `ℕ × ℝ → (Euc ℝ n) → ℝ` to avoid committing to lean-dojo's
  concrete `VelocityField` here. -/
  squaredVelocity : ℕ → ℝ → (EuclideanSpace ℝ (Fin n)) → ℝ
  /-- The squared-gradient density `|∇u_n(t, ·)|²`, similarly abstract. -/
  squaredGradient : ℕ → ℝ → (EuclideanSpace ℝ (Fin n)) → ℝ
  /-- The squared-velocity density at the limit `u_∞`. -/
  limitSquaredVelocity : ℝ → (EuclideanSpace ℝ (Fin n)) → ℝ
  /-- The squared-gradient density at the limit. -/
  limitSquaredGradient : ℝ → (EuclideanSpace ℝ (Fin n)) → ℝ
  /-- Uniform L² bound for the velocity (energy estimate output). -/
  M_kin : ℝ
  /-- Uniform L² bound for the gradient (enstrophy estimate output). -/
  M_ens : ℝ

namespace VelocityRegularityData

/-- Hypotheses linking the typed companion to the lean-dojo clause.

Every PDE-content obligation lives here as a Prop input.  The two
key obligations are:

* `lintegral_limit_velocity_le` — `∫⁻ |u_∞(t,x)|² ∂vol ≤ ofReal M_kin`,
  the L² LSC output at time `t` pulled into `ℝ≥0∞`.
* `lintegral_limit_gradient_le` — analogous bound for the gradient.

The remaining hypotheses are nonnegativity (always true since the
densities are sums of squares), the standing finiteness `M_kin, M_ens
< ∞` (real-valued by construction), and the time-domain restriction
`t ∈ Set.Icc 0 T` is implicit in the universal quantifier.
-/
structure Hypotheses (D : VelocityRegularityData) : Prop where
  /-- `T > 0` for non-degenerate time interval (matches lean-dojo's `T_pos`). -/
  T_pos : 0 < D.T
  /-- The squared-velocity density at the limit is a.e. nonneg. -/
  limit_squaredVelocity_nonneg :
    ∀ t ∈ Set.Icc (0 : ℝ) D.T,
      ∀ᵐ x ∂(MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))),
        0 ≤ D.limitSquaredVelocity t x
  /-- The squared-gradient density at the limit is a.e. nonneg. -/
  limit_squaredGradient_nonneg :
    ∀ t ∈ Set.Icc (0 : ℝ) D.T,
      ∀ᵐ x ∂(MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))),
        0 ≤ D.limitSquaredGradient t x
  /-- `M_kin` is a real number (not `+∞`).  Encoded as a bound on
  `ENNReal.ofReal M_kin` being finite. -/
  M_kin_finite : (ENNReal.ofReal D.M_kin) ≠ ∞
  /-- Same for `M_ens`. -/
  M_ens_finite : (ENNReal.ofReal D.M_ens) ≠ ∞
  /-- L² LSC output for the velocity, in `ℝ≥0∞` form.

  This is the canonical output of `l2_vector_norm_squared_lsc_under_weak_limit`
  applied at time `t` (yielding `∫ |u_∞(t,·)|² ≤ liminf ∫ |u_n(t,·)|²
  ≤ M_kin`) and then lifted into `ℝ≥0∞` via the standard identification
  for nonneg real integrals. -/
  lintegral_limit_velocity_le :
    ∀ t ∈ Set.Icc (0 : ℝ) D.T,
      (∫⁻ x, ENNReal.ofReal (D.limitSquaredVelocity t x)
          ∂(MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))))
        ≤ ENNReal.ofReal D.M_kin
  /-- L² LSC output for the gradient (enstrophy), analogous shape. -/
  lintegral_limit_gradient_le :
    ∀ t ∈ Set.Icc (0 : ℝ) D.T,
      (∫⁻ x, ENNReal.ofReal (D.limitSquaredGradient t x)
          ∂(MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))))
        ≤ ENNReal.ofReal D.M_ens

end VelocityRegularityData

open VelocityRegularityData

/-! ## Bridge corollary

Discharge `velocity_regularity` from the typed companion. -/

/-- **Velocity regularity from typed companion.**

Given:

* a `VelocityRegularityData` instance, supplying per-n densities, the
  limit densities, and uniform bounds `M_kin`, `M_ens` from the
  energy estimate (workstream #3),
* the LSC outputs `lintegral_limit_velocity_le` and
  `lintegral_limit_gradient_le` (canonical outputs of the L² LSC
  primitive `l2_norm_squared_lsc_under_weak_limit` lifted to `ℝ≥0∞`),

we conclude that for every `t ∈ [0, T]`, the limit's squared velocity
and squared gradient densities have finite integrals, matching the
shape of lean-dojo's `WeakSolution.velocity_regularity`.

The proof is structurally simple:
`HasFiniteIntegral g μ ↔ ∫⁻ ‖g‖ₑ ∂μ < ∞`; for nonneg `g`, the enorm
collapses to `ENNReal.ofReal g`, and the LSC hypothesis gives
`≤ ofReal M_kin < ∞`. -/
theorem velocityRegularity_from_typed_companion
    (D : VelocityRegularityData) (H : D.Hypotheses) :
    ∀ t ∈ Set.Icc (0 : ℝ) D.T,
      HasFiniteIntegral
        (fun x : EuclideanSpace ℝ (Fin D.n) => D.limitSquaredVelocity t x)
        (MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))) ∧
      HasFiniteIntegral
        (fun x : EuclideanSpace ℝ (Fin D.n) => D.limitSquaredGradient t x)
        (MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))) := by
  intro t ht
  refine ⟨?_, ?_⟩
  · -- Velocity clause:  HasFiniteIntegral |u_∞(t, ·)|².
    -- Strategy: rewrite via `hasFiniteIntegral_iff_ofReal` (since the
    -- density is a.e. nonneg) and then use `lintegral_limit_velocity_le`.
    rw [hasFiniteIntegral_iff_ofReal (H.limit_squaredVelocity_nonneg t ht)]
    -- Goal: (∫⁻ x, ENNReal.ofReal (D.limitSquaredVelocity t x) ∂vol) < ∞.
    calc (∫⁻ x, ENNReal.ofReal (D.limitSquaredVelocity t x)
            ∂(MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))))
        ≤ ENNReal.ofReal D.M_kin := H.lintegral_limit_velocity_le t ht
      _ < ∞ := lt_top_iff_ne_top.mpr H.M_kin_finite
  · -- Gradient clause: HasFiniteIntegral |∇u_∞(t, ·)|².
    rw [hasFiniteIntegral_iff_ofReal (H.limit_squaredGradient_nonneg t ht)]
    calc (∫⁻ x, ENNReal.ofReal (D.limitSquaredGradient t x)
            ∂(MeasureTheory.volume : Measure (EuclideanSpace ℝ (Fin D.n))))
        ≤ ENNReal.ofReal D.M_ens := H.lintegral_limit_gradient_le t ht
      _ < ∞ := lt_top_iff_ne_top.mpr H.M_ens_finite

/-! ## Discharge plan for `lintegral_limit_velocity_le` from the L² LSC primitive

The hypothesis `lintegral_limit_velocity_le` is the only PDE-content
obligation in the bridge.  Its discharge follows the standard
"real-bound → `ℝ≥0∞`-bound" upgrade:

1. Apply `ZtareProofs.l2_norm_squared_lsc_under_weak_limit` (or its
   vector lift) at time `t` to get
       `∫ |u_∞(t,x)|² ∂vol ≤ liminf_n ∫ |u_n(t,x)|² ∂vol`.
2. Combine with the uniform energy estimate
       `∀ n, ∫ |u_n(t,x)|² ∂vol ≤ M_kin`
   to deduce
       `∫ |u_∞(t,x)|² ∂vol ≤ M_kin`.
3. Convert to `ℝ≥0∞` via `MeasureTheory.ofReal_integral_eq_lintegral_ofReal`
   (or the equivalent `Integrable.lintegral_ofReal_eq_integral` /
   `lintegral_ofReal_eq_integral_of_nonneg`):  for nonneg integrable
   `g`,
       `∫⁻ x, ENNReal.ofReal (g x) ∂μ = ENNReal.ofReal (∫ g ∂μ)`.
4. Apply `ENNReal.ofReal_le_ofReal` (monotone) to obtain
       `(∫⁻ x, ENNReal.ofReal (g x) ∂μ) ≤ ENNReal.ofReal M_kin`.

Step 3 requires `Integrable g`, which follows from the per-n
`HasFiniteIntegral` plus `MemLp.toLp` machinery — but in the typed
companion's design, we expose the `ℝ≥0∞`-bound directly so that the
bridge corollary is decoupled from any specific Mathlib integrability
lemma name.

The same template applies for `lintegral_limit_gradient_le` with
the gradient density.

This separation of concerns mirrors the architecture of
`ns_trackb_lean_dojo_energy_bridge.lean`: PDE-content stays in named
hypothesis fields; the bridge is a structural reduction.
-/

/-! ## Composition receipt

This bridge composes with:

* `ns_trackb_finite_galerkin_energy_estimate.lean` (workstream #3) —
  produces `M_kin`, `M_ens` and the per-n L² bounds that feed the
  LSC primitive's `seqL2_isBoundedUnder` hypothesis.
* `ns_trackb_l2_lsc_primitive.lean` /
  `ns_trackb_l2_lsc_vector_lift.lean` — produces the LSC inequality
  whose lift to `ℝ≥0∞` form populates
  `lintegral_limit_velocity_le` / `lintegral_limit_gradient_le`.
* `ns_trackb_lean_dojo_energy_bridge.lean` — sibling bridge for
  `LerayHopfSolution.energy_inequality`; shares the same Galerkin
  data and weak-L² convergence input.
* (Future) `ns_trackb_weak_initial_condition_bridge.lean` — sibling
  bridge for `WeakSolution.weak_initial_condition`; reduces to the
  same weak-L² test against compactly-supported smooth `φ`.

Together the four discharge `WeakSolution` (lean-dojo) modulo the
weak-momentum-equation and weak-incompressibility clauses, which
require the additional convergence-of-nonlinearity argument
(Aubin-Lions compactness in `L²(0,T; H¹)` ∩ `L^∞(0,T; L²)`).
-/

end

end ZtareProofs.NS
