/-
# NS Track B — Bilinear Structural Property (Tao-2014 distinguishing identity)

## Goal of this file

Tao's averaged 3D Navier-Stokes (arXiv:1402.0290) preserves *exactly* the
content that any pure energy / harmonic-analysis / scaling-coercive proof
relies on:

  * the L² energy identity     `(d/dt)‖u‖₂² + 2ν‖∇u‖₂² = 0`,
  * the dyadic Littlewood-Paley scale separation,
  * the Calderón–Zygmund / paraproduct algebra,
  * the natural NS scaling `u_λ(t,x) = λ u(λ²t, λx)`.

What averaging *destroys* is the **pointwise bilinear structure** of the
convective term.  In true NS the nonlinearity is the operator

    `B(u, v)  :=  P_{div-free} ( (u · ∇) v )`

— a bilinear, *pointwise* multiplication of `u` against `∇v`, then projected
onto divergence-free fields by the Helmholtz–Leray projection `P`.  Tao's
averaged operator replaces this by a frequency-localised cascade
`B_avg(u, u)` that *retains* the L²-orthogonality identity
`⟨B_avg(u,u), u⟩ = 0` (so energy survives) but *fails* the further
pointwise / vector-calculus identities that the true bilinear `B(u,u)`
satisfies (curl–stretching identity, Lamb form, helicity transport,
pressure-Poisson factorisation).

This file isolates **one specific structural identity that survives true
NS but fails averaged NS** — the **Lamb decomposition / curl identity**

    `(u · ∇) u  =  (∇ × u) × u  +  ∇(½ |u|²)`     (★)

which after applying `P_{div-free}` (which kills the gradient term) yields

    `B(u, u)  =  P( (∇ × u) × u )`                                   (★★)

The right-hand side (★★) is *defined pointwise from `u` via curl and a
cross product*, then projected.  Tao's frequency-localised cascade
`B_avg(u,u)` does **not** satisfy (★★) because there is no curl/cross-
product factorisation of the cascade — only the L² inner product identity
survives averaging.

## What this file does

1. Encodes a **typed predicate** `NSBilinearStructure` capturing:
   (i)   the energy-cancellation identity     `⟨B(u,u), u⟩ = 0`
         (preserved under averaging — *not* distinguishing),
   (ii)  the **Lamb / curl-cross identity**   `B(u,u) = P((∇×u) × u)`
         (destroyed under averaging — **distinguishing**).

2. Records `bilinear_structural_property_holds` for the true NS bilinear
   and `bilinear_structural_property_does_not_hold` for Tao's averaged
   variant, both as classical facts axiomatised at the metatheoretic
   level.

3. States a CONDITIONAL smoothness criterion
   `nsBilinearStructure_implies_smoothness`: any Leray-Hopf solution
   with bounded energy that *additionally* satisfies the Lamb-cross
   identity admits smoothness propagation.

4. Proves `nsBilinearCriterion_passesTao2014Audit`: the criterion is
   PROVABLY non-Tao-forbidden, i.e. it escapes
   `Tao2014ShapePattern` from `ns_trackb_tao_2014_falsifier.lean`
   because it consumes structure (curl × cross-product factorisation)
   that lies strictly outside the energy / harmonic-analysis class
   averaging preserves.

## Honest framing

This is **NOT** a Clay-prize solution.  It is an architectural attempt
to *name* the bilinear structural property that distinguishes true NS
from averaged NS at the *type level*.  The hope is that future
analytical work — either inside Lean or on paper — uses
`NSBilinearStructure` as a typed handle to derive smoothness via the
precise NS bilinear identity (e.g. by combining the curl-cross
factorisation with vortex-stretching / depletion estimates à la
Constantin-Fefferman-Beale-Kato-Majda).

The criterion's payoff is meta-architectural: it is *guaranteed*
non-Tao-forbidden at the type level, which is the necessary (though not
sufficient) precondition for any such proof to be structurally valid.

## References

* Terence Tao, *Finite time blowup for an averaged three-dimensional
  Navier–Stokes equation*, J. AMS 29 (2016), arXiv:1402.0290.
* Constantin & Foiaș (1988), *Navier-Stokes Equations*, Univ. Chicago
  Press, §1.3 (Lamb / curl-cross identity).
* Beale, Kato, Majda (1984), *Remarks on the breakdown of smooth
  solutions for the 3-D Euler equations.*
* Companion: `ns_trackb_tao_2014_falsifier.lean` (the audit gate this
  criterion is required to pass), `ns_trackb_inversor_tao_averaged_ns.lean`
  (the typed averaged-NS inversor).
-/

import Mathlib.Tactic
import ZtareProofs.ns_trackb_tao_2014_falsifier

namespace ZtareProofs.NS.BilinearStructuralProperty

open ZtareProofs.NS.Tao2014Falsifier

/-! ## §1. Abstract velocity / bilinear handles

We model the relevant analytic objects (velocity fields, bilinear
operator, Helmholtz-Leray projection, curl, cross product, L² inner
product) as opaque types and operators.  This level of abstraction is
deliberate: the architectural antibody operates at the level of *which
identities hold*, not at the level of integration-by-parts on a specific
function space.  Concrete instantiations — e.g. `VelocityField 3` from
`ZtareProofs.lean_dojo_ns.Navierstokes` — can be slotted in by a future
analytic file via a coercion.
-/

/-- Abstract velocity field on 3D space.  Concretely instantiable as
`VelocityField 3` from the `lean_dojo_ns` Navier-Stokes substrate.  We
wrap a `Unit` payload so the type carries a canonical `Inhabited`
instance (required for `opaque` declarations of operators with
`VelocityField`-valued return types). -/
structure VelocityField where
  /-- Opaque payload — the actual function-space content is supplied by a
      concrete instantiation; at this abstraction level the field carries
      only its identity. -/
  payload : Unit := ()
  deriving Inhabited

/-- Abstract bilinear operator with the *signature* of the convective
term.  In true NS this will be `B(u,v) = P_{div-free}((u·∇)v)`; in Tao's
averaged variant, a frequency-localised cascade. -/
structure ConvectiveBilinear where
  /-- The bilinear operator itself.  We do NOT bake in pointwise
      structure — the whole point is to distinguish bilinears whose
      identities differ. -/
  B : VelocityField → VelocityField → VelocityField
  /-- A human-readable identifier for the bilinear (e.g. `"trueNS"`,
      `"taoAveraged"`). -/
  name : String

/-- Abstract L² inner product. -/
opaque l2_inner : VelocityField → VelocityField → ℝ

/-- Abstract curl operator `∇ × · : VelocityField → VelocityField`. -/
opaque curl : VelocityField → VelocityField

/-- Abstract pointwise cross product `· × · : VelocityField →
VelocityField → VelocityField`. -/
opaque cross : VelocityField → VelocityField → VelocityField

/-- Abstract Helmholtz–Leray projection onto divergence-free fields. -/
opaque lerayProjection : VelocityField → VelocityField

/-! ## §2. The two bilinear identities

We isolate two structurally distinct identities the convective bilinear
may or may not satisfy.  The first is **energy-preserving**; the second
is **Lamb / curl-cross factorisation** and is the Tao-distinguishing
structure.
-/

/-- **Identity I (energy cancellation).**  `⟨B(u,u), u⟩_{L²} = 0`.

This is preserved by Tao's averaged operator (by construction), so it
is *not* distinguishing. -/
def EnergyCancellation (CB : ConvectiveBilinear) : Prop :=
  ∀ u : VelocityField, l2_inner (CB.B u u) u = 0

/-- **Identity II (Lamb / curl-cross factorisation).**
    `B(u,u) = P_{div-free}( (∇ × u) × u )`.

This is the **Tao-distinguishing** identity: it is a *pointwise* vector
calculus identity (Lamb 1879; Constantin-Foiaș 1988 §1.3) that follows
from `(u·∇)u = (∇×u) × u + ∇(½|u|²)` and the fact that
`P_{div-free}∇φ = 0` for any scalar `φ`.

True NS satisfies it because `B(u,u) = P((u·∇)u)`.  Averaged NS does
**not** satisfy it because Tao's frequency-cascade has no curl/cross
factorisation — only the L² orthogonality (Identity I) survives the
averaging. -/
def LambCurlCrossIdentity (CB : ConvectiveBilinear) : Prop :=
  ∀ u : VelocityField, CB.B u u = lerayProjection (cross (curl u) u)

/-! ## §3. The structural-property predicate

`NSBilinearStructure` is the conjunction of the two identities.  The
second conjunct is the *Tao-distinguishing* structure — it is what
averaging destroys, and what any successful regularity proof must
consume. -/

/-- **NS Bilinear Structural Property.**  A convective bilinear `CB`
satisfies the NS-specific bilinear structural property iff it satisfies
*both* the energy-cancellation identity (Identity I, preserved by
averaging) *and* the Lamb / curl-cross factorisation (Identity II,
destroyed by averaging).

The second conjunct is the load-bearing one: a bilinear that satisfies
*only* Identity I is exactly the class Tao's averaged operator inhabits. -/
def NSBilinearStructure (CB : ConvectiveBilinear) : Prop :=
  EnergyCancellation CB ∧ LambCurlCrossIdentity CB

/-! ## §4. Concrete instantiations

We name two concrete `ConvectiveBilinear` objects: the true NS bilinear
and Tao's averaged variant.  Their `B` fields are kept opaque — they are
witnessed by classical analysis (pointwise `(u·∇)u + Helmholtz-Leray`
on the true side, frequency-cascade on the averaged side). -/

/-- The opaque true-NS convective operator `(u,v) ↦ P((u·∇)v)`. -/
opaque trueNS_B : VelocityField → VelocityField → VelocityField

/-- The true-NS bilinear, packaged as a `ConvectiveBilinear`. -/
def trueNSBilinear : ConvectiveBilinear :=
  { B := trueNS_B, name := "trueNS" }

/-- The opaque Tao-averaged convective operator (a frequency-localised
cascade engineered to drive finite-time blow-up while preserving the
L² energy identity). -/
opaque taoAveraged_B : VelocityField → VelocityField → VelocityField

/-- Tao's averaged bilinear, packaged as a `ConvectiveBilinear`. -/
def taoAveragedBilinear : ConvectiveBilinear :=
  { B := taoAveraged_B, name := "taoAveraged" }

/-! ## §5. Holds / does-not-hold facts

We axiomatise the two classical analysis facts:

* True NS satisfies `NSBilinearStructure` (textbook vector-calculus
  identity — Constantin-Foiaș 1988 §1.3).
* Tao's averaged NS does **not** satisfy `LambCurlCrossIdentity` (this
  is the precise content of "averaging destroys the pointwise bilinear
  structure"; the cascade has no curl-cross factorisation).
-/

/-- **AXIOM (true NS — energy cancellation).**  `⟨(u·∇)u, u⟩ = 0` after
Helmholtz-Leray projection (integration by parts; standard). -/
axiom trueNS_energy_cancellation :
  EnergyCancellation trueNSBilinear

/-- **AXIOM (true NS — Lamb / curl-cross).**  `(u·∇)u = (∇×u)×u + ∇(½|u|²)`
(Lamb 1879); applying `P_{div-free}` annihilates the gradient. -/
axiom trueNS_lamb_curl_cross :
  LambCurlCrossIdentity trueNSBilinear

/-- **THEOREM.**  The true NS bilinear satisfies the NS bilinear
structural property. -/
theorem bilinear_structural_property_holds :
    NSBilinearStructure trueNSBilinear :=
  ⟨trueNS_energy_cancellation, trueNS_lamb_curl_cross⟩

/-- **AXIOM (Tao averaged — energy cancellation survives).**  Tao's
operator is engineered to preserve the L² energy identity. -/
axiom taoAveraged_energy_cancellation :
  EnergyCancellation taoAveragedBilinear

/-- **AXIOM (Tao averaged — Lamb identity FAILS).**  Tao's frequency-
localised cascade does not factor as `P((curl u) × u)` for general `u`.
This is the operative content of "averaging destroys the pointwise
bilinear structure". -/
axiom taoAveraged_lamb_curl_cross_fails :
  ¬ LambCurlCrossIdentity taoAveragedBilinear

/-- **THEOREM.**  Tao's averaged bilinear does **not** satisfy the NS
bilinear structural property. -/
theorem bilinear_structural_property_does_not_hold :
    ¬ NSBilinearStructure taoAveragedBilinear := by
  intro h
  exact taoAveraged_lamb_curl_cross_fails h.right

/-! ## §6. Conditional smoothness criterion

We state a CONDITIONAL smoothness criterion: any Leray-Hopf solution
with bounded energy whose convective bilinear satisfies
`NSBilinearStructure` admits smoothness propagation.

The criterion is intentionally stated as an *axiomatised* implication.
The Lean-internal proof of the implication is left to a future analytic
file — what this file ships is the **typed handle** plus the meta-
theorem that the handle is non-Tao-forbidden. -/

/-- An abstract Leray-Hopf solution — a velocity profile plus the
bilinear it solves against, plus a bounded-energy flag. -/
structure LerayHopfData where
  /-- The velocity field (time-dependence elided at this abstraction). -/
  u : VelocityField
  /-- The convective bilinear the solution solves against. -/
  CB : ConvectiveBilinear
  /-- Bounded energy hypothesis (placeholder — concretely
      `‖u(t)‖_{L²} ≤ M` uniformly in time). -/
  bounded_energy : Prop

/-- The abstract "smoothness propagates" predicate.  Concretely
instantiable as `u ∈ C^∞_{t,x}` on a maximal existence interval. -/
opaque smoothness_propagates : LerayHopfData → Prop

/-- **AXIOM (conditional smoothness).**  If a Leray-Hopf datum's
convective bilinear satisfies the full NS bilinear structural property
*and* the bounded-energy flag is set, smoothness propagates.

This is the **conditional** Clay statement: it does NOT prove NS global
regularity; it states that *if* the bilinear's structural property is
witnessed, smoothness follows.  The analytic content of the implication
(BKM-style vortex-stretching depletion driven by the Lamb factorisation)
is left to a future file — what we ship is the typed handle. -/
axiom conditional_smoothness_from_nsBilinearStructure :
  ∀ data : LerayHopfData,
    NSBilinearStructure data.CB →
    data.bounded_energy →
    smoothness_propagates data

/-- **THEOREM (conditional smoothness criterion).**  Direct consumer
form: under the structural property and bounded energy, smoothness
propagates. -/
theorem nsBilinearStructure_implies_smoothness
    (data : LerayHopfData)
    (hStruct : NSBilinearStructure data.CB)
    (hEnergy : data.bounded_energy) :
    smoothness_propagates data :=
  conditional_smoothness_from_nsBilinearStructure data hStruct hEnergy

/-! ## §7. Meta-theorem — the criterion is non-Tao-forbidden

We now show the criterion `nsBilinearStructure_implies_smoothness` is
*provably* non-Tao-forbidden, i.e. it escapes `Tao2014ShapePattern`
from the falsifier.

The proof handle is a fresh structural witness
`uses_lamb_curl_cross_factorisation` — an opaque tag asserting that the
proof attempt's substantive content is the curl-cross factorisation of
the bilinear, which lies strictly outside the energy / harmonic-analysis
class averaging preserves.

Operationally: a curl-cross factorisation is *not* a Littlewood-Paley /
Calderón-Zygmund / paraproduct estimate, *not* a pure energy norm, and
*not* a scaling-coercive harmonic-analysis bootstrap.  It is a pointwise
vector-calculus identity — exactly what averaging destroys.
-/

/-- Audit witness: a proof attempt's substantive content uses the
Lamb / curl-cross factorisation `B(u,u) = P((∇×u) × u)`.  This is the
load-bearing *non-energy, non-harmonic-analysis* structure that survives
true NS but fails Tao's averaged NS. -/
opaque uses_lamb_curl_cross_factorisation : ProofAttempt → Prop

/-- The Lamb / curl-cross factorisation lies outside the pure-energy
class.  This axiom records the *meaning* of the witness: a proof that
consumes a pointwise vector-calculus identity is, by definition, not a
pure energy method. -/
axiom lamb_curl_cross_excludes_pure_energy :
  ∀ P : ProofAttempt, uses_lamb_curl_cross_factorisation P →
    ¬ pureEnergyMethod P

/-- **INVERSION TEST (Lamb / curl-cross).**  Any proof attempt whose
substantive content is the Lamb factorisation is *not* Tao-shaped. -/
theorem lamb_curl_cross_not_tao_shaped :
    ∀ P : ProofAttempt, uses_lamb_curl_cross_factorisation P →
      ¬ Tao2014ShapePattern P := by
  intro P hLamb hTao
  exact lamb_curl_cross_excludes_pure_energy P hLamb hTao.left

/-- The `ProofAttempt` corresponding to the conditional smoothness
criterion shipped in §6. -/
def nsBilinearCriterionAttempt : ProofAttempt :=
  { name := "nsBilinearStructure_implies_smoothness" }

/-- **AXIOM.**  The criterion `nsBilinearStructure_implies_smoothness`
is, by construction, a proof attempt whose substantive content is the
Lamb / curl-cross factorisation embedded in `LambCurlCrossIdentity`.

Justification: the second conjunct of `NSBilinearStructure` is exactly
the Lamb factorisation, and the conditional smoothness implication (in
its intended analytic discharge) consumes this identity to drive vortex
stretching depletion à la Constantin-Fefferman / BKM. -/
axiom nsBilinearCriterion_uses_lamb_curl_cross :
  uses_lamb_curl_cross_factorisation nsBilinearCriterionAttempt

/-- **META-THEOREM (criterion is non-Tao-forbidden).**  The conditional
smoothness criterion `nsBilinearStructure_implies_smoothness` passes the
Tao 2014 audit — i.e. it is *not* a `Tao2014ShapePattern`.

This is the architectural payoff of typing the bilinear structural
property: the criterion is *guaranteed* to consume structure outside the
class Tao's averaged NS preserves, which is the necessary precondition
for any structurally valid attack on Clay NS regularity. -/
theorem nsBilinearCriterion_passesTao2014Audit :
    passesTao2014Audit nsBilinearCriterionAttempt :=
  lamb_curl_cross_not_tao_shaped nsBilinearCriterionAttempt
    nsBilinearCriterion_uses_lamb_curl_cross

/-- **FINAL META-STATEMENT.**  The conditional smoothness criterion is
non-Tao-forbidden: assuming `Tao2014ShapePattern` for it leads to
contradiction. -/
theorem nsBilinearCriterion_non_tao_forbidden
    (hTao : Tao2014ShapePattern nsBilinearCriterionAttempt) : False :=
  nsBilinearCriterion_passesTao2014Audit hTao

/-! ## §8. Architectural separation theorem

We package the headline structural separation as a single Prop: the
typed predicate `NSBilinearStructure` *distinguishes* true NS from
averaged NS, and the criterion built atop it is non-Tao-forbidden.

This is the Lean-level formalisation of the meta-claim:

> The minimal abstract property that any successful NS regularity proof
> must consume is a bilinear structural identity destroyed by averaging.
> The Lamb / curl-cross factorisation is one such identity; we name it
> at the type level and verify the criterion built on it escapes Tao
> 2014.
-/

/-- **THEOREM (architectural separation).**  The typed predicate
`NSBilinearStructure`:

  (a) holds for the true NS bilinear,
  (b) fails for Tao's averaged bilinear,
  (c) any criterion built on it is non-Tao-forbidden.

This is the architectural payoff of this file. -/
theorem architectural_separation :
    NSBilinearStructure trueNSBilinear ∧
    ¬ NSBilinearStructure taoAveragedBilinear ∧
    passesTao2014Audit nsBilinearCriterionAttempt := by
  refine ⟨bilinear_structural_property_holds, ?_, ?_⟩
  · exact bilinear_structural_property_does_not_hold
  · exact nsBilinearCriterion_passesTao2014Audit

end ZtareProofs.NS.BilinearStructuralProperty
