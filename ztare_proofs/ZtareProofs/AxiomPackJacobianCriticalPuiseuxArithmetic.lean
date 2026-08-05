import Mathlib.Tactic

/-!
Arithmetic carrier for the critical Puiseux terminal.

The symbolic adapter owns the algebraic branch expansion, the selected germ,
Julia's formal-flow identity, and the two-flow factorization theorem.  This
file checks only the exact rational arithmetic used at the terminal:

* the regular denominator is `107/112` and hence nonzero;
* the first endpoint fractional coefficient is `1120/34347` and hence
  nonzero; and
* an integral polynomial-root multiplicity cannot equal `5/2`.

No formal-flow or Puiseux-expansion completeness claim is inferred here.
-/

namespace AxiomPackJacobianCriticalPuiseuxArithmetic

def regularDenominator : ℚ :=
  1 - 4 * (5 / 448)

def endpointRelativeBranch : ℚ :=
  (2 / 5) * (2800 / 34347)

theorem regular_denominator_exact :
    regularDenominator = 107 / 112 := by
  norm_num [regularDenominator]

theorem regular_denominator_nonzero :
    regularDenominator ≠ 0 := by
  norm_num [regularDenominator]

theorem endpoint_relative_branch_exact :
    endpointRelativeBranch = 1120 / 34347 := by
  norm_num [endpointRelativeBranch]

theorem endpoint_relative_branch_nonzero :
    endpointRelativeBranch ≠ 0 := by
  norm_num [endpointRelativeBranch]

theorem no_integral_multiplicity_five_halves (m : ℤ) :
    (m : ℚ) ≠ 5 / 2 := by
  intro h
  have hdoubleQ : (2 : ℚ) * m = 5 := by
    linarith
  have hdoubleZ : (2 : ℤ) * m = 5 := by
    exact_mod_cast hdoubleQ
  omega

/-- Aggregated arithmetic endpoint for the critical Puiseux obstruction. -/
theorem critical_puiseux_arithmetic_terminal_certificate :
    regularDenominator = 107 / 112 ∧
    regularDenominator ≠ 0 ∧
    endpointRelativeBranch = 1120 / 34347 ∧
    endpointRelativeBranch ≠ 0 ∧
    (∀ m : ℤ, (m : ℚ) ≠ 5 / 2) := by
  exact ⟨regular_denominator_exact,
    regular_denominator_nonzero,
    endpoint_relative_branch_exact,
    endpoint_relative_branch_nonzero,
    no_integral_multiplicity_five_halves⟩

end AxiomPackJacobianCriticalPuiseuxArithmetic
