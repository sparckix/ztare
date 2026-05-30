/-
# NS Track B — Canonical `TraceBindsSol` predicate family (SUBSTRATE-FIX)

## Why this file exists (STATEMENT-AUDIT 2026-05-07)

Three typed-companion conjectures in CREATE-1/4/6 carried `ℝ → ℝ`
abstract trace fields decoupled from the underlying weak solution
`sol`:

* `Lyapunov3DInequalityHolds sol a b c ν T` — the existential body
  introduces fresh `D, W, κ, E, H, Z : ℝ → ℝ` whose link to `sol.u`
  is purely textual.
* `HelicityVortexCrossData sol` — fields `helicity, vortex_stretching,
  energy : ℝ → ℝ` with no constraint binding them to `sol`.
* `LambCriterionData sol` — field `lamb_critical_L3_t : ℝ → ℝ` with
  no constraint binding it to `‖(∇×u(t,·))×u(t,·)‖_{L³_x}`.

The all-zero trace `(fun _ => 0)` inhabits each of those structures
for *any* weak solution.  Consumers like
`cross_identity_conditional_propagation` and
`lyapunov_3d_classical_propagation` then derive `ContDiff sol.u`
(`VasseurStretchingFinite sol`, etc.) for arbitrary `sol`, including
hypothetical Type-II blow-up scenarios.  This is unsound.

## The fix (this file)

We expose a canonical *opaque* family of predicates
`*TraceBindsSol sol f`, one for each scalar diagnostic, asserting that
the abstract trace `f : ℝ → ℝ` actually equals the corresponding
integral functional of `sol.u`.  The predicates are `opaque`, so the
all-zero trace cannot inhabit them definitionally; supplying a witness
requires an additional axiom that names the diagnostic identity.

Downstream files thread these predicates as additional conjuncts /
struct fields, turning the previously vacuous existential bodies into
honest open conjectures that must be supplied alongside the trace.

## What this file ships

* `EnstrophyTraceBindsSol sol Z` — `Z(t) = ½‖ω(t,·)‖_{L²}²`.
* `VortexStretchingTraceBindsSol sol W` — `W(t) = ⟨ω·∇u, ω⟩(t,·)`.
* `DissipationTraceBindsSol sol D` — `D(t) = ‖∇²u(t,·)‖_{L²}²`.
* `EnergyTraceBindsSol sol E` — `E(t) = ½‖u(t,·)‖_{L²}²`.
* `HelicityTraceBindsSol sol H` — `H(t) = ⟨u, ω⟩(t,·)`.
* `LambNormTraceBindsSol sol L` — `L(t) = ‖(∇×u)×u‖_{L³_x}(t)`.
* `KappaTraceBindsSol sol κ` — `κ(t) = ⟨ω, curl ω⟩(t,·)`.

All seven are `opaque : Prop`, so they cannot be inhabited by zero
traces.  Honest analytical witnesses that arise downstream (e.g. on
Beltrami flows, axisymmetric no-swirl, helically-decimated NS) supply
them via *named* axioms cited to the published diagnostic identity.

## Sound-discharge protocol (for downstream files)

When a lift theorem supplies a trace alongside an inequality, it MUST
also supply the binding via an additional axiom of the shape:

```
axiom <class>_<diagnostic>_trace_binds_sol :
    <class-membership> sol → <DiagnosticTraceBindsSol> sol <trace>
```

Such axioms are sound provided the `<trace>` is the explicit
diagnostic computed from `sol.u` (e.g. on axisymmetric no-swirl,
`W ≡ 0` is a computed identity not an arbitrary choice).  The opaque
`*TraceBindsSol` predicates make this discipline visible at the type
level.

ZERO `sorry`s.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The canonical opaque TraceBindsSol family -/

/-- **Enstrophy-trace binding.**

`EnstrophyTraceBindsSol sol Z` asserts that the abstract trace
`Z : ℝ → ℝ` equals the enstrophy of `sol.u` slice-by-slice:

  `∀ t ∈ [0, sol.T], Z t = ½ · ∫ |ω(t,·)|² dx`

where `ω = curl sol.u`.  Opaque so that arbitrary traces (in
particular the all-zero trace) cannot inhabit it. -/
opaque EnstrophyTraceBindsSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_Z : ℝ → ℝ) : Prop

/-- **Vortex-stretching trace binding.**

`VortexStretchingTraceBindsSol sol W` asserts

  `∀ t ∈ [0, sol.T], W t = ∫ ω · (ω · ∇) u dx`

where `u = sol.u` and `ω = curl u`.  Opaque. -/
opaque VortexStretchingTraceBindsSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_W : ℝ → ℝ) : Prop

/-- **Palinstrophy / dissipation trace binding.**

`DissipationTraceBindsSol sol D` asserts

  `∀ t ∈ [0, sol.T], D t = ∫ |∇ω(t,·)|² dx`.

Opaque. -/
opaque DissipationTraceBindsSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_D : ℝ → ℝ) : Prop

/-- **Kinetic-energy trace binding.**

`EnergyTraceBindsSol sol E` asserts

  `∀ t ∈ [0, sol.T], E t = ½ · ∫ |u(t,·)|² dx`.

Opaque. -/
opaque EnergyTraceBindsSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_E : ℝ → ℝ) : Prop

/-- **Total-helicity trace binding.**

`HelicityTraceBindsSol sol H` asserts

  `∀ t ∈ [0, sol.T], H t = ∫ u(t,·) · ω(t,·) dx`.

Opaque. -/
opaque HelicityTraceBindsSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_H : ℝ → ℝ) : Prop

/-- **Helicity-curl trace binding** (`κ := ∫ ω · curl ω`).

`KappaTraceBindsSol sol κ` asserts the diagnostic `κ` equals the
classical Moffatt-style integral.  Opaque. -/
opaque KappaTraceBindsSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse)
    (_κ : ℝ → ℝ) : Prop

/-- **Lamb-form L³ norm trace binding.**

`LambNormTraceBindsSol sol L` asserts that the abstract trace
`L : ℝ → ℝ` equals the Lamb-form Sobolev-critical norm of `sol.u`:

  `∀ t ∈ [0, sol.T], L t = ‖(∇×sol.u(t,·)) × sol.u(t,·)‖_{L³(ℝⁿ)}`.

Opaque so the all-zero trace cannot inhabit it. -/
opaque LambNormTraceBindsSol
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse)
    (_L : ℝ → ℝ) : Prop

/-! ## §2.  Bundled binding for the 3-D Lyapunov inequality

The `Lyapunov3DInequalityHolds` predicate carries six abstract traces
`D, W, κ, E, H, Z`.  We bundle their bindings into a single Prop so
the inequality definition has a clean conjunct shape. -/

/-- **Bundled binding for Lyapunov-3D traces.**

Asserts simultaneously that all six abstract traces of the Lyapunov
3-D inequality (`D, W, κ, E, H, Z`) are bound to the corresponding
diagnostic functionals of `sol.u`.  This is the conjunct the
substrate-fix adds to `Lyapunov3DInequalityHolds`. -/
def Lyapunov3DTracesBindSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D W κ E H Z : ℝ → ℝ) : Prop :=
  DissipationTraceBindsSol sol D ∧
  VortexStretchingTraceBindsSol sol W ∧
  KappaTraceBindsSol sol κ ∧
  EnergyTraceBindsSol sol E ∧
  HelicityTraceBindsSol sol H ∧
  EnstrophyTraceBindsSol sol Z

/-- **Bundled binding for the helicity ↔ vortex-stretching cross
identity.**

Asserts the three cross-identity traces (`H`, `V`, `E`) are bound to
the corresponding integral functionals of `sol.u`. -/
def HelicityVortexCrossTracesBindSol
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (helicity vortex_stretching energy : ℝ → ℝ) : Prop :=
  HelicityTraceBindsSol sol helicity ∧
  VortexStretchingTraceBindsSol sol vortex_stretching ∧
  EnergyTraceBindsSol sol energy

end

end ZtareProofs.NS
