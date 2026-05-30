import Mathlib.Tactic

/-!
# Low-beat weighted L1 receipt

Sequence-space receipt behind Phase 5IT/5IW:
if coherent same-output low-beat amplitudes are charged by a positive
predeclared physical reserve with minimum shell weight `w_min`, then bounded
reserve caps the low-output payoff `(sum b_j)^2`.

Phase 5IW is the anti-tautology guard: aggregate multi-pair low-beat columns
can look profitable under a hidden source-L2 budget.  That is not an admissible
global receipt.  The topology must declare the all-output L1/coherence price
before scoring payoff.  The theorems below intentionally require L1/coherence
charging hypotheses rather than source-coordinate L2 pricing.

This is not the continuum LP/Bony theorem.  It isolates the exact scalar
envelope that the continuum theorem must instantiate.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Prefix-level coherent low-beat envelope.

`lowBeatL1 n` is the absolute coherent output amplitude through prefix `n`.
`reserve n` is the predeclared physical reserve price through the same prefix.
`minWeight n` is the least reserve weight on the active prefix/tail.
`payoff n` is the same-output quadratic payoff. -/
structure WeightedLowBeatPrefixEnvelope where
  lowBeatL1 : ℕ → Real
  reserve : ℕ → Real
  minWeight : ℕ → Real
  payoff : ℕ → Real
  budget : Real
  lowBeat_nonneg : ∀ n, 0 ≤ lowBeatL1 n
  minWeight_pos : ∀ n, 0 < minWeight n
  budget_nonneg : 0 ≤ budget
  reserve_bounded : ∀ n, reserve n ≤ budget
  l1_charged_by_reserve : ∀ n, minWeight n * lowBeatL1 n ≤ reserve n
  payoff_def : ∀ n, payoff n = (lowBeatL1 n) ^ 2

/-- Bounded physical reserve gives the sharp prefix payoff cap. -/
theorem weighted_low_beat_payoff_cap
    (E : WeightedLowBeatPrefixEnvelope) (n : ℕ) :
    E.payoff n ≤ (E.budget / E.minWeight n) ^ 2 := by
  have hwpos : 0 < E.minWeight n := E.minWeight_pos n
  have hw_nonneg : 0 ≤ E.minWeight n := le_of_lt hwpos
  have hcharge : E.minWeight n * E.lowBeatL1 n ≤ E.reserve n :=
    E.l1_charged_by_reserve n
  have hreserve : E.reserve n ≤ E.budget := E.reserve_bounded n
  have hlow_mul : E.minWeight n * E.lowBeatL1 n ≤ E.budget :=
    le_trans hcharge hreserve
  have hlow_le : E.lowBeatL1 n ≤ E.budget / E.minWeight n := by
    rw [le_div_iff₀ hwpos]
    simpa [mul_comm] using hlow_mul
  have hbudget_div_nonneg : 0 ≤ E.budget / E.minWeight n :=
    div_nonneg E.budget_nonneg hw_nonneg
  rw [E.payoff_def n]
  let x := E.lowBeatL1 n
  let y := E.budget / E.minWeight n
  have hx : 0 ≤ x := E.lowBeat_nonneg n
  have hy : 0 ≤ y := hbudget_div_nonneg
  have hxy : x ≤ y := hlow_le
  have hdiff : 0 ≤ y - x := sub_nonneg.mpr hxy
  have hsum : 0 ≤ y + x := add_nonneg hy hx
  have hprod : 0 ≤ (y - x) * (y + x) := mul_nonneg hdiff hsum
  nlinarith

/-- Therefore an unbounded coherent low-beat payoff cannot coexist with a
bounded reserve and a tail weight bounded below by a positive constant. -/
theorem no_unbounded_weighted_low_beat_payoff
    (E : WeightedLowBeatPrefixEnvelope)
    {cap : Real}
    (hcap : ∀ n, (E.budget / E.minWeight n) ^ 2 ≤ cap)
    (hunbounded : ∀ B : Real, ∃ n, B < E.payoff n) :
    False := by
  rcases hunbounded cap with ⟨n, hn⟩
  have hpay : E.payoff n ≤ cap :=
    le_trans (weighted_low_beat_payoff_cap E n) (hcap n)
  exact not_lt_of_ge hpay hn

/-- Fixed-prefix version of the low-beat theorem packet.

The continuum LP/Bony estimate must instantiate `cap_tends_zero` from the
incompressible low-output symbol and the declared Sobolev reserve weights.
Once that is supplied, the coherent fixed-prefix low-beat payoff vanishes
along the high-shell tail. -/
structure VanishingFixedPrefixLowBeatEnvelope where
  envelope : WeightedLowBeatPrefixEnvelope
  cap_tends_zero :
    ∀ eps : Real, 0 < eps →
      ∃ N : ℕ, ∀ n : ℕ, N ≤ n →
        (envelope.budget / envelope.minWeight n) ^ 2 ≤ eps

/-- Bounded physical reserve plus diverging fixed-prefix reserve weights
precludes a surviving scalar coherent low-beat payoff. -/
theorem fixed_prefix_low_beat_payoff_vanishes
    (E : VanishingFixedPrefixLowBeatEnvelope) :
    ∀ eps : Real, 0 < eps →
      ∃ N : ℕ, ∀ n : ℕ, N ≤ n → E.envelope.payoff n ≤ eps := by
  intro eps heps
  rcases E.cap_tends_zero eps heps with ⟨N, hN⟩
  refine ⟨N, ?_⟩
  intro n hn
  exact le_trans (weighted_low_beat_payoff_cap E.envelope n) (hN n hn)

/-- A surviving fixed-prefix low-beat channel carries a positive payoff floor
arbitrarily far out in the high-shell tail. -/
def FixedPrefixLowBeatSurvivor
    (E : VanishingFixedPrefixLowBeatEnvelope) : Prop :=
  ∃ eps : Real, 0 < eps ∧
    ∀ N : ℕ, ∃ n : ℕ, N ≤ n ∧ eps < E.envelope.payoff n

/-- The fixed-prefix scalar low-beat escape is impossible once the continuum
LP/Bony theorem instantiates the growing physical reserve weight. -/
theorem no_fixed_prefix_low_beat_survivor
    (E : VanishingFixedPrefixLowBeatEnvelope) :
    ¬ FixedPrefixLowBeatSurvivor E := by
  intro hsurvivor
  rcases hsurvivor with ⟨eps, heps_pos, htail⟩
  rcases fixed_prefix_low_beat_payoff_vanishes E eps heps_pos with ⟨N, hN⟩
  rcases htail N with ⟨n, hn_tail, hn_payoff⟩
  exact not_lt_of_ge (hN n hn_tail) hn_payoff

/-- Moving-output/all-output scalar low-beat tail envelope.

`tailMinWeight J` is the minimum declared physical reserve weight in the
tail, such as `N_j^m / |q_j|` after all output atoms and coherence terms are
fixed before payoff scoring. -/
structure MovingAllOutputLowBeatEnvelope where
  tailL1 : ℕ → Real
  tailPayoff : ℕ → Real
  tailReserve : ℕ → Real
  tailMinWeight : ℕ → Real
  budget : Real
  output_topology_predeclared : Prop
  output_atoms_declared_before_payoff : Prop
  gram_coherence_declared_before_payoff : Prop
  physical_reserve_declared_before_payoff : Prop
  tail_l1_nonnegative : ∀ J, 0 ≤ tailL1 J
  tail_min_weight_positive : ∀ J, 0 < tailMinWeight J
  budget_nonnegative : 0 ≤ budget
  tail_reserve_bounded : ∀ J, tailReserve J ≤ budget
  tail_l1_charged_by_reserve :
    ∀ J, tailMinWeight J * tailL1 J ≤ tailReserve J
  tail_payoff_charged_by_l1 : ∀ J, tailPayoff J ≤ (tailL1 J) ^ 2
  cap_tends_zero :
    ∀ eps : Real, 0 < eps →
      ∃ J0 : ℕ, ∀ J : ℕ, J0 ≤ J →
        (budget / tailMinWeight J) ^ 2 ≤ eps

/-- Bounded physical reserve plus diverging moving-output tail weights kills
the scalar all-output low-beat tail. -/
theorem moving_all_output_low_beat_tail_payoff_vanishes
    (E : MovingAllOutputLowBeatEnvelope) :
    ∀ eps : Real, 0 < eps →
      ∃ J0 : ℕ, ∀ J : ℕ, J0 ≤ J → E.tailPayoff J ≤ eps := by
  intro eps heps
  rcases E.cap_tends_zero eps heps with ⟨J0, hJ0⟩
  refine ⟨J0, ?_⟩
  intro J hJ
  have hwpos : 0 < E.tailMinWeight J := E.tail_min_weight_positive J
  have hw_nonneg : 0 ≤ E.tailMinWeight J := le_of_lt hwpos
  have hcharge :
      E.tailMinWeight J * E.tailL1 J ≤ E.tailReserve J :=
    E.tail_l1_charged_by_reserve J
  have hreserve : E.tailReserve J ≤ E.budget :=
    E.tail_reserve_bounded J
  have hl1_mul : E.tailMinWeight J * E.tailL1 J ≤ E.budget :=
    le_trans hcharge hreserve
  have hl1_le : E.tailL1 J ≤ E.budget / E.tailMinWeight J := by
    rw [le_div_iff₀ hwpos]
    simpa [mul_comm] using hl1_mul
  have hbudget_div_nonneg : 0 ≤ E.budget / E.tailMinWeight J :=
    div_nonneg E.budget_nonnegative hw_nonneg
  let x := E.tailL1 J
  let y := E.budget / E.tailMinWeight J
  have hx : 0 ≤ x := E.tail_l1_nonnegative J
  have hy : 0 ≤ y := hbudget_div_nonneg
  have hxy : x ≤ y := hl1_le
  have hdiff : 0 ≤ y - x := sub_nonneg.mpr hxy
  have hsum : 0 ≤ y + x := add_nonneg hy hx
  have hprod : 0 ≤ (y - x) * (y + x) := mul_nonneg hdiff hsum
  have hsq : (E.tailL1 J) ^ 2 ≤ (E.budget / E.tailMinWeight J) ^ 2 := by
    nlinarith
  exact le_trans (E.tail_payoff_charged_by_l1 J)
    (le_trans hsq (hJ0 J hJ))

/-- A moving/all-output scalar low-beat survivor has a positive payoff floor
arbitrarily far out in the declared high-shell tail. -/
def MovingAllOutputLowBeatSurvivor
    (E : MovingAllOutputLowBeatEnvelope) : Prop :=
  ∃ eps : Real, 0 < eps ∧
    ∀ J0 : ℕ, ∃ J : ℕ, J0 ≤ J ∧ eps < E.tailPayoff J

/-- No moving/all-output scalar low-beat survivor remains once the continuum
topology instantiates a diverging physical tail weight. -/
theorem no_moving_all_output_low_beat_survivor
    (E : MovingAllOutputLowBeatEnvelope) :
    ¬ MovingAllOutputLowBeatSurvivor E := by
  intro hsurvivor
  rcases hsurvivor with ⟨eps, heps_pos, htail⟩
  rcases moving_all_output_low_beat_tail_payoff_vanishes E eps heps_pos
    with ⟨J0, hJ0⟩
  rcases htail J0 with ⟨J, hJ_tail, hJ_payoff⟩
  exact not_lt_of_ge (hJ0 J hJ_tail) hJ_payoff

/-- Diagnostic stream for the Phase 5IW topology trap.

`sourceL2Budget` is a hidden source-coordinate budget.  It is intentionally
separate from `outputCoherencePrice`: the audit showed that aggregate columns
can make source-L2 pricing look cheap unless the declared output/coherence
price is also charged. -/
structure SourceL2OnlyLowBeatDiagnostic where
  sourceL2Budget : ℕ → Real
  outputPayoff : ℕ → Real

/-- Bounded hidden source-L2 budgets alone do not imply any all-output low-beat
payoff cap.  This is the formal anti-tautology guard behind Phase 5IW: the
continuum theorem must instantiate `tail_l1_charged_by_reserve` or an
equivalent all-output positive-coherence price, not merely a source-coordinate
L2 estimate. -/
theorem source_l2_only_budget_does_not_cap_low_beat_payoff :
    ∃ S : SourceL2OnlyLowBeatDiagnostic,
      (∀ n : ℕ, S.sourceL2Budget n ≤ 1) ∧
        (∀ B : Real, ∃ n : ℕ, B < S.outputPayoff n) := by
  refine ⟨
    { sourceL2Budget := fun _ => 1
      outputPayoff := fun n => (n : Real) },
    ?_⟩
  constructor
  · intro n
    norm_num
  · intro B
    obtain ⟨n, hn⟩ := exists_nat_gt B
    exact ⟨n, by exact_mod_cast hn⟩

end

end ZtareProofs.NS
