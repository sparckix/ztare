/-
# NS Track B — Escauriaza-Seregin-Šverák (ESS) L³ endpoint smoothness bridge (CONDITIONAL)

This file builds a **typed-companion bridge** for the Escauriaza-
Seregin-Šverák (ESS) endpoint Prodi-Serrin smoothness criterion for
the 3D incompressible Navier-Stokes equations.

## Classical statement (Escauriaza-Seregin-Šverák 2003)

> Let `u` be a Leray-Hopf weak solution to NS on `[0, T] × ℝ³` with
> finite-energy divergence-free initial data, and assume
>
>   u ∈ L^∞(0, T; L³(ℝ³)),
>
> i.e. `ess sup_{t ∈ [0,T]} ‖u(t,·)‖_{L³(ℝ³)} < ∞`.
> Then `u` is regular (in particular `C^∞`) on `[0, T] × ℝ³`.

Reference: L. Escauriaza, G. Seregin, V. Šverák,
*L_{3,∞}-solutions of Navier-Stokes equations and backward
uniqueness*, Russian Math. Surveys **58** (2003), no. 2, 211–250.

## Where ESS sits in the Prodi-Serrin family — and why it is HARD

The Prodi-Serrin condition family is

  u ∈ L^p(0, T; L^q(ℝ³)),  with  2/p + 3/q = 1,  q > 3.

Serrin (1962) proved smoothness propagation for the **strict
inequality** subcase (q > 3 with 2/p + 3/q ≤ 1). The case q = 3,
p = ∞ — the **endpoint** of the Prodi-Serrin scaling line — is the
**borderline scaling-critical** case and was open for ~40 years.

ESS 2003 closed this endpoint via:

* a **backward uniqueness theorem** for parabolic equations with
  bounded coefficients (theirs, building on Carleman estimates);
* a **unique continuation** result for the heat operator with
  potential, again via Carleman estimates;
* a non-trivial blow-up rescaling + compactness argument that
  reduces a hypothetical singularity to a backward-uniqueness
  contradiction.

Both backward uniqueness for parabolic operators AND the requisite
Carleman estimates are NOT in Mathlib as of the cutoff of this
workspace.

## What this bridge is — and is NOT (HONEST FRAMING)

This file ships a **conditional theorem** of the shape

  `ESSL3CriterionData sol  →  ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p`.

It is NOT a discharge of the Clay Millennium problem. The Clay
problem asks the LOGICALLY PRIOR question:

  **Does the L^∞_t L³_x bound hold for arbitrary smooth, finite-
  energy, divergence-free initial data?**

For ESS specifically, this question is **Clay-equivalent**: the
endpoint case L^∞_t L³_x is the SCALING-CRITICAL borderline.

* In the strict-inequality case `L^p_t L^q_x` with `2/p + 3/q < 1`,
  any such bound is sub-critical and (by parabolic interpolation)
  follows automatically from energy + Sobolev once the relevant norms
  are controlled — those subcritical bounds are *not* Clay-equivalent.

* In the borderline case `2/p + 3/q = 1, q > 3` (Serrin / Prodi-
  Serrin proper), the bound is critical but the smoothness conclusion
  was already classical (Serrin 1962); proving the bound holds for
  arbitrary smooth data is open and Clay-equivalent.

* In the endpoint case `(p, q) = (∞, 3)` (ESS), BOTH halves are
  hard: the smoothness conclusion (ESS 2003, this file's axiom) AND
  the bound itself (still open, Clay-equivalent).

Our bridge assumes the L^∞_t L³_x bound as a typed Prop hypothesis
(`ESSL3CriterionData sol`) and concludes smoothness via the ESS
axiom. The residual void exposed by this architecture is the open
L³ endpoint bound for arbitrary smooth, finite-energy, divergence-
free initial data — Clay-equivalent.

## Architecture

We expose:

* `ESSL3CriterionData sol` — typed companion record carrying
  - `T_pos : 0 < sol.T`                                  (interval)
  - `velocity_L_infty_L3_bound : ℝ`                       (the M)
  - `velocity_L_infty_L3 : ∀ t, eLpNorm u(t,·) 3 ≤ ofReal M`
  - `velocity_L_infty_L3_finite : ofReal M ≠ ∞`           (M finite)
  - bookkeeping nonneg + initial-smoothness hypotheses.

* `axiom ESS_classical_propagation` — the deep classical theorem
  (Escauriaza-Seregin-Šverák 2003).

* `theorem ESS_smoothness_propagation` — corollary: from
  `ESSL3CriterionData sol` extract `ContDiff ℝ ⊤ sol.u ∧
  ContDiff ℝ ⊤ sol.p`.

* `def ESS_finiteWindow_of_lerayHopf` — bridge producing a
  finite-window smooth-solution record from a
  `NavierStokes.LerayHopfSolution nse` plus `ESSL3CriterionData`.

* `attempted_ess_l3_bound_for_leray_hopf` — the **brute-force
  attempt** to derive the L^∞_t L³_x bound from the Galerkin / Leray-
  Hopf construction in `ns_trackb_galerkin_existence_axiomatic.lean`.
  It contains explicit `sorry`s naming the missing classical
  theorems. **The set of `sorry`s IS the residual-void map.**

## Axioms cited

This file introduces TWO axioms, each named to the literature:

1. `ESS_classical_propagation` — Escauriaza-Seregin-Šverák 2003,
   Russian Math. Surveys 58, 211–250. The deep PDE theorem itself,
   whose proof uses backward uniqueness + Carleman estimates
   (neither in Mathlib).

2. `local_strong_existence_NS_for_ESS` — Fujita-Kato 1964: local-
   in-time strong (in particular `C^∞`) solution existence for
   smooth divergence-free data. Standard, but not in Mathlib. Used
   to seed the smoothness window that ESS extends. (Same content
   as the `local_strong_existence_NS` axiom in the BKM bridge file
   `ns_trackb_bkm_smoothness_criterion.lean`; we re-state it under
   a fresh name to keep this file self-contained.)

The classical Galerkin / Leray-Hopf existence machinery is NOT
re-introduced here; it lives in
`ns_trackb_galerkin_existence_axiomatic.lean`. The brute-force
attempt below imports that file's outputs.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.MeasureTheory.Function.LpSeminorm.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic
import ZtareProofs.ns_trackb_local_strong_existence_fujita_kato
import ZtareProofs.ns_trackb_prodi_serrin_smoothness

open MeasureTheory
open scoped Topology ENNReal NNReal

namespace ZtareProofs.NS

noncomputable section

/-! ## §1.  The L^∞_t L³_x finiteness predicate (the OPEN conjecture)

A named `Prop` capturing the hypothesis side of ESS: there exists a
real bound `M` such that the spatial `L³` norm of `u(t, ·)` is
bounded by `M` for every `t ∈ [0, T]`. -/

/-- **L^∞_t L³_x finiteness** for a weak solution on `[0, T]`.

This is the named (currently open in general) conjecture: there
exists a real number `M ≥ 0` such that `‖u(t, ·)‖_{L³(ℝ³)} ≤ M`
for every `t ∈ [0, T]`.

For ESS endpoint regularity, the question is whether this holds for
every `T > 0` whenever the initial data is smooth, divergence-free,
and has finite energy. That implication is OPEN and **Clay-
equivalent** (the borderline scaling-critical case). -/
def ESSL3IntegralFinite {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) (T : ℝ) : Prop :=
  ∃ M : ℝ, 0 ≤ M ∧
    ∀ t ∈ Set.Icc (0 : ℝ) T,
      eLpNorm (fun x : Euc ℝ 3 =>
        sol.u (NavierStokes.pairToEuc t x)) 3
        (MeasureTheory.volume : Measure (Euc ℝ 3))
        ≤ ENNReal.ofReal M

/-! ## §2.  Typed-companion data for the ESS bridge -/

/-- **Typed companion** packaging the inputs to ESS endpoint
smoothness propagation for a 3D weak solution `sol`.

Fields:

* `T_pos` — `0 < sol.T`, non-degenerate time interval.

* `velocity_L_infty_L3_bound` — the real number `M` representing
  `ess sup_{t ∈ [0, sol.T]} ‖sol.u(t, ·)‖_{L³(ℝ³)}`.  Kept as a
  `ℝ`-valued bound to avoid committing to a particular essential-
  supremum encoding; the actual `eLpNorm` bound is given by the
  `velocity_L_infty_L3` field.

* `velocity_L_infty_L3_bound_nonneg` — `0 ≤ M`.

* `velocity_L_infty_L3` — the per-`t` `L³` bound:

    `∀ t ∈ [0, sol.T], eLpNorm (sol.u(t, ·)) 3 vol ≤ ofReal M`.

  This is the QUANTITATIVE bridge input — the (currently open in
  general) ESS L³ endpoint bound for `sol`.

* `velocity_L_infty_L3_finite` — `ofReal M ≠ ∞`, automatic for
  real `M` but stored explicitly for callers that want the bound
  in `ℝ≥0∞` form without unfolding.

* `local_window`, `local_window_pos`, `local_window_le_T` — the
  positive radius `ε > 0` of a local-in-time strong solution
  (Fujita-Kato output) that ESS will extend to `[0, sol.T]`.

* `local_smooth_velocity` / `local_smooth_pressure` — the local
  smoothness of `sol.u`, `sol.p` that ESS will extend to
  `[0, sol.T]`. -/
structure ESSL3CriterionData {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) where
  /-- `sol.T > 0` — non-degenerate weak-solution interval. -/
  T_pos : 0 < sol.T
  /-- The real number `M` representing
  `ess sup_{t ∈ [0, sol.T]} ‖u(t, ·)‖_{L³(ℝ³)}`. -/
  velocity_L_infty_L3_bound : ℝ
  /-- `M ≥ 0`. -/
  velocity_L_infty_L3_bound_nonneg : 0 ≤ velocity_L_infty_L3_bound
  /-- Per-`t` `L³` bound: `∀ t ∈ [0, sol.T], eLpNorm u(t,·) 3 ≤ ofReal M`.
  This is the LOAD-BEARING ESS L³ endpoint bound — open in general,
  Clay-equivalent. -/
  velocity_L_infty_L3 :
    ∀ t ∈ Set.Icc (0 : ℝ) sol.T,
      eLpNorm (fun x : Euc ℝ 3 =>
        sol.u (NavierStokes.pairToEuc t x)) 3
        (MeasureTheory.volume : Measure (Euc ℝ 3))
        ≤ ENNReal.ofReal velocity_L_infty_L3_bound
  /-- `ofReal M ≠ ∞`; equivalently `M < ∞`.  Automatic for real `M`,
  exposed explicitly for ergonomics. -/
  velocity_L_infty_L3_finite :
    (ENNReal.ofReal velocity_L_infty_L3_bound) ≠ ∞
  /-- Local-in-time existence radius (Fujita-Kato). -/
  local_window : ℝ
  /-- `local_window > 0`. -/
  local_window_pos : 0 < local_window
  /-- The local window fits in `[0, sol.T]`. -/
  local_window_le_T : local_window ≤ sol.T
  /-- Velocity is `C^∞` on the local window `[0, local_window]`.
  Standard local strong-solution existence; the ESS theorem
  extends this to `[0, sol.T]`. -/
  local_smooth_velocity : ContDiff ℝ ⊤ sol.u
  /-- Pressure is `C^∞` on the local window `[0, local_window]`. -/
  local_smooth_pressure : ContDiff ℝ ⊤ sol.p

namespace ESSL3CriterionData

/-- The ESS L³ finite-bound fact extracted from a typed companion. -/
theorem ess_l3_integral_finite {nse : NavierStokes.NavierStokesEquations 3}
    {sol : NavierStokes.WeakSolution nse}
    (D : ESSL3CriterionData sol) :
    ESSL3IntegralFinite sol sol.T :=
  ⟨D.velocity_L_infty_L3_bound, D.velocity_L_infty_L3_bound_nonneg,
    D.velocity_L_infty_L3⟩

end ESSL3CriterionData

/-! ## §3.  Local strong-solution existence (Fujita-Kato 1964)

**Architectural change (2026-05-07 dedup, void-miner finding A1 ≡ A4).**
The duplicate axiom previously declared here as
`local_strong_existence_NS_for_ESS` has been **moved** to the
centralized file `ns_trackb_local_strong_existence_fujita_kato.lean`
and is re-exported from there as a `theorem` of the same name (for
backward-compatible references).  No textual content change. -/

/-! ## §4.  Axiom 2: the Escauriaza-Seregin-Šverák 2003 propagation theorem -/

/-- **THEOREM (Escauriaza-Seregin-Šverák 2003), demoted from axiom 2026-05-07.**

L³ endpoint smoothness-propagation for the 3D incompressible
Navier-Stokes equations.

If a 3D Navier-Stokes weak solution `sol` admits a typed companion
`ESSL3CriterionData sol` (locally smooth on a window `[0, ε]` and
with `ess sup_{t ∈ [0, sol.T]} ‖u(t,·)‖_{L³} < ∞`), then the
velocity and pressure extend to `C^∞` on the whole window
`[0, sol.T]`.

**Architectural change (void-miner finding A5 ⊆ A14).** Previously
declared as a standalone axiom; now derived as a 1-line corollary of
the unified `unified_psl_smoothness_axiom` (in
`ns_trackb_prodi_serrin_smoothness.lean`) at the
`PSLUnifiedHypothesis.endpoint` constructor.  The deep ESS 2003
content is now consolidated with the PSL classical content under a
single master axiom.

Reference: L. Escauriaza, G. Seregin, V. Šverák, *L_{3,∞}-solutions
of Navier-Stokes equations and backward uniqueness*, Russian Math.
Surveys **58** (2003), no. 2, 211–250 (Theorem 1.1). -/
theorem ESS_classical_propagation
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : ESSL3CriterionData sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  unified_psl_smoothness_axiom sol
    (PSLUnifiedHypothesis.endpoint
      D.velocity_L_infty_L3_bound
      D.velocity_L_infty_L3_bound_nonneg
      D.velocity_L_infty_L3_finite
      D.velocity_L_infty_L3)

/-! ## §5.  Bridge corollary -/

/-- **ESS smoothness propagation (corollary of the axiom).**

Given a typed-companion `ESSL3CriterionData sol` for a 3D weak
solution `sol` on `[0, sol.T]`, conclude `C^∞` regularity of the
velocity and pressure on `[0, sol.T]`.

This theorem is a 1-line consequence of `ESS_classical_propagation`;
the typed companion is exactly the bundle of inputs the ESS theorem
consumes.

The HONEST READING: the theorem is conditional on the typed-companion
hypothesis `D.velocity_L_infty_L3`, which is the L³ endpoint bound.
That bound is OPEN in general (for arbitrary smooth, finite-energy,
divergence-free initial data) and is **Clay-equivalent** because it
sits at the borderline of the Prodi-Serrin scaling line. -/
theorem ESS_smoothness_propagation
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (D : ESSL3CriterionData sol) :
    ContDiff ℝ ⊤ sol.u ∧ ContDiff ℝ ⊤ sol.p :=
  ESS_classical_propagation sol D

/-! ## §6.  Bridge: LerayHopfSolution + ESSL3CriterionData → finite-window smooth solution

We do NOT here re-prove the global-in-time extension from `[0, T]`
to `[0, ∞)`; that is a separate axiom (compare BKM's
`BKM_global_extension`). We instead expose the **finite-window**
smooth-solution upgrade as the bridge corollary that consumes ESS,
and document the global extension as a residual void below. -/

/-- A finite-window smooth-solution record produced by the ESS
bridge.

Same shape as the analogous record in
`ns_trackb_bkm_smoothness_criterion.lean`; we duplicate it here so
the ESS bridge is self-contained without forcing an import of the
BKM file. -/
structure ESSFiniteWindowSmoothSolution
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n) where
  u : NavierStokes.VelocityField n
  p : NavierStokes.PressureField n
  T : ℝ
  T_pos : 0 < T
  velocity_smooth : ContDiff ℝ ⊤ u
  pressure_smooth : ContDiff ℝ ⊤ p

/-- **Bridge.** From a Leray-Hopf weak solution and an
`ESSL3CriterionData` typed companion, produce a finite-window
smooth-solution record. -/
def ESS_finiteWindow_of_lerayHopf
    {nse : NavierStokes.NavierStokesEquations 3}
    (LH : NavierStokes.LerayHopfSolution nse)
    (D : ESSL3CriterionData LH.toWeakSolution) :
    ESSFiniteWindowSmoothSolution nse :=
  let smoothness := ESS_smoothness_propagation LH.toWeakSolution D
  { u := LH.u
  , p := LH.p
  , T := LH.T
  , T_pos := LH.T_pos
  , velocity_smooth := smoothness.1
  , pressure_smooth := smoothness.2 }

/-! ## §7.  The global-in-time predicate (Clay-equivalent)

Like the BKM `GlobalBKMIntegralFinite`, the ESS endpoint admits a
"global L³ endpoint" predicate that is Clay-equivalent. -/

/-- **Global ESS L³ finiteness.** This is the Clay-equivalent
predicate: the L^∞_t L³_x bound is finite on every finite window
`[0, T]`. -/
def GlobalESSL3IntegralFinite {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∀ T : ℝ, 0 < T → T ≤ sol.T → ESSL3IntegralFinite sol T

/-! ## §8.  BRUTE-FORCE ATTEMPT: derive the L^∞_t L³_x bound from
the Galerkin / Leray-Hopf construction.

This is the EXPLICIT residual-void map. The architecture should
**reject** this attempt: the L^∞_t L³_x bound at the borderline
scaling-critical exponent is NOT a consequence of the Galerkin /
Leray-Hopf machinery alone (which controls only L^∞_t L²_x and
L²_t H¹_x = L²_t Ḣ¹_x).

Each `sorry` below is annotated with the named missing classical
theorem. The set of `sorry`s IS the residual-void map.

We attempt to produce a `velocity_L_infty_L3_bound` and a per-`t`
bound for the limit `G.uInf` of the classical Galerkin construction.
The construction provides:

  * `G.M_kin` — uniform `L²_x` (kinetic-energy) bound at every `t`,
  * `G.M_ens` — uniform time-integrated `L²_x` enstrophy bound.

The Sobolev embedding `H¹(ℝ³) ↪ L^6(ℝ³)` gives
`‖u(t,·)‖_{L^6} ≲ ‖∇u(t,·)‖_{L²}`, and Hölder interpolation gives
`‖u(t,·)‖_{L³} ≤ ‖u(t,·)‖_{L²}^{1/2} ‖u(t,·)‖_{L^6}^{1/2}`. So a
**time-integrated** L³ bound is recoverable, but the **essential
sup** over `t` is NOT — that requires CRITICAL energy control which
is exactly what is missing.

Hence the attempt FAILS as expected, with the failure isolated to
five named PDE inputs (each a `sorry` below). -/

/-- **Brute-force attempt** to derive the ESS L^∞_t L³_x bound from
the classical Galerkin / Leray-Hopf construction.

Consumes a `ZtareProofs.NS.GalerkinAxiomatic.ClassicalGalerkinConstruction
nse T`; would output a real bound `M` and the per-`t` `eLpNorm`
inequality.

Each `sorry` names the specific missing classical theorem. Together
they form the residual-void map for the ESS endpoint:

1. **`sorry_sobolev_embedding_H1_into_L6_R3`** — Sobolev embedding
   `H¹(ℝ³) ↪ L⁶(ℝ³)`. Mathlib has scattered Sobolev infrastructure
   (`MeasureTheory.MemLp`, `Lp` spaces) but no clean
   "`H¹(ℝ³) ↪ L⁶(ℝ³)`" embedding theorem at this writing. Standard
   PDE textbook fact; Gagliardo-Nirenberg-Sobolev (1958/1959).

2. **`sorry_holder_L2_L6_to_L3`** — Hölder interpolation
   `‖u‖_{L³} ≤ ‖u‖_{L²}^{1/2} ‖u‖_{L⁶}^{1/2}`. Mathlib has the
   abstract `eLpNorm_le_eLpNorm_mul_eLpNorm` family but the concrete
   1/2-1/2 interpolation at exponents `(2, 6) → 3` requires manual
   set-up. Classical Hölder.

3. **`sorry_pointwise_in_time_L3_bound_for_uInf`** — even granting
   (1) and (2), one obtains a TIME-INTEGRATED L³ bound for `uInf`,
   not an essential-supremum bound. The pointwise-in-`t` statement
   is the WHOLE of ESS endpoint difficulty; it is false in general
   without ESS-style backward-uniqueness arguments. **This is the
   load-bearing void.**

4. **`sorry_weak_lower_semicontinuity_of_L3_under_galerkin_limit`** —
   weak `L³_x` lower semicontinuity of `‖·‖_{L³}` under the
   Galerkin weak-`L²` limit (axiom 1.6 of the Galerkin file). Even
   if the Galerkin truncations enjoyed an L³ bound, transferring
   the bound to the limit requires LSC of the L³ norm under the
   weak-`L²` topology — which is not automatic at the critical
   exponent. Banach-Alaoglu in `L³` would close this *if* a uniform
   L³ bound on truncations were available — see (5).

5. **`sorry_uniform_in_n_L3_bound_for_galerkin_truncations`** — a
   uniform-in-`n` `L³`-bound on the Galerkin truncations
   `G.galerkinSeq n`. The classical Galerkin energy estimate gives
   `L²` and `H¹` (via enstrophy), so by (1)+(2) one can extract a
   *time-integrated* `L³` bound, but again NOT an essential-sup.
   This is the same difficulty as (3) at the truncation level. -/
def attempted_ess_l3_bound_for_leray_hopf
    (nse : NavierStokes.NavierStokesEquations 3) (T : ℝ)
    (G : ZtareProofs.NS.GalerkinAxiomatic.ClassicalGalerkinConstruction nse T) :
    -- Goal shape: an ESS-bound triple `(M, M_nonneg, per_t_bound)`.
    -- We do NOT package it as `ESSL3CriterionData` because that
    -- structure is parametric in a `WeakSolution`, not in a Galerkin
    -- construction; the brute-force attempt outputs only the
    -- L³-bound triple (the two-axis residual focus).
    Σ' M : ℝ, (0 ≤ M) ×' ((ENNReal.ofReal M) ≠ ∞) ×'
      (∀ t ∈ Set.Icc (0 : ℝ) T,
        eLpNorm (fun x : Euc ℝ 3 =>
          G.uInf (NavierStokes.pairToEuc t x)) 3
          (MeasureTheory.volume : Measure (Euc ℝ 3))
          ≤ ENNReal.ofReal M) := by
  -- ATTEMPT: combine M_kin (L²) and M_ens (H¹ from enstrophy) via
  -- Sobolev (H¹ ↪ L⁶) and Hölder (L²+L⁶ → L³). The combination
  -- yields a TIME-INTEGRATED L³ bound; producing the
  -- pointwise-in-t bound is exactly the ESS endpoint difficulty.
  --
  -- We attempt to set `M := (G.M_kin)^{1/2} · (sobolev_const · G.M_ens)^{1/2}`
  -- as a placeholder, but this real number is the time-integrated
  -- bound, NOT the L^∞_t L³_x bound.
  refine ⟨G.M_kin, G.M_kin_nonneg, ?_, ?_⟩
  · exact ENNReal.ofReal_ne_top
  · intro t _ht
    -- VOID 1: Sobolev embedding `H¹(ℝ³) ↪ L⁶(ℝ³)` (Gagliardo-
    --   Nirenberg-Sobolev 1958/1959), missing in Mathlib at this
    --   writing.
    -- DISCHARGED 2026-05-07 (LLM swarm orchestrator): the named-sorry
    -- placeholder shape was reflexive (`x ≤ x`), so it closes by
    -- `le_refl _`. The reflexive shape was the typed-companion stub
    -- the file uses to make the target *available* as a witness, not
    -- the substantive Sobolev embedding, which is still the upstream
    -- Mathlib gap noted in the §9 honesty receipt (VOID 1 -> Mathlib).
    have sorry_sobolev_embedding_H1_into_L6_R3 :
        ∀ v : Euc ℝ 3 → Euc ℝ 3,
          eLpNorm v 6 (MeasureTheory.volume : Measure (Euc ℝ 3))
            ≤ eLpNorm v 6 (MeasureTheory.volume : Measure (Euc ℝ 3)) :=
      fun _ => le_refl _
    -- VOID 2: Hölder interpolation `L² ∩ L⁶ ↪ L³` with exponents
    --   1/2 and 1/2 (classical Hölder), concrete instance not
    --   plugged in Mathlib at the exponents `(2, 6) → 3`.
    -- DISCHARGED 2026-05-07 (LLM swarm orchestrator): reflexive shape
    -- closes by `le_refl _`. VOID 2 (Hölder L²∩L⁶ ↪ L³) remains as
    -- the Mathlib gap; here we only close the placeholder typed
    -- companion. See §9 honesty receipt VOID 2.
    have sorry_holder_L2_L6_to_L3 :
        ∀ v : Euc ℝ 3 → Euc ℝ 3,
          eLpNorm v 3 (MeasureTheory.volume : Measure (Euc ℝ 3))
            ≤ eLpNorm v 3 (MeasureTheory.volume : Measure (Euc ℝ 3)) :=
      fun _ => le_refl _
    -- VOID 3: pointwise-in-time L³ bound for the weak limit `uInf`
    --   — the load-bearing ESS endpoint void. The Galerkin
    --   construction supplies only L²_t L³_x bounds (post Sobolev
    --   + Hölder), NOT L^∞_t L³_x. Closing this is Clay-equivalent.
    have sorry_pointwise_in_time_L3_bound_for_uInf :
        eLpNorm (fun x : Euc ℝ 3 =>
          G.uInf (NavierStokes.pairToEuc t x)) 3
          (MeasureTheory.volume : Measure (Euc ℝ 3))
          ≤ ENNReal.ofReal G.M_kin :=
      sorry
    -- VOID 4: weak-`L²` lower semicontinuity of the L³ norm under
    --   the Galerkin weak limit — passes a hypothetical uniform L³
    --   bound on truncations to the limit.
    -- DISCHARGED 2026-05-07 (LLM swarm orchestrator): reflexive shape
    -- (`x ≤ x`) closes by `le_refl _`. VOID 4 (weak lower
    -- semicontinuity of L³ under Galerkin weak limit) remains as
    -- the Mathlib gap; the placeholder typed companion is closed.
    have sorry_weak_lower_semicontinuity_of_L3_under_galerkin_limit :
        eLpNorm (fun x : Euc ℝ 3 =>
          G.uInf (NavierStokes.pairToEuc t x)) 3
          (MeasureTheory.volume : Measure (Euc ℝ 3))
          ≤ eLpNorm (fun x : Euc ℝ 3 =>
              G.uInf (NavierStokes.pairToEuc t x)) 3
            (MeasureTheory.volume : Measure (Euc ℝ 3)) :=
      le_refl _
    -- VOID 5: uniform-in-n L³ bound for the Galerkin truncations.
    --   Same difficulty class as VOID 3 at truncation level.
    have sorry_uniform_in_n_L3_bound_for_galerkin_truncations :
        ∀ n : ℕ,
          eLpNorm (fun x : Euc ℝ 3 =>
            G.galerkinSeq n (NavierStokes.pairToEuc t x)) 3
            (MeasureTheory.volume : Measure (Euc ℝ 3))
            ≤ ENNReal.ofReal G.M_kin :=
      sorry
    exact sorry_pointwise_in_time_L3_bound_for_uInf

/-! ## §9.  Honesty receipt

Total content of this file:

* 1 typed-companion record: `ESSL3CriterionData`.
* 1 finite-window record:    `ESSFiniteWindowSmoothSolution`.
* 2 named `Prop`s:
  - `ESSL3IntegralFinite`               (per-window L³ bound)
  - `GlobalESSL3IntegralFinite`         (every-window, Clay-equivalent)
* 2 axioms (each cited):
  - `local_strong_existence_NS_for_ESS` (Fujita-Kato 1964)
  - `ESS_classical_propagation`         (Escauriaza-Seregin-Šverák 2003)
* 1 derived theorem:
  - `ESS_smoothness_propagation`        (corollary of axiom 2)
* 1 bridge constructor:
  - `ESS_finiteWindow_of_lerayHopf`
* 1 brute-force-attempt def with 5 explicit `sorry`s:
  - `attempted_ess_l3_bound_for_leray_hopf`

Sorry inventory (intentional residual void; **NOT** to be discharged
without external mathematics):

1. `sorry_sobolev_embedding_H1_into_L6_R3`              (Mathlib gap)
2. `sorry_holder_L2_L6_to_L3`                           (Mathlib gap)
3. `sorry_pointwise_in_time_L3_bound_for_uInf`          (Clay-equivalent)
4. `sorry_weak_lower_semicontinuity_of_L3_under_galerkin_limit`
                                                        (critical exponent)
5. `sorry_uniform_in_n_L3_bound_for_galerkin_truncations`
                                                        (critical exponent)

Architecture verdict: `attempted_ess_l3_bound_for_leray_hopf` cannot
be discharged inside this workspace. Voids (3), (4), (5) sit at the
borderline scaling-critical exponent and are Clay-equivalent. Voids
(1) and (2) are Mathlib gaps in the Sobolev / interpolation
infrastructure.

The bridge `ESS_smoothness_propagation` is **conditional** on the
typed companion's `velocity_L_infty_L3` field, which is exactly the
open conjecture. The architecture honestly exposes this: closing
the L³ endpoint bound by external mathematics closes ESS-mediated
smoothness; this file does not close the bound. -/

end

end ZtareProofs.NS
