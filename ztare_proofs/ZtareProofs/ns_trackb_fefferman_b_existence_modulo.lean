/-
# NS Track B — Fefferman B *weak-form* conditional discharge (`𝕋³`)

This file ASSEMBLES the existing workstream-O `lerayHopf_existence_oneshot`
construction and the workstream-S periodicity-preservation bridge
(`lerayHopf_periodicity_from_concrete_galerkin`) into a single
**conditional theorem** for the periodic Fefferman-B initial-data
hypotheses on `𝕋³`.

## What this file ships

A theorem `feffermanB_weakform_conditional` of the shape

```
∀ ν > 0, ∀ u₀ smooth & periodic & div-free, ∀ T > 0,
  ∀ E (energy-clause typed-companion input),
  ∀ M (momentum-clause typed-companion input — carrier of the
        Aubin-Lions Prop hypothesis),
  ∀ (per-n periodicity + pointwise-limit inputs for the Galerkin
     sequence built from `nseR3`),
    ∃ sol : NavierStokes.LerayHopfSolution (nseR3 ν ν_pos u₀ hdiv 0),
    ∃ pInf : PressureField 3,
      FeffermanCond10
        (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv 0) T T_pos).uInf
        pInf
```

i.e. a Leray–Hopf weak solution for the periodic Fefferman-B initial
data **plus** a witness that the Galerkin-limit velocity field is
spatially periodic at every nonneg time `t` (via `FeffermanCond10`).

## What this file is NOT

This is **NOT** a discharge of Fefferman B.  Fefferman B
(`MillenniumNS_BoundedDomain.FeffermanB`) requires a `GlobalSmoothSolution`
for `nseR3 ν ν_pos u₀ hdiv 0`, which carries a `ContDiff ℝ ⊤`
smoothness obligation on the velocity, the pressure, AND
finite-time-of-existence-equals-∞ ("global"), together with
`FeffermanCond10` periodicity on the resulting `(sol.u, sol.p)`.

Our output is **strictly weaker**: a `NavierStokes.LerayHopfSolution`
which only carries the five Leray–Hopf clauses

* `weak_initial_condition`,
* `velocity_regularity`  (L²/H¹ time-uniform integrability),
* `weak_incompressible`  (distributional `div u = 0`),
* `weak_momentum_equation` (distributional momentum identity),
* `energy_inequality`     (Hopf inequality at the limit).

Smoothness, uniqueness, and global existence in the strong (Sobolev/
classical) sense remain open.  This file therefore documents the
**weak-form Fefferman-B** that the typed-companion architecture
produces conditionally.

## Smoothness / regularity gap (explicit)

| Clay periodic-domain field    | Fefferman B requires      | This file produces             | Gap                                     |
|-------------------------------|---------------------------|--------------------------------|------------------------------------------|
| smoothness of `(u, p)`        | `ContDiff ℝ ⊤`            | L²-time / H¹-space (via Hopf)  | classical-regularity step                |
| time of existence             | `[0, ∞)` (global)         | `[0, T]` for any chosen `T`    | extension to ∞ + apriori bound           |
| momentum identity             | classical pointwise       | distributional weak form       | weak→strong selection / partial regularity |
| `FeffermanCond10` (periodic)  | on `(sol.u, sol.p)`       | on `(uInf, pInf)`              | identification of `sol.u` with `uInf`    |

The fourth row is the most subtle: the `abstractWitness_to_concreteLerayHopf`
axiom in workstream O is opaque about how the produced
`LerayHopfSolution.u` relates to the Galerkin-limit `G.uInf`.  We
therefore PRODUCE BOTH (the Leray–Hopf solution and a `FeffermanCond10`
witness for the Galerkin limit) and document the unproven identification
as part of the gap.

## Honesty discipline

* This file ships **zero `sorry`s** and **zero new `axiom`s**.
* It re-uses the seven workstream-O Galerkin axioms (transitively, via
  `lerayHopf_existence_oneshot` → `buildClassicalGalerkinConstruction`).
* It re-uses the workstream-S periodicity-preservation theorem
  `lerayHopf_periodicity_from_concrete_galerkin`.
* The Aubin–Lions strong-convergence Prop input is **carried as a
  hypothesis** inside `MomentumClauseInput.momCompanion`; it is NOT
  axiomatized here.
* All other PDE machinery (the four §3 typed-companion adapters, the
  master spine, the `abstractWitness_to_concreteLerayHopf` axiom) lives
  unchanged in workstream O.

## Audit command

```
cd /ztare_proofs &&
  lake env lean ZtareProofs/ns_trackb_fefferman_b_existence_modulo.lean
```
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.lean_dojo_ns_torus.MillenniumRDomain
import ZtareProofs.lean_dojo_ns_torus.MillenniumBoundedDomain
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic
import ZtareProofs.ns_trackb_lean_dojo_concrete_bridge_torus

namespace ZtareProofs.NS.FeffermanBWeakForm

noncomputable section

open MeasureTheory Filter Topology
open NavierStokes
open MillenniumNSRDomain
open MillenniumNS_BoundedDomain
open ZtareProofs.NS.GalerkinAxiomatic
open ZtareProofs.NS.ConcreteBridge.Torus

/-! ## §1.  Periodicity inputs over the Galerkin construction

The workstream-S theorem
`ZtareProofs.NS.ConcreteBridge.Torus.lerayHopf_periodicity_from_concrete_galerkin`
discharges `FeffermanCond10` for the limit `(uInf, pInf)` from per-`n`
periodicity of the Galerkin sequence + pointwise convergence.

We package its hypotheses (over the *built* Galerkin construction
`buildClassicalGalerkinConstruction nse T T_pos`) into a single
structure, `PeriodicityClauseInput`.

This isolates "periodicity is preserved by the spectral truncation"
(which is a classical Galerkin output for periodic test bases — the
discrete Fourier spectral basis on `𝕋³` is itself periodic, so each
truncation `u_n` is periodic by construction) and "the pointwise limit
exists at every shifted location" (a strengthening of the weak-L²
extraction).

These are CLASSICAL inputs analogous in nature to §1.1–§1.6 of
workstream O, but specific to the periodic-domain construction.  We do
NOT axiomatize them here; the caller supplies them. -/

/-- Periodicity + pointwise-limit hypotheses on the Galerkin
construction associated to a concrete `nse` and time horizon `T`.

Carries:

* per-`n` spatial periodicity of the velocity sequence at every
  nonneg time;
* per-`n` spatial periodicity of an externally supplied pressure
  sequence at every nonneg time;
* pointwise convergence of the velocity sequence to `G.uInf` at every
  shifted location and every nonneg time;
* pointwise convergence of the pressure sequence to `pInf` at every
  shifted location and every nonneg time. -/
structure PeriodicityClauseInput
    (nse : NavierStokesEquations 3) (T : ℝ) (T_pos : 0 < T) where
  /-- Externally supplied pressure sequence (the Helmholtz–Leray
  decomposition of the Galerkin truncations; classical). -/
  pSeq : ℕ → PressureField 3
  /-- Externally supplied limit pressure (the Helmholtz–Leray
  decomposition of the limit; classical). -/
  pInf : PressureField 3
  /-- Per-`n` spatial periodicity of the Galerkin velocity sequence at
  every nonneg time. -/
  per_n_velocity_periodic :
    ∀ (n : ℕ) (t : ℝ), 0 ≤ t →
      IsPeriodic
        (fun x : Euc ℝ 3 =>
          (buildClassicalGalerkinConstruction nse T T_pos).galerkinSeq
            n (pairToEuc t x))
  /-- Per-`n` spatial periodicity of the pressure sequence. -/
  per_n_pressure_periodic :
    ∀ (n : ℕ) (t : ℝ), 0 ≤ t →
      IsPeriodic (fun x : Euc ℝ 3 => (pSeq n) (pairToEuc t x))
  /-- Pointwise convergence of the velocity sequence to `G.uInf`. -/
  velocity_pointwise :
    ∀ (t : ℝ), 0 ≤ t → ∀ y : Euc ℝ 3,
      Tendsto
        (fun n =>
          (buildClassicalGalerkinConstruction nse T T_pos).galerkinSeq
            n (pairToEuc t y))
        atTop
        (nhds
          ((buildClassicalGalerkinConstruction nse T T_pos).uInf
            (pairToEuc t y)))
  /-- Pointwise convergence of the pressure sequence to `pInf`. -/
  pressure_pointwise :
    ∀ (t : ℝ), 0 ≤ t → ∀ y : Euc ℝ 3,
      Tendsto
        (fun n => (pSeq n) (pairToEuc t y))
        atTop
        (nhds (pInf (pairToEuc t y)))

/-! ## §2.  Conditional Fefferman-B *weak-form* discharge

The climactic theorem of this file.  Given:

* the periodic Fefferman-B initial-data hypotheses (smooth, periodic,
  divergence-free),
* a finite time horizon `T > 0`,
* the workstream-O typed-companion energy + momentum inputs `E`, `M`
  (the latter carrying the Aubin–Lions residual void in
  `M.momCompanion … .nonlinear_pairing_conv`),
* the §1 periodicity + pointwise-limit inputs `P`,

we produce:

* a concrete `NavierStokes.LerayHopfSolution (nseR3 ν ν_pos u₀ hdiv 0)`
  via `lerayHopf_existence_oneshot`,
* a `FeffermanCond10` witness on the *Galerkin limit* `(G.uInf, P.pInf)`
  via `lerayHopf_periodicity_from_concrete_galerkin`.

The Fefferman-B periodicity conclusion `FeffermanCond10 sol.u sol.p`
on the Leray–Hopf solution is NOT directly produced — see the gap row
"identification of `sol.u` with `uInf`" in the file header. -/

/-- **Fefferman-B weak-form conditional discharge.**

Given the periodic Fefferman-B initial-data hypotheses, a time horizon,
the workstream-O typed-companion inputs (`E`, `M`, `Pc`), and the
workstream-S periodicity inputs (`P`), produce a Leray–Hopf weak
solution and a Galerkin-limit periodicity witness.

Note: produces `Type`-valued data (a `LerayHopfSolution` structure);
hence `noncomputable def`, not `theorem`.  The result is a `PProd`
packaging the Leray–Hopf weak solution and the `FeffermanCond10`
periodicity Prop on the Galerkin limit.

The `Pc : ConcretePromotionInput` argument carries the five concrete
clause-bridge inputs (B/C/D/E + Helmholtz–Leray pressure) consumed by
workstream O's `abstractWitness_to_concreteLerayHopf` definition; it
also provides the pressure sequence `pSeq` and limit `pInf` used by the
periodicity bridge below.

This is **strictly weaker than Fefferman B**: see the smoothness /
regularity gap table in the file header. -/
noncomputable def feffermanB_weakform_conditional
    (ν : ℝ) (ν_pos : ν > 0)
    (u₀ : Euc ℝ 3 → Euc ℝ 3)
    (_u₀_smooth : ContDiff ℝ ⊤ u₀)
    (_u₀_periodic : FeffermanCond8_initial u₀)
    (hdiv : DivergenceFreeInitial u₀)
    (T : ℝ) (T_pos : 0 < T)
    (E : EnergyClauseInput
          (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos))
    (M : MomentumClauseInput
          (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos))
    (Pc : ConcretePromotionInput
          (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T
          (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos))
    (P : PeriodicityClauseInput
          (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos) :
    PProd
      (NavierStokes.LerayHopfSolution
        (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)))
      (FeffermanCond10
        (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos).uInf
        P.pInf) :=
  ⟨ -- Leray–Hopf weak solution from workstream O.
    lerayHopf_existence_oneshot
      (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos E M Pc,
    -- Galerkin-limit periodicity from workstream S.
    lerayHopf_periodicity_from_concrete_galerkin
      (fun n =>
        (buildClassicalGalerkinConstruction
          (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos).galerkinSeq n)
      P.pSeq
      (buildClassicalGalerkinConstruction
        (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos).uInf
      P.pInf
      P.per_n_velocity_periodic
      P.per_n_pressure_periodic
      P.velocity_pointwise
      P.pressure_pointwise ⟩

/-! ## §3.  Component re-exports

For downstream consumers that want only the Leray–Hopf weak solution
(without the periodicity witness) or only the periodicity witness
(without the Leray–Hopf weak solution). -/

/-- Just the Leray–Hopf weak solution, for the Fefferman-B initial data. -/
noncomputable def feffermanB_weakform_lerayHopf
    (ν : ℝ) (ν_pos : ν > 0)
    (u₀ : Euc ℝ 3 → Euc ℝ 3)
    (_u₀_smooth : ContDiff ℝ ⊤ u₀)
    (_u₀_periodic : FeffermanCond8_initial u₀)
    (hdiv : DivergenceFreeInitial u₀)
    (T : ℝ) (T_pos : 0 < T)
    (E : EnergyClauseInput
          (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos))
    (M : MomentumClauseInput
          (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos))
    (Pc : ConcretePromotionInput
          (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T
          (buildClassicalGalerkinConstruction
            (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos)) :
    NavierStokes.LerayHopfSolution
      (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) :=
  lerayHopf_existence_oneshot
    (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos E M Pc

/-- Just the Galerkin-limit periodicity, for the Fefferman-B initial
data.  Uses the workstream-S bridge directly. -/
theorem feffermanB_weakform_galerkinLimit_periodicity
    (ν : ℝ) (ν_pos : ν > 0)
    (u₀ : Euc ℝ 3 → Euc ℝ 3)
    (hdiv : DivergenceFreeInitial u₀)
    (T : ℝ) (T_pos : 0 < T)
    (P : PeriodicityClauseInput
          (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos) :
    FeffermanCond10
      (buildClassicalGalerkinConstruction
        (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos).uInf
      P.pInf :=
  lerayHopf_periodicity_from_concrete_galerkin
    (fun n =>
      (buildClassicalGalerkinConstruction
        (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos).galerkinSeq n)
    P.pSeq
    (buildClassicalGalerkinConstruction
      (nseR3 ν ν_pos u₀ hdiv (fun _ => 0)) T T_pos).uInf
    P.pInf
    P.per_n_velocity_periodic
    P.per_n_pressure_periodic
    P.velocity_pointwise
    P.pressure_pointwise

/-! ## §4.  Sorry / axiom inventory

This file ships:

* **Zero `sorry`s.**
* **Zero new `axiom`s.**
* **One new structure** (`PeriodicityClauseInput`) packaging the
  workstream-S bridge's hypotheses over the workstream-O Galerkin
  construction.
* **Three theorems** (`feffermanB_weakform_conditional`,
  `feffermanB_weakform_lerayHopf`,
  `feffermanB_weakform_galerkinLimit_periodicity`).

The classical-theory inputs transitively imported are exactly the
**seven workstream-O axioms** (see §10 of
`ns_trackb_galerkin_existence_axiomatic.lean`) plus the residual void
`NonlinearPairingStrongConv` carried inside `M.momCompanion`.

## Relationship to Fefferman B

This file does **NOT** discharge Fefferman B.  It produces the
WEAK-FORM analogue:

* Fefferman B asks for `GlobalSmoothSolution` (i.e. `ContDiff ℝ ⊤`,
  global-in-time, classical-strength) with `FeffermanCond10`.
* This file produces `NavierStokes.LerayHopfSolution` (weak,
  finite-`T`, distributional momentum identity, energy inequality)
  with `FeffermanCond10` on the *Galerkin limit*.

The smoothness gap is the open Clay problem.  See the file header for
the four-row gap table. -/

end

end ZtareProofs.NS.FeffermanBWeakForm
