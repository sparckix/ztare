import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Tactic
import ZtareProofs.FormalDifferentialPolynomialInvariantSpecialization
import ZtareProofs.FormalFilteredDarbouxWeightRigidity
import ZtareProofs.FormalOneWeightIrreducibleContraction

/-!
# Binding Darboux divisibility to filtered coefficient rows

For the Euler-filtered polynomial derivation `d₀ + L X d/dX`, coefficients
of visible weight `n` evolve by `d₀(aₙ) + n L aₙ`.  The derivation does
not increase visible degree.  Therefore, when a nonzero polynomial divides
its derivative image, the quotient is constant in the visible variable and
the abstract Darboux weight-row theorem applies.
-/

namespace FormalFilteredDarbouxPolynomialBinding

open Polynomial
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFilteredDarbouxWeightRigidity
open ZtareProofs.FormalOneWeightIrreducibleContraction

variable {K : Type*} [CommRing K] [IsDomain K]

/-- The Euler-filtered total derivation in the displayed variable. -/
noncomputable def filteredDarbouxDerivation
    (d : Derivation ℤ K K) (logarithmicWeight : K) :
    Derivation ℤ K[X] K[X] :=
  polynomialTotalDerivation d (C logarithmicWeight * X)

/-- Exact coefficient row of the Euler-filtered derivation. -/
theorem coeff_filteredDarbouxDerivation
    (d : Derivation ℤ K K) (logarithmicWeight : K)
    (polynomial : K[X]) (weight : ℕ) :
    (filteredDarbouxDerivation d logarithmicWeight polynomial).coeff weight =
      d (polynomial.coeff weight) +
        (weight : K) * logarithmicWeight * polynomial.coeff weight := by
  rw [filteredDarbouxDerivation, polynomialTotalDerivation_apply,
    coeff_add, coeff_polynomialCoefficientDerivation]
  cases weight with
  | zero => simp [coeff_mul]
  | succ weight =>
      rw [show C logarithmicWeight * X * polynomial.derivative =
          C logarithmicWeight * (polynomial.derivative * X) by ring,
        coeff_C_mul, coeff_mul_X, coeff_derivative]
      push_cast
      ring

/-- The filtered derivation cannot create a higher visible weight. -/
theorem natDegree_filteredDarbouxDerivation_le
    (d : Derivation ℤ K K) (logarithmicWeight : K)
    (polynomial : K[X]) :
    (filteredDarbouxDerivation d logarithmicWeight polynomial).natDegree ≤
      polynomial.natDegree := by
  rw [natDegree_le_iff_coeff_eq_zero]
  intro weight hweight
  rw [coeff_filteredDarbouxDerivation]
  rw [coeff_eq_zero_of_natDegree_lt hweight, map_zero, mul_zero,
    add_zero]

/-- Darboux divisibility has a cofactor constant in the visible variable. -/
theorem exists_scalar_cofactor_of_dvd_filteredDarbouxDerivation
    (d : Derivation ℤ K K) (logarithmicWeight : K)
    (polynomial : K[X])
    (hpolynomial : polynomial ≠ 0)
    (hdvd : polynomial ∣
      filteredDarbouxDerivation d logarithmicWeight polynomial) :
    ∃ cofactor : K,
      filteredDarbouxDerivation d logarithmicWeight polynomial =
        polynomial * C cofactor := by
  obtain ⟨quotient, hquotient⟩ := hdvd
  by_cases hquotientZero : quotient = 0
  · refine ⟨0, ?_⟩
    rw [hquotient, hquotientZero]
    simp
  · have hdegree := natDegree_filteredDarbouxDerivation_le
        d logarithmicWeight polynomial
    rw [hquotient, natDegree_mul hpolynomial hquotientZero] at hdegree
    have hquotientDegree : quotient.natDegree = 0 := by omega
    refine ⟨quotient.coeff 0, ?_⟩
    have hquotientConstant : quotient = C (quotient.coeff 0) :=
      eq_C_of_natDegree_eq_zero hquotientDegree
    exact hquotient.trans
      (congrArg (fun value : K[X] ↦ polynomial * value)
        hquotientConstant)

/-- The scalar cofactor equation supplies every abstract Darboux weight row.
-/
theorem darbouWeightRows_of_scalar_cofactor
    (d : Derivation ℤ K K) (logarithmicWeight cofactor : K)
    (polynomial : K[X])
    (hcofactor :
      filteredDarbouxDerivation d logarithmicWeight polynomial =
        polynomial * C cofactor) :
    ∀ weight,
      darbouWeightRow d logarithmicWeight cofactor
        (polynomial.coeff weight) weight := by
  intro weight
  have hcoeff := congrArg (fun p : K[X] ↦ p.coeff weight) hcofactor
  change
    (filteredDarbouxDerivation d logarithmicWeight polynomial).coeff weight =
      (polynomial * C cofactor).coeff weight at hcoeff
  rw [coeff_filteredDarbouxDerivation, coeff_mul_C] at hcoeff
  simpa [darbouWeightRow, mul_comm] using hcoeff

/-- Darboux divisibility plus cross-weight nonresonance makes the polynomial
a single visible-weight monomial. -/
theorem eq_monomial_of_darboux_dvd_and_no_weight_resonance
    (d : Derivation ℤ K K) (logarithmicWeight : K)
    (polynomial : K[X])
    (hpolynomial : polynomial ≠ 0)
    (hdvd : polynomial ∣
      filteredDarbouxDerivation d logarithmicWeight polynomial)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      polynomial.coeff firstWeight ≠ 0 →
      polynomial.coeff secondWeight ≠ 0 →
      polynomial.coeff secondWeight * d (polynomial.coeff firstWeight) -
          polynomial.coeff firstWeight * d (polynomial.coeff secondWeight) ≠
        ((secondWeight : K) - (firstWeight : K)) *
          logarithmicWeight * polynomial.coeff firstWeight *
            polynomial.coeff secondWeight) :
    polynomial = monomial polynomial.natDegree polynomial.leadingCoeff := by
  obtain ⟨cofactor, hcofactor⟩ :=
    exists_scalar_cofactor_of_dvd_filteredDarbouxDerivation
      d logarithmicWeight polynomial hpolynomial hdvd
  exact eq_monomial_natDegree_of_no_weight_resonance
    d logarithmicWeight cofactor polynomial
    (darbouWeightRows_of_scalar_cofactor
      d logarithmicWeight cofactor polynomial hcofactor)
    hnoResonance

/-- An irreducible one-weight polynomial over a domain is constant or
associated to the visible variable. -/
theorem natDegree_eq_zero_or_associated_X_of_irreducible_eq_monomial
    (polynomial : K[X])
    (hirreducible : Irreducible polynomial)
    (hmonomial :
      polynomial = monomial polynomial.natDegree polynomial.leadingCoeff) :
    polynomial.natDegree = 0 ∨ Associated polynomial X :=
  natDegree_eq_zero_or_associated_X polynomial hirreducible hmonomial

/-- Aggregated filtered Darboux-polynomial binding. -/
theorem filtered_darboux_polynomial_binding_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (logarithmicWeight : K)
      (polynomial : K[X]),
      polynomial ≠ 0 →
      polynomial ∣ filteredDarbouxDerivation d logarithmicWeight polynomial →
      (∀ firstWeight secondWeight,
        firstWeight ≠ secondWeight →
        polynomial.coeff firstWeight ≠ 0 →
        polynomial.coeff secondWeight ≠ 0 →
        polynomial.coeff secondWeight * d (polynomial.coeff firstWeight) -
            polynomial.coeff firstWeight * d (polynomial.coeff secondWeight) ≠
          ((secondWeight : K) - (firstWeight : K)) *
            logarithmicWeight * polynomial.coeff firstWeight *
              polynomial.coeff secondWeight) →
      polynomial =
        monomial polynomial.natDegree polynomial.leadingCoeff := by
  intro d logarithmicWeight polynomial hpolynomial hdvd hnoResonance
  exact eq_monomial_of_darboux_dvd_and_no_weight_resonance
    d logarithmicWeight polynomial hpolynomial hdvd hnoResonance

end FormalFilteredDarbouxPolynomialBinding
