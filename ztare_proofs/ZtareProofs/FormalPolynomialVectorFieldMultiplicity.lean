import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Tactic

/-!
# Root multiplicity under a polynomial vector-field derivation

For `D_p(Q) = p * Q'`, a root away from the equilibrium locus of `p` loses
exactly one unit of multiplicity at each iteration.  Thus the iterate indexed
by the original multiplicity evaluates nontrivially at the root.

This is a substrate-neutral algebraic kernel.  It does not identify a
particular differential-resultant tower with these iterates and does not
classify components contained in the equilibrium locus of `p`.
-/

namespace FormalPolynomialVectorFieldMultiplicity

open Polynomial

variable {K : Type*} [Field K] [CharZero K]

/-- Polynomial vector-field derivation `Q ↦ p Q'`. -/
noncomputable def vectorFieldDerivative (p q : K[X]) : K[X] :=
  p * q.derivative

/-- At a live root, applying the vector-field derivation preserves
nonzeroness. -/
theorem vectorFieldDerivative_ne_zero_of_isRoot
    {p q : K[X]} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hroot : q.IsRoot y) :
    vectorFieldDerivative p q ≠ 0 := by
  have hpPolynomial : p ≠ 0 := by
    intro hpZero
    apply hp
    simp [hpZero]
  have hqDerivative : q.derivative ≠ 0 := by
    intro hderivative
    have hconstant : q = C (q.coeff 0) :=
      eq_C_of_derivative_eq_zero hderivative
    have hconstantZero : q.coeff 0 = 0 := by
      rw [hconstant] at hroot
      simpa only [IsRoot, eval_C] using hroot
    apply hq
    rw [hconstant, hconstantZero, map_zero]
  exact mul_ne_zero hpPolynomial hqDerivative

/-- One application of `D_p` lowers the root multiplicity exactly by one
away from the zero set of `p`. -/
theorem rootMultiplicity_vectorFieldDerivative_of_isRoot
    {p q : K[X]} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hroot : q.IsRoot y) :
    (vectorFieldDerivative p q).rootMultiplicity y =
      q.rootMultiplicity y - 1 := by
  have hproduct := vectorFieldDerivative_ne_zero_of_isRoot hp hq hroot
  have hpNotRoot : ¬p.IsRoot y := by
    simpa only [IsRoot] using hp
  rw [vectorFieldDerivative, rootMultiplicity_mul hproduct,
    rootMultiplicity_eq_zero hpNotRoot,
    derivative_rootMultiplicity_of_root hroot, zero_add]

/-- Through the original root multiplicity, every `D_p` iterate is nonzero
and its multiplicity is the expected truncated subtraction. -/
theorem iterate_vectorFieldDerivative_ne_zero_and_rootMultiplicity
    {p q : K[X]} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0) :
    ∀ n ≤ q.rootMultiplicity y,
      (vectorFieldDerivative p)^[n] q ≠ 0 ∧
      ((vectorFieldDerivative p)^[n] q).rootMultiplicity y =
        q.rootMultiplicity y - n := by
  intro n hn
  induction n with
  | zero =>
      constructor
      · simpa only [Function.iterate_zero_apply] using hq
      · simp only [Function.iterate_zero_apply, Nat.sub_zero]
  | succ n inductionHypothesis =>
      have hnWeak : n ≤ q.rootMultiplicity y :=
        le_trans (Nat.le_succ n) hn
      obtain ⟨hiterate, hmultiplicity⟩ := inductionHypothesis hnWeak
      have hnStrict : n < q.rootMultiplicity y :=
        Nat.lt_of_succ_le hn
      have hpositive :
          0 < ((vectorFieldDerivative p)^[n] q).rootMultiplicity y := by
        rw [hmultiplicity]
        exact Nat.sub_pos_of_lt hnStrict
      have hroot : ((vectorFieldDerivative p)^[n] q).IsRoot y :=
        (rootMultiplicity_pos hiterate).mp hpositive
      have hnextNonzero :=
        vectorFieldDerivative_ne_zero_of_isRoot hp hiterate hroot
      have hnextMultiplicity :=
        rootMultiplicity_vectorFieldDerivative_of_isRoot hp hiterate hroot
      rw [Function.iterate_succ_apply']
      constructor
      · exact hnextNonzero
      · rw [hnextMultiplicity, hmultiplicity]
        omega

/-- Every iterate strictly below the multiplicity still vanishes at the
selected root. -/
theorem isRoot_iterate_vectorFieldDerivative_of_lt_rootMultiplicity
    {p q : K[X]} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    {n : ℕ}
    (hn : n < q.rootMultiplicity y) :
    ((vectorFieldDerivative p)^[n] q).IsRoot y := by
  obtain ⟨hiterate, hmultiplicity⟩ :=
    iterate_vectorFieldDerivative_ne_zero_and_rootMultiplicity hp hq n hn.le
  apply (rootMultiplicity_pos hiterate).mp
  rw [hmultiplicity]
  exact Nat.sub_pos_of_lt hn

/-- The iterate indexed by the original multiplicity escapes the selected
root. -/
theorem eval_iterate_vectorFieldDerivative_rootMultiplicity_ne_zero
    {p q : K[X]} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0) :
    ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).eval y ≠ 0 := by
  obtain ⟨hiterate, hmultiplicity⟩ :=
    iterate_vectorFieldDerivative_ne_zero_and_rootMultiplicity hp hq
      (q.rootMultiplicity y) le_rfl
  intro heval
  have hroot :
      ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).IsRoot y :=
    heval
  have hpositive := (rootMultiplicity_pos hiterate).mpr hroot
  rw [hmultiplicity, Nat.sub_self] at hpositive
  exact (Nat.not_lt_zero 0) hpositive

/-- Aggregated all-multiplicity peeling surface. -/
theorem polynomial_vector_field_multiplicity_terminal_certificate :
    ∀ (p q : K[X]) (y : K),
      p.eval y ≠ 0 →
      q ≠ 0 →
      (∀ n ≤ q.rootMultiplicity y,
        (vectorFieldDerivative p)^[n] q ≠ 0 ∧
        ((vectorFieldDerivative p)^[n] q).rootMultiplicity y =
          q.rootMultiplicity y - n) ∧
      (∀ n < q.rootMultiplicity y,
        ((vectorFieldDerivative p)^[n] q).IsRoot y) ∧
      ((vectorFieldDerivative p)^[q.rootMultiplicity y] q).eval y ≠ 0 := by
  intro p q y hp hq
  refine ⟨?_, ?_, ?_⟩
  · exact iterate_vectorFieldDerivative_ne_zero_and_rootMultiplicity hp hq
  · intro n hn
    exact isRoot_iterate_vectorFieldDerivative_of_lt_rootMultiplicity
      hp hq hn
  · exact eval_iterate_vectorFieldDerivative_rootMultiplicity_ne_zero hp hq

end FormalPolynomialVectorFieldMultiplicity
