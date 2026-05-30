/-
# NS Track B — Buckmaster-Vicol / Albritton-Brue-Colombo boundary

This file formalizes the **regularity-class boundary** between the
architecture's 6 sorry-free `GlobalSmoothSolution` (GSS) classes and the
wild non-unique solutions constructed by:

* Buckmaster-Vicol, *Annals* 189 (2019), 101-144 -- 3D NS weak solutions
  in `C^0_t H^β_x` for some `β > 0`, with finite energy but unbounded
  classical vorticity, sitting strictly below the Lions-Prodi-Serrin
  threshold.
* Albritton-Brue-Colombo, *Annals* 196 (2022), 415-455 -- two distinct
  Leray-Hopf solutions with zero initial data and a common smooth body
  force, built from a Vishik-style unstable axisymmetric vortex ring;
  also strictly below `L^∞_t H^{1/2}` / ESS.

## What this file is

A typed predicate `BVABCWildSolution sol` expressing the three regularity
properties any BV/ABC-class wild solution **lacks**, plus an axiom that
formalizes the contrapositive: any such solution **fails** the
sol-binding BKM hypothesis bundle of `BKM_global_extension`.

This is a SEMANTIC boundary statement. It is not constructive; we do not
import the convex-integration construction into Lean. The axiom
freezes the disjointness so future GSS-class extensions must explicitly
audit their hypothesis bundle against `BVABCWildSolution`.

## Why this is not weakening the architecture

The axiom only says: "wild solutions cannot satisfy the sol-binding
opaque predicate". Since `BKMGlobalEnvelopeBoundsSolution` is already
opaque (architectural anti-trivialization guard -- see
`bkm_discharge_attempt_2026_05_07.md`), this axiom rules out one sub-class
of inhabitants, namely BV/ABC wild solutions. Concretely: it prevents
anyone from later asserting `BKMGlobalEnvelopeBoundsSolution nse` on a
BV/ABC-class data set and then claiming a GSS via `BKM_global_extension`.

## Companion criteria

Symmetric axioms `BV_wild_excludes_{ESS,LeiZhang,CF}_premise` follow the
same pattern; only `BV_wild_excludes_BKM_premise` is shipped here as a
canonical anchor.
-/

import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bkm_smoothness_criterion

open MeasureTheory

namespace ZtareProofs.NS

noncomputable section

/-! ## Regularity-deficit predicates carried by BV/ABC wild solutions -/

/-- Abstract marker that `sol.u` lies in the ESS / Lions-Prodi-Serrin
endpoint class `L^∞_t L^3_x`. Kept opaque: defining this concretely
requires Bochner-`L^p` formalization Mathlib does not yet ship.

In the typed-companion idiom, this is a sol-binding `Prop` whose
inhabitants are exactly the witnesses that `sol.u ∈ L^∞_t L^3`. -/
opaque InLinftyTL3 {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Abstract marker that `sol.u` lies in `L^∞_t H^{1/2}_x` (the
energy-class ceiling above which uniqueness is known). -/
opaque InLinftyTHHalf {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Abstract marker that `sol`'s classical vorticity is `L^∞` in space
for almost every time -- equivalently, that there is a measurable
function `Ω : ℝ → ℝ` pointwise binding `‖∇×u(t,·)‖_{L^∞}`. -/
opaque ClassicalLinfVorticity {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-! ## The wild-solution typed predicate -/

/-- **`BVABCWildSolution sol`** -- the structural signature of a 3D
Buckmaster-Vicol / Albritton-Brue-Colombo wild solution:

* `belowESS`  : `sol.u ∉ L^∞_t L^3` (below the ESS / LPS endpoint).
* `belowH12`  : `sol.u ∉ L^∞_t H^{1/2}` (below the energy-class
  uniqueness ceiling).
* `vortUnbd`  : classical `L^∞_x` vorticity does not exist (the BKM
  integral has no finite measurable representative).

Any solution produced by the BV 2019 or ABC 2022 convex-integration
constructions inhabits this typed predicate. -/
structure BVABCWildSolution {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop where
  belowESS : ¬ InLinftyTL3 sol
  belowH12 : ¬ InLinftyTHHalf sol
  vortUnbd : ¬ ClassicalLinfVorticity sol

/-! ## The boundary axiom -/

/-- **Boundary axiom (BV/ABC vs BKM premise).**

If `sol` is a BV/ABC-class wild solution, it is impossible to
simultaneously hold the opaque sol-binding predicate
`BKMGlobalEnvelopeBoundsSolution nse` and the BKM integral finiteness
hypothesis on every `T > 0`.

This formalizes the regularity-class disjointness: the architecture's
BKM-driven GSS extension cannot be applied on the BV/ABC wild stratum.
The axiom is semantic; it follows from the regularity claims of BV 2019
Theorem 1.1 and ABC 2022 Theorem 1, which place the constructed
solutions strictly below any class admitting an `L^∞_x` classical
vorticity. -/
axiom BV_wild_excludes_BKM_premise
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (_h : BVABCWildSolution sol) :
    ¬ (BKMGlobalEnvelopeBoundsSolution nse ∧
       ∀ T : ℝ, 0 < T → BKMIntegralFinite sol T)

/-- **Companion lemma (BV/ABC vs ESS endpoint).**

A BV/ABC wild solution does not lie in the ESS class `L^∞_t L^3`.
This is a direct projection of the typed predicate, not an axiom. -/
theorem BV_wild_excludes_ESS_premise
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (h : BVABCWildSolution sol) :
    ¬ InLinftyTL3 sol :=
  h.belowESS

/-- **Companion lemma (BV/ABC vs H^{1/2} ceiling).**

A BV/ABC wild solution does not lie in the energy-class uniqueness
ceiling `L^∞_t H^{1/2}`. -/
theorem BV_wild_excludes_Hhalf_premise
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (h : BVABCWildSolution sol) :
    ¬ InLinftyTHHalf sol :=
  h.belowH12

/-- **Companion lemma (BV/ABC vs classical L^∞ vorticity).**

A BV/ABC wild solution has no classical `L^∞_x` vorticity field. -/
theorem BV_wild_excludes_classical_vorticity
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    {sol : NavierStokes.WeakSolution nse}
    (h : BVABCWildSolution sol) :
    ¬ ClassicalLinfVorticity sol :=
  h.vortUnbd

end

end ZtareProofs.NS
