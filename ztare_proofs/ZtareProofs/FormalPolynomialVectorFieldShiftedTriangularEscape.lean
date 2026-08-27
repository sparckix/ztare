import Mathlib.Tactic
import ZtareProofs.FormalPolynomialVectorFieldFiniteProlongationEscape

/-!
# Shifted escape for a triangular polynomial prolongation

The existing finite-escape theorem assumes that the zeroth scalar source jet
is nonzero.  More generally, let `r` be the first nonzero jet and let `m` be
the root multiplicity of the hidden polynomial.  In prolongation order
`r + m`, every summand except the `m`-th vector-field derivative vanishes:
lower derivatives still vanish at the root, while higher derivatives carry a
source jet below `r`.

This is the finite induction step needed when a normalized differential
relation has a delayed, but nonflat, scalar coefficient.
-/

namespace FormalPolynomialVectorFieldShiftedTriangularEscape

open Finset Polynomial

open FormalPolynomialVectorFieldFiniteProlongationEscape
open FormalPolynomialVectorFieldMultiplicity
open FormalPolynomialVectorFieldTriangularProlongation

variable {K : Type*} [Field K] [CharZero K]

/-- At the first nonzero source jet shifted by root multiplicity, exactly one
triangular summand survives. -/
theorem eval_triangularProlongation_firstNonzeroJet_add_rootMultiplicity
    {p q : K[X]} {jet : ℕ → K} {y : K} {r : ℕ}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hfirst : ∀ k < r, jet k = 0) :
    (triangularProlongation p q jet (r + q.rootMultiplicity y)).eval y =
      (((r + q.rootMultiplicity y).choose (q.rootMultiplicity y) : ℕ) : K) *
        jet r *
          ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).eval y := by
  let m := q.rootMultiplicity y
  have hmMem : m ∈ range (r + m + 1) := mem_range.mpr (by omega)
  rw [triangularProlongation, eval_finset_sum,
    sum_eq_single_of_mem m hmMem]
  · simp only [eval_mul, eval_C]
    have hsub : r + m - m = r := by omega
    rw [hsub]
  · intro j hj hjne
    have hjle : j ≤ r + m := by
      have hjrange := mem_range.mp hj
      omega
    by_cases hjm : j < m
    · have hroot :=
        isRoot_iterate_vectorFieldDerivative_of_lt_rootMultiplicity
          hp hq hjm
      have heval : ((vectorFieldDerivative p)^[j] q).eval y = 0 := hroot
      rw [eval_mul, eval_C, heval, mul_zero]
    · have hmj : m < j := lt_of_le_of_ne (Nat.le_of_not_gt hjm) (Ne.symm hjne)
      have hindex : r + m - j < r := by omega
      rw [eval_mul, eval_C, hfirst _ hindex, mul_zero, zero_mul]

/-- The shifted survivor is nonzero in characteristic zero. -/
theorem eval_triangularProlongation_firstNonzeroJet_add_rootMultiplicity_ne_zero
    {p q : K[X]} {jet : ℕ → K} {y : K} {r : ℕ}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hjet : jet r ≠ 0)
    (hfirst : ∀ k < r, jet k = 0) :
    (triangularProlongation p q jet (r + q.rootMultiplicity y)).eval y ≠ 0 := by
  rw [eval_triangularProlongation_firstNonzeroJet_add_rootMultiplicity
    hp hq hfirst]
  have hchooseNat :
      0 < (r + q.rootMultiplicity y).choose (q.rootMultiplicity y) :=
    Nat.choose_pos (by omega)
  have hchoose :
      ((((r + q.rootMultiplicity y).choose
          (q.rootMultiplicity y) : ℕ) : K)) ≠ 0 := by
    exact_mod_cast hchooseNat.ne'
  exact mul_ne_zero (mul_ne_zero hchoose hjet)
    (eval_iterate_vectorFieldDerivative_rootMultiplicity_ne_zero hp hq)

/-- Escape occurs no later than the first nonzero jet index plus the hidden
polynomial degree. -/
theorem exists_shifted_finite_triangularProlongation_escape
    {p q : K[X]} {jet : ℕ → K} {y : K} {r : ℕ}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hjet : jet r ≠ 0)
    (hfirst : ∀ k < r, jet k = 0) :
    ∃ n ≤ r + q.natDegree,
      (triangularProlongation p q jet n).eval y ≠ 0 := by
  refine ⟨r + q.rootMultiplicity y, ?_, ?_⟩
  · exact Nat.add_le_add_left (rootMultiplicity_le_natDegree q y) r
  · exact
      eval_triangularProlongation_firstNonzeroJet_add_rootMultiplicity_ne_zero
        hp hq hjet hfirst

/-- Aggregated shifted finite-prolongation certificate. -/
theorem polynomial_vector_field_shifted_triangular_escape_terminal_certificate :
    ∀ (p q : K[X]) (jet : ℕ → K) (y : K) (r : ℕ),
      p.eval y ≠ 0 →
      q ≠ 0 →
      jet r ≠ 0 →
      (∀ k < r, jet k = 0) →
      (triangularProlongation p q jet
          (r + q.rootMultiplicity y)).eval y =
        (((r + q.rootMultiplicity y).choose
            (q.rootMultiplicity y) : ℕ) : K) *
          jet r *
            ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).eval y ∧
      (triangularProlongation p q jet
          (r + q.rootMultiplicity y)).eval y ≠ 0 ∧
      ∃ n ≤ r + q.natDegree,
        (triangularProlongation p q jet n).eval y ≠ 0 := by
  intro p q jet y r hp hq hjet hfirst
  exact ⟨
    eval_triangularProlongation_firstNonzeroJet_add_rootMultiplicity
      hp hq hfirst,
    eval_triangularProlongation_firstNonzeroJet_add_rootMultiplicity_ne_zero
      hp hq hjet hfirst,
    exists_shifted_finite_triangularProlongation_escape
      hp hq hjet hfirst⟩

end FormalPolynomialVectorFieldShiftedTriangularEscape
