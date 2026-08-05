import ZtareProofs.AxiomPackJacobianDivisorMagnusEscape

/-!
Arithmetic endpoint for the all-order global-control Magnus ray.

The symbolic Hamiltonian certificate supplies

* logarithmic orders `n = 6 + 4m`;
* a Bernoulli divided-difference coefficient whose absolute even part obeys
  `positive_even_coefficient_recurrence`; and
* an adjoint-orbit multiplier with recurrence
  `r (k+1) = (-3/128) * (2k-1) * r k`.

This file checks the nonvanishing product and the source-degree arithmetic.
It does not encode the Hamiltonian quotient or the forward-dexp elimination.
-/

namespace AxiomPackJacobianGlobalControlMagnusEscapeArithmetic

open scoped BigOperators

open AxiomPackJacobianDivisorMagnusEscape

/-- Every multiplier in the normalized radial adjoint orbit is nonzero. -/
theorem radial_adjoint_chain_nonzero
    (r : ℕ → ℚ)
    (hZero : r 0 = 1)
    (hRec :
      ∀ k : ℕ,
        r (k + 1) =
          (-3 / 128) * (2 * (k : ℚ) - 1) * r k) :
    ∀ k : ℕ, r k ≠ 0 := by
  intro k
  induction k with
  | zero =>
      rw [hZero]
      norm_num
  | succ k ih =>
      rw [hRec k]
      apply mul_ne_zero
      · apply mul_ne_zero
        · norm_num
        · have hTwoK : (2 : ℚ) * k ≠ 1 := by
            exact_mod_cast (by omega : 2 * k ≠ 1)
          exact sub_ne_zero.mpr hTwoK
      · exact ih

/-- The even Bernoulli factor and radial orbit factor cannot cancel. -/
theorem global_control_ray_coefficient_nonzero
    (a r : ℕ → ℚ)
    (hOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hRZero : r 0 = 1)
    (hRRec :
      ∀ k : ℕ,
        r (k + 1) =
          (-3 / 128) * (2 * (k : ℚ) - 1) * r k)
    (m : ℕ) :
    (a (m + 1) / 2048) * r (2 * m + 1) ≠ 0 := by
  have haPos : 0 < a (m + 1) :=
    positive_even_coefficient_recurrence
      a hOne hARec (m + 1) (by omega)
  have hr : r (2 * m + 1) ≠ 0 :=
    radial_adjoint_chain_nonzero r hRZero hRRec (2 * m + 1)
  exact mul_ne_zero
    (div_ne_zero (ne_of_gt haPos) (by norm_num))
    hr

/-- On `n = 6 + 4m`, the Hamiltonian exponents `(3n-5,2n)` give source
derivation degree `5n-8` for density exponent two. -/
theorem global_control_ray_degree_arithmetic (m : ℕ) :
    let n := 6 + 4 * m
    (3 * n - 5) + 2 * n - 3 = 5 * n - 8 := by
  omega

/-- The certified source degrees are not bounded by any natural cap. -/
theorem global_control_ray_degrees_unbounded (bound : ℕ) :
    bound < 5 * (6 + 4 * bound) - 8 := by
  omega

/-- Aggregated arithmetic endpoint for the symbolic Hamiltonian theorem. -/
theorem global_control_magnus_escape_arithmetic_terminal_certificate
    (a r : ℕ → ℚ)
    (hOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hRZero : r 0 = 1)
    (hRRec :
      ∀ k : ℕ,
        r (k + 1) =
          (-3 / 128) * (2 * (k : ℚ) - 1) * r k) :
    (∀ m : ℕ, 1 ≤ m → 0 < a m) ∧
      (∀ k : ℕ, r k ≠ 0) ∧
      (∀ m : ℕ,
        (a (m + 1) / 2048) * r (2 * m + 1) ≠ 0) ∧
      (∀ m : ℕ,
        let n := 6 + 4 * m
        (3 * n - 5) + 2 * n - 3 = 5 * n - 8) ∧
      (∀ bound : ℕ, bound < 5 * (6 + 4 * bound) - 8) := by
  exact ⟨positive_even_coefficient_recurrence a hOne hARec,
    radial_adjoint_chain_nonzero r hRZero hRRec,
    global_control_ray_coefficient_nonzero
      a r hOne hARec hRZero hRRec,
    global_control_ray_degree_arithmetic,
    global_control_ray_degrees_unbounded⟩

end AxiomPackJacobianGlobalControlMagnusEscapeArithmetic
