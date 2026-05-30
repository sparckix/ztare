import Mathlib.Tactic
import ZtareProofs.ns_discrete_recurrence_map

namespace ZtareProofs

/-!
`ns_marginal_tax_rate` compresses the current NS branch to a single scalar
object:

  m(E) = L(E) / G(E)

This is the right bookkeeping object for the recurrence question, but it does
not magically solve the PDE. The theorem burden remains to prove properties of
`m` from Navier-Stokes structure rather than from narrative scaling claims.
-/

/-- Marginal tax rate: reset/exhaust loss divided by danger-phase gain. -/
noncomputable def marginalTaxRate (G L : cycleGain) (E : Real) : Real :=
  L E / G E

/-- Eventual tax dominance above threshold. -/
def eventualTaxDominance (G L : cycleGain) (EStar : Real) : Prop :=
  ∀ ⦃E : Real⦄, EStar ≤ E → 1 < marginalTaxRate G L E

/-- Non-dominant subsequence surviving to arbitrarily high intensity. -/
def nonDominantSubsequence (G L : cycleGain) (Es : Nat → Real) : Prop :=
  (∀ M : Real, ∃ n : Nat, M ≤ Es n) ∧ ∀ n : Nat, marginalTaxRate G L (Es n) ≤ 1

/--
If gain stays strictly positive and the marginal tax rate exceeds `1`, then
loss strictly dominates gain at that intensity.
-/
theorem loss_gt_gain_of_marginal_tax_gt_one
    {G L : cycleGain} {E : Real}
    (hG : 0 < G E)
    (htax : 1 < marginalTaxRate G L E) :
    G E < L E := by
  unfold marginalTaxRate at htax
  have := (one_lt_div hG).1 htax
  simpa [mul_comm] using this

/--
If gain stays strictly positive and the marginal tax rate is at most `1`, then
loss does not dominate gain at that intensity.
-/
theorem loss_le_gain_of_marginal_tax_le_one
    {G L : cycleGain} {E : Real}
    (hG : 0 < G E)
    (htax : marginalTaxRate G L E ≤ 1) :
    L E ≤ G E := by
  unfold marginalTaxRate at htax
  have := (div_le_one hG).1 htax
  simpa [mul_comm] using this

/--
Eventual tax dominance implies an eventual exhaust horizon, provided the
danger-phase gain remains strictly positive.
-/
theorem exhaust_horizon_of_eventual_tax_dominance
    {G L : cycleGain} {EStar : Real}
    (hG : ∀ ⦃E : Real⦄, EStar ≤ E → 0 < G E)
    (htax : eventualTaxDominance G L EStar) :
    exhaustHorizon G L EStar := by
  intro E hE
  exact loss_gt_gain_of_marginal_tax_gt_one (hG hE) (htax hE)

/--
If a non-dominant subsequence survives and the gain stays strictly positive
along that subsequence, then the fractal rival remains live at the scalar
budget level.
-/
theorem gain_not_outpaced_along_nonDominantSubsequence
    {G L : cycleGain} {Es : Nat → Real}
    (hsub : nonDominantSubsequence G L Es)
    (hG : ∀ n : Nat, 0 < G (Es n)) :
    ∀ n : Nat, L (Es n) ≤ G (Es n) := by
  intro n
  exact loss_le_gain_of_marginal_tax_le_one (hG n) (hsub.2 n)

/--
Target-shape theorem for the current scalar compression of the branch.
-/
theorem marginal_tax_rate_target_shape
    {G L : cycleGain} {EStar : Real}
    (h : eventualTaxDominance G L EStar) :
    eventualTaxDominance G L EStar := by
  exact h

end ZtareProofs
