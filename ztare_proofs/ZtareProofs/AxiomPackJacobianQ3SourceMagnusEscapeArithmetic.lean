import ZtareProofs.AxiomPackJacobianDivisorMagnusEscape

/-!
Arithmetic endpoint for the source Magnus escape after the `Q^3`
cancellation.

The symbolic Hamiltonian certificate supplies:

* logarithmic orders `n = 6 + 4m`;
* a response coefficient proportional to `B_(2m+2)/(2m+2)!`;
* a radial recurrence
  `r (k+1) = (9/896) * (2k+1) * r k`; and
* Hamiltonian exponents `(17+16m,16+12m)`.

This file checks noncancellation and degree arithmetic.  It does not encode
the excess quotient or the forward-dexp forcing calculation.
-/

namespace AxiomPackJacobianQ3SourceMagnusEscapeArithmetic

open scoped BigOperators

open AxiomPackJacobianDivisorMagnusEscape

/-- Every multiplier in the excess-minus-thirteen radial orbit is nonzero. -/
theorem q3_radial_adjoint_chain_nonzero
    (r : ℕ → ℚ)
    (hZero : r 0 = 1)
    (hRec :
      ∀ k : ℕ,
        r (k + 1) =
          (9 / 896) * (2 * (k : ℚ) + 1) * r k) :
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
        · have hOdd : (2 : ℚ) * k + 1 ≠ 0 := by
            positivity
          exact hOdd
      · exact ih

/-- The even Bernoulli response and radial orbit factor cannot cancel. -/
theorem q3_source_ray_coefficient_nonzero
    (a r : ℕ → ℚ)
    (hAOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hRZero : r 0 = 1)
    (hRRec :
      ∀ k : ℕ,
        r (k + 1) =
          (9 / 896) * (2 * (k : ℚ) + 1) * r k)
    (m : ℕ) :
    (27 / 12845056) * a (m + 1) * r (2 * m) ≠ 0 := by
  have haPos : 0 < a (m + 1) :=
    positive_even_coefficient_recurrence
      a hAOne hARec (m + 1) (by omega)
  have hr : r (2 * m) ≠ 0 :=
    q3_radial_adjoint_chain_nonzero
      r hRZero hRRec (2 * m)
  exact mul_ne_zero
    (mul_ne_zero (by norm_num) (ne_of_gt haPos))
    hr

/-- At `n = 6 + 4m`, the certified Hamiltonian exponents give source
derivation degree `7n-12` for density exponent two. -/
theorem q3_source_ray_degree_arithmetic (m : ℕ) :
    let n := 6 + 4 * m
    (17 + 16 * m) + (16 + 12 * m) - 3 = 7 * n - 12 := by
  omega

/-- The certified source degrees exceed every natural cap. -/
theorem q3_source_ray_degrees_unbounded (bound : ℕ) :
    bound < 30 + 28 * bound := by
  omega

/-- Aggregated arithmetic endpoint for the symbolic source theorem. -/
theorem q3_source_magnus_escape_arithmetic_terminal_certificate
    (a r : ℕ → ℚ)
    (hAOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hRZero : r 0 = 1)
    (hRRec :
      ∀ k : ℕ,
        r (k + 1) =
          (9 / 896) * (2 * (k : ℚ) + 1) * r k) :
    (∀ m : ℕ, 1 ≤ m → 0 < a m) ∧
      (∀ k : ℕ, r k ≠ 0) ∧
      (∀ m : ℕ,
        (27 / 12845056) * a (m + 1) * r (2 * m) ≠ 0) ∧
      (∀ m : ℕ,
        let n := 6 + 4 * m
        (17 + 16 * m) + (16 + 12 * m) - 3 = 7 * n - 12) ∧
      (∀ bound : ℕ, bound < 30 + 28 * bound) := by
  exact ⟨positive_even_coefficient_recurrence a hAOne hARec,
    q3_radial_adjoint_chain_nonzero r hRZero hRRec,
    q3_source_ray_coefficient_nonzero
      a r hAOne hARec hRZero hRRec,
    q3_source_ray_degree_arithmetic,
    q3_source_ray_degrees_unbounded⟩

end AxiomPackJacobianQ3SourceMagnusEscapeArithmetic
