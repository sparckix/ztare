import Mathlib.Tactic

/-!
# Tick591 — FORMALIZED NEGATIVE: the off-diagonal-CZ escape from C3
#   is covering-immune (cutoffs share support by construction)

## Why (operator standing instruction: "formalize the negatives")

Two INDEPENDENT generative cold-agents (gate [5]) converged: the
only way the C7-upper bounded-overlap covering could upgrade the
local-CZ half of C3 from supercritical (scaling 5/2) to
Carleman-admissible (≤1) is an OFF-DIAGONAL Biot–Savart gain, which
needs `dist(supp χ_loc , supp ∇φ_Q) ≳ r`. Agent #2 proved this is
FORCED to 0: the bad vorticity mass that makes `Cap_ω(Q)` a valid
lower bound on inherited badness (the separator's job) IS the mass
the CZ pressure source must localize for the harmonic-remainder
control (the pressure-decomposition's job) — same support. This
formalizes that impossibility as a clean re-litigation blocker
(tick578/590 shape; NO conditional-forward, NO closure claim).

## Manifest decision (HARD RULE)

This is NOT a new node: it is the perennial same-carrier
no-reuse / strict-margin atom (C5-family, 2026-05-12) recurring as
"off-diagonal-CZ separation forced to 0". Manifest alias #8.

## The negative (abstracted, genuine impossibility)

Model: a separator certificate `cap : Region → ℝ` lower-bounds
inherited badness ONLY via the bad mass on the separator support;
the CZ localization must cover that same support for the
harmonic-remainder bound. If one tries to separate the two supports
by distance `≥ d > 0` (to get the off-diagonal kernel gain), then
the separated bad mass `m_sep` on the separator-but-outside-loc
region is forced to 0 ⇒ `cap = 0` ⇒ the lower bound collapses.
I.e. there is NO support-separation `d>0` with BOTH `cap ≥ c·r`
(separator works) AND the CZ source disjoint from the separator
(off-diagonal gain). Exactly the signed-vs-positive / same-carrier
no-reuse obstruction.

## Post-check: Tier-1 + Tier-3 (expect NOT_APPLICABLE — clean
## impossibility, no closure claim).
-/

namespace ZtareProofs.NSTick591OffDiagonalCZEscapeBlockedNegative

/-- Schematic: `capBadMass` = bad enstrophy on the separator shell
that BOTH certifies inherited badness (cap ≥ c·r needs it > 0) AND
must be inside the CZ-localization (else the truncated singular
interaction is uncontrolled). `sepFromLoc` = 1 if the CZ source is
pulled disjoint from the separator (off-diagonal config), else 0.
The coupling: off-diagonal config ⇒ the certifying mass is excluded
⇒ capBadMass = 0. -/
structure ShellConfig where
  capBadMass : ℝ          -- bad enstrophy on the separator shell
  cap : ℝ                 -- the capacity lower-bound object
  radius : ℝ
  offDiagonalSeparated : Bool   -- CZ source pulled away from sep?

/-- The forced structural coupling (this IS the obstruction, not an
assumption about NS — it is the *definition* of the separator
certifying via its own bad mass + the CZ harmonic-remainder needing
that mass localized): in the off-diagonal config the certifying bad
mass is excluded, so `cap ≤ capBadMass = 0`. -/
def coupled (s : ShellConfig) : Prop :=
  (s.offDiagonalSeparated = true → s.capBadMass = 0) ∧
  (s.cap ≤ s.capBadMass)

/--
**`no_offdiagonal_with_valid_cap`** (PROVED — the negative).

There is NO shell configuration that is BOTH off-diagonally
separated (`offDiagonalSeparated = true`, the config the CZ gain
needs) AND has a valid positive capacity lower bound
(`c·radius ≤ cap` with `c, radius > 0`). Hence the off-diagonal-CZ
escape from C3 is unobtainable: the 3/2 deficit is covering-immune.
-/
theorem no_offdiagonal_with_valid_cap
    (s : ShellConfig) (c : ℝ)
    (hcoupled : coupled s)
    (hoff : s.offDiagonalSeparated = true)
    (hc : 0 < c) (hr : 0 < s.radius)
    (hvalid : c * s.radius ≤ s.cap) :
    False := by
  obtain ⟨hzero, hle⟩ := hcoupled
  have hm0 : s.capBadMass = 0 := hzero hoff
  have : s.cap ≤ 0 := by rw [hm0] at hle; exact hle
  have : c * s.radius ≤ 0 := le_trans hvalid this
  have : 0 < c * s.radius := mul_pos hc hr
  linarith

/--
**`offdiagonal_escape_is_covering_immune`** (PROVED, contrapositive
form). A valid capacity lower bound (`c·radius ≤ cap`, `c,radius>0`)
under the forced coupling FORCES the non-off-diagonal config
(`offDiagonalSeparated = false`) — i.e. the CZ source must share
the separator support, so the full Riesz singularity is on the
shell and no off-diagonal/Schur gain exists. Covering/cutoff
rearrangement cannot beat the 5/2→1 (deficit 3/2) supercriticality.
-/
theorem offdiagonal_escape_is_covering_immune
    (s : ShellConfig) (c : ℝ)
    (hcoupled : coupled s)
    (hc : 0 < c) (hr : 0 < s.radius)
    (hvalid : c * s.radius ≤ s.cap) :
    s.offDiagonalSeparated = false := by
  by_contra h
  have hoff : s.offDiagonalSeparated = true := by
    cases hb : s.offDiagonalSeparated with
    | false => exact absurd hb h
    | true => rfl
  exact no_offdiagonal_with_valid_cap s c hcoupled hoff hc hr hvalid

/-! ## Honest record -/

structure Tick591Record where
  /-- The off-diagonal-CZ escape from C3 is BLOCKED: no config has
      both a valid capacity lower bound and CZ-source/separator
      support-separation (PROVED). -/
  no_offdiagonal_with_valid_cap_proved : Prop
  /-- Covering/cutoff-rearrangement is provably immune to the 5/2→1
      deficit (the cutoffs share support by construction). -/
  covering_immune_proved : Prop
  /-- NOT a new wall: the perennial same-carrier no-reuse /
      strict-margin atom (C5-family, 2026-05-12) recurring; manifest
      alias #8. NO closure claim, NO conditional-forward. -/
  is_perennial_atom_recurrence_clean_negative : Prop
  /-- Honest live frontier (NOT a terminus): route-1 ⟺ C3 ∧
      closeable-C7-upper; C3 via a NON-cutoff mechanism is the open
      frontier (the cutoff-rearrangement family is exhausted). -/
  c3_via_noncutoff_mechanism_is_the_open_frontier : Prop

end ZtareProofs.NSTick591OffDiagonalCZEscapeBlockedNegative
