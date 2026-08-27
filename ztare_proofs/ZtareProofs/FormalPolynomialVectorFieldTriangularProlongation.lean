import Mathlib.Tactic
import ZtareProofs.FormalPolynomialVectorFieldMultiplicity

/-!
# Triangular prolongations of a polynomial vector field

On an invariant parameter divisor, a commuting source derivation and the
hidden vector-field derivation expand binomially.  At a root of multiplicity
`m`, every term below `D_p^m` vanishes, so the terminal value depends only on
the zeroth source jet.
-/

namespace FormalPolynomialVectorFieldTriangularProlongation

open Finset Polynomial

open FormalPolynomialVectorFieldMultiplicity

variable {K : Type*} [Field K] [CharZero K]

/-- The polynomial-valued binomial prolongation with arbitrary scalar source
jets. -/
noncomputable def triangularProlongation
    (p q : K[X]) (jet : ℕ → K) (n : ℕ) : K[X] :=
  ∑ j ∈ range (n + 1),
    C (((n.choose j : ℕ) : K) * jet (n - j)) *
      (vectorFieldDerivative p)^[j] q

/-- At the original root multiplicity, all lower triangular terms vanish and
the unique surviving coefficient is the zeroth source jet. -/
theorem eval_triangularProlongation_rootMultiplicity
    {p q : K[X]} {jet : ℕ → K} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0) :
    (triangularProlongation p q jet (q.rootMultiplicity y)).eval y =
      jet 0 *
        ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).eval y := by
  have hmMem : q.rootMultiplicity y ∈
      range (q.rootMultiplicity y + 1) :=
    mem_range.mpr (Nat.lt_succ_self _)
  rw [triangularProlongation, eval_finset_sum,
    sum_eq_single_of_mem (q.rootMultiplicity y) hmMem]
  · simp only [eval_mul, eval_C, Nat.choose_self, Nat.cast_one, one_mul,
      Nat.sub_self]
  · intro j hj hjne
    have hjle : j ≤ q.rootMultiplicity y := by
      have hjrange := mem_range.mp hj
      omega
    have hjlt : j < q.rootMultiplicity y := lt_of_le_of_ne hjle hjne
    have hroot :=
      isRoot_iterate_vectorFieldDerivative_of_lt_rootMultiplicity
        hp hq hjlt
    have heval : ((vectorFieldDerivative p)^[j] q).eval y = 0 := hroot
    rw [eval_mul, eval_C, heval, mul_zero]

/-- Arbitrary higher source jets cannot cancel the terminal multiplicity-
peeling term. -/
theorem eval_triangularProlongation_rootMultiplicity_ne_zero
    {p q : K[X]} {jet : ℕ → K} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hjet : jet 0 ≠ 0) :
    (triangularProlongation p q jet (q.rootMultiplicity y)).eval y ≠ 0 := by
  rw [eval_triangularProlongation_rootMultiplicity hp hq]
  exact mul_ne_zero hjet
    (eval_iterate_vectorFieldDerivative_rootMultiplicity_ne_zero hp hq)

/-- Aggregated commuting-prolongation terminal. -/
theorem polynomial_vector_field_triangular_prolongation_terminal_certificate :
    ∀ (p q : K[X]) (jet : ℕ → K) (y : K),
      p.eval y ≠ 0 →
      q ≠ 0 →
      jet 0 ≠ 0 →
      (triangularProlongation p q jet (q.rootMultiplicity y)).eval y =
        jet 0 *
          ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).eval y ∧
      (triangularProlongation p q jet
        (q.rootMultiplicity y)).eval y ≠ 0 := by
  intro p q jet y hp hq hjet
  constructor
  · exact eval_triangularProlongation_rootMultiplicity hp hq
  · exact eval_triangularProlongation_rootMultiplicity_ne_zero hp hq hjet

end FormalPolynomialVectorFieldTriangularProlongation
