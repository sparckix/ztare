import ZtareProofs.AxiomPackJacobianExceptionalDivisorObstruction
import ZtareProofs.AxiomPackJacobianHamiltonianJet

/-!
Kernel endpoints for the source-only degree-escape argument.

The geometric bridge is: a uniformly degree-bounded source contact
algebraizes; the exceptional-square identity makes it triangular; the two
equivariant source-map ideals force its exceptional scaling to one.  Its
parameter jets therefore lie in the fixed-exceptional shear subgroup, whose
first-order isotropy and second-order contact are excluded by the inverse
cubic remainder calculation.
-/

namespace AxiomPackJacobianSourceDegreeEscape

open Polynomial

/-- Scalar endpoint of the two equivariant source-map ideal evaluations.
`pOne` is `p(1)` and `dpOne` is `p'(1)` in exceptional coordinates. -/
theorem lift_ideals_force_unit_exceptional_scaling
    (c pOne dpOne : ℚ)
    (hUOrigin : pOne = 0)
    (hVOrigin : (c - 1) + (3 / 2) * pOne = 0)
    (hVLinear : (-9 / 4) * dpOne = 0) :
    c = 1 ∧ dpOne = 0 := by
  constructor
  · rw [hUOrigin] at hVOrigin
    norm_num at hVOrigin ⊢
    linarith
  · norm_num at hVLinear
    exact hVLinear

/-- A constant fixed-exceptional source shear cannot be a first-order
isotropy: at `P=0` its first inverse-cubic remainder has nonzero
`w`-coefficient `-4`. -/
theorem constant_fixed_gamma_isotropy_is_trivial
    (a : ℚ)
    (hcoefficient : a * (12 * 0 - 4) = 0) :
    a = 0 := by
  norm_num at hcoefficient
  exact hcoefficient

/-- After positive source degree has been removed, neither a constant source
shear nor a target-base term can cancel the second residual's `w^2`
coefficient at `P=0`. -/
theorem constant_fixed_gamma_second_jet_obstruction
    (a : ℚ) :
    (10 - 21 * 0) / 24 ≠ a * 0 := by
  norm_num

/-- The associated-graded top obstruction plus the constant remainder
eliminates every polynomial first-order fixed-exceptional isotropy. -/
theorem fixed_gamma_first_order_polynomial_isotropy_trivial
    (f : ℚ[X])
    (hTop :
      0 < f.natDegree →
        3 ∣ 2 * f.natDegree + 3 ∧
        3 ∣ 2 * f.natDegree + 4)
    (hConstant :
      f.natDegree = 0 →
        f.coeff 0 * (12 * 0 - 4) = 0) :
    f = 0 := by
  by_cases hPositive : 0 < f.natDegree
  · exact
      (AxiomPackJacobianHamiltonianJet.positive_degree_source_has_nonbase_top_component
          f.natDegree (hTop hPositive)).elim
  · have hZero : f.natDegree = 0 :=
      Nat.eq_zero_of_not_pos hPositive
    have hCoeff : f.coeff 0 = 0 :=
      constant_fixed_gamma_isotropy_is_trivial
        (f.coeff 0) (hConstant hZero)
    rw [Polynomial.eq_C_of_natDegree_eq_zero hZero, hCoeff,
      Polynomial.C_0]

/-- The same leading-degree split excludes every polynomial fixed-exceptional
source correction at the second jet. -/
theorem no_fixed_gamma_second_jet_polynomial
    (f : ℚ[X])
    (hTop :
      0 < f.natDegree →
        3 ∣ 2 * f.natDegree + 3 ∧
        3 ∣ 2 * f.natDegree + 4)
    (hConstant :
      f.natDegree = 0 →
        (10 - 21 * 0) / 24 = f.coeff 0 * 0) :
    False := by
  by_cases hPositive : 0 < f.natDegree
  · exact
      (AxiomPackJacobianHamiltonianJet.positive_degree_source_has_nonbase_top_component
          f.natDegree (hTop hPositive)).elim
  · have hZero : f.natDegree = 0 :=
      Nat.eq_zero_of_not_pos hPositive
    exact
      (constant_fixed_gamma_second_jet_obstruction
        (f.coeff 0)) (hConstant hZero)

/-- Componentwise second-order path arithmetic.  If the first target field
is `-X`, the chain-rule cross term is `-2 X²`; area preservation writes the
second target derivative as `X² + K`, leaving the residual `F₂ - X² + K`. -/
theorem general_second_order_path_reduction
    (F₂ X₂ K : ℚ) :
    F₂ - 2 * X₂ + (X₂ + K) = F₂ - X₂ + K := by
  ring

/-- Aggregated algebraic endpoint for provider-free ratification.  The
formal-contact and leading-term descent bridges are stated in the companion
pencil; this target binds every invariant scalar and factorization endpoint
used there. -/
theorem source_degree_escape_terminal_certificate
    (g j : Polynomial (ℚ[X]))
    (hg : g ≠ 0)
    (hj : j ≠ 0)
    (hgNonconstant :
      ∀ c : ℚ, g ≠ Polynomial.C (Polynomial.C c))
    (hsquare :
      g ^ 2 * j = Polynomial.C (X ^ 2))
    (c pOne dpOne : ℚ)
    (hUOrigin : pOne = 0)
    (hVOrigin : (c - 1) + (3 / 2) * pOne = 0)
    (hVLinear : (-9 / 4) * dpOne = 0) :
    (∃ u : ℚ, u ≠ 0 ∧
      g = Polynomial.C (C u * X) ∧
      j = Polynomial.C (C (u⁻¹ ^ 2))) ∧
    c = 1 ∧ dpOne = 0 ∧
    (∀ f : ℚ[X],
      (0 < f.natDegree →
        3 ∣ 2 * f.natDegree + 3 ∧
        3 ∣ 2 * f.natDegree + 4) →
      (f.natDegree = 0 →
        f.coeff 0 * (12 * 0 - 4) = 0) →
      f = 0) ∧
    (∀ f : ℚ[X],
      ¬ ((0 < f.natDegree →
          3 ∣ 2 * f.natDegree + 3 ∧
          3 ∣ 2 * f.natDegree + 4) ∧
        (f.natDegree = 0 →
          (10 - 21 * 0) / 24 = f.coeff 0 * 0))) ∧
    (∀ F₂ X₂ K : ℚ,
      F₂ - 2 * X₂ + (X₂ + K) = F₂ - X₂ + K) := by
  obtain ⟨hc, hdp⟩ :=
    lift_ideals_force_unit_exceptional_scaling
      c pOne dpOne hUOrigin hVOrigin hVLinear
  exact
    ⟨AxiomPackJacobianExceptionalDivisorObstruction.exceptional_square_bivariate_exact
          g j hg hj hgNonconstant hsquare,
      hc,
      hdp,
      fixed_gamma_first_order_polynomial_isotropy_trivial,
      fun f hCompatible =>
        no_fixed_gamma_second_jet_polynomial
          f hCompatible.1 hCompatible.2,
      general_second_order_path_reduction⟩

end AxiomPackJacobianSourceDegreeEscape
