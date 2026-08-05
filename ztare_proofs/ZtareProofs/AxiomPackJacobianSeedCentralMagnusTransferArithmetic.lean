import ZtareProofs.AxiomPackJacobianDivisorMagnusEscape

/-!
Arithmetic endpoint for the seed-central Magnus transfer.

The symbolic Hamiltonian certificate supplies:

* logarithmic orders `n = 6 + 4m`;
* a terminal right-Magnus response with nonzero even-Bernoulli factor;
* a first corrected orbit coefficient `9/917504`; and
* the later adjoint recurrence
  `r (k+1) = (-27/114688) * (2k-1) * r k`.

This file checks recurrence nonvanishing and the source-degree arithmetic.
It does not encode the Hamiltonian quotient or its finite-core projection.
-/

namespace AxiomPackJacobianSeedCentralMagnusTransferArithmetic

open scoped BigOperators

open AxiomPackJacobianDivisorMagnusEscape

/-- The transferred radial adjoint orbit is nonzero from its first terminal
iterate onward. -/
theorem seed_central_adjoint_chain_nonzero
    (r : ℕ → ℚ)
    (hOne : r 1 = 9 / 917504)
    (hRec :
      ∀ k : ℕ, 1 ≤ k →
        r (k + 1) =
          (-27 / 114688) * (2 * (k : ℚ) - 1) * r k) :
    ∀ k : ℕ, 1 ≤ k → r k ≠ 0 := by
  intro k hk
  obtain ⟨j, rfl⟩ := Nat.exists_eq_add_of_le hk
  induction j with
  | zero =>
      rw [hOne]
      norm_num
  | succ j ih =>
      change r ((1 + j) + 1) ≠ 0
      rw [hRec (1 + j) (by omega)]
      apply mul_ne_zero
      · apply mul_ne_zero
        · norm_num
        · have hTwoK :
              (2 : ℚ) * ((1 + j : ℕ) : ℚ) ≠ 1 := by
            exact_mod_cast (by omega : 2 * (1 + j) ≠ 1)
          exact sub_ne_zero.mpr hTwoK
      · exact ih (by omega)

/-- The even Bernoulli response and transferred orbit factor cannot cancel. -/
theorem seed_central_ray_coefficient_nonzero
    (a r : ℕ → ℚ)
    (hAOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hROne : r 1 = 9 / 917504)
    (hRRec :
      ∀ k : ℕ, 1 ≤ k →
        r (k + 1) =
          (-27 / 114688) * (2 * (k : ℚ) - 1) * r k)
    (m : ℕ) :
    (a (m + 1) / 2) * r (2 * m + 1) ≠ 0 := by
  have haPos : 0 < a (m + 1) :=
    positive_even_coefficient_recurrence
      a hAOne hARec (m + 1) (by omega)
  have hr : r (2 * m + 1) ≠ 0 :=
    seed_central_adjoint_chain_nonzero
      r hROne hRRec (2 * m + 1) (by omega)
  exact mul_ne_zero
    (div_ne_zero (ne_of_gt haPos) (by norm_num))
    hr

/-- At `n = 6 + 4m`, exponents `(23+22m,22+18m)` give source derivation
degree `10n-18` for density exponent two. -/
theorem seed_central_ray_degree_arithmetic (m : ℕ) :
    let n := 6 + 4 * m
    (23 + 22 * m) + (22 + 18 * m) - 3 = 10 * n - 18 := by
  omega

/-- The certified transferred source degrees exceed every natural cap. -/
theorem seed_central_ray_degrees_unbounded (bound : ℕ) :
    bound < 42 + 40 * bound := by
  omega

/-- Aggregated arithmetic endpoint for the seed-central symbolic theorem. -/
theorem seed_central_magnus_transfer_arithmetic_terminal_certificate
    (a r : ℕ → ℚ)
    (hAOne : a 1 = 1 / 12)
    (hARec :
      ∀ m : ℕ, 2 ≤ m →
        a m =
          (∑ i ∈ Finset.Icc 1 (m - 1), a i * a (m - i)) /
            (2 * (m : ℚ) + 1))
    (hROne : r 1 = 9 / 917504)
    (hRRec :
      ∀ k : ℕ, 1 ≤ k →
        r (k + 1) =
          (-27 / 114688) * (2 * (k : ℚ) - 1) * r k) :
    (∀ m : ℕ, 1 ≤ m → 0 < a m) ∧
      (∀ k : ℕ, 1 ≤ k → r k ≠ 0) ∧
      (∀ m : ℕ,
        (a (m + 1) / 2) * r (2 * m + 1) ≠ 0) ∧
      (∀ m : ℕ,
        let n := 6 + 4 * m
        (23 + 22 * m) + (22 + 18 * m) - 3 = 10 * n - 18) ∧
      (∀ bound : ℕ, bound < 42 + 40 * bound) := by
  exact ⟨positive_even_coefficient_recurrence a hAOne hARec,
    seed_central_adjoint_chain_nonzero r hROne hRRec,
    seed_central_ray_coefficient_nonzero
      a r hAOne hARec hROne hRRec,
    seed_central_ray_degree_arithmetic,
    seed_central_ray_degrees_unbounded⟩

end AxiomPackJacobianSeedCentralMagnusTransferArithmetic
