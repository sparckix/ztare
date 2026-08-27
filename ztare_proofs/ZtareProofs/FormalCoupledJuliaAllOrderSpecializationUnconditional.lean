import ZtareProofs.FormalCoupledJuliaAllOrderSpecialization

/-!
# Scalar-free all-order coupled-Julia specialization

The normalized coupled-Julia relation and its full triangular prolongation
tower are algebraic in the source scalar.  They therefore remain valid on the
zero-scalar locus.  Scalar nonvanishing belongs to a later branch
classification, not to this specialization theorem.
-/

namespace FormalCoupledJuliaAllOrderSpecializationUnconditional

open Polynomial

open FormalCoupledJuliaElimination
open FormalDifferentialPolynomialInvariantSpecialization
open FormalPolynomialVectorFieldTriangularProlongation
open FormalCoupledJuliaAllOrderSpecialization

variable {K : Type*} [Field K] [CharZero K]

/-- Construct the normalized coupled relation and all of its specialized
prolongations without assuming or concluding that the source scalar is
nonzero. -/
theorem coupled_julia_all_order_specialization_without_scalar_nonzero_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (p q : K[X])
      (source coefficient : K[X]) (a0 b : K),
      q.coeff 0 = 0 →
      q.coeff 1 = 0 →
      coefficient * (p.map C).eval source = C a0 →
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
        (C b * X : K[X]).eval 0 = 0 ∧
        ∀ n,
          (((polynomialTotalDerivation
              (polynomialTotalDerivation d (C b * X))
              (p.map C))^[n])
              (normalizedCoupledRelation p q qTail a0)).map
                (evalRingHom 0) =
            triangularProlongation p q (fun k ↦ (d^[k]) (-a0)) n := by
  intro d p q source coefficient a0 b hzero hone hsource hp hq
  obtain ⟨qTail, htangent⟩ :=
    exists_tangentGenerator_tail q hzero hone
  exact ⟨qTail, htangent,
    hiddenRelationPolynomial_eq_actualCoupledRelation
      p q source coefficient a0 hsource,
    actualCoupledRelation_eq_X_mul_normalized p q qTail a0 htangent,
    map_eval_zero_normalizedCoupledRelation p q qTail a0,
    eval_zero_logarithmicVisibleVelocity b,
    map_eval_zero_iterate_normalizedCoupledRelation
      d p q qTail a0 b hp hq⟩

end FormalCoupledJuliaAllOrderSpecializationUnconditional
