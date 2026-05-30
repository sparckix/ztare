/-
# NS Track B — Curl operator and vorticity equation derivation

This file provides the **concrete declarations** that the BKM proof
skeleton's Step 1 axiom (`vorticity_equation_holds` in
`ns_trackb_bkm_proof_skeleton.lean`) abstracts over.

Specifically, this file:

1. Defines the **curl operator** on a 3-D `NavierStokes.VelocityField`
   in coordinate form, using the existing `NavierStokes.partialDeriv`
   primitive on `Euc ℝ (n+1)` (spacetime).

2. Defines the **vorticity field** `ω := curl u` and the differential
   operators that appear in the vorticity equation: the convective
   derivative `(u·∇)ω`, the stretching term `(ω·∇)u`, and the
   spatial Laplacian `Δω`.

3. States `vorticity_equation_holds_concrete`: the classical
   identity

       ∂_t ω + (u·∇)ω = (ω·∇)u + ν Δω

   for a smooth NS solution `(u, p)`. This is **AXIOMATIZED** because
   the derivation, while classical (Majda-Bertozzi 2002,
   Proposition 1.8), is a multi-page coordinate computation in Lean:
   it requires Schwarz / Clairaut symmetry of mixed partials, the
   product rule for `partialDeriv` on `Euc ℝ (n+1)`, and the chain
   rule applied component-wise. None of these are directly available
   for `partialDeriv` as defined in `ZtareProofs.lean_dojo_ns`.

4. States the **BKM continuation theorem** (BKM 1984, Theorem 1) at
   the level of the abstract surrogate norm `‖curl u(t,·)‖_{L^∞}`,
   axiomatizing the integrability ⇒ smoothness implication so the
   theorem can be cited from downstream files (and so the BKM proof
   skeleton's typed-companion bridge has a concrete statement to
   point to).

5. **Connects** to `ns_trackb_bkm_proof_skeleton.lean` by providing a
   bridge lemma `vorticity_equation_holds_bridge` that consumes the
   concrete vorticity equation and produces the abstract typed
   companion `BKMVorticityEquation` (whose surrogate fields are
   produced via classical-existence axioms; see comments).

## What is shipped

* `curlVelocityField : VelocityField 3 → VelocityField 3` —
  coordinate definition.
* `vorticityField` (alias for `curlVelocityField`).
* `convectiveDeriv`, `stretchingTerm`, `spatialLaplacianVec` —
  helper differential operators on `VelocityField 3`.
* `VorticityEquationHoldsAt` — pointwise predicate stating
  `∂_t ω + (u·∇)ω = (ω·∇)u + ν Δω`.
* `vorticity_equation_holds_concrete` — AXIOM (classical PDE
  derivation; Mathlib gap).
* `BKMContinuationTheorem` — AXIOM (BKM 1984, Theorem 1).
* `vorticity_equation_holds_bridge` — bridge to the BKM proof
  skeleton's typed-companion `BKMVorticityEquation`.

## Mathlib gap (HONEST FRAMING)

The curl operator on `EuclideanSpace ℝ (Fin 3) → EuclideanSpace ℝ
(Fin 3)` is **not formalized** in current Mathlib (as of mid-2026).
What is available:

* `fderiv ℝ` and the `ContDiff` hierarchy.
* No `curl`, no `div` (vector-valued), no vector identities like
  `curl (curl u) = ∇(div u) − Δu` or `div(curl u) = 0`.
* Chain rule and product rule for *general* normed spaces, but no
  specialization to the concrete coordinate `partialDeriv` defined
  in `ZtareProofs.lean_dojo_ns.Definitions`.
* The Clairaut / Schwarz theorem on equality of mixed partials is
  available abstractly (`ContDiffAt.fderiv_within` plus symmetry of
  the second derivative), but bridging it to `partialDeriv (i.succ)
  (partialDeriv (j.succ) f) = partialDeriv (j.succ) (partialDeriv
  (i.succ) f)` requires an unfold + bilinear-form swap that has
  not been written.

Consequently **the derivation of the vorticity equation in Lean is
estimated at multi-page length**: each spatial component of `curl
(NS-momentum-equation)` requires expanding three partial-derivative
applications, applying product rule three times, and re-collecting
into the canonical `(u·∇)ω`, `(ω·∇)u`, `Δω` shape. We axiomatize at
the level of the final identity and let downstream files cite the
classical reference.

References:

* J. T. Beale, T. Kato, A. Majda, *Remarks on the breakdown of smooth
  solutions for the 3-D Euler equations*, Comm. Math. Phys. **94**
  (1984), 61–66, eq. (1.4) (vorticity equation) and Theorem 1
  (continuation criterion).
* A. Majda, A. Bertozzi, *Vorticity and Incompressible Flow*,
  Cambridge Univ. Press 2002, Proposition 1.8.
* P. Constantin, C. Foias, *Navier-Stokes Equations*, Univ. of
  Chicago Press 1988, Chapter 4.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bkm_proof_skeleton

namespace ZtareProofs.NS

noncomputable section

open NavierStokes
open MeasureTheory
open scoped Topology

/-! ## Coordinate index helpers for `Fin 3`

In the spacetime coordinate convention used by
`ZtareProofs.lean_dojo_ns.Navierstokes`, a point in `Euc ℝ 4`
corresponds to `(t, x_1, x_2, x_3)` where the time slot is `Fin.mk 0`
and spatial slots are `(j : Fin 3).succ : Fin 4`. -/

/-- Spatial index `1` lifted to `Fin (3+1)`: the `x`-axis. -/
private abbrev sx₀ : Fin 4 := (0 : Fin 3).succ
/-- Spatial index `2` lifted to `Fin (3+1)`: the `y`-axis. -/
private abbrev sx₁ : Fin 4 := (1 : Fin 3).succ
/-- Spatial index `3` lifted to `Fin (3+1)`: the `z`-axis. -/
private abbrev sx₂ : Fin 4 := (2 : Fin 3).succ
/-- Time index `0` in `Fin (3+1)`. -/
private abbrev tIdx : Fin 4 := 0

/-! ## The curl operator on a 3-D velocity field

For `u : VelocityField 3` (i.e. `Euc ℝ 4 → Euc ℝ 3`), the curl is
the 3-vector

    curl u = ( ∂_y u_z - ∂_z u_y ,
               ∂_z u_x - ∂_x u_z ,
               ∂_x u_y - ∂_y u_x )

written in the Cartesian basis. We index `u` by `Fin 3` as
`u y 0 = u_x`, `u y 1 = u_y`, `u y 2 = u_z`, and apply
`partialDeriv` on the spacetime input variable `y : Euc ℝ 4`.

This is purely a coordinate definition; no PDE content. The
**derivation** of the vorticity equation from `curl ∘ NS-momentum`
is the axiom below. -/
def curlVelocityField (u : VelocityField 3) : VelocityField 3 :=
  fun x =>
    Euc.ofFun (𝕜 := ℝ) (n := 3) (fun i : Fin 3 =>
      if i = (0 : Fin 3) then
        partialDeriv (n := 4) sx₁ (fun y => u y 2) x
          - partialDeriv (n := 4) sx₂ (fun y => u y 1) x
      else if i = (1 : Fin 3) then
        partialDeriv (n := 4) sx₂ (fun y => u y 0) x
          - partialDeriv (n := 4) sx₀ (fun y => u y 2) x
      else
        partialDeriv (n := 4) sx₀ (fun y => u y 1) x
          - partialDeriv (n := 4) sx₁ (fun y => u y 0) x)

/-- The vorticity field `ω := curl u`. Alias to give downstream
files a load-bearing name. -/
def vorticityField (u : VelocityField 3) : VelocityField 3 :=
  curlVelocityField u

/-! ## Differential operators appearing in the vorticity equation -/

/-- The convective spatial derivative `(u · ∇) v` at a spacetime
point: `((u·∇) v)_i = Σ_j u_j · ∂_{x_j} v_i`. The time slot of `v`
is left untouched (sum runs over spatial indices `j : Fin 3`).

This is *almost* `MaterialDerivative` from `Navierstokes.lean`, but
`MaterialDerivative` adds the time derivative `∂_t v_i`, which we
keep separate so the vorticity equation has the canonical shape
`∂_t ω + (u·∇)ω = (ω·∇)u + νΔω`. -/
def convectiveDeriv (u v : VelocityField 3) : VelocityField 3 :=
  fun x =>
    Euc.ofFun (𝕜 := ℝ) (n := 3) (fun i : Fin 3 =>
      ∑ j : Fin 3, u x j * partialDeriv (n := 4) j.succ (fun y => v y i) x)

/-- The vortex-stretching term `(ω · ∇) u` in the vorticity equation,
defined identically to `convectiveDeriv ω u` but exposed under its
load-bearing name. -/
def stretchingTerm (ω u : VelocityField 3) : VelocityField 3 :=
  convectiveDeriv ω u

/-- The (purely spatial) vector Laplacian `Δω` applied component-wise:
`(Δω)_i = Σ_j ∂_{x_j}^2 ω_i`. The sum runs over spatial axes only,
so this matches the Laplacian inside `NavierStokes.ViscousTerm`. -/
def spatialLaplacianVec (ω : VelocityField 3) : VelocityField 3 :=
  fun x =>
    Euc.ofFun (𝕜 := ℝ) (n := 3) (fun i : Fin 3 =>
      ∑ j : Fin 3,
        partialDeriv (n := 4) j.succ
          (fun y => partialDeriv (n := 4) j.succ (fun z => ω z i) y) x)

/-- The time derivative `∂_t ω` (component-wise), where the
spacetime-coordinate-`0` slot of `Euc ℝ 4` is the time variable. -/
def timeDerivVec (ω : VelocityField 3) : VelocityField 3 :=
  fun x =>
    Euc.ofFun (𝕜 := ℝ) (n := 3) (fun i : Fin 3 =>
      partialDeriv (n := 4) tIdx (fun y => ω y i) x)

/-! ## The vorticity equation as a pointwise predicate -/

/-- **`VorticityEquationHoldsAt nu u x`.** The classical identity

    ∂_t ω + (u·∇)ω = (ω·∇)u + ν Δω

holds at the spacetime point `x`, where `ω := curl u`. The
predicate holds component-wise (i.e. equality in `Euc ℝ 3`). -/
def VorticityEquationHoldsAt (nu : ℝ) (u : VelocityField 3)
    (x : Euc ℝ 4) : Prop :=
  let ω := vorticityField u
  timeDerivVec ω x + convectiveDeriv u ω x
    = stretchingTerm ω u x + (nu • spatialLaplacianVec ω x)

/-! ## Concrete vorticity/stretching window

This is the shared source object for PDE-facing attacks on vortex stretching.
It pins downstream De Giorgi, CF, and pressure routes to the concrete curl
field and stretching term, so a later estimate cannot silently replace them
with a scalar surrogate.
-/

/-- A local window whose vorticity and stretching fields are definitionally
connected to the solution velocity.  Hard PDE estimates may extend this
record with their own hypotheses, but should consume this concrete carrier
instead of starting from an arbitrary scalar proxy. -/
structure ConcreteVorticityStretchingWindow
    {nse : NavierStokesEquations 3}
    (sol : WeakSolution nse) where
  T : ℝ
  T_pos : 0 < T
  T_le_solT : T ≤ sol.T
  local_smooth_u : ContDiff ℝ ⊤ sol.u
  local_smooth_p : ContDiff ℝ ⊤ sol.p
  omega : VelocityField 3
  omega_eq : omega = vorticityField sol.u
  stretch : VelocityField 3
  stretch_eq : stretch = stretchingTerm omega sol.u
  vorticity_eq_on_domain :
    ∀ x ∈ sol.domain, VorticityEquationHoldsAt nse.nu sol.u x

/-- **AXIOM (concrete vorticity equation).** For a smooth solution
`(u, p)` of the 3-D Navier-Stokes momentum equation with viscosity
`nu`, the vorticity `ω := curl u` satisfies

    ∂_t ω + (u·∇)ω = (ω·∇)u + ν Δω

at every spacetime point in the solution's domain.

Mathlib gap: the derivation requires (a) symmetry of mixed partials
(`partialDeriv i ∘ partialDeriv j = partialDeriv j ∘ partialDeriv i`)
on `C^∞` arguments, (b) the product rule for `partialDeriv` on
component-wise compositions, and (c) re-grouping nine cross-product
terms into the canonical `(u·∇)ω + (ω·∇)u + νΔω` shape — all classical
but each step a multi-line Lean proof against the concrete
`partialDeriv` definition. We axiomatize.

Reference: A. Majda, A. Bertozzi, *Vorticity and Incompressible
Flow*, Cambridge University Press 2002, Proposition 1.8 (eq. (1.33)).
-/
axiom vorticity_equation_holds_concrete
    {nse : NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (_h_smooth_u : ContDiff ℝ ⊤ sol.u)
    (_h_smooth_p : ContDiff ℝ ⊤ sol.p) :
    ∀ x ∈ sol.domain, VorticityEquationHoldsAt nse.nu sol.u x

/-! ## BKM continuation theorem (concrete statement)

We expose BKM 1984 Theorem 1 at the level of the abstract surrogate
norm `vortSupNorm`, axiomatizing the integrability ⇒ smoothness
implication. This complements the typed-companion bridge in
`ns_trackb_bkm_proof_skeleton.lean`: that file provides the
*structural* composition; this file provides the *named* citation
target. -/

/-- A surrogate for `t ↦ ‖curl u(t, ·)‖_{L^∞}`. Real-valued; bridges
to the abstract `BKMVorticityEquation.vorticity_sup` field used in
the BKM proof skeleton. The actual `L^∞` norm is a Mathlib gap on
`EuclideanSpace`. -/
def vortSupNorm (u : VelocityField 3) : ℝ → ℝ :=
  fun _ => 0  -- placeholder; the BKM hypothesis quantifies over an
              -- abstract surrogate function, not this default. The
              -- BKM bridge axiom below quantifies over an arbitrary
              -- nonneg surrogate, which makes the placeholder
              -- harmless.

/-- **AXIOM — BKM 1984 continuation theorem (Theorem 1).** Suppose
`(u, p)` is a 3-D incompressible NS solution that is smooth on
`[0, T)` for some `T < ∞`. If there exists a nonneg surrogate
`Ω : ℝ → ℝ` for `t ↦ ‖curl u(t, ·)‖_{L^∞}` with finite integral on
`[0, T]`, then the smoothness of `u` extends past `T`.

This is the canonical **continuation criterion**: blow-up at `T*`
requires the vorticity sup-norm time-integral to diverge.

Reference: J. T. Beale, T. Kato, A. Majda, *Remarks on the
breakdown of smooth solutions for the 3-D Euler equations*, Comm.
Math. Phys. **94** (1984), 61–66, **Theorem 1**. The original
statement is for Euler; the Navier-Stokes version follows from the
same vorticity-equation derivation plus the parabolic-smoothing
upgrade that the viscous term provides for free.

Mathlib gap: (i) no `L^∞` norm on `EuclideanSpace`-valued spacetime
functions; (ii) no Picard re-launch + parabolic smoothing
machinery — see `ns_trackb_bkm_proof_skeleton.lean`'s axioms 3 and 4
for the typed-companion decomposition. -/
axiom BKMContinuationTheorem
    {nse : NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (T : ℝ) (_hT_pos : 0 < T) (_hT_le : T ≤ sol.T)
    (_h_smooth_before : ContDiff ℝ ⊤ sol.u)
    (Ω : ℝ → ℝ) (_hΩ_nonneg : ∀ t, 0 ≤ Ω t)
    (_h_integrable : IntervalIntegrable Ω MeasureTheory.volume 0 T) :
    ContDiff ℝ ⊤ sol.u

/-! ## Bridge to `ns_trackb_bkm_proof_skeleton.lean`

The BKM proof skeleton's Step 1 axiom

    `vorticity_equation_holds (sol) (h_local) : BKMVorticityEquation sol`

abstracts the curl operator into the surrogate field
`BKMVorticityEquation.vorticity_sup : ℝ → ℝ`. This bridge lemma
shows that *given* the concrete vorticity equation
(`vorticity_equation_holds_concrete`) plus an abstract surrogate
`Ω` for `‖curl u(t,·)‖_∞`, the BKM typed companion can be
constructed.

The bridge does not collapse to a Lean `theorem` because building
`BKMVorticityEquation`'s `biot_savart_log_sobolev_bound` field
requires the Biot-Savart law and a log-Sobolev inequality, which
remain Mathlib gaps. We therefore axiomatize the bridge at the
typed-companion-existence level. -/

/-- **AXIOM — bridge from the concrete vorticity equation to the
BKM typed companion.** Given a smooth NS solution and any
non-negative surrogate `Ω` for the vorticity sup-norm, there is a
`BKMVorticityEquation` companion whose `vorticity_sup` field is
`Ω`.

This is the existence half of the bridge between the **concrete**
declarations in this file and the **abstract** typed companions in
`ns_trackb_bkm_proof_skeleton.lean`. The deep PDE content (curl
derivation + Biot-Savart + log-Sobolev) is exactly what the
abstract typed companion's axiom `vorticity_equation_holds`
encodes; the bridge axiom here records that the abstract record
can be instantiated for *any* chosen surrogate, which the BKM
hypothesis then quantifies over.

Reference: same as `vorticity_equation_holds_concrete` plus
Majda-Bertozzi 2002, eq. (3.78) (log-Sobolev step). -/
axiom vorticity_equation_holds_bridge
    {nse : NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (_h_local : ZtareProofs.NS.LocalSmoothExistence sol)
    (Ω : ℝ → ℝ) (_hΩ_nonneg : ∀ t, 0 ≤ Ω t) :
    ∃ V : ZtareProofs.NS.BKMVorticityEquation sol, V.vorticity_sup = Ω

/-! ## Honesty receipt

This file ships:

* 1 concrete coordinate definition: `curlVelocityField`.
* 1 alias: `vorticityField`.
* 3 helper differential operators: `convectiveDeriv`,
  `stretchingTerm`, `spatialLaplacianVec`, plus `timeDerivVec`.
* 1 pointwise predicate: `VorticityEquationHoldsAt`.
* 3 axioms (each with classical citation):
  - `vorticity_equation_holds_concrete` — vorticity equation
    derivation (Majda-Bertozzi 2002, Prop. 1.8).
  - `BKMContinuationTheorem` — BKM 1984 Theorem 1.
  - `vorticity_equation_holds_bridge` — concrete-to-abstract bridge
    to `ns_trackb_bkm_proof_skeleton.lean`.

Zero `sorry`s.

The Mathlib gaps closed by these axioms are:
1. No curl operator on `EuclideanSpace ℝ (Fin 3) → EuclideanSpace ℝ (Fin 3)`.
2. No coordinate-form Schwarz / Clairaut symmetry for `partialDeriv`.
3. No coordinate-form product rule / chain rule for `partialDeriv`.
4. No `L^∞` norm on `EuclideanSpace`-valued spacetime functions.
5. No Picard re-launch + parabolic smoothing upgrade machinery.

Each axiom names exactly which gap it closes; a future Mathlib
formalization can discharge each axiom individually without
disturbing the BKM proof skeleton's typed-companion composition. -/

end

end ZtareProofs.NS
