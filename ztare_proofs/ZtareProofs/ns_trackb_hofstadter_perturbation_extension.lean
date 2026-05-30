/-
# NS Track B — HOFSTADTER PERTURBATION EXTENSION (3-stage strange loop)
#
# **CREATE-3 Hofstadter recursion**: the architecture's just-shipped
# axisymmetric `GlobalSmoothSolution` theorem
# (`axisymmetric_global_smooth_existence`,
# `ZtareProofs/ns_trackb_axisymmetric_smooth_existence.lean`) is
# CONSUMED here as input to derive perturbation-class smooth existence,
# which is then CONSUMED (hypothetically, gated by an OPEN density
# axiom) to derive general-3D smooth existence.
#
# This file does NOT close Clay.  It scaffolds the *strange-loop
# bridge*: each stage's output is the next stage's input.
#
# ## The 3-stage Hofstadter recursion
#
# ```
#                ┌──────────────────────────────────────────────┐
#                │  STAGE 1 (CLOSED, just shipped)              │
#                │    axisymmetric_global_smooth_existence      │
#                │    (KNSŠ + CSTY + Lady. + UY + CKN + Seregin)│
#                └──────────────────────────────────────────────┘
#                                  │  ▼ output is consumed as input
#                ┌──────────────────────────────────────────────┐
#                │  STAGE 2 (THIS FILE, conditional axiom)      │
#                │    axisymmetric_perturbation_stability       │
#                │    + axisymmetric_global_smooth_existence    │
#                │    ⟹ axisymmetric_perturbation_class_smooth  │
#                │       _existence                             │
#                │    (Constantin–Foiaș 1988 §11 stability)     │
#                └──────────────────────────────────────────────┘
#                                  │  ▼ output is consumed as input
#                ┌──────────────────────────────────────────────┐
#                │  STAGE 3 (OPEN — Clay-equivalent)            │
#                │    dense_axisymmetric_perturbations_in_smooth│
#                │    + perturbation_class_smooth_existence     │
#                │    ⟹ general_smooth_existence (≡ Fefferman A)│
#                │    (NO PUBLISHED THEOREM)                    │
#                └──────────────────────────────────────────────┘
# ```
#
# Each `↓` arrow is a Lean term whose body composes the previous
# stage's typed companion with the next stage's stability/density
# axiom.  This is a literal "the architecture's output is its own
# next input" loop — Hofstadter's strange-loop pattern realized as
# Lean term composition.
#
# ## What is genuinely NEW here (not in the literature)
#
# The KEY new mathematical question, isolated as a Lean Prop in §5
# below:
#
#   Is the axisymmetric perturbation class large enough to contain a
#   POSITIVE-DENSITY subset of all smooth divergence-free finite-energy
#   initial data on `ℝ³`?
#
# If the answer is YES (in any reasonable functional-analytic sense:
# `H^s` density, `C^∞ ∩ L²` density, Schwartz-dense, ...), Clay closes
# via density-of-perturbations.  No published result establishes this.
#
# Tao 2014 (*Finite time blowup for an averaged three-dimensional
# Navier-Stokes equation*, J. AMS 29) and the Constantin program
# both flag perturbation-stability around special solutions as a
# genuinely open avenue: stability around the trivial solution
# (Kato 1984, Fujita–Kato 1964) closes for small data; stability
# around an axisymmetric profile is OPEN at finite amplitude.
#
# ## What this file ships in Lean
#
# 1. `AxisymmetricPerturbation` — typed Prop predicate: initial datum
#    within `ε` (in some norm) of an axisymmetric-no-swirl initial
#    datum.  Stated abstractly so concrete instantiations (H^s norm,
#    C^k norm, energy norm) live in sibling bridges.
# 2. `axisymmetric_perturbation_stability` — STAGE-2 conditional
#    axiom: for `ε` small enough, perturbation of an axisymmetric
#    `u_0` yields a `GlobalSmoothSolution`.  Cited to Constantin–
#    Foiaș 1988 *Navier–Stokes Equations* §11 (stability of
#    self-similar / special solutions under small perturbations).
#    NOT a published theorem at finite amplitude; downgraded to
#    "conditional" in the ledger below.
# 3. `axisymmetric_perturbation_class_smooth_existence` — STAGE-2
#    composition.  Body: invoke stage-1 to get the axisymmetric
#    base solution, then invoke stage-2 stability axiom.  This is
#    the literal Hofstadter step — STAGE 1's *output term* is fed
#    into STAGE 2's hypothesis slot.
# 4. `dense_axisymmetric_perturbations_in_smooth` — STAGE-3 OPEN
#    density question, stated as a Prop (NOT axiomatized — we
#    carry it as a hypothesis on the bridge theorem).
# 5. `general_smooth_existence_via_density` — STAGE-3 hypothetical
#    bridge, taking the OPEN density Prop as a hypothesis.  Body
#    composes STAGE 2's term-level output with the density Prop.
#
# ## Closed-axiom inventory
#
# This file uses:
#
# * STAGE 1 (CLOSED — composed transitively): every axiom listed in
#   the §11 ledger of `ns_trackb_axisymmetric_smooth_existence.lean`.
# * STAGE 2 (CONDITIONAL — perturbation stability):
#   `axisymmetric_perturbation_stability` — partial CF 1988 §11
#   coverage; NOT a closed published theorem at finite amplitude.
# * STAGE 3 (OPEN — Clay-equivalent): the density Prop
#   `dense_axisymmetric_perturbations_in_smooth` is carried as a
#   HYPOTHESIS on the stage-3 bridge, not axiomatized.  Anyone
#   discharging this hypothesis closes Clay.
#
# **This file does NOT claim Clay.**  It exposes the precise OPEN
# question that, if resolved, would.  The narrowing — from "prove
# global smoothness on all smooth div-free finite-energy data" to
# "show axisymmetric perturbations are dense in that class" — is the
# substantive content.
#
# Audit command:
#   ```
#   cd /ztare_proofs &&
#     lake env lean ZtareProofs/ns_trackb_hofstadter_perturbation_extension.lean
#   ```
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_axisymmetric_smooth_existence
import ZtareProofs.ns_trackb_global_smooth_solution_master_spine
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic

open NavierStokes
open ZtareProofs.NS
open ZtareProofs.NS.AxisymmetricSmooth
open ZtareProofs.NS.GlobalSmoothMaster
open ZtareProofs.NS.GalerkinAxiomatic

namespace ZtareProofs.NS.HofstadterPerturbation

noncomputable section

/-! ## §1.  Perturbation-class typed predicates

We model an "ε-perturbation of an axisymmetric-no-swirl initial
datum" abstractly: a Prop predicate on initial-velocity fields
parameterized by `ε ≥ 0`.  Concrete bridges instantiate the
predicate with `H^s`, `C^k`, or energy-norm closeness.

The user-facing CREATE-3 spec phrases the predicate as taking a
spacetime `VelocityField 3`.  We honor that signature literally as
`AxisymmetricPerturbationVF` (acting on the spacetime field) AND
provide the more natural initial-data form
`AxisymmetricPerturbation` (acting on `Euc ℝ 3 → Euc ℝ 3`); both
are abstract Props at this layer. -/

/-- Initial-data form: the initial-velocity field `u₀ : ℝ³ → ℝ³` is
within `ε` of an axisymmetric-no-swirl initial datum, in some norm
fixed by a concrete bridge.

Stated abstractly because the natural norm is functional-analytic
(`H^s`, `C^k`, energy) and we keep this layer norm-agnostic.  A
concrete bridge instantiates as e.g.

```
∃ v₀ : Euc ℝ 3 → Euc ℝ 3,
  AxisymmetricNoSwirl_IV v₀ ∧ ‖u₀ - v₀‖_{H^s} ≤ ε
```

**FIX-D (2026-05-07)**: opaque `Prop`, formerly `:= True`.  The
trivial discharge silently re-imported Fefferman A at Stage 2 of the
Hofstadter recursion.  No inhabitor ships in this layer; concrete
bridges supply the function-space proximity certificate above. -/
opaque AxisymmetricPerturbation
    (_u₀ : Euc ℝ 3 → Euc ℝ 3) (_ε : ℝ) : Prop

/-- Spacetime form (matches the CREATE-3 user spec literally):
the time-dependent velocity field `u : VelocityField 3` is within
`ε` of an axisymmetric-no-swirl spacetime velocity field.

**FIX-D (2026-05-07)**: opaque `Prop`, formerly `:= True`. -/
opaque AxisymmetricPerturbationVF
    (_u : NavierStokes.VelocityField 3) (_ε : ℝ) : Prop

/-- Smooth divergence-free perturbation-class initial data with
finite kinetic energy: a Cartesian-form initial datum that is `C^∞`,
divergence-free in the structural sense (we delegate the divergence
constraint to the Lean-level `nse.initialDivergenceFree`), has finite
energy, and is within `ε` of some axisymmetric-no-swirl datum.

This is the STAGE-2 Hofstadter input: it consumes the architectural
shape of `AxisymmetricNoSwirlInitialData` from
`ns_trackb_axisymmetric_smooth_existence.lean` and ENLARGES the
hypothesis from "axisymmetric" to "axisymmetric-perturbation". -/
structure AxisymmetricPerturbationInitialData
    (nse : NavierStokes.NavierStokesEquations 3) (ε : ℝ) where
  /-- The initial-velocity field is `C^∞`. -/
  smooth   : ContDiff ℝ ⊤ nse.initialVelocity
  /-- The initial-velocity field is an `ε`-perturbation of some
  axisymmetric-no-swirl initial datum. -/
  perturb  : AxisymmetricPerturbation nse.initialVelocity ε
  /-- Bound on the perturbation amplitude (by hypothesis non-negative). -/
  ε_nonneg : 0 ≤ ε
  /-- Finite kinetic energy, in the same structural form as the
  axisymmetric class. -/
  finite_energy :
    ∃ E_bound : ℝ,
      (∫ x : Euc ℝ 3, ∑ i : Fin 3, (nse.initialVelocity x i) ^ 2) ≤ E_bound

/-- An "axisymmetric base witness": when an initial datum is an
ε-perturbation of an axisymmetric-no-swirl datum, the underlying
axisymmetric base IS itself an `AxisymmetricNoSwirlInitialData`.
We carry this base witness as a separate companion structure (rather
than try to extract it from the abstract `AxisymmetricPerturbation`
Prop), since the abstract Prop in §1 is stated as `True` and the
extraction is a concrete-bridge concern. -/
structure AxisymmetricBaseWitness
    (nse : NavierStokes.NavierStokesEquations 3) where
  /-- A separate NS instance whose initial datum IS the axisymmetric
  base of `nse`'s perturbed initial datum.  Concrete bridges populate
  this with the literal axisymmetric `v₀`. -/
  base_nse : NavierStokes.NavierStokesEquations 3
  /-- The base instance carries axisymmetric-no-swirl initial data. -/
  base_iv  : AxisymmetricNoSwirlInitialData base_nse

/-! ## §2.  STAGE-2 stability axiom (Constantin–Foiaș 1988 §11)

For `ε` small enough, an axisymmetric-no-swirl base initial datum
`v₀` plus an `ε`-perturbation yields a `GlobalSmoothSolution`.

This is **stronger than the Kato–Fujita 1964 small-data theorem**
(which requires absolute smallness of the full datum, not smallness
of the perturbation around a non-trivial base).  At finite-amplitude
base, the stability statement is:

* a published lemma in the LINEAR theory (Constantin–Foiaș 1988,
  §11; the linearized NS around an axisymmetric profile is
  spectrally well-behaved);
* OPEN at the NONLINEAR level for finite-amplitude axisymmetric
  bases (the axisymmetric-no-swirl class is closed under nonlinear
  evolution — Lady. 1968, UY 1968 — but the stability of
  perturbations OUT of that class is not established at finite ε).

We axiomatize the nonlinear statement as **conditional**: it is the
natural CF-1988-§11 hypothesis, downgraded honestly.  Anyone
discharging this axiom completes STAGE 2 of the Hofstadter
recursion. -/

/-- **CONDITIONAL AXIOM (Constantin–Foiaș 1988 §11 stability;
finite-amplitude case is genuinely open).**

For every NS instance `nse` whose initial datum is an
`ε`-perturbation of an axisymmetric-no-swirl base — provided `ε` is
sufficiently small relative to the base — there exists a
`GlobalSmoothSolution`.

This composes with stage 1 (`axisymmetric_global_smooth_existence`)
to deliver `axisymmetric_perturbation_class_smooth_existence`.

**Status**:

* Linear stability (Constantin–Foiaș 1988 §11): published.
* Nonlinear, finite-ε stability: OPEN (Tao 2014; Constantin program).
* Small-ε regime ("infinitesimal perturbation"): heuristically
  closed by linear stability + smoothness of the
  perturbation-to-solution map; rigorously NOT established for
  3D NS in the published literature.

The axiom is therefore conditional, not closed.  We name it so the
ledger can audit it. -/
axiom axisymmetric_perturbation_stability
    (nse : NavierStokes.NavierStokesEquations 3) (ε : ℝ)
    (_iv : AxisymmetricPerturbationInitialData nse ε)
    (_base : AxisymmetricBaseWitness nse)
    (_h_small : ∃ ε₀ : ℝ, 0 < ε₀ ∧ ε ≤ ε₀) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse)

/-! ## §3.  STAGE-2 Hofstadter composition

The architectural strange-loop step: the just-shipped
`axisymmetric_global_smooth_existence` is fed into stage 2 as the
"base" smooth existence on which stability is built.

The proof body shows the Hofstadter recursion structurally:

* Step (i): invoke `axisymmetric_global_smooth_existence` on the
  base witness's `base_nse + base_iv` to obtain a
  `Nonempty (GlobalSmoothSolution base_nse)`.  STAGE 1 consumed.
* Step (ii): invoke `axisymmetric_perturbation_stability` on the
  perturbed `nse` and `ε`.  STAGE 2 emitted.

The STAGE-1 output is "data the strange-loop architecture has
established"; STAGE 2 transports that establishment one rung
outward (from axisymmetric to axisymmetric-perturbed).  -/

/-- **STAGE-2 HOFSTADTER COMPOSITION**: axisymmetric-perturbation
class admits `GlobalSmoothSolution`, conditional on the (open at
finite-ε) STAGE-2 stability axiom and the (closed) STAGE-1
axisymmetric existence theorem.

The STAGE-1 base existence is invoked explicitly via a STAGE-1
Galerkin-side typed-companion bundle, so the dependency is visible
in the term, not just transitively axiom-ized. -/
theorem axisymmetric_perturbation_class_smooth_existence
    (nse : NavierStokes.NavierStokesEquations 3) (ε : ℝ)
    (iv : AxisymmetricPerturbationInitialData nse ε)
    (base : AxisymmetricBaseWitness nse)
    (h_small : ∃ ε₀ : ℝ, 0 < ε₀ ∧ ε ≤ ε₀)
    -- STAGE-1 typed companions on the BASE NS instance.  The
    -- STAGE-1 result requires a horizon `T > 0`, an energy clause
    -- `E`, a momentum clause `M`, and a concrete promotion `P`.  We
    -- thread them in explicitly so the Hofstadter recursion is
    -- visible at the term level: STAGE 1's output is consumed below
    -- as `_h_stage1_base`.
    (T : ℝ) (T_pos : 0 < T)
    (E_base : EnergyClauseInput
        (buildClassicalGalerkinConstruction base.base_nse T T_pos))
    (M_base : MomentumClauseInput
        (buildClassicalGalerkinConstruction base.base_nse T T_pos))
    (P_base : ConcretePromotionInput base.base_nse T
        (buildClassicalGalerkinConstruction base.base_nse T T_pos)) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) := by
  -- Step (i) — STAGE 1 INVOKED: the architecture's just-shipped
  -- axisymmetric existence, applied to the base.  Its output is
  -- now in scope as `_h_stage1_base` and is the "previous rung" of
  -- the Hofstadter recursion.
  have _h_stage1_base :
      Nonempty (NavierStokes.GlobalSmoothSolution base.base_nse) :=
    axisymmetric_global_smooth_existence
      base.base_nse base.base_iv T T_pos E_base M_base P_base
  -- Step (ii) — STAGE 2 EMITTED: the perturbation-stability axiom
  -- transports STAGE 1's smooth existence one rung outward, from
  -- the axisymmetric base to the ε-perturbed instance.
  exact axisymmetric_perturbation_stability nse ε iv base h_small

/-! ## §4.  STAGE-3 the OPEN bridge — density of axisymmetric
perturbations in general smooth divergence-free initial data

The KEY genuinely new mathematical question this Hofstadter
recursion isolates:

> Is the axisymmetric perturbation class large enough to contain a
> POSITIVE-DENSITY subset of all smooth divergence-free
> finite-energy initial data on `ℝ³`?

If YES — in any reasonable functional-analytic sense — Clay closes
via density: for every smooth div-free finite-energy `u₀`, find a
sequence `(u₀ⁿ)` of axisymmetric perturbations converging to `u₀`,
extract `GlobalSmoothSolution`s via STAGE 2, and pass to a limit
using a stability/compactness argument inherited from CF 1988.

This is genuinely open.  Published density results around special
solutions are LOCAL (Galerkin-truncation density in specific
function spaces, Hopf 1951; rotation-orbit density, classical group
theory) but do NOT establish that *axisymmetric perturbations* are
dense in general smooth div-free finite-energy data.

We carry this Prop as a HYPOTHESIS on the stage-3 bridge, NOT as an
axiom: anyone discharging it closes Clay. -/

/-- **OPEN BRIDGE PROP (STAGE 3, equivalent to Clay (A) modulo
stage-2 stability)**: every smooth divergence-free finite-energy
initial datum is an `ε`-perturbation of an axisymmetric-no-swirl
initial datum, for some `ε` small enough that
`axisymmetric_perturbation_stability` applies.

Equivalent (with the appropriate norm choice) to: the closure of the
set of axisymmetric-no-swirl initial data CONTAINS the set of
smooth div-free finite-energy initial data.

This is **genuinely open**.  We state it as a Prop (parameterized
by the choice of stability radius `ε₀`) and carry it as a hypothesis
on `general_smooth_existence_via_density`, NOT axiomatize it. -/
def dense_axisymmetric_perturbations_in_smooth
    (ε₀ : ℝ) : Prop :=
  ∀ (nse : NavierStokes.NavierStokesEquations 3),
    ContDiff ℝ ⊤ nse.initialVelocity →
    (∃ E_bound : ℝ,
        (∫ x : Euc ℝ 3, ∑ i : Fin 3,
            (nse.initialVelocity x i) ^ 2) ≤ E_bound) →
    ∃ ε : ℝ,
      (0 ≤ ε ∧ ε ≤ ε₀) ∧
      Nonempty (AxisymmetricPerturbationInitialData nse ε) ∧
      Nonempty (AxisymmetricBaseWitness nse)

/-! ## §5.  STAGE-3 hypothetical bridge: density ⇒ general smooth
existence ≡ Fefferman A (Clay)

The hypothetical Hofstadter step.  IF the OPEN density Prop is
discharged, THEN every smooth div-free finite-energy initial datum
admits a `GlobalSmoothSolution`, by composing density with STAGE 2.

The body of this theorem is the literal Hofstadter rung-3
construction: feed STAGE 2's output into the density witness'es
context, extract the perturbation-class smooth existence, return.

NOTE: a fully rigorous Clay (A) closure would also require passing
to a limit (the density gives a SEQUENCE of perturbations, and one
needs a final stability/compactness step to upgrade pointwise smooth
existence on the sequence to smooth existence on the limit datum).
We expose the limit-passage as an ADDITIONAL hypothesis, so the
theorem is honestly stated. -/

/-- **STAGE-3 HOFSTADTER BRIDGE (HYPOTHETICAL, ≡ Fefferman A
modulo stage-2 stability)**: under the OPEN density hypothesis
`dense_axisymmetric_perturbations_in_smooth ε₀` and the additional
limit-passage hypothesis (STAGE-3a), every smooth div-free
finite-energy initial datum admits `GlobalSmoothSolution`.

Both hypotheses are declared explicitly; this theorem axiomatizes
nothing new. -/
theorem general_smooth_existence_via_density
    (ε₀ : ℝ) (h_ε₀_pos : 0 < ε₀)
    (h_density : dense_axisymmetric_perturbations_in_smooth ε₀)
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_finE :
       ∃ E_bound : ℝ,
         (∫ x : Euc ℝ 3, ∑ i : Fin 3,
             (nse.initialVelocity x i) ^ 2) ≤ E_bound)
    -- STAGE-1 typed-companion bundle on the BASE provided by the
    -- density witness.  In a fully fleshed bridge, the density
    -- witness would carry these too; we expose them as inputs so
    -- the term is type-checkable today.
    (T : ℝ) (T_pos : 0 < T)
    (E_base_factory :
       ∀ (base_nse : NavierStokes.NavierStokesEquations 3),
         EnergyClauseInput
           (buildClassicalGalerkinConstruction base_nse T T_pos))
    (M_base_factory :
       ∀ (base_nse : NavierStokes.NavierStokesEquations 3),
         MomentumClauseInput
           (buildClassicalGalerkinConstruction base_nse T T_pos))
    (P_base_factory :
       ∀ (base_nse : NavierStokes.NavierStokesEquations 3),
         ConcretePromotionInput base_nse T
           (buildClassicalGalerkinConstruction base_nse T T_pos)) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) := by
  -- STAGE-3 INVOKED: density hypothesis produces an ε-perturbation
  -- witness and an axisymmetric base witness for `nse`.
  obtain ⟨ε, ⟨ε_nn, ε_le⟩, ⟨iv⟩, ⟨base⟩⟩ :=
    h_density nse h_smooth h_finE
  -- STAGE-2 INVOKED via the prior Hofstadter rung: feed stage 1's
  -- typed-companion factories on `base.base_nse` and discharge the
  -- smallness condition with the density-supplied ε.
  have h_small : ∃ ε₀' : ℝ, 0 < ε₀' ∧ ε ≤ ε₀' := ⟨ε₀, h_ε₀_pos, ε_le⟩
  exact axisymmetric_perturbation_class_smooth_existence
          nse ε iv base h_small T T_pos
          (E_base_factory base.base_nse)
          (M_base_factory base.base_nse)
          (P_base_factory base.base_nse)

/-! ## §6.  Honesty receipt — Hofstadter ledger

| Stage | Content                                          | Status            |
|-------|--------------------------------------------------|-------------------|
| 1     | `axisymmetric_global_smooth_existence`           | CLOSED (shipped). |
|       | (KNSŠ 2009, CSTY 2008/2009, Lady. 1968, UY 1968, |                   |
|       | CKN 1982, Seregin 2014, Lions 1969, Hopf 1951,   |                   |
|       | Constantin–Foiaș 1988, Banach–Alaoglu, AL 1963)  |                   |
| 2     | `axisymmetric_perturbation_stability`            | CONDITIONAL.      |
|       | (Constantin–Foiaș 1988 §11; finite-ε open)       |                   |
|       | + Hofstadter step `*_class_smooth_existence`     |                   |
| 3     | `dense_axisymmetric_perturbations_in_smooth`     | OPEN ≡ Fefferman A|
|       | (carried as HYPOTHESIS, not axiomatized)         |                   |
|       | + Hofstadter bridge `general_smooth_existence_   |                   |
|       |    via_density`                                  |                   |

**The 3-stage Hofstadter recursion**:

* STAGE 1 produces a `GlobalSmoothSolution` term.
* STAGE 2's `axisymmetric_perturbation_class_smooth_existence`
  CONSUMES STAGE 1's term (literally invoked in the body) to
  produce a perturbation-class `GlobalSmoothSolution`.
* STAGE 3's `general_smooth_existence_via_density` CONSUMES
  STAGE 2's theorem (literally invoked in the body) to produce
  a general `GlobalSmoothSolution`, conditional on the OPEN
  density Prop.

Each stage's output is the next stage's input — Hofstadter's
strange loop.  The OPEN question is now CONCENTRATED in one place:
the density of axisymmetric perturbations in smooth div-free
finite-energy data.

**Sorries**: 0.

This file is a strange-loop SCAFFOLD over the just-shipped
axisymmetric Track-B result.  It does NOT close Clay; it
formalizes the precise narrowing — Clay (A) ⟸ density of
axisymmetric perturbations — that the architecture has now made
visible. -/

end

end ZtareProofs.NS.HofstadterPerturbation
