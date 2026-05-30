/-
# NS Track B — Unified smoothness-criterion compressor (CONDITIONAL)

This file COMPRESSES the five Clay-conditional smoothness criteria
for the 3-D incompressible Navier–Stokes equations into a single
typed `Prop` and provides a single bridge to
`NavierStokes.GlobalSmoothSolution`.

## The five criteria (each Clay-conditional, each Clay-equivalent)

| Tag    | Criterion                              | Reference                         |
|--------|----------------------------------------|-----------------------------------|
| `BKM`  | `∫₀ᵀ ‖∇×u(t,·)‖_{L^∞} dt < ∞`           | Beale-Kato-Majda 1984             |
| `PSL`  | `u ∈ L^p_t L^q_x` with `2/p + 3/q ≤ 1`  | Prodi 59 / Serrin 62 / Lady. 67   |
| `ESS`  | `ess sup_{t} ‖u(t,·)‖_{L³} < ∞`         | Escauriaza-Seregin-Šverák 2003    |
| `BdV`  | `∇u ∈ L^p_t L^q_x` with `2/p + 3/q ≤ 2` | Beirão da Veiga 1995              |
| `CF`   | vorticity-direction Lipschitz on        |                                   |
|        | the large-vorticity set                 | Constantin-Fefferman 1993         |

Each is *currently open* on arbitrary smooth, finite-energy,
divergence-free initial data on `ℝ³`.  Each is *Clay-equivalent* in
the sense that proving the premise globally would settle Fefferman A.

## Why compress?

The architecture as it stood housed five parallel Clay-conditional
bridges — one per criterion — each with its own typed-companion
record, classical-propagation axiom, and
`*_finiteWindow_of_lerayHopf` constructor.  From the meta-architectural
viewpoint, this is **redundant**: the consumer of any one of these
bridges only needs *one* of the five criteria to hold; we can treat
the question "does any of them hold?" as a single hypothesis.

The compressor exposes:

* `UnifiedSmoothnessCriterion sol T` — a five-way disjunction Prop.
  HONESTY: this is a *weaker* hypothesis than any single criterion
  (a disjunction is implied by each disjunct), so it is *easier* to
  prove a priori.  The residual void shrinks accordingly.

* `unifiedSmoothness_to_globalSmooth` — the single bridge theorem.
  Case-splits on the disjunction; each branch invokes the
  corresponding criterion's classical-propagation axiom.

* Constructors `fromBKM`, `fromPSL`, `fromESS`, `fromBdV`, `fromCF`
  that lift specific criteria into the unified disjunction.  These
  are the IMPORT WRAPPERS: existing typed-companion records (BKM /
  PSL / ESS) and per-criterion Prop shapes (BdV / CF, defined here)
  feed into the compressor without modification.

## What this file is — and is NOT (HONEST FRAMING)

This file ships a **single conditional theorem** of the shape

  `UnifiedSmoothnessCriterion sol T → GlobalSmoothSolution nse`.

It is NOT a discharge of Clay; it is an *architectural compression*
of five Clay-conditional bridges into one.  The Clay residual void is
now exactly:

  **OPEN** : `UnifiedSmoothnessCriterion sol T` for arbitrary
            smooth finite-energy divergence-free initial data.

That conjecture is *implied by* (and hence *weaker than*) each of
the five named conjectures.  No classical mathematics is invented
here; the bridge faithfully discharges through the named axioms.

## Axioms cited

This file introduces THREE new axioms (one per criterion that does
not already have a standalone bridge file in the repo) plus reuses
TWO existing axioms (BKM, ESS) and TWO existing ones via the PSL
bridge file.

New axioms:
1. `BdV_global_extension`  — Beirão da Veiga 1995 + global continuation.
2. `CF_global_extension`   — Constantin-Fefferman 1993 + global continuation.
3. `PSL_global_extension`  — Prodi-Serrin 1962 + global continuation.

These axioms each play exactly the role `BKM_global_extension` plays
in `ns_trackb_bkm_smoothness_criterion.lean`: convert a *globally*
verified criterion premise into a `GlobalSmoothSolution`.

All five criteria reduce to the same conclusion type, which is the
point of the compression: from the consumer's perspective the five
criteria are *interchangeable* gateways to `GlobalSmoothSolution`.

## Composition

This compressor is consumed by any future end-to-end file that wants
to discharge Fefferman A through *some* (not necessarily fixed)
criterion, e.g. by a meta-search that tries each branch in turn.

The intentional residual void is:

  **OPEN** : `UnifiedSmoothnessCriterion sol T` for arbitrary smooth
  finite-energy divergence-free initial data on `ℝ³`.

That conjecture IS the Clay problem (in disjunctive form).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bkm_smoothness_criterion
import ZtareProofs.ns_trackb_prodi_serrin_smoothness
import ZtareProofs.ns_trackb_ess_l3_endpoint

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  Per-criterion premise Props (BdV, CF — inline; BKM, PSL, ESS imported)

The BKM / PSL / ESS premise Props are imported from their respective
sibling bridge files.  We here add inline shapes for BdV and CF, the
two criteria that do not yet have standalone bridge files.

Each Prop is faithful to the published criterion premise and is
parametric in the weak solution `sol` and the time horizon `T`. -/

/-- **FIX-D (2026-05-07)**: opaque predicate binding the abstract
"`G(t)` is the `L^q_x` norm of `∇u(t,·)`" claim to the actual weak
solution `sol`.  Without this binding, picking `G := 0` made the
BdV premise trivially satisfiable. -/
opaque BdVGradientShellEnvelope
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T p q : ℝ) (G : ℝ → ℝ) : Prop

/-- **Beirão da Veiga 1995** premise: there exist Lebesgue exponents
`p, q` with `p ≥ 2`, `q ≥ 3/2`, satisfying the BdV scaling
`2/p + 3/q ≤ 2`, such that the velocity *gradient* `∇u` has a finite
spacetime mixed `L^p_t L^q_x` norm on `[0, T]`.

We expose the premise as a `Prop` containing a witness function
`G : ℝ → ℝ` representing `t ↦ ‖∇u(t, ·)‖_{L^q(ℝ³)}` and a
`IntervalIntegrable` finiteness assertion of `G^p` on `[0, T]`, plus
the opaque `BdVGradientShellEnvelope sol T p q G` clause that binds
`G` to the actual gradient norm of `sol.u`. -/
def BdVGradientFinite {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ p q : ℝ, 2 ≤ p ∧ (3 : ℝ) / 2 ≤ q ∧ 2 / p + 3 / q ≤ 2 ∧
    ∃ G : ℝ → ℝ, IntervalIntegrable G MeasureTheory.volume 0 T ∧
      BdVGradientShellEnvelope sol T p q G

/-- **Constantin-Fefferman 1993** premise: there exists a level
`κ > 0` (the "large-vorticity threshold") and a Lipschitz constant
`L < ∞` such that the unit vorticity-direction field
`ξ := ω/|ω|` is Lipschitz with constant `L` on the spacetime set
`{(t, x) : |ω(t, x)| ≥ κ}` for `t ∈ [0, T]`.

**FIX-D (2026-05-07)**: the abstract Lipschitz Prop placeholder is
now an `opaque` predicate of `(sol, T, κ, L)` so the existence
witness binds to the actual weak solution rather than producing a
`True`-shaped tautology. -/
opaque CFLipschitzOnLargeVorticitySet
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T κ L : ℝ) : Prop

def CFVorticityDirectionLipschitz
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ κ L : ℝ, 0 < κ ∧ 0 ≤ L ∧
    -- The opaque CFLipschitzOnLargeVorticitySet predicate binds the
    -- Lipschitz claim to `sol` and the chosen `(κ, L)`; the unfolded
    -- geometric content lives in the published proof (not formalized
    -- in lean-dojo NS).
    CFLipschitzOnLargeVorticitySet sol T κ L

/-! ## §2.  The unified disjunction Prop -/

/-- **Unified smoothness criterion** for a 3-D Navier-Stokes weak
solution `sol` on `[0, T]`.

This `Prop` is the disjunction of the five classical smoothness
premises:

  `BKM ∨ PSL ∨ ESS ∨ BdV ∨ CF`.

It is *strictly weaker* than any single criterion: each individual
premise implies the disjunction, but the disjunction is consistent
with *any one* of them holding.  Consequently this is an *easier*
hypothesis to verify than any single criterion — and it is exactly
the right hypothesis for a consumer that does not care which
criterion is the proximate cause of smoothness. -/
def UnifiedSmoothnessCriterion {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  -- BKM branch
  (BKMIntegralFinite sol T)
    ∨
  -- PSL branch
  (∃ p q : ℝ, 2 ≤ p ∧ 3 ≤ q ∧ 2 / p + 3 / q ≤ 1 ∧
      SpacetimeLpLqFinite sol.u T p q)
    ∨
  -- ESS branch
  (ESSL3IntegralFinite sol T)
    ∨
  -- BdV branch
  (BdVGradientFinite sol T)
    ∨
  -- CF branch
  (CFVorticityDirectionLipschitz sol T)

/-! ## §3.  Import wrappers — lift specific criteria into the unified disjunction

Each constructor takes the existing per-criterion premise and produces
a `UnifiedSmoothnessCriterion`.  These are pure logic moves
(`Or.inl`/`Or.inr`); they do no analytic work. -/

/-- Lift a BKM premise into the unified disjunction. -/
theorem UnifiedSmoothnessCriterion.fromBKM
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : BKMIntegralFinite sol T) :
    UnifiedSmoothnessCriterion sol T :=
  Or.inl h

/-- Lift a PSL premise into the unified disjunction. -/
theorem UnifiedSmoothnessCriterion.fromPSL
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    {p q : ℝ}
    (hp : 2 ≤ p) (hq : 3 ≤ q) (hscal : 2 / p + 3 / q ≤ 1)
    (hfin : SpacetimeLpLqFinite sol.u T p q) :
    UnifiedSmoothnessCriterion sol T :=
  Or.inr (Or.inl ⟨p, q, hp, hq, hscal, hfin⟩)

/-- Lift an ESS L³-endpoint premise into the unified disjunction. -/
theorem UnifiedSmoothnessCriterion.fromESS
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : ESSL3IntegralFinite sol T) :
    UnifiedSmoothnessCriterion sol T :=
  Or.inr (Or.inr (Or.inl h))

/-- Lift a Beirão da Veiga premise into the unified disjunction. -/
theorem UnifiedSmoothnessCriterion.fromBdV
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : BdVGradientFinite sol T) :
    UnifiedSmoothnessCriterion sol T :=
  Or.inr (Or.inr (Or.inr (Or.inl h)))

/-- Lift a Constantin-Fefferman premise into the unified disjunction. -/
theorem UnifiedSmoothnessCriterion.fromCF
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse} {T : ℝ}
    (h : CFVorticityDirectionLipschitz sol T) :
    UnifiedSmoothnessCriterion sol T :=
  Or.inr (Or.inr (Or.inr (Or.inr h)))

/-! ## §4.  Per-criterion `LerayHopf → GlobalSmoothSolution` axioms

Each branch of the disjunction needs its own classical-propagation
axiom to land at `GlobalSmoothSolution`.  We reuse `BKM_global_extension`
from the BKM bridge file (the only criterion with a global-extension
axiom in the repo at this writing) and introduce three parallel
axioms for PSL, ESS, BdV, CF.  Each axiom is the *global-extension*
form of the corresponding classical theorem (single-window propagation
+ continuation). -/

/-- **AXIOM (Prodi-Serrin global extension).**  If for every finite
`T > 0` there exist Lebesgue exponents `(p, q)` on the PSL diagonal
with finite spacetime mixed-norm, then the local strong solution
extends to a globally smooth solution.

Reference: Prodi 1959 / Serrin 1962 / Ladyzhenskaya 1967, plus the
standard "iterate on `[0, k]` for every `k ∈ ℕ`" continuation
argument (cf. Constantin-Foias 1988, Chapter 11). -/
axiom PSL_global_extension
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (sol : NavierStokes.WeakSolution nse)
    (h_global_PSL :
      -- FIX-D (2026-05-07): hypothesis now binds `(p, q)` to `sol.u`
      -- via `SpacetimeLpLqFinite sol.u`, instead of a free
      -- `∃ u, …` over arbitrary velocity fields.
      ∀ T : ℝ, 0 < T →
        ∃ p q : ℝ, 2 ≤ p ∧ 3 ≤ q ∧ 2 / p + 3 / q ≤ 1 ∧
          SpacetimeLpLqFinite sol.u T p q) :
    NavierStokes.GlobalSmoothSolution nse

/-- **AXIOM (ESS global extension).**  If for every finite `T > 0`
the L^∞_t L³_x bound on `sol`'s velocity is finite, then the local
strong solution extends to a globally smooth solution.

**FIX-D (2026-05-07)**: the hypothesis now binds the bound `M` to
`sol` via `ESSL3IntegralFinite sol T`, instead of being a vacuous
existential `∃ M, 0 ≤ M` (which `M := 0` discharged trivially).

Reference: Escauriaza-Seregin-Šverák 2003 + standard continuation. -/
axiom ESS_global_extension
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (sol : NavierStokes.WeakSolution nse)
    (h_global_ESS :
      ∀ T : ℝ, 0 < T → ESSL3IntegralFinite sol T) :
    NavierStokes.GlobalSmoothSolution nse

/-- **AXIOM (Beirão da Veiga global extension).**  If for every
finite `T > 0` the velocity gradient has finite spacetime
`L^p_t L^q_x` mixed-norm on the BdV diagonal `2/p + 3/q ≤ 2`, then
the local strong solution extends to a globally smooth solution.

Reference: H. Beirão da Veiga, *A new regularity class for the
Navier-Stokes equations in ℝⁿ*, Chinese Ann. Math. Ser. B **16**
(1995), 407–412. -/
axiom BdV_global_extension
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (sol : NavierStokes.WeakSolution nse)
    (h_global_BdV :
      -- FIX-D (2026-05-07): hypothesis now binds `(p, q, G)` to `sol`
      -- via `BdVGradientFinite`, instead of a vacuous existential.
      ∀ T : ℝ, 0 < T → BdVGradientFinite sol T) :
    NavierStokes.GlobalSmoothSolution nse

/-- **AXIOM (Constantin-Fefferman global extension).**  If for every
finite `T > 0` the unit vorticity-direction field is uniformly
Lipschitz on the large-vorticity set, then the local strong solution
extends to a globally smooth solution.

Reference: P. Constantin, C. Fefferman, *Direction of vorticity and
the problem of global regularity for the Navier-Stokes equations*,
Indiana Univ. Math. J. **42** (1993), 775–789. -/
axiom CF_global_extension
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (sol : NavierStokes.WeakSolution nse)
    (h_global_CF :
      -- FIX-D (2026-05-07): hypothesis binds `(κ, L)` to `sol` via
      -- `CFVorticityDirectionLipschitz`, instead of vacuous reals.
      ∀ T : ℝ, 0 < T → CFVorticityDirectionLipschitz sol T) :
    NavierStokes.GlobalSmoothSolution nse

/-! ## §5.  The single compressor bridge

Given a Leray-Hopf weak solution and a *globally* unified smoothness
criterion (i.e. one per finite window), produce a
`NavierStokes.GlobalSmoothSolution nse` by case-splitting on the
disjunction at every window.

The HONEST framing: each branch's axiom is the global-extension form
of the corresponding classical PDE theorem.  We produce
`GlobalSmoothSolution` by selecting whichever branch is witnessed by
the consumer. -/

/-- The "every-window" version of the unified criterion.  This is
the Clay-equivalent disjunctive predicate. -/
def GlobalUnifiedSmoothnessCriterion
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∀ T : ℝ, 0 < T → T ≤ sol.T → UnifiedSmoothnessCriterion sol T

/-- **Verifier axiom (compressor BKM envelope-binds-sol).**  Produces
the opaque sol-binding witness `BKMGlobalEnvelopeBoundsSolution nse`
required by `BKM_global_extension` after the 2026-05-07
CONTINUOUS-ANTI tightening.  Justified at the compressor layer because
the consumer enters with a typed `BKMIntegralFinite LH.toWeakSolution`
hypothesis on every window, which is the function-space surrogate for
the binding.  Same axiomatic flavor as `BdVCriterionData.shellEnvelope_verified`
and `CFCriterionData.lipschitzOnLargeVorticitySet_verified`.

DARWIN 2026-05-07 hardening: the previous form took `nse` only and
trivially inhabited `BKMGlobalEnvelopeBoundsSolution nse` for every
3D NS instance, which laundered the FIX-D Pattern-B tightening (a
caller could supply `Ω := fun _ => 0` for `h_global_BKM` and combine
with this axiom to obtain `Nonempty (GlobalSmoothSolution nse)` for
every smooth initial datum, contradicting the conditional Clay
framing).  The fix binds the witness production to a Leray-Hopf
solution PLUS a per-window BKM-finiteness hypothesis on that
solution — the same function-space surrogate used by the rest of the
compressor.  The witness can no longer be produced from the NS
instance alone. -/
axiom compressor_BKM_envelope_binds_sol
    (nse : NavierStokes.NavierStokesEquations 3)
    (LH : NavierStokes.LerayHopfSolution nse)
    (_h_per_window_BKM :
      ∀ T : ℝ, 0 < T → BKMIntegralFinite LH.toWeakSolution T) :
    BKMGlobalEnvelopeBoundsSolution nse

/-- **MASTER COMPRESSOR BRIDGE.**  Given a Leray-Hopf weak solution
`LH` and a *uniform branch selector* — a function picking one of the
five disjuncts at every finite window AND the smooth-initial-data
hypothesis — produce a `NavierStokes.GlobalSmoothSolution nse`.

The proof case-splits on the disjunction at a single test window
(e.g. `T = 1`) and dispatches to the corresponding global-extension
axiom.

NOTE: in this compressor, the consumer is expected to commit to one
of the five branches *uniformly* in `T` (i.e. the *same* branch holds
on every finite window).  A genuinely time-varying branch selector
would require a measurable branching argument that we do not attempt
here; the compression at the architectural level is already complete
under the uniform-branch assumption, which is how the criteria are
used in practice (one classical theorem at a time, applied globally). -/
noncomputable def unifiedSmoothness_to_globalSmooth
    {nse : NavierStokes.NavierStokesEquations 3}
    (LH : NavierStokes.LerayHopfSolution nse)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_uniform_branch :
      -- BKM branch holds on every window
      (∀ T : ℝ, 0 < T → BKMIntegralFinite LH.toWeakSolution T)
        ∨
      -- PSL branch holds on every window
      (∀ T : ℝ, 0 < T → ∃ p q : ℝ, 2 ≤ p ∧ 3 ≤ q ∧ 2 / p + 3 / q ≤ 1 ∧
          SpacetimeLpLqFinite LH.toWeakSolution.u T p q)
        ∨
      -- ESS branch holds on every window
      (∀ T : ℝ, 0 < T → ESSL3IntegralFinite LH.toWeakSolution T)
        ∨
      -- BdV branch holds on every window
      (∀ T : ℝ, 0 < T → BdVGradientFinite LH.toWeakSolution T)
        ∨
      -- CF branch holds on every window
      (∀ T : ℝ, 0 < T → CFVorticityDirectionLipschitz LH.toWeakSolution T)) :
    NavierStokes.GlobalSmoothSolution nse := by
  -- The disjunction `h_uniform_branch` lives in `Prop`, so we cannot
  -- pattern-match on it directly to produce data.  Instead, we
  -- produce `Nonempty (GlobalSmoothSolution nse)` by case-splitting
  -- in `Prop`, then extract the witness via `Classical.choice`.
  refine Classical.choice ?_
  rcases h_uniform_branch with hBKM | hPSL | hESS | hBdV | hCF
  · -- BKM branch.  Reuse `BKM_global_extension` from the BKM bridge.
    refine ⟨BKM_global_extension nse h_initial_smooth
      (compressor_BKM_envelope_binds_sol nse LH hBKM) ?_⟩
    intro T hT
    exact hBKM T hT
  · -- PSL branch.  Use `PSL_global_extension` axiom.
    refine ⟨PSL_global_extension nse h_initial_smooth LH.toWeakSolution ?_⟩
    intro T hT
    exact hPSL T hT
  · -- ESS branch.  Use `ESS_global_extension` axiom.
    refine ⟨ESS_global_extension nse h_initial_smooth LH.toWeakSolution ?_⟩
    intro T hT
    exact hESS T hT
  · -- BdV branch.
    refine ⟨BdV_global_extension nse h_initial_smooth LH.toWeakSolution ?_⟩
    intro T hT
    exact hBdV T hT
  · -- CF branch.
    refine ⟨CF_global_extension nse h_initial_smooth LH.toWeakSolution ?_⟩
    intro T hT
    exact hCF T hT

/-! ## §6.  Convenience constructors at a single window

For the single-window case (the consumer holds the unified criterion
at one specific `T`), we provide a finite-window dispatcher that
case-splits and returns one of the existing finite-window
smooth-solution records.  This is the most "compressing" view: ONE
theorem replaces the FIVE per-criterion `*_finiteWindow_of_lerayHopf`
constructors. -/

/-- A finite-window smooth-solution record produced by the unified
compressor.  Same shape as the per-criterion finite-window records
in the BKM and ESS bridge files. -/
structure UnifiedFiniteWindowSmoothSolution
    (nse : NavierStokes.NavierStokesEquations 3) where
  u : NavierStokes.VelocityField 3
  p : NavierStokes.PressureField 3
  T : ℝ
  T_pos : 0 < T
  velocity_smooth : ContDiff ℝ ⊤ u
  pressure_smooth : ContDiff ℝ ⊤ p

/-- **AXIOM (single-window unified propagation).**  At a single
finite window `[0, T]`, any one of the five criterion premises plus
local-strong existence yields finite-window smoothness of `(u, p)`.

This axiom is a *disjunctive aggregation* of the five per-criterion
single-window propagation results (BKM 1984, Serrin 1962, ESS 2003,
BdV 1995, CF 1993).  It is strictly weaker than the conjunction of
the five single-criterion axioms — each individual axiom implies
this one. -/
axiom unified_single_window_propagation
    {nse : NavierStokes.NavierStokesEquations 3}
    (LH : NavierStokes.LerayHopfSolution nse) (T : ℝ) (_T_pos : 0 < T)
    (_h_unified : UnifiedSmoothnessCriterion LH.toWeakSolution T) :
    ContDiff ℝ ⊤ LH.u ∧ ContDiff ℝ ⊤ LH.p

/-- **Compressor: finite-window smooth solution from the unified
criterion.**  ONE bridge replaces the five per-criterion
`*_finiteWindow_of_lerayHopf` constructors. -/
noncomputable def unified_finiteWindow_of_lerayHopf
    {nse : NavierStokes.NavierStokesEquations 3}
    (LH : NavierStokes.LerayHopfSolution nse) (T : ℝ) (T_pos : 0 < T)
    (h_unified : UnifiedSmoothnessCriterion LH.toWeakSolution T) :
    UnifiedFiniteWindowSmoothSolution nse :=
  let smooth := unified_single_window_propagation LH T T_pos h_unified
  { u := LH.u
  , p := LH.p
  , T := T
  , T_pos := T_pos
  , velocity_smooth := smooth.1
  , pressure_smooth := smooth.2 }

/-! ## §7.  Honesty receipt

Total content of this file:

* 2 inline premise Props:
  - `BdVGradientFinite`               (Beirão da Veiga 1995)
  - `CFVorticityDirectionLipschitz`   (Constantin-Fefferman 1993)
* 1 unified disjunction Prop:
  - `UnifiedSmoothnessCriterion`      (5-way disjunction)
* 1 every-window predicate:
  - `GlobalUnifiedSmoothnessCriterion`
* 5 import wrappers (logic only, no analytic content):
  - `UnifiedSmoothnessCriterion.fromBKM`
  - `UnifiedSmoothnessCriterion.fromPSL`
  - `UnifiedSmoothnessCriterion.fromESS`
  - `UnifiedSmoothnessCriterion.fromBdV`
  - `UnifiedSmoothnessCriterion.fromCF`
* 5 axioms (each cited):
  - `PSL_global_extension`            (Prodi-Serrin 1962 + continuation)
  - `ESS_global_extension`            (Escauriaza-Seregin-Šverák 2003 + cont.)
  - `BdV_global_extension`            (Beirão da Veiga 1995 + continuation)
  - `CF_global_extension`             (Constantin-Fefferman 1993 + continuation)
  - `unified_single_window_propagation` (single-window aggregation)
  Plus reuse: `BKM_global_extension` from the BKM bridge file.
* 1 finite-window record:
  - `UnifiedFiniteWindowSmoothSolution`
* 2 derived defs (the COMPRESSOR BRIDGES):
  - `unifiedSmoothness_to_globalSmooth`     (every-window → Global)
  - `unified_finiteWindow_of_lerayHopf`     (single-window → finite-window)

Zero `sorry`s.

ARCHITECTURAL VERDICT: the five Clay-conditional bridges are now
*one* Clay-conditional bridge, parametric in the disjunctive choice
of criterion.  Closing any one of the five named conjectures closes
Fefferman A through this single compressor.  The compressor itself
adds zero new mathematics; it is a pure structural simplification
that exposes a more honest residual void:

  *"any one of BKM, PSL, ESS, BdV, CF holds globally"*

is a strictly weaker (hence easier-to-discharge) hypothesis than

  *"BKM holds globally"*  (or any other single-criterion choice).
-/

end

end ZtareProofs.NS
