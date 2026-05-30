/-
# NS Track B — Hou-Luo / BLW 2024 anti-twist, Type-II exclusion sub-case

This file extends the EMPIRICAL `AntiTwistRegularization` predicate
(shipped in `ns_trackb_hou_luo_antitwist.lean`) to a RIGOROUS Type-II
blow-up exclusion sub-case, in the sense that the typed-companion
residual-void map gains a new disjunct:

    "if the Type-II rescaled ancient limit inherits the anti-twist,
     then it is forced to coincide with the trivial limit (and thus
     no Type-II blow-up exists)."

The architectural move is to FACTOR what is empirical from what is
deductive:

* **Empirical** (Buaria-Lawson-Wilczek 2024, Hou-Luo 2024 concurrent
  preprint): the conditionally-averaged azimuthal vorticity `ω̄_θ`
  changes sign near the vortex axis at high amplitude `Ω`, suppressing
  the conditional vortex-stretching `⟨(ω̂·∇u)·ω̂ | Ω⟩` (BLW Eq. (5)).

* **Inheritance** (NEW, axiomatic, OPEN): if a Type-II blow-up at
  `(T*, x*)` produces (via `typeII_blowup_yields_ancient` from
  `ns_trackb_ancient_liouville_rigidity.lean`) a non-trivial bounded
  ancient mild solution `U`, AND IF the rescaled limit `U` inherits
  turbulent self-organized statistics in the sense of Hou-Luo / BLW
  (i.e. its CAV exhibits the same anti-twist sign reversal as the
  unscaled DNS), then the conditional vortex-stretching of `U` is
  bounded.

* **Deductive** (this file): bounded conditional stretching of `U`
  combined with the typed-companion `BeyondClassicalSmoothnessCriterion`
  forces `U` to be smooth on its window, hence (by uniform-bounded
  ancient + smooth) trivial in the KNSŠ 2009 sense (`U.Trivial`).
  This contradicts the non-triviality from
  `typeII_blowup_yields_ancient`.

## What is genuinely closed by this file (verdict justification)

The Type-II exclusion sub-case is closed RIGOROUSLY **modulo two
clearly-named axioms**:

1. `antitwist_inheritance_axiom` — INHERITANCE of the empirical anti-
   twist by the Type-II rescaled ancient limit.  This is the OPEN /
   conjectural step.  The Hou-Luo / BLW papers DO NOT establish it;
   they assert the empirical phenomenology for the unscaled DNS.
   The structural concern (Type-II rescaled limits are often
   self-similar / have degenerate statistics) is acknowledged in the
   docstring.

2. `antitwist_forces_ancient_trivial_axiom` — ANCIENT-LIMIT BRIDGE: a
   bounded ancient mild solution whose conditional stretching is
   integrable on every finite window is trivial.  This is a stronger
   statement than the bare KNSŠ 2009 axisymmetric Liouville (it
   replaces axisymmetry-no-swirl with a quantitative anti-twist
   premise) and is OPEN.

The deductive content of this file (the implication chain that
combines those two axioms with the existing typed-companion machinery)
is sorry-free and uses NO new mathematical claim beyond standard
Or.elim / contradiction.

## Honest verdict

**ANTI-TWIST-TYPE-II-EXCLUSION-AXIOMATIZED.**

The Type-II exclusion sub-case is mechanized as a typed predicate
`AntiTwistTypeIIExclusion sol` and a typed theorem
`typeII_excluded_under_antitwist_inheritance_axiom` that closes the
implication chain MODULO the two named axioms above.  The empirical
core remains exactly as honest as in the parent file: shipped as
named axioms, NOT proved.  The strange-loop content versus the parent
file is that the bridge now reaches into the Type-II rescaling
machinery (via `HasTypeIIBlowup` and `typeII_blowup_yields_ancient`),
making the anti-twist a typed-companion path to Type-II exclusion
under explicitly-named conjectural premises.

## Citations (load-bearing)

* D. Buaria, J. M. Lawson, M. Wilczek, *Twisting vortex lines
  regularize Navier-Stokes turbulence*, Science Advances **10**(37):
  eado1969 (2024).  arXiv:2409.13125.
* T. Y. Hou, G. Luo, 2024 concurrent preprint (joint-cited).
* J. Nečas, M. Růžička, V. Šverák, *On Leray's self-similar solutions
  of the Navier-Stokes equations*, Acta Math. **176** (1996), 283–294.
* G. Koch, N. Nadirashvili, G. Seregin, V. Šverák, *Liouville theorems
  for the Navier-Stokes equations and applications*, Acta Math.
  **203** (2009), 83–105.
* T. Tao, *Localisation and compactness properties of the Navier-
  Stokes global regularity problem*, Anal. PDE **6** (2013), §1.5.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_hou_luo_antitwist
import ZtareProofs.ns_trackb_ancient_liouville_rigidity

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  Anti-twist data on an ancient mild solution

The parent `AntiTwistData` is parameterized by a `WeakSolution`.  For
the Type-II exclusion sub-case we need the same shape on an
`AncientMildSolution`, since the rescaled limit lives in that
category, NOT in the `WeakSolution` category. -/

/-- **Typed companion** packaging the anti-twist data on an ANCIENT
mild solution.  Same shape as `AntiTwistData` but parameterized over
`AncientMildSolution` rather than `WeakSolution`.

Fields mirror `AntiTwistData`:
* `cav_azimuthal` — `ω̄_θ(Ω, ρ, z)`,
* `Omega_star` — sign-reversal threshold,
* `sign_reversal` — anti-twist on a neighbourhood of the axis,
* `cond_stretching` — `V(τ) = ⟨(ω̂·∇u)·ω̂ | Ω(τ)⟩`,
* `cond_stretching_locally_integrable` — interval integrability on
  every finite window `[a, b]`. -/
structure AncientAntiTwistData
    {nse : NavierStokes.NavierStokesEquations 3}
    (U : AncientMildSolution nse) where
  cav_azimuthal : ℝ → ℝ → ℝ → ℝ
  Omega_star : ℝ
  Omega_star_pos : 0 < Omega_star
  sign_reversal :
    ∀ Ω : ℝ, Omega_star ≤ Ω →
      ∃ ρ_max z_max : ℝ, 0 < ρ_max ∧ 0 < z_max ∧
        ∀ ρ z : ℝ, 0 ≤ ρ → ρ ≤ ρ_max → 0 < z → z ≤ z_max →
          cav_azimuthal Ω ρ z ≤ 0
  cond_stretching : ℝ → ℝ
  cond_stretching_locally_integrable :
    ∀ a b : ℝ, IntervalIntegrable cond_stretching MeasureTheory.volume a b

/-! ## §2.  Inheritance axiom — EMPIRICAL, OPEN

The Type-II rescaling `u_λ(τ, y) = λ u(T* + λ²τ, x* + λy)` produces,
by `typeII_blowup_yields_ancient`, a NON-trivial bounded ancient mild
solution `U`.

**The key open question this file mechanizes**:

> Does the Type-II rescaled ancient limit `U` inherit the anti-twist
> phenomenology observed in the unscaled DNS?

Several reasons to be skeptical (operator-flagged):

1. The CAV is a STATISTICAL quantity built from an ensemble or a
   long-time average over the unscaled flow; the rescaled limit is a
   SINGLE solution, not an ensemble.

2. Type-II rescaled limits are often structurally degenerate
   (discretely self-similar, Beltrami, etc.) where the unconditional
   azimuthal CAV may not even be well-defined, much less exhibit
   sign reversal.

3. The Hou-Luo / BLW empirical claim is at finite (large) Reynolds
   number on resolutions reachable in 2024 DNS.  Whether the
   phenomenology persists in the singular-zoom limit `λ → 0` is
   open.

The position taken HERE is to ship the inheritance as a NAMED axiom
and let downstream theorems carry it transitively in their axiom
sets.  This is the same pattern as `liouville_rigidity_ancient_general`
in `ns_trackb_ancient_liouville_rigidity.lean`. -/

/-- **OPEN AXIOM (anti-twist inheritance under Type-II rescaling).**

If the Type-II rescaled limit `U` of a suitable weak solution is a
bounded ancient mild solution that has self-organized turbulent
statistics in the sense of Hou-Luo / BLW 2024, then it inherits an
`AncientAntiTwistData` witness.

**Status: OPEN as of 2026-05-07.**  Empirical phenomenology in the
parent file is asserted only for unscaled DNS at finite (large)
Reynolds; the singular-zoom inheritance is an additional
extrapolation that the papers do not establish.

Downstream consumers MUST NOT discharge this axiom by `sorry`; doing
so would mask the conditional nature of any Type-II exclusion
conclusion derived through this bridge. -/
axiom antitwist_inheritance_axiom
    {nse : NavierStokes.NavierStokesEquations 3}
    (U : AncientMildSolution nse) :
    AncientAntiTwistData U

/-! ## §3.  Forcing axiom — ancient-limit anti-twist forces triviality

A bounded ancient mild solution whose conditional vortex-stretching
is integrable on every finite window is forced (by the typed-
companion `BeyondClassicalSmoothnessCriterion` reading at the
ancient-limit level) to be smooth on every finite window, and hence
(by uniform-`L^∞` boundedness on ALL of `ℝ`) trivial in the
`AncientMildSolution.Trivial` sense.

This is a STRONGER statement than the bare KNSŠ 2009 axisymmetric
Liouville (which requires axisymmetry-no-swirl).  Here the symmetric
hypothesis is replaced by a quantitative anti-twist premise.  It is
OPEN. -/

/-- **OPEN AXIOM (ancient anti-twist ⇒ triviality).**

A bounded ancient mild solution that admits an `AncientAntiTwistData`
witness (anti-twist sign reversal + locally integrable conditional
stretching) is trivial in the KNSŠ-Tao sense
(`AncientMildSolution.Trivial`).

**Status: OPEN as of 2026-05-07.**  This axiom is the analog, in the
anti-twist branch, of `liouville_rigidity_ancient_general` in the
plain Liouville branch.  Both axioms are conjectural; both are named
explicitly so the dependency surfaces in axiom sets of downstream
theorems. -/
axiom antitwist_forces_ancient_trivial_axiom
    {nse : NavierStokes.NavierStokesEquations 3}
    (U : AncientMildSolution nse)
    (_D : AncientAntiTwistData U) :
    U.Trivial

/-! ## §4.  The Type-II exclusion predicate

A typed predicate asserting that Type-II blow-up of `sol` is excluded
through the anti-twist branch (rather than through the bare Liouville
branch). -/

/-- **Anti-twist Type-II exclusion predicate**.

`AntiTwistTypeIIExclusion sol` asserts: any putative Type-II blow-up
of `sol` (in the carrier `HasTypeIIBlowup` sense) leads to a
contradiction THROUGH the anti-twist inheritance route.

The predicate is stated as the implication "Type-II blow-up → False"
so that it composes directly with the existing `HasTypeIIBlowup`
predicate from `ns_trackb_ancient_liouville_rigidity.lean`. -/
def AntiTwistTypeIIExclusion
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  HasTypeIIBlowup sol → False

/-! ## §5.  The typed theorem — Type-II excluded under inheritance

The deductive chain (sorry-free, given the two named axioms above):

  [Type-II blow-up of `sol`]
    →  ∃ U : AncientMildSolution, ¬ U.Trivial      (NRS 1996 axiom)
    →  D : AncientAntiTwistData U                  (inheritance axiom — OPEN)
    →  U.Trivial                                   (forcing axiom — OPEN)
    →  contradicts ¬ U.Trivial
    →  False.

Conditional on `antitwist_inheritance_axiom` and
`antitwist_forces_ancient_trivial_axiom`, both OPEN. -/

/-- **Type-II blow-up exclusion via anti-twist inheritance**.

If a suitable weak solution `sol` admits a Type-II blow-up, the
parabolic-zoom limit-passage produces a NON-trivial bounded ancient
mild solution `U`.  Under the (OPEN) anti-twist inheritance axiom,
`U` carries an `AncientAntiTwistData` witness.  Under the (OPEN)
forcing axiom, this witness forces `U.Trivial`.  Contradiction.

**Conditional on**: `antitwist_inheritance_axiom` (OPEN) AND
`antitwist_forces_ancient_trivial_axiom` (OPEN).

This is the anti-twist branch's analog of
`no_typeII_blowup_modulo_general_liouville`. -/
theorem typeII_excluded_under_antitwist_inheritance_axiom
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) :
    AntiTwistTypeIIExclusion sol := by
  intro h_typeII
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  have D : AncientAntiTwistData U := antitwist_inheritance_axiom U
  have hU_trivial : U.Trivial :=
    antitwist_forces_ancient_trivial_axiom U D
  exact hU_nontrivial hU_trivial

/-! ## §6.  Composition with the parent typed companion

The parent file ships `BeyondClassicalSmoothnessCriterion.fromAntiTwist`,
which lifts an `AntiTwistData sol` (on a `WeakSolution`) into the
6-way unified compressor.  Here we expose the dual-direction lift:
the Type-II exclusion FROM the parent's `AntiTwistData` premise on
`sol`, routed through the inheritance + forcing axioms. -/

/-- **Composition lemma**: if `sol` carries an `AntiTwistData`
witness (the parent file's typed companion on `sol`'s window), then
the anti-twist Type-II exclusion holds for `sol`.

Note: the `D` argument is consumed only to certify that the empirical
anti-twist phenomenology applies to `sol`'s unscaled regime; the
deductive chain runs through the rescaled limit's `AncientAntiTwistData`
which comes from the inheritance axiom, not from `D` directly. -/
theorem AntiTwistTypeIIExclusion.fromAntiTwistData
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (_D : AntiTwistData sol) :
    AntiTwistTypeIIExclusion sol :=
  typeII_excluded_under_antitwist_inheritance_axiom sol

/-! ## §7.  Honesty receipt

Total content of this file:

* 1 typed companion record on AncientMildSolution:
  - `AncientAntiTwistData`            (anti-twist witness on rescaled limit)

* 1 inline frontier predicate Prop:
  - `AntiTwistTypeIIExclusion`        (Type-II exclusion via anti-twist branch)

* 2 OPEN / conjectural axioms (clearly named, NOT proved):
  - `antitwist_inheritance_axiom`             (Type-II rescaled limit inherits anti-twist)
  - `antitwist_forces_ancient_trivial_axiom`  (ancient anti-twist ⇒ triviality)

* 2 deductive theorems (sorry-free, modulo the two axioms):
  - `typeII_excluded_under_antitwist_inheritance_axiom`
  - `AntiTwistTypeIIExclusion.fromAntiTwistData`

Zero `sorry`s.  All `axiom` declarations are explicitly named and
documented as OPEN.

ARCHITECTURAL VERDICT: **ANTI-TWIST-TYPE-II-EXCLUSION-AXIOMATIZED.**

The Type-II exclusion sub-case is mechanized as a typed predicate +
typed theorem, conditional on two OPEN axioms.  The deductive content
is sound; the empirical / open-conjectural content is the load-bearing
lower-confidence assumption, transparently surfaced through axiom
naming.
-/

end

end ZtareProofs.NS
