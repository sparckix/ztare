import ZtareProofs.AxiomPackJacobianDivisorMagnusEscape

/-!
Arithmetic endpoint for the sharp source rate of the minimum-weight
`P^2 Q` cancellation.

The symbolic Hamiltonian certificate supplies:

* logarithmic orders `n = 6 + 4m`;
* a normalized coefficient proportional to `B_(2m+2)/(2m+2)!`;
* the radial recurrence
  `r (k+1) = (-325/896) * (2k-3) * r k`; and
* Hamiltonian exponents `(11+10m,10+6m)`.

This file checks noncancellation, degree arithmetic, and unboundedness.  It
does not encode the filtered Hamiltonian quotient or the right-`dexp`
elimination.
-/

namespace AxiomPackJacobianP2QMagnusRateArithmetic

open scoped BigOperators

open AxiomPackJacobianDivisorMagnusEscape

/-- Every multiplier in the `h=5`, excess-minus-seven radial orbit is
nonzero. -/
theorem p2q_radial_adjoint_chain_nonzero
    (r : ℕ → ℚ)
    (hZero : r 0 = 1)
    (hRec :
      ∀ k : ℕ,
        r (k + 1) =
          (-325 / 896) * (2 * (k : ℚ) - 3) * r k) :
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
        · have hOdd : (2 : ℚ) * k ≠ 3 := by
            exact_mod_cast (by omega : 2 * k ≠ 3)
          exact sub_ne_zero.mpr hOdd
      · exact ih

/-- The even Bernoulli response and radial orbit factor cannot cancel. -/
theorem p2q_source_ray_coefficient_nonzero
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
          (-325 / 896) * (2 * (k : ℚ) - 3) * r k)
    (m : ℕ) :
    (13 / 1872) * a (m + 1) * r (2 * m + 2) ≠ 0 := by
  have haPos : 0 < a (m + 1) :=
    positive_even_coefficient_recurrence
      a hAOne hARec (m + 1) (by omega)
  have hr : r (2 * m + 2) ≠ 0 :=
    p2q_radial_adjoint_chain_nonzero
      r hRZero hRRec (2 * m + 2)
  exact mul_ne_zero
    (mul_ne_zero (by norm_num) (ne_of_gt haPos))
    hr

/-- At `n = 6 + 4m`, the certified Hamiltonian exponent gives source
derivation degree `4n-6` for density exponent two. -/
theorem p2q_source_ray_degree_arithmetic (m : ℕ) :
    let n := 6 + 4 * m
    (11 + 10 * m) + (10 + 6 * m) - 3 = 4 * n - 6 := by
  omega

/-- The certified source degrees exceed every natural cap. -/
theorem p2q_source_ray_degrees_unbounded (bound : ℕ) :
    bound < 4 * (6 + 4 * bound) - 6 := by
  omega

/-- Aggregated arithmetic endpoint for the symbolic `P^2 Q` theorem. -/
theorem p2q_magnus_rate_arithmetic_terminal_certificate
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
          (-325 / 896) * (2 * (k : ℚ) - 3) * r k) :
    (∀ m : ℕ, 1 ≤ m → 0 < a m) ∧
      (∀ k : ℕ, r k ≠ 0) ∧
      (∀ m : ℕ,
        (13 / 1872) * a (m + 1) * r (2 * m + 2) ≠ 0) ∧
      (∀ m : ℕ,
        let n := 6 + 4 * m
        (11 + 10 * m) + (10 + 6 * m) - 3 = 4 * n - 6) ∧
      (∀ bound : ℕ, bound < 4 * (6 + 4 * bound) - 6) := by
  exact ⟨positive_even_coefficient_recurrence a hAOne hARec,
    p2q_radial_adjoint_chain_nonzero r hRZero hRRec,
    p2q_source_ray_coefficient_nonzero
      a r hAOne hARec hRZero hRRec,
    p2q_source_ray_degree_arithmetic,
    p2q_source_ray_degrees_unbounded⟩

end AxiomPackJacobianP2QMagnusRateArithmetic
