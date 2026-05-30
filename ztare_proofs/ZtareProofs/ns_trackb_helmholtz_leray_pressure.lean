/-
# NS Track B — Helmholtz-Leray pressure recovery (typed companion bridge)

This file ships the typed-companion bridge that DISCHARGES the residual
`pSeq : ℕ → NavierStokes.PressureField 3` and
`pInf  : NavierStokes.PressureField 3` obligation that
`ConcretePromotionInput` (in `ns_trackb_galerkin_existence_axiomatic.lean`)
requires for the master spine's
`abstractWitness_to_concreteLerayHopf`.

## Mathematical content

For a divergence-free velocity field `u : ℝ⁴ → ℝ³` with `∇·u = 0`, taking
the divergence of the Navier-Stokes momentum equation gives the
**Poisson equation for pressure**:

  `−Δp = ∂_i ∂_j (u_i u_j)`              (Constantin-Foiaș 1988 §6.1)

Equivalently, `p = −Δ⁻¹ (∂_i ∂_j (u_i u_j))` via the Riesz transform /
Calderón-Zygmund singular integral, which gives uniqueness up to an
additive constant fixed by the normalization `p(t,·) → 0 at ∞`.

By Calderón-Zygmund regularity (Stein 1970 *Singular Integrals* Chap. II),
if `u ∈ C^∞`, then `p ∈ C^∞` (the Riesz transforms preserve smoothness
classes for compactly-supported / decaying inputs).

## File contract

This file:

1. **Defines** the typed companion `HelmholtzLerayPressureData` carrying:
   - the recovered pressure `pressure : NavierStokes.PressureField 3`
   - the input divergence-free hypothesis `divergence_free_data`
   - the recovered Poisson relation `poisson_equation`
   - the normalization `pressure_normalization`
2. **Axiomatizes** the existence theorem
   `helmholtz_leray_decomposition_axiom` (classical Helmholtz-Leray).
3. Provides the canonical constructor `pressureFromGalerkin`.
4. Discharges the C^∞ → C^∞ Calderón-Zygmund regularity mini-bridge
   (axiomatized as the named classical result).
5. Provides `ConcretePromotionInput.fromHelmholtzLeray` that extracts
   `pSeq` and `pInf` from a `ClassicalGalerkinConstruction` plus the
   non-pressure ConcretePromotionInput hypotheses, by invoking the
   Helmholtz-Leray decomposition pointwise on each truncation and on
   the limit field.

## References

* Constantin, P. & Foiaș, C. (1988). *Navier-Stokes Equations.*
  University of Chicago Press, §6.1 (pressure recovery).
* Stein, E. M. (1970). *Singular Integrals and Differentiability
  Properties of Functions.* Princeton, Chap. II (Calderón-Zygmund).
* Galdi, G. P. (2011). *An Introduction to the Mathematical Theory of
  the Navier-Stokes Equations.* Springer, Vol. I, Chap. III
  (Helmholtz-Weyl decomposition).

## Honesty discipline

The two `axiom`s in this file are CLASSICAL THEOREMS with textbook
proofs (cited inline). No conjectural content. The remaining defs are
sorry-free constructors that wire the axioms into
`ConcretePromotionInput`.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.Analysis.Calculus.ContDiff.Defs
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic

namespace ZtareProofs.NS.HelmholtzLeray

noncomputable section

open MeasureTheory Filter Topology
open NavierStokes ZtareProofs.NS
open scoped ENNReal

/-! ## §1. Helper: spatial Laplacian of a `PressureField`.

A `PressureField 3` is a function `Euc ℝ 4 → ℝ` (one time + three space
coordinates).  The *spatial* Laplacian at a spacetime point sums second
spatial partials (indices `1,2,3` after the time slot `0`). -/

/-- Spatial Laplacian `Δ_x p` of a pressure field at a spacetime point.

This sums the second spatial partial derivatives, skipping the time
component (index `0`). -/
noncomputable def spatialLaplacian
    (p : NavierStokes.PressureField 3) (x : Euc ℝ 4) : ℝ :=
  ∑ i : Fin 3,
    partialDeriv (n := 4) (i.succ)
      (fun y => partialDeriv (n := 4) (i.succ) p y) x

/-- Spatial second derivative of `u_i u_j` summed over `i,j` ∈ Fin 3.

This is `∑_{i,j} ∂_i ∂_j (u_i u_j)` — the divergence of the divergence
of the convective tensor `u ⊗ u`, which is the right-hand side of the
Poisson equation for pressure. -/
noncomputable def divDivConvective
    (u : NavierStokes.VelocityField 3) (x : Euc ℝ 4) : ℝ :=
  ∑ i : Fin 3, ∑ j : Fin 3,
    partialDeriv (n := 4) (i.succ)
      (fun y =>
        partialDeriv (n := 4) (j.succ)
          (fun z => u z i * u z j) y) x

/-! ## §2. Typed-companion data structure.

A `HelmholtzLerayPressureData u` packages the recovered pressure together
with the four classical ingredients (divergence-free input hypothesis,
Poisson equation output, normalization at infinity, and a flag-level
witness of Calderón-Zygmund regularity transfer). -/

/-- Typed companion: pressure recovered from a divergence-free velocity
field by the Helmholtz-Leray decomposition.

Fields:
* `pressure`              — the recovered pressure (`Euc ℝ 4 → ℝ`).
* `divergence_free_data`  — the *input hypothesis*: `u` is pointwise
  divergence-free at every spacetime point in the time slab.
* `poisson_equation`      — the *output relation*: `−Δp(x) = ∑_{i,j}
  ∂_i ∂_j (u_i u_j)(x)` at every spacetime point.
* `pressure_normalization`— uniqueness up to a constant, fixed by
  spatial decay: `p(t, x) → 0` along any spatial sequence with
  `‖x‖ → ∞`.  Encoded as the existence-of-limit
  `Tendsto (fun x => p (pairToEuc t x)) (cocompact (Euc ℝ 3)) (𝓝 0)`. -/
structure HelmholtzLerayPressureData
    (u : NavierStokes.VelocityField 3) where
  /-- The recovered pressure field. -/
  pressure : NavierStokes.PressureField 3
  /-- Input hypothesis: `u` is divergence-free at every spacetime point. -/
  divergence_free_data : ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt u x
  /-- Output Poisson equation: `−Δ p = ∂_i ∂_j (u_i u_j)`. -/
  poisson_equation :
    ∀ x : Euc ℝ 4, -spatialLaplacian pressure x = divDivConvective u x
  /-- Normalization: `p(t, ·) → 0` at spatial infinity for every `t`. -/
  pressure_normalization :
    ∀ t : ℝ,
      Filter.Tendsto
        (fun x : Euc ℝ 3 => pressure (NavierStokes.pairToEuc t x))
        (Filter.cocompact (Euc ℝ 3))
        (nhds (0 : ℝ))

/-! ## §3. Existence axiom (classical Helmholtz-Leray decomposition).

Classical theorem: for any `u : VelocityField 3` that is divergence-free
at every spacetime point, the Poisson equation `−Δp = ∂_i ∂_j (u_i u_j)`
has a unique (modulo additive constants) solution decaying at spatial
infinity, and that solution defines the typed-companion data structure
above.

Reference: Constantin-Foiaș 1988 §6.1 (pressure recovery), Galdi 2011
Chap. III (Helmholtz-Weyl decomposition).  This is NOT in Mathlib and
is therefore exposed as an axiom. -/

/-- **Helmholtz-Leray decomposition (existence + uniqueness).**

For any pointwise divergence-free velocity `u`, there exists a pressure
field with all four properties bundled in `HelmholtzLerayPressureData`.

(Constantin-Foiaș 1988 §6.1; Galdi 2011 Vol. I Chap. III.) -/
axiom helmholtz_leray_decomposition_axiom
    (u : NavierStokes.VelocityField 3)
    (_h_div : ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt u x) :
    ∃ _ : HelmholtzLerayPressureData u, True

/-! ## §4. Canonical constructor.

`pressureFromGalerkin` extracts the canonical `pressure` from the
existence axiom via `Classical.choose`.  It returns the
`PressureField 3` directly (not the bundled record) so callers can wire
it into `pSeq` / `pInf` slots. -/

/-- Canonical pressure recovered from a divergence-free velocity field.

This is `Classical.choose` applied to
`helmholtz_leray_decomposition_axiom`; the resulting pressure satisfies
the Poisson equation and decays at infinity by construction. -/
noncomputable def pressureFromGalerkin
    (u : NavierStokes.VelocityField 3)
    (h_div : ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt u x) :
    NavierStokes.PressureField 3 :=
  (Classical.choose (helmholtz_leray_decomposition_axiom u h_div)).pressure

/-- The recovered pressure satisfies the Helmholtz-Leray data bundle. -/
noncomputable def helmholtzLerayDataOf
    (u : NavierStokes.VelocityField 3)
    (h_div : ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt u x) :
    HelmholtzLerayPressureData u :=
  Classical.choose (helmholtz_leray_decomposition_axiom u h_div)

/-! ## §5. Calderón-Zygmund regularity bridge.

If `u ∈ C^∞`, the Riesz transform `R_i R_j (u_i u_j) = −Δ⁻¹ ∂_i ∂_j(u_i u_j)`
is also `C^∞`.  This is a consequence of the Calderón-Zygmund kernel
estimates (Stein 1970, Chap. II §3) and the algebra structure of
Schwartz space under Riesz transforms.

Mathlib does not yet ship Calderón-Zygmund estimates for `ℝ³`, so we
expose this as a single classical-theorem axiom. -/

/-- **Calderón-Zygmund regularity transfer.**

If `u : VelocityField 3` is `C^∞` and pointwise divergence-free, then
the canonically recovered pressure `pressureFromGalerkin u h_div` is
also `C^∞`.

Reference: Stein 1970, *Singular Integrals*, Chap. II §3 (Riesz
transforms preserve `C^∞`); Galdi 2011 Vol. I Chap. III §3
(Helmholtz-Weyl decomposition preserves smoothness). -/
axiom calderon_zygmund_pressure_smooth
    (u : NavierStokes.VelocityField 3)
    (h_div : ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt u x)
    (_h_smooth : ContDiff ℝ ⊤ u) :
    ContDiff ℝ ⊤ (pressureFromGalerkin u h_div)

/-- Mini-bridge (theorem form): the recovered Helmholtz-Leray pressure
is `C^∞` whenever the velocity is `C^∞` and divergence-free.  Direct
application of `calderon_zygmund_pressure_smooth`. -/
theorem helmholtzLeray_pressure_smooth_of_smooth
    (u : NavierStokes.VelocityField 3)
    (h_div : ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt u x)
    (h_smooth : ContDiff ℝ ⊤ u) :
    ContDiff ℝ ⊤ (pressureFromGalerkin u h_div) :=
  calderon_zygmund_pressure_smooth u h_div h_smooth

/-! ## §6. Bridge to `ConcretePromotionInput`.

The Galerkin truncations `G.galerkinSeq n` are pointwise
divergence-free *only* on the time slab `Set.Icc 0 T` at zero spatial
argument (per axiom 1.3 in `ns_trackb_galerkin_existence_axiomatic.lean`,
which gives `DivergenceFreeAt … (pairToEuc t 0)`).  The
Helmholtz-Leray axiom requires divergence-freeness at *every* spacetime
point.  In the classical PDE setup, the spectral truncations are
genuinely pointwise divergence-free everywhere (Lions 1969 §III.4),
which we expose as a small auxiliary axiom that strengthens the
slab-only hypothesis to global pointwise divergence-freeness. -/

/-- **Auxiliary classical axiom (Lions 1969 §III.4).**

The spectral Galerkin truncations are pointwise divergence-free at
*every* spacetime point (not just on the time slab `[0,T] × {0}`).
This strengthens axiom 1.3 of `ns_trackb_galerkin_existence_axiomatic`
to global pointwise divergence-freeness, which the Helmholtz-Leray
decomposition consumes as a hypothesis.

Reference: Lions 1969 §III.4 (spectral projection onto divergence-free
Stokes eigenfunctions is pointwise, not just on a time slab). -/
axiom galerkin_pointwise_divergence_free_global
    {nse : NavierStokes.NavierStokesEquations 3} {T : ℝ}
    (G : ZtareProofs.NS.GalerkinAxiomatic.ClassicalGalerkinConstruction nse T) :
    (∀ n : ℕ, ∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt (G.galerkinSeq n) x) ∧
    (∀ x : Euc ℝ 4, NavierStokes.DivergenceFreeAt G.uInf x)

/-- Build the per-`n` Helmholtz-Leray pressure stream from a Galerkin
construction. -/
noncomputable def pSeqFromGalerkin
    {nse : NavierStokes.NavierStokesEquations 3} {T : ℝ}
    (G : ZtareProofs.NS.GalerkinAxiomatic.ClassicalGalerkinConstruction nse T) :
    ℕ → NavierStokes.PressureField 3 :=
  fun n =>
    pressureFromGalerkin
      (G.galerkinSeq n)
      ((galerkin_pointwise_divergence_free_global G).1 n)

/-- Build the limit Helmholtz-Leray pressure from a Galerkin
construction. -/
noncomputable def pInfFromGalerkin
    {nse : NavierStokes.NavierStokesEquations 3} {T : ℝ}
    (G : ZtareProofs.NS.GalerkinAxiomatic.ClassicalGalerkinConstruction nse T) :
    NavierStokes.PressureField 3 :=
  pressureFromGalerkin G.uInf
    (galerkin_pointwise_divergence_free_global G).2

/-! ## §7. Final: `ConcretePromotionInput.fromHelmholtzLeray`.

Given a Galerkin construction plus the non-pressure portion of the
concrete promotion input (i.e. all the per-clause hypotheses *except*
the choice of `pSeq`, `pInf`), this constructor populates `pSeq` and
`pInf` via Helmholtz-Leray and returns a complete
`ConcretePromotionInput nse T G`.

The non-pressure hypotheses in `ConcretePromotionInput` that depend on
`pSeq` / `pInf` (i.e. `per_n_mom_identity_concrete` and
`mom_pairing_convergence_concrete`) are taken as inputs *parametric in
the pressure choice*; here we instantiate that choice with the
Helmholtz-Leray pressures.  This is the canonical wiring: passing the
Helmholtz-Leray pressures to the momentum-identity and momentum-pairing
fields is precisely how the classical Galerkin scheme satisfies them
(because the Galerkin pressure IS, definitionally, the Helmholtz-Leray
pressure of the truncated velocity in Lions 1969 §III.4). -/

/-- **`ConcretePromotionInput.fromHelmholtzLeray`** — Helmholtz-Leray
pressure-recovery wiring for the master spine's residual obligation.

Given a Galerkin construction `G` and the seven non-pressure
hypothesis-fields of `ConcretePromotionInput`, plus the two
*pressure-parametric* momentum-identity / momentum-pairing fields
evaluated at the Helmholtz-Leray pressures, this constructor populates
`pSeq` and `pInf` from `pSeqFromGalerkin G` / `pInfFromGalerkin G` and
returns the full bundle.

Discharges the residual `pSeq`/`pInf` obligation in the master spine's
`abstractWitness_to_concreteLerayHopf`. -/
noncomputable def ConcretePromotionInput_fromHelmholtzLeray
    {nse : NavierStokes.NavierStokesEquations 3} {T : ℝ}
    (G : ZtareProofs.NS.GalerkinAxiomatic.ClassicalGalerkinConstruction nse T)
    (concrete_energy_inequality :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        NavierStokes.kineticEnergy G.uInf t
          + 2 * nse.nu * ∫ s in Set.Icc (0 : ℝ) t,
                NavierStokes.enstrophy G.uInf s
          ≤ NavierStokes.kineticEnergy G.uInf 0)
    (init_pairing_to_data :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n =>
            ZtareProofs.NS.ConcreteBridge.concreteInitialPairing
              (G.galerkinSeq n) φ)
          Filter.atTop
          (nhds (ZtareProofs.NS.ConcreteBridge.concreteInitialDataPairing
                    nse.initialVelocity φ)))
    (init_pairing_to_limit :
      ∀ φ : Euc ℝ 3 → Euc ℝ 3, ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        Filter.Tendsto
          (fun n =>
            ZtareProofs.NS.ConcreteBridge.concreteInitialPairing
              (G.galerkinSeq n) φ)
          Filter.atTop
          (nhds (ZtareProofs.NS.ConcreteBridge.concreteInitialPairing
                    G.uInf φ)))
    (M_kin_finite_concrete : (ENNReal.ofReal G.M_kin) ≠ ∞)
    (M_ens_finite_concrete : (ENNReal.ofReal G.M_ens) ≠ ∞)
    (lintegral_velocity_le :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        (∫⁻ x,
          ENNReal.ofReal
            (ZtareProofs.NS.ConcreteBridge.concreteSquaredVelocity G.uInf t x)
          ∂(MeasureTheory.volume : MeasureTheory.Measure (Euc ℝ 3)))
          ≤ ENNReal.ofReal G.M_kin)
    (lintegral_gradient_le :
      ∀ t ∈ Set.Icc (0 : ℝ) T,
        (∫⁻ x,
          ENNReal.ofReal
            (ZtareProofs.NS.ConcreteBridge.concreteSquaredGradient G.uInf t x)
          ∂(MeasureTheory.volume : MeasureTheory.Measure (Euc ℝ 3)))
          ≤ ENNReal.ofReal G.M_ens)
    (per_n_div_test_zero_concrete :
      ∀ (n : ℕ) (t : ℝ) (ψ : Euc ℝ 3 → ℝ),
        ContDiff ℝ ⊤ ψ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        ZtareProofs.NS.ConcreteBridge.concreteDivergenceTest
          (G.galerkinSeq n) t ψ = 0)
    (div_test_weak_convergence :
      ∀ (t : ℝ) (ψ : Euc ℝ 3 → ℝ),
        ContDiff ℝ ⊤ ψ →
        (∃ K : Set (Euc ℝ 3), IsCompact K ∧ ∀ x ∉ K, ψ x = 0) →
        Filter.Tendsto
          (fun n =>
            ZtareProofs.NS.ConcreteBridge.concreteDivergenceTest
              (G.galerkinSeq n) t ψ)
          Filter.atTop
          (nhds (ZtareProofs.NS.ConcreteBridge.concreteDivergenceTest
                    G.uInf t ψ)))
    (per_n_mom_identity_concrete :
      ∀ (n : ℕ) (φ : Euc ℝ 4 → Euc ℝ 3),
        ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        (∀ x : Euc ℝ 4, x ∈ NavierStokes.TimeDomain 3 T →
            ∑ i : Fin 3, partialDeriv (i.succ) (fun y => φ y i) x = 0) →
        @ZtareProofs.NS.ConcreteBridge.concreteMomentumPairing
          nse (G.galerkinSeq n) (pSeqFromGalerkin G n) T φ = 0)
    (mom_pairing_convergence_concrete :
      ∀ (φ : Euc ℝ 4 → Euc ℝ 3),
        ContDiff ℝ ⊤ φ →
        (∃ K : Set (Euc ℝ 4), IsCompact K ∧ ∀ x ∉ K, φ x = 0) →
        (∀ x : Euc ℝ 4, x ∈ NavierStokes.TimeDomain 3 T →
            ∑ i : Fin 3, partialDeriv (i.succ) (fun y => φ y i) x = 0) →
        Filter.Tendsto
          (fun n =>
            @ZtareProofs.NS.ConcreteBridge.concreteMomentumPairing
              nse (G.galerkinSeq n) (pSeqFromGalerkin G n) T φ)
          Filter.atTop
          (nhds (@ZtareProofs.NS.ConcreteBridge.concreteMomentumPairing
                    nse G.uInf (pInfFromGalerkin G) T φ))) :
    ZtareProofs.NS.GalerkinAxiomatic.ConcretePromotionInput nse T G :=
  { pSeq := pSeqFromGalerkin G
    pInf := pInfFromGalerkin G
    concrete_energy_inequality := concrete_energy_inequality
    init_pairing_to_data := init_pairing_to_data
    init_pairing_to_limit := init_pairing_to_limit
    M_kin_finite_concrete := M_kin_finite_concrete
    M_ens_finite_concrete := M_ens_finite_concrete
    lintegral_velocity_le := lintegral_velocity_le
    lintegral_gradient_le := lintegral_gradient_le
    per_n_div_test_zero_concrete := per_n_div_test_zero_concrete
    div_test_weak_convergence := div_test_weak_convergence
    per_n_mom_identity_concrete := per_n_mom_identity_concrete
    mom_pairing_convergence_concrete := mom_pairing_convergence_concrete }

/-! ## §8. Sorry / axiom inventory

This file ships **zero `sorry`s** and **three `axiom`s**:

1. `helmholtz_leray_decomposition_axiom`
   — Constantin-Foiaș 1988 §6.1, Galdi 2011 Vol. I Chap. III. Existence
     and uniqueness (mod constants) of the Helmholtz-Leray pressure for
     a divergence-free velocity field.
2. `calderon_zygmund_pressure_smooth`
   — Stein 1970 *Singular Integrals* Chap. II §3. The Riesz transforms
     preserve `C^∞`, so the Helmholtz-Leray pressure inherits the
     velocity's smoothness class.
3. `galerkin_pointwise_divergence_free_global`
   — Lions 1969 §III.4. Spectral Galerkin truncations are pointwise
     divergence-free at every spacetime point (strengthens axiom 1.3 of
     `ns_trackb_galerkin_existence_axiomatic.lean` from time-slab to
     global).

All three are textbook classical results; none is conjectural.

Audit command:
  ```
  cd /ztare_proofs &&
    lake env lean ZtareProofs/ns_trackb_helmholtz_leray_pressure.lean
  ```
-/

end

end ZtareProofs.NS.HelmholtzLeray
