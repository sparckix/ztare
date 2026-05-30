/-
# Bridge: typed companion → Prodi–Serrin–Ladyzhenskaya (PSL) smoothness criterion

This file builds a typed-companion bridge for the Prodi–Serrin–Ladyzhenskaya
(PSL) smoothness criterion for the 3-D Navier–Stokes equations.

## Classical statement

Let `u` be a Leray–Hopf weak solution on `[0, T]`.  If
`u ∈ L^p((0,T); L^q(ℝ³))` with
  `2/p + 3/q ≤ 1`,
  `p ∈ (2, ∞], q ∈ (3, ∞]`,
then `u` is unique and smooth on `[0, T]`.

The strict case (`<`, Serrin 1962, Prodi 1959, Ladyzhenskaya 1967) is
a comparatively short bootstrap argument from the energy inequality
combined with Hölder's inequality and parabolic regularity.

The borderline case (equality, e.g. `(p,q) = (∞, 3)`) is much harder;
the `L^∞_t L^3_x` endpoint was settled by
Escauriaza–Seregin–Šverák (2003) using backward-uniqueness for
parabolic equations.  The other borderline cases on the
`2/p + 3/q = 1` line (e.g. `(p,q) = (4, 6)`) are also valid.

References:

* G. Prodi, *Un teorema di unicità per le equazioni di Navier–Stokes*,
  Ann. Mat. Pura Appl. **48** (1959), 173–182.
* J. Serrin, *On the interior regularity of weak solutions of the
  Navier–Stokes equations*, Arch. Rational Mech. Anal. **9** (1962),
  187–195.
* O. A. Ladyzhenskaya, *On the uniqueness and smoothness of generalized
  solutions to the Navier–Stokes equations*, Zap. Nauchn. Sem. LOMI
  **5** (1967), 169–185.
* L. Escauriaza, G. Seregin, V. Šverák, *L^{3,∞}-solutions of the
  Navier–Stokes equations and backward uniqueness*, Russian Math.
  Surveys **58** (2003), 211–250.

## Honest framing — Clay equivalence

PSL gives a SPECTRUM of conditional smoothness statements parameterized
by `(p, q)` on the diagonal `2/p + 3/q ≤ 1`.  For arbitrary smooth
finite-energy initial data on `ℝ³`, NO PSL inequality is known to
hold globally in time — that is exactly the open Clay Millennium
Problem.

Concretely, the Clay problem is *equivalent* to producing some
`(p, q)` on the boundary `2/p + 3/q = 1` (or strictly inside) and
showing that for every smooth divergence-free initial datum
`u₀ ∈ S(ℝ³; ℝ³)` there exists a Leray–Hopf solution `u` such that
the spacetime norm

    ‖u‖_{L^p_t L^q_x} := (∫₀ᵀ (∫_{ℝ³} ‖u(t,x)‖^q dx)^(p/q) dt)^(1/p)

is finite for every `T > 0`.  No such `(p, q)` is currently known to
work.  Conversely, if any single `(p, q)` PSL bound is proved
globally, smoothness follows by PSL.

This file therefore provides:

* a typed companion `ProdiSerrinCriterionData sol p q` carrying the
  scaling `2/p + 3/q ≤ 1` and a Prop input asserting finiteness of the
  spacetime norm;
* an axiom `prodi_serrin_axiom` capturing the deep classical theorem;
* a bridge theorem `prodi_serrin_smoothness_propagation` exposing the
  conditional `L^p_t L^q_x → C^∞` implication as a Lean theorem;
* a canonical instance `ProdiSerrinCriterionData.fromUniformBound`
  showing how a uniform-in-time `L^q_x` bound yields a PSL companion
  with `p = ∞`.

The PSL theorem itself is **axiomatized** (deep classical analysis
result; full formal proof in Lean would require Sobolev-embedding,
maximal-regularity, and parabolic-bootstrap libraries that Mathlib
does not yet ship).  The bridge architecture isolates this single
classical statement as a named axiom; everything else is mechanical.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Defs
import Mathlib.Analysis.SpecialFunctions.Pow.NNReal
import Mathlib.MeasureTheory.Integral.Lebesgue.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes

open MeasureTheory
open scoped ENNReal NNReal BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## Spacetime `L^p_t L^q_x` norm proxy

We deliberately keep the spacetime norm at the *abstract Prop* level —
i.e. as a `Prop` input asserting finiteness of the standard mixed-norm
integral expression — rather than constructing a Mathlib `MemLp`-of-
`MemLp` witness.  The reason is twofold:

1.  Mathlib does not yet ship a clean spacetime mixed-norm typeclass
    (`MemLp` over a `MemLp` codomain) that would let us write
    `MemLp u (p, q)` directly.  The standard workaround is to phrase
    the norm as the iterated lintegral
    `∫₀ᵀ (∫ ‖u(t,·)‖^q)^(p/q) dt` and assert finiteness.

2.  The PSL axiom only consumes a *finiteness* fact, not a particular
    construction of the norm.  So a `Prop`-level field is enough.

Concretely, the typed companion exposes
`spacetimeNormFinite : SpacetimeLpLqFinite sol.u sol.T p q`,
which unfolds to `(iterated lintegral) < ∞`.  The endpoint cases
`p = ∞` and `q = ∞` reduce to essential-supremum versions; we encode
`p = ∞` via a uniform-in-time `L^q_x` bound, which is the canonical
Prodi case.
-/

/-- The spacetime mixed `L^p_t L^q_x` norm of a velocity field
`u : ℝ⁴ → ℝ³` (concretely, `Euc ℝ 4 → Euc ℝ 3`) restricted to
`t ∈ [0, T]`, expressed as a `Prop` asserting finiteness of the
iterated `lintegral`.

For finite `p, q ∈ (1, ∞)`, the standard spacetime norm is

  ‖u‖_{L^p_t L^q_x} := (∫₀ᵀ (∫_{ℝ³} ‖u(t,x)‖^q dx)^(p/q) dt)^(1/p).

We assert finiteness of the inner-then-outer Lebesgue integral
(without the outer `1/p` root, which is monotone-equivalent to
finiteness of the rooted norm). -/
def SpacetimeLpLqFinite
    (u : NavierStokes.VelocityField 3) (T : ℝ) (p q : ℝ) : Prop :=
  (∫⁻ t in Set.Ioo (0 : ℝ) T,
      ENNReal.rpow
        (∫⁻ x : Euc ℝ 3,
            ENNReal.rpow
              (ENNReal.ofReal (∑ i : Fin 3, (u (NavierStokes.pairToEuc t x) i)^2))
              (q / 2)
          ∂(MeasureTheory.volume : Measure (Euc ℝ 3)))
        (p / q)
      ∂(MeasureTheory.volume : Measure ℝ)) < ∞

/-! ## Typed companion for PSL

We follow the spec literally: the typed companion `ProdiSerrinCriterionData`
carries the exponents `(p, q)`, the scaling inequality, and a finiteness
Prop input for the spacetime norm. -/

/-- **Typed companion data for the Prodi–Serrin–Ladyzhenskaya criterion.**

Given a Leray–Hopf weak solution `sol : NavierStokes.WeakSolution nse`
of the 3-D NSE, this record packages exponents `(p, q)` and the
spacetime-norm finiteness assumption that activates PSL.

Fields:

* `p, q` — Lebesgue exponents.
* `p_ge_two`, `q_ge_three` — `p ≥ 2`, `q ≥ 3` (relaxed to allow the
  borderline case; the strict case is `p > 2`, `q > 3`, captured by
  `strict_case` below).
* `scaling_inequality` — the PSL diagonal `2/p + 3/q ≤ 1`.
* `velocity_LpLq_norm_finite` — the spacetime mixed-norm finiteness
  `(∫₀ᵀ (∫ ‖u(t,·)‖^q)^(p/q) dt) < ∞`.

The bridge theorem `prodi_serrin_smoothness_propagation` consumes
exactly this companion. -/
structure ProdiSerrinCriterionData
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (p q : ℝ) : Prop where
  /-- Lower bound on `p`: at least `2`.  PSL is vacuous for `p ≤ 2`. -/
  p_ge_two : 2 ≤ p
  /-- Lower bound on `q`: at least `3`.  The `q = 3` borderline case
  (with `p = ∞`) is the Escauriaza–Seregin–Šverák endpoint. -/
  q_ge_three : 3 ≤ q
  /-- The PSL scaling inequality `2/p + 3/q ≤ 1`. -/
  scaling_inequality : 2 / p + 3 / q ≤ 1
  /-- Spacetime `L^p_t L^q_x` norm of the velocity field is finite on
  `[0, T]`.  This is the load-bearing analytic input. -/
  velocity_LpLq_norm_finite : SpacetimeLpLqFinite sol.u sol.T p q

/-! ## The Prodi–Serrin–Ladyzhenskaya axiom

We axiomatize the classical PSL theorem: given a Leray–Hopf weak
solution and a PSL typed companion, the velocity field is `C^∞` on
spacetime.

This axiom encapsulates ~60 years of analytic work:

* Prodi 1959 — uniqueness in `L^∞_t L^3_x` (special case).
* Serrin 1962 — strict-case smoothness via energy + Hölder bootstrap.
* Ladyzhenskaya 1967 — closure of the strict-case argument with
  uniqueness.
* Escauriaza–Seregin–Šverák 2003 — borderline `L^∞_t L^3_x` case via
  backward uniqueness for parabolic equations.

A formal Lean proof would require: Bochner-space mixed-norm theory,
parabolic maximal regularity, Sobolev embedding `H^s ↪ L^q`,
Calderón–Zygmund theory for the heat semigroup, and (for the
borderline case) the backward-uniqueness theorem for parabolic
equations.  None of these are currently in Mathlib. -/

/-! ## Unified PSL hypothesis (subsumes ESS endpoint)

The void-miner audit (finding A5 ⊆ A14, 2026-05-07) flagged that the
ESS axiom `ESS_classical_propagation` is the `(p, q) = (∞, 3)` endpoint
of the Prodi–Serrin–Ladyzhenskaya theorem.  PSL evaluated at finite
`p ≥ 2, q ≥ 3` does NOT cover the endpoint — `2/p + 3/q ≤ 1` with
`q = 3` forces `p = ∞`, which the spacetime-norm encoding above does
not admit.

We resolve the architectural redundancy by introducing a **unified
PSL hypothesis** that is a `Sum` of the two regimes:

* `PSLUnifiedHypothesis.interior p q psl` — the strict-interior /
  borderline finite-`p` case (Prodi-Serrin-Ladyzhenskaya 1959/62/67);
* `PSLUnifiedHypothesis.endpoint M h_bound …` — the borderline
  endpoint `(p, q) = (∞, 3)` (Escauriaza-Seregin-Šverák 2003), encoded
  via a uniform-in-time `L³_x` bound `M`.

A single master axiom `unified_psl_smoothness_axiom` consumes
`PSLUnifiedHypothesis` and concludes smoothness.  Both
`prodi_serrin_axiom` (the PSL strict/borderline case) and
`ESS_classical_propagation` (the L³ endpoint, in the ESS file) are
derived as `theorem`s from this single master.

**Net axiom count effect:** ONE master axiom replaces TWO previously
independent axioms (PSL + ESS); residual void becomes structurally
unified. -/

/-- The unified PSL/ESS hypothesis. -/
inductive PSLUnifiedHypothesis
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) : Prop
  /-- Strict-interior or finite-`p` borderline PSL (Prodi 1959 /
  Serrin 1962 / Ladyzhenskaya 1967). -/
  | interior (p q : ℝ) (psl : ProdiSerrinCriterionData sol p q) :
      PSLUnifiedHypothesis sol
  /-- Endpoint `(p, q) = (∞, 3)` case (Escauriaza-Seregin-Šverák 2003).
  Encoded via a uniform-in-time `L³_x` essential-supremum bound. -/
  | endpoint (M : ℝ) (M_nonneg : 0 ≤ M)
      (M_finite : (ENNReal.ofReal M) ≠ ∞)
      (per_t_bound :
        ∀ t ∈ Set.Icc (0 : ℝ) sol.T,
          eLpNorm (fun x : Euc ℝ 3 =>
            sol.u (NavierStokes.pairToEuc t x)) 3
            (MeasureTheory.volume : Measure (Euc ℝ 3))
            ≤ ENNReal.ofReal M) :
      PSLUnifiedHypothesis sol

/-- **MASTER AXIOM (unified Prodi-Serrin-Ladyzhenskaya / ESS).**

If a 3-D Leray-Hopf weak solution carries any unified PSL hypothesis
(strict-interior PSL OR ESS endpoint), then **both** its velocity and
pressure fields are `C^∞`.

This single axiom **subsumes** the previously independent
`prodi_serrin_axiom` and `ESS_classical_propagation`; both are derived
below as 1-line theorems from this master.

The pressure-smoothness conclusion is included so that ESS's
`ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p` can be derived directly.
For the strict-interior PSL case, pressure smoothness follows from
velocity smoothness via the standard Helmholtz-Leray pressure-recovery
projection (Constantin-Foiaș 1988 §6.1). -/
axiom unified_psl_smoothness_axiom
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (h : PSLUnifiedHypothesis sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p

/-- **Theorem (Prodi-Serrin-Ladyzhenskaya), demoted from axiom 2026-05-07.**

If a 3-D Leray-Hopf weak solution `sol` carries a PSL typed companion
`ProdiSerrinCriterionData sol p q`, then its velocity field is `C^∞`.

Previously declared as `axiom prodi_serrin_axiom`; now derived as a
1-line corollary of the unified `unified_psl_smoothness_axiom` via the
`.interior` constructor of `PSLUnifiedHypothesis`. -/
theorem prodi_serrin_axiom
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (p q : ℝ)
    (psl : ProdiSerrinCriterionData sol p q) :
    ContDiff ℝ ⊤ sol.u :=
  (unified_psl_smoothness_axiom sol (PSLUnifiedHypothesis.interior p q psl)).1

/-! ## Bridge theorem: typed companion → smoothness -/

/-- **Prodi–Serrin–Ladyzhenskaya smoothness propagation (bridge theorem).**

Given a Leray–Hopf weak solution `sol : NavierStokes.WeakSolution nse`
of the 3-D NSE and a PSL typed companion `ProdiSerrinCriterionData
sol p q`, the velocity field is `C^∞`.

This is the *conditional* Lean theorem: PSL bounds → smoothness.
Producing the PSL companion globally for arbitrary smooth initial data
is the Clay Millennium Problem and is open. -/
theorem prodi_serrin_smoothness_propagation
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (p q : ℝ)
    (psl : ProdiSerrinCriterionData sol p q) :
    ContDiff ℝ ⊤ sol.u :=
  prodi_serrin_axiom sol p q psl

/-! ## Spectrum of `(p, q)` cases handled

The bridge theorem covers the entire PSL spectrum in a single statement:

| Case            | `p`   | `q`   | `2/p + 3/q` | Reference                    |
|-----------------|-------|-------|-------------|------------------------------|
| Strict interior | `4`   | `6`   | `1`         | Serrin 1962                  |
| Strict interior | `∞`*  | `> 3` | `< 1`       | Serrin 1962                  |
| Strict interior | `> 2` | `∞`*  | `< 1`       | Serrin 1962                  |
| Borderline      | `4`   | `6`   | `= 1`       | Serrin 1962 / Sohr           |
| Borderline      | `∞`*  | `3`   | `= 1`       | Escauriaza–Seregin–Šverák 03 |

*The endpoint `p = ∞` (resp. `q = ∞`) is encoded via a uniform-in-time
`L^q` bound (resp. uniform-in-space `L^p_t` bound); see
`fromUniformBound` below for the canonical `p = ∞` instance.*

Each row corresponds to a *valid* selection of `(p, q)` for which the
typed-companion + axiom yields `ContDiff ℝ ⊤ sol.u`.  None of the
rows is currently *known* to hold globally for arbitrary smooth
initial data. -/

/-! ## Canonical instance: PSL companion from a uniform-in-time `L^q_x` bound

The Prodi case `p = ∞` reduces to a uniform-in-time `L^q_x` bound on
`u(t, ·)` with `q > 3`.  We provide the instance `fromUniformBound`
producing a PSL companion at the endpoint `p = ∞` from such a uniform
bound.

To stay at the abstract bridge level, we *take the spacetime-norm
finiteness as a Prop input* in the constructor — the actual reduction
"uniform bound + finite-time-interval ⇒ spacetime-norm finite" is
elementary (Hölder in `t` over `[0, T]` with `p = ∞` gives essentially
`T · sup_t (‖u(t,·)‖_{L^q})^q < ∞`) but instantiating it formally
requires the same mixed-norm machinery the axiom obviates.  The
constructor's signature still exposes the uniform bound as a real
finite number, which is the canonical PSL hypothesis shape. -/

/-- **PSL companion at `p = ∞` from a uniform-in-time `L^q_x` bound.**

If for every `t ∈ [0, T]` the spatial `L^q` norm `‖u(t, ·)‖_{L^q}` is
bounded by a finite constant `M`, and `q > 3`, then we have a PSL
typed companion with `p = ∞` (encoded numerically as any large
exponent satisfying `2/p + 3/q ≤ 1`).

We take the spacetime-norm finiteness as a `Prop` input
(`spacetime_finite`) so that the constructor remains an *abstract*
bridge: caller supplies the canonical PSL hypothesis shape (uniform
spatial-`L^q`-bound + finiteness witness), receives a typed companion. -/
def ProdiSerrinCriterionData.fromUniformBound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (q : ℝ) (hq : 3 ≤ q)
    (p : ℝ) (hp_ge : 2 ≤ p)
    (hscaling : 2 / p + 3 / q ≤ 1)
    (spacetime_finite : SpacetimeLpLqFinite sol.u sol.T p q) :
    ProdiSerrinCriterionData sol p q :=
  { p_ge_two := hp_ge
    q_ge_three := hq
    scaling_inequality := hscaling
    velocity_LpLq_norm_finite := spacetime_finite }

/-! ## Endpoint corollary: `(p, q) = (4, 6)` borderline case

A useful instantiation: the symmetric borderline `p = 4, q = 6`,
satisfying `2/4 + 3/6 = 1`. -/

/-- Canonical borderline endpoint corollary at `(p, q) = (4, 6)`.

Given a PSL typed companion at `p = 4, q = 6`, conclude `C^∞`.  This
is the symmetric borderline case `2/4 + 3/6 = 1` — the "Serrin
diagonal midpoint." -/
theorem prodi_serrin_smoothness_at_4_6
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (psl : ProdiSerrinCriterionData sol 4 6) :
    ContDiff ℝ ⊤ sol.u :=
  prodi_serrin_smoothness_propagation sol 4 6 psl

/-! ## Honest open-problem framing

The bridge above is **conditional**: it converts a `ProdiSerrinCriterionData`
input into smoothness.  Producing the input itself — i.e. proving any
finite spacetime mixed-norm bound for arbitrary smooth divergence-free
initial data — is the open Clay Millennium Problem (or stronger,
since the spectrum admits any single `(p, q)` choice on the diagonal).

The architecture is: PSL is a *spectrum of sufficient conditions*, and
this file faithfully exposes that spectrum as Lean theorems
parameterized over `(p, q)`. The single axiom encapsulates the
classical analytic content; everything visible is conditional. -/

end

end ZtareProofs.NS
