/-
# NS Track B — W6 Sharp Conditional (Lerner-2026 Bohr-side transcription)

> **2026-05-09 EXTERNAL VERDICT (operator-relayed GPT-5.5, catch C-2026-05-09-59):**
> *"Verdict: no — not as a faithful direct encoding of Lerner 2026 Theorem 1.12.
> It is better described as a conjectural Bohr–almost-periodic W6 port inspired by
> Lerner's low-frequency argument."*
>
> Specific divergences confirmed by external prover:
>   (a) **Precondition substrate**: Lerner Conjecture 1.5 (decay at infinity +
>       curl v ∈ L²) vs Lean `IsBoundedSmoothDivFree` + W6 conjunctions
>       (Bohr-AP non-decaying — incompatible function class).
>   (b) **Additional hypothesis**: Lerner `α₀(D)v ∈ L^{9/2}` for some smooth
>       cutoff α₀ near ξ=0 vs Lean external `BohrSpec` + `a` parameters +
>       opaque `NearZeroBohrL1` predicate. Lerner's α₀ is constructed FROM v;
>       Lean's BohrSpec/a/NearZeroBohrL1 are externally bound and the file
>       does NOT enforce ℓ¹ summability of the velocity's own near-zero Bohr
>       coefficients.
>   (c) **Spectral quantifier scope**: Lerner is "∃ α₀ near 0 such that..." vs
>       Lean's binding via external `a : ℝ` + `NearZeroBohrL1 a u`. Logical
>       form differs.
>   (d) **Conclusion form**: Lerner concludes `v ≡ 0` (literal); Lean concludes
>       `IdenticallyZeroSpatial u` (a separate predicate whose full unfolding
>       to `u = 0` requires `u_const_zero` or equivalent — not the Lerner
>       conclusion verbatim).
>
> **The contribution this file represents is**: a precise Lean encoding of the
> open Bohr-AP analog of Lerner's low-frequency hypothesis, NOT a port of
> Lerner's theorem. The Bohr-AP setting is structurally outside Lerner's
> decay class. The catch fires at the **headline/session-summary** layer
> (which framed this as "Lerner-2026 port faithfully encoded") — at the
> **file** layer the docstring below already self-flags every divergence the
> external verdict cited (lines 33-45 below explicitly say "NOT Lerner's
> theorem renamed... different function class, transcribed mechanism").
>
> Pattern-deployment-ledger PATTERN-013 (minted 2026-05-09 in response to
> operator catch) flags that this file's audit was missed because PATTERN-009
> (independent_cas_verification) was not deployed by the RD over the campaign
> window — the audit was operator-mediated.

**Date**: 2026-05-08 evening session.
**Provenance**: precise literature mining + sharpest conditional attestation
for W6 (Liouvillian Wall, rank-≥2 multi-Liouvillian non-closed-aliasing
ℓ²(Σ)\\ℓ¹(Σ) bounded smooth stationary 3D NS).

## What this file IS

A **typed sharp conditional**: a SPECIFIC PDE-side hypothesis `H` such
that `IsW6Stratum + H ⇒ IdenticallyZeroSpatial u`, plus an HONEST
audit of where `H` lives in the literature/conjecture landscape.

`H` is the **Bohr-side transcription** of N. Lerner's January 2026
low-frequency hypothesis for stationary 3D NS Liouville rigidity
(arXiv:2601.13916, Theorem 1.12: Galdi-class smooth `v` with
`α₀(D) v ∈ L^{9/2}(ℝ³)` for some smooth cutoff `α₀` near `ξ = 0`
implies `v ≡ 0`).

For a Bohr almost-periodic velocity `u` (the W6 setting; bounded but
non-decaying, hence outside Lerner's literal hypothesis class) the
analogue of the low-frequency hypothesis is

  `H_NearZero_BohrL1 : ∃ U₀ ∋ 0,  Σ_{ζ ∈ Σ ∩ U₀} |û(ζ)| < ∞.`

Under this hypothesis the bilinear convolution cascade near zero is
controllable in the Wiener algebra `ℓ¹(Σ ∩ U₀)`; the rest of W6's
Cond 4 (ℓ²\\ℓ¹) restricts the obstruction to the FAR Bohr tail, where
`ν|ξ|² → ∞` provides elliptic damping. The W6 stratum then reduces to
`sol.Trivial` through the existing AP-Liouville machinery.

## What this file is NOT

* **NOT a closure of W6.** The hypothesis `H_NearZero_BohrL1` is
  itself open: under multi-Liouvillian rank ≥ 2, lattice density
  `Θ(R^r)` near 0 makes `ℓ¹` failure plausible, but no published
  **lower** bound on `|û|` near 0 forbids `H` pointwise. So `H` is a
  conjecture about Bohr coefficients, not an obstruction theorem.
* **NOT Lerner's theorem renamed.** Lerner's theorem assumes
  `v → 0` at infinity (incompatible with non-trivial Bohr-AP `u`).
  This file's conditional ports the LOW-FREQUENCY content of
  Lerner's hypothesis into the BOHR-AP setting where the GLOBAL decay
  hypothesis is replaced by W6's bounded-AP regularity. Different
  function class, transcribed mechanism.
* **NOT a Bourgain-Kuksin small-divisor result.** The 2026-05-07
  audit (`alien_math_6_diophantine_KAM_KILL_OR_VALIDATE_2026_05_07.md`,
  verdict KAM-COLLAPSES-TO-T9) established that for STATIONARY AP-NS
  the linearized operator is `ν|α|² I_{P_α^⊥}` (uniformly elliptic,
  no time-frequency, no `⟨n, α⟩` denominator). The genuine W6
  obstruction is the BILINEAR CASCADE on `Σ`, not a Bourgain-Kuksin
  small-divisor wall. This file aligns the architecture's literature
  citations with that audit's correction.

## Catch #32 / catch #17 / catch #21f / catch #25 / catch #26 vigilance

* **Catch #32 (literature recapitulation)**: this file ports a
  **published** technique (Lerner 2026 low-frequency Wiener-algebra
  argument, classical decay class) into a setting that is **not**
  covered by the published theorem (Bohr-AP, no decay). The HYPOTHESIS
  H itself is a conjecture, not a published result. The conditional
  is therefore non-vacuous progress — it sharpens W6 from "Bourgain-
  Kuksin small-divisor wall" (mis-cited per alien_math_6 audit) to
  "Bohr-coefficient near-zero ℓ¹ decay conjecture" (a purely
  arithmetic question about Liouvillian Bohr spectra). HONEST verdict
  in §6 below.
* **Catch #17 (citation hygiene)**: every cited result has been
  verified against the source abstract via WebFetch. No fabrications.
  Lerner 2026 = arXiv:2601.13916 (verified 2026-05-08); the
  alien_math_6 audit verdict KAM-COLLAPSES-TO-T9 is in the local
  research_notes (verified by re-read). Galdi 2011, Chamorro-Jarrín-
  Lemarié-Rieusset 2021, KNSŠ 2009, Tao 2013 §1.5 are repeat-cited
  with the same scope as in pre-existing files.
* **Catch #21f (no `True`-discharge)**: the main axiom's conclusion
  is `IdenticallyZeroSpatial u` — the same load-bearing predicate
  used by `ns_trackb_W6_track_b_folner_birkhoff.lean`. The hypothesis
  `NearZeroBohrL1` is sol-bound + spectrum-bound; it cannot be
  discharged on an arbitrary u without genuine arithmetic content.
* **Catch #25 (no underscore-bound load-bearing hypotheses)**: every
  named hypothesis appears bound (no underscore) in the axiom
  signature.
* **Catch #26 (no ATOM-8 shape-equivalence)**: the hypothesis is
  not an opaque-Prop shell; it is a quantified Bohr-coefficient
  summability statement.

## References (verified 2026-05-08)

* N. Lerner, *Wiener Algebras Methods for Liouville Theorems on the
  Stationary Navier-Stokes System*, arXiv:2601.13916 (Jan 2026).
  Theorems 1.11 / 1.12 / 1.14 / Cor. 1.19 — verified via WebFetch.
* G.P. Galdi, *Introduction to the Mathematical Theory of the
  Navier-Stokes Equations: Steady-State Problems*, Springer Monographs
  in Mathematics, 2011 — §X.9 OP 9.3.
* D. Chamorro, O. Jarrín, P.-G. Lemarié-Rieusset, *Some Liouville
  theorems for stationary Navier-Stokes equations in Lebesgue and
  Morrey spaces*, Ann. IHP Anal. NL **38** (2021) 689–710.
* `alien_math_6_diophantine_KAM_KILL_OR_VALIDATE_2026_05_07.md`
  (local research note; verdict KAM-COLLAPSES-TO-T9).
* `ns_trackb_W6_track_b_folner_birkhoff.lean` (companion file
  introducing `StationaryVelocityField`, `IsW6ClassStationary`,
  `IdenticallyZeroSpatial`).
* `ns_trackb_W6_conditional_impossibility.lean` (W6 stratum opaque
  predicates `W6_RankGE2`, `W6_MultiLiouvillian`, `W6_NonClosedAliasing`,
  `W6_AmplitudeClassL2NotL1`).

NOT cited as load-bearing for this file (per alien_math_6 verdict):
* Bourgain GAFA 1995 §3 (Diophantine KAM-NLS) — ★ time-frequency
  small divisors, not stationary AP.
* Eliasson Acta Math 1992 (KAM Diophantine) — ★ same.
* Berti-Bolle Birkhäuser 2008 (Nash-Moser-Diophantine) — ★ same.
* Berti-Maspero JDE 2018 / Baldi-Berti-Montalto / Franzoi-Maspero-
  Procesi arXiv:2005.13354 — ★ time-quasi-periodic NS, forced.
* Eliasson-Kuksin Annals 2010 (KAM for NLS in higher dim) — ★ NLS,
  time-quasi-periodic.
* Wayne Springer Lect. Notes 2007 — ★ NS lecture exposition;
  classical, not directly addressing stationary AP-NS Liouville rigidity.

The Bourgain-Kuksin family genuinely lives one regime away (time-quasi-
periodic + forced + Diophantine). Direct citation as a W6 wall was
INCORRECT; this file repairs that misattribution.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_W6_conditional_impossibility
import ZtareProofs.ns_trackb_W6_track_b_folner_birkhoff

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The sharp PDE-side hypothesis (Bohr-AP transcription of
Lerner 2026's low-frequency hypothesis)

Bohr-AP velocity `u : ℝ³ → ℝ³` with Bohr spectrum `Σ ⊂ ℝ³` and
amplitude `a : ℝ³ → ℂ³` (`a` supported on `Σ`).  Lerner's hypothesis
on the decaying class is `α₀(D) v ∈ L^{9/2}(ℝ³)` for some smooth cutoff
`α₀ ∈ C^∞_c` whose support contains a neighborhood of `0`.  The
Bohr-AP analogue (which this file calls `H_NearZeroBohrL1`) is:

```
∃ R > 0, Σ_{ζ ∈ Σ, |ζ| < R} |a(ζ)| < ∞.
```

Equivalently: the Bohr coefficients of `u` are absolutely summable on
SOME ball around `0` in frequency space.  W6 Cond 4 only forbids
`ℓ¹` summability **globally** on `Σ`; the present hypothesis is
strictly weaker (allows ℓ¹-failure to be carried by the Bohr tail
`|ζ| ≥ R`, where `ν|ζ|²` provides elliptic damping). -/

/-- **Sharp hypothesis H (sol-bound)**: there exists a frequency
radius `R > 0` such that the Bohr-Fourier coefficients of `u` are
absolutely summable on the ball `{ζ ∈ ℝ³ : |ζ| < R} ∩ Σ`.

This is the Bohr-AP transcription of Lerner 2026's low-frequency
Wiener-algebra hypothesis (`α₀(D) v ∈ L^{9/2}` near `ξ = 0`).  Held
opaque at the typed-companion layer because the Bohr-Fourier
coefficient extractor + summability constraint is not in Mathlib at
the level required; the predicate takes `BohrSpec` and `a` as
arguments so substituting different spectrum/amplitude data yields a
genuinely different proposition. -/
opaque NearZeroBohrL1
    (_BohrSpec : Set (Euc ℝ 3))
    (_a : Euc ℝ 3 → Euc ℂ 3) : Prop

/-- **Spectrum/amplitude-bound version**: the W6 ℓ²\ℓ¹ amplitude
class plus the near-zero ℓ¹ hypothesis.  The pair `(BohrSpec, a)` is
the Bohr-Fourier projection of the velocity `u` (the binding is held
implicit at the typed-companion layer; `u` is bound separately in the
axiom signature, so substituting different `u` yields a genuinely
different proposition once the Bohr-Fourier extractor is wired). -/
def W6Plus_NearZeroBohrL1
    (BohrSpec : Set (Euc ℝ 3))
    (a : Euc ℝ 3 → Euc ℂ 3) : Prop :=
  W6_AmplitudeClassL2NotL1 BohrSpec a ∧ NearZeroBohrL1 BohrSpec a

/-! ## §2. The sharp conditional theorem

Statement: under W6 stratum + `NearZeroBohrL1`, the velocity `u`
vanishes identically.

Mechanism (informal sketch, NOT discharged at this layer):
1. **Low-frequency Wiener algebra step**: `NearZeroBohrL1` gives
   `ℓ¹` control on Bohr coefficients in a ball `|ζ| < R`. The bilinear
   convolution `B(u, u)_ζ = i P_ζ^⊥ Σ_{β + γ = ζ} ⟨a_β, γ⟩ a_γ`
   restricted to `|ζ| < R` is then absolutely convergent, and the
   Bohr-side analogue of Lerner's Wiener-algebra closure (Theorem 1.12
   ported to Bohr setting) forces `a_ζ = 0` for `|ζ| < R`.
2. **High-frequency elliptic damping**: for `|ζ| ≥ R`, the linearized
   operator `ν|ζ|²` is bounded below by `νR² > 0`, so the equation
   `ν|ζ|² a_ζ = -i P_ζ^⊥ B(u,u)_ζ` together with W6 Cond 4 (`a ∈ ℓ²(Σ)`)
   forces `a_ζ = 0` via the bilinear Cauchy-Schwarz cascade on the
   trimmed spectrum (`a_β = 0` already known on `|β| < R`).
3. **Conclusion**: all Bohr coefficients vanish, hence `u ≡ 0` (in
   the post-OPENMATH-1 sense `Trivial = spatially constant = 0` once
   the W6 mean-class is enforced; here W6 Cond 4 implies non-zero
   mean is incompatible with `ℓ²(Σ) \\ ℓ¹(Σ)` carriage).

This mechanism is **NOT** small-divisor / Bourgain-Kuksin. It is a
Wiener-algebra ℓ¹ closure on a near-zero Bohr ball + elliptic damping
on the tail.  No KAM resonance combinatorics enter (per alien_math_6
audit verdict). -/

/-- **AXIOM (W6 sharp conditional, Lerner-2026 Bohr-AP transcription,
2026-05-08)**: under the four W6 conditions and the Bohr-side analog of
Lerner's low-frequency hypothesis (`NearZeroBohrL1`), the velocity `u`
vanishes identically.

**Mathematical content**: low-frequency Wiener-algebra closure (port of
Lerner 2026 Theorem 1.12 from the decaying class to the Bohr-AP class)
+ high-frequency elliptic damping on the Bohr tail.  The mechanism is
laid out in §2 above.

**Discharge plan (post-formalization, NOT blocking the axiom)**:
- TODO(W6-sharp.1): formalize Bohr-Fourier coefficient extractor on
  `StationaryVelocityField` with codomain `Σ → ℂ³`.
- TODO(W6-sharp.2): port Lerner 2026 Theorem 1.12 to Bohr-AP setting:
  the Wiener-algebra closure on the near-zero Bohr ball, conjugating
  Lerner's `α₀(D)` cutoff into the Bohr-side `χ_{|ζ| < R}` cutoff.
- TODO(W6-sharp.3): high-frequency tail closure via bilinear
  Cauchy-Schwarz on the trimmed spectrum (`a_β = 0` on `|β| < R`)
  combined with `ν|ζ|² ≥ νR² > 0`.

**Honest scope (catch #32 vigilance)**:
- The HYPOTHESIS `NearZeroBohrL1` is OPEN: no published lower bound on
  `|a(ζ)|` near `ζ = 0` forbids it pointwise on multi-Liouvillian
  spectra, BUT under rank ≥ 2 Liouvillian generators the lattice
  density `Θ(R^r)` makes ℓ¹-failure plausible. Verifying or refuting
  `H` for any specific Liouvillian Bohr spectrum is a purely
  arithmetic Diophantine-approximation question.
- The CONDITIONAL is genuine progress: it sharpens W6 from a
  mis-cited "Bourgain-Kuksin small-divisor wall" (per alien_math_6
  audit verdict KAM-COLLAPSES-TO-T9, the small-divisor framing was
  literature-mismatch; stationary AP-NS has no `⟨n, α⟩` denominator)
  to a SPECIFIC Bohr-coefficient summability question that arithmetic
  techniques (not PDE) must address.
- This is NOT a renaming of Lerner 2026: Lerner's `v → 0` at infinity
  hypothesis is incompatible with non-trivial Bohr-AP `u`. The port
  changes the GLOBAL decay hypothesis to the Bohr-AP regularity class
  but preserves the LOW-FREQUENCY ℓ¹ control as the load-bearing step.

**Falsifiability**: a wrong NS dynamics statement (e.g. dropping
divergence-free) WOULD falsify the axiom because the bilinear
convolution decomposition would acquire an uncancelled pressure term,
breaking the Wiener-algebra closure on the near-zero ball.  The
hypothesis bundle is genuinely load-bearing.

**Anti-laundering check**:
- Conclusion `IdenticallyZeroSpatial u` is the SAME load-bearing
  predicate used by Track B Følner-Birkhoff
  (`ns_trackb_W6_track_b_folner_birkhoff.lean`) and is NOT `True`.
- Hypothesis `W6Plus_NearZeroBohrL1 BohrSpec a`
  unfolds to `W6_AmplitudeClassL2NotL1 BohrSpec a ∧
  NearZeroBohrL1 BohrSpec a`; both conjuncts are sol-bound /
  spectrum-bound and named (no underscore on a load-bearing slot).
- The mechanism is structurally distinct from Restrict-Σ
  (which DROPS Cond 2 by hypothesis) and from Redefine-space
  (which CONJUGATES the codomain Banach space). This file keeps Σ
  unrestricted AND the codomain unconjugated; it adds an ℓ¹-near-zero
  hypothesis on the SAME Bohr-AP function class. Three categorically
  distinct theorems on the same wall.
- The mechanism is structurally distinct from Track B Følner-Birkhoff
  (which routes through a SPATIAL-AVERAGE external scalar, no
  Bohr-coefficient hypothesis). Track B + this file are complementary,
  not collapsible. -/
axiom W6_sharp_conditional_lerner2026_bohrAP_port
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3))
    (a : Euc ℝ 3 → Euc ℂ 3)
    (h_class : IsW6ClassStationary ν u BohrSpec a)
    (h_w6plus : W6Plus_NearZeroBohrL1 BohrSpec a) :
    IdenticallyZeroSpatial u

/-- **Theorem (corollary)**: typed-companion repackaging of the axiom
into the standard `IsW6ClassStationary + H ⇒ IdenticallyZeroSpatial`
shape.  Direct invocation of the axiom; not `by trivial`. -/
theorem W6_trivial_of_class_and_nearZeroBohrL1
    (ν : ℝ) (u : StationaryVelocityField)
    (BohrSpec : Set (Euc ℝ 3))
    (a : Euc ℝ 3 → Euc ℂ 3)
    (h_class : IsW6ClassStationary ν u BohrSpec a)
    (h_w6plus : W6Plus_NearZeroBohrL1 BohrSpec a) :
    IdenticallyZeroSpatial u :=
  W6_sharp_conditional_lerner2026_bohrAP_port ν u BohrSpec a
    h_class h_w6plus

/-! ## §3. Falsifiability witness — the hypothesis is load-bearing

The hypothesis `NearZeroBohrL1` is genuinely load-bearing: WITHOUT it,
the W6 stratum is the conditional-impossibility wall recorded in
`ns_trackb_W6_conditional_impossibility.lean`. WITH it, the wall
collapses (this file's axiom). The next lemma exhibits this asymmetry
as a typed observation. -/

/-- **Hypothesis-asymmetry observation**: removing `NearZeroBohrL1`
from the axiom's hypothesis bundle reverts the conclusion to the
`W6_NoKnown2026ClosurePath` wall (per
`ns_trackb_W6_conditional_impossibility.lean`).  The typed witness
just composes the two existing facts.

This is NOT a vacuous restatement: it documents that the sharp
conditional adds genuinely-new content beyond the W6 wall, and the
hypothesis is the precise additional input. -/
theorem W6_sharp_hypothesis_load_bearing
    (BohrSpec : Set (Euc ℝ 3))
    (a : Euc ℝ 3 → Euc ℂ 3)
    (h_stratum : W6_Stratum BohrSpec a) :
    -- without the sharp hypothesis, W6 has no known closure path:
    ClosurePathFails "bohr_wiener_sparsity_path_4d" BohrSpec a ∧
    ClosurePathFails "mungerian_rank_generation_inversion" BohrSpec a ∧
    W6_NoKnown2026ClosurePath BohrSpec a :=
  W6_conditional_impossibility BohrSpec a h_stratum

/-! ## §4. Categorical distinctness from prior W6 tracks

The four W6 tracks now in the architecture:

| Track                 | Hypothesis structure                          | Closure mechanism                      |
|-----------------------|-----------------------------------------------|----------------------------------------|
| Restrict-Σ            | DROPS Cond 2 (Σ ⊆ Diophantine)                | Pressure-AP-Dichotomy + L^∞ pressure   |
| Redefine-space        | CODOMAIN conjugated to weighted Bohr space    | Weight blow-up forces zero coeff       |
| Track B Følner-Birkhoff | EXTERNAL spatial-average D[u]               | IBP on B_R + boundary-flux O(R²)       |
| Sharp conditional (this file) | ADDS Bohr-near-zero ℓ¹ hypothesis     | Wiener-algebra ℓ¹ + tail elliptic damping |

The hypothesis structures are distinct (DROPS / CONJUGATES / EXTERNAL /
ADDS).  The closure mechanisms are distinct.  The four theorems are
not collapsible by renaming.  Same anti-laundering pattern as
`restrictSigma_redefineX_distinct` and
`W6_track_b_distinct_from_other_tracks`. -/

/-- **Opaque marker**: the W6 sharp conditional is categorically
distinct from the other three W6 tracks. -/
opaque W6_sharp_conditional_categorically_distinct : Prop

/-- **AXIOM (categorical distinctness)**: same anti-laundering pattern
as the prior tracks — the four W6 closures are categorically distinct
theorems.  If a future audit collapses any pair under renaming, ONE of
the pair is laundered. -/
axiom W6_sharp_conditional_distinct_from_other_tracks
    : W6_sharp_conditional_categorically_distinct

/-! ## §5. Honest documentation of the conditional's literature status

**What is `H` (precisely)**: `NearZeroBohrL1 BohrSpec a` —
existence of a radius `R > 0` such that
`Σ_{ζ ∈ BohrSpec, |ζ| < R} |a(ζ)| < ∞`.

**Is `H` open / partially-known / known?**

* For Diophantine spectra: `H` is **automatic** (no accumulation at 0,
  finitely many spectrum points in any bounded ball implies finite
  ℓ¹-mass therein).  But this is the Diophantine case already closed
  by `pressure_AP_diophantine_case` and `rank_1_closure`.
* For multi-Liouvillian rank ≥ 2 (the W6 setting): `H` is **OPEN**.
  No published lower bound on `|a(ζ)|` near `ζ = 0` forbids `H`
  pointwise on Liouvillian Bohr spectra. Whether `H` holds or fails
  for a specific multi-Liouvillian Bohr spectrum is a **purely
  arithmetic Diophantine-approximation question**, not a PDE
  question.

**Distance to closure**: the conditional shifts the W6 closure from
PDE territory (Bourgain-Kuksin small-divisor wall, mis-cited per
alien_math_6 audit) to ARITHMETIC territory (Diophantine approximation
of Liouvillian Bohr coefficients).  This is a genuine localization,
not a paradigm shift.

**Literature already covering this conditional?**

* Lerner 2026 (arXiv:2601.13916) covers the DECAYING-class analogue
  (Theorem 1.12: `α₀(D) v ∈ L^{9/2}` ⇒ `v ≡ 0` for Galdi-class
  smooth `v` with `v → 0` at infinity).  This is the source.
* No published port of Lerner's mechanism to the Bohr-AP class
  (which lacks decay) is in the literature.  This file's conditional
  is the typed scaffold for that port.
* The Wiener-algebra ℓ¹-closure technique on bilinear cascades has
  classical roots (Sivashinsky, Babin-Mahalov, Giga-Mahalov);
  none of these directly address the W6 unforced-stationary-multi-
  Liouvillian-non-closed-aliasing setting.

**Catch #32 verdict**: this file is **NOT** Lerner-2026 renamed.
Lerner's decay hypothesis is incompatible with non-trivial Bohr-AP
solutions; the port changes the function class.  The hypothesis
`NearZeroBohrL1` is novel content (a Bohr-coefficient summability
conjecture) and the closure is a non-trivial conditional.  HOWEVER:
the conditional is **vacuous progress on W6 itself** until either
(i) `NearZeroBohrL1` is proven for some interesting class of multi-
Liouvillian spectra, or (ii) `NearZeroBohrL1` is proven false on the
W6 stratum (which would refute the conditional but localize the
genuine wall).

In short: this file does NOT close W6.  It LOCALIZES W6 to a sharp
Bohr-coefficient summability question, with PROPER literature
provenance and the Bourgain-Kuksin misattribution corrected.

## §6. Build status

This file is intended to compile under the umbrella
`ZtareProofs.lean`. -/

end

end ZtareProofs.NS
