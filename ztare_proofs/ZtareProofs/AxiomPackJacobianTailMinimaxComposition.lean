import Mathlib.Tactic

/-!
Logical and arithmetic carrier for the exhaustive Jacobian tail comparison.

The component artifacts own the pure contact-zero lower theorem, the
least-positive-contact lower theorem, and the admissible radial staircase.
This file checks only the well-order case split and the final bound
composition.  It does not infer any component theorem from finite data.
-/

namespace AxiomPackJacobianTailMinimaxComposition

/-- A predicate on parameter rows either never occurs or has a least
occurrence. -/
theorem zero_or_least_positive_occurrence (positive : ℕ → Prop) :
    (∀ n, ¬ positive n) ∨
      ∃ n, positive n ∧ ∀ m, m < n → ¬ positive m := by
  classical
  by_cases hexists : ∃ n, positive n
  · right
    let n := Nat.find hexists
    refine ⟨n, ?_, ?_⟩
    · simpa [n] using Nat.find_spec hexists
    · intro m hm
      exact Nat.find_min hexists (by simpa [n] using hm)
  · left
    exact fun n hn => hexists ⟨n, hn⟩

/-- Lower bounds on the two exhaustive branches give the unrestricted lower
bound. -/
theorem exhaustive_two_branch_lower_bound
    (hasPositive : Prop)
    (threshold sigma : ℚ)
    (hpure : ¬ hasPositive → threshold ≤ sigma)
    (hpositive : hasPositive → threshold ≤ sigma) :
    threshold ≤ sigma := by
  by_cases h : hasPositive
  · exact hpositive h
  · exact hpure h

/-- Matching lower and upper bounds determine the minimax value. -/
theorem matching_tail_bounds_force_value
    (threshold sigma : ℚ)
    (hlower : threshold ≤ sigma)
    (hupper : sigma ≤ threshold) :
    sigma = threshold := by
  exact le_antisymm hupper hlower

/-- Jacobian specialization of the general two-branch lower composition. -/
theorem exhaustive_contact_branch_lower_bound
    (hasPositive : Prop)
    (sigma : ℚ)
    (hpure : ¬ hasPositive → 2 ≤ sigma)
    (hpositive : hasPositive → 2 ≤ sigma) :
    2 ≤ sigma := by
  exact exhaustive_two_branch_lower_bound hasPositive 2 sigma hpure hpositive

/-- Jacobian specialization of the general matching-bound theorem. -/
theorem matching_tail_bounds_force_two
    (sigma : ℚ)
    (hlower : 2 ≤ sigma)
    (hupper : sigma ≤ 2) :
    sigma = 2 := by
  exact matching_tail_bounds_force_value 2 sigma hlower hupper

/-- Aggregated endpoint for the global comparison. -/
theorem tail_minimax_composition_terminal_certificate :
    (∀ positive : ℕ → Prop,
      (∀ n, ¬ positive n) ∨
        ∃ n, positive n ∧ ∀ m, m < n → ¬ positive m) ∧
    (∀ (hasPositive : Prop) (sigma : ℚ),
      (¬ hasPositive → 2 ≤ sigma) →
      (hasPositive → 2 ≤ sigma) → 2 ≤ sigma) ∧
    (∀ sigma : ℚ, 2 ≤ sigma → sigma ≤ 2 → sigma = 2) := by
  exact ⟨zero_or_least_positive_occurrence,
    exhaustive_contact_branch_lower_bound,
    matching_tail_bounds_force_two⟩

end AxiomPackJacobianTailMinimaxComposition
