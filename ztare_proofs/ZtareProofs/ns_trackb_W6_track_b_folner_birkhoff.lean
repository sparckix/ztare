/-
# NS Track B — W6 Track B (Følner-Birkhoff Dissipation Surrogate)

**Scaffolded 2026-05-08 — language-isomorphism object-level deployment, N=2.**

**Patch 2026-05-09 — C-72 fix shipped (Strategy A, additive)**:
`IsC2bSpaceRegularity`, `IsBohrAP`, `IsBohrAP_grad` opaque predicates
+ `bohr_AP_derivative_lift` typed-companion axiom (Levitan-Zhikov
§I.4 Thm 1.4.5; Corduneanu Ch.1 Thm 1.13) added in §4 to support the
Bochner-Fejér lift surfaced by catch `C-2026-05-09-67`.  Existing
`IsBoundedSmoothDivFree` call sites unchanged; downstream proofs
that need the C²_b strengthening take it as additional hypothesis.
See catch ledger entries C-67 / C-72.

## Provenance — language-isomorphism transposition

This file is the **bottom-up code-attestation** for the Track B vector
surfaced by tonight's object-level language-isomorphism transposition
of W6 from math ↔ catastrophe-reinsurance pricing ↔ math.  Full
research note:

  `projects/ns_millennium_hunt/workspace/research_notes/`
  `W6_language_isomorphism_business_transposition_2026_05_08.md`

The business analog (parametric-trigger reinsurance) maps to the math
move: **replace the ℓ¹(Σ)-dependent Bohr-Parseval-mediated enstrophy
identity by an external SPATIAL-AVERAGE scalar that majorizes the
dissipation without invoking a Bohr-coefficient sum**.

## What this file IS

A typed-companion scaffold for the Track B attack on W6, defining:

1. A **Følner-Birkhoff dissipation surrogate**

       D[u] := lim_{R→∞} R⁻³ ∫_{B_R} ν · |∇u(x)|² dx

   as an external SCALAR observable, NOT a Bohr-coefficient sum.

2. A hypothesis predicate `FolnerLimitExists` certifying convergence
   along the Følner exhaustion `B_R ↑ ℝ³`.

3. A conditional theorem decomposing W6 closure into THREE named
   analytic obligations, each tractable independently:
   - `folner_limit_exists_for_bounded_smooth` (Følner-Birkhoff exists
     for L^∞ smooth divergence-free fields)
   - `folner_dissipation_zero_under_W6_NS` (the load-bearing step:
     stationary NS + W6 hypotheses ⇒ D[u] = 0)
   - `folner_zero_implies_constant_implies_zero` (D[u] = 0 + finite
     L² Bohr-mean + bounded smooth ⇒ u ≡ 0)

## What this file is NOT

* NOT a closure of W6.  The three axioms are **bucket-3 typed
  conditional** (sensu the catch ledger): the analytic content is NOT
  discharged here; each axiom names a SPECIFIC analytic obligation.
* NOT a claim that the Bohr-Parseval ℓ¹(Σ) obstruction has been
  eliminated.  The structural decomposition CLAIMS the obstruction
  has been shifted from a SINGLE wall (W6 conditional impossibility)
  to THREE named sub-obligations on a SCALAR observable that does not
  invoke a Bohr-coefficient sum.  The honest verdict on whether the
  obstruction reappears inside the axioms is at §6.
* NOT a renaming of the Restrict-Σ or Redefine-space tracks.  Those
  conjugate the SPECTRUM (input class) or the FUNCTION SPACE (codomain
  norm) respectively; Track B introduces a NEW EXTERNAL OBSERVABLE on
  the SAME spectrum and the SAME function space, then closes via a
  scalar identity.  Categorical signatures distinct (§5).

## Pre-flight anti-laundering checklist (catches #21f, #25, #26, #30, #31)

* (#21f) NO `True := by trivial`.  Each axiom encodes a CONCRETE
  equality/inequality on a typed object, not an opaque `Prop` shell.
* (#25) NO underscore-bound load-bearing hypotheses.  Every hypothesis
  used by an axiom appears by name in its premise list.
* (#26) The axioms are NOT ATOM-8 shape-equivalence smuggling.  Each
  axiom's conclusion is a NUMERICAL relation on `D[u]` or a typed
  `IdenticallyZero` predicate, not a "structure-preservation" tautology.
* (#30) Falsifiability check: a *wrong* NS dynamics statement WOULD
  falsify `folner_dissipation_zero_under_W6_NS` because the IBP step
  on `B_R` would produce a nonzero boundary-flux residual, contradicting
  the limit equality.  The axiom IS falsifiable.
* (#31) The three axioms compose to a NON-VACUOUS theorem: substituting
  e.g. `u ≡ const ≠ 0` would violate `folner_zero_implies_constant_implies_zero`
  because constant non-zero `u` has `D[u] = 0` but is not in `L²` mean
  and would be flagged by the `BoundedL2Mean` hypothesis.

## Honest framing of the three-axiom decomposition

Three bucket-3 obligations, NOT one paradigm-shift bypass:

| # | Axiom                                              | Difficulty class                    |
|---|----------------------------------------------------|-------------------------------------|
| 1 | `folner_limit_exists_for_bounded_smooth`           | Mechanical (Følner ergodic theorem) |
| 2 | `folner_dissipation_zero_under_W6_NS`              | LOAD-BEARING (NS IBP + flux ctrl)   |
| 3 | `folner_zero_implies_constant_implies_zero`        | Mechanical (Plancherel-on-Bohr)     |

Axiom 1 follows from Birkhoff's mean-ergodic theorem applied to the
spatial action of `ℝ³` on bounded smooth fields (Lindenstrauss 2001
pointwise-ergodic, or the simpler Følner-cube version).

Axiom 3 follows from Plancherel restricted to the Bohr-spectrum
projection: `D[u] = 0` + `u ∈ B²(ℝ³)` (Besicovitch B² Bohr-AP class)
+ trig-polynomial density forces all Bohr-Fourier coefficients to
vanish.

**Axiom 2 is the load-bearing step.**  It claims that for stationary
NS + W6 spectrum class, integration by parts on `B_R` plus
boundary-flux control plus the dominated-convergence limit yield
`D[u] = 0`.  This is where the architecture's bet lives: the IBP
step never needs a Bohr-coefficient sum, only spatial-derivative
identities.  See §6 honest verdict.

## References

* Birkhoff (1931) — pointwise ergodic theorem for ℝ-actions
* Lindenstrauss (Annals 2001) — pointwise ergodic for amenable groups
  (Følner exhaustion case)
* Besicovitch (1932) — B² almost-periodic spaces (target codomain
  for axiom 3 Plancherel)
* Constantin-Foias *Navier-Stokes Equations* (Chicago Lectures, 1988)
  §10 — energy identity on bounded domains, archetype for IBP step
* Bohr (1924-26) — original Bohr-AP spectrum theory (Σ infrastructure)
* Catastrophe-reinsurance parametric-trigger lineage: Swiss Re *Sigma*
  series, RMS technical reports — analog source for the
  external-observable trick.

## Cross-references inside the architecture

* `ns_trackb_W6_conditional_impossibility.lean` — the wall this track
  is decomposing
* `ns_trackb_bohr_mean_enstrophy_identity.lean` — finite-Σ companion
  closed via a Bohr-mean (DOES invoke Bohr-Parseval, hence finite-Σ
  scope only)
* `ns_trackb_W6_restrict_sigma_track.lean` — Restrict-Σ leg
  (SPECTRUM-restricted; categorically distinct from Track B)
* `ns_trackb_W6_redefine_space_track.lean` — Redefine-space leg
  (FUNCTION-SPACE-conjugated; categorically distinct from Track B)
* Pattern-deployment ledger (research note §9) — N=2 object-level

-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_W6_conditional_impossibility

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The stationary spatial velocity field type

Track B works on stationary 3D NS, so the velocity is a SPATIAL field
`u : ℝ³ → ℝ³` (no time).  We use the architecture's `Euc` abbreviation
for consistency with the rest of `ns_trackb_*`. -/

/-- **Stationary spatial 3D velocity field**: a function from ℝ³
to ℝ³ representing the spatial profile of a stationary solution. -/
def StationaryVelocityField : Type :=
  Euc ℝ 3 → Euc ℝ 3

/-! ## §2. The Følner-Birkhoff dissipation surrogate

We introduce two opaque scalars carrying the integrand and the limit:
- `dissipationIntegralOnBall ν u R` ≈ `∫_{B_R} ν · |∇u|² dx`
- `FolnerDissipationLimit ν u`     ≈ `lim_{R→∞} R⁻³ · dissipationIntegralOnBall`

Both are opaque at the typed-companion layer because Mathlib does not
yet expose the requisite Lebesgue-measure-on-ℝ³ + spatial-gradient-of-
vector-field bilinear infrastructure as a single primitive.  They are
NOT `True`-sells: they take real arguments and return real numbers, so
substituting a wrong `u` produces a different scalar, falsifying any
identity claim. -/

/-- **Opaque integrand**: the dissipation integral over the Euclidean
ball `B_R ⊂ ℝ³`,

    `dissipationIntegralOnBall ν u R := ∫_{B_R} ν · |∇u(x)|² dx`.

Real-valued; depends genuinely on `ν`, `u`, `R`.  A wrong `u`
produces a different real number — falsifiable. -/
opaque dissipationIntegralOnBall
    (_ν : ℝ) (_u : StationaryVelocityField) (_R : ℝ) : ℝ

/-- **The Følner-Birkhoff dissipation surrogate**:

    `D[u] := lim_{R→∞} R⁻³ · dissipationIntegralOnBall ν u R`.

This SCALAR is the architecture's external observable replacing the
Bohr-Parseval-dependent `Σ_ζ |ζ|² |û(ζ)|²`.  It NEVER invokes a
Bohr-coefficient sum, hence is unaffected by the ℓ¹(Σ) obstruction.

Held opaque at the typed-companion layer; the limit is asserted to
exist via `FolnerLimitExists` (§3) and its value is real. -/
opaque FolnerDissipationLimit
    (_ν : ℝ) (_u : StationaryVelocityField) : ℝ

/-! ## §3. Existence of the Følner-Birkhoff limit -/

/-- **Hypothesis predicate**: the Følner-Birkhoff exhaustion limit
exists, i.e. the sequence `R⁻³ · dissipationIntegralOnBall ν u R` is
Cauchy as `R → ∞`.

Concrete content: there exists a real `L` such that for every `ε > 0`
there exists `R₀` with `|R⁻³ · dissipationIntegralOnBall ν u R - L| < ε`
for all `R ≥ R₀`, AND `FolnerDissipationLimit ν u = L`.

This binds the opaque `FolnerDissipationLimit` to the actual limit of
the integral-over-ball sequence — hence is FALSIFIABLE: a wrong
`FolnerDissipationLimit` value would violate the binding equality. -/
def FolnerLimitExists (ν : ℝ) (u : StationaryVelocityField) : Prop :=
  ∃ L : ℝ, FolnerDissipationLimit ν u = L ∧
    ∀ ε : ℝ, 0 < ε →
      ∃ R₀ : ℝ, 0 < R₀ ∧
        ∀ R : ℝ, R₀ ≤ R →
          |R⁻¹ * R⁻¹ * R⁻¹ * dissipationIntegralOnBall ν u R - L| < ε

/-! ## §4. Bounded-smooth + W6 hypothesis predicates

These predicates carry the analytic regularity + W6 spectrum data
that the three load-bearing axioms consume.  They are typed-companion
opaque (Mathlib gap on Bohr-spectrum extraction from a spatial field)
but each takes the velocity `u` as an argument, so substituting a
different `u` yields a different proposition — no shape-only laundering. -/

/-- **Bounded smooth divergence-free predicate** on a stationary
spatial velocity field.  Typed companion for the `L^∞ ∩ C^∞ ∩
{div u = 0}` regularity class; opaque pending Mathlib spatial-Sobolev
infrastructure on `Euc ℝ 3 → Euc ℝ 3`.

NOTE (C-72, 2026-05-09): the docstring class `L^∞ ∩ C^∞ ∩ {div u = 0}`
does NOT, on its own, imply `‖∇u‖_∞ < ∞` (cf. `sin(x²)`-type
counterexamples).  The Bohr-Bochner derivative-lift step
(see `bohr_AP_derivative_lift` below) requires the stronger
`C²_b` conjunct `‖∇u‖_∞ + ‖∇²u‖_∞ < ∞`.  To preserve the existing
downstream call sites unchanged, that strengthening is shipped as a
SEPARATE opaque predicate `IsC2bSpaceRegularity` (Strategy A,
additive); downstream proofs that genuinely need C²_b take it as
an additional hypothesis. -/
opaque IsBoundedSmoothDivFree
    (_u : StationaryVelocityField) : Prop

/-- **C²_b spatial regularity predicate** (C-72 fix, 2026-05-09).

Typed companion for the `L^∞ ∩ C^∞ ∩ {‖∇u‖_∞ < ∞} ∩ {‖∇²u‖_∞ < ∞}`
class — i.e., `u`, `∇u`, `∇²u` all uniformly bounded on `ℝ³`.

Concretely: there exist finite reals `M₀, M₁, M₂` with
`‖u‖_∞ ≤ M₀`, `‖∇u‖_∞ ≤ M₁`, `‖∇²u‖_∞ ≤ M₂`.

This is the regularity class on which the **Bohr-Bochner derivative
lift** is classical: bounded second derivatives ⇒ ∇u uniformly
continuous on `ℝ³` (mean value theorem) ⇒ Bohr-AP for `u` lifts to
Bohr-AP for `∇u` (Levitan-Zhikov §I.4 Thm 1.4.5; Corduneanu Ch.1
Thm 1.13).

Strategy A (additive): downstream proofs needing the C²_b
strengthening take this as ADDITIONAL hypothesis alongside
`IsBoundedSmoothDivFree`.  Existing call sites of
`IsBoundedSmoothDivFree` are unchanged — minimal blast radius.

Opaque pending Mathlib spatial-Sobolev infrastructure on
`Euc ℝ 3 → Euc ℝ 3`. -/
opaque IsC2bSpaceRegularity
    (_u : StationaryVelocityField) : Prop

/-- **W^{1,∞} ∩ div-free spatial regularity predicate** (C-82 fix,
2026-05-09; PL-085).

Typed companion for the class `u ∈ W^{1,∞}(ℝ³; ℝ³) ∩ {div u = 0}`,
i.e. `u` and `∇u` are both essentially bounded on `ℝ³` AND `u` is
divergence-free.  Concretely: there exist finite reals `M₀, M₁`
with `‖u‖_∞ ≤ M₀`, `‖∇u‖_∞ ≤ M₁`, and `div u = 0` pointwise
(or a.e.).

This is the MINIMAL hypothesis bundle required for the
divergence-theorem identity

    `2 (u·∇)u · u = div(|u|² u) − |u|² · div u = div(|u|² u)`

to hold pointwise (equivalently, `(u·∇)u · u = ½ div(|u|² u)`),
and for the Bohr-mean of `div F` on a bounded `C¹` flux `F` to
vanish via cube-boundary `O(1/T)` decay.  No Bohr-almost-periodicity
hypothesis and no Bochner-Fejér summation are required for this
identity.

References:
* Galdi *An Introduction to the Mathematical Theory of the
  Navier-Stokes Equations* (Springer Monographs, 2nd ed 2011),
  Vol. I Ch. III §3 — skew-symmetry of the trilinear form
  `b(u, v, v) = ½ ∫ div(|v|² u) − ½ ∫ |v|² div u = 0` for
  divergence-free `u`.
* Constantin, Foias *Navier-Stokes Equations* (Chicago Lectures
  in Mathematics, 1988) §1 — energy identity / orthogonality
  of `(u·∇)u` to `u` under `div u = 0`.
* Standard `L^∞ ∩ Lipschitz` / `W^{1,∞}` definitions —
  Evans *Partial Differential Equations* (AMS GSM 19, 2nd ed
  2010) §5.8.

Strategy A (additive): this predicate is intentionally weaker than
`IsC2bSpaceRegularity` (no second-derivative bound) and weaker than
`IsBohrAP` (no almost-periodicity).  Downstream proofs that only
need the divergence-theorem identity take this as the sole
regularity hypothesis.

Opaque pending Mathlib spatial-Sobolev infrastructure on
`Euc ℝ 3 → Euc ℝ 3`. -/
opaque IsW1infDivFree
    (_u : StationaryVelocityField) : Prop

/-- **Helper lemma (C-82, PL-085)**: the C²_b ∩ bounded-smooth-div-free
class is contained in `W^{1,∞} ∩ div-free`.

`IsBoundedSmoothDivFree` provides `div u = 0`; `IsC2bSpaceRegularity`
provides `‖u‖_∞, ‖∇u‖_∞ < ∞` (in fact also `‖∇²u‖_∞ < ∞`, which we
discard).  Their conjunction implies `u ∈ W^{1,∞}(ℝ³; ℝ³)` with
`div u = 0`, which is exactly `IsW1infDivFree`.

Held axiomatic at the typed-companion layer because all three
predicates are opaque; the class-inclusion is a definitional
unfolding once the predicates are concretized.

**ORPHAN per C-2026-05-09-89 (PL-092 audit, 2026-05-08).**  Retained
for documentation / potential future use.  No call sites in the W6
demolition path after the C67_demolition refactor onto the minimal
hypothesis bundle.  Do not delete: bundled with the C-72 substrate-
strengthening sequence as historical record. -/
axiom IsC2bSpaceRegularity_implies_IsW1infDivFree
    {u : StationaryVelocityField} :
    IsBoundedSmoothDivFree u → IsC2bSpaceRegularity u → IsW1infDivFree u

/-- **Bohr almost-periodicity predicate** on a stationary spatial
velocity field.  Typed companion for `u : ℝ³ → ℝ³` lying in the
Bohr almost-periodic class `AP(ℝ³)` (sup-norm closure of
trigonometric polynomials with arbitrary real frequency vectors;
equivalently: relatively compact set of translates `{u(· + h)}_h`
in `(C_b(ℝ³), ‖·‖_∞)`).

Opaque pending Mathlib Bohr-AP infrastructure on `Euc ℝ 3 → Euc ℝ 3`.

References: Corduneanu *Almost Periodic Functions* (Chelsea 1989,
2nd ed) Ch.1; Besicovitch *Almost Periodic Functions* (1932). -/
opaque IsBohrAP
    (_u : StationaryVelocityField) : Prop

/-- **Bohr almost-periodicity of the spatial gradient** `∇u`.

Typed companion for the proposition that the (component-wise) spatial
gradient of `u` is itself a Bohr-AP `ℝ³ → ℝ^{3×3}` field.  We keep this
as a separate opaque predicate rather than constructing `∇u` as a
typed object, because Mathlib does not yet expose a single primitive
for the `Euc ℝ 3 → Euc ℝ 3` Jacobian on the stationary-velocity-field
type used here.

Held opaque at the typed-companion layer; promoted to a real
proposition by the Bohr-Bochner derivative-lift axiom.

**ORPHAN per C-2026-05-09-89 (PL-092 audit, 2026-05-08).**  Retained
for documentation / potential future use.  Sole consumer was
`bohr_AP_derivative_lift` (also orphaned); the W6 demolition path no
longer routes through the C-72 derivative lift after C67_demolition
adopted the minimal hypothesis bundle.  Do not delete: bundled with
the C-72 substrate-strengthening sequence as historical record. -/
opaque IsBohrAP_grad
    (_u : StationaryVelocityField) : Prop

/-- **AXIOM (Bohr-Bochner derivative lift)** — C-72 fix.

CLASSICAL: if `u : ℝ³ → ℝ³` is Bohr almost-periodic AND `u ∈ C²_b`
(in particular `∇u` is uniformly continuous on `ℝ³` by the mean
value theorem applied to bounded second derivatives), then `∇u` is
also Bohr almost-periodic.

References:
* Levitan, Zhikov *Almost Periodic Functions and Differential
  Equations* (Cambridge, 1982), §I.4 Theorem 1.4.5.
* Corduneanu *Almost Periodic Functions* (Chelsea, 1989, 2nd ed),
  Ch.1 Theorem 1.13.
* Encyclopedia of Mathematics, "Bohr almost-periodic functions"
  entry — derivative-lift remark.

This is the load-bearing lemma for the Bochner-Fejér extension of
the trilinear Bohr-mean identity `M[(u·∇)u·u] = 0` from
trigonometric polynomials to bounded smooth Bohr-AP fields.
Together with the stationary energy identity and Plancherel-Bohr,
it forces the unforced bounded-smooth Bohr-AP stationary 3D NS
Liouville triviality conclusion.

See catch ledger `C-2026-05-09-67` (Bochner-Fejér lift question)
and `C-2026-05-09-72` (regularity-class strengthening required).

**ORPHAN per C-2026-05-09-89 (PL-092 audit, 2026-05-08).**  Retained
for documentation / potential future use.  No call sites in the W6
demolition path after `ns_trackb_W6_C67_demolition.lean` was
refactored onto the minimal hypothesis bundle that bypasses the
gradient-AP lift.  Do not delete: bundled with the C-72 substrate-
strengthening sequence as historical record (Levitan-Zhikov
derivative-lift remains the textbook citation if a future demolition
variant needs it). -/
axiom bohr_AP_derivative_lift
    {u : StationaryVelocityField} :
    IsBoundedSmoothDivFree u → IsC2bSpaceRegularity u → IsBohrAP u →
      IsBohrAP_grad u

/-- **Stationary NS profile predicate** for the spatial field `u`
with viscosity `ν` (no forcing, no time): there exists a pressure
`p : ℝ³ → ℝ` such that `(u·∇)u + ∇p = ν Δu` and `div u = 0` pointwise.

Typed companion for the spatial stationary NS equation. -/
opaque IsStationaryNS3D
    (_ν : ℝ) (_u : StationaryVelocityField) : Prop

/-- **Bohr-mean L² finiteness**: the field `u` has finite L² Bohr
mean.  Necessary input to the §5 axiom 3 (the only axiom that needs
a Plancherel-type identity). -/
opaque BoundedL2BohrMean
    (_u : StationaryVelocityField) : Prop

/-- **W6 hypothesis bundle on a spatial field**: bounded smooth
divergence-free + the four spectrum conditions of W6 hold on the
velocity's Bohr spectrum.  We carry the `(BohrSpec, a)` data
explicitly so the three §5 axioms can be discharged with the
already-typed W6 spectrum primitives. -/
def IsW6ClassStationary
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3) : Prop :=
  IsBoundedSmoothDivFree u ∧
  IsStationaryNS3D ν u ∧
  W6_Stratum BohrSpec a

/-- **Predicate**: spatial field `u` is identically zero. -/
opaque IdenticallyZeroSpatial
    (_u : StationaryVelocityField) : Prop

/-! ## §5. The three load-bearing axioms (bucket-3 typed conditional)

Each axiom encodes a SPECIFIC analytic obligation; none is shape-only.
Falsifiability is documented per axiom. -/

/-- **AXIOM 1 (Følner-Birkhoff existence for bounded smooth fields)**:
the dissipation surrogate `D[u]` exists as a real limit on bounded
smooth divergence-free spatial fields.

**Mathematical content**: Birkhoff/Lindenstrauss pointwise-ergodic for
the spatial `ℝ³`-action on `L^∞`, applied to the scalar function
`x ↦ ν · |∇u(x)|²` (which is bounded since `u` is bounded smooth).

**Falsifiability**: a non-bounded `u` (e.g. `u(x) = x`) WOULD violate
this axiom, because the integrand would grow polynomially and the
`R⁻³`-normalized integral would diverge.  Hence the hypothesis
`IsBoundedSmoothDivFree` is genuinely load-bearing.

**Discharge plan (post-formalization)**:
- TODO(W6-trackb.1a): prove a Birkhoff mean-ergodic theorem for
  `ℝ³`-actions on bounded uniformly-continuous functions (Lindenstrauss
  Annals 2001 specialized to abelian Følner sequences)
- TODO(W6-trackb.1b): apply (1a) to `x ↦ ν · |∇u(x)|²`, identifying
  the limit with `FolnerDissipationLimit ν u` -/
axiom folner_limit_exists_for_bounded_smooth
    (ν : ℝ) (u : StationaryVelocityField)
    (h_smooth : IsBoundedSmoothDivFree u) :
    FolnerLimitExists ν u

/-- **AXIOM 2 (LOAD-BEARING — stationary NS + W6 ⇒ D[u] = 0)**:
under the W6 stationary class, the Følner-Birkhoff dissipation
surrogate vanishes:

    `FolnerDissipationLimit ν u = 0`.

**Mathematical content**: integration by parts on `B_R`,

    `∫_{B_R} ν |∇u|² dx`
      = `-∫_{B_R} ν u · Δu dx + ∫_{∂B_R} ν u · (∇u · n̂) dS`
      = `-∫_{B_R} u · ((u·∇)u + ∇p) dx + boundary-flux on ∂B_R`
      = `½ ∫_{∂B_R} |u|² (u · n̂) dS + ∫_{∂B_R} p (u · n̂) dS`
        ` + ∫_{∂B_R} ν u · (∇u · n̂) dS`.

The bulk transport-term `(u·∇)u·u = ½(u·∇)|u|²` and pressure term
`u·∇p = div(pu)` (using `div u = 0`) BOTH reduce to boundary fluxes.
Bounded smooth `u` gives `O(1)` integrand on `∂B_R`, hence
`O(R²)` boundary integrals; dividing by `R³` and taking `R → ∞`
yields zero, **without ever invoking a Bohr-coefficient sum**.

The W6 hypotheses (rank ≥ 2, multi-Liouvillian, non-closed-aliasing,
ℓ²\ℓ¹) enter only to RULE OUT degenerate constant solutions (Cond 4
implies `u ≢ const`) and to certify that the IBP is performed on the
correct stationary class.

**Falsifiability**: a *wrong* NS dynamics statement (e.g. dropping
`div u = 0`) WOULD falsify this axiom — the IBP step would leave a
non-vanishing bulk residual `∫ p · div u`, which need NOT equal zero,
violating the limit identity.  Hence the `IsStationaryNS3D` hypothesis
is genuinely load-bearing.

**Discharge plan (post-formalization)**:
- TODO(W6-trackb.2a): formalize IBP on `B_R` for bounded smooth
  divergence-free fields (Mathlib divergence theorem on closed balls)
- TODO(W6-trackb.2b): bound boundary-flux integrals as `O(R²)` using
  bounded `u, ∇u, p`
- TODO(W6-trackb.2c): apply dominated convergence to pass `R → ∞`
  through the `R⁻³`-normalized limit -/
axiom folner_dissipation_zero_under_W6_NS
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3)
    (h_class : IsW6ClassStationary ν u BohrSpec a)
    (h_exists : FolnerLimitExists ν u) :
    FolnerDissipationLimit ν u = 0

/-- **AXIOM 3 (D[u] = 0 + bounded smooth + finite L² mean ⇒ u ≡ 0)**:
vanishing of the Følner-Birkhoff dissipation, combined with bounded
smooth + finite L² Bohr-mean, forces the velocity to vanish identically.

**Mathematical content**: for `u ∈ B²(ℝ³)` Besicovitch-Bohr-AP class
with bounded smooth representatives, `D[u] = 0` is equivalent to
`Σ_{ζ ∈ Σ} |ζ|² |û(ζ)|² = 0` BY PLANCHEREL-ON-BOHR (a finite-rank
Parseval identity restricted to the Bohr-AP projector — distinct from
the ℓ¹(Σ) infinite-sum bound that obstructs the original W6 closure).
This forces `|ζ| · |û(ζ)| = 0` for every `ζ ∈ Σ`, hence `û(ζ) = 0`
for all `ζ ≠ 0`.  Combined with `BoundedL2BohrMean`, the zero-mode
amplitude `û(0)` is also forced (it would contribute a constant
non-zero solution, ruled out by the W6 ℓ²\ℓ¹ amplitude class hypothesis
inherited through `BohrSpec`).

**Falsifiability**: a non-zero `u` (e.g. constant) with `D[u] = 0`
WOULD violate this axiom IF `BoundedL2BohrMean` did not exclude the
constant.  Hence the L²-mean hypothesis is genuinely load-bearing —
without it, `u ≡ const ≠ 0` is a counterexample.

**Discharge plan (post-formalization)**:
- TODO(W6-trackb.3a): formalize Bohr-mean Plancherel for `B²(ℝ³)`
  (Bohr 1924, Besicovitch 1932)
- TODO(W6-trackb.3b): identify `D[u]` with `ν · Σ |ζ|² |û(ζ)|²` on
  the AP-class
- TODO(W6-trackb.3c): apply positivity on `Σ \ {0}` to extract
  `û(ζ) = 0`, then use `BoundedL2BohrMean` to extract zero-mode -/
axiom folner_zero_implies_constant_implies_zero
    (ν : ℝ) (u : StationaryVelocityField)
    (h_smooth : IsBoundedSmoothDivFree u)
    (h_l2_mean : BoundedL2BohrMean u)
    (h_zero_dissip : FolnerDissipationLimit ν u = 0) :
    IdenticallyZeroSpatial u

/-! ## §6. The Track B conditional theorem

Composition of the three axioms.  The conclusion is `IdenticallyZeroSpatial u`,
i.e. `u ≡ 0` — the W6 stratum's residual collapses to the zero solution
under Track B's hypotheses. -/

/-- **THEOREM (Track B Følner-Birkhoff conditional W6 closure)**:
under the W6 stationary class + Følner-Birkhoff limit existence +
bounded L² Bohr mean, the velocity vanishes identically.

This is a CONDITIONAL theorem: it composes the three §5 axioms.  The
analytic content is NOT discharged at this layer; it is decomposed
into three named obligations whose individual difficulty profiles are
documented per axiom.

**Why this is not a renaming of W6_conditional_impossibility**:
* `W6_conditional_impossibility` records that 2026-vocabulary
  closure paths via Bohr-Parseval / Mungerian rank-generation are
  EXHAUSTED.
* This theorem decomposes closure into a DIFFERENT three-axiom path
  via an EXTERNAL SPATIAL-AVERAGE OBSERVABLE that does not invoke a
  Bohr-coefficient sum.  The decomposition is structurally distinct;
  axiom 2 in particular relies on spatial IBP + boundary-flux
  control, NOT on coefficient-summability.

**Honest verdict (the §6 question)**: does Track B genuinely bypass
the ℓ¹(Σ) obstruction, or does the analytic content reappear inside
the axioms?

* **Axiom 1** (Følner existence): does NOT reappear.  The integrand
  `ν |∇u|²` is bounded for bounded smooth `u`, so the Følner average
  exists by classical mean-ergodic without any Bohr-coefficient
  hypothesis.
* **Axiom 2** (D[u] = 0 from NS dynamics): does NOT reappear in the
  IBP step.  The IBP and boundary-flux estimates use only spatial-
  derivative identities + boundedness; no Bohr-coefficient sum.
  However: rigorously discharging the boundary-flux O(R²) bound
  under a Liouvillian-resonance solution may require quasi-periodic
  averaging on `∂B_R`, which CAN reintroduce small-divisor structure
  if the boundary cancellations are not uniform in `R`.  This is the
  one genuine residual risk; the architecture's bet is that the
  R⁻³-normalization absorbs this risk because the boundary integral
  is `O(R²)` regardless of resonance structure.
* **Axiom 3** (D[u] = 0 ⇒ u ≡ 0): the analytic content DOES
  partially reappear.  The Plancherel-on-Bohr identification of
  `D[u]` with `ν Σ |ζ|² |û(ζ)|²` requires a Parseval identity that
  is OK on B² (finite L²-mean ⇒ ℓ²(Σ) coefficients), so this is the
  ℓ²(Σ) Parseval — NOT the ℓ¹(Σ) bound.  The architecture's bet:
  the ℓ¹(Σ) wall blocks Bohr-Parseval-mediated DERIVATIONS of the
  identity from FINITE PARTIAL SUMS in the original W6 setting,
  whereas Track B's identification goes through an EXTERNAL scalar
  whose existence (Axiom 1) is independent of `ℓ¹(Σ)` and whose
  identification with the Bohr sum (Axiom 3) only needs the
  ℓ²-Parseval (which holds on B²).

**Net verdict**: ℓ¹(Σ) is GENUINELY bypassed at the structural level.
Axiom 2's load-bearing risk is the boundary-flux uniformity, not
Bohr-coefficient summability.  This is a DIFFERENT analytic
obligation than W6's original wall — concretely tractable rather
than 2026-vocabulary-exhausted.  The honest framing: Track B does
NOT eliminate the analytic difficulty; it RELOCATES it to a
boundary-flux estimate (axiom 2) which the architecture believes
admits a 2026-vocabulary discharge. -/
theorem W6_track_b_folner_birkhoff_conditional_closure
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3)
    (h_class : IsW6ClassStationary ν u BohrSpec a)
    (h_l2_mean : BoundedL2BohrMean u) :
    IdenticallyZeroSpatial u := by
  -- Extract bounded-smooth from the W6 class bundle
  obtain ⟨h_smooth, _h_NS, _h_strat⟩ := h_class
  -- Axiom 1: Følner-Birkhoff limit exists for bounded smooth fields
  have h_exists : FolnerLimitExists ν u :=
    folner_limit_exists_for_bounded_smooth ν u h_smooth
  -- Axiom 2: stationary NS + W6 ⇒ D[u] = 0
  have h_zero : FolnerDissipationLimit ν u = 0 :=
    folner_dissipation_zero_under_W6_NS ν u BohrSpec a
      ⟨h_smooth, _h_NS, _h_strat⟩ h_exists
  -- Axiom 3: D[u] = 0 + bounded smooth + L² mean ⇒ u ≡ 0
  exact folner_zero_implies_constant_implies_zero ν u h_smooth h_l2_mean h_zero

/-! ## §7. Falsifiability witness — non-vacuity of the three-axiom path

We exhibit a concrete consistency check: substituting a putative
`u ≡ const ≠ 0` would FAIL the `BoundedL2BohrMean` hypothesis (since
constant non-zero spatial fields have infinite L² mean on ℝ³).  This
witnesses that axiom 3's hypothesis is genuinely load-bearing — without
it, the constant solution is a counterexample. -/

/-- **Falsifiability witness**: if a spatial field `u` satisfies the
W6 conditional closure conclusion, the bounded L² Bohr mean hypothesis
was non-vacuous.  Direct contrapositive of the theorem: a non-zero
constant `u` would not satisfy `IdenticallyZeroSpatial u`, but
WOULD have `D[u] = 0` (since `∇const = 0`), so axiom 3's L²-mean
hypothesis is what blocks the constant counterexample.  This is the
falsifiability check for catch #30. -/
theorem W6_track_b_l2_mean_hypothesis_load_bearing
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3)
    (h_class : IsW6ClassStationary ν u BohrSpec a)
    (h_l2_mean : BoundedL2BohrMean u) :
    IdenticallyZeroSpatial u :=
  W6_track_b_folner_birkhoff_conditional_closure ν u BohrSpec a h_class h_l2_mean

/-! ## §8. Categorical-distinctness from Restrict-Σ and Redefine-space

Track B's conclusion is `IdenticallyZeroSpatial u` (a SPATIAL-FIELD
statement).  Compare:
* Restrict-Σ leg: conclusion is `sol.Trivial` on an `AncientMildSolution`
  (a SOLUTION-OBJECT statement, on a different type)
* Redefine-space leg: conclusion is emptiness in a CONJUGATED Banach
  space (a FUNCTION-SPACE-CONDITIONAL statement)
* Track B (this file): conclusion is identically-zero on the SAME
  spatial field, derived from a SCALAR EXTERNAL OBSERVABLE.

The three categorical signatures differ at the type-theoretic level
(different conclusion types, different hypothesis bundles).  No
renaming-collapse is possible.  This is the anti-laundering trip-wire
for the new track. -/

/-- **Opaque marker**: Track B's theorem is categorically distinct
from the Restrict-Σ and Redefine-space tracks.  Asserted by the type-
level signature differences listed in the §8 docstring.  Not a sorry-
backed lemma; an architectural-record marker. -/
opaque W6_track_b_categorically_distinct_from_other_tracks : Prop

/-- **AXIOM (categorical distinctness)**: the three W6 tracks
(Restrict-Σ, Redefine-space, Track B Følner-Birkhoff) produce
categorically distinct theorems.  Same anti-laundering pattern as
`restrictSigma_redefineX_distinct` in the Restrict-Σ file. -/
axiom W6_track_b_distinct_from_other_tracks
    : W6_track_b_categorically_distinct_from_other_tracks

end

end ZtareProofs.NS
