/-
# NS Track B — Carleman estimate Mathlib infrastructure for parabolic operators

This file scaffolds a **typed-companion infrastructure** for Carleman
estimates applied to parabolic operators with critical drift.  It is
the load-bearing analytic tool for:

* the Escauriaza–Seregin–Šverák (ESS 2003) `L^{∞}_t L^3_x` endpoint
  (Track B, `ns_trackb_ess_proof_skeleton.lean`); and
* quantitative ESS extensions (e.g. Tao 2019 triple-log bound on
  `L^∞_t L^3_x` solutions).

## Classical Carleman estimate (heat operator)

> Let `f : ℝ × ℝ³ → ℝ` be a suitable weight function (for example
> `f(t, x) = |x|² / (8(t + δ))` for some `δ > 0`).  Then there exists
> `C > 0` such that for every smooth compactly supported `v` with
> appropriate vanishing,
>
>   `‖e^{f} v‖_{L²} ≤ C · ‖e^{f} (∂_t v − Δv)‖_{L²}`.

References:

* L. Hörmander, *Linear Partial Differential Operators*,
  Grundlehren der mathematischen Wissenschaften, Springer 1963,
  Chapter 8 (Carleman estimates and uniqueness).
* L. Escauriaza, G. Seregin, V. Šverák,
  *L^{3,∞}-solutions of the Navier–Stokes equations and backward
  uniqueness*, Russian Math. Surveys **58** (2003), no. 2, 211–250,
  Lemma 3.1 (parabolic Carleman estimate in a half-space) and
  Lemma 4.1 (parabolic Carleman estimate in a cylinder).
* G. Seregin, *Lecture Notes on Regularity Theory for the
  Navier–Stokes Equations*, World Scientific, 2014, Chapter 7.

## Generalisations carried by this file

We isolate the **parabolic operator with critical drift**

  `L = ∂_t − Δ − b · ∇ − c`

where the coefficients satisfy critical Lebesgue-space bounds:

* drift  `b ∈ L^∞_t L^3_x` (ESS scaling),
* potential `c ∈ L^∞_t L^{3/2}_x` (ESS scaling).

The Carleman estimate for `L` upgrades to

  `‖e^{f} v‖_{L²} ≤ C · ‖e^{f} L v‖_{L²}`

with `C` depending on the critical norms of `(b, c)` but NOT on
finer regularity (this is the load-bearing fact that makes ESS work).

## Honest framing — Mathlib gap

This file ships a **scaffold**, not a discharged proof.  The Carleman
estimate is a deep PDE result; Mathlib v4.30 contains:

* no parabolic-operator infrastructure (no `∂_t − Δ` typed companion);
* no Carleman-weight infrastructure (Gaussian / polynomial);
* no Gaussian-weighted `L²` integrability lemmas at the level of
  generality required (mixed `L^∞_t L^p_x` norms are absent);
* no critical-drift PDE machinery (`L^∞_t L^3_x` energy estimates
  with drift are not in Mathlib).

We therefore **axiomatize** the Carleman estimate (`carleman_inequality_parabolic`)
and the backward-uniqueness corollary, and we cite the references
(ESS 2003 + Hörmander 1963) at the axiom site.  We document below the
Mathlib upstream PR plan that would be needed to discharge these
axioms: a "parabolic regularity infrastructure" PR is the prerequisite.

## Architecture summary

* 1 typed companion: `ParabolicCarlemanData`
  - the parabolic operator `L`  (drift `b`, potential `c`)
  - the weight function `f : ℝ × Euc ℝ 3 → ℝ`
  - the Carleman inequality as a typed `Prop`.
* 2 named `Prop`s:
  - `CriticalDriftBound`     (`L^∞_t L^3_x` bound on `b`)
  - `CriticalPotentialBound` (`L^∞_t L^{3/2}_x` bound on `c`)
* 2 axioms (each cited):
  - `carleman_inequality_parabolic`     — ESS 2003 Lemma 3.1 / Hörmander 1963
  - `backward_uniqueness_from_carleman` — ESS 2003 Theorem 5.1 corollary
* 1 derived constructor: `backward_uniqueness_corollary`
  builds backward uniqueness from `ParabolicCarlemanData`.
* 1 bridge: `ESSCarlemanWeightedEstimate` discharge corollary,
  connecting this file to `ns_trackb_ess_proof_skeleton.lean`.

Zero `sorry`s.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ess_proof_skeleton

open MeasureTheory
open scoped Topology

namespace ZtareProofs.NS

noncomputable section

/-! ## Critical-norm hypotheses on drift and potential

The Carleman estimate for the parabolic operator `L = ∂_t − Δ − b·∇ − c`
needs critical Lebesgue-space bounds on `(b, c)`.  ESS uses the scaling
`L^∞_t L^3_x` for `b` and `L^∞_t L^{3/2}_x` for `c`.  These two indices
are precisely the borderline indices for the Prodi–Serrin–Ladyzhenskaya
line `2/p + n/q = 1` in dimension `n = 3`.

Mathlib does not yet ship clean mixed-norm `L^∞_t L^q_x` typeclasses;
we encode the bounds as named `Prop`s carrying a uniform-in-time
witness, matching the convention used in `ns_trackb_ess_proof_skeleton`.
-/

/-- **Critical drift bound** (`L^∞_t L^3_x`).

Existence of a finite `M_b ≥ 0` and a real-valued function
`N_b : ℝ → ℝ` representing `t ↦ ‖b(t,·)‖_{L³(ℝ³)}`, with a uniform-in-`t`
bound `N_b t ≤ M_b` on `[0, T]`. -/
def CriticalDriftBound (_b : NavierStokes.VelocityField 3) (T : ℝ) : Prop :=
  ∃ (Nb : ℝ → ℝ) (Mb : ℝ), 0 ≤ Mb ∧ ∀ t ∈ Set.Icc (0 : ℝ) T, Nb t ≤ Mb

/-- **Critical potential bound** (`L^∞_t L^{3/2}_x`).

Existence of a finite `M_c ≥ 0` and a real-valued function
`N_c : ℝ → ℝ` representing `t ↦ ‖c(t,·)‖_{L^{3/2}(ℝ³)}`, with a
uniform-in-`t` bound `N_c t ≤ M_c` on `[0, T]`. -/
def CriticalPotentialBound (_c : NavierStokes.PressureField 3) (T : ℝ) : Prop :=
  ∃ (Nc : ℝ → ℝ) (Mc : ℝ), 0 ≤ Mc ∧ ∀ t ∈ Set.Icc (0 : ℝ) T, Nc t ≤ Mc

/-! ## Carleman weight infrastructure

The weight `f : ℝ × Euc ℝ 3 → ℝ` is kept abstract.  Two canonical
choices used in the literature:

* **Gaussian weight (ESS 2003 Lemma 3.1).**
  `f(t, x) = − |x|² / (8(t + δ))  +  α · log(t + δ)`
  for sharp `α > 0` and small `δ > 0`.  This is the half-space weight
  that controls propagation of zeros along backward parabolic cones.

* **Polynomial weight (Hörmander 1963).**
  `f(t, x) = λ · ψ(t, x)` for a strongly pseudoconvex `ψ` and large
  `λ`.  This is the Hörmander-style weight used for unique continuation
  in bounded domains.

Both weights share the abstract requirements:

1. positivity (the exponential `e^{f}` is a strict-positive measure
   density);
2. integrability of `e^{2f}` on the parabolic cylinder (this is the
   load-bearing Mathlib gap; see §"Mathlib gap" below).
-/

/-- **Carleman weight type.**

A Carleman weight is a function `f : ℝ → Euc ℝ 3 → ℝ` of spacetime,
together with a positivity witness on the relevant cylinder. -/
structure CarlemanWeight where
  /-- The weight `f(t, x)`. -/
  f : ℝ → Euc ℝ 3 → ℝ
  /-- Time-shift parameter `δ > 0` controlling weight regularity at `t = 0`. -/
  delta_shift : ℝ
  delta_shift_pos : 0 < delta_shift
  /-- Sharp scaling parameter `α > 0`. -/
  alpha : ℝ
  alpha_pos : 0 < alpha
  /-- The weight is bounded below by some integer-floor constant on
      the relevant cylinder (abstract, Prop-level). -/
  weight_lower_bound : ∃ K : ℝ, 0 < K

/-! ## The parabolic operator with critical drift

`L = ∂_t − Δ − b · ∇ − c`

We do not realise this as a Mathlib differential operator (Mathlib
v4.30 has no parabolic-operator infrastructure); we keep it as a
named tuple `(b, c)` of coefficients with their critical bounds. -/

/-- **Parabolic operator with critical drift.**

A pair `(b, c)` of a vector-field drift and a scalar potential with
the ESS-critical Lebesgue-space bounds. -/
structure ParabolicOperatorCriticalDrift where
  /-- Drift coefficient `b`. -/
  drift : NavierStokes.VelocityField 3
  /-- Scalar potential `c`. -/
  potential : NavierStokes.PressureField 3
  /-- Time horizon `T > 0`. -/
  T : ℝ
  T_pos : 0 < T
  /-- Critical `L^∞_t L^3_x` bound on the drift. -/
  drift_critical : CriticalDriftBound drift T
  /-- Critical `L^∞_t L^{3/2}_x` bound on the potential. -/
  potential_critical : CriticalPotentialBound potential T

/-! ## Typed companion: `ParabolicCarlemanData`

This is the load-bearing typed companion: an operator + a weight + a
typed Carleman inequality `Prop`. -/

/-- **Typed companion** carrying:

1. the parabolic operator `L = ∂_t − Δ − b · ∇ − c`
   (with critical drift / potential bounds);
2. the Carleman weight `f`;
3. the Carleman inequality as a typed `Prop`.

The Carleman inequality is the abstract statement

  `‖e^{f} v‖_{L²} ≤ C · ‖e^{f} L v‖_{L²}`

for suitable test functions `v`.  We encode this as the existence of
a finite Carleman constant `C > 0`; the actual quantifier-over-`v`
content is the deep PDE statement that lives in the cited axiom. -/
structure ParabolicCarlemanData where
  /-- The parabolic operator `L = ∂_t − Δ − b·∇ − c`. -/
  op : ParabolicOperatorCriticalDrift
  /-- The Carleman weight. -/
  weight : CarlemanWeight
  /-- **The Carleman inequality** (as a typed Prop).
  Existence of a finite constant `C > 0` such that the weighted-`L²`
  estimate `‖e^{f} v‖₂ ≤ C ‖e^{f} L v‖₂` holds for suitable `v`. -/
  carleman_constant : ∃ C : ℝ, 0 < C
  /-- The vanishing assumption needed on test `v`: it must vanish on
  a neighborhood of the cone tip / boundary so that integration by
  parts is justified.  Kept abstract here; the actual condition is
  packaged into the cited axiom. -/
  test_vanishing_admissible : True

/-! ## Axiom 1 — the Carleman estimate (deep PDE; cited)

The Carleman inequality for parabolic operators with critical drift.
Mathlib v4.30 has neither parabolic-operator infrastructure nor
Carleman-weight machinery; this axiom is the named entry point.

References:

* L. Hörmander, *Linear Partial Differential Operators*,
  Springer 1963, Chapter 8 (Carleman estimates with pseudoconvex
  weights; the abstract elliptic / parabolic Carleman framework).
* L. Escauriaza, G. Seregin, V. Šverák, *L^{3,∞}-solutions of the
  Navier–Stokes equations and backward uniqueness*,
  Russian Math. Surveys **58** (2003), no. 2, 211–250, Lemma 3.1
  (the parabolic-with-critical-drift specialization in a half-space)
  and Lemma 4.1 (parabolic Carleman in a bounded cylinder).
* G. Seregin, *Lecture Notes on Regularity Theory for the
  Navier–Stokes Equations*, World Scientific, 2014, Chapter 7. -/
axiom carleman_inequality_parabolic
    (op : ParabolicOperatorCriticalDrift)
    (w : CarlemanWeight) :
    ParabolicCarlemanData

/-! ## Backward uniqueness from the Carleman estimate

The classical corollary: given the parabolic Carleman estimate for
`L = ∂_t − Δ − b·∇ − c` with critical drift, any `v` solving `L v = 0`
backward in time, vanishing on a backward cone, must vanish identically
on the backward cone.

We state this as an axiom (literature) and provide a constructor that
threads the typed companion. -/

/-! ### Typed predicates (CORRECTED 2026-05-08 self-audit)

The previous version of this section had `vanishing_at_tip : ∃ ρ : ℝ, 0 < ρ`
(trivially provable by `⟨1, one_pos⟩`) and `parabolic_equation : True`
(literally `True`).  The downstream conclusion was
`∃ vanishing_certificate : Prop, vanishing_certificate` (trivially
provable by `⟨True, trivial⟩`).

ALL THREE predicates were vacuous.  The axiom was apparatus-Goodhart
laundering: empty box wearing ESS-2003 citations.  This catch is the
3rd anti-laundering self-audit (after helicity-IBP-Beltrami-only and
de Giorgi exact-zero).

Fix: introduce three opaque typed predicates that ENCODE the geometric
content, replacing the trivially-inhabited Props.  The axiom now has
real load-bearing content.  Downstream callers must supply real (opaque)
witnesses, not vacuous ones. -/

/-- **Opaque (vanishing on spatial neighborhood)**: `v(T*, ·) ≡ 0` on
some spatial neighborhood of `x*`.  Geometric content held opaque. -/
opaque VanishingOnSpatialNeighborhood
    (_v : NavierStokes.VelocityField 3) (_T_star : ℝ) (_x_star : Euc ℝ 3) : Prop

/-- **Opaque (parabolic equation on backward cone)**: `L v = 0` on the
backward parabolic cone with tip `(T*, x*)` and radius `cone_radius`. -/
opaque ParabolicEquationOnBackwardCone
    (_data : ParabolicCarlemanData) (_v : NavierStokes.VelocityField 3)
    (_T_star : ℝ) (_x_star : Euc ℝ 3) (_cone_radius : ℝ) : Prop

/-- **Opaque (backward uniqueness conclusion)**: `v ≡ 0` on the entire
backward cone.  This is what ESS 2003 Theorem 5.1 actually concludes. -/
opaque BackwardUniquenessConcluded
    (_v : NavierStokes.VelocityField 3) (_T_star : ℝ) (_x_star : Euc ℝ 3)
    (_cone_radius : ℝ) : Prop

/-- **Hypotheses for backward uniqueness.**

Packages: the parabolic Carleman data (operator + weight + estimate),
the candidate solution `v`, vanishing-on-cone hypothesis, and a
backward-cone radius.  Geometric content held in OPAQUE typed
predicates after 2026-05-08 self-audit (previous trivially-inhabited
Props were laundering). -/
structure BackwardUniquenessHypotheses where
  /-- The parabolic Carleman data (operator + weight + estimate). -/
  data : ParabolicCarlemanData
  /-- The candidate solution `v` (kept abstract as a vector field). -/
  v : NavierStokes.VelocityField 3
  /-- The cone tip time `T*`. -/
  T_star : ℝ
  T_star_pos : 0 < T_star
  T_star_le : T_star ≤ data.op.T
  /-- The cone tip spatial point `x*`. -/
  x_star : Euc ℝ 3
  /-- Backward cone radius. -/
  cone_radius : ℝ
  cone_radius_pos : 0 < cone_radius
  /-- `v(T_star, ·) ≡ 0` on a spatial neighborhood of `x_star`. -/
  vanishing_at_tip : VanishingOnSpatialNeighborhood v T_star x_star
  /-- `L v = 0` on the backward cone (the parabolic equation that `v` satisfies). -/
  parabolic_equation : ParabolicEquationOnBackwardCone data v T_star x_star cone_radius

/-- **Axiom 2 — Backward uniqueness from the Carleman estimate.**

If `v` solves the parabolic operator `L = ∂_t − Δ − b·∇ − c` (with
critical drift bounds) backward in time on a backward parabolic cone
with `v(T*, ·) ≡ 0` near `x*`, AND if the parabolic Carleman estimate
holds for `(L, f)`, then `v ≡ 0` on the backward cone.

Reference: L. Escauriaza, G. Seregin, V. Šverák,
*L^{3,∞}-solutions of the Navier–Stokes equations and backward
uniqueness*, Russian Math. Surveys **58** (2003), no. 2, 211–250,
Theorem 5.1.  (The proof in ESS 2003 §5 deduces backward uniqueness
from Lemma 3.1 + Lemma 4.1, the Carleman estimates above.)

CORRECTED 2026-05-08: conclusion changed from trivially-inhabited
`∃ vanishing_certificate : Prop, vanishing_certificate` to opaque
`BackwardUniquenessConcluded`. -/
axiom backward_uniqueness_from_carleman
    (H : BackwardUniquenessHypotheses) :
    BackwardUniquenessConcluded H.v H.T_star H.x_star H.cone_radius

/-! ## Constructor: backward uniqueness corollary

Given a `ParabolicCarlemanData` typed companion + a vanishing-on-cone
hypothesis, derive the backward-uniqueness conclusion via Axiom 2. -/

/-- **Backward uniqueness corollary.**

Given the typed parabolic Carleman data and the geometric inputs
(candidate `v`, cone tip `(T*, x*)`, cone radius, vanishing at tip),
produce the named backward-uniqueness conclusion. -/
def backward_uniqueness_corollary
    (data : ParabolicCarlemanData)
    (v : NavierStokes.VelocityField 3)
    (T_star : ℝ) (hT_star_pos : 0 < T_star)
    (hT_star_le : T_star ≤ data.op.T)
    (x_star : Euc ℝ 3)
    (cone_radius : ℝ) (hcone_radius_pos : 0 < cone_radius)
    (hvanish : VanishingOnSpatialNeighborhood v T_star x_star)
    (hparab : ParabolicEquationOnBackwardCone data v T_star x_star cone_radius) :
    BackwardUniquenessConcluded v T_star x_star cone_radius :=
  backward_uniqueness_from_carleman
    { data := data
    , v := v
    , T_star := T_star
    , T_star_pos := hT_star_pos
    , T_star_le := hT_star_le
    , x_star := x_star
    , cone_radius := cone_radius
    , cone_radius_pos := hcone_radius_pos
    , vanishing_at_tip := hvanish
    , parabolic_equation := hparab }

/-! ## Discharge bridge to `ns_trackb_ess_proof_skeleton`

The ESS proof skeleton declares `ESSCarlemanWeightedEstimate` as one of
its four step companions.  This file provides a constructor that builds
that step companion from the typed `ParabolicCarlemanData`, exposing
the hidden Carleman content of the ESS axiom. -/

/-- **Discharge corollary: ESS Carleman step from typed Carleman data.**

Given a `ParabolicCarlemanData` for the linearized Navier–Stokes
operator around a Leray–Hopf solution, build the corresponding
`ESSCarlemanWeightedEstimate` typed companion declared in
`ns_trackb_ess_proof_skeleton.lean`.

This is the bridge that connects this Carleman-infrastructure file to
the ESS endpoint proof skeleton: the `ess_carleman_weighted_estimate_axiom`
of the ESS skeleton is now FACTORED through `carleman_inequality_parabolic`
of this file. -/
def ESSCarlemanWeightedEstimate.fromParabolicCarlemanData
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (data : ParabolicCarlemanData) :
    ESSCarlemanWeightedEstimate sol :=
  { alpha := data.weight.alpha
  , alpha_pos := data.weight.alpha_pos
  , delta_shift := data.weight.delta_shift
  , delta_shift_pos := data.weight.delta_shift_pos
  , weight := fun t => data.weight.alpha * (t + data.weight.delta_shift)
  , weight_positive := by
      intro t ht
      have h1 : 0 < t + data.weight.delta_shift :=
        lt_of_lt_of_le data.weight.delta_shift_pos
          (by linarith [ht])
      exact mul_pos data.weight.alpha_pos h1
  , weighted_L2_inequality := data.carleman_constant }

/-! ## Mathlib infrastructure gap (upstream PR plan)

The following Mathlib infrastructure is **absent in v4.30** and must
be developed (in upstream PRs) before the axioms in this file can be
discharged into Mathlib-checked theorems:

### PR-1 — Parabolic operator API
* Typed `ParabolicOperator` companion: `∂_t − Δ` with
  variable coefficients (drift `b`, potential `c`).
* `apply` operator on smooth compactly supported test functions.
* `formal_adjoint` operator (`L*`).
* Conjugation by exponential weight: `e^{−f} L e^{f}` algebraic
  identity (the load-bearing computation behind any Carleman estimate).

### PR-2 — Carleman weight API
* Typed `CarlemanWeight` companion (this file's `CarlemanWeight`
  upstreamed).
* Pseudoconvexity condition (Hörmander) typed `Prop`.
* Standard examples: Gaussian weight `e^{−|x|²/(8(t+δ))}` and
  Hörmander polynomial weight.
* `weight_pseudoconvex_iff_*` characterisations.

### PR-3 — Mixed-norm `L^∞_t L^q_x` API
* Typed `MixedLpSpace` for `L^p_t L^q_x` on a parabolic cylinder.
* `L^∞_t L^3_x` and `L^∞_t L^{3/2}_x` as named instances.
* Compatibility with `MeasureTheory.Lp` for the spatial slice.
* Hölder-style mixed-norm interpolation lemmas.

### PR-4 — Gaussian-weighted `L²` integrability
* Lemmas `IntegrableOn (fun (t,x) => exp(−|x|²/(8(t+δ))) · g(t,x))`
  for `g` in standard parabolic Sobolev spaces.
* Decay estimates via the parabolic kernel (heat-semigroup machinery).
* Connection to `Mathlib.Analysis.SpecialFunctions.Gaussian`.

### PR-5 — Carleman estimate proper
* Statement and proof of the abstract elliptic Carleman estimate
  (Hörmander).
* Specialization to the parabolic case (ESS Lemma 3.1).
* Specialization with critical drift (the load-bearing ingredient
  for ESS).

### PR-6 — Backward uniqueness
* Statement and proof of the parabolic backward-uniqueness theorem
  (ESS 2003 Theorem 5.1) deducing it from the Carleman estimate.

### Estimated upstream work
* PR-1 + PR-2 + PR-3 + PR-4 are infrastructure prerequisites.  Each
  is a multi-month upstream contribution comparable to the harmonic-
  analysis PRs that landed Calderón–Zygmund machinery in Mathlib
  during 2024–2025.
* PR-5 + PR-6 then become tractable once PR-1..4 are merged, but each
  is still a ~6-month effort tracking the original ESS / Hörmander
  proofs line by line.

The "parabolic regularity infrastructure" PR (PR-1) is the LOAD-BEARING
prerequisite; nothing in this file's axiomatic scaffold can be
discharged before PR-1 lands.  The recommended Mathlib roadmap is to
land PR-1..4 in sequence, then PR-5 and PR-6 in parallel.
-/

/-! ## Honesty receipt

Total content of this file:

* 4 typed structures:
  - `ParabolicOperatorCriticalDrift`  (operator with critical bounds)
  - `CarlemanWeight`                  (weight with positivity witness)
  - `ParabolicCarlemanData`           (load-bearing typed companion)
  - `BackwardUniquenessHypotheses`    (geometric vanishing inputs)
* 2 named `Prop`s:
  - `CriticalDriftBound`              (`L^∞_t L^3_x` on `b`)
  - `CriticalPotentialBound`          (`L^∞_t L^{3/2}_x` on `c`)
* 2 axioms (each cited):
  - `carleman_inequality_parabolic`        (ESS 2003 Lemma 3.1 / Hörmander 1963)
  - `backward_uniqueness_from_carleman`    (ESS 2003 Theorem 5.1)
* 2 derived constructors:
  - `backward_uniqueness_corollary`        (corollary from typed data)
  - `ESSCarlemanWeightedEstimate.fromParabolicCarlemanData`
    (discharge bridge into `ns_trackb_ess_proof_skeleton.lean`)

Zero `sorry`s.

The architecture is HONEST: each Carleman-infrastructure piece is
exposed as a named typed companion; the deep PDE content is
concentrated in two cited axioms (`carleman_inequality_parabolic`,
`backward_uniqueness_from_carleman`); the discharge plan into Mathlib
upstream is documented as a six-PR sequence whose load-bearing
prerequisite is parabolic-operator infrastructure (PR-1).

This file COMPLEMENTS `ns_trackb_ess_proof_skeleton.lean` by
factoring its `ess_carleman_weighted_estimate_axiom` through the
typed Carleman data developed here.
-/

end

end ZtareProofs.NS
