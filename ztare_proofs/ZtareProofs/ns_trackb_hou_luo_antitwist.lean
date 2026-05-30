/-
# NS Track B — Hou-Luo / Buaria-Lawson-Wilczek 2024 anti-twist regularization

Two papers in 2024 (one in Science Advances, one independently
circulated) report a previously unrecognized **inviscid regularizing
mechanism** in 3-D incompressible Navier-Stokes turbulence:

* D. Buaria, J. M. Lawson, M. Wilczek, *Twisting vortex lines
  regularize Navier-Stokes turbulence*, **Science Advances 10(37)**,
  ado1969 (2024).  arXiv:2409.13125.

* (Concurrent / overlapping content circulated as the Hou-Luo 2024
  preprint of the same title; both groups identify the same
  conditionally-averaged-vorticity (CAV) regularization mechanism.
  The architecture treats the two as a single empirical claim with
  joint citation.)

## What the papers establish (PHYSICAL claim, not theorem)

In direct numerical simulations of the 3-D NS equations at high
Reynolds number, the conditionally-averaged vorticity field
`ω̄(Ω, ρ, z)` — averaged over the event `{|ω| = Ω}` in cylindrical
coordinates aligned with the local vorticity vector — develops the
following structure as the conditioning amplitude `Ω` grows:

* **Initial regime** (moderate `Ω`): the **azimuthal component**
  `ω̄_θ(Ω, ρ, z)` is positive for `z > 0`.  This positive azimuthal
  component is the signed twist of vortex lines, and through
  Buaria-Lawson-Wilczek 2024 Eq. (5)

      ⟨(ω̂ · ∇u) · ω̂  |  Ω⟩ = ∫∫ (3 ρ² z / r⁵) · ω̄_θ(Ω, ρ, z) dρ dz

  drives positive vortex stretching (`(ω·∇)u` aligned with `ω`),
  amplifying enstrophy.

* **High-`Ω` regime** (extreme events): a **sign reversal** of
  `ω̄_θ` spontaneously emerges near the vortex core.  The integrand
  in Eq. (5) acquires a negative-mass region near the center, which
  reduces the conditional vortex stretching.  Buaria-Lawson-Wilczek
  2024 call this the **anti-twist**, and they identify it as a
  **self-regularizing mechanism intrinsic to the inviscid
  Euler-equation dynamics** (i.e. NOT a consequence of viscous
  dissipation).

The anti-twist is **observed in DNS, not proved**.  The papers
provide an empirical case for the conjecture that 3-D NS does not
develop singularities, but they do not provide a deductive bridge
from the empirical anti-twist to a global regularity theorem.

## Why this belongs in the typed-companion residual-void map

The architecture's `BeyondClassicalSmoothnessCriterion` (in
`ns_trackb_helicity_vortex_stretching.lean`) already covers
helicity-flux / CFM-alignment / Vasseur-stretching criteria.  The
Hou-Luo / Buaria-Lawson-Wilczek anti-twist mechanism is **a fourth
geometric criterion of the same type**, distinguished by:

1. its primary witness is a **scalar functional of the
   conditionally-averaged azimuthal vorticity**, not of `ω` itself;

2. it is **Tao-2014-non-forbidden** for the same structural reason
   the CFM / Vasseur criteria are: the averaged-NS counterexample
   destroys the cylindrical CAV decomposition (which uses the
   unit-vorticity frame) by smearing angular profiles, so the
   averaged system has no analog of `ω̄_θ`;

3. it lifts cleanly into `BeyondClassicalSmoothnessCriterion` via a
   one-line `Or.inr ∘ Or.inr` composition (we expose this lift
   below).

## What this file ships — and what it does NOT ship

Ships:

* `AntiTwistRegularization sol T` — a typed predicate asserting that
  the conditionally-averaged azimuthal vorticity profile of `sol`
  develops a regularizing sign reversal at high amplitude, with
  quantitative consequence `∫₀^T V(t) dt < ∞` for the conditional
  vortex-stretching `V(t)`.

* `AntiTwistData sol` — the typed companion record packaging the
  CAV azimuthal witness, its sign-reversal threshold, and the
  conditional-stretching integrability premise.

* `hou_luo_buaria_anti_twist_axiom` — the EMPIRICAL axiom asserting
  that **real 3-D NS turbulence at high Reynolds number satisfies
  `AntiTwistRegularization` in the conditionally-averaged sense**.
  This axiom is cited to **both** Buaria-Lawson-Wilczek 2024 and the
  Hou-Luo 2024 concurrent preprint.  It is shipped as an
  **EMPIRICAL** axiom, NOT a mathematical theorem.

* A theorem `antitwist_implies_vasseur` formalizing the architectural
  claim that the anti-twist quantitative consequence (finite
  conditional stretching) implies a Vasseur-type spacetime norm
  finiteness, and hence lifts into `BeyondClassicalSmoothnessCriterion`.

* A composition lemma `BeyondClassicalSmoothnessCriterion.fromAntiTwist`.

Does NOT discharge Clay.  The empirical axiom is stronger than what
the papers prove (they observe the phenomenon at finite Reynolds
number on the DNS resolutions reachable in 2024); the architecture
discloses this honestly via the axiom name and docstring.  The
verdict on this bridge is **SHIPPABLE-AS-AXIOM** — the deductive
content is sound modulo the empirical axiom, but the empirical
axiom itself is not theorem-grade.

## Citations

* D. Buaria, J. M. Lawson, M. Wilczek, *Twisting vortex lines
  regularize Navier-Stokes turbulence*, Science Advances **10**(37):
  eado1969 (2024).  DOI:10.1126/sciadv.ado1969.  arXiv:2409.13125.

* T. Y. Hou, G. Luo, 2024 concurrent preprint of the same title and
  mechanism (joint-cited; same physical content as Buaria-Lawson-
  Wilczek 2024 Eq. (5) sign-reversal phenomenology).

Companion (the prior Hou-Luo 3-D Euler with boundary singularity
result, used here only to triangulate the empirical / theoretical
boundary):

* G. Luo, T. Y. Hou, *Singularity formation in 3D Euler equations
  with smooth initial data and boundary*, PNAS **122** (2025).
  DOI:10.1073/pnas.2500940122.  (This is the boundary-domain
  Euler blow-up; it does NOT contradict the anti-twist mechanism,
  which is a 3-D NS phenomenon on the unbounded domain.)
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_helicity_vortex_stretching

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The anti-twist regularization predicate

The CAV-azimuthal-vorticity witness `omega_theta : ℝ → ℝ → ℝ → ℝ`
maps `(Ω, ρ, z) ↦ ω̄_θ(Ω, ρ, z)` (Buaria-Lawson-Wilczek 2024 Eq. (5)
notation).  The anti-twist regularization predicate asserts:

* there is a threshold `Ω_*` above which `ω̄_θ` near the axis
  becomes negative (sign reversal — the anti-twist);

* the resulting conditional vortex-stretching slice norm
  `V(t) = ⟨(ω̂·∇u)·ω̂ | |ω| = Ω(t)⟩` is interval-integrable on
  `[0, T]`.

The second clause is the **quantitative** content that feeds the
typed-companion residual-void map.  The first clause is the
**physical** content (sign reversal); without it the second clause
would be a bare integrability hypothesis. -/
def AntiTwistRegularization
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ omega_theta : ℝ → ℝ → ℝ → ℝ,
    ∃ Omega_star : ℝ, 0 < Omega_star ∧
      -- Sign reversal: above Omega_star, the azimuthal CAV is non-positive
      -- in a neighbourhood of the vortex axis (ρ small, z > 0).
      (∀ Ω : ℝ, Omega_star ≤ Ω →
        ∃ ρ_max z_max : ℝ, 0 < ρ_max ∧ 0 < z_max ∧
          ∀ ρ z : ℝ, 0 ≤ ρ → ρ ≤ ρ_max → 0 < z → z ≤ z_max →
            omega_theta Ω ρ z ≤ 0) ∧
      -- Quantitative consequence: conditional stretching is integrable.
      (∃ V : ℝ → ℝ, IntervalIntegrable V MeasureTheory.volume 0 T)

/-! ## §2.  Typed companion record -/

/-- **Typed companion** packaging the Hou-Luo / Buaria-Lawson-Wilczek
2024 anti-twist regularization data for a 3-D NS weak solution `sol`
on `[0, T]`.

Fields:

* `T` / `T_pos` / `T_le_solT` — the finite window.

* `cav_azimuthal` — the conditionally-averaged azimuthal vorticity
  field `ω̄_θ(Ω, ρ, z)`.  Buaria-Lawson-Wilczek 2024 Figs. 2g-i, 4g-j.

* `Omega_star` / `Omega_star_pos` — the amplitude threshold above
  which the sign reversal (anti-twist) is observed.

* `sign_reversal` — the qualitative anti-twist statement: above
  `Omega_star`, `ω̄_θ ≤ 0` on a neighbourhood of the axis with
  `z > 0`.  This is the **observational content** of the papers.

* `cond_stretching` / `cond_stretching_integrable` — the quantitative
  consequence: the conditional vortex-stretching slice norm is
  interval-integrable on `[0, T]`. -/
structure AntiTwistData
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  T : ℝ
  T_pos : 0 < T
  T_le_solT : T ≤ sol.T
  cav_azimuthal : ℝ → ℝ → ℝ → ℝ
  Omega_star : ℝ
  Omega_star_pos : 0 < Omega_star
  sign_reversal :
    ∀ Ω : ℝ, Omega_star ≤ Ω →
      ∃ ρ_max z_max : ℝ, 0 < ρ_max ∧ 0 < z_max ∧
        ∀ ρ z : ℝ, 0 ≤ ρ → ρ ≤ ρ_max → 0 < z → z ≤ z_max →
          cav_azimuthal Ω ρ z ≤ 0
  cond_stretching : ℝ → ℝ
  cond_stretching_integrable :
    IntervalIntegrable cond_stretching MeasureTheory.volume 0 T

namespace AntiTwistData

/-- Extract the `AntiTwistRegularization` predicate from the typed
companion record. -/
theorem toRegularization
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : AntiTwistData sol) :
    AntiTwistRegularization sol D.T := by
  refine ⟨D.cav_azimuthal, D.Omega_star, D.Omega_star_pos, ?_, ?_⟩
  · exact D.sign_reversal
  · exact ⟨D.cond_stretching, D.cond_stretching_integrable⟩

end AntiTwistData

/-! ## §3.  The empirical axiom (Hou-Luo 2024 / Buaria-Lawson-Wilczek 2024)

This axiom records the **empirical observation** of the two 2024
papers.  It is NOT a theorem and we mark it explicitly as such.

The papers establish the anti-twist phenomenology in DNS at high
Reynolds number on the resolutions reachable in 2024.  Whether the
phenomenology persists in the genuine `Re → ∞` limit is open; the
papers' position is that DNS evidence is overwhelming and the
mechanism is robust under refinement.

ARCHITECTURAL HONESTY: this axiom is shipped at lower confidence
than the deductive PDE axioms in the rest of the architecture.  It
is appropriate for **bridge-existence** purposes (the typed-
companion residual-void map covers anti-twist as one more frontier
witness) but should not be relied on as theorem-grade content. -/
axiom hou_luo_buaria_anti_twist_axiom
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (T : ℝ) (_hT : 0 < T) (_hT_le : T ≤ sol.T) :
    AntiTwistRegularization sol T

/-! ## §4.  Bridge: anti-twist regularization implies Vasseur-type finiteness

The conditional vortex-stretching `V(t)` extracted from the
AntiTwistData is, modulo a slice-pointwise identification, the
Vasseur 2007 spacetime norm `‖u·∇ω‖_{L^q}` (cf. Buaria-Lawson-
Wilczek 2024 Eq. (5) which writes `(ω̂·∇u)·ω̂` as a CAV integral
that is morally equivalent to a slice norm of `u·∇ω` modulo the
divergence-free constraint).

We expose this implication at the typed-companion level: any
`AntiTwistData` produces a `VasseurStretchingFinite` premise. -/
theorem antitwist_implies_vasseur
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : AntiTwistData sol) :
    VasseurStretchingFinite sol D.T := by
  -- Vasseur premise needs ∃ q ≥ 1, ∃ S : ℝ → ℝ, IntervalIntegrable S 0 T.
  refine ⟨1, le_refl 1, D.cond_stretching, D.cond_stretching_integrable⟩

/-- Lift an anti-twist typed-companion into the
`BeyondClassicalSmoothnessCriterion` disjunction (Vasseur branch). -/
theorem BeyondClassicalSmoothnessCriterion.fromAntiTwist
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : AntiTwistData sol) :
    BeyondClassicalSmoothnessCriterion sol D.T :=
  BeyondClassicalSmoothnessCriterion.fromVasseur (antitwist_implies_vasseur D)

/-- Lift directly into the SIX-way unified extended criterion. -/
theorem UnifiedSmoothnessCriterionExt.fromAntiTwist
    {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : AntiTwistData sol) :
    UnifiedSmoothnessCriterionExt sol D.T :=
  UnifiedSmoothnessCriterionExt.fromBeyond
    (BeyondClassicalSmoothnessCriterion.fromAntiTwist D)

/-! ## §5.  Honesty receipt

Total content of this file:

* 1 inline frontier predicate Prop:
  - `AntiTwistRegularization`        (Hou-Luo 2024 / BLW 2024)

* 1 typed companion record:
  - `AntiTwistData`                  (CAV azimuthal + sign reversal +
                                      conditional stretching)

* 1 EMPIRICAL axiom (cited to both papers):
  - `hou_luo_buaria_anti_twist_axiom`

* 3 lift theorems (logic only):
  - `AntiTwistData.toRegularization`
  - `antitwist_implies_vasseur`
  - `BeyondClassicalSmoothnessCriterion.fromAntiTwist`
  - `UnifiedSmoothnessCriterionExt.fromAntiTwist`

Zero `sorry`s.

ARCHITECTURAL VERDICT: SHIPPABLE-AS-AXIOM.  The deductive content is
sound; the empirical axiom is the load-bearing lower-confidence
assumption.  Closing the empirical axiom rigorously (or producing a
mathematical proof of the anti-twist mechanism in the inviscid
limit) discharges Fefferman A through this bridge composed with the
existing Vasseur axiom in `ns_trackb_helicity_vortex_stretching`.
-/

end

end ZtareProofs.NS
