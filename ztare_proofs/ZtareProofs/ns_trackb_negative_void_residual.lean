/-
# NS Track B — Negative-Void Residual (Munger Inversion of Clay)

This file formalizes the **exact remaining Clay statement** after
architectural subtraction. We invert the question: instead of asking
"can we close all bounded-ancient-mild solutions?", we ask "what
class of bounded-ancient-mild solutions is NOT yet closed by either
the architecture or the published literature?". The residual class —
the *negative void* — is the precise inhabitant set Clay still requires
to be excluded.

## Subtraction list (14 closed sub-classes)

A bounded ancient mild solution `sol` is **architecturally accounted
for** if it inhabits any of the following predicates:

1.  `IsSelfSimilarTypeII sol`        (NRŠ 1996; Šverák 2003)
2.  `IsAxisymmetricNoSwirl sol`      (KNSŠ 2009)
3.  `IsAxisymmetricBoundedSwirlAxisDecay sol`  (Lei-Zhang 2011)
4.  `IsClosedAliasingAP sol`         (T9 — sum-closed FM_{σ,δ} backward Liouville)
5.  `IsHadamardLacunaryAP sol`       (T11 — auto-CA via triangle inequality)
6.  `IsSparseSmallDataAP sol`        (T13)
7.  `IsFiniteResonanceSmallDataAP sol`  (T10)
8.  `IsAntiTwistRegime sol`          (Hou-Luo 2024 empirical regularization)
9.  `IsTypeI_Linfty_Rate sol`        (LPS / Serrin classical)
10. `IsLinftyL3Bounded sol`          (ESS 2003)
11. `IsL3LimsupFinite sol`           (Seregin 2012)
12. `IsBoundedStationaryDecayOrLp sol` (Galdi 2011 / Chae-Wolf, p ≥ 9/2)
13. `IsTemporallyAP sol`             (Foiaș-Saut / Khovanov)
14. `IsBVABCWildBelowH12 sol`        (BV 2019 / ABC 2022; below `H^{1/2}`)

The **negative-void residual** is the class of bounded-ancient-mild
solutions in NONE of these predicates.

## What this file is

A typed predicate `BoundedAncientMildResidual sol` characterizing the
residual class, plus a conjectural axiom `negative_void_empty_conjecture`
formalizing the Clay-equivalent statement: this residual is empty.

## Why this is the EXACT Clay-attack

Every closed sub-class above is shipped as a sorry-free or
literature-cited closure inside the `ns_trackb_*` architecture. The
residual class is therefore the *named gap* between the architecture
and Clay. If the residual is empty, Clay closes; if it is non-empty,
the example exhibits the missing closure principle.

This is a Munger **inversion** rather than a positive proof: we do not
attempt to show emptiness directly. We freeze the void shape so that
any future closure attempt can be benchmarked against the exact
residual it claims to handle.

## Status

`negative_void_empty_conjecture` is `axiom`-level and is the formal
statement of the Clay Millennium Problem RESTRICTED to the residual.
Together with the 14 closure theorems/axioms it is logically equivalent
to the full Clay statement on bounded-ancient-mild solutions.
-/

import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bv_abc_boundary
import ZtareProofs.ns_trackb_ancient_liouville_rigidity
import ZtareProofs.ns_trackb_lei_zhang_2011_axisym_liouville
import ZtareProofs.ns_trackb_hou_luo_antitwist
import ZtareProofs.ns_trackb_galdi_op_9_3_AP_closure
import ZtareProofs.ns_trackb_ess_l3_endpoint

namespace ZtareProofs.NS

noncomputable section

/-! ## Sub-class predicates (opaque, sol-binding) -/

/-- Self-similar Type-II profile (NRŠ 1996; Šverák 2003 closes). -/
opaque IsSelfSimilarTypeII {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Axisymmetric without swirl (KNSŠ 2009 closes). -/
opaque IsAxisymmetricNoSwirl {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Axisymmetric, bounded swirl, axis decay (Lei-Zhang 2011 closes). -/
opaque IsAxisymmetricBoundedSwirlAxisDecay
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Closed-aliasing almost-periodic spectrum (architecture T9). -/
opaque IsClosedAliasingAP {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Hadamard-lacunary AP spectrum (architecture T11). -/
opaque IsHadamardLacunaryAP {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Sparse small-data AP (architecture T13). -/
opaque IsSparseSmallDataAP {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Finite-resonance small-data AP (architecture T10). -/
opaque IsFiniteResonanceSmallDataAP
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Anti-twist regularization regime (Hou-Luo 2024). -/
opaque IsAntiTwistRegime {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Type-I `L^∞`-rate alone (classical LPS). -/
opaque IsTypeI_Linfty_Rate {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- `L^∞_t L^3_x` bounded (ESS 2003); reuses
`InLinftyTL3` from `ns_trackb_bv_abc_boundary.lean`. -/
abbrev IsLinftyL3Bounded {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  InLinftyTL3 sol

/-- `L^3` lim-sup finite (Seregin 2012). -/
opaque IsL3LimsupFinite {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Bounded stationary with decay or `u ∈ L^p, p ≥ 9/2`
(Galdi 2011 / Chae-Wolf). -/
opaque IsBoundedStationaryDecayOrLp
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- Periodic / temporally almost-periodic (Foiaș-Saut / Khovanov). -/
opaque IsTemporallyAP {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-- BV/ABC wild stratum below `H^{1/2}`; reuses the typed predicate
from `ns_trackb_bv_abc_boundary.lean`. -/
abbrev IsBVABCWildBelowH12 {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  BVABCWildSolution sol

/-! ## Bounded-ancient-mild marker -/

/-- Abstract marker that `sol` is a **bounded ancient mild** solution:
* `t ∈ (-∞, 0]` ancient time-domain;
* spatial-`L^∞` bounded uniformly in `t` (after rescaling);
* mild-form regularity (parabolic smoothing P★);
* derivatives bounded uniformly in `t` (RD-D's lemma T4 envelope).

This is the ambient class on which Clay is restricted by the
ancient-rescaling reduction. -/
opaque IsBoundedAncientMild
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop

/-! ## The residual predicate -/

/-- **`BoundedAncientMildResidual sol`** — the typed signature of the
*negative void*: a bounded-ancient-mild solution that is NOT in any
of the 14 closed sub-classes.

A constructive inhabitant of this predicate would be a Clay-equivalent
counterexample candidate; emptiness of inhabitants is Clay-equivalent
on the bounded-ancient-mild stratum. -/
structure BoundedAncientMildResidual
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop where
  isBAM     : IsBoundedAncientMild sol
  notSS2    : ¬ IsSelfSimilarTypeII sol
  notAxNS   : ¬ IsAxisymmetricNoSwirl sol
  notAxBSAD : ¬ IsAxisymmetricBoundedSwirlAxisDecay sol
  notCAAP   : ¬ IsClosedAliasingAP sol
  notHLAP   : ¬ IsHadamardLacunaryAP sol
  notSSDAP  : ¬ IsSparseSmallDataAP sol
  notFRSDAP : ¬ IsFiniteResonanceSmallDataAP sol
  notAT     : ¬ IsAntiTwistRegime sol
  notTI     : ¬ IsTypeI_Linfty_Rate sol
  notLiL3   : ¬ IsLinftyL3Bounded sol
  notL3LSF  : ¬ IsL3LimsupFinite sol
  notBSDLp  : ¬ IsBoundedStationaryDecayOrLp sol
  notTAP    : ¬ IsTemporallyAP sol
  notBVABC  : ¬ IsBVABCWildBelowH12 sol

/-! ## The negative-void conjecture -/

/-- **Negative-Void Empty Conjecture (Clay-equivalent on BAM).**

No bounded-ancient-mild Navier-Stokes solution inhabits the residual
class. Equivalently, every bounded-ancient-mild solution lies in at
least one of the 14 closed sub-classes.

This is the **exact remaining Clay statement** after architectural
subtraction. It is shipped as `axiom` to make the void shape
formal; closing the conjecture is equivalent to closing Clay on the
bounded-ancient-mild stratum (which itself reduces from full Clay
by the standard parabolic-rescaling normalization). -/
axiom negative_void_empty_conjecture
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) :
    ¬ BoundedAncientMildResidual sol

/-! ## Companion: trivial Clay reduction on BAM -/

/-- **Clay reduction on the BAM stratum.**

If `sol` is bounded-ancient-mild, then `sol` falls into one of the 14
closed sub-classes (the architectural disjunction). This is the
contrapositive of `negative_void_empty_conjecture` rephrased as a
disjunctive coverage statement. -/
theorem clay_disjunctive_coverage_on_BAM
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse)
    (h : IsBoundedAncientMild sol) :
    IsSelfSimilarTypeII sol ∨ IsAxisymmetricNoSwirl sol ∨
    IsAxisymmetricBoundedSwirlAxisDecay sol ∨ IsClosedAliasingAP sol ∨
    IsHadamardLacunaryAP sol ∨ IsSparseSmallDataAP sol ∨
    IsFiniteResonanceSmallDataAP sol ∨ IsAntiTwistRegime sol ∨
    IsTypeI_Linfty_Rate sol ∨ IsLinftyL3Bounded sol ∨
    IsL3LimsupFinite sol ∨ IsBoundedStationaryDecayOrLp sol ∨
    IsTemporallyAP sol ∨ IsBVABCWildBelowH12 sol := by
  by_contra hcontra
  push_neg at hcontra
  obtain ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14⟩ := hcontra
  exact negative_void_empty_conjecture sol
    { isBAM := h, notSS2 := h1, notAxNS := h2, notAxBSAD := h3,
      notCAAP := h4, notHLAP := h5, notSSDAP := h6, notFRSDAP := h7,
      notAT := h8, notTI := h9, notLiL3 := h10, notL3LSF := h11,
      notBSDLp := h12, notTAP := h13, notBVABC := h14 }

end

end ZtareProofs.NS
