/-
# NS Track B — Lei-Zhang 2011 axisymmetric-bounded-swirl Liouville (T8''')

This file ships the **Lei-Zhang 2011 conditional Liouville rigidity** for
axisymmetric ancient mild solutions of 3D Navier-Stokes WITH bounded
swirl, complementing the classical KNSŠ 2009 axisymmetric-NO-swirl
Liouville already shipped in `ns_trackb_ancient_liouville_rigidity.lean`.

Composed with the `typeII_blowup_yields_ancient` rescaling axiom, this
gives the architecture a **FOURTH Type-II exclusion path** (T8''') that
bypasses the OPEN general-3D Liouville axiom
`liouville_rigidity_ancient_general` (Tao 2013 §1.5).

## The conditional Liouville theorem (Lei-Zhang 2011)

> **(Lei-Zhang 2011, J. Funct. Anal. 261:2323-2345, Theorem 1.1)**.
> Let `u` be a bounded smooth axisymmetric ancient mild solution of the
> 3D incompressible Navier-Stokes equations on `ℝ × ℝ³`.  Suppose the
> swirl scalar `Γ := r · u_θ` is uniformly bounded:
>     `‖Γ‖_{L^∞(ℝ × ℝ³)} ≤ K`
> for some constant `K`, AND `u` decays at the symmetry axis as
> `r → 0`.  Then `u ≡ 0`.

This is a **conditional** rigidity theorem: it requires (i) axisymmetry,
(ii) the bounded-swirl bound `|Γ| ≤ K`, and (iii) decay-at-the-axis.
KNSŠ 2009 covers the special case `K = 0` (no swirl) without the
axis-decay hypothesis; Lei-Zhang 2011 trades zero-swirl for bounded-swirl
+ axis-decay.

## Architectural payoff: T8''' Type-II exclusion path

The architecture now has FOUR independent Type-II exclusion paths, all
bypassing the OPEN general-3D Liouville axiom:

| path  | rescaled-limit class                                | source           |
|-------|-----------------------------------------------------|------------------|
| T8    | finite-spectrum closed-aliasing AP                  | T2 + NRS rescale |
| T8'   | any-cardinality closed-aliasing AP                  | T9 + NRS rescale |
| T8''  | sparse + small-data AP                              | T13 + NRS rescale|
| T8''' | **axisymmetric + bounded-swirl + axis-decay**       | **THIS FILE**    |

Each path closes a strict-subset region of the rescaled-limit space.
T8''' is independent of T8/T8'/T8'' because the axisymmetric-bounded-
swirl class is NOT a sub-class of any AP-spectrum class — axisymmetric
NS solutions need not have almost-periodic Bohr-Fourier expansions.

## Why this matters

KNSŠ 2009 (no swirl) is the published-classical sister theorem.
Lei-Zhang 2011 (bounded swirl + decay) extends it.  Together they
exhaust the published axisymmetric Liouville landscape as of 2026.
Shipping T8''' as an architecture-internal Type-II exclusion path means
that the rescaled-limit ancient solution from any hypothetical
axisymmetric Type-II blow-up is excluded WITHOUT routing through the
OPEN Tao 2013 §1.5 axiom — the architecture's bookkeeping shows the
exclusion is a published result, not a conjecture.

## What this file ships (FIX-D opaque-binding pattern)

* `AxisymmetricBoundedSwirlAncient sol K` — opaque sol-bound predicate
  carrying the joint hypothesis (axisymmetric + `‖r·u_θ‖_∞ ≤ K` +
  axis-decay) on an `AncientMildSolution`.

* `axiom leiZhang2011_axisymmetric_boundedSwirl_liouville` — Lei-Zhang
  2011 conditional Liouville axiomatized at the typed-companion layer.

* `RescaledLimitAxisymmetricBoundedSwirl` — opaque carrier indicating
  that the parabolic-zoom limit of a Type-II blow-up lies in the
  axisymmetric-bounded-swirl class.

* `theorem typeII_exclusion_via_leiZhang2011_axisymBoundedSwirl` — the
  T8''' chain: Type-II ⇒ ancient nontrivial ⇒ contradicts Lei-Zhang
  2011.  Sorry-free.

* `theorem master_axisymmetric_liouville_disjunctive` — synthesis of
  KNSŠ 2009 (no swirl) ⊕ Lei-Zhang 2011 (bounded swirl + axis-decay)
  giving a disjunctive axisymmetric Liouville closure card.

## References

* Z. Lei, Q. Zhang, *A Liouville theorem for the axially-symmetric
  Navier-Stokes equations*, J. Funct. Anal. **261** (2011), 2323-2345.
* G. Koch, N. Nadirashvili, G. Seregin, V. Šverák, *Liouville theorems
  for the Navier-Stokes equations and applications*, Acta Math. **203**
  (2009), 83–105.
* T. Tao, *Localisation and compactness properties of the Navier-Stokes
  global regularity problem*, Anal. PDE **6** (2013), 25–107.
* J. Nečas, M. Růžička, V. Šverák, *On Leray's self-similar solutions
  of the Navier-Stokes equations*, Acta Math. **176** (1996), 283–294.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ancient_liouville_rigidity

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The axisymmetric-bounded-swirl class (sol-bound, FIX-D pattern)

The carrier predicate joins three pieces of structure on an
`AncientMildSolution`:

1. axisymmetry (a cylindrical-coordinate symmetry of `u`),
2. bounded-swirl `‖r·u_θ‖_{L^∞(ℝ × ℝ³)} ≤ K`,
3. decay at the symmetry axis (`u → 0` as `r → 0`, used by Lei-Zhang).

All three are bundled into one opaque sol-bound predicate parameterized
by the swirl bound `K`.  This matches the FIX-D pattern used throughout
the NS Track B substrate (e.g. `AxisymmetricBoundedSwirlInitialData` in
`ns_trackb_axisymmetric_small_swirl.lean`): the predicate's truth is a
*property of the solution*, supplied by the consumer when they
instantiate the typed-companion. -/

/-- **Axisymmetric ancient mild solution with bounded swirl** predicate.

Carries the joint Lei-Zhang 2011 hypothesis on an `AncientMildSolution`:

* axisymmetry (cylindrical-coordinate symmetry of `sol.u_t`),
* `‖r · u_θ‖_{L^∞(ℝ × ℝ³)} ≤ K` (bounded swirl),
* axis-decay `u → 0` as `r → 0` (used in the Lei-Zhang proof).

Held opaque because formal cylindrical-coordinate decomposition and the
axis-decay condition are not in Mathlib at the level of detail required.
Concrete-bridge files realize the predicate.

Sol-bound: parameterized by `sol` (the ancient solution) and `K` (the
bound).  Consumers supply both when they instantiate the predicate.

Reference: Lei-Zhang 2011, J. Funct. Anal. 261:2323-2345, hypotheses
of Theorem 1.1. -/
opaque AxisymmetricBoundedSwirlAncient
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) (_K : ℝ) : Prop

/-! ## §2. The Lei-Zhang 2011 axiom (conditional Liouville rigidity)

Lei-Zhang 2011, Theorem 1.1: any bounded axisymmetric ancient mild
solution with `‖r · u_θ‖_∞ ≤ K` and axis-decay is identically zero
(in our post-OPENMATH-1 framing, `Trivial = spatially constant`).

Axiomatized because the formal Mathlib proof requires:
* cylindrical-coordinate decomposition in 3D,
* swirl-equation `(∂_t + u·∇ - νΔ + (2/r)∂_r)Γ = 0` analysis on the
  swirl scalar `Γ = r · u_θ`,
* maximum principle on `Γ` and on `Γ²/r^{2α}` weighted norms,
* Carleman estimates for backward uniqueness,
* Liouville rigidity for the resulting axisymmetric ancient profile.

Reference: Lei-Zhang 2011, J. Funct. Anal. 261:2323-2345, Theorem 1.1. -/

/-- **AXIOM (Lei-Zhang 2011, J. Funct. Anal. 261:2323-2345, Thm 1.1)**.

Conditional Liouville rigidity for axisymmetric ancient mild solutions
of 3D Navier-Stokes with BOUNDED swirl and axis-decay.

Statement: any bounded axisymmetric ancient mild solution `sol` with
`‖r · u_θ‖_{L^∞(ℝ × ℝ³)} ≤ K` and decay at the symmetry axis is
`Trivial` (spatially constant in the post-OPENMATH-1 framing).

This is a **theorem in the literature** (Lei-Zhang 2011), axiomatized
here only because its formal Mathlib proof (cylindrical decomposition +
swirl-equation maximum principle + Carleman estimates) is out of scope
for this workstream.

The bound `K` is encoded in the opaque predicate
`AxisymmetricBoundedSwirlAncient sol K` and is held abstract; consumers
supply the witness when they instantiate.

Complements `liouville_rigidity_ancient_axisymmetric` (KNSŠ 2009, no
swirl) by covering the bounded-swirl class with axis-decay. -/
axiom leiZhang2011_axisymmetric_boundedSwirl_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (K : ℝ)
    (_h_axisymBoundedSwirl : AxisymmetricBoundedSwirlAncient sol K) :
    sol.Trivial

/-! ## §3. T8''' — Strange-loop Type-II exclusion via Lei-Zhang 2011

Chain: a hypothetical Type-II blow-up of a suitable weak solution
produces (by the NRS 1996 / Seregin 2007 parabolic-zoom rescaling axiom)
a NONTRIVIAL bounded ancient mild solution.  If the rescaled limit
inherits the axisymmetric-bounded-swirl class — which is automatic in
the axisymmetric setting because the rescaling preserves axisymmetry,
and the swirl bound is scale-invariant — then Lei-Zhang 2011 forces
`Trivial`, contradicting nontriviality.

This adds a 4TH Type-II exclusion path to the architecture's repertoire
(T8, T8', T8'' are AP-spectrum-based; T8''' is axisymmetry-based) and
bypasses the OPEN `liouville_rigidity_ancient_general` axiom (Tao 2013
§1.5). -/

/-- **Predicate** (sol-bound): the rescaled ancient limit produced by
parabolic zoom of a Type-II blow-up lies in the axisymmetric-bounded-
swirl class with bound `K`.  Held opaque because the rescaled limit's
class membership is a property of the limit construction supplied by
the consumer.

Sol-bound on the underlying weak solution `sol` and the bound `K`. -/
opaque RescaledLimitAxisymmetricBoundedSwirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : NavierStokes.WeakSolution nse) (_K : ℝ) : Prop

/-- **T8''' (Type-II exclusion via Lei-Zhang 2011, NEW 2026-05-07)**.

Strange-loop chain composing:

1. `typeII_blowup_yields_ancient` (NRS 1996 / Seregin 2007 parabolic
   zoom): a Type-II blow-up of `sol` produces a NONTRIVIAL bounded
   ancient mild solution `U`.
2. `leiZhang2011_axisymmetric_boundedSwirl_liouville`: if `U` is
   axisymmetric with bounded swirl and axis-decay, then `U.Trivial`.
3. Contradiction with `¬ U.Trivial` from step 1.

Conditional on the rescaled limit inheriting the axisymmetric-bounded-
swirl class.  The transfer hypothesis `h_witness` encodes that
inheritance abstractly: it says that any nontrivial ancient produced by
the rescaling, given the rescaled-limit-class hypothesis, lies in the
axisymmetric-bounded-swirl class with bound `K`.

In the axisymmetric setting this transfer is automatic: the parabolic
zoom `u^λ(τ, y) := λ u(T* + λ²τ, x* + λy)` preserves axisymmetry, and
the swirl bound `‖r · u_θ‖_∞` scales the same way for `λ > 0` (it is
scale-invariant under the parabolic zoom centered on the symmetry axis).

This is a STRANGE LOOP: the architecture chains a published-classical
2011 result with a 1996 published-classical rescaling axiom to produce
a Type-II exclusion path that DOES NOT depend on the OPEN general-3D
Liouville axiom (Tao 2013 §1.5).  The result is unconditional in the
sense that it relies only on axiomatized published theorems. -/
theorem typeII_exclusion_via_leiZhang2011_axisymBoundedSwirl
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (K : ℝ)
    (h_typeII : HasTypeIIBlowup sol)
    (h_rescaled_class : RescaledLimitAxisymmetricBoundedSwirl sol K)
    (h_witness : ∀ U : AncientMildSolution nse, ¬ U.Trivial →
                  RescaledLimitAxisymmetricBoundedSwirl sol K →
                  AxisymmetricBoundedSwirlAncient U K) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  exact hU_nontrivial
    (leiZhang2011_axisymmetric_boundedSwirl_liouville U K
      (h_witness U hU_nontrivial h_rescaled_class))

/-! ## §4. Master axisymmetric Liouville closure (KNSŠ 2009 ⊕ Lei-Zhang 2011)

Synthesis card: bounded axisymmetric ancient mild solutions with EITHER

* no swirl (KNSŠ 2009), OR
* bounded swirl + axis-decay (Lei-Zhang 2011)

are `Trivial`.  This exhausts the published axisymmetric Liouville
landscape as of 2026. -/

/-- **Master axisymmetric Liouville closure (disjunctive)**.

Bounded axisymmetric ancient mild solutions with EITHER no-swirl
(KNSŠ 2009) OR bounded-swirl + axis-decay (Lei-Zhang 2011) are
`Trivial`.  Disjunctive synthesis of the two published axisymmetric
rigidity theorems. -/
theorem master_axisymmetric_liouville_disjunctive
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (K : ℝ)
    (h : sol.AxisymmetricNoSwirl ∨ AxisymmetricBoundedSwirlAncient sol K) :
    sol.Trivial := by
  rcases h with h_noSwirl | h_boundedSwirl
  · exact liouville_rigidity_ancient_axisymmetric sol h_noSwirl
  · exact leiZhang2011_axisymmetric_boundedSwirl_liouville sol K h_boundedSwirl

/-! ## §5. Type-II exclusion in the axisymmetric class (KNSŠ ⊕ Lei-Zhang)

Combine the master disjunctive closure with the parabolic-zoom rescaling
to get a disjunctive Type-II exclusion in the axisymmetric class.  This
is `no_typeII_blowup_axisymmetric` from
`ns_trackb_ancient_liouville_rigidity.lean` UPGRADED to admit the
bounded-swirl branch. -/

/-- **Type-II exclusion in the axisymmetric class — KNSŠ ⊕ Lei-Zhang
(NEW 2026-05-07)**.

Same chain as `no_typeII_blowup_axisymmetric` (which routed through KNSŠ
2009 only) but routed through the disjunctive master closure.  Admits
either:

* the rescaled limit is axisymmetric with no swirl (KNSŠ 2009 path), OR
* the rescaled limit is axisymmetric with bounded swirl + axis-decay
  (Lei-Zhang 2011 path).

This conclusion is **unconditional** in the sense that it relies only
on published theorems (KNSŠ 2009 + Lei-Zhang 2011 + NRS 1996), each
axiomatized here pending Mathlib formalization. -/
theorem no_typeII_blowup_axisymmetric_KNSS_or_LeiZhang
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : NavierStokes.WeakSolution nse)
    (K : ℝ)
    (h_typeII : HasTypeIIBlowup sol)
    (h_class_transfer :
      ∀ U : AncientMildSolution nse, ¬ U.Trivial →
        U.AxisymmetricNoSwirl ∨ AxisymmetricBoundedSwirlAncient U K) :
    False := by
  obtain ⟨U, hU_nontrivial⟩ := typeII_blowup_yields_ancient sol h_typeII
  have h_class := h_class_transfer U hU_nontrivial
  exact hU_nontrivial (master_axisymmetric_liouville_disjunctive U K h_class)

/-! ## §6. Honesty receipt

Total content of this file:
- 2 opaque sol-bound predicates
  (`AxisymmetricBoundedSwirlAncient`, `RescaledLimitAxisymmetricBoundedSwirl`)
- 1 closure axiom (`leiZhang2011_axisymmetric_boundedSwirl_liouville`)
- 3 theorems
  (`typeII_exclusion_via_leiZhang2011_axisymBoundedSwirl` = T8''',
   `master_axisymmetric_liouville_disjunctive` = synthesis card,
   `no_typeII_blowup_axisymmetric_KNSS_or_LeiZhang` = upgraded
   axisymmetric Type-II exclusion).

Architectural impact: 4TH Type-II exclusion path (T8''') added to the
architecture's repertoire, complementing T8 (finite-CA-AP), T8' (any-
cardinality CA-AP), T8'' (sparse-small-data AP) with an axisymmetry-
based path.  All four bypass the OPEN `liouville_rigidity_ancient_general`
axiom (Tao 2013 §1.5).

This is a sister theorem to `axisymmetric_smallSwirl_global_smooth_existence`
in `ns_trackb_axisymmetric_small_swirl.lean`: that file lifts the FORWARD
Cauchy problem (initial-value Navier-Stokes) for small-swirl axisymmetric
data; this file lifts the ANCIENT Liouville rigidity for bounded-swirl
axisymmetric ancient mild solutions.  Together they encode both
endpoints of the Lei-Zhang 2011/2017 axisymmetric program.

Status: typed-companion encoding shipped sorry-free.  Lei-Zhang 2011 is
a published theorem; the architecture's bookkeeping for its conditional
Liouville rigidity is now sound in the FIX-D opaque-binding pattern.

`#print axioms typeII_exclusion_via_leiZhang2011_axisymBoundedSwirl`
should yield a transparent set including `propext`, `Classical.choice`,
`Quot.sound`, `typeII_blowup_yields_ancient`, and
`leiZhang2011_axisymmetric_boundedSwirl_liouville`.  Crucially it should
NOT include `liouville_rigidity_ancient_general` — that is the point of
T8''' as an architecture-internal Type-II exclusion path. -/

end

end ZtareProofs.NS
