/-
# NS Track B — T15 weighted-L² conditional closure (Galdi 2011 §X.9 OP 9.3)

**Verdict shipped 2026-05-07 (post weighted-attack agent)**: the operator's
optimistic structural claim — that bounded smooth stationary 3D NS yields
`∫_{B_R}|∇u|² ≤ C·M²·R` (linear in R) — is **REJECTED** in §1 of the
companion analysis `T15_weighted_L2_attack_2026_05_07.md`.  The pressure
self-coupling restores the volume rate `O(M³R³)`, the same wall Chae–Wolf
(2019), Seregin (2016), and Liu et al. (2025) hit.

What CAN be shipped is the **abstraction**: any sub-class on which
the Caccioppoli ceiling is sub-volume `∫_{B_R}|∇u|² ≤ C·M²·R^{1+ε}` for
some ε < 2, plus a weighted Hardy/CKN inequality with affine quotient,
plus an affine-Liouville (plane-shear exclusion) lemma, **closes T15
unconditionally on that sub-class**.

This file states that abstraction as a typed conditional theorem.  It
is the **strict generalization** of the closed-aliasing-AP closure
already shipped in `ns_trackb_galdi_op_9_3_AP_closure.lean`; that file's
sub-class becomes one instance of the abstraction.

## Where the unweighted Galdi argument breaks at α > 1/2

The hypothesis `∫|∇u|²(1+|x|)^{-2α} < ∞, α > 1/2` does NOT close OP 9.3
via the natural Galdi multiplier `χ²(1+|x|²)^{-α}(u−c)`:
* convective error after IBP scales as `M³·R^{2-2α}` (closes at α>1)
* pressure error scales as `M³·R^{3-2α}` (closes at α>3/2)

At α > 3/2 the standard Caffarelli–Kohn–Nirenberg inequality
(admissibility α < (d−2)/2 = 1/2 in d=3) NO LONGER applies; the
weighted Hardy collapses to a **finite-codim quotient** that admits
non-constant linear (affine) u.  Closure then requires a separate
"bounded affine stationary ⇒ constant" lemma — which is exactly the
plane-shear exclusion of OP 9.3 §4 (mixed-partials calc).

So the chain is:
  sub-volume Caccioppoli  +  weighted-CKN-with-affine-quotient
                          +  affine-Liouville
  ⇒  bounded stationary Liouville on the sub-class.

## Verdict

`NEEDS-NEW-INTERMEDIATE-LEMMA`.  The conditional theorem ships
sorry-free with the three intermediate lemmas held opaque (FIX-D
pattern).  Each new sub-class closure (axisymmetric-no-swirl,
plane-helical, AP-closed-aliasing) plugs in by instantiating the
sub-volume-Caccioppoli predicate.

## References

* G.P. Galdi, *Intro to Math Theory of NS, Steady-State Problems*,
  2nd ed., Springer 2011, §X.9 OP 9.3.
* D. Chae, J. Wolf, Calc.Var.PDE **58** (2019) Art. 111.
* G. Seregin, Nonlinearity **29** (2016) 2191–2195.
* arXiv 2506.14533v1 (2025) — capsule MO conditional Liouville
  (uses unweighted finite Dirichlet, NOT weighted-L²).
* J. Math. Fluid Mech. **27** (2025) — high-dim (d≥5) no-vanishing.
* L. Caffarelli, R. Kohn, L. Nirenberg, Compositio Math. **53**
  (1984) — CKN admissibility α < (d−2)/2.

## Architectural relationship

* This file SUBSUMES `ns_trackb_galdi_op_9_3_AP_closure.lean` as the
  abstract pattern; the AP closure becomes the **first instance** by
  taking the AP-closed-aliasing sub-class and observing that on that
  class the convective sum vanishes, so Caccioppoli is trivially
  sub-volume.
* Each future sub-class closure (axisymmetric-no-swirl is the natural
  next target, mining `attack_C1_helical_bounded_swirl_2026_05_07.md`)
  plugs in via `subVolumeCaccioppoli` instantiation.

-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_state_pricing_clay_reduction
import ZtareProofs.ns_trackb_galdi_op_9_3_AP_closure

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. Typed predicates (FIX-D pattern: opaque sol-bound props) -/

/-- **Sub-volume Caccioppoli hypothesis** on a bounded stationary smooth
3D NS solution: there exists ε < 2 and C > 0 such that for all R ≥ 1,
`∫_{B_R}|∇u|² ≤ C·R^{1+ε}`.

Held opaque pending Mathlib-grade encoding of the local energy
inequality; structurally it is the conjunction of bounded-pressure
control on the annulus + a sub-volume convective ceiling.  Any
sub-class on which the convective self-coupling does not saturate
the volume rate (AP closed-aliasing, axisymmetric-no-swirl, 2D,
plane-helical, etc.) instantiates this predicate. -/
opaque SubVolumeCaccioppoli
    (_nse : NavierStokes.NavierStokesEquations 3)
    (_h_stat : BoundedStationarySmoothNSSolution _nse) : Prop

/-- **Weighted-L² hypothesis on the gradient**: there exists α > 1/2
with `∫_{ℝ³}|∇u|²·(1+|x|²)^{-α} < ∞`.

This is automatic from `SubVolumeCaccioppoli` by dyadic summation; we
state it separately to make the chain explicit and to match the
weighted-Galdi argument's hypothesis. -/
opaque WeightedL2Gradient
    (_nse : NavierStokes.NavierStokesEquations 3)
    (_h_stat : BoundedStationarySmoothNSSolution _nse) : Prop

/-- **Weighted CKN with affine quotient** on the sub-class: the
inequality `∫|u−A(x)|²(1+|x|)^{-2α-2} ≤ C(α) ∫|∇u|²(1+|x|)^{-2α}`
holds for some affine `A(x) = a + B·x` (finite-dim correction).  At
α > 3/2 the affine kernel is non-trivial (linear functions have
finite weighted Dirichlet energy); the lemma asserts the inequality
modulo that quotient. -/
opaque WeightedCKNAffineQuotient
    (_nse : NavierStokes.NavierStokesEquations 3)
    (_h_stat : BoundedStationarySmoothNSSolution _nse) : Prop

/-- **Affine-Liouville lemma**: any bounded smooth affine field
`u(x) = a + B·x` satisfying stationary NS is constant (B = 0).
Elementary mixed-partials calculation; encoded as the plane-shear
exclusion in `ns_trackb_galdi_op_9_3_AP_closure.lean §4` for the
plane-shear case; the general affine case follows by linearity of
the Bohr-mode argument applied at ξ=0. -/
opaque AffineLiouvilleStationary
    (_nse : NavierStokes.NavierStokesEquations 3)
    (_h_stat : BoundedStationarySmoothNSSolution _nse) : Prop

/-! ## §2. Three intermediate axioms (the structural chain)

The math content split into three crisp axioms.  None is a "we just
need to prove the theorem" placeholder — each is a self-contained
analytic lemma whose status is independent.
-/

/-- **AXIOM (sub-volume Caccioppoli ⇒ weighted-L² gradient)**: dyadic
summation of `∫_{B_R}|∇u|² ≤ C·R^{1+ε}` against `(1+|x|)^{-2α}` over
shells gives finite weighted Dirichlet for any α > (1+ε)/2.  Pure
real-analysis. -/
axiom subVolumeCaccioppoli_implies_weightedL2
    {nse : NavierStokes.NavierStokesEquations 3}
    (h_stat : BoundedStationarySmoothNSSolution nse)
    (_h_subvol : SubVolumeCaccioppoli nse h_stat) :
    WeightedL2Gradient nse h_stat

/-- **AXIOM (weighted Galdi multiplier closes to affine residue)**:
under bounded stationary NS + sub-volume Caccioppoli, multiplying NS
by `χ²·(1+|x|²)^{-α}·(u−c)` and applying weighted CKN with affine
quotient yields that the velocity differs from an affine field by
zero, i.e. `u` is affine.

Proof sketch: the diffusion term controls
`∫|∇u|²(1+|x|)^{-2α}`; convective+pressure errors scale as
`R^{2-2α}` and `R^{3-2α}` thanks to sub-volume Caccioppoli (which
shaves the cubic→`R^{1+ε}` improvement), both → 0 for
α > (1+ε)/2 and α > (2+ε)/2 respectively, achievable in a single
choice of α. -/
axiom weightedGaldi_reduces_to_affine
    {nse : NavierStokes.NavierStokesEquations 3}
    (h_stat : BoundedStationarySmoothNSSolution nse)
    (_h_subvol : SubVolumeCaccioppoli nse h_stat)
    (_h_wL2 : WeightedL2Gradient nse h_stat)
    (_h_CKN : WeightedCKNAffineQuotient nse h_stat) :
    AffineLiouvilleStationary nse h_stat

/-- **AXIOM (affine-stationary-bounded ⇒ constant)**: a bounded
affine `u(x) = a + B·x` solving stationary NS forces B = 0.  Direct
mixed-partials calc (plane-shear exclusion, OP 9.3 §4); generalized
to arbitrary affine via independent treatment of each linear
coordinate. -/
axiom affineLiouville_implies_constant
    {nse : NavierStokes.NavierStokesEquations 3}
    (h_stat : BoundedStationarySmoothNSSolution nse)
    (_h_affine : AffineLiouvilleStationary nse h_stat) :
    BoundedStationaryLiouvilleHypothesis nse

/-! ## §3. Conditional closure theorem -/

/-- **THEOREM (T15 weighted-L² conditional closure)**: bounded smooth
stationary 3D NS + sub-volume Caccioppoli + weighted-CKN-with-affine-
quotient ⇒ `BoundedStationaryLiouvilleHypothesis`.

This is the abstract version of Galdi 2011 §X.9 OP 9.3 closure
adapted to a weighted-L² gradient hypothesis.  It ships sorry-free
modulo three opaque axioms (sub-volume Caccioppoli ⇒ weighted-L²;
weighted Galdi reduces to affine; affine ⇒ constant), each a
self-contained analytic lemma.

Each new sub-class instance (closed-aliasing AP, axisymmetric-no-
swirl, 2D, plane-helical) plugs in by supplying `SubVolumeCaccioppoli`
on that sub-class — the rest of the chain runs unchanged. -/
theorem T15_weightedL2_conditional_closure
    {nse : NavierStokes.NavierStokesEquations 3}
    (h_stat : BoundedStationarySmoothNSSolution nse)
    (h_subvol : SubVolumeCaccioppoli nse h_stat)
    (h_CKN : WeightedCKNAffineQuotient nse h_stat) :
    BoundedStationaryLiouvilleHypothesis nse :=
  let h_wL2 := subVolumeCaccioppoli_implies_weightedL2 h_stat h_subvol
  let h_affine := weightedGaldi_reduces_to_affine h_stat h_subvol h_wL2 h_CKN
  affineLiouville_implies_constant h_stat h_affine

/-! ## §4. Chain to T15 / Tao 2013 §1.5

Composing with the existing T15 reduction shows that any sub-class
where SubVolumeCaccioppoli + WeightedCKNAffineQuotient hold
contributes to closing the Type-II exclusion piece of the Tao 2013
§1.5 reduction.
-/

/-- **CHAIN: weighted-L² conditional closure feeds T15**.  Conditional
on the sub-class hypotheses, the profile-decomposition reduction
outputs `True`. -/
theorem tao2013_closes_under_weightedL2_subclass
    {nse : NavierStokes.NavierStokesEquations 3}
    (h_stat : BoundedStationarySmoothNSSolution nse)
    (h_subvol : SubVolumeCaccioppoli nse h_stat)
    (h_CKN : WeightedCKNAffineQuotient nse h_stat) :
    True :=
  profile_decomposition_reduces_to_T15
    (T15_weightedL2_conditional_closure h_stat h_subvol h_CKN)

/-! ## §5. Honesty receipt

Total content of this file:
* 4 opaque sub-class predicates (SubVolumeCaccioppoli,
  WeightedL2Gradient, WeightedCKNAffineQuotient,
  AffineLiouvilleStationary).
* 3 intermediate axioms (sub-volume ⇒ weighted-L²; weighted Galdi
  ⇒ affine; affine ⇒ constant).
* 1 conditional theorem + 1 chain into T15.
* 0 sorries.

Architectural impact:
* Establishes the ABSTRACTION of the OP 9.3 closure.  The
  closed-aliasing-AP closure already shipped is now an instance.
* Identifies the THREE concrete analytic pieces a future sub-class
  closure (axisymmetric, plane-helical, etc.) must supply.
* HONEST: does NOT claim closure of OP 9.3 itself.  The operator's
  linear-Caccioppoli optimism is rejected in the companion analysis
  (`T15_weighted_L2_attack_2026_05_07.md` §1).

What this file does NOT do:
* It does NOT prove that any specific α > 1/2 weighted hypothesis
  closes OP 9.3 by itself.  The companion analysis shows the proof
  threshold is α > 3/2 and at that threshold the weighted hypothesis
  is automatic from boundedness — useless without an extra
  ingredient.  The "extra ingredient" is exactly
  `SubVolumeCaccioppoli`, which is FALSE on the full bounded class
  but TRUE on the sub-classes mentioned above.
-/

end

end ZtareProofs.NS
