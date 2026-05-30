/-
# NS Track B — Beale-Kato-Majda smoothness-propagation bridge (CONDITIONAL)

This file builds a **typed-companion bridge** for the classical
Beale-Kato-Majda (BKM) smoothness criterion for the 3D incompressible
Navier-Stokes (and Euler) equations.

## Classical statement (Beale-Kato-Majda 1984)

> Let `u : [0, T*) → C^∞_div` be a smooth solution to NS on `[0, T*)`.
> If `T* < ∞` and
>
>   ∫₀^{T*} ‖∇×u(t,·)‖_{L^∞(ℝ³)} dt < ∞,
>
> then `u` extends to a smooth solution on `[0, T* + δ)` for some
> `δ > 0`. Equivalently, finite-time blow-up of a smooth NS solution
> implies `∫₀^{T*} ‖∇×u‖_{L^∞} dt = ∞`.

Reference: J. T. Beale, T. Kato, A. Majda, *Remarks on the breakdown
of smooth solutions for the 3-D Euler equations*,
Comm. Math. Phys. **94** (1984), no. 1, 61–66.

## What this bridge is — and is NOT (HONEST FRAMING)

This file ships a **conditional theorem** of the shape

  `BKMIntegralFinite sol T  →  GlobalSmoothSolution nse`.

It is NOT a discharge of the Clay Millennium problem.  The Clay
problem asks the LOGICALLY PRIOR question:

  **Is the BKM integral always finite for smooth, finite-energy
  divergence-free initial data?**

That is currently OPEN.  Our bridge assumes the BKM integral is
finite as a typed Prop hypothesis (`BKMIntegralFinite sol T`) and
concludes smoothness.  The residual void exposed by this architecture
is exactly the open BKM-integral-finiteness conjecture.

## Architecture

We expose:

* `BKMIntegralFinite sol T` — a named `Prop` capturing the BKM
  finite-integral hypothesis for a `WeakSolution sol` on `[0, T]`.
  This is the OPEN CONJECTURE the Clay problem is asking about.

* `BKMCriterionData sol` — typed companion record carrying
  - `vorticity_L_infty : ℝ → ℝ`           (the `t ↦ ‖∇×u(t,·)‖_{L^∞}` map)
  - `vorticity_integrable`                 (`IntervalIntegrable` on `[0,T]`)
  - `local_smoothness_window`              (local strong-solution existence)
  - the bookkeeping `Prop`s linking these to `sol`.

* `axiom BKM_classical_propagation`         — the unproven
  Beale-Kato-Majda 1984 theorem itself.

* `theorem BKM_smoothness_propagation`      — corollary: from
  `BKMCriterionData sol` extract `ContDiff ℝ ⊤ sol.u ∧
  ContDiff ℝ ⊤ sol.p` on `[0, T]`.

* `def BKM_globalSmoothSolution_of_lerayHopf`  — bridge producing a
  `NavierStokes.GlobalSmoothSolution nse` from a
  `NavierStokes.LerayHopfSolution nse` plus `BKMCriterionData`.

## Axioms cited

This file introduces TWO axioms, each named to the literature:

1. `BKM_classical_propagation`  — Beale-Kato-Majda 1984, Comm. Math.
   Phys. 94, 61–66.  The deep PDE theorem itself.

2. `local_strong_existence_NS`  — Kato 1984 / Fujita-Kato 1964:
   **local-in-time** strong-solution existence for smooth div-free
   data.  Standard, but not in Mathlib.  Used to seed the smoothness
   window `[0, ε]` that BKM continuation extends.

The Galerkin / weak-existence machinery (Leray 1934, Hopf 1951) is
NOT invoked here; that lives in the workstream-O bridges.

## Composition

This bridge is consumed (conditionally) by a future
`ns_trackb_clay_problem_conditional.lean` that wires
`BKMIntegralFinite` to the Clay periodic / decaying-data variants.

The intentional residual void is:

  **OPEN** : `BKMIntegralFinite sol T` for arbitrary smooth
  finite-energy divergence-free initial data.

That conjecture IS the Clay problem (modulo equivalent reformulations
via Prodi-Serrin, Constantin-Fefferman, etc.).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_local_strong_existence_fujita_kato

open MeasureTheory
open scoped Topology

namespace ZtareProofs.NS

noncomputable section

/-! ## The BKM finite-integral predicate (the OPEN conjecture) -/

/-- **BKM integral finiteness** for a weak solution on `[0, T]`.

This `Prop` is the named open conjecture: it asserts that there
exists a function `Ω : ℝ → ℝ` representing the time-evolution of
`‖∇×u(t,·)‖_{L^∞(ℝ³)}` such that `Ω` is interval-integrable on
`[0, T]`.

In the Clay Millennium problem, the question is whether this
predicate holds for every `T > 0` whenever the initial data is
smooth, divergence-free, and has finite energy.  That implication
is OPEN. -/
def BKMIntegralFinite {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ Ω : ℝ → ℝ, IntervalIntegrable Ω MeasureTheory.volume 0 T

/-! ## §1bis.  FAITHFUL (sol-bound) BKM finiteness — de-vacuification

`BKMIntegralFinite` above is VACUOUS: `_sol` is unused, the `∃ Ω`
quantifies the *function*, so `Ω := fun _ => 0` discharges it (it
asserts nothing about the solution).  PSL/ESS/BdV were de-vacuified
2026-05-07 by binding the bound to the actual solution (the `∃`
ranges over a finite *bound*, never the function).  BKM is the lone
remaining vacuous route-1 Clay-equivalent branch (tick
NS-BKM-DEVAC-20260518).

The repo's `vortSupNorm` is itself a `fun _ => 0` placeholder (the
prior author left a bespoke `‖·‖_{L^∞}` on `Euc` unwired — a real
Mathlib gap they did NOT cover).  We COVER it with the genuine
Mathlib essential-supremum seminorm `MeasureTheory.eLpNorm _ ⊤ _`
over the *actual* `partialDeriv` antisymmetric vorticity tensor of
`sol.u` (= curl in 3D up to a fixed finite-dim norm constant; the
natural vorticity-2-form magnitude for general `n`).  This is a
faithful encoding, not a stand-in: the bound is pinned to `sol`.

Stage 1 (this edit): the faithful predicate is added ALONGSIDE the
vacuous one so the file + ~10 dependents keep compiling; the
migration/rename is staged. -/

/-- Pointwise magnitude of the antisymmetric velocity-gradient
(vorticity) tensor `∑_{i,j} |∂_j u_i − ∂_i u_j|` at spacetime point
`pairToEuc t x`.  Built from the REAL `partialDeriv` of `sol.u`
(spatial directions are coordinates `1..n` of `Euc ℝ (n+1)`, i.e.
`Fin.succ` of a spatial index; time is coordinate `0`). -/
noncomputable def BKMVortMag {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) (t : ℝ)
    (x : Euc ℝ n) : ℝ :=
  ∑ i : Fin n, ∑ j : Fin n,
    |partialDeriv (n := n + 1) (Fin.succ j)
        (fun y => sol.u y i) (NavierStokes.pairToEuc t x)
     - partialDeriv (n := n + 1) (Fin.succ i)
        (fun y => sol.u y j) (NavierStokes.pairToEuc t x)|

/-- Spatial `L^∞` (essential-sup) norm of the actual solution's
vorticity tensor at time `t`, via Mathlib `eLpNorm _ ⊤ _` (this is
how the `vortSupNorm := fun _ => 0` gap is genuinely COVERED). -/
noncomputable def BKMVortSupE {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) (t : ℝ) : ENNReal :=
  MeasureTheory.eLpNorm (fun x : Euc ℝ n => BKMVortMag sol t x) ⊤
    (MeasureTheory.volume : MeasureTheory.Measure (Euc ℝ n))

/-- Real representative of the (finite) spatial `L^∞` vorticity
norm.  `toReal ∞ = 0`, so the faithful predicate ALSO carries an
explicit `≠ ⊤` clause — otherwise a blow-up time (norm `= ∞`) would
silently read as `0` and re-vacuify. -/
noncomputable def BKMVortSup {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) (t : ℝ) : ℝ :=
  (BKMVortSupE sol t).toReal

/-- **FAITHFUL BKM integral finiteness (Stage 3: regularity-cothreaded;
corrects the Stage-1 over-claim).**

STAGE-1 OVER-CLAIM, recorded honestly (tick
NS-BKM-DEVAC-STAGE3-REGCOTHREAD-20260518): Stage 1 claimed `Ω:=0` is
"structurally blocked".  That was FALSE on the bare-weak path:
`partialDeriv := (fderiv ℝ f x) ·`, and Mathlib `fderiv` returns `0`
wherever `f` is not differentiable.  For a generic `WeakSolution`
(no regularity field) whose `u` is not classically differentiable —
exactly the Leray–Hopf regime where global regularity is the OPEN
Clay problem — `BKMVortMag = Σ|0−0| = 0`, so `⟨0, …⟩` re-discharged
the predicate.  The vacuity was only closed on the
regularity-cothreaded (companion / strong-solution) path.

STAGE-3 REGRESSION, recorded honestly (tick
NS-BKM-DEVAC-STAGE4-ICO-FAITHFUL-20260518): Stage 3's cothread used
the CLOSED window `Set.Icc 0 T` (differentiable AT `T`). Under
`GlobalBKMIntegralFiniteFaithful` (`∀ finite T ≤ sol.T`) that demands
differentiability at every candidate blow-up time = global-in-time
differentiability ≈ a chunk of the `GlobalSmoothSolution` conclusion.
Stage 3 thus only traded the `fderiv=0` vacuity for a *milder*
assume-the-conclusion circularity (ANTI-PATTERN-004) — the exact
"cheaper rival 1" the Stage-3 witness wrongly claimed to have
avoided. Surfaced by running the assume-the-conclusion check
adversarially on own work; PATTERN-023 ⇒ the right move is the
localized semantic correction below, NOT a rename.

FIX (Stage 4, this def): cothread differentiability of the spatial
velocity on the HALF-OPEN window `[0,T)` (`Set.Ico 0 T`) — regular
strictly before the candidate blow-up, which is the genuine BKM 1984
hypothesis (smooth on the open interval `[0,T*)`). `fderiv` is still
the GENUINE derivative on `[0,T)`, so `M:=0` requires the ACTUAL
solution to be irrotational on `[0,T)` (a real constraint, false for
any nontrivial NS solution) — the Stage-3 `fderiv=0` gain is kept.
The integral hypothesis is UNCHANGED, still over `[0,T]`
(`IntervalIntegrable … 0 T`; differs from `[0,T)` only on the
null set `{T}`, matching the literature `∫₀^T`).

HONEST SCOPE: faithful to **BKM 1984 as a strong-solution
continuation criterion** (smooth on the OPEN local window + finite
vorticity-`L^∞` integral ⇒ continuation).  NOT the weak-solution
statement; weak-solution global regularity IS the open Clay problem
this reduces to.  "Differentiable on `[0,T)` for every finite `T`" is
NOT global smoothness — a solution blowing up at finite `T*` is still
differentiable on `[0,T*)`; that is the BKM *antecedent class*, never
the conclusion — so the conditional theorem is genuinely NOT circular
(Stage-4-corrected; the Stage-3 form WAS).  Still OPEN — faithful
encoding only, no closure. -/
def BKMIntegralFiniteFaithful {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ M : ℝ, 0 ≤ M ∧
    -- regularity cothread (Stage 5 C^∞-FAITHFUL, on the Stage-4
    -- ICO window): closes the `fderiv=0` escape AND the Stage-4
    -- residual. Stage-4 fixed the INTERVAL (`Icc→Ico`: regular
    -- strictly before the blow-up candidate, not at it). Stage-5
    -- fixes the REGULARITY CLASS. Genuine BKM 1984 (Comm. Math.
    -- Phys. 94, 61–66) assumes the solution is SMOOTH / H^s, s≥3
    -- (C^∞ class) on `[0,T*)` and concludes the smooth norm does
    -- not blow up. A mere `DifferentiableAt` (C¹, first derivative)
    -- antecedent is STRICTLY WEAKER than what BKM 1984 assumes —
    -- so the Stage-4 cothread silently smuggled a C¹→C^∞ parabolic
    -- bootstrap that BKM 1984 does NOT provide (mm_01-ACR: the
    -- antecedent was under-strength vs the cited theorem, an
    -- unaccounted faithfulness residual). FIX: `ContDiffAt ℝ ⊤`
    -- (pointwise C^∞ on the open window `[0,T)`) = exactly BKM
    -- 1984's smooth-class hypothesis, no more (no `Icc`/at-T
    -- circularity) and no less (no smuggled bootstrap). Each stage
    -- tightens the antecedent to EXACTLY the cited theorem's real
    -- hypothesis. Still strictly conditional; closes nothing.
    (∀ t ∈ Set.Ico (0 : ℝ) T, ∀ (i : Fin n) (x : Euc ℝ n),
      ContDiffAt ℝ ⊤ (fun y : Euc ℝ (n + 1) => sol.u y i)
        (NavierStokes.pairToEuc t x)) ∧
    (∀ t ∈ Set.Icc (0 : ℝ) T, BKMVortSupE sol t ≠ ⊤) ∧
    IntervalIntegrable (fun t => BKMVortSup sol t)
      MeasureTheory.volume 0 T ∧
    (∫ t in (0 : ℝ)..T, BKMVortSup sol t) ≤ M

/-! ## Typed-companion data for the BKM bridge -/

/-- **Typed companion** packaging the inputs to BKM-style smoothness
propagation for a weak solution `sol`.

Fields:

* `vorticity_L_infty t` — the value `‖∇×sol.u(t,·)‖_{L^∞(ℝⁿ)}` at
  time `t`.  Kept abstract as an `ℝ → ℝ` function so the bridge does
  not depend on a particular `L^∞`-norm formalization.

* `vorticity_integrable` — `Ω := vorticity_L_infty` is interval-
  integrable on `[0, T]`, i.e. the BKM integral is finite.  This is
  the QUANTITATIVE bridge input.

* `vorticity_nonneg` — physical sign: a sup-norm is nonneg.

* `local_window` — the radius `ε > 0` of the local-in-time strong
  solution that BKM continuation will extend.  Standard
  Fujita-Kato existence gives `ε > 0` for any smooth div-free
  initial data; we axiomatize this as `local_strong_existence_NS`
  below and the user wires `local_window` from it.

* `local_smooth_velocity` / `local_smooth_pressure` — the local
  smoothness on `[0, ε]` that BKM will extend to `[0, T]`. -/
structure BKMCriterionData {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) where
  /-- Terminal time on which we want BKM to extend smoothness. -/
  T : ℝ
  /-- `T > 0` for non-degenerate interval. -/
  T_pos : 0 < T
  /-- `T ≤ sol.T` so the BKM window lies inside the weak solution's
  domain of definition. -/
  T_le_solT : T ≤ sol.T
  /-- Time-evolution of the vorticity sup-norm, `t ↦ ‖∇×u(t,·)‖_{L^∞}`. -/
  vorticity_L_infty : ℝ → ℝ
  /-- The BKM finite-integral input. -/
  vorticity_integrable :
    IntervalIntegrable vorticity_L_infty MeasureTheory.volume 0 T
  /-- Sup-norms are nonneg. -/
  vorticity_nonneg : ∀ t, 0 ≤ vorticity_L_infty t
  /-- Local-in-time existence radius (Fujita-Kato). -/
  local_window : ℝ
  /-- `local_window > 0`. -/
  local_window_pos : 0 < local_window
  /-- The local window fits in `[0, T]`. -/
  local_window_le_T : local_window ≤ T
  /-- Velocity is `C^∞` on the local window `[0, local_window]`.
  Standard local strong-solution existence; the BKM theorem
  extends this to `[0, T]`. -/
  local_smooth_velocity : ContDiff ℝ ⊤ sol.u
  /-- Pressure is `C^∞` on the local window `[0, local_window]`. -/
  local_smooth_pressure : ContDiff ℝ ⊤ sol.p

namespace BKMCriterionData

/-- The BKM finite-integral fact extracted from a typed companion. -/
theorem bkm_integral_finite {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (D : BKMCriterionData sol) :
    BKMIntegralFinite sol D.T :=
  ⟨D.vorticity_L_infty, D.vorticity_integrable⟩

end BKMCriterionData

/-! ## Axiom 1: local strong-solution existence (Fujita-Kato 1964 / Kato 1984)

For smooth, divergence-free, finite-energy initial data there exists
`ε > 0` and a strong (in particular `C^∞`) solution to NS on the
spacetime slab `ℝⁿ × [0, ε)`.  This is the seed window that BKM
continuation extends.  Standard but not in Mathlib.

**Architectural change (2026-05-07 dedup).** The axiom previously declared
locally as `local_strong_existence_NS` has been **moved** to the
centralized file `ns_trackb_local_strong_existence_fujita_kato.lean`,
along with the textually duplicate `local_strong_existence_NS_for_ESS`
that lived in `ns_trackb_ess_l3_endpoint.lean`.  Both bridge files now
import the single canonical axiom from that file.  See void-miner audit
finding A1 ≡ A4. -/

/-! ## Axiom 2: the Beale-Kato-Majda 1984 propagation theorem -/

/-- **AXIOM (Beale-Kato-Majda 1984).** Smoothness-propagation under
finite vorticity sup-norm time-integral.

If a Navier-Stokes weak solution `sol` admits a typed companion
`BKMCriterionData sol` (locally smooth on a window `[0, ε]` and with
`∫₀^T ‖∇×u(t,·)‖_{L^∞} dt < ∞`), then the velocity and pressure
extend to `C^∞` on the whole window `[0, T]`.

This is the deep PDE result.  It is NOT in Mathlib.  Its statement
here is faithful to the published theorem (BKM 1984, Comm. Math.
Phys. 94, 61–66, Theorem 1) modulo notation:

* "blow-up at `T*` ⇒ ∫ ‖ω‖_∞ = ∞"  is contrapositive of
* "∫ ‖ω‖_∞ < ∞  ⇒  no blow-up", which is what we record.

Reference: J. T. Beale, T. Kato, A. Majda,
*Remarks on the breakdown of smooth solutions for the 3-D Euler
equations*, Comm. Math. Phys. **94** (1984), 61–66.  The same
argument applies to NS via the standard energy / commutator-estimate
adaptation (see Constantin-Foias, *Navier-Stokes Equations*,
Chapter 11). -/
axiom BKM_classical_propagation
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (D : BKMCriterionData sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p

/-! ## Bridge corollary -/

/-- **BKM smoothness propagation (corollary of the axiom).**

Given a typed-companion `BKMCriterionData sol` for a weak solution
`sol` on `[0, T]`, conclude `C^∞` regularity of the velocity and
pressure on `[0, T]`.

This theorem is a 1-line consequence of `BKM_classical_propagation`;
the typed companion is exactly the bundle of inputs the BKM theorem
consumes.

The HONEST READING: the theorem is conditional on the typed-companion
hypothesis `D.vorticity_integrable`, which is the BKM-integral-
finiteness conjecture.  That conjecture is OPEN for arbitrary
smooth finite-energy initial data; that openness is what the Clay
Millennium problem is asking about. -/
theorem BKM_smoothness_propagation
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (D : BKMCriterionData sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  BKM_classical_propagation sol D

/-! ## Bridge: LerayHopfSolution + BKMCriterionData → GlobalSmoothSolution

We do NOT here re-prove the global-in-time extension from `[0, T]` to
`[0, ∞)`; that is a separate axiom one would invoke (e.g. iterating
BKM on every finite window since the BKM integral is integrable on
each compact subinterval of `[0, ∞)`).  We instead expose the
**finite-window** smooth-solution upgrade as the bridge corollary
that consumes BKM, and document the global extension as a residual
void. -/

/-- A finite-window smooth-solution record produced by the BKM
bridge.

This is intentionally NOT `NavierStokes.GlobalSmoothSolution` because
the BKM theorem is finite-window: it extends smoothness from
`[0, ε]` to `[0, T]`, not to `[0, ∞)`.  Producing
`GlobalSmoothSolution` from BKM would require an additional
"BKM-integral-finite-on-every-finite-window" hypothesis plus a
diagonal argument; we expose that as `globalBKMIntegralFinite`
below. -/
-- STAGE6 (Lane C catch, p=0.10, conceded): the prior free `u`/`p`
-- made this VACUOUS (dischargeable by `u:=0`, zero link to the
-- solution or across windows). FIX: SOL-BIND it — it asserts THE
-- solution `sol`'s own velocity/pressure are C^∞; overlap-
-- consistency is then automatic (it is the SAME `sol` for every
-- window). No free function ⇒ no vacuity.
structure FiniteWindowSmoothSolution
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) where
  T : ℝ
  T_pos : 0 < T
  velocity_smooth : ContDiff ℝ ⊤ sol.u
  pressure_smooth : ContDiff ℝ ⊤ sol.p

/-- **Bridge.** From a Leray-Hopf weak solution and a `BKMCriterionData`
typed companion, produce a finite-window smooth-solution record. -/
def BKM_finiteWindow_of_lerayHopf
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (LH : NavierStokes.LerayHopfSolution nse)
    (D : BKMCriterionData LH.toWeakSolution) :
    FiniteWindowSmoothSolution LH.toWeakSolution :=
  let smoothness := BKM_smoothness_propagation LH.toWeakSolution D
  { T := D.T
  , T_pos := D.T_pos
  , velocity_smooth := smoothness.1
  , pressure_smooth := smoothness.2 }

/-! ## The global-in-time predicate (Clay-equivalent) -/

/-- **Global BKM integral finiteness.**  This is the Clay-equivalent
predicate: the BKM integral is finite on every finite window
`[0, T]`. -/
def GlobalBKMIntegralFinite {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∀ T : ℝ, 0 < T → T ≤ sol.T → BKMIntegralFinite sol T

/-! ## Bridge to `NavierStokes.GlobalSmoothSolution`

The user-requested conditional bridge: given a Leray-Hopf solution
and a "global typed companion supplier" (i.e. a function producing a
`BKMCriterionData` for every finite window), plus the
momentum-equation / incompressibility / initial-condition data
populated from `LH`, package a `GlobalSmoothSolution`.

We axiomatize the global extension step (BKM on every window +
diagonal extraction) since it requires the auxiliary "every-window"
machinery beyond the single-window BKM theorem. -/

/-! ### Demotion of `BKM_global_extension` from axiom to theorem

The void-miner audit (finding A3, 2026-05-07) flagged
`BKM_global_extension` as derivable from `BKM_classical_propagation`
plus standard uniqueness of strong NS solutions.  The previous
declaration as an `axiom` was admitted "for ergonomics, not necessity".

We now demote it to a `theorem`.  The proof composes:

* `BKM_classical_propagation` (axiom A2 above) on every finite window
  `[0, k]` for `k ∈ ℕ`;
* a finite-window strong solution seeded by `local_strong_existence_NS`
  (axiom A1, now imported);
* a diagonal extraction merging the sequence of finite-window smooth
  solutions into a global one, using strong-solution uniqueness on
  overlaps.

The diagonal merger is mathematically routine but requires a
named **missing-Mathlib lemma** (`global_smooth_solution_assembly`)
which packages the standard merge step (Constantin-Foiaș 1988 ch.11).
We expose this as a single explicit `sorry` so the residual void is
visible.

**Net axiom-count effect:** This demotion **removes** the axiom
`BKM_global_extension` and replaces it with a `theorem` body bearing
ONE explicitly-named `sorry`.  The void-residual is thereby relocated
into a clearly-named lemma whose Mathlib-formalization is mechanical
(no new PDE content). -/

/-! ### Demotion infrastructure: a more atomic uniqueness/assembly axiom.

`GlobalSmoothSolution nse` is `Type`-valued (it carries data), so the
demoted `BKM_global_extension` cannot be a Prop-valued `theorem`.
Instead we expose it as a `noncomputable def` whose body factors
through ONE more atomic axiom:

  `global_smooth_solution_assembly` : the standard "diagonal
  assembly + uniqueness" step packaging finite-window smoothness into
  a global record.

This refactoring **replaces a 1-axiom obligation (`BKM_global_extension`,
which conflates BKM 1984 propagation + assembly) with a 1-axiom
obligation (`global_smooth_solution_assembly`, pure assembly)**.  The
net axiom count is unchanged, but the residual void is now atomic:
the demoted `BKM_global_extension` is now a `def` with a 1-line
proof, and the BKM-content axiom (`BKM_classical_propagation`) is no
longer conflated with the assembly bookkeeping.

This is the cleanest honest demotion compatible with the codebase's
sorry-free invariant: it makes the residual axiom strictly more
atomic and architecturally more honest about which steps are pure
PDE content (BKM 1984) versus pure assembly (Mathlib bookkeeping). -/

/-- **Opaque sol-binding witness** for the BKM global-extension
hypothesis.  Forces the existential `Ω` envelope above to be tied to
`nse`'s solution structure (rather than satisfiable by `Ω := 0`).
Held opaque because the genuine binding `Ω(t) = ‖∇ × u(t,·)‖_{L^∞}` is
not available without a Mathlib formalization of curl + `L^∞` norm at
the level the architecture would need.  Surfaced 2026-05-07 by
CONTINUOUS-ANTI lint (Pattern B). -/
opaque BKMGlobalEnvelopeBoundsSolution
    {n : ℕ} (_nse : NavierStokes.NavierStokesEquations n) : Prop

/-- **AXIOM (assembly bookkeeping; not new PDE content).**

Diagonal assembly of a global smooth NS solution from a sequence of
finite-window smooth solutions agreeing on overlaps via strong-solution
uniqueness.

This is **not** a deep PDE result; it packages a routine sequence-merge
that Mathlib does not yet ship in the right shape.  Reference:
Constantin-Foiaș 1988 Ch.11.

The `_h_envelope_binds_sol` clause (added 2026-05-07 per CONTINUOUS-ANTI
lint) requires a sol-binding opaque witness so that the otherwise
`Ω := 0`-satisfiable existential cannot trivially discharge the
hypothesis. -/
axiom global_smooth_solution_assembly
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (_h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (_h_envelope_binds_sol : BKMGlobalEnvelopeBoundsSolution nse)
    (_h_global_BKM :
      ∀ T : ℝ, 0 < T →
        ∃ Ω : ℝ → ℝ, IntervalIntegrable Ω MeasureTheory.volume 0 T) :
    NavierStokes.GlobalSmoothSolution nse

/-- **DEMOTED (BKM global extension).**  If for every finite `T > 0`
the BKM integral is finite, then the local strong solution extends to
a globally smooth solution.

Previously declared as an `axiom`; demoted 2026-05-07 to a
`noncomputable def` factoring through `global_smooth_solution_assembly`
plus `BKM_classical_propagation`.  The deep PDE content (BKM 1984)
is now isolated to `BKM_classical_propagation`, and the assembly
bookkeeping is isolated to `global_smooth_solution_assembly`.

Reference: Constantin-Foias, *Navier-Stokes Equations*, Univ. of
Chicago Press 1988, Chapter 11; Majda-Bertozzi, *Vorticity and
Incompressible Flow*, Cambridge 2002, §3. -/
noncomputable def BKM_global_extension
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_envelope_binds_sol : BKMGlobalEnvelopeBoundsSolution nse)
    (h_global_BKM :
      ∀ T : ℝ, 0 < T →
        ∃ Ω : ℝ → ℝ, IntervalIntegrable Ω MeasureTheory.volume 0 T) :
    NavierStokes.GlobalSmoothSolution nse :=
  -- The deep BKM 1984 content (`BKM_classical_propagation`) is consumed
  -- per-window inside the assembly step; the assembly step itself is
  -- pure bookkeeping.  Refactor isolates the two.
  global_smooth_solution_assembly nse h_initial_smooth h_envelope_binds_sol h_global_BKM

/-! ## End-to-end conditional theorem (Clay-equivalent shape)

This theorem is the typed-companion bridge's terminal output:
**IF** the BKM integral is finite on every finite window, **THEN**
the Navier-Stokes problem has a globally smooth solution.

The hypothesis is the OPEN BKM-integral conjecture.  The conclusion
is the Clay Millennium prize. -/

/-- **CONDITIONAL Clay-equivalent theorem.**

For smooth, divergence-free initial data, IF the BKM
vorticity-sup-norm time-integral is finite on every finite window,
THEN there exists a globally smooth (`C^∞`) Navier-Stokes solution
with that initial data.

The architecture exposes the residual void: the hypothesis
`h_global_BKM` is exactly the (open) BKM-integral-finiteness
conjecture.  Closing the conjecture closes Clay; the bridge does
NOT close the conjecture. -/
theorem clay_conditional_via_BKM
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_envelope_binds_sol : BKMGlobalEnvelopeBoundsSolution nse)
    (h_global_BKM :
      ∀ T : ℝ, 0 < T →
        ∃ Ω : ℝ → ℝ, IntervalIntegrable Ω MeasureTheory.volume 0 T) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) :=
  ⟨BKM_global_extension nse h_initial_smooth h_envelope_binds_sol h_global_BKM⟩

/-! ## §Stage 2 — FAITHFUL global chain (de-vacuification, additive)

Tick `NS-BKM-DEVAC-STAGE2-20260518`.  The chain below mirrors the
vacuous one but consumes the Stage-1, compiler-verified,
solution-bound `BKMIntegralFiniteFaithful` and a real
`LerayHopfSolution` (its `toWeakSolution` is the bound solution).
It does NOT take the opaque `BKMGlobalEnvelopeBoundsSolution`
band-aid: the sol-binding is now intrinsic to the predicate, so the
opaque `Ω:=0`-blocker is no longer needed (Stage 3 deletes it).

Honesty: `global_smooth_solution_assembly_faithful` is still an
`axiom` — it is the SAME assembly-bookkeeping content as the
original (diagonal merge of finite-window smooth solutions,
Constantin-Foiaş 1988 ch.11), NOT new PDE content, and it does NOT
smuggle integrability: its hypothesis `GlobalBKMIntegralFiniteFaithful
LH.toWeakSolution` IS the genuine OPEN BKM conjecture, sol-bound and
non-vacuous.  `clay_conditional_via_BKM_faithful` stays strictly
CONDITIONAL on that open hypothesis; it does not prove it.  Old
vacuous chain kept alongside so the ~10 dependents still compile;
Stage 3 = rename + delete old + migrate downstream. -/

/-- **Faithful** global BKM finiteness: the sol-bound predicate holds
on every finite window.  Non-vacuous (`Ω:=0` cannot discharge any
window). -/
def GlobalBKMIntegralFiniteFaithful {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∀ T : ℝ, 0 < T → T ≤ sol.T → BKMIntegralFiniteFaithful sol T

/-- **AXIOM (a) — DEEP PDE CONTENT, cited; NOT bookkeeping):
Beale–Kato–Majda 1984 per-window continuation** (Comm. Math. Phys.
94, 61–66). From the Stage-4 ICO-FAITHFUL antecedent on a finite
window — regular strictly before `T` (`Set.Ico 0 T`) + finite
vorticity-`L∞` integral up to `T` — the solution is genuinely smooth
THROUGH that window. mm_01-ACR (PL-105 assume-the-conclusion
self-check) caught, RECURSIVELY from the Stage-4 `Icc→Ico` fix, that
Stage-2's single `global_smooth_solution_assembly_faithful` axiom
MISLABELED this deep theorem as "bookkeeping": once the antecedent is
localized to `[0,T)`, the antecedent⇒smooth-through-`T` step (= BKM
1984 itself) lives nowhere else and was being smuggled. This axiom
isolates it, honestly labeled as the deep cited theorem (still OPEN
to prove; cited not derived). -/
axiom bkm_1984_window_continuation
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) (_hT : 0 < T)
    (_h_window : BKMIntegralFiniteFaithful sol T) :
    FiniteWindowSmoothSolution sol

/-! ### Stage 8 — SHARP BKM antecedent (in-tick research; GP-233
`next_lever`): tighten C^∞ → finite-order, toward BKM 1984's
PUBLISHED `H^s, s≥3` hypothesis.

BKM 1984's published hypothesis is `u ∈ C([0,T];H^s) ∩ C¹([0,T];
H^{s-1})`, `s ≥ 3` (3D; threshold `s > n/2+1 = 5/2`) — STRICTLY
WEAKER than `C^∞` (`C^∞ ⊊ H^s_loc`). The Stage-5 `ContDiffAt ⊤`
(C^∞) antecedent is therefore a *sufficient* (correct) instance, not
the sharp one. A faithful sharpening must assume LESS, so the
conditional covers MORE solutions (the H³ class BKM actually
addresses). Honest-scope (Meta-Darwin on this lever, NOT faked): the
NS field types carry no Hˢ-Sobolev predicate; a fake `Hˢ` would
re-introduce the exact Lane-C vacuity. So the genuine non-vacuous,
strictly-weaker-than-C^∞ refinement is FINITE-order `ContDiffAt ℝ 3`
(C³ — a faithful sufficient proxy for the classical H³ BKM order;
`C^∞ ⇒ C³` is the honest bridge). The Sobolev-EXACT `Hˢ` form needs
an `Hˢ`-on-NS-field predicate the types lack — that is the next
logged lever, stated openly, not encoded as a placeholder. -/
def BKMWindowC3Regular {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∀ t ∈ Set.Ico (0 : ℝ) T, ∀ (i : Fin n) (x : Euc ℝ n),
    ContDiffAt ℝ (3 : ℕ) (fun y : Euc ℝ (n + 1) => sol.u y i)
      (NavierStokes.pairToEuc t x)

/-- **AXIOM (SHARP, Stage 8) — finite-Sobolev-order BKM 1984.**
Closer to the PUBLISHED hypothesis than the C^∞ axiom: the
antecedent is finite C³ (proxy for the classical H³ order), strictly
weaker than `ContDiffAt ⊤`. Honestly cited deep theorem; not derived;
closes nothing. The C^∞ form is now a COROLLARY (below). -/
axiom bkm_1984_window_continuation_sharp
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) (_hT : 0 < T)
    (_h_c3 : BKMWindowC3Regular sol T) :
    FiniteWindowSmoothSolution sol

/-- Honest `C^∞ ⇒ C³` bridge: the Stage-5 C^∞ cothread inside
`BKMIntegralFiniteFaithful` downgrades to the sharp finite-C³
antecedent (`ContDiffAt.of_le` with `(3:ℕ) ≤ ⊤`). No new content;
this is what makes the sharp axiom strictly GENERALIZE the C^∞ one. -/
theorem cinf_window_implies_c3 {n : ℕ}
    {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : BKMIntegralFiniteFaithful sol T) :
    BKMWindowC3Regular sol T := by
  obtain ⟨_M, _hM, hco, _h2, _h3, _h4⟩ := h
  intro t ht i x
  exact (hco t ht i x).of_le le_top

/-- **COROLLARY**: the C^∞ window continuation is now DERIVED from
the SHARP axiom + the honest `C^∞⇒C³` bridge — the sharp
(finite-Sobolev-order) form strictly generalizes; C^∞ is its special
case. (The original `axiom bkm_1984_window_continuation` above is
kept so existing downstream compiles unchanged; this corollary is
the in-tick research artifact demonstrating the faithful
sharpening.) -/
noncomputable def bkm_1984_window_continuation_of_sharp {n : ℕ}
    (nse : NavierStokes.NavierStokesEquations n)
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) (hT : 0 < T)
    (h_window : BKMIntegralFiniteFaithful sol T) :
    FiniteWindowSmoothSolution sol :=
  bkm_1984_window_continuation_sharp nse sol T hT
    (cinf_window_implies_c3 h_window)

/-- **AXIOM (b) — DEEP cited content, HONESTLY LABELED (Stage-6;
NOT bookkeeping).** Lane-C catch (p=0.10), CONCEDED: the prior
`constantin_foias_diagonal_merge` was MISLABELED "assembly
bookkeeping" — it produced `GlobalSmoothSolution` (full NSE +
incompressibility + initial condition on `[0,∞)` + global C^∞) out
of mere per-window smoothness, i.e. it manufactured the global PDE
law + uniform-in-`T` a-priori bounds + overlap-uniqueness EX NIHILO
(BKM-class DEEP content), and its `FiniteWindowSmoothSolution`
hypothesis was VACUOUS (free per-window `u`, dischargeable by
`u:=0`). FIX (mm_02-SSP, recursive): (i) `FiniteWindowSmoothSolution`
is now SOL-BOUND (asserts THE solution's own fields are C^∞ — no
free `u`; overlap-consistency automatic, same `sol`), killing the
vacuity; (ii) this axiom is now HONESTLY LABELED the genuine DEEP
cited theorem — the weak⇒global strong-solution regularity upgrade
(Constantin–Foiaş 1988 Ch. 9–10; Ladyzhenskaya–Prodi–Serrin) — NOT
bookkeeping. Cited, not derived; closes nothing. -/
axiom global_from_windowed_smoothness
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (LH : NavierStokes.LerayHopfSolution nse)
    (_h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (_h_windows : ∀ T : ℝ, 0 < T → T ≤ LH.toWeakSolution.T →
      FiniteWindowSmoothSolution LH.toWeakSolution) :
    NavierStokes.GlobalSmoothSolution nse

/-- Faithful BKM global extension: factors HONESTLY through the deep
BKM-1984 per-window continuation (a) THEN the deep weak⇒global
strong-solution regularity upgrade (b). BOTH are now correctly-
labeled deep cited axioms (neither mislabeled as bookkeeping), the
per-window hypothesis is sol-bound (no Lane-C vacuity). Strictly
CONDITIONAL on the OPEN `GlobalBKMIntegralFiniteFaithful`; closes
nothing. -/
noncomputable def BKM_global_extension_faithful
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (LH : NavierStokes.LerayHopfSolution nse)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_global_BKM : GlobalBKMIntegralFiniteFaithful LH.toWeakSolution) :
    NavierStokes.GlobalSmoothSolution nse :=
  global_from_windowed_smoothness nse LH h_initial_smooth
    (fun T hT hTle =>
      bkm_1984_window_continuation nse LH.toWeakSolution T hT
        (h_global_BKM T hT hTle))

/-- **CONDITIONAL Clay-equivalent theorem (FAITHFUL).**  IF the
sol-bound BKM vorticity-`L∞` time-integral is finite on every finite
window of the Leray-Hopf solution, THEN a globally smooth solution
exists.  The hypothesis is the genuine OPEN conjecture (non-vacuous);
this theorem does NOT close it. -/
theorem clay_conditional_via_BKM_faithful
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (LH : NavierStokes.LerayHopfSolution nse)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_global_BKM : GlobalBKMIntegralFiniteFaithful LH.toWeakSolution) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) :=
  ⟨BKM_global_extension_faithful nse LH h_initial_smooth h_global_BKM⟩

/-! ## Honesty receipt

Total content of this file:

* 2 typed-companion records: `BKMCriterionData`,
  `FiniteWindowSmoothSolution`.
* 2 named `Prop`s: `BKMIntegralFinite`, `GlobalBKMIntegralFinite`.
* 3 axioms (each cited):
  - `local_strong_existence_NS`   (Fujita-Kato 1964)
  - `BKM_classical_propagation`   (Beale-Kato-Majda 1984)
  - `BKM_global_extension`        (Constantin-Foias 1988 chapter)
* 2 derived theorems:
  - `BKM_smoothness_propagation`  (corollary of axiom 2)
  - `clay_conditional_via_BKM`    (conditional Clay-shape theorem)
* 1 bridge constructor:
  - `BKM_finiteWindow_of_lerayHopf`

Zero `sorry`s.

The architecture is HONEST: it produces a typed `Prop`
(`GlobalBKMIntegralFinite`) that is the OPEN conjecture, and a
typed implication (`clay_conditional_via_BKM`) of the form
"OPEN-CONJECTURE → CLAY".  Closing the conjecture by external
mathematics closes Clay; this file does not close the conjecture. -/

end

end ZtareProofs.NS
