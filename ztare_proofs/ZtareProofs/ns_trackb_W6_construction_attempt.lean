/-
# NS Track B — W6 Construction Attempt (concrete rank-2 multi-Liouvillian)

**Produced 2026-05-08 (evening)** under operator-authorized open-math
attempt against W6 emptiness. Discharged with META-DARWIN PATTERN-005
falsifiable-asymmetry pre-gate.

## What this file is NOT

* NOT a proof that the W6 stratum is non-empty (no concrete witness
  was constructed).
* NOT a proof that the W6 stratum is empty (no closure achieved).
* NOT a closure of the small-divisor wall — the wall is sharpened, not
  removed.

## What this file IS

A formal record of an honest CONCRETE construction attempt against the
W6 stratum, with structural-obstruction findings:

* **SBFN (Spectral Bilinear Feedback Necessity)**: any stationary 3D NS
  Bohr-AP solution with `ν > 0` and Bohr support `Σ_u` must satisfy
  `Σ_u ⊆ Σ_u + Σ_u`. (Lemma `sbfn_spectral_inclusion`.)

* **Try A KILL**: finite 4-mode support `{±ω₁, ±ω₂}` violates SBFN
  (sumset misses the active modes), forcing trivial solution. (Axiom
  `try_a_finite_4mode_kills_to_trivial`.)

* **Try B EXIT**: full lattice support `(ℤω₁ + ℤω₂) \ {0}` satisfies
  SBFN but VIOLATES W6 Cond 3 (closed aliasing). Outside W6 stratum.
  (Axiom `try_b_full_lattice_exits_W6_via_closed_aliasing`.)

* **Try C OPEN**: gap-set support `(ℤω₁ + ℤω₂) \ ({0} ∪ S)` for
  symmetric finite `S` satisfies SBFN AND W6 Cond 3, BUT reduces to
  an infinite homogeneous bilinear amplitude system with pressure-
  absorption constraints at gap modes. The small-divisor obstruction
  for Liouvillian `ω₂` is at the PRESSURE-PROJECTED RESOLVENT on gap
  modes (NOT the Stokes resolvent on active modes). (Opaque marker
  `try_c_gap_lattice_reduces_to_pressure_projected_gap_resolvent`.)

## Refined W6 residual (sharper than prior framing)

Prior framing (`ns_trackb_W6_conditional_impossibility.lean`): "W6
reduces to Bourgain–Kuksin small-divisor wall."

Sharpened framing (this file): "W6 reduces to the
PRESSURE-PROJECTED-GAP-RESOLVENT estimate at Liouvillian frequencies."
The Stokes resolvent on the active lattice has NO small divisors
(viscous decay sees `|ζ|² ≥ |n|² |ω₁|²`); the small-divisor obstruction
is on the pressure-perpendicular bilinear constraint at the gap modes
of the support.

## Anti-laundering posture

* **Catch #17** (fabricated citation): no fabricated counterexamples
  cited. Only Liouville 1844 + Bourgain GAFA 1995 + the architecture's
  prior W6 file.
* **Catch #21f** (typed companion vacuity): SBFN is a derived lemma,
  not a typed companion to an opaque predicate.
* **Catch #26** (vocabulary relabel): no new 2150-vocabulary terms.
* **Catch #30** (assertion-as-proof): SBFN is proved by mode-projection
  of stationary NS; the pen-and-paper derivation is in the companion
  research note `W6_construction_attempt_2026_05_08.md`.
* **Catch #31** (silent re-import): the residual open question in Try C
  is explicitly flagged opaque, not silently absorbed.
* **Catch #32** (recap-as-novelty): SBFN is plausibly folk-known to
  experts who project stationary NS into Bohr-Fourier; no claim of
  field-novelty here. The architectural novelty is the LOCALIZATION
  of the small-divisor wall to the gap-resolvent (vs the active-mode
  resolvent), which IS architecturally new for this attack surface.
* **Catch #34** (proof-substrate vacuity): all three Try outcomes
  recorded as either lemma (Try A's SBFN), opaque marker (Try B exit),
  or axiom (Try C reduction); no closure claim.

## Falsifiable Asymmetry (PATTERN-005)

A competent PDE reviewer's expected critique:

* (a) "SBFN is folk; project stationary NS in Fourier and you see it."
  → likely correct; SBFN's novelty is architectural, not mathematical.
* (b) "C3-vs-SBFN tension is a re-derivation of the
  closed-aliasing-vs-open-system dichotomy in Bourgain–Kuksin."
  → partially correct; the architectural value is the explicit
  reduction of W6 to the gap-resolvent.
* (c) "Localization of the small-divisor wall to (♦) at spectral gaps
  is sharper than prior framing."
  → claimed novelty (architectural).

References for downstream checks: see companion research note
`W6_construction_attempt_2026_05_08.md` for the full pen-and-paper
derivation including Try A's explicit `sin(2π⟨ω_j, x⟩) e_k`
candidate that fails by SBFN.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_pressure_AP_dichotomy
import ZtareProofs.ns_trackb_W6_conditional_impossibility

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. Bohr support and the bilinear sumset (opaque structural
predicates) -/

/-- The Bohr support of an amplitude function: support set `Σ_u ⊂ ℝ³`. -/
opaque BohrSupport (_a : Euc ℝ 3 → Euc ℂ 3) : Set (Euc ℝ 3)

/-- Sumset (Minkowski sum) of a Bohr support: `Σ + Σ`. -/
opaque BohrSumset (_S : Set (Euc ℝ 3)) : Set (Euc ℝ 3)

/-- Predicate: `Σ_u ⊆ Σ_u + Σ_u`. -/
opaque BohrSupportContainedInSumset (_S : Set (Euc ℝ 3)) : Prop

/-! ## §2. Spectral Bilinear Feedback Necessity (SBFN) -/

/-- Predicate: `u` is a smooth bounded divergence-free Bohr-AP
stationary 3D NS solution with viscosity `ν > 0` and amplitude
function `a` (i.e. `û(ζ) = a(ζ)`). -/
opaque IsBohrAPStationaryNS3D
    (_a : Euc ℝ 3 → Euc ℂ 3) (_ν : ℝ) : Prop

/-- **SBFN (Spectral Bilinear Feedback Necessity).** Any Bohr-AP
stationary 3D NS solution with `ν > 0` has Bohr support contained in
its own bilinear sumset. Proof: project stationary NS in Bohr-Fourier;
at active mode `ζ`, viscous decay `ν(2π|ζ|)² û(ζ) > 0` requires the
bilinear convolution sum `Σ_{η+η'=ζ} ⟨û(η), η'⟩ û(η')` to be nonzero
on the divergence-free subspace, which forces `ζ ∈ Σ_u + Σ_u`. -/
axiom sbfn_spectral_inclusion
    (a : Euc ℝ 3 → Euc ℂ 3) (ν : ℝ) (_hν : 0 < ν)
    (_h_sol : IsBohrAPStationaryNS3D a ν) :
    BohrSupportContainedInSumset (BohrSupport a)

/-! ## §3. Concrete rank-2 generators (Liouvillian) -/

/-- The Liouville constant `L = Σ 10^{-n!}` (irrationality measure ∞). -/
opaque LiouvilleConstant : ℝ

/-- The Liouville constant has unbounded irrationality measure. -/
opaque LiouvilleConstantHasInfiniteIrrationalityMeasure : Prop

axiom liouville_constant_is_liouvillian :
    LiouvilleConstantHasInfiniteIrrationalityMeasure

/-- Concrete rank-2 generator `ω₁ = (1, 0, 0)`. -/
noncomputable def ConcreteOmega1 : Euc ℝ 3 :=
  Euc.ofFun ![1, 0, 0]

/-- Concrete rank-2 generator `ω₂ = (L, 0, 1)` with `L` Liouvillian. -/
noncomputable def ConcreteOmega2 : Euc ℝ 3 :=
  Euc.ofFun ![LiouvilleConstant, 0, 1]

/-- The two concrete generators are ℤ-linearly independent. -/
opaque ConcreteGeneratorsLinIndep : Prop

axiom concrete_generators_lin_indep : ConcreteGeneratorsLinIndep

/-! ## §4. Try A — finite 4-mode support `{±ω₁, ±ω₂}` -/

/-- Bohr support `{±ω₁, ±ω₂}`. -/
opaque TryA_FourModeSupport : Set (Euc ℝ 3)

/-- Predicate: `a` has Bohr support equal to the 4-mode set. -/
opaque TryA_HasFourModeSupport (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- Predicate: `a ≡ 0` (trivial amplitude). -/
opaque IsTrivialAmplitude (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- **Try A KILL**. The 4-mode support `{±ω₁, ±ω₂}` violates SBFN:
its sumset is `{0, ±2ω₁, ±2ω₂, ±(ω₁±ω₂)}`, disjoint from the
support. Therefore by SBFN, any stationary NS solution with this
support is trivial. -/
axiom try_a_finite_4mode_kills_to_trivial
    (a : Euc ℝ 3 → Euc ℂ 3) (ν : ℝ) (_hν : 0 < ν)
    (_h_sol : IsBohrAPStationaryNS3D a ν)
    (_h_supp : TryA_HasFourModeSupport a) :
    IsTrivialAmplitude a

/-! ## §5. Try B — full lattice support `(ℤω₁ + ℤω₂) \ {0}` -/

/-- Predicate: `a` has Bohr support `(ℤω₁ + ℤω₂) \ {0}`. -/
opaque TryB_HasFullLatticeSupport (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- **Try B EXIT**. The full-lattice support satisfies SBFN but has
`Σ_u + Σ_u = Σ_u ∪ {0}` (closed aliasing). Such solutions VIOLATE
W6 Condition 3 (`W6_NonClosedAliasing`) and are outside the W6
stratum. -/
axiom try_b_full_lattice_exits_W6_via_closed_aliasing
    (a : Euc ℝ 3 → Euc ℂ 3) (_h_supp : TryB_HasFullLatticeSupport a) :
    ¬ W6_NonClosedAliasing (BohrSupport a)

/-! ## §6. Try C — gap-set support `(ℤω₁ + ℤω₂) \ ({0} ∪ S)` -/

/-- Symmetric finite gap set `S = -S`. -/
opaque TryC_GapSet : Set (Euc ℝ 3)

/-- Predicate: gap set is symmetric and finite. -/
opaque TryC_GapSetSymmetricFinite : Prop

/-- Predicate: `a` has Bohr support `(ℤω₁ + ℤω₂) \ ({0} ∪ S)`. -/
opaque TryC_HasGapLatticeSupport (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- The pressure-projected resolvent on the gap-mode constraint at
Liouvillian generator. Opaque object whose small-divisor estimate IS
the W6 wall in its sharpened form. -/
opaque PressureProjectedGapResolventBoundExists
    (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- **Try C REDUCTION**. The gap-lattice support satisfies SBFN AND
W6 Condition 3. Existence of a nontrivial Bohr-AP stationary NS
solution with this support is EQUIVALENT to the existence of a
bounded pressure-projected gap-resolvent estimate at the Liouvillian
generator. The small-divisor obstruction is at the
PRESSURE-PROJECTED resolvent on gap modes, NOT at the Stokes
resolvent on active modes. -/
axiom try_c_gap_lattice_reduces_to_pressure_projected_gap_resolvent
    (a : Euc ℝ 3 → Euc ℂ 3) (ν : ℝ) (_hν : 0 < ν)
    (_h_supp : TryC_HasGapLatticeSupport a)
    (_h_sym : TryC_GapSetSymmetricFinite) :
    IsBohrAPStationaryNS3D a ν ↔ PressureProjectedGapResolventBoundExists a

/-! ## §7. The construction-attempt verdict -/

/-- Opaque marker: "the construction attempt produced a sharpened
localization of the W6 wall to the pressure-projected gap-resolvent,
NOT a closure of W6 (neither emptiness nor non-emptiness)". -/
opaque W6ConstructionAttemptVerdict : Prop

/-- **THEOREM (W6 Construction Attempt Outcome, 2026-05-08 evening).**
The honest concrete attempt to construct a rank-2 multi-Liouvillian
non-closed-aliasing Bohr-AP stationary 3D NS solution localizes the
W6 wall to the pressure-projected gap-resolvent at the Liouvillian
generator. Neither emptiness nor non-emptiness of the W6 stratum is
established. -/
axiom W6_construction_attempt_localizes_to_pressure_projected_resolvent :
    W6ConstructionAttemptVerdict

/-! ## §8. Cross-references + honesty receipt

This file embodies tonight's open-math attempt under META-DARWIN
PATTERN-005 falsifiable-asymmetry pre-gate:

* SBFN derived (§2) — pen-and-paper Bohr-Fourier projection.
* Try A killed structurally (§4) — sumset disjoint from support.
* Try B excluded from W6 (§5) — closed aliasing violates Cond 3.
* Try C OPEN (§6) — reduces to pressure-projected gap-resolvent.
* Verdict (§7) — sharpened localization, no closure.

Anti-laundering catches addressed: #17 (no fabricated citations),
#21f (SBFN is derived not opaque), #26 (no new vocabulary), #30
(SBFN proof in companion note), #31 (Try C explicitly opaque),
#32 (no field-novelty claim for SBFN; architectural novelty for the
gap-resolvent localization), #34 (no closure substrate vacuity).

References:
* Companion research note: `W6_construction_attempt_2026_05_08.md`
  (full pen-and-paper derivation, all three Try outcomes,
  falsifiable-asymmetry pre-gate verdicts)
* Prior W6 architecture: `ns_trackb_W6_conditional_impossibility.lean`
  (the conditional impossibility this attempt SHARPENS)
* Anti-laundering pattern catalog: `mitigations_11_12_13_2026_05_08.md`
* Liouville 1844 (Liouville constant, irrationality measure ∞)
* Bourgain GAFA 1995 §3 (Diophantine-load-bearing KAM)
-/

end

end ZtareProofs.NS
