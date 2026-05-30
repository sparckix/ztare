/-
# NS Track B — Costin–Tanveer Borel-summability conditional on T15

**Verdict shipped 2026-05-07 (resurgence-2150 adversarial probe)**:
the Costin–Luo–Tanveer 2008 IE proves *short-time* Borel summability
of an evolutionary 1/t expansion for analytic data; it **does NOT
transcribe to the stationary Liouville problem T15 without
re-derivation** of the integral equation in a different small
parameter (forcing `ε`, far-field trans-monomial, …) for which the
heat-kernel resolvent is replaced by the steady Stokes/Oseen
resolvent.  See companion analysis
`projects/ns_millennium_hunt/workspace/research_notes/costin_tanveer_T15_attack_2026_05_07.md`.

What CAN be shipped honestly is the **typed conditional**: IF one can
re-derive a Costin–Tanveer-style IE for the stationary perturbation
series around `u=0` AND the Borel transform of that series has no
Stokes constants on `ℝ⁺`, THEN T15 closes.  Both hypotheses are open
mathematical work of comparable difficulty to T15 itself.

The architectural value is therefore not a closure but:
1. a clean naming of the two open analytic obstacles (IE re-derivation
   in stationary regime; Stokes-constants-on-`ℝ⁺` triviality),
2. a typed bridge from those two obstacles to T15, so any future
   progress on either plugs in by instantiation,
3. a record that the 2008 theorem itself does **not** discharge T15,
   blocking the optimistic misreading.

## Strict relationship to existing files

* `ns_trackb_state_pricing_clay_reduction` introduces the opaque
  `BoundedStationaryLiouvilleHypothesis` (T15) and ships the T15 →
  Tao 2013 §1.5 reduction skeleton.  This file consumes that opaque
  predicate; it does NOT redefine T15.
* `ns_trackb_T15_weighted_L2_closure` ships the weighted-L²
  conditional closure of T15 on a sub-class.  This file is an
  ORTHOGONAL conditional: it closes T15 via resurgence hypotheses,
  not weighted-L² hypotheses.  Either, plus its premises, suffices.

## Honesty receipt

* 3 opaque predicates (CT 2008 hypothesis; stationary IE re-derivation;
  Borel transform has no Stokes constants on `ℝ⁺`)
* 1 axiom (the structural reduction: stationary IE + no Stokes
  constants ⇒ T15)  — STRUCTURAL CITATION to the 2150 resurgence
  conjecture, not a proven theorem in 2026
* 1 conditional theorem (T15 closure conditional on the two
  resurgence hypotheses)
* 0 closure of T15

## References

* Costin, Luo, Tanveer, *Divergent expansion, Borel summability and 3D
  Navier–Stokes*, Phil. Trans. Roy. Soc. A **366** (2008) 2775–2788.
* Costin, Tanveer, *Short time existence and Borel summability in NS
  in ℝ³* (OSU MRI preprint 2007-04).
* Costin, Tanveer, *Integral formulation of 3D NS and ...*,
  World Scientific (2011).
* Aniceto, Başar, Schiappa, *Introduction to Resurgence, Trans-Series
  and Alien Calculus*, arXiv:1411.3585.
* Companion analysis: `costin_tanveer_T15_attack_2026_05_07.md`.

-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_state_pricing_clay_reduction

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. Costin–Tanveer 2008 — typed hypothesis

The 2008 theorem itself, as a typed predicate.  Holds for analytic
initial data on `ℝ³`, gives short-time existence and a conditional
global statement in terms of large-`p` asymptotics of the Borel-IE
solution.  The predicate captures the **2008 hypothesis** that holds
on analytic data; it does NOT capture the stationary case.
-/

/-- **Costin–Luo–Tanveer 2008 Borel-summability hypothesis** (evolutionary).
The formal `1/t` expansion of the NS solution from analytic initial
data is Borel-summable in the dual variable `p`, and the resulting
Borel-plane IE has a unique solution in an exponentially weighted
space.  This is the 2008 theorem, recorded as a typed predicate. -/
opaque BorelSummabilityCT2008
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-! ## §2. Stationary regime — the two open analytic obstacles

The CT 2008 IE does NOT transcribe to stationary NS without
re-derivation:
* `p` is conjugate to `1/t`; stationary NS has no time.
* The heat-kernel resolvent (level-1 Gevrey) is replaced by the
  steady Stokes/Oseen resolvent (Riesz potentials), which has
  weaker / different divergence behaviour.

Two open hypotheses are needed.
-/

/-- **(Open hypothesis #1, stationary IE re-derivation)** — there
exists a Costin–Tanveer-style integral equation for the stationary
perturbation series around `u = 0`, with a small parameter (forcing
`ε`, far-field decay variable, or 1/Re).  This is OPEN in 2026; it
is structurally analogous to the CT 2008 IE but in a different
analytic class (steady Stokes resolvent rather than heat semigroup).

Reference: companion `costin_tanveer_T15_attack_2026_05_07.md` §3.
-/
opaque StationaryBorelIntegralEquationExists
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **(Open hypothesis #2, no Stokes constants on `ℝ⁺`)** — assuming
the stationary IE of hypothesis #1 exists, its Borel transform has no
isolated singularities along the positive real axis.  Equivalently
(in Écalle alien-calculus language): the alien derivative along `ℝ⁺`
annihilates the formal stationary perturbation series.  This is the
**resurgence reformulation** of "no bounded non-trivial stationary
solution = T15".

Reference: alien-math 2150 framing in
`alien_math_resurgence_2150_2026_05_07.md` §3, §5.
-/
opaque NoStokesConstantsOnPositiveReal
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-! ## §3. Structural axiom — resurgence ⇒ T15

The 2150 conjecture, named precisely.  This is a **structural
citation**, not a 2026 theorem.  It records the architectural bet
that resurgence in the stationary regime, with trivial Stokes
structure on `ℝ⁺`, is equivalent to the bounded stationary Liouville
property.  Open work; if one direction were a theorem, T15 would be
closed (in that direction).
-/

/-- **AXIOM (resurgence ⇒ stationary Liouville, 2150-frame conjecture)**.

If a Costin–Tanveer-style IE exists for the stationary perturbation
series around `u = 0`, and its Borel transform has no Stokes constants
along `ℝ⁺`, then bounded smooth stationary 3D NS solutions are
constant (T15).

This axiom encodes the resurgence-theoretic reformulation of T15.  It
is **conjectural in 2026**: even if both hypotheses are eventually
proven, the link from "no Stokes constants on `ℝ⁺`" to "no bounded
non-trivial stationary solution" requires the Borel-Laplace inversion
to recover a *bounded* candidate, which itself requires control of
the IE solution at infinity in `p` — the same hard step that gates
CT 2008's global existence.

Reference: companion analyses
`costin_tanveer_T15_attack_2026_05_07.md` and
`alien_math_resurgence_2150_2026_05_07.md`. -/
axiom resurgence_no_stokes_implies_T15
    {nse : NavierStokes.NavierStokesEquations 3}
    (_h_IE : StationaryBorelIntegralEquationExists nse)
    (_h_no_stokes : NoStokesConstantsOnPositiveReal nse) :
    BoundedStationaryLiouvilleHypothesis nse

/-! ## §4. Conditional theorem — T15 from resurgence

The typed conditional: under the two open resurgence hypotheses, T15
is closed.  This is the same conditional pattern as the weighted-L²
closure (`ns_trackb_T15_weighted_L2_closure`), via a different rail.
-/

/-- **T15 closure conditional on resurgence hypotheses** —
combining the two open analytic obstacles (stationary IE existence;
no Stokes constants on `ℝ⁺`) with the structural resurgence axiom
delivers the bounded stationary Liouville property.  Conditional;
not a closure of T15. -/
theorem T15_resurgence_conditional_closure
    {nse : NavierStokes.NavierStokesEquations 3}
    (h_IE : StationaryBorelIntegralEquationExists nse)
    (h_no_stokes : NoStokesConstantsOnPositiveReal nse) :
    BoundedStationaryLiouvilleHypothesis nse :=
  resurgence_no_stokes_implies_T15 h_IE h_no_stokes

/-- **Chain to Tao 2013 §1.5** — composing the resurgence-conditional
T15 closure with the existing T15 → Tao reduction skeleton.  This is
purely a typed composition; both ingredients are conditional. -/
theorem resurgence_conditional_chains_to_tao13
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_IE : StationaryBorelIntegralEquationExists nse)
    (h_no_stokes : NoStokesConstantsOnPositiveReal nse) :
    True :=
  t15_reduces_ancient_liouville_skeleton nse
    (T15_resurgence_conditional_closure h_IE h_no_stokes)

/-! ## §5. Non-applicability of CT 2008 (negative receipt)

The 2008 theorem itself, recorded as `BorelSummabilityCT2008`, does
NOT imply the stationary IE existence hypothesis.  We make this
non-implication structural: there is no axiom

  `BorelSummabilityCT2008 nse → StationaryBorelIntegralEquationExists nse`

in this file, and there should be none.  CT 2008 is a *time-evolution*
result; the stationary regime needs a separately re-derived IE.

This negative receipt is the file's main architectural contribution:
it blocks the optimistic misreading "CT 2008 essentially solves T15".
-/

/-- **Non-implication receipt** — a `True` statement whose docstring
records that no implication

  `BorelSummabilityCT2008 nse → StationaryBorelIntegralEquationExists nse`

is asserted in this file.  This is intentional: the 2008 theorem is
evolutionary; the stationary IE is a separate open problem.  See
companion analysis §2, §4. -/
theorem ct2008_does_not_imply_stationary_IE_receipt :
    True := trivial

end

end ZtareProofs.NS
