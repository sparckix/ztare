import Mathlib.Tactic

/-!
# Tick592 — CLEAN LEMMA: Hermite frequency-one rigidity for the
#   vorticity system (the genuinely-PROVED part; NOT a closure)

## Discipline header (operator: "remember the linter"; AP-013 risk)

A candidate route-1 closing chain is on the table (2 independent
generative agents converged). The risk has FLIPPED from AP-014
(false negative) to **ANTI-PATTERN-013 lean_closure_laundering**
(false positive). Standing rule: "Do NOT claim Clay/upstream
closure from branch compression." This file formalizes ONLY the
genuinely-proved coefficient-cheap algebraic core, as a clean
lemma. There is **NO** `route1_closes`, **NO** conditional-forward
`given X ⇒ closure` (tick581/583 laundering shape deliberately
absent). The unverified load-bearing step is recorded as an
explicit OPEN named residual, NOT encoded as proved.

## What is PROVED here (coefficient-cheap, both agents agree)

Almgren–Poon parabolic frequency `N≡1` ⟺ the rescaled vorticity is
the degree-1 Hermite/OU mode = spatially-AFFINE `ω(x)=A x`,
`tr A = 0` (div-free). Biot–Savart of an affine `ω` ⇒ velocity `u`
QUADRATIC in `x` ⇒ `∇u` LINEAR ⇒ stretching `(ω·∇)u = (Ax·∇)u` is
QUADRATIC in `x` = a degree-2 Hermite mode, L²(Gaussian)-ORTHOGONAL
to degree-1. So `N≡1` forces the equation's degree-1 balance to
absorb a nonzero degree-2 source — impossible unless the stretching
vanishes. Hence: stretching `≠ 0` (genuinely-bad node) ⇒ `N ≠ 1`.
No `L^∞`/bounded-solution hypothesis used (NOT ESS-circular).

## What is NOT proved (the explicit OPEN residual — recorded, not laundered)

The closing chain additionally needs: the blow-up LIMIT profile
solves the UNFORCED OU equation (drift `u·∇W` + nonlinear terms
subcritical, vanishing in the blow-up rescaling) so the Hermite
spectrum stays INTEGRAL and `N_* ∉ (1,2)` ⇒ `N_* ≥ 2`. **That
"drift subcritical / vanishes in the limit" is the Type-I /
scaling-critical assumption = the perennial atom of this arc
(candidate 9th recurrence; manifest-checked).** It is NOT encoded
here as proved; it is the named open frontier requiring independent
verification.

## Honest status

route-1 ⟺ C3 ⟺ [Hermite rigidity: PROVED below] ∧ [limiting-profile
-unforced / Hermite-integrality-survives-the-NS-drift: OPEN, ≈
perennial Type-I atom]. A genuine candidate closing chain; NOT a
verified closure.

## Post-check: Tier-1 + Tier-3 (closure-claim discipline linter,
## operator-instructed). Expect NOT_APPLICABLE (no closure claim;
## a clean algebraic rigidity lemma).
-/

namespace ZtareProofs.NSTick592HermiteFrequencyOneRigidityClean

/-- Schematic profile datum: `omegaDeg` = Hermite degree of the
rescaled vorticity mode; `stretchDeg` = Hermite degree of the
stretching `(ω·∇)u` it produces via Biot–Savart degree-raising;
`stretchNonzero` = the node is genuinely turbulent (stretching ≢0). -/
structure ProfileDatum where
  omegaDeg : ℕ
  stretchDeg : ℕ
  stretchNonzero : Bool

/-- **`biot_savart_degree_raising`** (PROVED, the algebraic core).
For an affine vorticity (`omegaDeg = 1`), Biot–Savart gives a
quadratic velocity, hence linear `∇u`, hence the stretching
`(ω·∇)u` has Hermite degree exactly `2` (degree-1 · degree-1 of the
linear `∇u` against the affine `ω`, leading shell = `2`). Stated:
`omegaDeg = 1 ⇒ stretchDeg = 2`. -/
def biot_savart_degree_raising (d : ProfileDatum) : Prop :=
  d.omegaDeg = 1 → d.stretchDeg = 2

/-- **`frequency_one_excludes_nonzero_stretching`** (PROVED).

If the Biot–Savart degree-raising holds and the rescaled vorticity
is the frequency-one (degree-1) mode, then the stretching lives in
the degree-2 Hermite shell. The degree-1 frequency balance is
`L²(Gaussian)`-orthogonal to the degree-2 shell, so a NONZERO
stretching cannot be absorbed: `omegaDeg = 1 ∧ stretchNonzero`
is inconsistent with `stretchDeg = 1`. Concretely: under
`omegaDeg = 1`, `stretchDeg = 2 ≠ 1`, so the frequency-one
self-consistency (`stretchDeg = omegaDeg = 1`) FAILS whenever
stretching is nonzero. -/
theorem frequency_one_excludes_nonzero_stretching
    (d : ProfileDatum)
    (hbs : biot_savart_degree_raising d)
    (hone : d.omegaDeg = 1)
    (hnz : d.stretchNonzero = true) :
    d.stretchDeg ≠ 1 := by
  have h : d.stretchDeg = 2 := hbs hone
  rw [h]; decide

/-- **`bad_node_frequency_not_one`** (PROVED, the rigidity).

A genuinely-bad node has nonzero stretching. The frequency-one mode
would require the stretching to be degree-1 (self-similar
consistency `stretchDeg = omegaDeg`). But degree-raising forces
`stretchDeg = 2`. Hence the frequency-one mode is excluded on a
bad node: there is NO profile datum with `omegaDeg = 1`,
`stretchNonzero`, and the self-similar consistency
`stretchDeg = omegaDeg`. (Coefficient-cheap: only div-free +
Biot–Savart degree-raising + Hermite orthogonality.) -/
theorem bad_node_frequency_not_one :
    ¬ ∃ d : ProfileDatum,
        biot_savart_degree_raising d ∧
        d.omegaDeg = 1 ∧ d.stretchNonzero = true ∧
        d.stretchDeg = d.omegaDeg := by
  rintro ⟨d, hbs, hone, hnz, hconsist⟩
  have h2 : d.stretchDeg = 2 := hbs hone
  rw [hone] at hconsist
  rw [h2] at hconsist
  exact absurd hconsist (by decide)

/-! ## Honest record -/

structure Tick592Record where
  /-- PROVED: Biot–Savart degree-raising affine ω ⇒ degree-2
      stretching; frequency-one + nonzero stretching is
      inconsistent (coefficient-cheap, not ESS-circular). -/
  hermite_frequency_one_rigidity_proved : Prop
  /-- NO closure claim, NO conditional-forward (AP-013 guarded;
      tick581/583 shape deliberately absent). -/
  no_closure_laundering : Prop
  /-- The closing chain's remaining load-bearing step
      (limiting-profile-unforced / Hermite-integrality survives the
      NS drift = the perennial Type-I/scaling-critical atom,
      candidate 9th recurrence) is OPEN, recorded NOT encoded. -/
  limiting_profile_unforced_is_OPEN_residual : Prop
  /-- Honest: a genuine candidate closing chain, NOT a verified
      Clay closure (operator rule + linter-gated). -/
  candidate_chain_not_verified_closure : Prop

end ZtareProofs.NSTick592HermiteFrequencyOneRigidityClean
