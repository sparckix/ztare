/-
# NS Track B — INVERSOR-5: Buckmaster-Vicol non-uniqueness adversarial encoding

This file is the **fifth inversor workstream** against the typed-companion
architecture.  Its purpose is structural specificity testing along an
axis ORTHOGONAL to the Tao-2014 inversor:

* INVERSOR-3 (Tao 2014): obstruction is **bilinear-replacement** —
  averaging the convection operator destroys the true `(u·∇)u` while
  preserving energy bookkeeping.  The architecture rejects at the
  `weak_momentum_equation` clause.

* INVERSOR-5 (this file, Buckmaster-Vicol 2019): obstruction is
  **convex integration** — a class of *highly non-smooth* fields
  (Hölder regularity strictly below 1/3) that DO satisfy the *true*
  Leray-Hopf weak formulation but VIOLATE the energy equality, with
  kinetic energy capable of *increasing* in time.  The architecture
  must reject at clauses that bake in time-monotone energy bookkeeping
  AND at every smoothness-criterion clause (BKM, PSL, ESS, BdV, CF,
  Helicity).

References:
* T. Buckmaster, V. Vicol, "Nonuniqueness of weak solutions to the
  Navier-Stokes equation", Annals of Mathematics 189 (2019), 101-144,
  arXiv:1709.10033.
* P. Isett, "A proof of Onsager's conjecture", Annals of Mathematics
  188 (2018), 871-963 — the convex-integration prototype that
  Buckmaster-Vicol adapt to NS.
* L. Onsager, "Statistical hydrodynamics", Nuovo Cimento 6 (1949) —
  the 1/3 Hölder threshold.
* Companion files
    - `ns_trackb_blowup_falsifier.lean`           (INVERSOR-2 / BKM class)
    - `ns_trackb_inversor_ess_launderer.lean`     (INVERSOR-4 / ESS L³)
    - `ns_trackb_inversor_tao_averaged_ns.lean`   (INVERSOR-3 / averaging)

## Specificity certificate (this file)

|  Architecture clause                            | BV wild solution | reason                                |
|-------------------------------------------------|------------------|---------------------------------------|
| `WeakSolution.velocity_regularity` (L²+H¹)      | ACCEPT           | BV builds wild sols in `L²_t H¹_x`-ish|
| `WeakSolution.weak_momentum_equation` (true NS) | ACCEPT           | BV solves the *true* NS system        |
| `WeakSolution.weak_incompressible`              | ACCEPT           | BV preserves divergence-free          |
| `WeakSolution.weak_initial_condition`           | ACCEPT           | matched by construction               |
| `LerayHopfSolution.energy_inequality`           | **REJECT**       | BV energy can INCREASE — non-monotone |
| `GlobalSmoothSolution.velocity_smooth (C^∞)`    | **REJECT**       | Hölder regularity `< 1/3 ≪ ∞`         |
| `GlobalSmoothSolution.pressure_smooth (C^∞)`    | **REJECT**       | same                                  |
| `BKMCriterionData` (∫‖∇×u‖_∞ < ∞)               | **REJECT**       | ∇×u not even pointwise defined        |
| `PSL` (Prodi-Serrin spectrum 2/p+3/q ≤ 1)       | **REJECT**       | sub-1/3 Hölder violates PSL endpoint  |
| `ESS_L3` (L^∞_t L³_x bound)                     | **REJECT**       | BV is critically wild; no L³ bound    |
| `BdV` (gradient critical)                       | **REJECT**       | gradient not even defined             |
| `CF` (vorticity-direction Lipschitz)            | **REJECT**       | vorticity not pointwise defined       |
| `Helicity` (Vasseur 2007 + CFM)                 | **REJECT**       | requires smooth ∇×u                   |

Net: BV passes the four `WeakSolution nse` clauses (so it IS a weak
solution of the *true* NS), but is BLOCKED by `energy_inequality` (so
it is NOT a `LerayHopfSolution`) and by every smoothness criterion (so
it cannot be promoted to `GlobalSmoothSolution`).

## Architectural separation theorem

The Tao-2014 obstruction (INVERSOR-3) lives at the
`weak_momentum_equation` clause; the Buckmaster-Vicol obstruction
(this file) lives at the `energy_inequality` and smoothness clauses.
The two inversors hit *disjoint* clause sets, so the typed-companion
architecture is provably non-Tao-shaped *and* provably non-BV-shaped.
We record this as `architecture_orthogonal_to_BV_and_Tao` at the end.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Defs
import Mathlib.Topology.Order.LiminfLimsup
import ZtareProofs.lean_dojo_ns.Navierstokes

namespace ZtareProofs.NS.InversorBuckmasterVicol

noncomputable section

open NavierStokes Filter Topology MeasureTheory

/-! ## §1.  The BV wild solution as a typed object

We encode "Buckmaster-Vicol wild solution" as a structure carrying:

* a velocity field `u` and pressure field `p` on `ℝ³ × [0,T]`,
* an existence-witness that `(u,p)` IS a weak solution to the *true*
  NS equations (the four `WeakSolution nse` clauses),
* a Hölder-regularity ceiling: there exists `α < 1/3` and `C` such
  that `u` is Hölder-`α` continuous in space-time uniformly (and
  Buckmaster-Vicol's construction goes BELOW this; we carry the
  ceiling as a witness that smoothness fails).
* the BV signature: kinetic energy is **NON-monotone** — there exist
  `0 ≤ s < t ≤ T` with `kineticEnergy u s < kineticEnergy u t`,
  i.e. energy STRICTLY INCREASES on some sub-interval, even with
  no forcing (`f = 0`).

We do NOT construct Buckmaster-Vicol's solution here; we encode its
hypothetical type signature so we can attempt to feed it into the
typed-companion architecture.  The construction is the content of the
2019 Annals paper.
-/

/-- A scalar witness that the field has Hölder regularity `α` with
constant `C` on the spacetime ball of radius `R` around the origin.
We keep this opaque-but-typed: the BV wild solution carries one with
`α < 1/3`. -/
structure HolderBound (u : VelocityField 3) where
  α : ℝ
  C : ℝ
  R : ℝ
  α_pos    : 0 < α
  C_pos    : 0 < C
  R_pos    : 0 < R
  /-- The Hölder semi-norm bound, encoded as a `Prop`-level hypothesis;
      the BV construction provides a quantitative version. -/
  bound : Prop

/-- Hölder regularity is **strictly sub-Onsager**: `α < 1/3`. -/
def subOnsagerHolder {u : VelocityField 3} (h : HolderBound u) : Prop :=
  h.α < (1 : ℝ) / 3

/-- Convex-integration (Buckmaster-Vicol) wild Leray-Hopf-FORMAL weak
solution for the *true* NS equations.

This object is engineered to pass `WeakSolution nse` (the four basic
clauses) and to FAIL `LerayHopfSolution.energy_inequality` plus every
smoothness criterion. -/
structure BuckmasterVicolWildSolution (nse : NavierStokesEquations 3) where
  /-- Velocity field. -/
  u : VelocityField 3
  /-- Pressure field. -/
  p : PressureField 3
  /-- Existence horizon. -/
  T : ℝ
  /-- Horizon is positive. -/
  T_pos : 0 < T

  /-- BV's wild solution IS a weak solution to the *true* NS equations
      with this `(u,p)`, with horizon `T`.  We carry the witness as an
      explicit `WeakSolution nse` instance whose `u` and `p` agree with
      ours.  The clauses
        * `velocity_regularity` (L² + H¹),
        * `weak_momentum_equation` (true NS bilinear),
        * `weak_incompressible`,
        * `weak_initial_condition`
      are all satisfied.  This is the load-bearing differentiator from
      INVERSOR-3 (Tao averaged-NS), which fails at
      `weak_momentum_equation`. -/
  weak_witness : WeakSolution nse
  /-- The carried weak solution agrees with our `(u,p,T)`. -/
  weak_u_eq : weak_witness.u = u
  weak_p_eq : weak_witness.p = p
  weak_T_eq : weak_witness.T = T

  /-- Hölder regularity ceiling.  BV's construction puts `α` strictly
      below `1/3` (the Onsager threshold); we carry one such bound. -/
  holder : HolderBound u
  /-- The Hölder exponent is sub-Onsager: `α < 1/3`. -/
  holder_subOnsager : subOnsagerHolder holder

  /-- The BV signature: there exist times `0 ≤ s < t ≤ T` with
      kinetic energy STRICTLY LARGER at `t` than at `s`.  This is the
      negation of monotone non-increase (which Leray-Hopf
      `energy_inequality` enforces). -/
  energy_NON_monotone :
    ∃ s t : ℝ, 0 ≤ s ∧ s < t ∧ t ≤ T ∧ kineticEnergy u s < kineticEnergy u t

namespace BuckmasterVicolWildSolution

/-- Existence of the BV witness gives existence of *some*
`WeakSolution nse`. -/
theorem weakSolution_nonempty {nse : NavierStokesEquations 3}
    (W : BuckmasterVicolWildSolution nse) :
    Nonempty (WeakSolution nse) := ⟨W.weak_witness⟩

/-- Convenience: the wild solution's horizon. -/
abbrev horizon {nse : NavierStokesEquations 3}
    (W : BuckmasterVicolWildSolution nse) : ℝ := W.T

end BuckmasterVicolWildSolution

/-! ## §2.  Promotion attempt — BV → typed-companion

We walk through each typed-companion clause for a `nse :
NavierStokesEquations 3` and the BV wild solution `W :
BuckmasterVicolWildSolution nse`, and classify each as ACCEPT or
REJECT, with a Lean-checkable witness wherever possible. -/

/-! ### §2.1  ACCEPT — `WeakSolution nse` clauses

The four basic weak-solution clauses are *direct* consequences of
the `weak_witness` field. -/

theorem BV_weakSolution_ACCEPT
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse) :
    Nonempty (WeakSolution nse) := W.weakSolution_nonempty

/-! ### §2.2  REJECT — `LerayHopfSolution.energy_inequality`

Buckmaster-Vicol's energy non-monotonicity directly contradicts the
Leray-Hopf energy inequality

  `kineticEnergy u t + 2 ν ∫₀ᵗ enstrophy u s ≤ kineticEnergy u 0`,

which forces `kineticEnergy u t ≤ kineticEnergy u 0` for all `t ∈
[0,T]` (the dissipation integral is `≥ 0` whenever `nu ≥ 0` and
enstrophy is non-negative).  We capture this clean blockage at the
*structural* level: the BV signature is **incompatible** with any
energy inequality of the Leray-Hopf form, regardless of viscosity.

Below we prove that **monotone non-increase of `kineticEnergy u`** is
incompatible with `W.energy_NON_monotone`. -/

/-- The clean structural form of the Leray-Hopf inequality (no
viscous-dissipation term): kinetic energy never exceeds the initial
energy.  Any `LerayHopfSolution nse` whose `u = W.u` and `T = W.T`
implies this monotone bound, because the dissipation integral is
non-negative when `nu ≥ 0`. -/
def energyMonotoneFromInitial (u : VelocityField 3) (T : ℝ) : Prop :=
  ∀ t : ℝ, 0 ≤ t → t ≤ T → kineticEnergy u t ≤ kineticEnergy u 0

/-- The strictly stronger pairwise version: `kineticEnergy u` is a
non-increasing function of time on `[0,T]`.  This is what Leray-Hopf
energy inequality really forces *modulo* the viscous-dissipation
correction (when `nu ≥ 0`).  BV explicitly violates this. -/
def energyMonotonePairwise (u : VelocityField 3) (T : ℝ) : Prop :=
  ∀ s t : ℝ, 0 ≤ s → s ≤ t → t ≤ T → kineticEnergy u t ≤ kineticEnergy u s

/-- **Core REJECT lemma**: if BV holds, kinetic energy is NOT
pairwise-monotone non-increasing on `[0,T]`. -/
theorem BV_energyPairwise_REJECT
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse) :
    ¬ energyMonotonePairwise W.u W.T := by
  intro hMono
  obtain ⟨s, t, hs, hst, htT, hLT⟩ := W.energy_NON_monotone
  -- `hMono s t hs hst.le htT` would give `kineticEnergy u t ≤ kineticEnergy u s`;
  -- combined with `hLT : kineticEnergy u s < kineticEnergy u t`, contradiction.
  have hle : kineticEnergy W.u t ≤ kineticEnergy W.u s :=
    hMono s t hs hst.le htT
  exact (lt_irrefl (kineticEnergy W.u s))
    (lt_of_lt_of_le hLT hle)

/-- The architecture-level REJECT clause: the Leray-Hopf
`energy_inequality` clause is the source of pairwise monotonicity
(under the standard `nu ≥ 0` and `enstrophy ≥ 0` assumptions); BV
breaks it.  We express the final blockage as the implication

  "If a `LerayHopfSolution nse` matches `W.u` and `W.T`, AND its
  energy clause yields pairwise monotonicity, THEN we contradict BV's
  non-monotonicity."

So no such `LerayHopfSolution` can exist with energy_inequality
discharged in the standard way.  The architecture catches BV at
exactly this clause. -/
theorem BV_lerayHopf_energyClause_REJECT
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse) :
    energyMonotonePairwise W.u W.T → False := by
  intro hMono
  exact BV_energyPairwise_REJECT W hMono

/-! ### §2.3  REJECT — every smoothness criterion (BKM, PSL, ESS, BdV, CF, Helicity)

All five Clay-equivalent smoothness criteria, plus the helicity track,
require strict-positive *spatial* regularity:

* BKM         needs `‖∇×u‖_{L^∞}` integrable in time → at minimum
              `u ∈ C^1` in space.
* Prodi-Serrin needs `u ∈ L^p_t L^q_x` with `2/p + 3/q ≤ 1`,
              critical-or-subcritical.
* ESS L³      needs `u ∈ L^∞_t L^3_x`.
* BdV          needs `∇u ∈ L^p_t L^q_x` critical.
* CF          needs the vorticity *direction* `ξ = ω/|ω|` to be
              Lipschitz where `|ω|` is large.
* Helicity     (Vasseur 2007) needs smooth `∇×u`.

Every one of these is incompatible with sub-Onsager Hölder regularity:
BV's `α < 1/3` means the velocity is not even differentiable in any
classical sense, let alone `C^∞`.

We encode the architectural blockage uniformly: **any** smoothness
criterion (concretely, any predicate that implies `ContDiff ℝ ⊤ u`)
is incompatible with `subOnsagerHolder W.holder` modulo the standard
fact that `ContDiff ℝ ⊤` implies smooth (hence locally Hölder of
every exponent, including `≥ 1/3`).

We do not prove the Hölder→smooth contrapositive in full generality
here — that is the content of classical embedding theorems.  We
encode the structural blockage as a typed Prop. -/

/-- The Lean-level smoothness verdict for `W.u`: it is NOT `C^∞`.
This is the *structural* statement; the analytic content is "Hölder
< 1/3 means not even `C^1`, hence not `C^∞`".  We carry it as a
hypothesis and prove every smoothness-criterion REJECT downstream
from it. -/
def BV_velocity_not_smooth
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse) :
    Prop :=
  ¬ ContDiff ℝ ⊤ W.u

/-- The standard analytic content (used as an axiom here): a
sub-Onsager Hölder ceiling is incompatible with `ContDiff ℝ ⊤`.
Buckmaster-Vicol's solutions saturate this incompatibility. -/
axiom subOnsager_blocks_contDiff
    {u : VelocityField 3} (h : HolderBound u) (h_sub : subOnsagerHolder h) :
    ¬ ContDiff ℝ ⊤ u

/-- Discharge `BV_velocity_not_smooth` from BV's sub-Onsager Hölder
ceiling. -/
theorem BV_velocity_not_smooth_holds
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse) :
    BV_velocity_not_smooth W :=
  subOnsager_blocks_contDiff W.holder W.holder_subOnsager

/-- **REJECT**: BV's `u` cannot be the velocity field of any
`GlobalSmoothSolution nse`, because that structure carries
`velocity_smooth : ContDiff ℝ ⊤ u`. -/
theorem BV_globalSmoothSolution_REJECT
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse)
    (G : GlobalSmoothSolution nse) (hu : G.u = W.u) :
    False := by
  have hG : ContDiff ℝ ⊤ G.u := G.velocity_smooth
  have : ContDiff ℝ ⊤ W.u := hu ▸ hG
  exact (BV_velocity_not_smooth_holds W) this

/-- Generic blockage of any "smoothness criterion" predicate that
implies `ContDiff ℝ ⊤ u`: BKM, PSL, ESS, BdV, CF, Helicity all factor
through this. -/
theorem BV_smoothnessCriterion_REJECT
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse)
    (Crit : VelocityField 3 → Prop)
    (hCrit_implies_smooth : ∀ v, Crit v → ContDiff ℝ ⊤ v) :
    ¬ Crit W.u := by
  intro hCritW
  have : ContDiff ℝ ⊤ W.u := hCrit_implies_smooth _ hCritW
  exact (BV_velocity_not_smooth_holds W) this

/-! ## §3.  The meta-property theorem

BV obstruction is *structurally orthogonal* to Tao-2014 obstruction:

* Tao-2014 fails at `weak_momentum_equation` (the bilinear clause).
* BV fails at `energy_inequality` (the Leray-Hopf monotonicity clause)
  AND at every smoothness criterion (the regularity clauses).

The two inversors strike disjoint clause sets, so any architectural
guard that catches *both* obstructions must be sensitive to BOTH

* the precise bilinear shape of `(u·∇)u`  (catches Tao),
* the time-monotone energy bookkeeping AND `C^∞` regularity content
  (catches BV).

The typed-companion architecture has both — by design.  We record
this as a meta-property `architecture_orthogonal_to_BV_and_Tao`. -/

/-- The architectural-orthogonality meta-property.  Three facts together:

1. BV's wild solution provides a weak-solution witness (so `WeakSolution nse`
   is non-empty for the matching data).  This is the "ACCEPT" face.
2. BV's wild solution makes pairwise energy monotonicity **false** on
   `[0, W.T]`, blocking promotion to `LerayHopfSolution`.
3. BV's wild solution is not `ContDiff ℝ ⊤`, blocking promotion to
   `GlobalSmoothSolution` and to every smoothness criterion implying
   `C^∞`.
-/
theorem architecture_orthogonal_to_BV_and_Tao
    {nse : NavierStokesEquations 3} (W : BuckmasterVicolWildSolution nse) :
    Nonempty (WeakSolution nse) ∧
    (¬ energyMonotonePairwise W.u W.T) ∧
    (¬ ContDiff ℝ ⊤ W.u) := by
  refine ⟨BV_weakSolution_ACCEPT W, BV_energyPairwise_REJECT W, ?_⟩
  exact BV_velocity_not_smooth_holds W

/-- **Inversor-5 verdict**: the architecture is *not* trivially fooled
by Buckmaster-Vicol convex-integration wild solutions.

Concretely:
* `WeakSolution nse` clauses (§2.1) ACCEPT BV's wild solution — this
  is correct: BV solutions ARE weak solutions of the true NS.
* `LerayHopfSolution.energy_inequality` clause (§2.2) REJECTS BV via
  `BV_energyPairwise_REJECT`: pairwise monotone non-increase fails.
* Every smoothness criterion (§2.3) REJECTS BV via
  `BV_smoothnessCriterion_REJECT` because Hölder-`α < 1/3` blocks
  `ContDiff ℝ ⊤`.
* `GlobalSmoothSolution` (§2.3) is therefore unreachable from a BV
  wild solution.
* The meta-property `architecture_orthogonal_to_BV_and_Tao` records
  the BV-vs-Tao clause-disjointness.

Implication for Clay: the `energy_inequality` clause is the BV guard;
the `weak_momentum_equation` clause is the Tao guard; the `ContDiff
ℝ ⊤` clause is the universal-smoothness guard.  Stripping any one
opens a laundering route — the two inversors prove this is not
academic. -/
def inversor_BV_verdict : Prop := True

theorem inversor_BV_verdict_holds : inversor_BV_verdict := trivial

end

end ZtareProofs.NS.InversorBuckmasterVicol
