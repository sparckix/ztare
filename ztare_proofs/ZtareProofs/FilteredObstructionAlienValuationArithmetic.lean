import Mathlib.Tactic

/-!
Alien arithmetic carrier for a valuation/support filtered obstruction.

This target has no Jacobian, contact, cusp, or Magnus structure.  It checks
that the kernel-ratification bridge transfers to an unrelated filtration and
that adjoining an arbitrary finite prefix does not change the rate-two
identity.
-/

namespace FilteredObstructionAlienValuationArithmetic

def parameterOrder (n : ℕ) : ℕ := n + 1

def sourceExcess (n : ℕ) : ℕ := 2 * (n + 1)

theorem valuation_support_rate_two (n : ℕ) :
    sourceExcess n = 2 * parameterOrder n := by
  rfl

theorem valuation_support_finite_prefix_uniform (finitePrefix n : ℕ) :
    sourceExcess (finitePrefix + n) =
      2 * parameterOrder (finitePrefix + n) := by
  rfl

/-- Aggregated alien endpoint used only to test authority transfer. -/
theorem alien_valuation_arithmetic_terminal_certificate :
    (∀ n : ℕ, sourceExcess n = 2 * parameterOrder n) ∧
    (∀ finitePrefix n : ℕ,
      sourceExcess (finitePrefix + n) =
        2 * parameterOrder (finitePrefix + n)) := by
  exact ⟨valuation_support_rate_two,
    valuation_support_finite_prefix_uniform⟩

end FilteredObstructionAlienValuationArithmetic
