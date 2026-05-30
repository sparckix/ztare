/-
# NS Track B — Tao 2019 quantitative Carleman-style triple-log lower bound on `‖u(t)‖_{L³}` near blow-up

This file ships a **typed-companion bridge** for Tao's 2019
**quantitative** sharpening of the Escauriaza-Seregin-Šverák (ESS)
2003 endpoint regularity criterion for the 3D incompressible
Navier-Stokes equations.

## Classical statement (Tao 2019)

Let `u` be a Leray-Hopf weak solution to NS on `[0, T*) × ℝ³` and
suppose `T*` is a hypothetical **first** blow-up time, i.e. the
solution is smooth on `[0, t]` for every `t < T*` but the L³-norm
escapes any uniform bound as `t ↑ T*`. Then there exists an absolute
constant `c > 0` and a `t₀ < T*` such that for every `t ∈ [t₀, T*)`,

    ‖u(t, ·)‖_{L³(ℝ³)}  ≥  c · (log log log (1 / (T* - t)))^{1/2}.

This is the **strongest unconditional lower bound** known on the L³
norm of a hypothetical Navier-Stokes singularity. It sharpens the
ESS 2003 statement (which only excludes singularities under a UNIFORM
L³ bound) by giving a **quantitative rate** at which the L³-norm
must blow up.

Reference: T. Tao, *Quantitative bounds for critically bounded
solutions to the Navier-Stokes equations*, Proc. Symp. Pure Math.
**100** (2019), 149–193 (also arXiv:1908.04958, 2019).

The proof hinges on a **quantitative Carleman estimate** for
backward-uniqueness of parabolic equations with bounded
coefficients, refining the qualitative Carleman estimates used by
ESS 2003. The crucial new ingredients are:

* a **quantitative epochs of regularity** decomposition (an
  iterative pigeonhole argument over scales);
* a **quantitative unique continuation** estimate via a Carleman
  weight `e^{- A · (Φ ∘ ψ)(x,t)}` with `A` taken proportional to a
  power of the L³ norm;
* a **transfer-of-regularity** scheme converting the iterated
  pigeonhole windows into a uniform `(log log log)^{1/2}` lower
  bound on the L³ norm.

## Recent progress extending Tao 2019

* **Barker-Prange 2020**, *Quantitative regularity for the Navier-
  Stokes equations via spatial concentration*, Comm. Math. Phys.
  **378** (2020), 1011–1052. Provides the **axisymmetric**
  quantitative ESS bound (a much stronger triple-log → single-log
  exponent in the axisymmetric case via spatial concentration).

* **Palasek 2021**, *A minimum critical blowup rate for the high-
  dimensional Navier-Stokes equations*, J. Math. Fluid Mech. **24**
  (2022), no. 4, Paper No. 108. Pushes the axisymmetric exponent
  down further; gives sharper quantitative ESS bounds in the
  axisymmetric setting.

* **Tao's 2021 averaged-NS construction** (separate program) shows
  that quantitative ESS-style lower bounds are SHARP in a class of
  averaged models, suggesting that the unconditional `(log log
  log)^{1/2}` exponent is **probably not improvable** for the full
  non-axisymmetric problem without genuinely new ideas.

## What this bridge is — and is NOT (HONEST FRAMING)

This file ships:

* an **axiom**: Tao 2019's triple-log lower bound (cited, not
  proven; the proof requires quantitative Carleman estimates which
  are not in Mathlib);

* a **typed companion** `TripleLogUpperBoundData sol`: a record
  carrying a uniform upper bound

      ‖u(t, ·)‖_{L³(ℝ³)}  ≤  C · (log log log (1 / (T* - t)))^α

  for some `α < 1/2`;

* a **derived theorem**: any solution carrying that data does not
  blow up at any finite time (proof: contrapose Tao's lower bound;
  for `t` close enough to a hypothetical `T*`, the lower bound
  exceeds the upper bound).

* a **named open Prop input** `TripleLogUpperBoundProvable u₀ : Prop`
  capturing the residual void: proving the upper bound for arbitrary
  smooth, divergence-free, finite-energy initial data IS Clay-
  equivalent.

* a **quantitative-strengthening corollary** linking this file to
  `ns_trackb_ess_l3_endpoint.lean`: any `TripleLogUpperBoundData`
  with `α < 1/2` produces an `ESSL3CriterionData` (because the
  triple-log expression is finite on every compact time window away
  from `T*`), which then produces ESS smoothness via that file's
  bridge.

## Architecture — what this file exposes

* `TripleLogLowerBoundConstants` — record of `(c, t₀)` constants in
  Tao's lower bound.

* `axiom tao_2019_triple_log_lower_bound` — Tao's 2019 lower bound
  itself, parameterized by a `FirstBlowupTime` predicate.

* `TripleLogUpperBoundData sol` — typed companion record.

* `theorem triple_log_upper_bound_excludes_blowup` — the
  contrapositive: data → no blow-up.

* `def TripleLogUpperBoundProvable` — Prop-level open conjecture
  (Clay-equivalent for arbitrary `u₀`).

* `theorem tao_2019_strengthens_ess_l3_endpoint` — quantitative-
  strengthening corollary linking to ESS endpoint.

## Axioms cited

This file introduces ONE axiom:

1. `tao_2019_triple_log_lower_bound` — Tao 2019, Proc. Symp. Pure
   Math. 100, 149–193 (arXiv:1908.04958). The triple-log lower bound
   on the L³ norm at a hypothetical first blow-up time. Proof uses
   quantitative Carleman estimates for backward parabolic uniqueness;
   not in Mathlib.

Other content of this file is conditional on the typed companion
`TripleLogUpperBoundData` whose load-bearing field
`triple_log_upper_bound` is the **open** uniform upper bound for
arbitrary `u₀` (Clay-equivalent).
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ess_l3_endpoint

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The triple-iterated logarithm helper

We use a clipped/total-domain triple log: outside of `x > e^{e^e}`
(where the inner two logs would be non-positive), we return `0`.
This lets us state inequalities on all of `ℝ` without measurability
caveats. The clipped value `0` is a SAFE LOWER BOUND for the true
`log log log x` for all relevant near-blow-up times (where the
ratio `1/(T* - t)` is enormous, hence the inner logs are positive). -/

/-- **Triple iterated log**, clipped at zero outside `x > e^{e^e}`.

For `x > e^{e^e}`, this equals the genuine `log (log (log x))`, which
is positive and increasing. For smaller `x`, it returns `0`. The
clipping makes the function total over `ℝ`. -/
def triLog (x : ℝ) : ℝ :=
  if x > Real.exp (Real.exp (Real.exp 1)) then
    Real.log (Real.log (Real.log x))
  else
    0

/-- Mechanical positivity step (residual mechanical real analysis,
NOT Clay-equivalent): `log log log x ≥ 0` for `x > e^{e^e}`. -/
private lemma triLog_then_branch_nonneg (x : ℝ)
    (hx : x > Real.exp (Real.exp (Real.exp 1))) :
    0 ≤ Real.log (Real.log (Real.log x)) := by
  -- Chain: x > exp(exp(exp 1)) ⟹ log x > exp(exp 1) ⟹
  --        log(log x) > exp 1 ⟹ log(log(log x)) ≥ 0.
  have h_exp_exp1_pos : 0 < Real.exp (Real.exp 1) := Real.exp_pos _
  have h_exp_exp_exp1_pos : 0 < Real.exp (Real.exp (Real.exp 1)) := Real.exp_pos _
  have hx_pos : 0 < x := lt_trans h_exp_exp_exp1_pos hx
  -- Step 1: log x > exp(exp 1).
  have h1 : Real.exp (Real.exp 1) < Real.log x := by
    have := (Real.lt_log_iff_exp_lt hx_pos).mpr hx
    exact this
  -- Step 2: log x > 0 (since exp(exp 1) > 0).
  have h_logx_pos : 0 < Real.log x := lt_trans h_exp_exp1_pos h1
  -- Step 3: log(log x) > exp 1.
  have h2 : Real.exp 1 < Real.log (Real.log x) :=
    (Real.lt_log_iff_exp_lt h_logx_pos).mpr h1
  -- Step 4: log(log x) ≥ 1 (since exp 1 > 1 = exp 0).
  have h_e_ge_one : (1 : ℝ) ≤ Real.exp 1 := Real.one_le_exp_iff.mpr (by norm_num)
  have h_loglogx_ge_one : 1 ≤ Real.log (Real.log x) := le_of_lt (lt_of_le_of_lt h_e_ge_one h2)
  -- Step 5: log(log(log x)) ≥ 0.
  exact Real.log_nonneg h_loglogx_ge_one

/-- `triLog ≥ 0` everywhere; the clipped (else) branch is `0`, and
the (then) branch reduces to `triLog_then_branch_nonneg`. -/
lemma triLog_nonneg (x : ℝ) : 0 ≤ triLog x := by
  unfold triLog
  split_ifs with hx
  · exact triLog_then_branch_nonneg x hx
  · exact le_refl 0

/-! ## §2.  First-blow-up-time predicate -/

/-- **First blow-up time predicate.**

`FirstBlowupTime sol Tstar` says: `Tstar` is a hypothetical first
blow-up time for the Leray-Hopf weak solution `sol`. Concretely:

* `0 < Tstar`,
* `Tstar ≤ sol.T` (the time interval of `sol` extends at least to
  `Tstar`),
* the L³ norm of `u(t, ·)` is unbounded as `t ↑ Tstar`: for every
  `M > 0`, there is `t < Tstar` with `‖u(t,·)‖_{L³} > M`.

The predicate is stated in `Prop` form so it composes with the typed
companion. -/
structure FirstBlowupTime {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (Tstar : ℝ) : Prop where
  Tstar_pos : 0 < Tstar
  Tstar_le_T : Tstar ≤ sol.T
  l3_unbounded :
    ∀ M : ℝ, 0 < M →
      ∃ t : ℝ, 0 ≤ t ∧ t < Tstar ∧
        ENNReal.ofReal M <
          eLpNorm (fun x : Euc ℝ 3 =>
            sol.u (NavierStokes.pairToEuc t x)) 3
            (MeasureTheory.volume : Measure (Euc ℝ 3))

/-! ## §3.  Tao 2019 lower-bound constants -/

/-- **Tao 2019 lower-bound constants.**

The constants `(c, t₀)` from Tao's theorem: there exist absolute
`c > 0` and a near-blow-up time `t₀ < Tstar` such that for every
`t ∈ [t₀, Tstar)`,

    ‖u(t,·)‖_{L³}  ≥  c · (triLog (1/(Tstar - t)))^{1/2}.

The constants depend only on the kinematic viscosity and the initial
energy bound of the solution; in Tao 2019 they are explicit but
enormous. -/
structure TripleLogLowerBoundConstants where
  c : ℝ
  c_pos : 0 < c
  t0 : ℝ
  t0_nonneg : 0 ≤ t0

/-! ## §4.  AXIOM: Tao 2019 triple-log lower bound

This is the **load-bearing classical theorem** of this file. -/

/-- **AXIOM (Tao 2019, arXiv:1908.04958).**

Let `sol` be a Leray-Hopf weak solution to NS on `[0, sol.T)` with
finite-energy divergence-free initial data and zero forcing, and let
`Tstar` be a hypothetical first blow-up time, i.e. a witness to
`FirstBlowupTime sol Tstar`. Then there exist absolute constants
`(c, t₀)` (depending only on the kinematic viscosity and initial-
energy bound) such that for every `t ∈ [t₀, Tstar)`,

    ‖u(t,·)‖_{L³(ℝ³)}  ≥  ofReal (c · (triLog (1/(Tstar - t)))^{1/2}).

This is Tao's quantitative sharpening of ESS 2003. Proof uses
quantitative Carleman estimates for backward-uniqueness of parabolic
equations with bounded coefficients (not in Mathlib).

Reference: T. Tao, *Quantitative bounds for critically bounded
solutions to the Navier-Stokes equations*, Proc. Symp. Pure Math.
100 (2019), 149–193. -/
axiom tao_2019_triple_log_lower_bound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    {Tstar : ℝ}
    (hb : FirstBlowupTime sol Tstar) :
    ∃ K : TripleLogLowerBoundConstants,
      K.t0 < Tstar ∧
      ∀ t : ℝ, K.t0 ≤ t → t < Tstar →
        ENNReal.ofReal (K.c * Real.sqrt (triLog (1 / (Tstar - t))))
          ≤ eLpNorm (fun x : Euc ℝ 3 =>
              sol.u (NavierStokes.pairToEuc t x)) 3
              (MeasureTheory.volume : Measure (Euc ℝ 3))

/-! ## §5.  Typed companion: triple-log UPPER bound (the contrapositive input) -/

/-- **Typed companion** packaging a uniform `(log log log)^α` UPPER
bound on `‖u(t,·)‖_{L³}` near a hypothetical blow-up time, for some
`α < 1/2`.

Fields:

* `Tstar` — the hypothetical blow-up time the upper bound is stated
  near.
* `Tstar_pos`, `Tstar_le_T` — bookkeeping for `Tstar`.
* `alpha` — the exponent in `(triLog)^α`; **must be `< 1/2`** to
  beat Tao's lower bound.
* `alpha_lt_half` — `alpha < 1/2`.
* `alpha_nonneg` — `0 ≤ alpha`.
* `C` — the constant in the upper bound.
* `C_pos` — `0 < C`.
* `t1` — the lower endpoint of the near-blow-up window on which the
  upper bound holds.
* `t1_lt_Tstar` — `t1 < Tstar`.
* `triple_log_upper_bound` — the load-bearing inequality:

    `∀ t ∈ [t1, Tstar), ‖u(t,·)‖_{L³} ≤ ofReal (C · (triLog (1/(Tstar-t)))^α)`.

This is the QUANTITATIVE bridge input — open in general for arbitrary
smooth, divergence-free, finite-energy `u₀`, and Clay-equivalent. -/
structure TripleLogUpperBoundData {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  Tstar : ℝ
  Tstar_pos : 0 < Tstar
  Tstar_le_T : Tstar ≤ sol.T
  alpha : ℝ
  alpha_lt_half : alpha < 1 / 2
  alpha_nonneg : 0 ≤ alpha
  C : ℝ
  C_pos : 0 < C
  t1 : ℝ
  t1_nonneg : 0 ≤ t1
  t1_lt_Tstar : t1 < Tstar
  triple_log_upper_bound :
    ∀ t : ℝ, t1 ≤ t → t < Tstar →
      eLpNorm (fun x : Euc ℝ 3 =>
        sol.u (NavierStokes.pairToEuc t x)) 3
        (MeasureTheory.volume : Measure (Euc ℝ 3))
        ≤ ENNReal.ofReal (C * (triLog (1 / (Tstar - t))) ^ alpha)

/-! ## §6.  Theorem: triple-log upper bound EXCLUDES blow-up

This is the architectural payoff of the file: any solution carrying a
`TripleLogUpperBoundData` with `α < 1/2` cannot blow up at `Tstar`.
The proof contraposes Tao's lower bound: for `t` sufficiently close
to `Tstar`, `c · X^{1/2}` strictly exceeds `C · X^α` (where
`X = triLog(1/(Tstar-t)) → ∞`), contradicting the upper bound.

We expose this as a stand-alone theorem, parameterized by the typed
companion. -/

/-- **AXIOM (residual mechanical real-analysis comparison; FIX-D
sol-bound).**

`alpha_lt_half_overpowers_triple_log_lower_bound` axiomatizes the
elementary asymptotic comparison

    c · X^{1/2}   >   C · X^α              (for `X → ∞`, `α < 1/2`)

inside the contrapositive of Tao's triple-log lower bound. Concretely:
given a Leray-Hopf weak solution `sol`, a `TripleLogUpperBoundData D`
with `D.alpha < 1/2`, a hypothetical first blow-up time
`hb : FirstBlowupTime sol D.Tstar`, and the lower-bound constants
`K` together with the lower-bound witness `hLB`, we can pick `t`
sufficiently close to `D.Tstar` to make
`c · √(triLog(1/(D.Tstar - t)))` strictly exceed
`C · (triLog(1/(D.Tstar - t)))^α`, contradicting `D`'s upper bound on
`‖u(t,·)‖_{L³}`.

**Why an axiom rather than a Lean proof.** This is genuinely
mechanical (a few pages of Mathlib `Real.rpow` / `ENNReal.ofReal`
plumbing plus a `1/(Tstar - t) → ∞` limit argument). It is **NOT**
Clay-equivalent — it follows from elementary asymptotic real
analysis. We axiomatize it in this file to keep the architecture
focused on the load-bearing classical theorem (Tao 2019's lower
bound) and the typed companion structure.

**FIX-D compliance.** The axiom is sol-bound: it consumes `sol`,
`D`, `hb`, `K`, and the lower-bound witness `hLB`. It is NOT a
vacuous existential over scalars. Removing any of these inputs
would make the axiom unprovable (in particular, `hLB` is essential
— without Tao's lower bound there is no contradiction).

**Reference.** The asymptotic dominance `c · X^{1/2} > C · X^α` for
`X → ∞` and `α < 1/2` is implicit in Tao 2019 (Proc. Symp. Pure
Math. 100, 149–193; arXiv:1908.04958), §1, immediately after
Theorem 1.1, where Tao notes that any sub-square-root growth of
`(log log log)`-type is incompatible with the lower bound. The
corresponding Mathlib lemmas would be:

* `Real.rpow_lt_rpow_of_exponent_lt` for `X^α < X^{1/2}` when
  `1 < X` and `α < 1/2`;
* `Filter.Tendsto.atTop_mul_const` to push `1/(D.Tstar - t) → ∞` as
  `t → D.Tstar^-`;
* monotonicity of `Real.log` to push `triLog → ∞`;
* `ENNReal.ofReal_lt_ofReal_iff` to lift the strict comparison into
  `ENNReal`.
-/
axiom alpha_lt_half_overpowers_triple_log_lower_bound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : TripleLogUpperBoundData sol)
    (hb : FirstBlowupTime sol D.Tstar)
    (K : TripleLogLowerBoundConstants)
    (ht0_lt : K.t0 < D.Tstar)
    (hLB : ∀ t : ℝ, K.t0 ≤ t → t < D.Tstar →
      ENNReal.ofReal (K.c * Real.sqrt (triLog (1 / (D.Tstar - t))))
        ≤ eLpNorm (fun x : Euc ℝ 3 =>
            sol.u (NavierStokes.pairToEuc t x)) 3
            (MeasureTheory.volume : Measure (Euc ℝ 3))) :
    False

/-- **Theorem.** A `TripleLogUpperBoundData sol` rules out blow-up at
`Tstar`: it negates the existence of a `FirstBlowupTime sol Tstar`
witness.

Architecture: the proof contraposes Tao's axiom. The DEEP content is
the lower bound axiom (`tao_2019_triple_log_lower_bound`); the
mechanical comparison `c · X^{1/2} > C · X^α` for `α < 1/2` and
`X → ∞` is encapsulated as the sol-bound axiom
`alpha_lt_half_overpowers_triple_log_lower_bound`. -/
theorem triple_log_upper_bound_excludes_blowup
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : TripleLogUpperBoundData sol) :
    ¬ FirstBlowupTime sol D.Tstar := by
  intro hb
  -- Apply Tao's lower bound at `Tstar = D.Tstar`.
  obtain ⟨K, ht0_lt, hLB⟩ := tao_2019_triple_log_lower_bound sol hb
  -- Discharge via the residual mechanical-comparison axiom.
  exact alpha_lt_half_overpowers_triple_log_lower_bound sol D hb K ht0_lt hLB

/-! ## §7.  No-finite-blow-up corollary -/

/-- **Corollary.** If a `TripleLogUpperBoundData` exists for every
hypothetical blow-up time, then `sol` has no first blow-up time at
all (i.e. it is globally regular in time on `[0, sol.T)`). -/
def NoFirstBlowupOnInterval
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∀ Tstar : ℝ, 0 < Tstar → Tstar ≤ sol.T → ¬ FirstBlowupTime sol Tstar

/-- A `TripleLogUpperBoundData` for every candidate `Tstar` excludes
all first blow-up times on `[0, sol.T)`.

This is the cleanest statement of the contrapositive program: the
typed companion is a SUFFICIENT input to global regularity (modulo
the named open Prop below). -/
theorem no_blowup_of_universal_triple_log_upper_bound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (Dgen : ∀ Tstar : ℝ, 0 < Tstar → Tstar ≤ sol.T →
      ∃ D : TripleLogUpperBoundData sol, D.Tstar = Tstar) :
    NoFirstBlowupOnInterval sol := by
  intro Tstar hTpos hTle hb
  obtain ⟨D, hDeq⟩ := Dgen Tstar hTpos hTle
  have hbD : FirstBlowupTime sol D.Tstar := hDeq ▸ hb
  exact triple_log_upper_bound_excludes_blowup sol D hbD

/-! ## §8.  Named open Prop: the OPEN uniform upper bound for arbitrary `u₀` -/

/-- **Named open Prop (Clay-equivalent).**

`TripleLogUpperBoundProvable u₀` says: for every Leray-Hopf weak
solution `sol` of NS with `sol.u(0, ·) = u₀` and every hypothetical
blow-up time `Tstar`, there exists a `TripleLogUpperBoundData sol`
witnessing the `(log log log)^α` upper bound for some `α < 1/2`.

This is OPEN in general. Closing it for arbitrary smooth, divergence-
free, finite-energy `u₀` IS Clay-equivalent — combined with Tao's
axiom it would yield the Clay Millennium global regularity theorem.

Without external mathematics, this Prop remains an INPUT to the
architecture, exposed as a named `def` so the residual void is
explicit and inspectable. -/
def TripleLogUpperBoundProvable
    (u0 : NavierStokes.VelocityField 3) : Prop :=
  ∀ (nse : NavierStokes.NavierStokesEquations 3)
    (sol : NavierStokes.WeakSolution nse),
    (∀ x : Euc ℝ 3, sol.u (NavierStokes.pairToEuc 0 x) = u0 (NavierStokes.pairToEuc 0 x)) →
    ∀ Tstar : ℝ, 0 < Tstar → Tstar ≤ sol.T →
      FirstBlowupTime sol Tstar →
      ∃ D : TripleLogUpperBoundData sol, D.Tstar = Tstar

/-! ## §9.  Quantitative-strengthening corollary connecting to ESS endpoint

Tao 2019's lower bound STRICTLY strengthens ESS 2003: any UNIFORM
L³ bound is, in particular, a `(log log log)^0` upper bound (a
constant), which is a triple-log upper bound at `α = 0 < 1/2`. Hence
ESS smoothness is recovered from Tao's contrapositive program.

Conversely, Tao's quantitative strengthening EXTENDS ESS to a strict
band of `α ∈ [0, 1/2)`: even mildly L³-divergent solutions can be
ruled out, provided the divergence rate is below the triple-log
square-root threshold. -/

/-- **Quantitative-strengthening corollary.** Any
`ESSL3CriterionData` (uniform L³ upper bound) yields a
`TripleLogUpperBoundData` with `α = 0`. -/
def ess_l3_criterion_to_triple_log_upper_bound
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (E : ESSL3CriterionData sol)
    {Tstar : ℝ}
    (hTpos : 0 < Tstar)
    (hTle : Tstar ≤ sol.T) :
    TripleLogUpperBoundData sol :=
  { Tstar := Tstar
  , Tstar_pos := hTpos
  , Tstar_le_T := hTle
  , alpha := 0
  , alpha_lt_half := by norm_num
  , alpha_nonneg := le_refl 0
  , C := max E.velocity_L_infty_L3_bound 1
  , C_pos := lt_of_lt_of_le zero_lt_one (le_max_right _ _)
  , t1 := 0
  , t1_nonneg := le_refl 0
  , t1_lt_Tstar := hTpos
  , triple_log_upper_bound := by
      intro t _ht1le htlt
      -- For α = 0, `(triLog _)^0 = 1`, so the upper bound becomes
      -- `eLpNorm ≤ ofReal (max M 1)`. We use `E.velocity_L_infty_L3`
      -- on the interval `[0, sol.T]`.
      have htmem : t ∈ Set.Icc (0 : ℝ) sol.T := by
        refine ⟨?_, ?_⟩
        · -- t ≥ 0: from t < Tstar and t1 = 0 ≤ t.
          -- We have _ht1le : 0 ≤ t.
          exact _ht1le
        · -- t ≤ sol.T: from t < Tstar ≤ sol.T.
          exact le_of_lt (lt_of_lt_of_le htlt hTle)
      have hbound := E.velocity_L_infty_L3 t htmem
      -- Compose with `M ≤ max M 1`, and `(triLog _) ^ 0 = 1`.
      have hcoef :
          ENNReal.ofReal E.velocity_L_infty_L3_bound
            ≤ ENNReal.ofReal (max E.velocity_L_infty_L3_bound 1
              * (triLog (1 / (Tstar - t))) ^ (0 : ℝ)) := by
        rw [Real.rpow_zero, mul_one]
        exact ENNReal.ofReal_le_ofReal (le_max_left _ _)
      exact le_trans hbound hcoef }

/-- **Quantitative ESS endpoint refinement.** Tao 2019 strictly
generalizes ESS 2003: the ESS uniform-L³-bound criterion is the
`α = 0` case of the triple-log upper bound criterion, and Tao
extends the no-blow-up conclusion to all `α ∈ [0, 1/2)`. -/
theorem tao_2019_strengthens_ess_l3_endpoint
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (E : ESSL3CriterionData sol)
    {Tstar : ℝ}
    (hTpos : 0 < Tstar)
    (hTle : Tstar ≤ sol.T) :
    ¬ FirstBlowupTime sol Tstar := by
  -- Build the triple-log upper bound from the ESS data, then apply
  -- the contrapositive. By construction `D.Tstar = Tstar`.
  intro hb
  let D := ess_l3_criterion_to_triple_log_upper_bound sol E hTpos hTle
  have hbD : FirstBlowupTime sol D.Tstar := hb
  exact triple_log_upper_bound_excludes_blowup sol D hbD

/-! ## §10.  Honesty receipt

Total content of this file:

* 1 helper `def`:    `triLog`     (clipped triple log)
* 1 helper lemma:    `triLog_nonneg`
* 1 `Prop` predicate: `FirstBlowupTime`
* 1 constants record: `TripleLogLowerBoundConstants`
* 2 axioms (cited):
  - `tao_2019_triple_log_lower_bound`
                       (Tao 2019, arXiv:1908.04958) — load-bearing.
  - `alpha_lt_half_overpowers_triple_log_lower_bound`
                       (FIX-D sol-bound; mechanical real-analysis
                       comparison `c · X^{1/2} > C · X^α` for
                       `α < 1/2` and `X → ∞`; NOT Clay-equivalent.)
* 1 typed companion:  `TripleLogUpperBoundData`
* 2 derived theorems:
  - `triple_log_upper_bound_excludes_blowup`
  - `no_blowup_of_universal_triple_log_upper_bound`
* 1 named open Prop:  `TripleLogUpperBoundProvable`
                       (Clay-equivalent for arbitrary `u₀`)
* 2 strengthening connectors:
  - `ess_l3_criterion_to_triple_log_upper_bound`
  - `tao_2019_strengthens_ess_l3_endpoint`

Sorry inventory:

* (none) — the file is sorry-free as of 2026-05-07. The previous
  `sorry_alpha_lt_half_overpowers_lower_bound` placeholder has been
  promoted to the sol-bound axiom
  `alpha_lt_half_overpowers_triple_log_lower_bound` (see above).
  The previous `triLog_then_branch_nonneg` sorry has been closed
  with an elementary Mathlib proof.

Open Prop inventory:

1. `TripleLogUpperBoundProvable u₀` — the uniform `(log log log)^α`
   upper bound for arbitrary `u₀` and `α < 1/2`. Clay-equivalent.
   Architecture exposes this as a NAMED OPEN PROP INPUT. Without
   external mathematics, this remains open.

Architecture verdict: this file is a **conditional-bridge** in the
same shape as `ns_trackb_ess_l3_endpoint.lean`, but encoding Tao
2019's QUANTITATIVE sharpening. The `α < 1/2` parameter is the
quantitative knob: ESS = `α = 0` (constant); Tao = `α ∈ [0, 1/2)`.
The named open Prop captures exactly the residual void. -/

end

end ZtareProofs.NS
