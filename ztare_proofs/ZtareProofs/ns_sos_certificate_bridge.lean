import Mathlib.Tactic
import ZtareProofs.ns_stealth_growth_tradeoff

/-!
# SOS certificate bridge for stealth-growth exclusion

Phase 5BK narrowed the proof target to a static intersection:

`pressure stealth + viscous tangency + active torque + positive net enstrophy`

did not occur in the tested high-resolution survivor basin.

This file adds the exact verifier side of an oracle-verifier architecture.
Python/SDP code may search for a certificate, but Lean should only check a
lossless receipt.  The receipt shape used here is intentionally small:

`dissipation - production = slack + sum_i square_i`

with `slack > 0`.  Once such an identity is supplied exactly, positivity of the
gap is immediate and no polynomial search is performed by Lean.
-/

namespace ZtareProofs.NS

/-- Square notation used by certificate receipts. -/
def certSq (x : ℝ) : ℝ :=
  x * x

/-- Sum of squares for a finite certificate term list. -/
def sumSquares : List ℝ → ℝ
  | [] => 0
  | x :: xs => certSq x + sumSquares xs

lemma certSq_nonneg (x : ℝ) : 0 ≤ certSq x := by
  unfold certSq
  exact mul_self_nonneg x

lemma sumSquares_nonneg : ∀ xs : List ℝ, 0 ≤ sumSquares xs
  | [] => by
      unfold sumSquares
      norm_num
  | x :: xs => by
      unfold sumSquares
      exact add_nonneg (certSq_nonneg x) (sumSquares_nonneg xs)

/--
If an exact certificate writes `gap` as positive slack plus a sum of squares,
then the gap is strictly positive.
-/
theorem positive_gap_of_sos_certificate
    (gap slack : ℝ) (terms : List ℝ)
    (hslack : 0 < slack)
    (hcert : gap = slack + sumSquares terms) :
    0 < gap := by
  rw [hcert]
  exact add_pos_of_pos_of_nonneg hslack (sumSquares_nonneg terms)

/-- Dissipation-production gap for the scalar stealth-growth cage. -/
def dissipationProductionGap (s : StealthGrowthState) : ℝ :=
  s.viscousDissipation - s.signedProduction

/--
An SOS certificate for the dissipation-production gap rules out positive net
enstrophy budget for the same state.
-/
theorem nonpositive_net_budget_of_sos_gap_certificate
    (s : StealthGrowthState) (slack : ℝ) (terms : List ℝ)
    (hslack : 0 < slack)
    (hcert : dissipationProductionGap s = slack + sumSquares terms) :
    netEnstrophyBudget s < 0 := by
  have hgap_pos : 0 < dissipationProductionGap s :=
    positive_gap_of_sos_certificate (dissipationProductionGap s) slack terms hslack hcert
  unfold dissipationProductionGap at hgap_pos
  unfold netEnstrophyBudget
  linarith

/--
If the gap certificate holds, a pressure-stealth segment cannot be
growth-bearing once the standard enstrophy-budget consistency identity is
available.
-/
theorem no_growth_bearing_segment_of_sos_gap_certificate
    (s : StealthGrowthState)
    (eps derivBound torqueFloor slack : ℝ) (terms : List ℝ)
    (_htube : inPressureStealthTube s eps derivBound torqueFloor)
    (hbudget : enstrophyBudgetConsistent s)
    (hslack : 0 < slack)
    (hcert : dissipationProductionGap s = slack + sumSquares terms) :
    ¬ growthBearingSegment s := by
  have hnet_lt : netEnstrophyBudget s < 0 :=
    nonpositive_net_budget_of_sos_gap_certificate s slack terms hslack hcert
  have hsterile : stealthGrowthSterile s := le_of_lt hnet_lt
  exact no_blowup_engine_inside_sterile_stealth_tube
    s eps derivBound torqueFloor _htube hbudget hsterile

end ZtareProofs.NS
