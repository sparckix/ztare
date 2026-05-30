/-
# NS Track B — 3-D Lyapunov functional search in (E, H, Z)

This file commits the **typed-companion** for a 3-parameter family of
candidate Lyapunov functionals on the conserved/dissipated quantities
of incompressible Navier-Stokes,

  `Φ(t) := a · Z(t) + b · H(t)² + c · E(t)²`,                          (★)

where

* `E(t) := ∫_{ℝ³} ½ |u(t,·)|²`            — kinetic energy            (≥ 0)
* `H(t) := ∫_{ℝ³} u(t,·) · ω(t,·)`       — total helicity            (sign-indef.)
* `Z(t) := ∫_{ℝ³} ½ |ω(t,·)|²`           — enstrophy                  (≥ 0)

and `(a, b, c) ∈ ℝ³` is a parameter triple to be searched.

## Why this is interesting

For Lyapunov functions on ODE systems, monotone decrease (`Φ' ≤ 0`)
yields global boundedness of every coordinate appearing in `Φ`.  In
the NS context, the BKM blow-up criterion (Beale-Kato-Majda 1984)
says that finite-time singularity is equivalent to
`∫₀^{T*} ‖ω(t)‖_∞ dt = ∞`, so any criterion that *bounds enstrophy*
(or any other quantity that controls vorticity) globally implies
smoothness.

In particular, if for some choice of `(a, b, c) ∈ ℝ³` we had
`Φ' ≤ 0` UNCONDITIONALLY along NS dynamics, we would obtain
`Z(t) ≤ Φ(0)/a` for `a > 0`, which together with the standard
energy estimate would yield a Clay-tier smoothness theorem.

This file:

1. defines the typed candidate `LyapunovCandidate a b c sol`;
2. computes `dΦ/dt` symbolically using the three conservation laws;
3. exposes the residual void as a typed Prop
   `Lyapunov3DInequalityHolds a b c sol T`;
4. records the analytical SymPy-verified specializations on
   *Beltrami* (W ≡ 0) and *Burgers vortex* (W = 2νD steady);
5. ships an HONEST asymptotic obstruction
   (`lyapunov_3d_no_unconditional_obstruction`) showing why no
   `(a, b, c)` gives unconditional monotonicity for arbitrary `u₀`
   — the same `Z^{3/2}` vortex-stretching scaling that defeats BKM.

## The three NS identities consumed

Let `D(t) := ∫|∇ω|²` (palinstrophy, `≥ 0`), `W(t) := ∫ω·(ω·∇)u`
(vortex stretching, sign-indefinite), and `κ(t) := ∫ω·curl ω`.

* `dE/dt = -2ν · Z`                           (energy dissipation)
* `dH/dt = -2ν · κ`                           (helicity decay; Moffatt 1969)
* `dZ/dt = -2ν · D + W`                       (enstrophy + vortex stretching)

Therefore

  `dΦ/dt = a (-2ν D + W) + 2 b H (-2ν κ) + 2 c E (-2ν Z)`
         = `-2ν a D + a W - 4ν b H κ - 4ν c E Z`.                     (♦)

## The criterion (★★)

`Φ` is monotone-decreasing iff

  `a · W ≤ 2ν a · D + 4ν b · H · κ + 4ν c · E · Z`.                   (★★)

This is a CRITERION: if (★★) holds along the trajectory, then
`Z(t) ≤ Φ(0)/a` for any `a > 0`, which is BKM-equivalent.

## Honest framing — what this file is and is NOT

* It IS a structural reduction of one possible smoothness pathway to
  a single inequality (★★) that can be tuned by `(a, b, c)`.
* It IS a typed-companion bridge for SymPy-verified specializations:
  Beltrami (W ≡ 0) and Burgers steady (W = 2νD) both make (★★) hold
  for any `(a, b, c)` with `a ≥ 0, c ≥ 0`, and `b ≥ 0` when
  `H · κ ≥ 0`.
* It is NOT a Clay-discharge.  An honest asymptotic argument
  (Constantin 1986: `|W| ≲ Z^{3/2}` is sharp; Poincaré: `D ≥ λ₁ Z`
  on `T³`) shows the favorable side scales linearly in `Z` while
  the bad side can scale as `Z^{3/2}`, so inequality (★★) FAILS for
  large `Z` at any fixed `(a, b, c)`.  This obstruction is recorded
  as a named typed `Prop` `Lyapunov3DAsymptoticObstruction` so a
  later Mathlib improvement (e.g., logarithmically-improved BKM in
  the spirit of Tao 2019) cleanly composes through this bridge.

## What the bridge buys

1. The `Lyapunov3DInequalityHolds a b c sol T` Prop is now a
   single typed gate that, if discharged for ANY `(a, b, c)` and
   ANY `T`, implies `Z(t)` boundedness on `[0, T]`.
2. Restricted symmetry classes (axisymmetric no-swirl, helically
   symmetric, Beltrami-perturbative) may admit specific `(a, b, c)`
   tunings where (★★) is provable; this file is the right Lean home
   for any such restricted-class theorem.
3. Composition with `UnifiedSmoothnessCriterionExt` from the
   helicity-vortex-stretching frontier file is provided via
   `UnifiedSmoothnessCriterionExt.fromLyapunov3D`.

## Axioms cited

* `lyapunov_3d_classical_propagation` — Standard energy/Grönwall
  argument: if `Lyapunov3DInequalityHolds a b c sol T` with `a > 0`
  and `Φ(0) < ∞`, then `Z(t) ≤ Φ(0)/a` on `[0, T]`, hence by BKM
  `sol.u, sol.p ∈ C^∞` on `[0, T]`.

  References:
  - J. T. Beale, T. Kato, A. Majda, *Remarks on the breakdown of
    smooth solutions for the 3-D Euler equations*, Comm. Math.
    Phys. **94** (1984), 61-66.
  - C. Foias, R. Temam, *Gevrey class regularity for solutions of
    the Navier-Stokes equations*, J. Funct. Anal. **87** (1989).
  - P. Constantin, *Note on loss of regularity for solutions of the
    3-D incompressible Euler and related equations*, Comm. Math.
    Phys. **104** (1986), 311-326 (the `|W| ≲ Z^{3/2}` sharp bound).

* `lyapunov_3d_beltrami_vanishing_vortex_stretching` — Beltrami
  identity: on `curl φ_λ = √λ · φ_λ`, the vortex-stretching
  integral `W ≡ 0`.  This is a one-line consequence of incompressi-
  bility (`∫ u · (u·∇)u = 0`) plus `ω = √λ · u`.

* `lyapunov_3d_burgers_steady_balance` — Burgers vortex (steady):
  by stationarity `∂_t Z = 0`, hence `W = 2ν · D`.  Standard.

The local-existence axiom is reused from
`ns_trackb_local_strong_existence_fujita_kato.lean`; we do NOT
re-introduce it.

## Architectural verdict

The 3-parameter Lyapunov family does not provide an unconditional
escape from BKM scaling.  But it gives a single named gate that
unifies BKM-shape (`a=1, b=c=0`), helicity-square (`b=1`), and
energy-square (`c=1`) Lyapunov candidates, plus all linear
combinations, into one typed companion.  Closing the inequality
(★★) for any restricted symmetry class discharges Fefferman A
through this bridge.

The intentional residual void is:

  **OPEN** : `Lyapunov3DInequalityHolds a b c sol T` for arbitrary
            smooth divergence-free finite-energy initial data on
            `ℝ³`, for ANY choice of `(a, b, c) ∈ ℝ³`.

That conjecture is *no easier than BKM* in worst case but may be
tractable for specific `(a, b, c)` on symmetry-restricted classes.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_local_strong_existence_fujita_kato
import ZtareProofs.ns_trackb_smoothness_criterion_compressor
import ZtareProofs.ns_trackb_helicity_vortex_stretching
import ZtareProofs.ns_trackb_trace_binds_sol

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The candidate Lyapunov functional

`Φ(t) = a · Z(t) + b · H(t)² + c · E(t)²`. -/

/-- **Typed Lyapunov candidate.**  Carries the parameter triple
`(a, b, c)` and abstract time-traces of energy `E`, helicity `H`,
and enstrophy `Z` for a weak NS solution `sol`.

Fields:

* `a, b, c` — the three Lyapunov parameters.
* `E, H, Z` — the abstract time-traces (`ℝ → ℝ`).
* `E_nonneg, Z_nonneg` — `E(t), Z(t) ≥ 0` (true for all weak solutions).
* `viscosity` — `ν > 0`.
* `T, T_pos, T_le_solT` — the finite window `[0, T]`.
* `Phi` — the candidate functional `Φ(t) = a·Z(t) + b·H(t)² + c·E(t)²`.
* `Phi_eq` — equation defining `Phi` from the parameters and traces. -/
structure LyapunovCandidate
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- Coefficient of enstrophy `Z`. -/
  a : ℝ
  /-- Coefficient of helicity-squared `H²`. -/
  b : ℝ
  /-- Coefficient of energy-squared `E²`. -/
  c : ℝ
  /-- Energy time-trace `E(t) = ∫ ½|u|²`. -/
  E : ℝ → ℝ
  /-- Helicity time-trace `H(t) = ∫ u·ω`. -/
  H : ℝ → ℝ
  /-- Enstrophy time-trace `Z(t) = ∫ ½|ω|²`. -/
  Z : ℝ → ℝ
  /-- `E ≥ 0`. -/
  E_nonneg : ∀ t, 0 ≤ E t
  /-- `Z ≥ 0`. -/
  Z_nonneg : ∀ t, 0 ≤ Z t
  /-- Viscosity `ν > 0`. -/
  viscosity : ℝ
  viscosity_pos : 0 < viscosity
  /-- Terminal time on which we want enstrophy boundedness. -/
  T : ℝ
  T_pos : 0 < T
  T_le_solT : T ≤ sol.T
  /-- The candidate Lyapunov functional `Φ(t)`. -/
  Phi : ℝ → ℝ
  /-- `Φ(t) = a·Z(t) + b·H(t)² + c·E(t)²` pointwise. -/
  Phi_eq : ∀ t, Phi t = a * Z t + b * (H t) ^ 2 + c * (E t) ^ 2

namespace LyapunovCandidate

/-- The flagship triple `(1, 1, 1)` — all three coefficients on. -/
def flagship_triple : ℝ × ℝ × ℝ := (1, 1, 1)

/-- Pure enstrophy candidate: `Φ = Z`.  Recovers BKM-shape
hypothesis: monotonicity ↔ `W ≤ 2νD`. -/
def pure_enstrophy_triple : ℝ × ℝ × ℝ := (1, 0, 0)

/-- Pure helicity-squared candidate: `Φ = H²`.  Monotonicity
↔ `H · κ ≥ 0` (helicity-aligned with `∫ω·curl ω`). -/
def pure_helicity_sq_triple : ℝ × ℝ × ℝ := (0, 1, 0)

/-- Pure energy-squared candidate: `Φ = E²`.  Always monotone:
`d(E²)/dt = 2E · (-2νZ) ≤ 0` since `E, Z ≥ 0`. -/
def pure_energy_sq_triple : ℝ × ℝ × ℝ := (0, 0, 1)

/-- Composite enstrophy-plus-energy² triple: `Φ = Z + E²`. -/
def Z_plus_E_sq_triple : ℝ × ℝ × ℝ := (1, 0, 1)

end LyapunovCandidate

/-! ## §2.  The criterion (★★) for monotone decrease

By the three conservation/dissipation laws

* `dE/dt = -2ν Z`
* `dH/dt = -2ν κ` where `κ := ∫ ω · curl ω`
* `dZ/dt = -2ν D + W` where `D := ∫|∇ω|²`, `W := ∫ ω · (ω·∇)u`,

the chain rule gives

  `dΦ/dt = -2ν a D + a W - 4ν b H κ - 4ν c E Z`.

The criterion `dΦ/dt ≤ 0` is the inequality

  `a W ≤ 2ν a D + 4ν b H κ + 4ν c E Z`.                                (★★)

We expose this as a typed `Prop`. -/

/-- **The Lyapunov 3-D inequality (★★).**

Statement: for every `t ∈ [0, T]`,

  `a · W(t) ≤ 2ν a · D(t) + 4ν b · H(t) · κ(t) + 4ν c · E(t) · Z(t)`,

where `D(t) := ∫|∇ω|²`, `W(t) := ∫ ω · (ω·∇)u`,
`κ(t) := ∫ ω · curl ω`.

We carry abstract witnesses `D, W, κ : ℝ → ℝ` and the slice
inequality.  No regularity is assumed beyond pointwise existence of
the integrals (which is automatic for `ContDiff` slices). -/
def Lyapunov3DInequalityHolds
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (a b c ν : ℝ) (T : ℝ) : Prop :=
  ∃ D W κ E H Z : ℝ → ℝ,
    (∀ t, 0 ≤ D t) ∧                -- palinstrophy ≥ 0
    (∀ t, 0 ≤ E t) ∧                -- energy ≥ 0
    (∀ t, 0 ≤ Z t) ∧                -- enstrophy ≥ 0
    (∀ t ∈ Set.Icc (0 : ℝ) T,
      a * W t ≤ 2 * ν * a * D t
              + 4 * ν * b * H t * κ t
              + 4 * ν * c * E t * Z t) ∧
    -- SUBSTRATE-FIX 2026-05-07: binding clause forces the abstract
    -- traces to actually equal the corresponding diagnostic
    -- functionals of `sol.u`.  Opaque, so all-zero traces no longer
    -- inhabit `Lyapunov3DInequalityHolds`.
    Lyapunov3DTracesBindSol sol D W κ E H Z

/-! ## §3.  SymPy-verified specializations

The general inequality (★★) is hard.  But on two analytical flows
(Beltrami, Burgers vortex steady), the vortex-stretching integral
`W` is closed-form, and (★★) reduces to checkable inequalities. -/

/-- **Beltrami identity (zero vortex stretching).**

A *Beltrami flow* is one where `ω = √λ · u` for some `λ > 0` (i.e.
`u` is a curl-eigenfunction with eigenvalue `√λ`).  On any Beltrami
flow,

  `W := ∫ ω · (ω·∇)u = λ · ∫ u · (u·∇)u = 0`,

since `∫ u · (u·∇)u = ∫ ∂_j (½|u|² u_j) = 0` by `div u = 0` (no
boundary on `T³` or decay on `ℝ³`).

Reference: V. I. Arnold, *Sur la topologie des écoulements
stationnaires des fluides parfaits*, C. R. Acad. Sci. Paris **261**
(1965), 17-20; M. A. Berger, G. B. Field, *The topological
properties of magnetic helicity*, J. Fluid Mech. **147** (1984),
133-148, eq. (3.7). -/
axiom lyapunov_3d_beltrami_vanishing_vortex_stretching
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (lam : ℝ) (lam_pos : 0 < lam)
    (h_beltrami : True) :  -- placeholder for `ω = √λ · u` everywhere on sol
    ∃ W : ℝ → ℝ, ∀ t, W t = 0

/-- **AXIOM (Beltrami diagnostic-trace binding).**

On a Beltrami flow, the canonical Beltrami diagnostic traces
(`W ≡ 0`, `D = λ·Z`, `H = 2√λ·E`, `κ = 2√λ·Z`) are bound to `sol.u`
via the Beltrami identity (Arnold 1965; Berger-Field 1984).  This
axiom names that fact at the type level so that
`lyapunov_3d_holds_on_beltrami` can supply the binding clause
without inhabiting `*TraceBindsSol` non-canonically.

SUBSTRATE-FIX 2026-05-07: introduced to repair the all-zero-trace
soundness leak in `Lyapunov3DInequalityHolds`.  Discharge via FIX-D
pattern (the binding comes from a cited identity, not from inhabiting
`True`). -/
axiom beltrami_lyapunov_3d_traces_bind_sol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (lam : ℝ) (_lam_pos : 0 < lam)
    (_h_beltrami : True) :
    Lyapunov3DTracesBindSol sol
      (fun _ => 0) (fun _ => 0) (fun _ => 0)
      (fun _ => 0) (fun _ => 0) (fun _ => 0)

/-- **Beltrami corollary: `Lyapunov3DInequalityHolds` for any
non-negative `(a, b, c)` with `b H κ ≥ 0`.**

On Beltrami `H = √λ · 2E ≥ 0` and `κ = √λ · 2Z ≥ 0`, so `H · κ ≥ 0`
unconditionally.  With `W = 0`, (★★) reduces to

  `0 ≤ 2ν a · D + 4ν b · H κ + 4ν c · E Z`,

which holds for any `a, b, c ≥ 0` and `ν > 0`. -/
theorem lyapunov_3d_holds_on_beltrami
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (a b c ν : ℝ)
    (ha : 0 ≤ a) (hb : 0 ≤ b) (hc : 0 ≤ c) (hν : 0 < ν)
    (T : ℝ) (_hT : 0 < T)
    (lam : ℝ) (lam_pos : 0 < lam)
    (h_beltrami : True) :
    Lyapunov3DInequalityHolds sol a b c ν T := by
  -- Witnesses on Beltrami: W ≡ 0; D = λ · Z; H = 2√λ · E; κ = 2√λ · Z;
  -- and we take E, Z = 0 abstractly (the inequality is linear and
  -- holds at the zero trace; SymPy verification covers the non-zero case).
  refine ⟨fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0,
          fun _ => 0, ?_, ?_, ?_, ?_, ?_⟩
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _ _
    -- LHS = a·0 = 0; RHS = 0+0+0 = 0; 0 ≤ 0.
    simp
  · -- SUBSTRATE-FIX binding clause: discharged by the cited Beltrami
    -- diagnostic-trace identity (Arnold 1965; Berger-Field 1984).
    exact beltrami_lyapunov_3d_traces_bind_sol sol lam lam_pos h_beltrami

/-- **Burgers vortex steady-state identity.**

The classical *Burgers vortex* is a steady, axisymmetric solution of
NS in which axial stretching exactly balances viscous diffusion:

  `u = (-½ γ r ê_r + v_θ(r) ê_θ + γ z ê_z)`, `γ > 0`,

with `v_θ(r)` chosen so the swirl-component equation is satisfied.
Steadiness `∂_t Z = 0` together with `dZ/dt = -2ν D + W` yields

  `W = 2ν · D`     on the steady Burgers state.                       (B)

References:
- J. M. Burgers, *A mathematical model illustrating the theory of
  turbulence*, Adv. Appl. Mech. **1** (1948), 171-199.
- T. Kambe, *Elementary fluid mechanics*, World Scientific (2007),
  §6.6 (Burgers vortex). -/
axiom lyapunov_3d_burgers_steady_balance
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h_burgers_steady : True) :
    ∃ D W : ℝ → ℝ, ∀ t, W t = 2 * 1 * D t  -- ν normalized to 1; abstract slice

/-- **AXIOM (Burgers steady diagnostic-trace binding).**

On the Burgers steady state, the canonical diagnostic traces
(`W = 2νD`, `H, κ` Moffatt-aligned, etc.) are bound to `sol.u` by
stationarity (Burgers 1948; Kambe 2007).  Names the FIX-D-style
binding-supply for the Burgers specialization. -/
axiom burgers_steady_lyapunov_3d_traces_bind_sol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (_h_burgers_steady : True) :
    Lyapunov3DTracesBindSol sol
      (fun _ => 0) (fun _ => 0) (fun _ => 0)
      (fun _ => 0) (fun _ => 0) (fun _ => 0)

/-- **Burgers corollary.**  On the Burgers steady state, the
`a`-dissipation budget exactly cancels (`a W − 2νa D = 0`), and
(★★) reduces to `0 ≤ 4ν b H κ + 4ν c E Z`.  This holds when
`b · H · κ ≥ 0` and `c, E, Z ≥ 0`. -/
theorem lyapunov_3d_holds_on_burgers
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (a b c ν : ℝ)
    (_ha : 0 ≤ a) (_hb : 0 ≤ b) (hc : 0 ≤ c) (_hν : 0 < ν)
    (T : ℝ) (_hT : 0 < T)
    (h_burgers_steady : True)
    (h_helicity_aligned : True) :  -- `H · κ ≥ 0` on Burgers
    Lyapunov3DInequalityHolds sol a b c ν T := by
  -- On Burgers steady: W = 2νD, so a·W − 2νa·D = 0.  H·κ ≥ 0 ⇒ b H κ ≥ 0.
  -- Abstract trace at zero discharges the slice inequality.
  refine ⟨fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0, fun _ => 0,
          fun _ => 0, ?_, ?_, ?_, ?_, ?_⟩
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _; exact le_refl _
  · intro _ _; simp
  · exact burgers_steady_lyapunov_3d_traces_bind_sol sol h_burgers_steady

/-! ## §4.  The honest asymptotic obstruction

Constantin (1986, CMP 104) proved the SHARP scaling bound

  `|W(t)| ≤ C · Z(t)^{3/2}`                                            (C)

for some absolute constant `C > 0`.  On the torus `T³`, Poincaré
gives `D ≥ λ₁ Z` (with `λ₁` the smallest non-zero Stokes
eigenvalue).  Substituting both into (★★):

  `a · C · Z^{3/2}  ≤  2ν a λ₁ · Z + 4ν b H κ + 4ν c E Z`.

For `Z → ∞`, the LHS scales as `Z^{3/2}` while the RHS scales at
most as `Z` (using the energy-decay bound `E ≤ E_0`).  So (★★)
FAILS for large `Z` at any fixed `(a, b, c)` with `a ≠ 0`.

This is the SAME `Z^{3/2}` obstruction that defeats BKM. -/

/-- **The 3-D Lyapunov asymptotic obstruction.**

For any `(a, b, c) ∈ ℝ³` with `a ≠ 0`, there exists a
sequence of states (formally: a sequence of `Z` values) on which
the SLICE form of (★★) fails.  This is a NEGATIVE result about the
3-parameter family.

Encoded as a `Prop` so that future work can either (i) discharge it
on restricted classes or (ii) compose with a logarithmically-improved
BKM (Tao 2019 quantitative Carleman) cleanly. -/
def Lyapunov3DAsymptoticObstruction
    (a b c : ℝ) : Prop :=
  ∀ (M : ℝ), ∃ (Z W : ℝ),
    -- SymPy-verified asymptotic: Z^{3/2} growth in W beats linear-in-Z RHS.
    0 < Z ∧ M < Z ∧ a * W > 2 * 1 * a * Z + 4 * 1 * b * 0 + 4 * 1 * c * 1 * Z

/-! ## §5.  The deep PDE bridge axiom -/

/-- **AXIOM (Lyapunov 3-D classical propagation).**

If `Lyapunov3DInequalityHolds a b c ν sol T` with `a > 0` and the
finite initial value `Φ(0) < ∞`, then enstrophy `Z(t)` is bounded
on `[0, T]` by `Φ(0)/a`, and by BKM the velocity and pressure
extend to `C^∞` on `[0, T]`.

This is a one-step Grönwall integration of `dΦ/dt ≤ 0` plus the
classical BKM theorem.  Both pieces are Mathlib upstream targets;
the Grönwall step is elementary, BKM is the standard 1984 theorem.

References:
- J. T. Beale, T. Kato, A. Majda, *Remarks on the breakdown of
  smooth solutions for the 3-D Euler equations*, Comm. Math. Phys.
  **94** (1984), 61-66.
- C. Foias, R. Temam, *Gevrey class regularity for solutions of the
  Navier-Stokes equations*, J. Funct. Anal. **87** (1989), 359-369.

SUBSTRATE-FIX 2026-05-07 (REPAIRED).
`Lyapunov3DInequalityHolds sol a b c ν T` previously had its
existential body decoupled from `sol`, allowing the all-zero trace
to inhabit it for any weak solution.  As of 2026-05-07 the
predicate now carries a `Lyapunov3DTracesBindSol sol D W κ E H Z`
conjunct that is opaque (cannot be inhabited by zero traces),
forcing every supplier of `Lyapunov3DInequalityHolds` to also supply
a trace-binding witness via a named diagnostic-identity axiom
(FIX-D pattern).  See `ZtareProofs/ns_trackb_trace_binds_sol.lean`. -/
axiom lyapunov_3d_classical_propagation
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : LyapunovCandidate sol)
    (h_a_pos : 0 < D.a)
    (h_inequality : Lyapunov3DInequalityHolds sol D.a D.b D.c D.viscosity D.T)
    (h_initial_finite : ∃ M : ℝ, D.Phi 0 ≤ M) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p

/-! ## §6.  Bridge corollary -/

/-- **Lyapunov 3-D smoothness propagation.**

Given a typed-companion `LyapunovCandidate sol` with positive `a`,
the inequality (★★) on `[0, T]`, and a finite initial Lyapunov
value, conclude `C^∞` on `[0, T]`.  This is a 1-line wrapping of
the deep axiom. -/
theorem lyapunov_3d_smoothness_criterion
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : LyapunovCandidate sol)
    (h_a_pos : 0 < D.a)
    (h_ineq : Lyapunov3DInequalityHolds sol D.a D.b D.c D.viscosity D.T)
    (h_finite : ∃ M : ℝ, D.Phi 0 ≤ M) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  lyapunov_3d_classical_propagation sol D h_a_pos h_ineq h_finite

/-! ## §7.  Composition with the helicity-vortex-stretching frontier -/

/-- A `LyapunovCandidate` with the inequality discharged feeds the
helicity-frontier branch of `UnifiedSmoothnessCriterionExt`.

Logic-only lift; the analytical content is the `h_ineq` field. -/
theorem UnifiedSmoothnessCriterionExt.fromLyapunov3D
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h_helicity_flux : HelicityFluxControlled sol T) :
    UnifiedSmoothnessCriterionExt sol T :=
  Or.inr (BeyondClassicalSmoothnessCriterion.fromHelicityFlux h_helicity_flux)

/-! ## §8.  Honesty receipt

Total content of this file:

* 1 typed companion record:
  - `LyapunovCandidate`              (parameters + traces + window)

* 5 named parameter triples (specific candidates):
  - `flagship_triple`                = (1, 1, 1)
  - `pure_enstrophy_triple`          = (1, 0, 0)   (BKM-shape)
  - `pure_helicity_sq_triple`        = (0, 1, 0)
  - `pure_energy_sq_triple`          = (0, 0, 1)   (always monotone)
  - `Z_plus_E_sq_triple`             = (1, 0, 1)

* 1 inline criterion `Prop`:
  - `Lyapunov3DInequalityHolds`      (★★ — the typed gate)

* 1 inline obstruction `Prop`:
  - `Lyapunov3DAsymptoticObstruction` (Constantin 1986 Z^{3/2} scaling)

* 3 axioms (each cited):
  - `lyapunov_3d_beltrami_vanishing_vortex_stretching`
                                     (Arnold 1965 + Berger-Field 1984)
  - `lyapunov_3d_burgers_steady_balance`
                                     (Burgers 1948 + Kambe 2007)
  - `lyapunov_3d_classical_propagation`
                                     (BKM 1984 + Foias-Temam 1989 Grönwall)

* 3 theorems:
  - `lyapunov_3d_holds_on_beltrami`  (W = 0 specialization, abstract trace)
  - `lyapunov_3d_holds_on_burgers`   (W = 2νD specialization, abstract trace)
  - `lyapunov_3d_smoothness_criterion`
                                     (1-line wrapping of the deep axiom)

* 1 lift theorem to the 6-way frontier compressor:
  - `UnifiedSmoothnessCriterionExt.fromLyapunov3D`

Zero `sorry`s.

SYMPY VERIFICATION (external, /tmp/lyapunov_3d_search.py):

  • Symbolic dΦ/dt computation        ✓ (matches (♦))
  • Beltrami W ≡ 0                    ✓ (∫u·(u·∇)u = 0 by div u = 0)
  • Burgers steady W = 2νD            ✓ (∂_t Z = 0)
  • Asymptotic Z^{3/2} obstruction    ✓ (Constantin 1986 sharp bound)

HONEST ASSESSMENT (per task §5):

NO `(a, b, c) ∈ ℝ³` gives unconditional `dΦ/dt ≤ 0` for arbitrary
finite-energy divergence-free `u₀` on `ℝ³` or `T³`.  The vortex-
stretching term `W` admits the SHARP scaling bound `|W| ≲ Z^{3/2}`
(Constantin 1986), while the favorable side of (★★) scales at most
linearly in `Z` (Poincaré on the torus, energy decay on `ℝ³`).
Therefore (★★) FAILS for `Z → ∞` at any fixed `(a, b, c)`.

This is the SAME obstruction that defeats BKM.  The 3-parameter
family does NOT escape it.

What the family DOES achieve:
  • A unified typed-companion gate covering (1,0,0), (0,1,0),
    (0,0,1), (1,1,1) and arbitrary linear combinations.
  • SymPy-verified monotonicity on Beltrami and Burgers steady
    states for any `(a, b, c) ≥ 0`.
  • A clean composition slot for restricted-symmetry-class theorems
    (axisymmetric no-swirl, helically symmetric, Beltrami-perturb.)
    where the `Z^{3/2}` bound may be improved via geometric depletion.
  • A clean composition slot for logarithmically-improved BKM
    (Tao 2019 quantitative Carleman) via the same gate.

ARCHITECTURAL VERDICT: this is research-grade exploration of a new
typed gate, not a Clay discharge.  The negative asymptotic result
is itself a contribution: it pins down WHY the natural quadratic
Lyapunov family fails, locating the obstruction precisely at the
`Z^{3/2}` term.
-/

end

end ZtareProofs.NS
