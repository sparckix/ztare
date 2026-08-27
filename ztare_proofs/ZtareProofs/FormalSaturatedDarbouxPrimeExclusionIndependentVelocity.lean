import Mathlib.Tactic
import ZtareProofs.FormalSaturatedDarbouxPrimeExclusion

/-!
# Saturated Darboux-prime exclusion with an independent stored velocity

This module separates the polynomial that defines the stored bivariate
derivation from the two polynomials that define the normalized coupled
relation.  Coprime saturation concerns `relationInner` and `relationOuter`;
the Darboux and cross-weight arguments concern the independent `velocity`.
-/

namespace FormalSaturatedDarbouxPrimeExclusionIndependentVelocity

open Polynomial
open FormalBivariateDerivationSwap
open FormalBivariateDarbouxLocalizationBinding
open FormalCoupledJuliaAllOrderSpecialization
open FormalCoupledJuliaCommonFactorSaturation
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFilteredDarbouxPolynomialBinding
open FormalOneWeightMapDescent
open ZtareProofs.FormalOneWeightIrreducibleContraction

variable {K L : Type*} [Field K] [Field L]

/-- Direct polynomial-domain exclusion with the stored velocity independent
of the generators of the normalized coupled relation. -/
theorem no_saturated_persistent_darboux_prime_over_polynomial_domain_independent_velocity
    (d : Derivation ℤ K K)
    (velocity relationInner relationOuter relationOuterTail : K[X])
    (logarithmicWeight a0 : K)
    (hrelationOuter : relationOuter ≠ 0)
    (hrelationOuterTail : relationOuterTail ≠ 0)
    (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime relationInner relationOuter)
    (h : K[X][X]) (hirreducible : Irreducible h)
    (hdivRelation :
      h ∣ normalizedCoupledRelation
        relationInner relationOuter relationOuterTail a0)
    (hdivDerivative :
      h ∣ storedBivariateDerivation d velocity logarithmicWeight h)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      (Bivariate.swap h).coeff firstWeight ≠ 0 →
      (Bivariate.swap h).coeff secondWeight ≠ 0 →
      (Bivariate.swap h).coeff secondWeight *
            polynomialTotalDerivation d velocity
              ((Bivariate.swap h).coeff firstWeight) -
          (Bivariate.swap h).coeff firstWeight *
            polynomialTotalDerivation d velocity
              ((Bivariate.swap h).coeff secondWeight) ≠
        ((secondWeight : K[X]) - (firstWeight : K[X])) *
          C logarithmicWeight *
          (Bivariate.swap h).coeff firstWeight *
          (Bivariate.swap h).coeff secondWeight) :
    False := by
  have hswapIrreducible : Irreducible (Bivariate.swap h) :=
    hirreducible.map Bivariate.swap
  have hdivSwappedDerivative :
      Bivariate.swap h ∣
        swappedBivariateDerivation d velocity logarithmicWeight
          (Bivariate.swap h) := by
    obtain ⟨quotient, hquotient⟩ := hdivDerivative
    refine ⟨Bivariate.swap quotient, ?_⟩
    calc
      swappedBivariateDerivation d velocity logarithmicWeight
            (Bivariate.swap h) =
          Bivariate.swap
            (storedBivariateDerivation d velocity logarithmicWeight h) :=
        (swap_storedBivariateDerivation
          d velocity logarithmicWeight h).symm
      _ = Bivariate.swap (h * quotient) :=
        congrArg Bivariate.swap hquotient
      _ = Bivariate.swap h * Bivariate.swap quotient := map_mul _ _ _
  have hdarbouxDomain :
      Bivariate.swap h ∣
        filteredDarbouxDerivation
          (polynomialTotalDerivation d velocity) (C logarithmicWeight)
          (Bivariate.swap h) := by
    simpa [swappedBivariateDerivation, filteredDarbouxDerivation] using
      hdivSwappedDerivative
  have hmonomial :
      Bivariate.swap h =
        monomial (Bivariate.swap h).natDegree
          (Bivariate.swap h).leadingCoeff :=
    eq_monomial_of_darboux_dvd_and_no_weight_resonance
      (polynomialTotalDerivation d velocity) (C logarithmicWeight)
      (Bivariate.swap h) hswapIrreducible.ne_zero hdarbouxDomain
      hnoResonance
  have honeWeight :
      (Bivariate.swap h).natDegree = 0 ∨
        Associated (Bivariate.swap h) X :=
    natDegree_eq_zero_or_associated_X
      (Bivariate.swap h) hswapIrreducible hmonomial
  have hdivSwappedRelation :
      Bivariate.swap h ∣
        Bivariate.swap
          (normalizedCoupledRelation
            relationInner relationOuter relationOuterTail a0) := by
    obtain ⟨quotient, hquotient⟩ := hdivRelation
    refine ⟨Bivariate.swap quotient, ?_⟩
    rw [hquotient, map_mul]
  exact no_irreducible_one_weight_divisor_of_coprime_normalized
    relationInner relationOuter relationOuterTail a0 (Bivariate.swap h)
    hrelationOuter hrelationOuterTail ha0 hcoprime hswapIrreducible
    honeWeight hdivSwappedRelation

/-- Coefficient-field exclusion with the stored velocity independent of the
generators of the normalized coupled relation. -/
theorem no_saturated_persistent_darboux_prime_independent_velocity
    (d : Derivation ℤ K K)
    (velocity relationInner relationOuter relationOuterTail : K[X])
    (logarithmicWeight a0 : K)
    (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L)
    (hcoeff : ∀ a : K[X],
      phi (polynomialTotalDerivation d velocity a) = dL (phi a))
    (hweight : phi (C logarithmicWeight) = weightL)
    (hphi : Function.Injective phi)
    (hrelationOuter : relationOuter ≠ 0)
    (hrelationOuterTail : relationOuterTail ≠ 0)
    (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime relationInner relationOuter)
    (h : K[X][X]) (hirreducible : Irreducible h)
    (hdivRelation :
      h ∣ normalizedCoupledRelation
        relationInner relationOuter relationOuterTail a0)
    (hdivDerivative :
      h ∣ storedBivariateDerivation d velocity logarithmicWeight h)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      ((Bivariate.swap h).map phi).coeff firstWeight ≠ 0 →
      ((Bivariate.swap h).map phi).coeff secondWeight ≠ 0 →
      ((Bivariate.swap h).map phi).coeff secondWeight *
            dL (((Bivariate.swap h).map phi).coeff firstWeight) -
          ((Bivariate.swap h).map phi).coeff firstWeight *
            dL (((Bivariate.swap h).map phi).coeff secondWeight) ≠
        ((secondWeight : L) - (firstWeight : L)) * weightL *
          ((Bivariate.swap h).map phi).coeff firstWeight *
          ((Bivariate.swap h).map phi).coeff secondWeight) :
    False := by
  have hswapIrreducible : Irreducible (Bivariate.swap h) :=
    hirreducible.map Bivariate.swap
  have hmappedNonzero : (Bivariate.swap h).map phi ≠ 0 := by
    intro hmappedZero
    apply hswapIrreducible.ne_zero
    apply Polynomial.map_injective phi hphi
    simpa using hmappedZero
  have hdarbouxMapped :
      (Bivariate.swap h).map phi ∣
        filteredDarbouxDerivation dL weightL
          ((Bivariate.swap h).map phi) :=
    map_swap_darboux_dvd d velocity logarithmicWeight dL phi weightL
      hcoeff hweight h hdivDerivative
  have hmappedMonomial :
      (Bivariate.swap h).map phi =
        monomial ((Bivariate.swap h).map phi).natDegree
          ((Bivariate.swap h).map phi).leadingCoeff :=
    eq_monomial_of_darboux_dvd_and_no_weight_resonance
      dL weightL ((Bivariate.swap h).map phi)
      hmappedNonzero hdarbouxMapped hnoResonance
  have honeWeight :
      (Bivariate.swap h).natDegree = 0 ∨
        Associated (Bivariate.swap h) X :=
    natDegree_eq_zero_or_associated_X_of_map_eq_monomial
      phi hphi (Bivariate.swap h) hswapIrreducible hmappedMonomial
  have hdivSwappedRelation :
      Bivariate.swap h ∣
        Bivariate.swap
          (normalizedCoupledRelation
            relationInner relationOuter relationOuterTail a0) := by
    obtain ⟨quotient, hquotient⟩ := hdivRelation
    refine ⟨Bivariate.swap quotient, ?_⟩
    rw [hquotient, map_mul]
  exact no_irreducible_one_weight_divisor_of_coprime_normalized
    relationInner relationOuter relationOuterTail a0 (Bivariate.swap h)
    hrelationOuter hrelationOuterTail ha0 hcoprime hswapIrreducible
    honeWeight hdivSwappedRelation

/-- Terminal certificate: the stored derivation velocity and the saturated
relation generators are independent inputs. -/
theorem saturated_darboux_prime_exclusion_independent_velocity_terminal_certificate :
    ∀ (d : Derivation ℤ K K)
      (velocity relationInner relationOuter relationOuterTail : K[X])
      (logarithmicWeight a0 : K)
      (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L),
      (∀ a : K[X],
        phi (polynomialTotalDerivation d velocity a) = dL (phi a)) →
      phi (C logarithmicWeight) = weightL →
      Function.Injective phi →
      relationOuter ≠ 0 → relationOuterTail ≠ 0 → a0 ≠ 0 →
      IsCoprime relationInner relationOuter →
      ∀ h : K[X][X], Irreducible h →
        h ∣ normalizedCoupledRelation
          relationInner relationOuter relationOuterTail a0 →
        h ∣ storedBivariateDerivation d velocity logarithmicWeight h →
        (∀ firstWeight secondWeight,
          firstWeight ≠ secondWeight →
          ((Bivariate.swap h).map phi).coeff firstWeight ≠ 0 →
          ((Bivariate.swap h).map phi).coeff secondWeight ≠ 0 →
          ((Bivariate.swap h).map phi).coeff secondWeight *
                dL (((Bivariate.swap h).map phi).coeff firstWeight) -
              ((Bivariate.swap h).map phi).coeff firstWeight *
                dL (((Bivariate.swap h).map phi).coeff secondWeight) ≠
            ((secondWeight : L) - (firstWeight : L)) * weightL *
              ((Bivariate.swap h).map phi).coeff firstWeight *
              ((Bivariate.swap h).map phi).coeff secondWeight) →
        False := by
  intro d velocity relationInner relationOuter relationOuterTail
    logarithmicWeight a0 dL phi weightL hcoeff hweight hphi
    hrelationOuter hrelationOuterTail ha0 hcoprime h hirreducible
    hdivRelation hdivDerivative hnoResonance
  exact no_saturated_persistent_darboux_prime_independent_velocity
    d velocity relationInner relationOuter relationOuterTail
    logarithmicWeight a0 dL phi weightL hcoeff hweight hphi
    hrelationOuter hrelationOuterTail ha0 hcoprime h hirreducible
    hdivRelation hdivDerivative hnoResonance

end FormalSaturatedDarbouxPrimeExclusionIndependentVelocity
