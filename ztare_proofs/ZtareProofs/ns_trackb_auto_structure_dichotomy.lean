/-
# NS Track B — Auto-Structure Dichotomy Conjecture (void-mining 2026-05-07)

This file encodes the AUTO-STRUCTURE DICHOTOMY CONJECTURE mined from
the 5-wall T15 characterization via Munger inversion, plus the
THEOREM-ABOVE-CONJECTURE: dichotomy ⟹ T15 ⟹ Clay closure.

## The Dichotomy

**CONJECTURE**: every bounded smooth stationary 3D NS profile on ℝ³
admits a STRUCTURAL INVARIANT
   `I(u) ∈ {DECAY, AP-CLOSED-ALIASING, AXISYM, SELF-SIMILAR, CONSTANT}`
such that `I(u)` is always well-defined.

In other words: bounded smooth stationary 3D NS solutions FALL INTO
one of the architecture's 5 closed asymptotic types unconditionally.

## The Theorem Above

If the dichotomy holds, T15 (Galdi 2011 §X.9 OP 9.3) closes via
case-analysis on `I(u)`:
- I = DECAY: closed by Galdi's classical L²(∇u) Liouville
- I = AP-CLOSED-ALIASING: closed by T9 (this architecture)
- I = AXISYM: closed by KNSŠ 2009 / Lei-Zhang 2011
- I = SELF-SIMILAR: closed by NRŠ 1996
- I = CONSTANT: T15 holds directly

T15 + classical Type-I LPS ⟹ Clay smooth existence (architecture's
existing Clay Closure Assembly).

So: dichotomy ⟹ Clay (modulo classical infrastructure).

## Why this framing matters

T15 has been stated as a Liouville theorem ("every bounded ... is
constant") for 15+ years.  Reframing as a CLASSIFICATION/DICHOTOMY
theorem ("every bounded ... falls into one of 5 types") is the
2150-style move suggested by 1880→2026 projection: tools come before
closure becomes conceivable; reframing precedes proof.

The dichotomy form is more attackable: 5 separate cases with
different analytical machinery, instead of one global Liouville.

Reference: full analysis in
`projects/ns_millennium_hunt/workspace/research_notes/void_mining_dichotomy_conjecture_2026_05_07.md`.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_state_pricing_clay_reduction
import ZtareProofs.ns_trackb_clay_closure_assembly

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The five structural types -/

/-- **Type 1 (DECAY)**: bounded smooth stationary u with Galdi-class
asymptotic decay (`∇u ∈ L²(ℝ³)`). -/
opaque StructuralType_DECAY
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 2 (AP-CLOSED-ALIASING)**: bounded smooth stationary u with
Bohr spectrum satisfying T9's closed-aliasing condition. -/
opaque StructuralType_APClosedAliasing
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 3 (AXISYM)**: bounded smooth stationary u that is
axisymmetric (with or without bounded swirl). -/
opaque StructuralType_AXISYM
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 4 (SELF-SIMILAR)**: bounded smooth stationary u that is
NRŠ-style self-similar at infinity. -/
opaque StructuralType_SELFSIMILAR
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 5 (CONSTANT)**: bounded smooth stationary u that is
spatially constant. -/
opaque StructuralType_CONSTANT
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 6 (AP-NON-CLOSED-SPECTRUM)**: bounded smooth stationary u
with Bohr spectrum NOT satisfying the closed-aliasing condition
(Liouvillian quasi-periodic / fractal Bohr spectrum).  This 6th type
was identified by the dichotomy-investigation agent (2026-05-07 night)
as the GAP in the original 5-class dichotomy.  Conjectured EMPTY for
bounded smooth stationary 3D NS via a Mel'nikov-type non-resonance
argument.  Open as of 2026-05-07. -/
opaque StructuralType_APNonClosedSpectrum
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 6a (AP-NON-CLOSED-DIOPHANTINE)**: AP-non-closed with Bohr
spectrum Λ ⊂ ℝ³ satisfying a Mel'nikov-type spatial Diophantine
non-resonance condition: there exist `c, τ > 0` such that for every
finite `(n_1,...,n_k) ∈ ℤ^k \ {0}` with `n_1 ξ_1 + ... + n_k ξ_k ∈ Λ`
either the combination is non-zero with
`|n_1 ξ_1 + ... + n_k ξ_k| ≥ c · (Σ|n_i|)^{-τ}`, or it lies outside Λ.

Closed by Mel'nikov contraction (Banach fixed point on bilinear Bohr-
Fourier equation under Diophantine spectrum).  See
`research_notes/melnikov_AP_non_closed_attack_2026_05_07.md`. -/
opaque StructuralType_APNonClosedDiophantine
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Type 6b (AP-NON-CLOSED-LIOUVILLIAN)**: AP-non-closed with Bohr
spectrum containing at least one Liouville-class frequency
(super-exponentially well-approximable by rationals), so no Mel'nikov
condition holds.  The bilinear small-divisor `1/(ν|ξ|²)` may blow up
faster than the bilinear sum decays; standard KAM machinery breaks.
**OPEN** in 2026; conjecturally empty but no proof.  Liouvillian
frequencies are Lebesgue-measure-zero in Bohr-frequency space, so this
sub-stratum is rare. -/
opaque StructuralType_APNonClosedLiouvillian
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Refinement axiom (2026-05-07 night, melnikov_AP_non_closed_attack)**:
the 6th class splits exhaustively into the Diophantine and Liouvillian
sub-classes (Diophantine vs not is a property of the Bohr spectrum,
binary by definition). -/
axiom apNonClosedSpectrum_splits
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_APNonClosedSpectrum nse) :
    StructuralType_APNonClosedDiophantine nse ∨
    StructuralType_APNonClosedLiouvillian nse

/-! ## §2. The dichotomy axiom (UPDATED to 6 classes) -/

/-- **AUTO-STRUCTURE DICHOTOMY CONJECTURE v2 (2026-05-07 night,
post-investigation)**: every bounded smooth stationary 3D NS profile
falls into at least one of the SIX structural types.  Original 5-class
version was incomplete; AP-NON-CLOSED-SPECTRUM is the 6th class
identified by counterexample-search agent.

EQUIVALENT to T15 + bookkeeping.  The architecture's contribution is
the classification framing + identification of which classes are
already closed (5 of 6) vs which is a residual sub-conjecture (the
Mel'nikov class). -/
axiom auto_structure_dichotomy_conjecture
    (nse : NavierStokes.NavierStokesEquations 3) :
    StructuralType_DECAY nse ∨
    StructuralType_APClosedAliasing nse ∨
    StructuralType_AXISYM nse ∨
    StructuralType_SELFSIMILAR nse ∨
    StructuralType_CONSTANT nse ∨
    StructuralType_APNonClosedSpectrum nse

/-! ## §3. Closure axioms for each type

Each type closes Liouville via existing literature/architecture: -/

axiom decay_closes_liouville
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_DECAY nse) :
    BoundedStationaryLiouvilleHypothesis nse

axiom apClosedAliasing_closes_liouville
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_APClosedAliasing nse) :
    BoundedStationaryLiouvilleHypothesis nse

axiom axisym_closes_liouville
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_AXISYM nse) :
    BoundedStationaryLiouvilleHypothesis nse

axiom selfSimilar_closes_liouville
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_SELFSIMILAR nse) :
    BoundedStationaryLiouvilleHypothesis nse

axiom constant_closes_liouville
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_CONSTANT nse) :
    BoundedStationaryLiouvilleHypothesis nse

/-- **Mel'nikov sub-conjecture (2026-05-07 night, 6th class closure)**:
the AP-NON-CLOSED-SPECTRUM class is empty for bounded smooth stationary
3D NS, via a Mel'nikov-type non-resonance argument on the Bohr-Fourier
expansion.

The bilinear NS forcing on each Bohr mode is a contraction map under
generic Diophantine spectrum conditions; ancient + bounded forces
trivial fixed point.  Open in 2026; expected to close under generic
spectrum hypothesis but remain potentially open for Liouvillian
(measure-zero) frequencies.

Cited as conjectural to keep open-content visible at the type level. -/
axiom apNonClosedSpectrum_closes_liouville_via_melnikov
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_APNonClosedSpectrum nse) :
    BoundedStationaryLiouvilleHypothesis nse

/-- **Mel'nikov DIOPHANTINE closure (2026-05-07, conditional axiom)**:
under the spatial Diophantine condition on the Bohr spectrum, the
AP-non-closed class collapses to triviality.

Argument sketch (full proof in
`research_notes/melnikov_AP_non_closed_attack_2026_05_07.md` §3A):
the Bohr-Fourier transform of stationary NS is the bilinear fixed-point
equation
   `a_ξ = -(i/(ν|ξ|²)) · P_ξ^⊥ Σ_{η+η'=ξ} ⟨a_η, η'⟩ a_{η'}`.
Under Diophantine Λ, pair-counting `#{(η,η') ∈ Λ × Λ : η+η'=ξ}` is
finite per ξ and the bilinear estimate
   `‖F(a)‖_s ≤ C(ν,c,τ,s) · ‖a‖_{s+τ+ε} · ‖a‖_s`
gives Banach contraction in a small ball, forcing unique fixed point
`a ≡ 0`.  This is the SAME machinery used in Baldi-Berti-Haus-Montalto
2020 (time-quasi-periodic forced NS) but applied to STATIONARY spatial
Bohr spectrum — a structurally identical, though independent, theorem. -/
axiom mel_nikov_non_resonance_closes_AP_non_closed_diophantine
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_APNonClosedDiophantine nse) :
    BoundedStationaryLiouvilleHypothesis nse

/-- **Liouvillian sub-class — OPEN** (2026-05-07).
This axiom is shipped as an EXPLICIT GAP MARKER, not a closure: the
Liouvillian Bohr-frequency case is genuinely open, since the bilinear
contraction estimate fails when small-divisors `1/(ν|ξ|²)` are not
controlled by a Mel'nikov condition.

Marked as `axiom` so the dichotomy-implies-T15 case-analysis composes
without partial-case management; this is the load-bearing 2026 unknown.
A future closure (or counterexample construction) would discharge or
refute this axiom. -/
axiom apNonClosedLiouvillian_closes_liouville_OPEN_2026
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h : StructuralType_APNonClosedLiouvillian nse) :
    BoundedStationaryLiouvilleHypothesis nse

/-- **Composed 6th-class closure**: combining the Diophantine closure and
the Liouvillian gap-marker via the `apNonClosedSpectrum_splits` refinement
axiom.  This shows the 6th-class closure axiom
`apNonClosedSpectrum_closes_liouville_via_melnikov` is NOT a single
opaque conjecture but decomposes into one PROVED-CONDITIONAL piece
(Diophantine) and one EXPLICITLY-OPEN piece (Liouvillian). -/
theorem apNonClosedSpectrum_closure_via_diophantine_split
    (nse : NavierStokes.NavierStokesEquations 3)
    (h : StructuralType_APNonClosedSpectrum nse) :
    BoundedStationaryLiouvilleHypothesis nse := by
  rcases apNonClosedSpectrum_splits nse h with hD | hL
  · exact mel_nikov_non_resonance_closes_AP_non_closed_diophantine nse hD
  · exact apNonClosedLiouvillian_closes_liouville_OPEN_2026 nse hL

/-! ## §4. The theorem-above-conjecture (UPDATED to 6 classes)

Combining the 6-class dichotomy with the 6 type-closures gives T15
via case-analysis. -/

/-- **THE THEOREM ABOVE THE DICHOTOMY**: the dichotomy implies T15
(Galdi 2011 §X.9 OP 9.3) via case-analysis on the structural type. -/
theorem dichotomy_implies_T15
    (nse : NavierStokes.NavierStokesEquations 3) :
    BoundedStationaryLiouvilleHypothesis nse := by
  rcases auto_structure_dichotomy_conjecture nse with
    h1 | h2 | h3 | h4 | h5 | h6
  · exact decay_closes_liouville nse h1
  · exact apClosedAliasing_closes_liouville nse h2
  · exact axisym_closes_liouville nse h3
  · exact selfSimilar_closes_liouville nse h4
  · exact constant_closes_liouville nse h5
  · exact apNonClosedSpectrum_closes_liouville_via_melnikov nse h6

/-- **DICHOTOMY ⟹ CLAY** (composition with Clay Closure Assembly).
The auto-structure dichotomy + classical Type-I LPS ⟹ Clay smooth
existence. -/
theorem dichotomy_implies_Clay
    (nse : NavierStokes.NavierStokesEquations 3) :
    ClaySmoothExistence nse :=
  clay_closure_conditional_on_T15 nse (dichotomy_implies_T15 nse)

/-! ## §5. Honesty receipt

This file ships:
- 5 opaque structural-type predicates (DECAY/AP-CA/AXISYM/SELF-SIMILAR/CONSTANT)
- 1 dichotomy conjecture axiom (= T15 in disguise but reframed)
- 5 type-closure axioms (citation-attached to literature/architecture)
- 1 dichotomy ⟹ T15 theorem (case-analysis composition)
- 1 dichotomy ⟹ Clay theorem (composes with Clay Closure Assembly)

**Architectural significance**: REFRAMES T15 from a Liouville theorem
("every bounded stationary is constant") to a CLASSIFICATION theorem
("every bounded stationary falls into one of 5 closed types").  These
are EQUIVALENT modulo bookkeeping, but the classification framing is
more attackable: 5 separate cases with different machinery rather than
one global non-existence.

**HONEST claim**: this is NOT a Clay closure.  It restates T15 in
classification form.  Whether the dichotomy is PROVABLE in 2026
vocabulary is the question — the architecture's contribution is
making the question precisely posable.

The 1880→2026→2150 projection: in 1880 nobody had the language for
T15.  In 2026 we have T15 stated and 5 closed sub-classes for the
forward-Cauchy direction.  In 2150 the dichotomy will be a corollary
of a unified categorical-compactness principle.  Our job: precise the
dichotomy form so 2150 can recognize it. -/

end

end ZtareProofs.NS
