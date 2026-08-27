import Mathlib.Algebra.Polynomial.Bivariate
import Mathlib.Tactic
import ZtareProofs.FormalCoupledJuliaAllOrderSpecialization
import ZtareProofs.FormalTangentSubstitutionInjectivity

/-!
# Contracting visible-weight-zero factors of the coupled-Julia relation

The normalized coupled relation is stored as a polynomial in the hidden
variable over the visible polynomial ring.  Mathlib's bivariate swap turns it
into a polynomial in the visible variable over the hidden polynomial ring.
A divisor constant in visible weight then divides every visible coefficient.
The constant and top nonzero coefficients force it to divide both polynomial
generators.
-/

namespace FormalCoupledJuliaCommonFactorSaturation

open Polynomial
open FormalCoupledJuliaAllOrderSpecialization
open FormalTangentSubstitutionInjectivity

variable {K : Type*} [Field K]

/-- A divisor constant in the displayed variable divides every coefficient. -/
theorem dvd_coeff_of_C_dvd
    (divisor : K[X]) (family : K[X][X]) (weight : ℕ)
    (hdvd : C divisor ∣ family) :
    divisor ∣ family.coeff weight := by
  obtain ⟨quotient, hquotient⟩ := hdvd
  refine ⟨quotient.coeff weight, ?_⟩
  rw [hquotient, coeff_C_mul]

/-- Swapping the stored hidden-variable presentation exposes visible weight
as the outer polynomial degree. -/
theorem swap_normalizedCoupledRelation
    (p q qTail : K[X]) (a0 : K) :
    Bivariate.swap (normalizedCoupledRelation p q qTail a0) =
      (X * qTail).map C * C p - C (C a0) * C q := by
  rw [normalizedCoupledRelation]
  simp [map_mul, Bivariate.swap_C, Bivariate.swap_map_C]

/-- Every visible-weight-zero divisor of the exact normalized relation is a
common hidden-variable divisor of both polynomial generators. -/
theorem common_generator_divisor_of_C_dvd_swap_normalized
    (p q qTail h : K[X]) (a0 : K)
    (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hdvd : C h ∣
      Bivariate.swap (normalizedCoupledRelation p q qTail a0)) :
    h ∣ p ∧ h ∣ q := by
  rw [swap_normalizedCoupledRelation] at hdvd
  let family : K[X][X] :=
    (X * qTail).map C * C p - C (C a0) * C q
  change C h ∣ family at hdvd
  constructor
  · have hcoefficient : h ∣ family.coeff (qTail.natDegree + 1) :=
      dvd_coeff_of_C_dvd h family (qTail.natDegree + 1) hdvd
    have hcoefficientIdentity :
        family.coeff (qTail.natDegree + 1) =
          C qTail.leadingCoeff * p := by
      simp [family, coeff_sub, coeff_mul_C, coeff_map, coeff_X_mul,
        coeff_natDegree]
    rw [hcoefficientIdentity] at hcoefficient
    have hleading : qTail.leadingCoeff ≠ 0 :=
      leadingCoeff_ne_zero.mpr hqTail
    have hunit : IsUnit (C qTail.leadingCoeff : K[X]) :=
      isUnit_C.mpr (isUnit_iff_ne_zero.mpr hleading)
    exact hunit.dvd_mul_left.mp hcoefficient
  · have hcoefficient : h ∣ family.coeff 0 :=
      dvd_coeff_of_C_dvd h family 0 hdvd
    have hcoefficientIdentity : family.coeff 0 = -(C a0 * q) := by
      simp [family, coeff_sub, coeff_map]
    rw [hcoefficientIdentity] at hcoefficient
    have hunit : IsUnit (C a0 : K[X]) :=
      isUnit_C.mpr (isUnit_iff_ne_zero.mpr ha0)
    exact hunit.dvd_mul_left.mp (dvd_neg.mp hcoefficient)

/-- On a coprime generator pair, every divisor constant in visible weight is
a unit. -/
theorem isUnit_of_C_dvd_swap_normalized_of_isCoprime
    (p q qTail h : K[X]) (a0 : K)
    (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime p q)
    (hdvd : C h ∣
      Bivariate.swap (normalizedCoupledRelation p q qTail a0)) :
    IsUnit h := by
  obtain ⟨hp, hq⟩ := common_generator_divisor_of_C_dvd_swap_normalized
    p q qTail h a0 hqTail ha0 hdvd
  exact hcoprime.isUnit_of_dvd' hp hq

/-- The visible variable cannot divide the normalized relation: its constant
visible coefficient is the nonzero polynomial `-a0*q`. -/
theorem X_not_dvd_swap_normalized
    (p q qTail : K[X]) (a0 : K)
    (hq : q ≠ 0) (ha0 : a0 ≠ 0) :
    ¬X ∣ Bivariate.swap (normalizedCoupledRelation p q qTail a0) := by
  rw [swap_normalizedCoupledRelation, X_dvd_iff]
  simp [coeff_sub, coeff_map, hq, ha0]

/-- Nor can any polynomial associated to the visible variable divide the
normalized relation. -/
theorem associated_X_not_dvd_swap_normalized
    (p q qTail : K[X]) (a0 : K) (h : K[X][X])
    (hq : q ≠ 0) (ha0 : a0 ≠ 0)
    (hassociated : Associated h X) :
    ¬h ∣ Bivariate.swap (normalizedCoupledRelation p q qTail a0) := by
  intro hdvd
  exact X_not_dvd_swap_normalized p q qTail a0 hq ha0
    (hassociated.dvd_iff_dvd_left.mp hdvd)

/-- The two extreme outcomes of one-weight rigidity are both impossible for
a nonunit irreducible divisor of a coprime normalized relation. -/
theorem no_irreducible_one_weight_divisor_of_coprime_normalized
    (p q qTail : K[X]) (a0 : K) (h : K[X][X])
    (hq : q ≠ 0) (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime p q)
    (hirreducible : Irreducible h)
    (honeWeight : h.natDegree = 0 ∨ Associated h X)
    (hdvd : h ∣
      Bivariate.swap (normalizedCoupledRelation p q qTail a0)) :
    False := by
  rcases honeWeight with hdegreeZero | hassociated
  · have hconstant : h = C (h.coeff 0) :=
      eq_C_of_natDegree_eq_zero hdegreeZero
    have hcoefficientUnit : IsUnit (h.coeff 0) := by
      rw [hconstant] at hdvd
      apply isUnit_of_C_dvd_swap_normalized_of_isCoprime
        p q qTail (h.coeff 0) a0 hqTail ha0 hcoprime
      exact hdvd
    exact hirreducible.not_isUnit (by
      rw [hconstant]
      exact isUnit_C.mpr hcoefficientUnit)
  · exact associated_X_not_dvd_swap_normalized
      p q qTail a0 h hq ha0 hassociated hdvd

/-- A common hidden-variable factor pulls out of the exact normalized
coupled-Julia relation without changing the declared visible tail. -/
theorem normalizedCoupledRelation_mul_common_factor
    (factor p q qTail : K[X]) (a0 : K) :
    normalizedCoupledRelation (factor * p) (factor * q) qTail a0 =
      factor.map C * normalizedCoupledRelation p q qTail a0 := by
  simp [normalizedCoupledRelation, map_mul]
  ring

/-- A nonzero common factor can be canceled on a selected invertible tangent
germ.  The visible endpoint is arbitrary. -/
theorem cancel_common_factor_on_selected_tangent_germ
    (factor p q qTail : K[X]) (a0 : K)
    (visible hidden : PowerSeries K)
    (hfactor : factor ≠ 0)
    (hhiddenConstant : hidden.constantCoeff = 0)
    [Invertible (hidden.coeff 1)]
    (hrelation :
      aevalAeval visible hidden
        (normalizedCoupledRelation (factor * p) (factor * q) qTail a0) = 0) :
    aevalAeval visible hidden
      (normalizedCoupledRelation p q qTail a0) = 0 := by
  rw [normalizedCoupledRelation_mul_common_factor] at hrelation
  simp only [map_mul] at hrelation
  have hfactorEvaluation : Polynomial.aeval hidden factor ≠ 0 :=
    polynomial_aeval_ne_zero_of_invertible_linear
      hidden hhiddenConstant factor hfactor
  have hfactorBinding :
      aevalAeval visible hidden (factor.map C : K[X][X]) =
        Polynomial.aeval hidden factor := by
    rw [← Bivariate.swap_C factor,
      Bivariate.aevalAeval_swap, aevalAeval_C]
  rw [hfactorBinding] at hrelation
  exact (mul_eq_zero.mp hrelation).resolve_left hfactorEvaluation

/-- Aggregated common-factor contraction certificate. -/
theorem coupled_julia_common_factor_saturation_terminal_certificate :
    ∀ (p q qTail h : K[X]) (a0 : K),
      qTail ≠ 0 →
      a0 ≠ 0 →
      C h ∣ Bivariate.swap (normalizedCoupledRelation p q qTail a0) →
      h ∣ p ∧ h ∣ q := by
  intro p q qTail h a0 hqTail ha0 hdvd
  exact common_generator_divisor_of_C_dvd_swap_normalized
    p q qTail h a0 hqTail ha0 hdvd

end FormalCoupledJuliaCommonFactorSaturation
