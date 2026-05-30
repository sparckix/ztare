import Mathlib.Tactic

open scoped BigOperators

namespace ZtareProofs

/-!
`ns_cycle_resupply_threshold` records the abstract scalar theorem behind the
Phase 5EC cycle audit.

It does not prove a Navier-Stokes estimate.  It formalizes the bookkeeping
bar: if every return uses the same nonnegative ledger weights for signed
response and residual/tax, summing cycles cannot improve a local ratio bound.
Any promotion must therefore supply an independent amplifier, memory, or
resupply theorem.
-/

/-- Same-ledger accumulation cannot improve a pointwise response/tax ratio.

If `response i <= S * weight i` on every return, then the summed response is
also bounded by `S` times the summed ledger weight. -/
theorem same_ledger_accumulation_le
    {ι : Type*} [Fintype ι]
    {S : Real} {weight response : ι → Real}
    (hpoint : ∀ i, response i ≤ S * weight i) :
    (∑ i, response i) ≤ S * (∑ i, weight i) := by
  calc
    (∑ i, response i) ≤ ∑ i, S * weight i := by
      exact Finset.sum_le_sum (by intro i _hi; exact hpoint i)
    _ = S * (∑ i, weight i) := by
      simp [Finset.mul_sum]

/-- Ratio form of `same_ledger_accumulation_le`. -/
theorem same_ledger_ratio_le
    {ι : Type*} [Fintype ι]
    {S : Real} {weight response : ι → Real}
    (hden : 0 < ∑ i, weight i)
    (hpoint : ∀ i, response i ≤ S * weight i) :
    (∑ i, response i) / (∑ i, weight i) ≤ S := by
  have hsum :
      (∑ i, response i) ≤ S * (∑ i, weight i) :=
    same_ledger_accumulation_le hpoint
  exact (div_le_iff₀ hden).2 (by simpa [mul_comm] using hsum)

/-- Adaptive same-ledger accumulation cannot improve a pointwise response/tax
bound.

The multipliers `adapt i` may be chosen by any external or history-dependent
rule.  The scalar proof only needs their realized values to be nonnegative and
paired with the same blockwise defect ledger. -/
theorem adaptive_same_ledger_accumulation_le
    {ι : Type*} [Fintype ι]
    {S : Real} {adapt defect profit : ι → Real}
    (hadapt : ∀ i, 0 ≤ adapt i)
    (hpoint : ∀ i, profit i ≤ S * defect i) :
    (∑ i, adapt i * profit i) ≤ S * (∑ i, adapt i * defect i) := by
  calc
    (∑ i, adapt i * profit i)
        ≤ ∑ i, adapt i * (S * defect i) := by
          exact Finset.sum_le_sum
            (by
              intro i _hi
              exact mul_le_mul_of_nonneg_left (hpoint i) (hadapt i))
    _ = ∑ i, S * (adapt i * defect i) := by
          apply Finset.sum_congr rfl
          intro i _hi
          ring
    _ = S * (∑ i, adapt i * defect i) := by
          simp [Finset.mul_sum]

/-- Ratio form of `adaptive_same_ledger_accumulation_le`. -/
theorem adaptive_same_ledger_ratio_le
    {ι : Type*} [Fintype ι]
    {S : Real} {adapt defect profit : ι → Real}
    (hden : 0 < ∑ i, adapt i * defect i)
    (hadapt : ∀ i, 0 ≤ adapt i)
    (hpoint : ∀ i, profit i ≤ S * defect i) :
    (∑ i, adapt i * profit i) / (∑ i, adapt i * defect i) ≤ S := by
  have hsum :
      (∑ i, adapt i * profit i) ≤ S * (∑ i, adapt i * defect i) :=
    adaptive_same_ledger_accumulation_le hadapt hpoint
  exact (div_le_iff₀ hden).2 (by simpa [mul_comm] using hsum)

/-- If a local damped response `S` is positive, crossing one after multiplying
by an independent cycle amplifier requires amplifier at least `1/S`. -/
theorem amplifier_ge_inv_of_crosses_one
    {S amplifier : Real}
    (hS : 0 < S)
    (hcross : 1 ≤ amplifier * S) :
    1 / S ≤ amplifier := by
  exact (div_le_iff₀ hS).2 (by simpa [mul_comm] using hcross)

/-- If a geometric signed-coordinate memory sum crosses one, then memory must
exceed the threshold `1 - S` in the strict case. -/
theorem memory_gt_one_sub_response_of_crosses_one
    {S memory : Real}
    (hmem : memory < 1)
    (hcross : 1 < S / (1 - memory)) :
    1 - S < memory := by
  have hden : 0 < 1 - memory := by linarith
  have hmul : 1 * (1 - memory) < S := by
    exact (lt_div_iff₀ hden).1 hcross
  linarith

end ZtareProofs
