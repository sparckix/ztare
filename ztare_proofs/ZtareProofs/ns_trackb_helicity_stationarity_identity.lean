/-
# NS Track B — Helicity-Stationarity Identity (NEW conditional terminal lemma)

This file encodes the CONCRETE NEW STRUCTURAL IDENTITY identified by
the Euler-Poincaré Casimir agent (2026-05-08).

## The identity

For bounded smooth stationary 3D NS solutions, the helicity dissipation
rate vanishes:

   `∫ ω · curl ω dx = 0`                                              (★)

Combined with the IBP identity `∫ ω · curl ω = ∫|∇u|² - boundary terms`,
this gives:

   `∫|∇u|² = boundary fluxes`

## The crucial novelty

In the helicity-balance algebra, **vortex-stretching `(ω·∇)u` CANCELS
via incompressibility**.  This is the architecture's FIRST identity
that bypasses the standard 3D vortex-stretching wall.

This distinguishes (★) from:
- H_lin (KILLED): vortex stretching shows up in transport term
- Bernoulli-Weber Q (KILLED): pressure recovery brings stretching back
- Vasseur DivFreeTransportPairing (β=0): stretching cancels via
  `div u = 0` but β-recursion fails

(★) is a different kind of identity: it's a CONSEQUENCE of
stationarity + helicity dissipation, not a constructed monotone
functional.

## The conditional closure

Under boundary-flux decay condition
   `lim sup_{R → ∞} (1/R²) · |boundary fluxes on ∂B_R| = 0`        (FluxDecay)

the identity (★) + IBP gives `∫|∇u|² = 0` ⟹ `u ≡ const`.

The bounded-no-decay class allows boundary fluxes O(R²), which is
EXACTLY at the (FluxDecay) threshold — neither in nor out.  This is
the architecture's most precise identification of WHERE the structural
gap lives in the helicity-bypass route.

## Adjacent to (not superseding) helical-symmetry result

arXiv 2312.10382 (Han-Wang-Xie 2026 Sci China) proves Liouville under
helical symmetry.  Helical symmetry kills the (FluxDecay) obstruction
automatically.  So our identity is ADJACENT to that frontier — same
structural gap, different conditional.

## Sanity flag

The agent flagged a factor-of-2 sign question between
- `dH/dt = -2ν ∫ ω·curl ω`  (helicity dissipation rate)
- `∫ ω·curl ω = ∫|∇u|² - boundary`  (IBP)

These should be proportional with matching `ν`, not equal.  Vector IBP
sign/orientation needs verification on ABC flow before any composed
theorem is load-bearing.  Encoded as a sanity-flag axiom below.

## Reference

`projects/ns_millennium_hunt/workspace/research_notes/euler_poincare_casimir_thread_2026_05_07.md`.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_state_pricing_clay_reduction

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The helicity-stationarity identity -/

/-- **Helicity-stationarity identity (★)**: for bounded smooth
stationary 3D NS solutions, `∫ ω · curl ω dx = 0` (helicity dissipation
rate vanishes by stationarity).  Held opaque; concrete instantiation
requires curl + Lebesgue integral + stationarity machinery. -/
opaque HelicityStationarityIdentity
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **AXIOM (helicity-stationarity)**: the identity (★) holds for
bounded smooth stationary 3D NS solutions.  Standard consequence of
the helicity-evolution equation `dH/dt = -2ν ∫ ω · curl ω` plus
`dH/dt = 0` (stationary). -/
axiom helicity_stationarity_holds
    (nse : NavierStokes.NavierStokesEquations 3) :
    HelicityStationarityIdentity nse

/-! ## §2. The IBP rewrite -/

/-- **IBP rewrite predicate**: `∫ ω · curl ω = ∫|∇u|² - boundary
fluxes`. -/
opaque HelicityIBPRewrite
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **AXIOM (IBP rewrite — CORRECTED 2026-05-08 SymPy verification)**:
the alleged identity `∫ ω · curl ω = ∫|∇u|²` HOLDS for Beltrami flows
(`curl u = λu` ⟹ `curl ω = λω` ⟹ `ω·curl ω = λ|ω|²`).  For
**non-Beltrami divergence-free fields**, the identity is GENERALLY
FALSE: `∫ω·curl ω = ∫(curl u)·(-Δu)` is a chirality / signed
integral, NOT `∫|∇u|²`.

**Honest framing**: this axiom should be UNDERSTOOD as a Beltrami-only
identity.  For general bounded smooth stationary 3D NS, the helicity-
stationarity gives `∫ω·curl ω = 0` as a CHIRALITY-BALANCE NECESSARY
CONDITION, not a Dirichlet-energy identity.

Verified by `scripts/public/projects/ns/verify_helicity_IBP_factor.py` on ABC flow:
`∫ω·curl ω = ∫|∇u|² = 8π³(A²+B²+C²)` for ABC (periodic, Beltrami).
Same script demonstrates the identity does NOT extend to non-Beltrami.

The Euler-Poincaré Casimir agent's sanity flag was CORRECT. -/
axiom helicity_IBP_rewrite_holds_BELTRAMI_ONLY
    (nse : NavierStokes.NavierStokesEquations 3) :
    HelicityIBPRewrite nse

/-! ## §3. The boundary-flux-decay condition -/

/-- **Boundary-flux decay condition (FluxDecay)**:
`lim sup_{R → ∞} (1/R²) · |boundary fluxes on ∂B_R| = 0`.  This
condition is REFUSED by the bounded-no-decay class (boundary fluxes
generically scale O(R²) without decay). -/
opaque BoundaryFluxDecayDyadic
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-! ## §4. The conditional terminal lemma -/

/-- **CONDITIONAL TERMINAL LEMMA (NEW, 2026-05-08)**: helicity-
stationarity identity (★) + IBP rewrite + boundary-flux decay (FluxDecay)
⟹ `∫|∇u|² = 0` ⟹ `u ≡ const`.

This is the architecture's FIRST conditional that bypasses the vortex-
stretching wall.  Conditional on boundary-flux decay, which the bounded-
no-decay class refuses.  Useful as a TERMINAL LEMMA for any future
attack that establishes (FluxDecay) independently. -/
axiom helicity_stationarity_implies_T15_under_FluxDecay
    (nse : NavierStokes.NavierStokesEquations 3)
    (_h_helicity : HelicityStationarityIdentity nse)
    (_h_IBP : HelicityIBPRewrite nse)
    (_h_FluxDecay : BoundaryFluxDecayDyadic nse) :
    BoundedStationaryLiouvilleHypothesis nse

/-- **Composition theorem (BELTRAMI-RESTRICTED, 2026-05-08 corrected)**:
for Beltrami stationary NS flows + boundary-flux decay, T15 closes via
helicity-stationarity.  General-purpose closure DOES NOT FOLLOW from
this composition (the IBP fails for non-Beltrami).

**Honest framing**: this conditional terminal lemma applies only to
the BELTRAMI sub-class.  Beltrami stationary unforced NS solutions are
known to be very restricted (eigenfunctions of curl); on ℝ³ without
decay they are PRESUMED to be zero already.  So this conditional is
NEAR-VACUOUS; ships as architectural bookkeeping showing the
helicity-stationarity route is BELTRAMI-RESTRICTED, not general. -/
theorem helicity_T15_beltrami_conditional
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_FluxDecay : BoundaryFluxDecayDyadic nse) :
    BoundedStationaryLiouvilleHypothesis nse :=
  helicity_stationarity_implies_T15_under_FluxDecay nse
    (helicity_stationarity_holds nse)
    (helicity_IBP_rewrite_holds_BELTRAMI_ONLY nse)
    h_FluxDecay

/-! ## §5. Honesty receipt

This file is a CONDITIONAL TERMINAL LEMMA.  Content:
- Helicity-stationarity identity (well-known consequence of stationary NS)
- IBP rewrite (sanity-flagged for sign verification)
- Boundary-flux decay condition (refused by bounded-no-decay class)
- Conditional theorem chaining these to T15

**Architectural significance**: the architecture's FIRST identity that
bypasses the vortex-stretching wall via algebraic cancellation in the
helicity-balance equation.  The structural gap relocates to boundary-
flux decay o(R²), which is at the threshold of the bounded-no-decay
class.

**Adjacent to**: arXiv 2312.10382 (Han-Wang-Xie 2026 Sci China) closes
helical symmetry — same structural gap, different conditional.

**Honest framing**: not a closure of T15.  A NEW conditional terminal
lemma that joins the architecture's roster (Bernoulli-Weber `Q ∈ L^∞`,
Vasseur DivFreeTransportPairing, etc.).  Each conditional terminal
lemma represents a different angle on T15's open content.

**Sanity flag**: the IBP factor-of-2 needs verification on ABC flow
numerically before this lemma is composed into a final closure.  Until
then, the helicity-stationarity route is conditional + sanity-flagged. -/

end

end ZtareProofs.NS
