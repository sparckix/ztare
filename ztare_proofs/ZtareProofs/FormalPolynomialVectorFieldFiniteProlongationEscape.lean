import Mathlib.Algebra.Polynomial.Roots
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialVectorFieldTriangularProlongation

/-!
# Finite escape from a polynomial prolongation tower

The multiplicity-selected triangular prolongation is indexed no later than
the degree of the original polynomial.  Consequently, a common root of all
prolongations through that degree must lie in the equilibrium locus of the
vector field.
-/

namespace FormalPolynomialVectorFieldFiniteProlongationEscape

open Polynomial

open FormalPolynomialVectorFieldMultiplicity
open FormalPolynomialVectorFieldTriangularProlongation

variable {K : Type*} [Field K]

/-- Root multiplicity is bounded by polynomial degree. -/
lemma rootMultiplicity_le_natDegree
    (q : K[X]) (y : K) :
    q.rootMultiplicity y ≤ q.natDegree := by
  classical
  calc
    q.rootMultiplicity y = q.roots.count y := (count_roots q).symm
    _ ≤ q.roots.card := Multiset.count_le_card _ _
    _ ≤ q.natDegree := card_roots' q

/-- Every root outside the equilibrium locus is escaped by one of the first
`natDegree q + 1` triangular prolongations. -/
theorem exists_finite_triangularProlongation_escape
    [CharZero K]
    {p q : K[X]} {jet : ℕ → K} {y : K}
    (hp : p.eval y ≠ 0)
    (hq : q ≠ 0)
    (hjet : jet 0 ≠ 0)
    (hroot : q.IsRoot y) :
    ∃ n ≤ q.natDegree,
      0 < n ∧
      (triangularProlongation p q jet n).eval y ≠ 0 := by
  refine ⟨q.rootMultiplicity y, rootMultiplicity_le_natDegree q y, ?_, ?_⟩
  · exact (rootMultiplicity_pos hq).mpr hroot
  · exact eval_triangularProlongation_rootMultiplicity_ne_zero hp hq hjet

/-- A common root of the finite prolongation family must be an equilibrium
of `p`. -/
theorem commonRoot_finite_triangularProlongations_imp_equilibrium
    [CharZero K]
    {p q : K[X]} {jet : ℕ → K} {y : K}
    (hq : q ≠ 0)
    (hjet : jet 0 ≠ 0)
    (hroot : q.IsRoot y)
    (hall : ∀ n ≤ q.natDegree,
      (triangularProlongation p q jet n).eval y = 0) :
    p.eval y = 0 := by
  by_contra hp
  obtain ⟨n, hn, _hnPositive, hescape⟩ :=
    exists_finite_triangularProlongation_escape hp hq hjet hroot
  exact hescape (hall n hn)

/-- Aggregated finite saturated-prolongation surface. -/
theorem polynomial_vector_field_finite_prolongation_escape_terminal_certificate
    [CharZero K] :
    ∀ (p q : K[X]) (jet : ℕ → K) (y : K),
      q ≠ 0 →
      jet 0 ≠ 0 →
      q.IsRoot y →
      ((p.eval y ≠ 0 →
        ∃ n ≤ q.natDegree,
          0 < n ∧
          (triangularProlongation p q jet n).eval y ≠ 0) ∧
       ((∀ n ≤ q.natDegree,
          (triangularProlongation p q jet n).eval y = 0) →
        p.eval y = 0)) := by
  intro p q jet y hq hjet hroot
  constructor
  · intro hp
    exact exists_finite_triangularProlongation_escape hp hq hjet hroot
  · intro hall
    exact commonRoot_finite_triangularProlongations_imp_equilibrium
      hq hjet hroot hall

end FormalPolynomialVectorFieldFiniteProlongationEscape
