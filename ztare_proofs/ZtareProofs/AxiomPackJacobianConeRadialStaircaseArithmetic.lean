import Mathlib

/-!
Arithmetic endpoint for the coefficientwise-finite radial cone staircase.

The symbolic certificate supplies the two-layer family identity, the
triangular radial solve, and the normal-layer coefficient bound.  This file
checks:

* six infinite families of cone weights;
* the target-degree consequence of the cone weight bound;
* the higher-normal slope-two inequality;
* the first-normal slope-two inequality; and
* the Hamiltonian-to-vector degree translation.

It does not encode the polynomial radial division or the formal Magnus
group.
-/

namespace AxiomPackJacobianConeRadialStaircaseArithmetic

def coneWeight (a b : ℕ) : ℕ := 2 * a + 3 * b

/-- Weights divisible by six occur in the cone. -/
theorem cone_weight_mod_zero (k : ℕ) :
    coneWeight 0 (2 * (k + 1)) = 6 * (k + 1) ∧
      1 ≤ 2 * (k + 1) ∧
      0 ≤ 2 * (2 * (k + 1)) := by
  simp [coneWeight]
  omega

/-- Weights congruent to one modulo six, starting at seven, occur in the
cone. -/
theorem cone_weight_mod_one (k : ℕ) :
    coneWeight 2 (2 * k + 1) = 6 * k + 7 ∧
      1 ≤ 2 * k + 1 ∧
      2 ≤ 2 * (2 * k + 1) := by
  simp [coneWeight]
  omega

/-- Weights congruent to two modulo six, starting at eight, occur in the
cone. -/
theorem cone_weight_mod_two (k : ℕ) :
    coneWeight 1 (2 * (k + 1)) = 6 * k + 8 ∧
      1 ≤ 2 * (k + 1) ∧
      1 ≤ 2 * (2 * (k + 1)) := by
  simp [coneWeight]
  omega

/-- Weights congruent to three modulo six, starting at nine, occur in the
target-lift-compatible cone.  The excluded lower value is the bare
Hamiltonian `Q`, of weight three. -/
theorem cone_weight_mod_three (k : ℕ) :
    coneWeight 0 (2 * k + 3) = 6 * k + 9 ∧
      3 ≤ 2 * k + 3 ∧
      0 ≤ 2 * (2 * k + 3) := by
  simp [coneWeight]
  omega

/-- Weights congruent to four modulo six, starting at ten, occur in the
cone. -/
theorem cone_weight_mod_four (k : ℕ) :
    coneWeight 2 (2 * (k + 1)) = 6 * k + 10 ∧
      1 ≤ 2 * (k + 1) ∧
      2 ≤ 2 * (2 * (k + 1)) := by
  simp [coneWeight]
  omega

/-- Weights congruent to five modulo six occur in the cone. -/
theorem cone_weight_mod_five (k : ℕ) :
    coneWeight 1 (2 * k + 1) = 6 * k + 5 ∧
      1 ≤ 2 * k + 1 ∧
      1 ≤ 2 * (2 * k + 1) := by
  simp [coneWeight]
  omega

/-- A row weight at most `n+6` has target Hamiltonian degree at most
`n+3`. -/
theorem cone_target_degree_bound
    (n a b : ℕ)
    (hWeight : coneWeight a b ≤ n + 6) :
    a + b ≤ n + 3 := by
  unfold coneWeight at hWeight
  omega

/-- Every normal layer of order at least two lies in the source
slope-two Hamiltonian envelope. -/
theorem higher_normal_rees_bound
    (n j a : ℕ)
    (hNormal : 2 ≤ j)
    (hRadial : a + 2 * j ≤ n + 6) :
    2 * a + j ≤ 2 * n + 6 := by
  omega

/-- The tangency-controlled first-normal layer lies in the same envelope. -/
theorem first_normal_rees_bound
    (n a : ℕ)
    (hRadial : a ≤ n + 2) :
    2 * a + 1 ≤ 2 * n + 6 := by
  omega

/-- The Hamiltonian bound at velocity coefficient `s^n` becomes the shifted
source-vector bound at logarithmic order `q=n+1`. -/
theorem source_vector_degree_arithmetic (n : ℕ) :
    (2 * n + 6) - 3 = 2 * (n + 1) + 1 := by
  omega

/-- The source excess at logarithmic order `q=n+1` is at most `2q`. -/
theorem source_excess_rate_two_arithmetic (n : ℕ) :
    (2 * (n + 1) + 1) - 1 = 2 * (n + 1) := by
  omega

/-- Aggregated arithmetic endpoint for the triangular staircase. -/
theorem cone_radial_staircase_arithmetic_terminal_certificate :
    (∀ k : ℕ,
      coneWeight 0 (2 * (k + 1)) = 6 * (k + 1)) ∧
    (∀ k : ℕ,
      coneWeight 2 (2 * k + 1) = 6 * k + 7) ∧
    (∀ k : ℕ,
      coneWeight 1 (2 * (k + 1)) = 6 * k + 8) ∧
    (∀ k : ℕ,
      coneWeight 0 (2 * k + 3) = 6 * k + 9) ∧
    (∀ k : ℕ,
      coneWeight 2 (2 * (k + 1)) = 6 * k + 10) ∧
    (∀ k : ℕ,
      coneWeight 1 (2 * k + 1) = 6 * k + 5) ∧
    (∀ n a b : ℕ,
      coneWeight a b ≤ n + 6 → a + b ≤ n + 3) ∧
    (∀ n j a : ℕ,
      2 ≤ j → a + 2 * j ≤ n + 6 →
        2 * a + j ≤ 2 * n + 6) ∧
    (∀ n a : ℕ,
      a ≤ n + 2 → 2 * a + 1 ≤ 2 * n + 6) ∧
    (∀ n : ℕ,
      (2 * n + 6) - 3 = 2 * (n + 1) + 1) := by
  exact ⟨fun k => (cone_weight_mod_zero k).1,
    fun k => (cone_weight_mod_one k).1,
    fun k => (cone_weight_mod_two k).1,
    fun k => (cone_weight_mod_three k).1,
    fun k => (cone_weight_mod_four k).1,
    fun k => (cone_weight_mod_five k).1,
    cone_target_degree_bound,
    higher_normal_rees_bound,
    first_normal_rees_bound,
    source_vector_degree_arithmetic⟩

end AxiomPackJacobianConeRadialStaircaseArithmetic
