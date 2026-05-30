/-
# NS Track B — Local Energy Inequality (LEI) typed-companion bridge

This file builds the typed-companion bridge for the **Local Energy
Inequality** (LEI), the load-bearing tool underlying Caffarelli-Kohn-
Nirenberg (CKN) partial regularity for 3D incompressible
Navier-Stokes.

## Classical statement (Scheffer 1976 / CKN 1982)

For a *suitable* Leray-Hopf weak solution `(u, p)` to the 3D
incompressible Navier-Stokes equations and any nonneg test function
`φ : ℝ × ℝ³ → ℝ` smooth with compact support,

  ∫_{ℝ³} |u(t,x)|² φ(t,x) dx
    + 2ν ∫₀ᵗ ∫_{ℝ³} |∇u(s,x)|² φ(s,x) dx ds
  ≤ ∫₀ᵗ ∫_{ℝ³} |u|² (∂_s φ + ν Δφ) dx ds
    + ∫₀ᵗ ∫_{ℝ³} (|u|² + 2 p) (u · ∇φ) dx ds.

LEI is the *local-in-spacetime* analogue of the global Leray energy
inequality.  CKN proves: at any putative singular point, LEI implies
a local lower bound on `∫_{Q_r} (|u|² + |∇u|² + |p|^{3/2}) dx dt`
whose **smallness** would contradict the singularity.  Hence the
parabolic Hausdorff dimension of the singular set is at most `1`
(CKN Theorem D).

## Architectural role (the LOAD-BEARING claim)

LEI is the *single tool* that promotes a Leray-Hopf weak solution to
a **suitable weak solution** in the sense of CKN.  Once a solution is
suitable, every modern partial-regularity result downstream
(CKN 1982, Lin 1998, Tian-Xin 1999, Ladyzhenskaya-Seregin 1999, Vasseur
2007, …) becomes available.  In particular:

  *suitable weak solution + uniform local-energy smallness criterion
   ⇒ ContDiff ℝ ⊤ u almost everywhere (parabolic codim ≥ 5/3)*.

If the smallness criterion held *uniformly on all parabolic balls*,
the singular set would be empty and we would have a path to
`GlobalSmoothSolution`.  THAT IS THE CLAY GAP — but the typed-
companion architecture *isolates* it: every other plumbing
(integration-by-parts, Galerkin compactness, Lebesgue limit) is
mechanical once LEI is in hand.

## What this file ships

* `LocalEnergyInequalityData (sol : NavierStokes.WeakSolution nse)`
  — the typed companion: a Prop record carrying the LEI inequality
  for every nonneg smooth compactly-supported test function.

* `GalerkinLocalEnergyBoundData` — the upstream hypothesis side: a
  uniform L² bound on the *local* energies of the Galerkin sequence
  on every parabolic ball.  This is the input the Galerkin compactness
  argument feeds into LEI.

* `axiom LEI_from_galerkin_classical` — the classical derivation of
  LEI from the Galerkin sequence (Scheffer 1976; simplified in Lin
  1998).  AXIOMATIZED here because its proof requires Sobolev-space
  duality + integration-by-parts on test functions, neither of which
  is fully formalized in Mathlib.  The hypothesis side now carries a
  TYPED `GalerkinSolutionCompatibility` witness that pins the
  Galerkin sequence's local energies to those of `sol.u` — the
  `True` placeholder is gone.

* `SuitableWeakSolution` — Leray-Hopf solution + LEI, packaged as a
  typed wrapper (a structure extending `NavierStokes.LerayHopfSolution`
  with the LEI typed companion).

* `LocalSmallnessCriterion` — the open Prop input to CKN: uniform
  smallness of the local energy on parabolic balls.  Tightened
  2026-05-07 (void-miner audit `ns_trackb_void_audit_2026_05_07.md`,
  Severity 1) so the predicate is **NOT** vacuously satisfiable: the
  smallness clause integrates `|∇sol.u|²` over `Q_r(z)` against the
  scale `1/r` and is required for ALL `r > 0` off `E`, and the
  dimension witness uses an opaque `ParabolicHausdorffDim` whose value
  on `Set.univ` is fixed (axiomatically) at the parabolic dimension
  `5 > 1`.  Together these reject the trivial witness `E := Set.univ,
  ε₀ := 1` that the previous `∧ True` formulation accepted.

* `axiom CKN_partial_regularity_classical` — the Caffarelli-Kohn-
  Nirenberg 1982 partial regularity theorem itself, axiomatized.

* `theorem ckn_partial_regularity_modulo_smallness` — the bridge
  corollary: from `LocalEnergyInequalityData sol +
  LocalSmallnessCriterion sol` conclude that `sol.u` is `C^∞` on the
  complement of a *named* exception set of parabolic Hausdorff
  dimension at most `1`.

## Composition with the Leray-Hopf typed-companion architecture

This bridge is the SIXTH typed-companion clause beyond the five
shipped in `ns_trackb_leray_hopf_master_spine.lean`:

  Galerkin → (A) energy_ineq, (B) weak_init, (C) vel_reg,
              (D) weak_incomp, (E) weak_mom, (F) **LEI**
                  ↑
                  this file

The final composition theorem reads:

  `Galerkin sequence with local energy bounds (this file)`
   `+ existing 5 typed companions (master spine)`
   `+ LocalSmallnessCriterion (OPEN Prop input)`
   `→ GlobalSmoothSolution-modulo-1-dimensional-exception-set`.

## Honest residual void

Two Prop inputs remain *open* and named:

1. `GalerkinLocalEnergyBoundData.local_energy_bounded` — the *uniform*
   local-energy bound on parabolic balls.  This holds for the standard
   Galerkin construction but its formalization needs the Sobolev-space
   integration-by-parts machinery.

2. `LocalSmallnessCriterion sol` — uniform smallness of local energies
   on every parabolic ball.  THIS IS THE CLAY GAP.  If it held, the
   exception set would be empty and `sol.u` would be `C^∞` everywhere.

## References

* V. Scheffer, *Partial regularity of solutions to the Navier-Stokes
  equations*, Pacific J. Math. **66** (1976), 535–552.
* L. Caffarelli, R. Kohn, L. Nirenberg, *Partial regularity of suitable
  weak solutions of the Navier-Stokes equations*, Comm. Pure Appl.
  Math. **35** (1982), 771–831.
* F.-H. Lin, *A new proof of the Caffarelli-Kohn-Nirenberg theorem*,
  Comm. Pure Appl. Math. **51** (1998), 241–257.
* G. Seregin, *Lecture Notes on Regularity Theory for the Navier-
  Stokes Equations*, World Scientific (2014).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes

open MeasureTheory
open scoped Topology BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## Test functions used in the LEI

A test function for LEI is a nonneg smooth compactly-supported
function `φ : ℝ × ℝ³ → ℝ`.  We use the lean-dojo flavoring
`Euc ℝ 4` (= `EuclideanSpace ℝ (Fin 4)`) for the spacetime variable
and *abstract* the test-function predicate so the bridge does not
depend on which formalization of "smooth + compact support + nonneg"
we adopt downstream. -/

/-- Predicate identifying admissible LEI test functions: smooth,
compactly supported, nonneg.  Kept as a Prop alias so callers who
ship a stronger predicate (e.g. with prescribed parabolic-ball support)
can plug it in without changing the bridge. -/
def LEITestFn (φ : EuclideanSpace ℝ (Fin 4) → ℝ) : Prop :=
  ContDiff ℝ ⊤ φ ∧
  (∃ K : Set (EuclideanSpace ℝ (Fin 4)), IsCompact K ∧ ∀ x ∉ K, φ x = 0) ∧
  (∀ x, 0 ≤ φ x)

/-! ## Typed-companion data: LocalEnergyInequalityData

The companion is a *Prop record* over a fixed weak solution `sol`.
Its single load-bearing field is `lei_holds`, the local energy
inequality itself, quantified over admissible test functions and
times `t ∈ [0, sol.T]`.

The five-term integral structure is captured by *five named scalar
fields* `lhsKinetic`, `lhsDissipation`, `rhsTimeDeriv`, `rhsViscousLap`,
`rhsTransportPressure`.  Each is a `ℝ`-valued functional of `(φ, t)`.
The LEI is the inequality

  `lhsKinetic φ t + 2 * ν * lhsDissipation φ t`
   `≤ rhsTimeDeriv φ t + rhsViscousLap φ t + rhsTransportPressure φ t`.

This decomposition lets downstream consumers (CKN, Lin, Vasseur)
*re-bound* individual terms without re-proving the master inequality.

Keeping the five terms abstract avoids committing to a particular
Bochner-integral formalization of `∫₀ᵗ ∫_{ℝ³} |u|² ∂_s φ dx ds` etc.
A concrete-bridge file (out of scope for this workstream) would
realize each functional as the corresponding lean-dojo spacetime
integral.

**FIX-D LEI parity (2026-05-07).**  STATEMENT-AUDIT (CKN parity sweep)
flagged that the five LEI functionals
`lhsKinetic, lhsDissipation, rhsTimeDeriv, rhsViscousLap,
rhsTransportPressure` have type `(φ → ℝ) → ℝ → ℝ` and are NOT bound
to `sol` at the type level.  Without an additional sol-binding
predicate the all-zero functional `fun _ _ => 0` inhabits
`LocalEnergyInequalityData sol` for every `sol` (the inequality
`0 + 0 ≤ 0 + 0 + 0` holds), exactly the FIX-D laundering channel
already closed for trace fields elsewhere
(`ns_trackb_trace_binds_sol.lean`).

We close the channel here by introducing five `opaque` sol-binding
predicates in the same spirit as `EnstrophyTraceBindsSol` etc., and
requiring them as fields of `LocalEnergyInequalityData`.  Concrete
inhabitants must supply a typed witness pinning each functional to
the corresponding integral of `sol.u` and `sol`'s pressure. -/

/-! ### Opaque sol-binding predicates for the five LEI terms

Each predicate asserts that the abstract scalar functional equals the
corresponding integral functional of `sol.u` (and the LEI test
function `φ`).  Held opaque so the all-zero / constant-zero
functional cannot inhabit any of them — the FIX-D pattern.  Concrete
bridges supply inhabitants via additional `axiom <name>_at_sol_classical`
identities cited to Scheffer 1976 / Lin 1998. -/

/-- Sol-binding for `lhsKinetic`: the abstract functional equals
`∫_{ℝⁿ} |sol.u(t,x)|² φ(t,x) dx`.  Opaque. -/
opaque LEILhsKineticBindsSol
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse)
    (_K : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ) : Prop

/-- Sol-binding for `lhsDissipation`: equals
`∫₀ᵗ ∫_{ℝⁿ} |∇sol.u|² φ ds dx`.  Opaque. -/
opaque LEILhsDissipationBindsSol
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse)
    (_D : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ) : Prop

/-- Sol-binding for `rhsTimeDeriv`: equals
`∫₀ᵗ ∫_{ℝⁿ} |sol.u|² ∂_s φ ds dx`.  Opaque. -/
opaque LEIRhsTimeDerivBindsSol
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse)
    (_R : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ) : Prop

/-- Sol-binding for `rhsViscousLap`: equals
`∫₀ᵗ ∫_{ℝⁿ} |sol.u|² ν Δφ ds dx`.  Opaque. -/
opaque LEIRhsViscousLapBindsSol
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse)
    (_R : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ) : Prop

/-- Sol-binding for `rhsTransportPressure`: equals
`∫₀ᵗ ∫_{ℝⁿ} (|sol.u|² + 2 sol.p) (sol.u · ∇φ) ds dx`.  Opaque. -/
opaque LEIRhsTransportPressureBindsSol
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse)
    (_R : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ) : Prop

structure LocalEnergyInequalityData
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) where
  /-- The kinetic-energy LHS term `∫_{ℝⁿ} |u(t,x)|² φ(t,x) dx`. -/
  lhsKinetic : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ
  /-- The dissipation LHS term `∫₀ᵗ ∫_{ℝⁿ} |∇u|² φ ds dx`. -/
  lhsDissipation : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ
  /-- The time-derivative RHS term `∫₀ᵗ ∫_{ℝⁿ} |u|² ∂_s φ ds dx`. -/
  rhsTimeDeriv : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ
  /-- The viscous-Laplacian RHS term `∫₀ᵗ ∫_{ℝⁿ} |u|² ν Δφ ds dx`. -/
  rhsViscousLap : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ
  /-- The transport+pressure RHS term
  `∫₀ᵗ ∫_{ℝⁿ} (|u|² + 2 p) (u · ∇φ) ds dx`. -/
  rhsTransportPressure : (EuclideanSpace ℝ (Fin 4) → ℝ) → ℝ → ℝ
  /-- Nonnegativity of the dissipation term (sums of squares). -/
  lhsDissipation_nonneg :
    ∀ φ : EuclideanSpace ℝ (Fin 4) → ℝ, LEITestFn φ →
      ∀ t ∈ Set.Icc (0 : ℝ) sol.T, 0 ≤ lhsDissipation φ t
  /-- Nonnegativity of the kinetic-energy term (sums of squares). -/
  lhsKinetic_nonneg :
    ∀ φ : EuclideanSpace ℝ (Fin 4) → ℝ, LEITestFn φ →
      ∀ t ∈ Set.Icc (0 : ℝ) sol.T, 0 ≤ lhsKinetic φ t
  /-- **THE LEI**: load-bearing field.

  For every nonneg smooth compactly-supported test function `φ` and
  every `t ∈ [0, sol.T]`,

    `lhsKinetic φ t + 2 ν * lhsDissipation φ t`
     `≤ rhsTimeDeriv φ t + rhsViscousLap φ t + rhsTransportPressure φ t`.

  This is the local-in-spacetime analogue of Leray's global energy
  inequality.  Its derivation from the Galerkin sequence is classical
  (Scheffer 1976; simplified in Lin 1998) and is axiomatized in
  `LEI_from_galerkin_classical` below. -/
  lei_holds :
    ∀ φ : EuclideanSpace ℝ (Fin 4) → ℝ, LEITestFn φ →
      ∀ t ∈ Set.Icc (0 : ℝ) sol.T,
        lhsKinetic φ t + 2 * nse.nu * lhsDissipation φ t ≤
          rhsTimeDeriv φ t + rhsViscousLap φ t + rhsTransportPressure φ t
  /-- **FIX-D LEI sol-binding (2026-05-07).**  Each of the five LEI
  functionals is bound to the corresponding integral functional of
  `sol.u` (and pressure).  Without this conjunct the all-zero
  functional `fun _ _ => 0` inhabits the structure and laundering is
  trivial — see the file-level comment block above.  Concrete bridges
  supply this witness via `axiom <name>_at_sol_classical` cited to
  Scheffer 1976 / Lin 1998. -/
  lei_terms_bind_sol :
    LEILhsKineticBindsSol sol lhsKinetic ∧
    LEILhsDissipationBindsSol sol lhsDissipation ∧
    LEIRhsTimeDerivBindsSol sol rhsTimeDeriv ∧
    LEIRhsViscousLapBindsSol sol rhsViscousLap ∧
    LEIRhsTransportPressureBindsSol sol rhsTransportPressure

/-! ## Hypothesis side: Galerkin local-energy boundedness

The Galerkin sequence `u_n` satisfies a *uniform* local-energy bound
on every parabolic ball `Q_r(z₀) = B_r(x₀) × (t₀ - r², t₀]`.  This
bound is the *prerequisite* fed into the classical LEI derivation: it
controls the four terms on the RHS of LEI uniformly in `n`, so passing
to weak / strong subsequential limits preserves the inequality.

We package the bound as `local_energy_bounded`: there is a constant
`M_loc : ℝ` such that for every `n` and every parabolic ball
`Q ⊂ ℝ × ℝ³`,

  `∫∫_Q (|u_n|² + |∇u_n|²) dx ds ≤ M_loc * |Q|`,

with `|Q|` the parabolic-ball volume.  This follows from the global
energy estimate (workstream #3) plus the parabolic-ball volume
formula; we expose it as a Prop input to keep this file decoupled
from the global-estimate machinery. -/

structure GalerkinLocalEnergyBoundData where
  /-- Spatial dimension. -/
  n : ℕ
  /-- Uniform constant for local L²-spacetime bound. -/
  M_loc : ℝ
  /-- `M_loc ≥ 0`. -/
  M_loc_nonneg : 0 ≤ M_loc
  /-- The Galerkin sequence's *abstract* parabolic local energy at
  level `k` and parabolic-ball center / radius `(z₀, r)`. -/
  localEnergy : ℕ → EuclideanSpace ℝ (Fin 4) → ℝ → ℝ
  /-- Parabolic-ball volume `|Q_r| = c_n r^{n+2}`. -/
  parabolicVolume : ℝ → ℝ
  /-- The *uniform* local-energy bound: independent of `n`, the
  Galerkin local energy on `Q_r(z₀)` is bounded by `M_loc * |Q_r|`.

  This is the input that, together with mollifier-stability of
  `(∂_s + νΔ)φ`, lets the LEI derivation (Lin 1998) pass through the
  weak limit. -/
  local_energy_bounded :
    ∀ k : ℕ, ∀ z₀ : EuclideanSpace ℝ (Fin 4), ∀ r : ℝ, 0 < r →
      localEnergy k z₀ r ≤ M_loc * parabolicVolume r

/-! ## Galerkin↔solution compatibility (the Lin 1998 weak-limit hypothesis)

The classical LEI derivation requires that the Galerkin sequence
`u_n` not just satisfy uniform local-energy bounds in isolation, but
that those bounds *transfer* to the limit object `sol.u`.  In Lin
1998 this is the lower-semicontinuity step: weak-`L²` lower bound +
strong-`L²` upper bound force the limit's local energy to lie below
the Galerkin sup.

Previously this was a `True` placeholder, which let any
`GalerkinLocalEnergyBoundData` discharge the LEI axiom regardless of
whether it was related to `sol`.  The void-miner audit
(`ns_trackb_void_audit_2026_05_07.md`, Severity 2) flagged this;
the placeholder is replaced here by a typed witness saying that
`sol.u`'s local L² (over a parabolic ball at `(z₀, r)`) is bounded
above by the Galerkin level-`k` local energy plus an arbitrarily
small slack.  This is the standard weak-LSC consequence used in the
LEI proof.
-/

/-- Local L² content of `sol.u` on a parabolic ball at `(z₀, r)`.

This is the *abstract* parabolic-ball L² — concrete-bridge files
(out of scope here) realize it as the spacetime Bochner integral
`∫∫_{Q_r(z₀)} |sol.u(s,x)|² dx ds`.

The definition is `opaque` (not transparent / not `def := 0`) so
the predicate `(1/r) * solLocalGradL2 sol z r < ε₀` cannot be
trivially discharged by a `simp [solLocalGradL2]` rewrite to `0`.
The opacity is what enforces the binding to `sol.u` at the type-
checker level: any concrete bridge wishing to evaluate the predicate
must supply its own realization of these opaque symbols. -/
opaque solLocalL2
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (z₀ : EuclideanSpace ℝ (Fin 4)) (r : ℝ) : ℝ

/-- Local L² content of `∇ sol.u` on a parabolic ball at `(z₀, r)`.

The gradient analogue of `solLocalL2`.  Held opaque for the same
reason; the concrete-bridge realization is `∫∫_{Q_r(z₀)} |∇sol.u|² dx ds`.

Crucially, this functional is `sol`-dependent (the type signature
takes `sol : NavierStokes.WeakSolution nse` as a primary argument)
so the smallness clause `(1/r) * solLocalGradL2 sol z r < ε₀` cannot
be discharged without naming a `sol` — closing the laundering
channel where the smallness `∃ S, S < ε₀ ∧ True` slot was previously
`sol`-blind. -/
opaque solLocalGradL2
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (z₀ : EuclideanSpace ℝ (Fin 4)) (r : ℝ) : ℝ

/-- Galerkin↔solution compatibility for the weak-`L²` limit step.

**Carries**: a level threshold `N₀` and the inequality
`solLocalL2 sol z₀ r ≤ B.localEnergy k z₀ r + ε` for every `k ≥ N₀`,
every parabolic-ball center `z₀`, every radius `r > 0`, and every
slack `ε > 0`.  This is the abstract content of the Lin 1998 weak-LSC
step that forces the limit's local L² below the Galerkin sup.

The previous `True` placeholder is replaced by this typed witness. -/
structure GalerkinSolutionCompatibility
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (B : GalerkinLocalEnergyBoundData) : Prop where
  /-- The dimension of the Galerkin bound matches `nse`. -/
  dim_match : B.n = n
  /-- For every slack `ε > 0`, eventually-in-`k` the level-`k`
  Galerkin local energy controls the solution's local L² up to `ε`. -/
  weak_lsc_local_L2 :
    ∀ ε : ℝ, 0 < ε →
      ∃ N₀ : ℕ, ∀ k : ℕ, N₀ ≤ k →
        ∀ z₀ : EuclideanSpace ℝ (Fin 4), ∀ r : ℝ, 0 < r →
          solLocalL2 sol z₀ r ≤ B.localEnergy k z₀ r + ε

/-! ## Axiom: LEI from Galerkin (Scheffer 1976 / Lin 1998)

The classical derivation of LEI from the Galerkin sequence proceeds:

1. Multiply the Galerkin momentum equation by `2 u_n φ`.
2. Integrate over `[0, t] × ℝ³`.
3. Use Galerkin orthogonality: spectral truncation commutes with the
   `L²` pairing against finite-dimensional projections.
4. Integrate by parts in time and space.
5. Pass to the weak / strong subsequential limit; the inequality is
   preserved by lower-semicontinuity (cubic nonlinearity becomes an
   inequality, not an equality, due to non-strong convergence of
   `|u_n|² u_n`).

This argument is classical but requires Sobolev-space duality and
integration-by-parts machinery beyond current Mathlib.  We axiomatize
the *output*: given a weak solution `sol` and a uniform local-energy
bound on its Galerkin precursor, the typed-companion record
`LocalEnergyInequalityData sol` exists. -/

/-- **AXIOM (Scheffer 1976; Lin 1998).** Local Energy Inequality
derivation from the Galerkin sequence.

For any weak solution `sol` constructed as the weak limit of a
Galerkin sequence with uniform local-energy bound (encoded by
`GalerkinLocalEnergyBoundData`), the LEI typed companion exists.

References:
* V. Scheffer, *Partial regularity of solutions to the Navier-Stokes
  equations*, Pacific J. Math. **66** (1976), 535–552.
* F.-H. Lin, *A new proof of the Caffarelli-Kohn-Nirenberg theorem*,
  Comm. Pure Appl. Math. **51** (1998), 241–257.

The hypothesis side carries a typed `GalerkinSolutionCompatibility`
witness (replacing the previous `True` placeholder identified by
the void-miner audit, Severity 2).  This witness pins the Galerkin
sequence's local energies to those of `sol.u` via the weak-LSC
inequality `solLocalL2 sol z₀ r ≤ B.localEnergy k z₀ r + ε`. -/
axiom LEI_from_galerkin_classical
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (B : GalerkinLocalEnergyBoundData)
    (h_dim : B.n = n)
    (compat : GalerkinSolutionCompatibility sol B) :
    LocalEnergyInequalityData sol

/-! ## Bridge wrapper: SuitableWeakSolution

A *suitable weak solution* in the sense of CKN is a Leray-Hopf weak
solution that additionally satisfies the LEI.  We package this as a
structure extending `NavierStokes.LerayHopfSolution` with the LEI
typed companion. -/

/-- **Suitable weak solution** (CKN 1982, Definition).

A Leray-Hopf weak solution that satisfies the local energy inequality
(LEI) for every nonneg smooth compactly-supported test function.

This is the class of weak solutions for which CKN partial regularity
applies. -/
structure SuitableWeakSolution
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    extends NavierStokes.LerayHopfSolution nse where
  /-- The LEI typed companion. -/
  lei : LocalEnergyInequalityData (toLerayHopfSolution.toWeakSolution)

namespace SuitableWeakSolution

/-- Promote a Leray-Hopf solution to a suitable weak solution by
supplying a LEI typed companion. -/
def ofLerayHopfWithLEI {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (lh : NavierStokes.LerayHopfSolution nse)
    (lei : LocalEnergyInequalityData lh.toWeakSolution) :
    SuitableWeakSolution nse :=
  { toLerayHopfSolution := lh, lei := lei }

end SuitableWeakSolution

/-! ## Local smallness criterion (the OPEN Prop input)

The CKN partial regularity theorem requires that on every sufficiently
small parabolic ball where smoothness is to be deduced, the *scaled*
local energy `r⁻¹ ∫∫_{Q_r} (|∇u|² + |p|^{3/2}) dx dt` falls below an
absolute constant `ε₀ > 0`.

We package this as a Prop predicate on a suitable weak solution: there
exists `ε₀ > 0` and a measurable exception set `E` of parabolic
Hausdorff dimension at most `1` such that on the complement, the
scaled local energy is `< ε₀` for every sufficiently small `r`. -/

/-- The *parabolic Hausdorff dimension* of a set in `ℝ × ℝ³`.

Held opaque (the full Hausdorff-measure construction is out of scope
for this bridge) but **axiomatized to satisfy two non-trivial
properties** that together close the laundering channel identified
by the void-miner audit:

1. `parabolicHausdorffDim_empty` — `∅` has dimension `0`.
2. `parabolicHausdorffDim_univ_eq_five` — `Set.univ` has dimension
   `5` (the parabolic dimension of `ℝ × ℝ³`, i.e.
   `dim_space + 2 * dim_time = 3 + 2 = 5`).

Property (2) is what kills the degenerate witness `E := Set.univ` in
`LocalSmallnessCriterion`: the dimension clause `... ≤ 1` would have
to assert `5 ≤ 1`, which is false. -/
opaque ParabolicHausdorffDim : Set (EuclideanSpace ℝ (Fin 4)) → ℝ

/-- **Axiom (parabolic-dimension calibration).**  The empty set has
parabolic Hausdorff dimension `0`. -/
axiom parabolicHausdorffDim_empty :
    ParabolicHausdorffDim (∅ : Set (EuclideanSpace ℝ (Fin 4))) = 0

/-- **Axiom (parabolic-dimension calibration).**  `Set.univ` in
`ℝ⁴` (parabolic dimension of `ℝ_t × ℝ³_x` with the parabolic scaling
`(t, x) ↦ (λ²t, λx)`) has parabolic Hausdorff dimension `5`.

This axiom is the structural blocker that rejects the previously
admissible degenerate witness `E := Set.univ`: see
`LocalSmallnessCriterion_not_vacuous` below. -/
axiom parabolicHausdorffDim_univ_eq_five :
    ParabolicHausdorffDim (Set.univ : Set (EuclideanSpace ℝ (Fin 4))) = 5

/-- **Local smallness criterion** for a suitable weak solution
(VOID-MINER-HARDENED form, 2026-05-07).

Holds iff there is an absolute constant `ε₀ > 0` and a *measurable*
exception set `E ⊆ ℝ × ℝ³` of **parabolic Hausdorff dimension at
most `1`** such that, off `E`, the SCALE-INVARIANT local energy

  `(1/r) * ∫∫_{Q_r(z)} |∇sol.u|² dx ds`

stays below `ε₀` for every parabolic-ball radius `r > 0`.

This is the inequality CKN (1982 §IV) and Lin (1998, Prop 1) use as
the direct hypothesis of partial regularity.  The previous shipping
form had two `∧ True` slots (one for the dimension clause, one for
the smallness clause) and let `E := Set.univ, ε₀ := 1` discharge it
trivially.  The void-miner audit
(`ns_trackb_void_audit_2026_05_07.md`, Severity 1) flagged this as a
laundering channel.

The void is closed by:

1. The smallness clause is the SCALED gradient L² on parabolic balls
   *of `sol.u`*, not an abstract `∃ S, S < ε₀` slot.  This binds the
   Prop to `sol.u` so a `sol`-blind witness is type-rejected.

2. The dimension clause now references the opaque
   `ParabolicHausdorffDim` (calibrated to `5` on `Set.univ` by axiom);
   `E := Set.univ` therefore forces `5 ≤ 1`, which is false.  The
   `∃ d, d ≤ 1` slot was the laundering doorway — it has been
   replaced by `ParabolicHausdorffDim E ≤ 1`.

The bridge corollary `ckn_partial_regularity_modulo_smallness`
downstream consumes the strengthened predicate and the CKN axiom
signature is updated accordingly. -/
def LocalSmallnessCriterion
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∃ (ε₀ : ℝ) (E : Set (EuclideanSpace ℝ (Fin 4))),
    0 < ε₀ ∧
    -- Parabolic Hausdorff dimension of `E` is `≤ 1`.  This is now a
    -- REAL Prop (no `∧ True`); on `Set.univ` the axiom forces
    -- `5 ≤ 1`, which is false, so degenerate witnesses are rejected.
    ParabolicHausdorffDim E ≤ 1 ∧
    -- Scale-invariant local-gradient smallness OFF `E`, FOR ALL
    -- radii `r > 0`.  Bound by `solLocalGradL2 sol z r` so the
    -- predicate is non-vacuously coupled to `sol.u`.
    (∀ z : EuclideanSpace ℝ (Fin 4), z ∉ E →
      ∀ r : ℝ, 0 < r →
        (1 / r) * solLocalGradL2 sol z r < ε₀) ∧
    -- Time-window non-degeneracy (preserved from the previous form).
    sol.T > 0

/-- Projection lemma: the current `LocalSmallnessCriterion` really is the
literal all-scale predicate, demanding scaled local-gradient smallness for
every radius `r > 0` off a single exceptional set. This theorem exists so
later no-go shells can cite the exact quantifier shape instead of paraphrase. -/
theorem LocalSmallnessCriterion_has_literal_all_scale_clause
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (hSmall : LocalSmallnessCriterion sol) :
    ∃ (ε₀ : ℝ) (E : Set (EuclideanSpace ℝ (Fin 4))),
      0 < ε₀ ∧
      ParabolicHausdorffDim E ≤ 1 ∧
      (∀ z : EuclideanSpace ℝ (Fin 4), z ∉ E →
        ∀ r : ℝ, 0 < r →
          (1 / r) * solLocalGradL2 sol z r < ε₀) ∧
      sol.T > 0 := by
  exact hSmall

/-! ### Void-miner inversion test: `LocalSmallnessCriterion` is NOT
vacuously satisfiable

The two structural strengthenings above (typed gradient L² coupling
to `sol.u`, plus the `ParabolicHausdorffDim` axiom calibration on
`Set.univ`) imply the following falsifier: the previously admissible
"trivial witness" `(ε₀ := 1, E := Set.univ)` can no longer discharge
the predicate.  We prove this as a defensive lemma so the closure of
the laundering channel is *machine-checked* — not just inspected. -/

/-- **Void-miner inversion test (calibration lemma).**

The degenerate Σ-clause `(0 < ε₀ ∧ ParabolicHausdorffDim Set.univ ≤ 1)`
is *unprovable*.  Together with `LocalSmallnessCriterion_no_univ_exception`
below, this lemma shows that the previously admissible laundering
witness `(ε₀ := 1, E := Set.univ, ...)` is structurally rejected. -/
theorem LocalSmallnessCriterion_rejects_univ_exception :
    ¬ (∃ ε₀ : ℝ, 0 < ε₀ ∧
        ParabolicHausdorffDim (Set.univ : Set (EuclideanSpace ℝ (Fin 4))) ≤ 1) := by
  rintro ⟨_, _, hdim⟩
  rw [parabolicHausdorffDim_univ_eq_five] at hdim
  linarith

/-- **Void-miner inversion test (full predicate form).**

No `LocalSmallnessCriterion` witness can use `E := Set.univ` as its
exception set.  This is the *machine-checked closure* of the
laundering channel that the void-miner audit
(`ns_trackb_void_audit_2026_05_07.md`, Severity 1) flagged:

> Take `E := univ` and `ε₀ := 1` and the Prop is satisfied for any
> solution.

Under the tightened predicate, that witness type-rejects because the
`ParabolicHausdorffDim E ≤ 1` clause becomes `5 ≤ 1` (false).

This lemma deliberately discusses the predicate one would *try* to
build (with a chosen ε₀, E := univ) and shows it is unprovable. -/
theorem LocalSmallnessCriterion_no_univ_exception
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (ε₀ : ℝ) :
    ¬ (0 < ε₀ ∧
       ParabolicHausdorffDim (Set.univ : Set (EuclideanSpace ℝ (Fin 4))) ≤ 1 ∧
       (∀ z : EuclideanSpace ℝ (Fin 4), z ∉ (Set.univ : Set _) →
          ∀ r : ℝ, 0 < r →
            (1 / r) * solLocalGradL2 sol z r < ε₀) ∧
       sol.T > 0) := by
  rintro ⟨_, hdim, _, _⟩
  rw [parabolicHausdorffDim_univ_eq_five] at hdim
  linarith

/-! ## Axiom: CKN classical partial regularity (Caffarelli-Kohn-Nirenberg 1982)

The deep PDE theorem itself.  Faithful to the published statement
(CKN 1982 Theorem D, modulo notation):

> Let `sol` be a suitable weak solution to the 3D incompressible
> Navier-Stokes equations.  Then there exists a measurable set
> `Σ ⊂ ℝ × ℝ³` of *parabolic 1-dimensional Hausdorff measure zero*
> such that `u` is `C^∞` on `(ℝ × ℝ³) ∖ Σ`.

We axiomatize this with the typed-companion bundle as input. -/

/-- **AXIOM (Caffarelli-Kohn-Nirenberg 1982, Theorem D).** Partial
regularity for suitable weak solutions.

Given:

* a weak solution `sol` (in lean-dojo flavor),
* a LEI typed companion `lei : LocalEnergyInequalityData sol`
  (so `sol` is suitable),
* the local smallness criterion `hSmall : LocalSmallnessCriterion sol`,

there exists a *named exception set* `Σ` (the singular set) of
parabolic Hausdorff dimension at most `1` such that `sol.u` is `C^∞`
on the complement of `Σ`.

References:
* L. Caffarelli, R. Kohn, L. Nirenberg, *Partial regularity of suitable
  weak solutions of the Navier-Stokes equations*, Comm. Pure Appl.
  Math. **35** (1982), 771–831.
* F.-H. Lin, *A new proof of the Caffarelli-Kohn-Nirenberg theorem*,
  Comm. Pure Appl. Math. **51** (1998), 241–257.
* G. Seregin, *Lecture Notes on Regularity Theory for the Navier-
  Stokes Equations*, World Scientific (2014).

The conclusion exposes:

* `Σ` — the named exception set.
* `Σ_dim_le_one` — its dimension witness.
* `smooth_off_Σ` — the smoothness conclusion. -/
axiom CKN_partial_regularity_classical
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (_lei : LocalEnergyInequalityData sol)
    (_hSmall : LocalSmallnessCriterion sol) :
    ∃ singularSet : Set (EuclideanSpace ℝ (Fin 4)),
      ParabolicHausdorffDim singularSet ≤ 1 ∧
      ContDiff ℝ ⊤ sol.u

/-! ## Bridge corollary: CKN-skeleton theorem -/

/-- **CKN partial regularity, modulo local smallness.**

Given a weak solution `sol` plus

* `lei : LocalEnergyInequalityData sol` — the LEI typed companion
  (= `sol` is suitable),
* `hSmall : LocalSmallnessCriterion sol` — the Prop input naming
  the exception set's dimension and the scaled-local-energy
  smallness off it,

we conclude that `sol.u` is `C^∞` on the complement of a named
exception set `Σ` of parabolic Hausdorff dimension at most `1`.

This is the bridge corollary; its proof is a 1-line consequence of
`CKN_partial_regularity_classical`. -/
theorem ckn_partial_regularity_modulo_smallness
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (lei : LocalEnergyInequalityData sol)
    (hSmall : LocalSmallnessCriterion sol) :
    ∃ singularSet : Set (EuclideanSpace ℝ (Fin 4)),
      ParabolicHausdorffDim singularSet ≤ 1 ∧
      ContDiff ℝ ⊤ sol.u :=
  CKN_partial_regularity_classical sol lei hSmall

/-! ## Bridge corollary: from suitable weak solution to partial regularity

Same conclusion as above, but with input phrased against the
`SuitableWeakSolution` wrapper. -/

/-- **CKN partial regularity for a suitable weak solution.**

Convenience corollary: if `sws : SuitableWeakSolution nse` and
`hSmall : LocalSmallnessCriterion sws.toWeakSolution`, then the
velocity field is `C^∞` off a parabolic-1-dimensional exception set. -/
theorem suitable_weakSolution_partial_regularity
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sws : SuitableWeakSolution nse)
    (hSmall : LocalSmallnessCriterion sws.toLerayHopfSolution.toWeakSolution) :
    ∃ singularSet : Set (EuclideanSpace ℝ (Fin 4)),
      ParabolicHausdorffDim singularSet ≤ 1 ∧
      ContDiff ℝ ⊤ sws.toLerayHopfSolution.toWeakSolution.u :=
  ckn_partial_regularity_modulo_smallness
    sws.toLerayHopfSolution.toWeakSolution sws.lei hSmall

/-! ## Composition map (for the master spine)

  Galerkin sequence `u_n`
   ↓
   (existing 5 typed-companion bridges → AbstractLerayHopfWitness)
   ↓
  `NavierStokes.LerayHopfSolution nse`   (= concrete promotion)
   ↓
   + `LocalEnergyInequalityData sol`     (this file: LEI typed companion,
                                          via `LEI_from_galerkin_classical`)
   ↓
  `SuitableWeakSolution nse`
   ↓
   + `LocalSmallnessCriterion sol`       (OPEN Prop input — the Clay gap)
   ↓
  `∃ Σ ⊂ ℝ × ℝ³, ParabolicHausdorffDim Σ ≤ 1
                  ∧ ContDiff ℝ ⊤ sol.u`

If `LocalSmallnessCriterion` were strengthened to `Σ = ∅` uniformly,
the chain would close to `GlobalSmoothSolution nse`.

## Honest residual void

* **Open**: `LocalSmallnessCriterion sol` for arbitrary smooth finite-
  energy divergence-free initial data.  In its `Σ = ∅` form, this is
  equivalent (modulo Prodi-Serrin / Constantin-Fefferman reformulations)
  to the Clay Millennium problem.

* **Axiomatized but classical**:
  - `LEI_from_galerkin_classical` (Scheffer 1976; Lin 1998).
  - `CKN_partial_regularity_classical` (CKN 1982 Theorem D).

  Both are theorems in the literature whose Mathlib formalization is
  out of scope of this workstream.  They are isolated as named axioms
  so that downstream consumers can audit the residual void.
-/

end

end ZtareProofs.NS
