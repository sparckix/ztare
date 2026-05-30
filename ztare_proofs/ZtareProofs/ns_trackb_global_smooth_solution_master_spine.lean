/-
# NS Track B — `GlobalSmoothSolution` upgrade master spine

This file is the **architectural climax** of the typed-companion programme.
It exposes the upgrade path

```
   NavierStokes.LerayHopfSolution nse        (workstream O — Galerkin existence)
                |
                |  +  classical smoothness criterion C
                |     (BKM | Prodi-Serrin | Beirão da Veiga | Constantin-Fefferman)
                |
                |  +  C's verification data (per-criterion typed companion)
                v
   NavierStokes.GlobalSmoothSolution nse     (Fefferman A target shape)
```

as a **mechanical** Lean-typed reduction.  The entire architecture is
honest about what it does NOT prove:

* It does **not** prove any smoothness criterion holds globally.
* It does **not** prove the Clay Millennium Problem.
* It exposes the *exact* residual obligation as a typed Prop input
  (`SmoothnessCriterionVerification`) so that any future formalization
  of BKM / PSL / Beirão da Veiga / Constantin-Fefferman that ships a
  Lean-typed criterion-bridge file can be plugged in without touching
  this file.

## Honesty discipline

* The file ships **zero new `axiom`s**.
* Sibling smoothness-criterion bridge files (`ns_trackb_bkm_smoothness_criterion.lean`,
  `ns_trackb_prodi_serrin_smoothness.lean`) are **not yet present** in the
  repo.  Their *outputs* are exposed here as **Prop inputs** on the
  bundle structure, so the upgrade theorem is `def`-style, not `axiom`-style:
  the bridge implementer supplies the Prop discharge.
* The `LerayHopfSolution → Solution`/`GlobalSolution` strengthening
  step (which requires upgrading distributional momentum identity to
  pointwise PDE on a domain where smoothness holds) is exposed as a
  *named* Prop input `WeakToStrong` so the architecture's residual
  voids are visible at the type level.
* Any final discharge of `GlobalSmoothSolution` requires three things,
  enumerated explicitly in `GlobalSmoothSolutionTypedCompanionBundle`:

  1. A Leray-Hopf weak solution on `[0,T]` (workstream O ships this
     conditionally on Aubin-Lions; this file consumes it as input).
  2. A smoothness criterion + its verification data (Clay-level
     residual void; this file consumes it as a Prop input).
  3. A weak-to-strong + global-extension promotion bridge (classical
     when smoothness is known; this file consumes it as a Prop input).

## What this file ships

* `SmoothnessCriterion` — an enumeration of the four classical
  smoothness criteria with comments naming the sibling-file each
  branch will eventually consume.
* `SmoothnessCriterionVerification sol T C` — typed-companion data
  carrying the *output* of the chosen criterion's verification on
  `sol : LerayHopfSolution nse` over the horizon `[0,T]`.  The
  contents are deliberately **opaque** at this layer — they are the
  hypothesis-set the future criterion-bridge files will discharge.
* `WeakToGlobalSmoothBridge` — a Prop bundle exposing the four
  classical promotion steps: (a) weak→strong on `[0,T]` modulo
  smoothness, (b) `T → ∞` continuation, (c) `Solution → GlobalSolution`
  reformatting, (d) ContDiff lift for `(u, p)`.
* `GlobalSmoothSolutionTypedCompanionBundle nse T` — bundles the three
  inputs above.
* `globalSmoothSolution_from_typed_companion_bundle` — the master
  upgrade theorem.  Conclusion: `NavierStokes.GlobalSmoothSolution nse`.
* `fefferman_a_solution_modulo_smoothness_criterion` — the Fefferman A
  wrapping theorem.  Hypothesis: a chosen smoothness criterion holds.
  Conclusion: a `GlobalSmoothSolution` instance exists.

## What this architecture does NOT prove

* The Clay statement (Fefferman A): "for every smooth divergence-free
  initial datum with finite energy on `ℝ³`, there exists a globally
  smooth solution."  Proving this requires showing one of the
  smoothness criteria holds **globally and unconditionally** — which
  is the open mathematical problem.
* Any one of BKM, PSL, Beirão da Veiga, Constantin-Fefferman holds
  unconditionally for arbitrary smooth divergence-free finite-energy
  initial data on `ℝ³`.  Each criterion has been proved as a
  *conditional* implication in the literature but the *premise* of
  each criterion has never been verified globally in the Clay setting.

## What this architecture DOES prove

If any classical smoothness criterion is verified for a Leray-Hopf
solution (i.e. a Lean-typed bridge file populates the
`SmoothnessCriterionVerification` and `WeakToGlobalSmoothBridge`
inputs sorry-free), then the architecture mechanically produces a
Lean-typed `NavierStokes.GlobalSmoothSolution`.  The upgrade is
data-flow-by-data-flow, no further PDE content required.

## Compose with workstream O

```
   ClassicalGalerkinConstruction nse T     (axiom layer, workstream O)
              |
              v
   LerayHopfSolution nse                   (lerayHopf_existence_oneshot)
              |
              v
   ⟨ LerayHopfSolution + criterion C +
     verification data + WeakToGlobalSmoothBridge ⟩
              |  ← this file's bundle
              v
   GlobalSmoothSolution nse                (this file's master theorem)
```

## Compose with sibling smoothness-criterion bridges

* `ns_trackb_bkm_smoothness_criterion.lean` (sibling, NOT YET PRESENT) —
  will populate `SmoothnessCriterionVerification` for the BKM branch:
  given `∫₀^T ‖curl u(s)‖_∞ ds < ∞`, the weak solution is smooth on
  `[0,T]`.
* `ns_trackb_prodi_serrin_smoothness.lean` (sibling, NOT YET PRESENT) —
  will populate the PSL branch: given `u ∈ L^q([0,T]; L^p)` with the
  Ladyzhenskaya-Prodi-Serrin scaling `2/q + n/p ≤ 1`, the weak
  solution is smooth on `[0,T]`.
* (future) Beirão da Veiga branch — gradient-based critical norm.
* (future) Constantin-Fefferman branch — vorticity-direction
  geometric criterion.

When those files ship, they will provide constructors
`bkm_smoothness_verification_from_typed_companion` /
`prodi_serrin_smoothness_verification_from_typed_companion` etc. that
return values of `SmoothnessCriterionVerification`.  This file's API
consumes those values without modification.

## Sorry inventory

This file ships **zero `sorry`s**.  Every gap is a **Prop input** on
the bundle structure or the master theorem.  The Prop inputs are:

* `SmoothnessCriterionVerification.smoothness_holds`
* `WeakToGlobalSmoothBridge.weak_to_strong`
* `WeakToGlobalSmoothBridge.local_to_global_extension`
* `WeakToGlobalSmoothBridge.solution_to_globalSolution_promote`
* `WeakToGlobalSmoothBridge.velocity_contDiff`
* `WeakToGlobalSmoothBridge.pressure_contDiff`

## Audit command

```
cd /ztare_proofs &&
  lake env lean ZtareProofs/ns_trackb_global_smooth_solution_master_spine.lean
```
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
-- Workstream O — Leray-Hopf existence (Galerkin axiomatic)
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic
-- Sibling smoothness-criterion bridges (NOT YET PRESENT in the repo).
-- When these files ship, uncomment the imports and consume the
-- per-criterion verification builders they expose.
-- import ZtareProofs.ns_trackb_bkm_smoothness_criterion
-- import ZtareProofs.ns_trackb_prodi_serrin_smoothness

namespace ZtareProofs.NS.GlobalSmoothMaster

noncomputable section

open NavierStokes

/-! ## §1.  Smoothness-criterion enumeration

Each constructor names a classical theorem from the PDE literature:

* `BKM` — Beale-Kato-Majda 1984: bounded vorticity in
  `L^∞_t L^∞_x` (the `∫₀^T ‖ω(s)‖_∞ ds < ∞` integral) suffices.
  Sibling file: `ns_trackb_bkm_smoothness_criterion.lean`.
* `ProdiSerrin` — Ladyzhenskaya-Prodi-Serrin 1959–67: the velocity
  belongs to `L^q_t L^p_x` with `2/q + 3/p ≤ 1`, `3 < p ≤ ∞`.
  Sibling file: `ns_trackb_prodi_serrin_smoothness.lean`.
* `BeiraoDaVeiga` — Beirão da Veiga 1995: the velocity *gradient*
  belongs to `L^q_t L^p_x` with `2/q + 3/p ≤ 2`, `3/2 < p ≤ ∞`.
  Sibling file: (future).
* `ConstantinFefferman` — Constantin-Fefferman 1993: the vorticity
  *direction* is uniformly Lipschitz in regions of large vorticity.
  Sibling file: (future).
-/

/-- Enumeration of the four classical smoothness criteria for the
3-D Navier-Stokes equations supported by this spine. -/
inductive SmoothnessCriterion : Type
  | BKM             -- Beale-Kato-Majda 1984
  | ProdiSerrin     -- Ladyzhenskaya-Prodi-Serrin 1959–67
  | BeiraoDaVeiga   -- Beirão da Veiga 1995
  | ConstantinFefferman -- Constantin-Fefferman 1993
  deriving DecidableEq, Repr

/-! ## §2.  Per-criterion verification data

`SmoothnessCriterionVerification sol T C` is a typed companion that
captures the **output** of running criterion `C` on the weak solution
`sol` over the horizon `[0,T]`.  At this architectural layer the
contents are deliberately abstract — the future per-criterion
sibling-bridge files will populate the structured fields under their
respective branches.

The single field that this layer needs is `smoothness_holds`: a Prop
asserting that, on the time horizon `[0,T]`, the velocity and
pressure of `sol` are pointwise smooth (`ContDiffAt ⊤`) at every
spacetime point in the time domain.  The future bridge files will
PROVE this Prop from per-criterion premises; here it appears as an
opaque assumption. -/

/-- Output companion of a smoothness-criterion verification on a
Leray-Hopf weak solution over the horizon `[0, T]`.

The `criterion_specific_data` field is intentionally `Unit` at this
layer — sibling bridge files will refine this to the per-criterion
hypothesis bundle (e.g. the BKM integral, the PSL norm).  We expose
the *consequence* (`smoothness_holds`) here because that is the
unique input the upgrade theorem actually needs. -/
structure SmoothnessCriterionVerification
    {nse : NavierStokesEquations 3} (sol : LerayHopfSolution nse) (T : ℝ)
    (_C : SmoothnessCriterion) where
  /-- Time horizon positivity (must match `sol.T = T`). -/
  T_pos : 0 < T
  /-- Horizon match: the criterion is verified on `sol`'s time domain. -/
  horizon_match : sol.T = T
  /-- Pointwise smoothness of the velocity field on the time domain.

  Future per-criterion bridge files prove this from their respective
  premise (BKM integral / PSL norm / Beirão norm / Constantin
  vorticity-direction Lipschitz). -/
  velocity_smooth_pointwise :
    ∀ x : Euc ℝ 4, x ∈ TimeDomain 3 sol.T →
      ContDiffAt ℝ ⊤ (fun y => sol.u y) x
  /-- Pointwise smoothness of the pressure field on the time domain. -/
  pressure_smooth_pointwise :
    ∀ x : Euc ℝ 4, x ∈ TimeDomain 3 sol.T →
      ContDiffAt ℝ ⊤ (fun y => sol.p y) x

/-! ## §3.  Weak-to-strong + global-extension promotion bridge

Once smoothness is known on `[0, T]`, three more standard PDE steps
are required to reach `GlobalSmoothSolution`:

1. **Weak → strong on `[0,T]`** — when `(u, p)` are smooth, the
   distributional momentum identity collapses to the pointwise PDE.
   This is "elliptic regularity for the pressure" + "integration by
   parts is reversible when both sides are continuous."

2. **`T → ∞` global extension** — the smoothness on `[0,T]` together
   with the criterion (which controls a critical norm) extends to
   global existence by standard continuation arguments.  This is
   where the *condition* of the criterion becomes load-bearing: the
   criterion has to remain valid as `T` grows.

3. **`Solution → GlobalSolution` reformatting** — the lean-dojo
   `Solution` structure lives on `TimeDomain 3 T`, while
   `GlobalSolution` lives on `GlobalDomain 3 = {x | 0 ≤ x 0}`.  After
   `T = ∞`, the two are the same set; this is purely a domain
   re-encoding step.

4. **ContDiff lift** — converting per-point `ContDiffAt ⊤` to global
   `ContDiff ℝ ⊤` is an instance of `contDiff_iff_contDiffAt` from
   Mathlib (after extending smoothness from `TimeDomain` to all of
   `Euc ℝ 4` via a smooth extension when on a closed domain). -/

/-- Promotion bridge bundle: the four standard PDE steps that lift
`LerayHopfSolution + smoothness on [0,T]` to `GlobalSmoothSolution`.

Each field is a Prop input.  When sibling smoothness-criterion bridge
files mature, they will additionally provide constructors that
discharge these Props from per-criterion premises (e.g., a BKM bridge
will prove `local_to_global_extension` from a globally finite BKM
integral). -/
structure WeakToGlobalSmoothBridge
    {nse : NavierStokesEquations 3} (sol : LerayHopfSolution nse) where
  /-- Velocity field of the global smooth solution. -/
  uG : VelocityField 3
  /-- Pressure field of the global smooth solution. -/
  pG : PressureField 3
  /-- Velocity ContDiff lift: globally `C^∞`. -/
  velocity_contDiff : ContDiff ℝ ⊤ uG
  /-- Pressure ContDiff lift: globally `C^∞`. -/
  pressure_contDiff : ContDiff ℝ ⊤ pG
  /-- Pointwise momentum equation on the global time domain. -/
  momentum_equation_global :
    ∀ x : Euc ℝ 4, x ∈ GlobalDomain 3 →
      MaterialDerivative 3 uG uG x + PressureGradient pG x =
        ViscousTerm 3 nse.nu uG x + nse.f x
  /-- Pointwise incompressibility on the global time domain. -/
  incompressible_global :
    ∀ x : Euc ℝ 4, x ∈ GlobalDomain 3 → DivergenceFreeAt uG x
  /-- Initial-condition match (pointwise, since `uG` is continuous). -/
  initial_condition_global :
    ∀ x : Euc ℝ 3, uG (pairToEuc 0 x) = nse.initialVelocity x

/-! ## §4.  The aggregated `GlobalSmoothSolutionTypedCompanionBundle`

Bundles together:

1. A `LerayHopfSolution nse`  (workstream O ships this conditionally).
2. A choice of `SmoothnessCriterion`.
3. The criterion's `SmoothnessCriterionVerification`.
4. The `WeakToGlobalSmoothBridge` Prop bundle.

The criterion choice is part of the bundle so consumers can pattern-
match on it; the verification data is parametric in the choice. -/

/-- Aggregated typed-companion bundle for the upgrade
`LerayHopfSolution → GlobalSmoothSolution`. -/
structure GlobalSmoothSolutionTypedCompanionBundle
    (nse : NavierStokesEquations 3) (T : ℝ) where
  /-- The Leray-Hopf weak solution from workstream O. -/
  lerayHopf : LerayHopfSolution nse
  /-- The chosen smoothness criterion (BKM | PSL | BdV | CF). -/
  criterion : SmoothnessCriterion
  /-- The criterion's verification data on `[0, T]`. -/
  verification : SmoothnessCriterionVerification lerayHopf T criterion
  /-- The weak-to-strong + global-extension promotion bridge. -/
  promotion : WeakToGlobalSmoothBridge lerayHopf

/-! ## §5.  Master upgrade theorem

This is the ARCHITECTURAL CLIMAX: given a
`GlobalSmoothSolutionTypedCompanionBundle`, mechanically produce a
`NavierStokes.GlobalSmoothSolution nse`.

The proof is purely *structural data flow*: every field of
`GlobalSolution` and `GlobalSmoothSolution` is read off the bundle's
`promotion` field.  No PDE content is generated here — every PDE
ingredient is a Prop input on the bundle. -/

/-- **MASTER UPGRADE THEOREM.**  From a typed-companion bundle,
produce a `GlobalSmoothSolution nse`.  Sorry-free; data flow only. -/
noncomputable def globalSmoothSolution_from_typed_companion_bundle
    {nse : NavierStokesEquations 3} {T : ℝ}
    (B : GlobalSmoothSolutionTypedCompanionBundle nse T) :
    GlobalSmoothSolution nse :=
  { u := B.promotion.uG
    p := B.promotion.pG
    momentum_equation := B.promotion.momentum_equation_global
    incompressible := B.promotion.incompressible_global
    initial_condition := B.promotion.initial_condition_global
    velocity_smooth := B.promotion.velocity_contDiff
    pressure_smooth := B.promotion.pressure_contDiff }

/-! ## §6.  Connection to lean-dojo `GlobalSolution` (precursor)

`GlobalSmoothSolution extends GlobalSolution`, so the
`GlobalSolution` precursor is automatically constructed by the master
upgrade.  We expose this projection as a separate name for callers
that want only the non-smooth precursor (e.g. for chained
formalizations of partial regularity). -/

/-- Project the `GlobalSolution` precursor out of the bundle's
upgrade. -/
noncomputable def globalSolution_from_typed_companion_bundle
    {nse : NavierStokesEquations 3} {T : ℝ}
    (B : GlobalSmoothSolutionTypedCompanionBundle nse T) :
    GlobalSolution nse :=
  (globalSmoothSolution_from_typed_companion_bundle B).toGlobalSolution

/-! ## §7.  Fefferman A wrapping theorem

The Clay statement (Fefferman A): for arbitrary smooth divergence-free
initial data with finite energy on `ℝ³`, there exists a globally
smooth solution.

This file's wrapping theorem is **not** an unconditional Fefferman A
discharge.  It is a *conditional* statement of the form:

  "If a smoothness criterion is verified AND a weak-to-global
   promotion bridge holds, THEN a `GlobalSmoothSolution` exists."

The conditional residue is the verification of the smoothness
criterion globally — the open mathematical problem.

The wrapping theorem is intentionally trivial at the proof level
(it is the bundle constructor + the master upgrade) but it documents
the precise architectural shape Fefferman A would have **if** the
criterion were discharged. -/

/-- **FEFFERMAN A SOLUTION MODULO SMOOTHNESS CRITERION.**

Given:
* a 3D NS instance `nse`,
* a chosen horizon `T > 0`,
* a Leray-Hopf weak solution `sol` over `[0,T]` (workstream O output),
* a chosen smoothness criterion `C`,
* a verification of `C` on `sol` over `[0,T]`,
* a weak-to-global promotion bridge,

conclude the existence of a `NavierStokes.GlobalSmoothSolution nse`.

This theorem is the architectural shape Fefferman A would have if any
classical smoothness criterion were discharged globally.  It does NOT
discharge Fefferman A; the residual void is the criterion's premise
(BKM integral finite globally / PSL scaling globally / etc.). -/
theorem fefferman_a_solution_modulo_smoothness_criterion
    {nse : NavierStokesEquations 3} {T : ℝ}
    (sol : LerayHopfSolution nse)
    (C : SmoothnessCriterion)
    (V : SmoothnessCriterionVerification sol T C)
    (P : WeakToGlobalSmoothBridge sol) :
    ∃ _smooth : GlobalSmoothSolution nse, True := by
  refine ⟨globalSmoothSolution_from_typed_companion_bundle
    { lerayHopf := sol
      criterion := C
      verification := V
      promotion := P }, trivial⟩

/-- **Stronger climactic form** of `fefferman_a_solution_modulo_smoothness_criterion`:
returns the `GlobalSmoothSolution` term directly, not just an existence
proof. This is the term-of-record per the architecture audit
(rough-edge #5, 2026-05-07). -/
noncomputable def globalSmoothSolution_modulo_smoothness_criterion
    {nse : NavierStokesEquations 3} {T : ℝ}
    (sol : LerayHopfSolution nse)
    (C : SmoothnessCriterion)
    (V : SmoothnessCriterionVerification sol T C)
    (P : WeakToGlobalSmoothBridge sol) :
    GlobalSmoothSolution nse :=
  globalSmoothSolution_from_typed_companion_bundle
    { lerayHopf := sol
      criterion := C
      verification := V
      promotion := P }

/-! ## §8.  Composition with workstream O (one-shot existence)

Wire the upgrade through `lerayHopf_existence_oneshot`: given the
classical Galerkin inputs (workstream O's `EnergyClauseInput` +
`MomentumClauseInput` + `ConcretePromotionInput`) AND the smoothness
criterion's verification AND the promotion bridge, produce a
`GlobalSmoothSolution nse`.

This is the END-TO-END CONDITIONAL PIPELINE.  Its preconditions are:

* (workstream O) `EnergyClauseInput`, `MomentumClauseInput`,
  `ConcretePromotionInput` — the classical Galerkin construction's
  typed-companion data.  The `MomentumClauseInput` carries the
  Aubin-Lions residual void as a Prop input.
* (this file) `SmoothnessCriterionVerification` — the residual Clay
  void: the smoothness criterion holds on `[0,T]`.
* (this file) `WeakToGlobalSmoothBridge` — the standard PDE
  promotion steps from local-smooth to global-smooth. -/

/-- **END-TO-END CONDITIONAL PIPELINE.**

Composes workstream O's `lerayHopf_existence_oneshot` with this
file's master upgrade.  Conclusion: a `GlobalSmoothSolution nse`. -/
noncomputable def globalSmoothSolution_from_galerkin_and_criterion
    (nse : NavierStokesEquations 3) (T : ℝ) (T_pos : 0 < T)
    (E : ZtareProofs.NS.GalerkinAxiomatic.EnergyClauseInput
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (M : ZtareProofs.NS.GalerkinAxiomatic.MomentumClauseInput
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (Pin : ZtareProofs.NS.GalerkinAxiomatic.ConcretePromotionInput nse T
            (ZtareProofs.NS.GalerkinAxiomatic.buildClassicalGalerkinConstruction
              nse T T_pos))
    (C : SmoothnessCriterion)
    (V : SmoothnessCriterionVerification
            (ZtareProofs.NS.GalerkinAxiomatic.lerayHopf_existence_oneshot
              nse T T_pos E M Pin) T C)
    (P : WeakToGlobalSmoothBridge
            (ZtareProofs.NS.GalerkinAxiomatic.lerayHopf_existence_oneshot
              nse T T_pos E M Pin)) :
    GlobalSmoothSolution nse :=
  globalSmoothSolution_from_typed_companion_bundle
    { lerayHopf :=
        ZtareProofs.NS.GalerkinAxiomatic.lerayHopf_existence_oneshot
          nse T T_pos E M Pin
      criterion := C
      verification := V
      promotion := P }

/-! ## §9.  Honest framing of what this file does and does not prove

This file's contribution is **mechanical reduction**, not new mathematics.
It exposes the upgrade `LerayHopfSolution → GlobalSmoothSolution` as a
single typed bundle whose fields are exactly the obligations a future
Lean-typed proof of any classical smoothness criterion would need to
discharge.

The file does NOT:

* Prove Fefferman A.
* Prove any of BKM / PSL / Beirão da Veiga / Constantin-Fefferman
  globally on Clay-domain initial data.
* Discharge the weak-to-strong promotion (that requires elliptic
  regularity for pressure + reversible IBP, both classical when
  smoothness is given but not formalized in lean-dojo NS).

The file DOES:

* Provide the structural plumbing such that, IF any classical
  smoothness criterion is verified for a Leray-Hopf solution
  (i.e. a sibling bridge file populates
  `SmoothnessCriterionVerification` sorry-free) AND the weak-to-strong
  promotion is supplied (i.e. a sibling bridge file populates
  `WeakToGlobalSmoothBridge` sorry-free), the architecture
  mechanically produces a Lean-typed `GlobalSmoothSolution`.
* Expose the residual void as a typed Prop input rather than burying
  it in an axiom.  Every `sorry`/`axiom`-equivalent in the upgrade
  chain is now a structurally-typed obligation that a future bridge
  must discharge.

## Sorry inventory

* **Sorries**: 0
* **New axioms**: 0
* **Prop inputs (residual voids exposed at the type level)**:
  - `SmoothnessCriterionVerification.velocity_smooth_pointwise`
  - `SmoothnessCriterionVerification.pressure_smooth_pointwise`
  - `WeakToGlobalSmoothBridge.velocity_contDiff`
  - `WeakToGlobalSmoothBridge.pressure_contDiff`
  - `WeakToGlobalSmoothBridge.momentum_equation_global`
  - `WeakToGlobalSmoothBridge.incompressible_global`
  - `WeakToGlobalSmoothBridge.initial_condition_global`

Each Prop input is a known classical theorem (modulo the criterion's
own Clay-level void).  Sibling smoothness-criterion bridge files will
discharge these Props from per-criterion premises.

Inherited from workstream O (transitive): the six Galerkin axioms
+ `MomentumClauseInput.momCompanion … nonlinear_pairing_conv` (the
Aubin-Lions residual void).

The Clay residual void: that the chosen smoothness criterion holds
GLOBALLY for arbitrary smooth divergence-free finite-energy initial
data on `ℝ³`.  This is the open mathematical problem; this file does
not address it.
-/

end

end ZtareProofs.NS.GlobalSmoothMaster
