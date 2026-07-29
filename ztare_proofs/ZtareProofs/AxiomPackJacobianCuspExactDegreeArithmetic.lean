import Mathlib

/-!
Arithmetic carrier for the exact ordinary-degree calculation in the
Jacobian cusp-stabilizer cascade.

After removing the alternating sign from the coefficients of

`u' + 2 * x * u'' = -324 * u^2`,

the coefficient recurrence is positive.  This file records that positivity,
the resulting nonvanishing cubic convolution, and the even/odd index
arithmetic behind `3 + k / 2`.

The identification with the Hamiltonian flow of
`C = 4 * P^3 + 27 * Q^2`, coefficient extraction from `u^3`, and the
weighted-support argument for `deg (X_C^[k] B)` are deliberately outside
this arithmetic carrier.
-/

namespace AxiomPackJacobianCuspExactDegreeArithmetic

open scoped BigOperators

noncomputable section

/-- The sign-normalized quadratic coefficient convolution. -/
def quadraticConvolution (b : ℕ → ℚ) (m : ℕ) : ℚ :=
  ∑ i ∈ Finset.range (m + 1), b i * b (m - i)

/-- The sign-normalized cubic coefficient convolution. -/
def cubicConvolution (b : ℕ → ℚ) (m : ℕ) : ℚ :=
  ∑ i ∈ Finset.range (m + 1),
    ∑ j ∈ Finset.range (m - i + 1),
      b i * b j * b (m - i - j)

/-- Restore the alternating sign of the coefficients of `u`. -/
def signedCoefficient (b : ℕ → ℚ) (m : ℕ) : ℚ :=
  (-1 : ℚ) ^ m * b m

/-- The recurrence obeyed by `b m = (-1)^m a_m`. -/
def SatisfiesPositiveRecurrence (b : ℕ → ℚ) : Prop :=
  b 0 = 1 ∧
    ∀ m : ℕ,
      b (m + 1) =
        (324 : ℚ) /
          (((m + 1) * (2 * m + 1) : ℕ) : ℚ) *
            quadraticConvolution b m

theorem quadraticConvolution_pos_of_prefix
    (b : ℕ → ℚ) (m : ℕ)
    (hb : ∀ i ≤ m, 0 < b i) :
    0 < quadraticConvolution b m := by
  rw [quadraticConvolution]
  apply Finset.sum_pos
  · intro i hi
    have hi' : i ≤ m := by
      simpa [Nat.lt_succ_iff] using Finset.mem_range.mp hi
    exact mul_pos (hb i hi') (hb (m - i) (Nat.sub_le m i))
  · simp

theorem positiveRecurrence_pos
    (b : ℕ → ℚ)
    (hrec : SatisfiesPositiveRecurrence b) :
    ∀ m : ℕ, 0 < b m := by
  intro m
  induction m using Nat.strong_induction_on with
  | h m ih =>
      cases m with
      | zero =>
          rw [hrec.1]
          norm_num
      | succ m =>
          rw [hrec.2 m]
          apply mul_pos
          · positivity
          · exact quadraticConvolution_pos_of_prefix b m fun i hi =>
              ih i (Nat.lt_succ_of_le hi)

theorem cubicConvolution_pos
    (b : ℕ → ℚ)
    (hb : ∀ m : ℕ, 0 < b m)
    (m : ℕ) :
    0 < cubicConvolution b m := by
  rw [cubicConvolution]
  apply Finset.sum_pos
  · intro i hi
    apply Finset.sum_pos
    · intro j hj
      exact mul_pos (mul_pos (hb i) (hb j)) (hb (m - i - j))
    · simp
  · simp

theorem cubicConvolution_ne_zero
    (b : ℕ → ℚ)
    (hrec : SatisfiesPositiveRecurrence b)
    (m : ℕ) :
    cubicConvolution b m ≠ 0 :=
  ne_of_gt (cubicConvolution_pos b (positiveRecurrence_pos b hrec) m)

theorem signed_cubic_convolution_eq
    (b : ℕ → ℚ) (m : ℕ) :
    cubicConvolution (signedCoefficient b) m =
      (-1 : ℚ) ^ m * cubicConvolution b m := by
  rw [cubicConvolution, cubicConvolution, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro i hi
  have hi' : i ≤ m := by
    simpa [Nat.lt_succ_iff] using Finset.mem_range.mp hi
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro j hj
  have hj' : j ≤ m - i := by
    simpa [Nat.lt_succ_iff] using Finset.mem_range.mp hj
  have hsum : i + j + (m - i - j) = m := by
    omega
  calc
    signedCoefficient b i * signedCoefficient b j *
          signedCoefficient b (m - i - j) =
        (((-1 : ℚ) ^ i * (-1 : ℚ) ^ j *
            (-1 : ℚ) ^ (m - i - j)) *
          (b i * b j * b (m - i - j))) := by
            simp only [signedCoefficient]
            ring
    _ = (-1 : ℚ) ^ m * (b i * b j * b (m - i - j)) := by
      rw [← pow_add, ← pow_add, hsum]

theorem signed_cubic_convolution_ne_zero
    (b : ℕ → ℚ)
    (hrec : SatisfiesPositiveRecurrence b)
    (m : ℕ) :
    cubicConvolution (signedCoefficient b) m ≠ 0 := by
  rw [signed_cubic_convolution_eq]
  exact mul_ne_zero (pow_ne_zero _ (by norm_num))
    (cubicConvolution_ne_zero b hrec m)

theorem even_degree_index (m : ℕ) :
    3 + (2 * m) / 2 = m + 3 := by
  omega

theorem odd_degree_index (m : ℕ) :
    3 + (2 * m + 1) / 2 = m + 3 := by
  omega

/-- Terminal arithmetic certificate used by the exact-degree pencil proof. -/
theorem cusp_exact_degree_arithmetic_terminal_certificate :
    (∀ (b : ℕ → ℚ),
      SatisfiesPositiveRecurrence b →
        (∀ m : ℕ, 0 < b m)) ∧
    (∀ (b : ℕ → ℚ),
      SatisfiesPositiveRecurrence b →
        ∀ m : ℕ,
          cubicConvolution b m ≠ 0 ∧
            cubicConvolution (signedCoefficient b) m ≠ 0 ∧
            cubicConvolution (signedCoefficient b) m =
              (-1 : ℚ) ^ m * cubicConvolution b m) ∧
    (∀ m : ℕ,
      3 + (2 * m) / 2 = m + 3 ∧
        3 + (2 * m + 1) / 2 = m + 3) := by
  refine ⟨positiveRecurrence_pos, ?_, ?_⟩
  · intro b hrec m
    exact ⟨cubicConvolution_ne_zero b hrec m,
      signed_cubic_convolution_ne_zero b hrec m,
      signed_cubic_convolution_eq b m⟩
  intro m
  exact ⟨even_degree_index m, odd_degree_index m⟩

end

end AxiomPackJacobianCuspExactDegreeArithmetic
