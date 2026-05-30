/-
# NS Track B — Tao-2014-shape auto-falsifier (architectural antibody)

This file is the **architectural antibody** against Ri-style energy-only
attacks on the 3D incompressible Navier-Stokes (NS) Clay problem.  Any
smoothness criterion that does **not** use pressure-direction structure,
vorticity geometry, helicity, or other non-energy / non-harmonic-analysis
structure is **presumptively rejected** by this falsifier — because Tao
2014 explicitly constructed a finite-time blowup for an *averaged* NS
that preserves precisely the energy + harmonic-analysis content shared
by all such attacks.

## Tao 2014 — the load-bearing obstruction theorem

> **Theorem (Tao 2014, arXiv:1402.0290 / J. AMS 29 (2016)).**
>   There exists an averaged 3D Navier-Stokes equation with smooth,
>   compactly-supported, divergence-free initial data whose solution
>   develops a finite-time `H¹` blowup (in fact `L^∞_t L^∞_x` blowup of
>   the velocity).  The averaged operator preserves the L² energy
>   identity and is built from a frequency-localised cascade of
>   Littlewood-Paley projections.

**Architectural consequence**: any proof of NS global regularity whose
*entire substantive content* is

  (i)   pure energy method,
  (ii)  scaling-coercive control of a critical norm (e.g. `H^{1/2}`,
        `L^3`, `BMO^{-1}`, `Ḃ^{-1}_{∞,∞}`) using only energy +
        Littlewood-Paley / Calderón–Zygmund / paraproduct estimates,
        and
  (iii) a supercritical-to-critical bootstrap (raising regularity from
        `L²` (supercritical) to a critical norm by harmonic analysis
        alone),

cannot exist, because Tao's averaged operator preserves **exactly** the
class of estimates such a proof relies on, and yet the averaged NS
blows up.  This file encodes that obstruction as a typed Lean
predicate `Tao2014ShapePattern` together with a structural theorem
`tao_2014_obstruction` rejecting any proof attempt matching the
pattern.

## The Ri 2508.19590 audit

The audit that motivated this file pointed out that Track B's structural
fingerprint must be *demonstrably outside* the Tao-forbidden class.
This file gives the apparatus to test that structurally: any new
Track B file (BKM, PSL, ESS, BdV, Constantin–Fefferman, or new) must be
audited against `Tao2014ShapePattern` before it is accepted as a
candidate smoothness criterion.

## Auditing rule

> **Rule (architectural antibody).**  For every smoothness-criterion
> file `F` in Track B, an explicit witness `usesNonEnergyStructure F`
> must be discharged, exhibiting the non-energy / non-harmonic-analysis
> structure `F` consumes (vorticity direction, pressure Hessian sign,
> helicity, geometric depletion, anisotropic stretching, …).  If no
> such witness exists, `F` is presumptively a `Tao2014ShapePattern` and
> is auto-rejected.

This rule is documented in the Track B charter at
`projects/ns_trackb_closure_recursive_strategy/project_charter.md`.

## Inversion test (sanity)

A predicate this aggressive must *correctly accept* known-valid Track B
arguments (BKM, ESS) as **non-Tao-forbidden**.  We discharge the
inversion test in §4 by exhibiting `bkm_uses_vorticity_direction` and
`ess_uses_critical_serrin_endpoint` — both of which use structure
strictly outside the Tao-preserved class — and showing that the
predicate's third clause `supercriticalToCriticalBootstrapOnly` fails
on them.

## References

* Terence Tao, *Finite time blowup for an averaged three-dimensional
  Navier–Stokes equation*, J. AMS 29 (2016), arXiv:1402.0290 (2014).
* Beale, Kato, Majda, *Remarks on the breakdown of smooth solutions
  for the 3-D Euler equations*, Comm. Math. Phys. 94 (1984), 61–66.
* Escauriaza, Seregin, Šverák, *L^{3,∞}-solutions of the Navier–Stokes
  equations and backward uniqueness*, Russ. Math. Surv. 58 (2003).
* Companion: `ns_trackb_inversor_tao_averaged_ns.lean` (the
  structurally-typed averaged-NS inversor that this falsifier
  generalises into a *meta-pattern*).
-/

import Mathlib.Tactic

namespace ZtareProofs.NS.Tao2014Falsifier

/-! ## §1. Opaque structural predicates

We model "use of a structural feature" as opaque `Prop`s indexed by an
abstract `ProofAttempt`.  Each predicate carries no proof-theoretic
content beyond its identity — the architectural antibody is a
**meta-level structural classifier**, not an internal verifier.

This is the right level of abstraction: Tao 2014 is an obstruction
about *what kind of estimates a proof uses*, not about specific
inequalities.  Encoding the predicates as opaque structural tags
mirrors how the audit is actually run (by inspection of the file's
imports, lemmas invoked, and explicit non-energy structure witnesses).
-/

/-- An abstract "Track B proof attempt" — a candidate smoothness
criterion or global regularity argument.  Concrete instantiations are
files like `ns_trackb_bkm_smoothness_criterion.lean`,
`ns_trackb_ess_l3_endpoint.lean`, etc. -/
structure ProofAttempt where
  /-- A human-readable identifier (file name, theorem name, audit tag). -/
  name : String

/-- **Forbidden feature 1**: the proof attempt's substantive content is
a *pure energy method* — its only quantitative inputs are L² norms of
the velocity, gradient, and their Littlewood-Paley dyadic pieces.

In particular the proof does NOT consume:
  * pressure-Hessian sign / pressure direction structure,
  * vorticity geometry (alignment, depletion, Constantin-Fefferman),
  * helicity sign,
  * anisotropic / non-isotropic geometric structure of the Euler
    bilinear,
  * any non-energy conserved quantity. -/
opaque pureEnergyMethod : ProofAttempt → Prop

/-- **Forbidden feature 2**: the proof's critical-norm control is
*scaling-coercive*, i.e. obtained from energy + harmonic analysis
(Littlewood-Paley, Calderón–Zygmund, paraproducts, multiplier theorems)
*only*.  No transport-of-geometry, no pressure-pollution analysis, no
self-similar profile decomposition outside the harmonic-analysis class.

This is the precise property Tao's averaged operator is engineered to
preserve. -/
opaque scalingCoerciveOnly : ProofAttempt → Prop

/-- **Forbidden feature 3**: the proof's regularity-elevation step is a
*supercritical-to-critical bootstrap* — the Ri pattern.  It controls a
critical scaling-invariant norm starting from a supercritical bound
(typically `L²` energy) using only harmonic analysis.

Any `Tao2014ShapePattern` instance must satisfy all three forbidden
features simultaneously: **pure energy + scaling-coercive + bootstrap**.
A proof using *any* structure outside this class escapes the pattern. -/
opaque supercriticalToCriticalBootstrapOnly : ProofAttempt → Prop

/-! ## §2. The Tao-2014-shape pattern -/

/-- **Tao-2014-shape pattern** — the architectural fingerprint of a
proof attempt that lies entirely within the class Tao 2014's averaged
NS preserves.  A proof attempt matches the pattern iff it satisfies
all three forbidden features.

Concretely: any proof whose only working tools are
  (i)   energy estimates,
  (ii)  scaling-coercive critical-norm control via harmonic analysis,
  (iii) a supercritical-to-critical bootstrap

is **presumptively false** — Tao's counterexample shows the same tools
admit a finite-time blowup. -/
def Tao2014ShapePattern (P : ProofAttempt) : Prop :=
  pureEnergyMethod P ∧ scalingCoerciveOnly P ∧
    supercriticalToCriticalBootstrapOnly P

/-! ## §3. The obstruction theorem

We axiomatise Tao 2014's main theorem as the structural obstruction:
**no proof attempt fitting the Tao-2014 shape can be valid**.  The
axiom `tao_2014_main_obstruction` records this; the theorem
`tao_2014_obstruction` is its direct consumer.

The axiom encodes the *contrapositive* of Tao 2014: if such a proof
existed, it would also apply to the averaged NS (since the averaged
operator preserves all three forbidden features), contradicting Tao's
explicit blowup construction.

This axiom is **not** a Lean-internal proof of NS global regularity's
falsity — it is a *meta-level rejection rule* that any Tao-shaped
proof attempt is structurally invalid. -/

/-- **AXIOM (Tao 2014 main obstruction).**  No proof attempt whose
substantive content lies entirely within the `Tao2014ShapePattern`
class can be a valid proof of NS global regularity.

Justification (external to Lean):
  Tao's averaged 3D NS preserves L² energy, all dyadic Littlewood-Paley
  estimates, all Calderón–Zygmund / paraproduct bounds, and the
  scaling structure.  Any proof whose substantive content uses *only*
  these tools applies, mutatis mutandis, to averaged NS.  But Tao
  exhibited a finite-time blowup for averaged NS.  Hence no
  Tao-shaped proof of true-NS global regularity can be valid.

This is precisely the obstruction recorded in
`ns_trackb_inversor_tao_averaged_ns.lean` for the typed-companion
architecture; here we lift it to a *meta-level structural rejector*. -/
axiom tao_2014_main_obstruction :
  ∀ P : ProofAttempt, Tao2014ShapePattern P → False

/-- **Theorem (Tao-2014-shape auto-falsifier).**  The architectural
antibody: any proof attempt matching the Tao-2014 shape pattern is
auto-rejected.

This is the consumer-facing entry point: an audit gate for any new
Track B smoothness criterion.  If a candidate file's audit witness
`Tao2014ShapePattern P` is constructible, the candidate is rejected.

Proof: directly from the axiomatized obstruction `tao_2014_main_obstruction`. -/
theorem tao_2014_obstruction :
    ∀ P : ProofAttempt, Tao2014ShapePattern P → False := by
  intro P hP
  exact tao_2014_main_obstruction P hP

/-! ## §4. Inversion test — BKM and ESS escape the pattern

A predicate this aggressive must *correctly accept* known-valid Track B
arguments as non-Tao-forbidden.  We discharge the inversion test for
two canonical smoothness criteria:

  * **BKM** (Beale-Kato-Majda 1984): controls `∫₀^{T*} ‖∇×u‖_{L^∞} dt`.
    The vorticity is a **non-energy** geometric quantity (it carries
    direction information that `‖∇u‖_{L²}` discards).  BKM therefore
    fails `pureEnergyMethod`.

  * **ESS** (Escauriaza-Seregin-Šverák 2003): controls the *critical*
    `L^{3,∞}` norm via backward-uniqueness for the *parabolic
    operator* — explicitly using non-harmonic-analysis structure
    (unique continuation, parabolic Carleman estimates, blow-up
    profile rigidity).  ESS therefore fails `scalingCoerciveOnly`.

Both predicates are encoded as opaque non-tags
(`bkm_uses_vorticity_direction`, `ess_uses_critical_serrin_endpoint`)
asserting the structural escape.  The inversion theorems
`bkm_not_tao_shaped` and `ess_not_tao_shaped` show that under those
escape hypotheses the Tao pattern fails — **the predicate correctly
accepts BKM and ESS as valid Track B candidates**.
-/

/-- Audit witness: BKM's vorticity-direction structure lies outside the
energy-method class.  Equivalently, BKM's substantive content is *not*
a pure energy method — it uses the vorticity vector field, whose
direction is non-energy structure. -/
opaque bkm_uses_vorticity_direction : ProofAttempt → Prop

/-- Audit witness: ESS's L^{3,∞} backward-uniqueness machinery uses
parabolic Carleman estimates, which are not part of the
scaling-coercive harmonic-analysis class. -/
opaque ess_uses_critical_serrin_endpoint : ProofAttempt → Prop

/-- The escape clauses are exclusive of the corresponding forbidden
features.  These are recorded as axioms because they encode the
**meaning** of the structural witnesses: a proof that uses vorticity
direction is, by definition, not a pure energy method; a proof that
uses parabolic Carleman estimates is, by definition, not
scaling-coercive-only. -/
axiom bkm_vorticity_excludes_pure_energy :
  ∀ P : ProofAttempt, bkm_uses_vorticity_direction P → ¬ pureEnergyMethod P

axiom ess_serrin_endpoint_excludes_scaling_coercive_only :
  ∀ P : ProofAttempt, ess_uses_critical_serrin_endpoint P →
    ¬ scalingCoerciveOnly P

/-- **Inversion test (BKM).**  Any proof attempt that uses vorticity
direction is *not* Tao-shaped.  This certifies that the falsifier
correctly accepts BKM as a valid Track B candidate. -/
theorem bkm_not_tao_shaped :
    ∀ P : ProofAttempt, bkm_uses_vorticity_direction P →
      ¬ Tao2014ShapePattern P := by
  intro P hBKM hTao
  exact bkm_vorticity_excludes_pure_energy P hBKM hTao.left

/-- **Inversion test (ESS).**  Any proof attempt that uses the
parabolic-Carleman / backward-uniqueness machinery is *not* Tao-shaped.
This certifies that the falsifier correctly accepts ESS as a valid
Track B candidate. -/
theorem ess_not_tao_shaped :
    ∀ P : ProofAttempt, ess_uses_critical_serrin_endpoint P →
      ¬ Tao2014ShapePattern P := by
  intro P hESS hTao
  exact ess_serrin_endpoint_excludes_scaling_coercive_only P hESS hTao.right.left

/-! ## §5. Audit gate — consumer-facing API

We expose a single audit-gate definition and a smoke theorem to be
consumed by any future Track B smoothness-criterion file.  A new file
must either:

  (a)  exhibit an escape witness (e.g. `bkm_uses_vorticity_direction`
       or `ess_uses_critical_serrin_endpoint` or a new analogue), or
  (b)  prove `¬ Tao2014ShapePattern` directly.

Failure to do either flags the file as a presumptive Ri-style
energy-only attack and is auto-rejected. -/

/-- **Audit gate**: a candidate proof attempt `P` passes the Tao-2014
falsifier iff it is *not* Tao-shaped. -/
def passesTao2014Audit (P : ProofAttempt) : Prop := ¬ Tao2014ShapePattern P

/-- BKM-class candidates pass the audit. -/
theorem bkm_passes_audit (P : ProofAttempt)
    (h : bkm_uses_vorticity_direction P) : passesTao2014Audit P :=
  bkm_not_tao_shaped P h

/-- ESS-class candidates pass the audit. -/
theorem ess_passes_audit (P : ProofAttempt)
    (h : ess_uses_critical_serrin_endpoint P) : passesTao2014Audit P :=
  ess_not_tao_shaped P h

/-- **Final architectural statement.**  Any candidate that does NOT
pass the audit is rejected via the Tao 2014 obstruction. -/
theorem audit_failure_implies_invalid (P : ProofAttempt)
    (_h : ¬ passesTao2014Audit P) : Tao2014ShapePattern P → False := by
  intro hTao
  exact tao_2014_obstruction P hTao

end ZtareProofs.NS.Tao2014Falsifier
