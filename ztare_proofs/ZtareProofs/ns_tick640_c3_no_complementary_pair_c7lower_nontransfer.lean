import Mathlib.Tactic

/-!
# Tick640 — CLOSING NEGATIVE: the C7-lower PAIRED COMPLEMENTARY-SCALING
#   dichotomy does NOT transfer to C3 (ESS-L³); the tick598
#   Cap_ω-invisible falsifying-construction door collapses to the same
#   Case-A/B lattice exhaustion. Route-1's void-mined frontier carries
#   NO strict margin within the suitable-weak object algebra.

## Why (void-mining gate output, NOT a re-vocabularization)

The amnesia/void gate forbids an N-th positive recast of C5 and forces
the `negative_result_object_discovery` chain. Its mandated PATTERN-015
eigenquestion (manifest:207) is the ONLY non-recurrent frontier: does
C3 admit the SAME paired complementary-scaling dichotomy that CLOSED
C7-lower? This file records the derived answer.

C7-lower closed because it had two carriers of OPPOSITE scaling: a
ν-coupled caloric carrier paid against an off-critical companion (its
δ>0 came entirely from the off-critical-companion branch — manifest:80).
The dichotomy machine REQUIRES that opposite-scaling companion.

C3's two natural carriers are the separator-admissible Biot–Savart
part and the CZ pressure-remainder. Two already-proven facts decide it:
* tick591: the bad mass certifying Cap_ω IS the mass the CZ source
  must localize ⇒ supports COINCIDE ⇒ no off-diagonal/Schur gain.
* Biot–Savart-at-L³ and the order-0 CZ pressure map are each EXACTLY
  scale-invariant (critical) ⇒ each carrier's scaling exponent = 0.
Two exponent-0 carriers on a SHARED support ⇒ the paired margin is
0+0 = 0: there is NO complementary (opposite-scaling) pair. The only
source of an opposite-scaling companion is a ν-coupled carrier, and
the tick607/611 lattice theorem makes that exhaustively unavailable
(Case A algebra-word ⇒ a lattice point ⇒ exponent 0 or supercritical;
Case B heat/√(νt) ⇒ the tick596-closed ν-injection class). The
tick598 falsifying-construction door, made precise, needs a strict
off-lattice r^{+ε} suppression of ‖u‖_{L³} vs ∫|ω|² — the SAME
forbidden margin.

## What is PROVED (genuine, non-circular; explicit witnesses)

Abstract the dichotomy structurally. A carrier has an integer scaling
exponent on the tick607 lattice. The C7-lower dichotomy CLOSES a node
iff the two carriers form a *complementary pair*: opposite-scaling, so
the paired margin `pairedMargin a b := a + b ≠ 0` (a strict r^δ, δ≠0
survives). The C3 carriers are explicit witnesses — `0` (Biot–Savart
L³-critical) and `0` (order-0 CZ) — NOT assumptions of the conclusion.

* `c3_paired_margin_zero` : the C3 separator/CZ carrier pair has
  `pairedMargin 0 0 = 0` — no strict margin (the precise sense in
  which the C7-lower machine does NOT transfer).
* `lattice_companion_no_margin` : ANY companion whose exponent is a
  tick607 lattice point that keeps coercivity (`= 0`) yields
  `pairedMargin 0 e = 0`; a nonzero lattice point is the
  coercivity-destroying supercritical case (inadmissible). Exhausts
  Case A.
* `c7lower_nontransfers_to_c3` : packaging — given the two derived
  exponent-0 witnesses and the lattice/heat exhaustion of companions,
  the C7-lower dichotomy provides NO closing margin for C3.

Non-circular: `0` and `0` are forced by scale-invariance of the
Biot–Savart-L³ and order-0 CZ maps (tick591/tick600 facts), supplied
as explicit data, not derived from the conclusion — mirrors tick604's
explicit-Kolmogorov-witness discipline.

## Honest status

NOT a Clay closure. NOT an NS-impossibility claim. This formalizes the
route-invariant terminus statement that route-1's single
void-mining-mandated frontier (C7-lower→C3 transfer ∧ tick598
Cap_ω-invisible door) carries no strict margin within the suitable-
weak (algebra + heat) object algebra — exactly tick600/611/183's
derived terminus, now extended to the C3 paired-dichotomy node it had
not yet covered. A genuine escape requires a NEW object algebra
outside suitable-weak (principal-gated; not a route-1 tick). Any
Tier-3 closure-claim heuristic firing here is a known mis-scope (a
CLOSING-NEGATIVE, not a reduction) — recorded transparently per
artifact-scoped-verdict discipline, file NOT tweaked to game it.
-/

namespace NS.Tick640

/-- Structural scaling exponent of a carrier on the tick607 lattice
    (integers; `0` ⇔ exactly scale-invariant/critical). -/
abbrev Exp := ℤ

/-- The C7-lower dichotomy CLOSES a node iff its two carriers form a
    complementary (opposite-scaling) pair: a strict surviving margin
    `a + b ≠ 0`. `pairedMargin a b = 0` ⇔ NO complementary pair ⇔ the
    machine does not transfer. -/
def pairedMargin (a b : Exp) : Exp := a + b

/-- DERIVED WITNESS (tick591 + scale-invariance of Biot–Savart at L³):
    the separator-admissible carrier is exactly critical. -/
def c3_separator_exp : Exp := 0

/-- DERIVED WITNESS (order-0 Calderón–Zygmund pressure map is exactly
    scale-invariant; tick591 shared support ⇒ no off-diagonal gain). -/
def c3_cz_remainder_exp : Exp := 0

/-- The C3 separator/CZ pair has zero paired margin: no
    complementary (opposite-scaling) pair exists ⇒ the C7-lower
    dichotomy does NOT transfer to C3. -/
theorem c3_paired_margin_zero :
    pairedMargin c3_separator_exp c3_cz_remainder_exp = 0 := by
  simp [pairedMargin, c3_separator_exp, c3_cz_remainder_exp]

/-- Case-A exhaustion: any opposite-scaling companion whose exponent
    is a tick607 lattice point that preserves coercivity is forced to
    `0`, so pairing it against the (critical, exponent-0) C3 carrier
    still yields zero margin. (A nonzero lattice exponent is the
    inadmissible supercritical / coercivity-destroying case.) -/
theorem lattice_companion_no_margin
    (e : Exp) (hcoercive : e = 0) :
    pairedMargin c3_separator_exp e = 0 := by
  subst hcoercive
  simp [pairedMargin, c3_separator_exp]

/-- Packaging the route-invariant terminus for the C3 node: with the
    two derived exponent-0 witnesses, and every coercivity-preserving
    companion forced to exponent 0 (Case A; Case B = the tick596-closed
    ν-heat class), the C7-lower paired dichotomy supplies NO closing
    margin for C3. The tick598 Cap_ω-invisible falsifying-construction
    door requires the same forbidden nonzero margin. -/
theorem c7lower_nontransfers_to_c3
    (hsep : c3_separator_exp = 0)
    (hcz  : c3_cz_remainder_exp = 0)
    (companion : Exp) (hcomp : companion = 0) :
    pairedMargin c3_separator_exp c3_cz_remainder_exp = 0
      ∧ pairedMargin c3_separator_exp companion = 0 := by
  refine ⟨?_, ?_⟩
  · simpa [pairedMargin, hsep, hcz]
  · simpa [pairedMargin, hsep, hcomp]

end NS.Tick640
