import Mathlib.Tactic
import ZtareProofs.FormalCoupledJuliaElimination
import ZtareProofs.FormalDerivationIteratedLeibniz
import ZtareProofs.FormalDifferentialPolynomialInvariantSpecialization
import ZtareProofs.FormalPolynomialVectorFieldTriangularProlongation

/-!
# All-order specialization of the normalized coupled-Julia relation

For a tangent outer generator `q(F) = F^2 qTail(F)`, the division-free
coupled-Julia relation has a canonical factor `F`.  After removing it, the
special fiber is `-a₀ q(Y)`.  The invariant-divisor total-derivation theorem
and the general iterated Leibniz rule identify every specialized prolongation
with the triangular vector-field family.

This file proves only the algebraic specialization.  It does not promote an
empty special fiber to an endpoint eliminant and does not classify dominant
components.
-/

namespace FormalCoupledJuliaAllOrderSpecialization

open Finset Polynomial

open FormalCoupledJuliaElimination
open FormalDerivationIteratedLeibniz
open FormalDifferentialPolynomialInvariantSpecialization
open FormalPolynomialVectorFieldMultiplicity
open FormalPolynomialVectorFieldTriangularProlongation

variable {K : Type*} [Field K] [CharZero K]

/-- The coupled relation after the source-dependent scalar product has been
named `a0`.  The first copy of `q` is evaluated at the visible variable; the
second is the hidden polynomial. -/
noncomputable def actualCoupledRelation
    (p q : K[X]) (a0 : K) : K[X][X] :=
  C q * p.map C - C (X * C a0) * q.map C

/-- Remove the visible factor forced by `q(F) = F^2 qTail(F)`. -/
noncomputable def normalizedCoupledRelation
    (p q qTail : K[X]) (a0 : K) : K[X][X] :=
  C (X * qTail) * p.map C - C (C a0) * q.map C

/-- A tangent polynomial generator has a canonically usable quadratic
factor; the tail is constructed from its first two vanishing coefficients. -/
theorem exists_tangentGenerator_tail
    (q : K[X])
    (hzero : q.coeff 0 = 0)
    (hone : q.coeff 1 = 0) :
    ∃ qTail, q = X ^ 2 * qTail := by
  have hdvd : X ^ 2 ∣ q := by
    rw [X_pow_dvd_iff]
    intro degree hdegree
    interval_cases degree
    · exact hzero
    · exact hone
  exact hdvd

/-- The explicit relation constructed by the Julia-elimination kernel becomes
`actualCoupledRelation` once the source scalar product is named `a0`. -/
theorem hiddenRelationPolynomial_eq_actualCoupledRelation
    (p q : K[X]) (source coefficient : K[X]) (a0 : K)
    (hsource : coefficient * (p.map C).eval source = C a0) :
    hiddenRelationPolynomial (p.map C) (q.map C) source X coefficient =
      actualCoupledRelation p q a0 := by
  rw [hiddenRelationPolynomial, actualCoupledRelation]
  simp only [eval_map, eval₂_C_X]
  have hsource' : coefficient * eval₂ C source p = C a0 := by
    simpa only [eval_map] using hsource
  have hcoefficient :
      coefficient * X * eval₂ C source p = X * C a0 := by
    calc
      coefficient * X * eval₂ C source p =
          X * (coefficient * eval₂ C source p) := by ring
      _ = X * C a0 := by rw [hsource']
  rw [hcoefficient]

/-- Tangency gives the exact visible factorization of the actual relation. -/
theorem actualCoupledRelation_eq_X_mul_normalized
    (p q qTail : K[X]) (a0 : K)
    (htangent : q = X ^ 2 * qTail) :
    actualCoupledRelation p q a0 =
      C X * normalizedCoupledRelation p q qTail a0 := by
  rw [actualCoupledRelation, normalizedCoupledRelation, htangent]
  simp only [map_mul, map_pow, map_X, map_C]
  ring

/-- The normalized special fiber is the nonzero source scalar times the
hidden outer generator. -/
theorem map_eval_zero_normalizedCoupledRelation
    (p q qTail : K[X]) (a0 : K) :
    (normalizedCoupledRelation p q qTail a0).map (evalRingHom 0) =
      -C a0 * q := by
  have hmap : (q.map C).map (evalRingHom 0) = q := by
    ext n
    simp
  rw [normalizedCoupledRelation]
  simp [hmap]

/-- The logarithmic visible velocity preserves the divisor `F=0`. -/
theorem eval_zero_logarithmicVisibleVelocity (b : K) :
    (C b * X : K[X]).eval 0 = 0 := by
  simp

/-- Total differentiation of a constant polynomial commutes with every
iterate of the coefficient derivation. -/
theorem iterate_polynomialTotalDerivation_C
    (d : Derivation ℤ K K) (p : K[X]) :
    ∀ n a,
      ((polynomialTotalDerivation d p)^[n]) (C a) =
        C ((d^[n]) a) := by
  intro n
  induction n with
  | zero =>
      intro a
      rfl
  | succ n inductionHypothesis =>
      intro a
      rw [Function.iterate_succ_apply', inductionHypothesis,
        polynomialTotalDerivation_C, Function.iterate_succ_apply']

/-- Coefficientwise differentiation commutes with polynomial
differentiation. -/
theorem polynomialCoefficientDerivation_derivative
    (d : Derivation ℤ K K) (r : K[X]) :
    polynomialCoefficientDerivation d r.derivative =
      (polynomialCoefficientDerivation d r).derivative := by
  ext n
  simp [coeff_polynomialCoefficientDerivation, coeff_derivative,
    Derivation.leibniz]
  ring

/-- Coefficient constancy is preserved by one vector-field derivative. -/
theorem polynomialCoefficientDerivation_vectorFieldDerivative_eq_zero
    (d : Derivation ℤ K K) {p r : K[X]}
    (hp : polynomialCoefficientDerivation d p = 0)
    (hr : polynomialCoefficientDerivation d r = 0) :
    polynomialCoefficientDerivation d (vectorFieldDerivative p r) = 0 := by
  rw [vectorFieldDerivative, Derivation.leibniz, hp,
    polynomialCoefficientDerivation_derivative, hr]
  simp

/-- Constant coefficients remain constant throughout the hidden
vector-field tower. -/
theorem polynomialCoefficientDerivation_iterate_vectorFieldDerivative_eq_zero
    (d : Derivation ℤ K K) {p q : K[X]}
    (hp : polynomialCoefficientDerivation d p = 0)
    (hq : polynomialCoefficientDerivation d q = 0) :
    ∀ n,
      polynomialCoefficientDerivation d
        ((vectorFieldDerivative p)^[n] q) = 0 := by
  intro n
  induction n with
  | zero => simpa using hq
  | succ n inductionHypothesis =>
      rw [Function.iterate_succ_apply']
      exact polynomialCoefficientDerivation_vectorFieldDerivative_eq_zero
        d hp inductionHypothesis

/-- Under coefficient constancy, the polynomial total derivation restricts
to the vector-field derivation on every iterate of `q`. -/
theorem iterate_polynomialTotalDerivation_eq_vectorFieldDerivative
    (d : Derivation ℤ K K) {p q : K[X]}
    (hp : polynomialCoefficientDerivation d p = 0)
    (hq : polynomialCoefficientDerivation d q = 0) :
    ∀ n,
      ((polynomialTotalDerivation d p)^[n]) q =
        (vectorFieldDerivative p)^[n] q := by
  intro n
  induction n with
  | zero => rfl
  | succ n inductionHypothesis =>
      rw [Function.iterate_succ_apply', Function.iterate_succ_apply',
        inductionHypothesis, polynomialTotalDerivation_apply,
        polynomialCoefficientDerivation_iterate_vectorFieldDerivative_eq_zero
          d hp hq n,
        zero_add]
      rfl

/-- The specialized total-derivation tower is exactly the binomial
triangular family. -/
theorem iterate_specialFiber_eq_triangularProlongation
    (d : Derivation ℤ K K) (p q : K[X]) (a0 : K)
    (hp : polynomialCoefficientDerivation d p = 0)
    (hq : polynomialCoefficientDerivation d q = 0) :
    ∀ n,
      ((polynomialTotalDerivation d p)^[n]) (-C a0 * q) =
        triangularProlongation p q (fun k ↦ (d^[k]) (-a0)) n := by
  intro n
  have hproduct : -C a0 * q = q * C (-a0) := by
    simp only [map_neg]
    ring
  rw [hproduct]
  calc
    ((polynomialTotalDerivation d p)^[n]) (q * C (-a0)) =
        ∑ j ∈ range (n + 1),
          n.choose j •
            (((polynomialTotalDerivation d p)^[j]) q *
              ((polynomialTotalDerivation d p)^[n - j]) (C (-a0))) :=
      iterate_apply_mul_range (polynomialTotalDerivation d p)
        n q (C (-a0))
    _ = triangularProlongation p q
          (fun k ↦ (d^[k]) (-a0)) n := by
      rw [triangularProlongation]
      refine sum_congr rfl fun j hj ↦ ?_
      rw [iterate_polynomialTotalDerivation_eq_vectorFieldDerivative
          d hp hq,
        iterate_polynomialTotalDerivation_C]
      simp [nsmul_eq_mul]
      ring

/-- Every actual normalized prolongation specializes to the governed
triangular family. -/
theorem map_eval_zero_iterate_normalizedCoupledRelation
    (d : Derivation ℤ K K) (p q qTail : K[X]) (a0 b : K)
    (hp : polynomialCoefficientDerivation d p = 0)
    (hq : polynomialCoefficientDerivation d q = 0) :
    ∀ n,
      (((polynomialTotalDerivation
          (polynomialTotalDerivation d (C b * X))
          (p.map C))^[n])
          (normalizedCoupledRelation p q qTail a0)).map
            (evalRingHom 0) =
        triangularProlongation p q (fun k ↦ (d^[k]) (-a0)) n := by
  intro n
  calc
    (((polynomialTotalDerivation
        (polynomialTotalDerivation d (C b * X))
        (p.map C))^[n])
        (normalizedCoupledRelation p q qTail a0)).map (evalRingHom 0) =
        ((polynomialTotalDerivation d p)^[n])
          ((normalizedCoupledRelation p q qTail a0).map
            (evalRingHom 0)) :=
      map_eval_zero_iterate_hiddenTotalDerivation d (C b * X) p
        (eval_zero_logarithmicVisibleVelocity b) n _
    _ = ((polynomialTotalDerivation d p)^[n]) (-C a0 * q) := by
      rw [map_eval_zero_normalizedCoupledRelation]
    _ = triangularProlongation p q (fun k ↦ (d^[k]) (-a0)) n :=
      iterate_specialFiber_eq_triangularProlongation d p q a0 hp hq n

/-- Aggregated actual-normalization and all-order specialization terminal. -/
theorem coupled_julia_all_order_specialization_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (p q : K[X])
      (source coefficient : K[X]) (a0 b : K),
      q.coeff 0 = 0 →
      q.coeff 1 = 0 →
      coefficient * (p.map C).eval source = C a0 →
      a0 ≠ 0 →
      polynomialCoefficientDerivation d p = 0 →
      polynomialCoefficientDerivation d q = 0 →
      ∃ qTail,
        q = X ^ 2 * qTail ∧
        hiddenRelationPolynomial (p.map C) (q.map C) source X coefficient =
            actualCoupledRelation p q a0 ∧
        actualCoupledRelation p q a0 =
            C X * normalizedCoupledRelation p q qTail a0 ∧
        (normalizedCoupledRelation p q qTail a0).map (evalRingHom 0) =
            -C a0 * q ∧
        a0 ≠ 0 ∧
        (C b * X : K[X]).eval 0 = 0 ∧
        ∀ n,
          (((polynomialTotalDerivation
              (polynomialTotalDerivation d (C b * X))
              (p.map C))^[n])
              (normalizedCoupledRelation p q qTail a0)).map
                (evalRingHom 0) =
            triangularProlongation p q (fun k ↦ (d^[k]) (-a0)) n := by
  intro d p q source coefficient a0 b hzero hone hsource ha0 hp hq
  obtain ⟨qTail, htangent⟩ := exists_tangentGenerator_tail q hzero hone
  exact ⟨qTail, htangent,
    hiddenRelationPolynomial_eq_actualCoupledRelation
      p q source coefficient a0 hsource,
    actualCoupledRelation_eq_X_mul_normalized p q qTail a0 htangent,
    map_eval_zero_normalizedCoupledRelation p q qTail a0,
    ha0,
    eval_zero_logarithmicVisibleVelocity b,
    map_eval_zero_iterate_normalizedCoupledRelation
      d p q qTail a0 b hp hq⟩

end FormalCoupledJuliaAllOrderSpecialization
