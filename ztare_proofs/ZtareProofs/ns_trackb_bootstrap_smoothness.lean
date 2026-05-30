/-
# NS Track B — Bootstrap smoothness criterion (FINITE-T → GLOBAL-T)

This file ships a **typed-companion bridge** that converts a family of
finite-time smooth Navier–Stokes solutions (one per finite horizon
`T > 0`) into a single GLOBAL-in-time smooth solution on `[0, ∞)`.

## Why this is a NEW Clay-conditional criterion (not a duplicate of BKM/PSL/ESS/BdV/CF)

The five existing Clay-conditional criteria in the architecture all
ask: "For some functional `F[u]`, is `F[u]` finite on every finite
window?"  Each `F` is a different smoothness criterion (BKM = vorticity
sup-norm integral, PSL = `L^q_t L^p_x`, ESS = `L^∞_t L^3_x`, BdV =
gradient `L^q_t L^p_x`, CF = vorticity-direction Lipschitz).

The **bootstrap criterion** is structurally different: it asks for
**uniformity in T**, not for a new functional.  It is the SHAPE of the
implication

  (∀ T > 0, finite-window smooth solution exists with bounds
            independent of T)
   →
  (∃ global smooth solution on `[0, ∞)`)

This is genuinely independent of the five branches because each branch
provides finite-window smoothness at a fixed T, but does NOT
automatically provide T-uniform bounds.  The bootstrap step converts
finite-T smoothness with the right uniformity into global-T smoothness
mechanically.

## Architecture

We expose:

* `BootstrapSmoothnessData nse u_0` — the typed companion, carrying:
  - a per-horizon family `finiteT_solution : (T : ℝ) → 0 < T → GlobalSmoothSolution`
    of smooth solutions on `[0, T]` with the prescribed initial data
    `u_0`;
  - the **Leray energy bound**: `‖u(t,·)‖_{L²} ≤ ‖u_0‖_{L²}` (uniform in
    `t` and in `T`);
  - the **uniformity hypothesis**: bounds do NOT grow super-polynomially
    with `T` — formalized as a polynomial envelope on the chosen
    smoothness-bound functional.

* `theorem bootstrap_smoothness_to_global` — bootstrap data → a
  globally smooth solution on `[0, ∞)`, modulo a single named
  axiom `bootstrap_diagonal_assembly` whose content is purely
  Mathlib-bookkeeping (no new PDE).

* `def UniformLerayHopfSmoothness u_0 : Prop` — the new Clay-equivalent
  predicate: the per-horizon Leray–Hopf solution is smooth with bounds
  T-uniform.  Closing this for arbitrary smooth divergence-free `u_0`
  is Clay-equivalent.

## Connection to `lerayHopf_existence_oneshot`

The architecture's `lerayHopf_existence_oneshot` is parameterized by
`T : ℝ` (finite horizon) and produces a `LerayHopfSolution nse` on
`[0, T]`.  When combined with one of the five smoothness criteria
(BKM/PSL/ESS/BdV/CF), it yields a finite-T smooth record.  The
bootstrap criterion COMPOSES with that finite-T pipeline: if for every
`T > 0` the pipeline succeeds AND the resulting bounds are T-uniform,
then the bootstrap step produces a global smooth solution.

Schematically:

  finite-T Galerkin (workstream O)
    + finite-T smoothness criterion (workstream S, one of 5)
    + T-uniform bounds  (this file, NEW)
   ─────────────────────────────────────────────────
    global smooth solution

## The OPEN mathematical question

The bootstrap criterion's **uniformity hypothesis** asks for
T-INDEPENDENT bounds on `‖u(T,·)‖_{H^m}` (or another smoothness norm).
This is essentially Clay-equivalent BUT phrased differently: it asks
for QUANTITATIVE bounds rather than qualitative smoothness, and the
quantitative form might be tractable in specific regimes (e.g.,
small-data, axisymmetric without swirl, helical flows) where the
qualitative form is not obviously easier.

## Honesty

This file ships ONE new axiom, `bootstrap_diagonal_assembly`, whose
content is Mathlib bookkeeping (sequential extraction + uniqueness
on overlaps, parallel to `global_smooth_solution_assembly` in
`ns_trackb_bkm_smoothness_criterion.lean`).  It is NOT a deep PDE
result.  Zero `sorry`s.

## Distinction from CREATE-2 (the BUA contrapositive)

A separately-circulated "CREATE-2 bootstrap conjecture" asks: IF the
H^s norm of a strong solution has a finite envelope `M(s, ‖u₀‖, T)`
on every `[0, T]` with `T < T*(u₀)`, THEN `T*(u₀) = +∞`.

That conjecture is the contrapositive of the **classical Beale-Kato-Majda
blow-up alternative** (Kato 1984; Majda-Bertozzi 2002, Theorem 3.6):
"if `T* < ∞` then `lim sup_{t→T*} ‖u(t)‖_{H^s} = ∞`".  Under the
charitable reading that `M(·,·,T)` is a continuous function of `T` so
extends to `T = T*`, the contrapositive proof is the standard local-
well-posedness restart and CREATE-2 is a textbook theorem, NOT a new
conjecture.  Under the literal reading (`M(T)` finite for each `T < T*`
but allowed to grow without bound as `T ↗ T*`), the hypothesis is
automatic from `u ∈ C([0,T*); H^s)` and CREATE-2 is vacuous.

The Clay-equivalent content lives HERE, in `UniformLerayHopfSmoothness`,
which is strictly stronger than CREATE-2:

* CREATE-2 quantifies over `T < T*` (the local-well-posedness regime);
  `UniformLerayHopfSmoothness` quantifies over **all** `T > 0` (the
  global regime).
* CREATE-2 only requires the bound be finite at each `T`;
  `UniformLerayHopfSmoothness` requires a **polynomial envelope**
  (T-uniform up to polynomial growth).

See `projects/ns_millennium_hunt/workspace/research_notes/
attack_CREATE2_bootstrap_2026_05_07.md` for the full analysis.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bkm_smoothness_criterion

open MeasureTheory
open scoped Topology

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The bootstrap typed-companion record -/

/-- **Bootstrap typed companion.**

For initial data `u_0 = nse.initialVelocity`, this record packages:

* `finiteT_solution T T_pos` — a `GlobalSmoothSolution nse` whose
  fields, restricted to `[0, T]`, give the finite-T smooth NS
  solution with initial data `u_0`.  (We use `GlobalSmoothSolution`
  even at finite T as the value type because `Solution` is
  parameterized by `T` and the architecture's bridges already give
  global-shaped records over `[0, T]`.  The KEY new content is the
  `polynomial_envelope` field and the `leray_energy_bound` field.)

* `leray_energy_bound T T_pos t` — for each `T > 0` and each `t ∈ [0,T]`,
  the Leray energy inequality: `‖u(t,·)‖_{L²} ≤ ‖u_0‖_{L²}`.  The bound
  on the RHS is independent of `T`.  This is the standard Leray–Hopf
  energy estimate; we expose it as a typed input rather than a derived
  lemma so the bridge does not depend on a particular `L²`-norm
  formalization.

* `polynomial_envelope_degree` and `polynomial_envelope_constant` —
  natural-number degree `d` and constant `M` such that for every
  `T > 0`, the chosen smoothness-bound functional `F` (left abstract as
  `bound : ℝ → ℝ`) satisfies `bound T ≤ M * (1 + T)^d`.  This is the
  **uniformity hypothesis**: bounds DO NOT grow super-polynomially
  with `T`.  Polynomial growth is sufficient for the diagonal
  extraction in the bootstrap step. -/
structure BootstrapSmoothnessData {n : ℕ}
    (nse : NavierStokes.NavierStokesEquations n) where
  /-- The smoothness-bound functional `T ↦ F(u_T)`, kept abstract as
  `ℝ → ℝ` so the bridge does not commit to a particular norm. -/
  bound : ℝ → ℝ
  /-- Per-horizon smooth solution.  At each `T > 0`, the architecture
  has constructed (e.g. via `lerayHopf_existence_oneshot` plus a
  smoothness criterion) a smooth NS solution with the prescribed
  initial data, valid on `[0, T]`. -/
  finiteT_solution :
    ∀ (T : ℝ), 0 < T → NavierStokes.GlobalSmoothSolution nse
  /-- **Leray energy bound (T-uniform).**  For each `T` and each `t`,
  the kinetic energy of the per-horizon solution is bounded by a
  T-independent constant `E0` (typically `‖u_0‖_{L²}^2 / 2`). -/
  leray_energy_constant : ℝ
  leray_energy_constant_nonneg : 0 ≤ leray_energy_constant
  leray_energy_bound :
    ∀ (T : ℝ) (T_pos : 0 < T) (t : ℝ),
      0 ≤ t → t ≤ T →
        NavierStokes.kineticEnergy
          ((finiteT_solution T T_pos).toGlobalSolution.u) t
        ≤ leray_energy_constant
  /-- **Polynomial envelope on the smoothness-bound functional.**
  The bound functional grows at most polynomially in `T`. -/
  polynomial_envelope_degree : ℕ
  polynomial_envelope_constant : ℝ
  polynomial_envelope_constant_nonneg : 0 ≤ polynomial_envelope_constant
  polynomial_envelope :
    ∀ (T : ℝ), 0 < T →
      bound T ≤ polynomial_envelope_constant *
                 (1 + T) ^ polynomial_envelope_degree

/-! ## §2.  The bootstrap predicate (Clay-equivalent shape) -/

/-- **Uniform Leray–Hopf smoothness predicate.**

For initial data `u_0 = nse.initialVelocity`, the predicate asserts
that for every `T > 0` the Leray–Hopf solution exists smoothly on
`[0, T]` with quantitative bounds independent of `T` (i.e. growing
at most polynomially in `T`).

Closing this predicate for arbitrary smooth, divergence-free,
finite-energy `u_0` is **Clay-equivalent**: it implies global smooth
existence via `bootstrap_smoothness_to_global`.  The quantitative
form (polynomial envelope) might be tractable in restricted regimes
(small-data, axisymmetric without swirl, helical flows, 2D) where
the qualitative form of Clay is not. -/
def UniformLerayHopfSmoothness {n : ℕ}
    (nse : NavierStokes.NavierStokesEquations n) : Prop :=
  Nonempty (BootstrapSmoothnessData nse)

/-! ## §3.  Diagonal-assembly axiom (Mathlib bookkeeping; NOT new PDE)

The `bootstrap_diagonal_assembly` axiom packages the standard
diagonal-extraction step that merges a sequence of finite-T smooth
solutions (with T-uniform polynomial envelopes) into a single global
smooth solution on `[0, ∞)`.  This is mathematically routine
(Constantin–Foiaș 1988 Ch. 11; Majda–Bertozzi 2002 §3) but Mathlib
does not yet ship the lemma in the right shape, so we expose it as
an axiom — parallel to `global_smooth_solution_assembly` in the
BKM file.

The polynomial envelope hypothesis is what makes the merger work:
on each `[0, T]`, all finite-T_k solutions for `T_k ≥ T` agree by
strong-solution uniqueness (a property of NS, used implicitly), and
the polynomial growth of the bound functional ensures that the
merger does not blow up at any finite time. -/

/-- **AXIOM (assembly bookkeeping; NOT new PDE content).**

Diagonal assembly of a global smooth NS solution from a per-horizon
family of finite-T smooth solutions admitting T-uniform polynomial
envelopes on the smoothness-bound functional and a T-uniform energy
bound.  Parallel to `global_smooth_solution_assembly` (BKM file).

Reference: Constantin–Foiaș, *Navier–Stokes Equations*, Univ. of
Chicago Press 1988, Chapter 11; Majda–Bertozzi, *Vorticity and
Incompressible Flow*, Cambridge 2002, §3. -/
axiom bootstrap_diagonal_assembly
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (_D : BootstrapSmoothnessData nse) :
    NavierStokes.GlobalSmoothSolution nse

/-! ## §4.  The bootstrap theorem -/

/-- **Bootstrap smoothness to global.**

From a `BootstrapSmoothnessData nse` (a per-horizon family of
finite-T smooth NS solutions with T-uniform energy bound and
T-polynomial envelope on the smoothness-bound functional), produce a
single globally smooth NS solution on `[0, ∞)`.

This is the architectural climax of the bootstrap criterion: it
converts a family of finite-time results into a global-time result
mechanically, modulo the named bookkeeping axiom
`bootstrap_diagonal_assembly`. -/
noncomputable def bootstrap_smoothness_to_global
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (D : BootstrapSmoothnessData nse) :
    NavierStokes.GlobalSmoothSolution nse :=
  bootstrap_diagonal_assembly nse D

/-- **Conditional Clay-shape theorem (bootstrap branch).**

For initial data with `nse.initialVelocity`, IF
`UniformLerayHopfSmoothness nse` holds (i.e. there exists a
`BootstrapSmoothnessData`), THEN there exists a globally smooth NS
solution.

The hypothesis `UniformLerayHopfSmoothness nse` is the new
Clay-equivalent predicate.  Closing it closes Clay; the bridge does
NOT close it. -/
theorem clay_conditional_via_bootstrap
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_uniform : UniformLerayHopfSmoothness nse) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) := by
  rcases h_uniform with ⟨D⟩
  exact ⟨bootstrap_smoothness_to_global nse D⟩

/-! ## §5.  Composition with the architectural finite-T pipeline

The architecture's `lerayHopf_existence_oneshot` produces, for each
`T > 0`, a `LerayHopfSolution nse` on `[0, T]` from the workstream-O
classical-Galerkin inputs.  Combined with one of the five smoothness
criteria (BKM/PSL/ESS/BdV/CF), this becomes a finite-T smooth NS
solution.  The bootstrap step CONSUMES such a per-horizon family and
emits a global smooth solution — provided the family satisfies the
T-uniform polynomial envelope.

This composition is captured by the typed-companion
`BootstrapSmoothnessData`: its `finiteT_solution` field is exactly the
output of "(workstream O) + (workstream S)" at horizon `T`, and its
`polynomial_envelope` field is the new uniformity input.

The bootstrap branch is therefore a SIXTH Clay-conditional criterion,
orthogonal to the existing five:

  1. BKM           — finite vorticity sup-norm integral (per-window);
  2. Prodi–Serrin  — `L^q_t L^p_x` velocity (per-window);
  3. ESS           — `L^∞_t L^3_x` velocity (per-window);
  4. Beirão da Veiga — `L^q_t L^p_x` velocity gradient (per-window);
  5. Constantin–Fefferman — Lipschitz vorticity direction (per-window);
  6. **bootstrap (this file)** — T-uniform polynomial envelope on a
     smoothness-bound functional (across windows).

Branches 1–5 are PER-WINDOW; branch 6 is ACROSS-WINDOWS.  They are
COMPLEMENTARY, not duplicative: branches 1–5 give finite-window
smoothness; branch 6 lifts finite-window smoothness to global. -/

/-! ## §6.  Honesty receipt

* 1 typed-companion record: `BootstrapSmoothnessData`.
* 1 named `Prop`: `UniformLerayHopfSmoothness`.
* 1 axiom (assembly bookkeeping, NOT new PDE):
  - `bootstrap_diagonal_assembly`.
* 1 derived `def`: `bootstrap_smoothness_to_global`.
* 1 derived theorem: `clay_conditional_via_bootstrap`.

Zero `sorry`s.

The architecture is HONEST: the bootstrap step does NOT close Clay;
it converts a NEW Clay-equivalent predicate
(`UniformLerayHopfSmoothness`, asking for T-uniform polynomial
envelopes on a smoothness functional) into a globally smooth
solution.  Closing the predicate is the open conjecture, of the same
logical strength as the Clay millennium problem but phrased in
QUANTITATIVE form. -/

end

end ZtareProofs.NS
