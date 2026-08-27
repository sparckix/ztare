import Mathlib.Tactic
import ZtareProofs.FormalBivariateDarbouxLocalizationBinding
import ZtareProofs.FormalCoupledJuliaCommonFactorSaturation
import ZtareProofs.FormalOneWeightIrreducibleContraction
import ZtareProofs.FormalOneWeightMapDescent

/-!
# Excluding persistent Darboux primes after common-factor saturation

This module assembles the algebraic route.  A persistent irreducible divisor
of the exact normalized coupled relation is swapped, mapped to a commuting
coefficient field, collapsed to one visible weight, reflected to the original
coefficient ring, and contradicted by coprime saturation.
-/

namespace FormalSaturatedDarbouxPrimeExclusion

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

/-- Direct polynomial-domain version: no coefficient-field localization is
needed once scalar-cofactor rigidity is stated over domains. -/
theorem no_saturated_persistent_darboux_prime_over_polynomial_domain
    (d : Derivation ℤ K K) (p q qTail : K[X])
    (logarithmicWeight a0 : K)
    (hq : q ≠ 0) (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime p q)
    (h : K[X][X]) (hirreducible : Irreducible h)
    (hdivRelation : h ∣ normalizedCoupledRelation p q qTail a0)
    (hdivDerivative : h ∣
      storedBivariateDerivation d p logarithmicWeight h)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      (Bivariate.swap h).coeff firstWeight ≠ 0 →
      (Bivariate.swap h).coeff secondWeight ≠ 0 →
      (Bivariate.swap h).coeff secondWeight *
            polynomialTotalDerivation d p
              ((Bivariate.swap h).coeff firstWeight) -
          (Bivariate.swap h).coeff firstWeight *
            polynomialTotalDerivation d p
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
        swappedBivariateDerivation d p logarithmicWeight
          (Bivariate.swap h) := by
    obtain ⟨quotient, hquotient⟩ := hdivDerivative
    refine ⟨Bivariate.swap quotient, ?_⟩
    calc
      swappedBivariateDerivation d p logarithmicWeight
            (Bivariate.swap h) =
          Bivariate.swap
            (storedBivariateDerivation d p logarithmicWeight h) :=
        (swap_storedBivariateDerivation d p logarithmicWeight h).symm
      _ = Bivariate.swap (h * quotient) :=
        congrArg Bivariate.swap hquotient
      _ = Bivariate.swap h * Bivariate.swap quotient := map_mul _ _ _
  have hdarbouxDomain :
      Bivariate.swap h ∣
        filteredDarbouxDerivation
          (polynomialTotalDerivation d p) (C logarithmicWeight)
          (Bivariate.swap h) := by
    simpa [swappedBivariateDerivation, filteredDarbouxDerivation] using
      hdivSwappedDerivative
  have hmonomial :
      Bivariate.swap h =
        monomial (Bivariate.swap h).natDegree
          (Bivariate.swap h).leadingCoeff :=
    eq_monomial_of_darboux_dvd_and_no_weight_resonance
      (polynomialTotalDerivation d p) (C logarithmicWeight)
      (Bivariate.swap h) hswapIrreducible.ne_zero hdarbouxDomain
      hnoResonance
  have honeWeight :
      (Bivariate.swap h).natDegree = 0 ∨
        Associated (Bivariate.swap h) X :=
    natDegree_eq_zero_or_associated_X
      (Bivariate.swap h) hswapIrreducible hmonomial
  have hdivSwappedRelation :
      Bivariate.swap h ∣
        Bivariate.swap (normalizedCoupledRelation p q qTail a0) := by
    obtain ⟨quotient, hquotient⟩ := hdivRelation
    refine ⟨Bivariate.swap quotient, ?_⟩
    rw [hquotient, map_mul]
  exact no_irreducible_one_weight_divisor_of_coprime_normalized
    p q qTail a0 (Bivariate.swap h) hq hqTail ha0 hcoprime
    hswapIrreducible honeWeight hdivSwappedRelation

/-- No irreducible divisor of the coprime normalized relation can persist
under the actual stored derivation once its coefficient-field realization
satisfies cross-weight nonresonance. -/
theorem no_saturated_persistent_darboux_prime
    (d : Derivation ℤ K K) (p q qTail : K[X])
    (logarithmicWeight a0 : K)
    (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L)
    (hcoeff : ∀ a : K[X],
      phi (polynomialTotalDerivation d p a) = dL (phi a))
    (hweight : phi (C logarithmicWeight) = weightL)
    (hphi : Function.Injective phi)
    (hq : q ≠ 0) (hqTail : qTail ≠ 0) (ha0 : a0 ≠ 0)
    (hcoprime : IsCoprime p q)
    (h : K[X][X]) (hirreducible : Irreducible h)
    (hdivRelation : h ∣ normalizedCoupledRelation p q qTail a0)
    (hdivDerivative : h ∣
      storedBivariateDerivation d p logarithmicWeight h)
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
    map_swap_darboux_dvd d p logarithmicWeight dL phi weightL
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
        Bivariate.swap (normalizedCoupledRelation p q qTail a0) := by
    obtain ⟨quotient, hquotient⟩ := hdivRelation
    refine ⟨Bivariate.swap quotient, ?_⟩
    rw [hquotient, map_mul]
  exact no_irreducible_one_weight_divisor_of_coprime_normalized
    p q qTail a0 (Bivariate.swap h) hq hqTail ha0 hcoprime
    hswapIrreducible honeWeight hdivSwappedRelation

/-- Aggregated saturated Darboux-prime exclusion certificate. -/
theorem saturated_darboux_prime_exclusion_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (p q qTail : K[X])
      (logarithmicWeight a0 : K)
      (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L),
      (∀ a : K[X],
        phi (polynomialTotalDerivation d p a) = dL (phi a)) →
      phi (C logarithmicWeight) = weightL →
      Function.Injective phi →
      q ≠ 0 → qTail ≠ 0 → a0 ≠ 0 → IsCoprime p q →
      ∀ h : K[X][X], Irreducible h →
        h ∣ normalizedCoupledRelation p q qTail a0 →
        h ∣ storedBivariateDerivation d p logarithmicWeight h →
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
  intro d p q qTail logarithmicWeight a0 dL phi weightL
    hcoeff hweight hphi hq hqTail ha0 hcoprime h hirreducible
    hdivRelation hdivDerivative hnoResonance
  exact no_saturated_persistent_darboux_prime
    d p q qTail logarithmicWeight a0 dL phi weightL
    hcoeff hweight hphi hq hqTail ha0 hcoprime h hirreducible
    hdivRelation hdivDerivative hnoResonance

end FormalSaturatedDarbouxPrimeExclusion
