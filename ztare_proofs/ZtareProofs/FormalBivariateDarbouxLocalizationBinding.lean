import Mathlib.Algebra.Polynomial.Bivariate
import Mathlib.Tactic
import ZtareProofs.FormalBivariateDerivationSwap
import ZtareProofs.FormalFilteredDarbouxPolynomialBinding

/-!
# Transporting bivariate Darboux divisibility to a coefficient field

After bivariate swap, any coefficient homomorphism intertwining the hidden
total derivation with a field derivation carries the stored derivation to the
Euler-filtered field derivation.  Darboux divisibility therefore transports
through both presentation change and coefficient extension.
-/

namespace FormalBivariateDarbouxLocalizationBinding

open Polynomial
open FormalBivariateDerivationSwap
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFilteredDarbouxPolynomialBinding

variable {K L : Type*} [CommRing K] [Field L]

/-- Swap followed by a commuting coefficient-field map intertwines the exact
stored derivation with the field-valued Euler-filtered derivation. -/
theorem map_swap_storedBivariateDerivation
    (d : Derivation ℤ K K) (p : K[X]) (logarithmicWeight : K)
    (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L)
    (hcoeff : ∀ a : K[X],
      phi (polynomialTotalDerivation d p a) = dL (phi a))
    (hweight : phi (C logarithmicWeight) = weightL)
    (polynomial : K[X][X]) :
    (Bivariate.swap
        (storedBivariateDerivation d p logarithmicWeight polynomial)).map
          phi =
      filteredDarbouxDerivation dL weightL
        ((Bivariate.swap polynomial).map phi) := by
  rw [swap_storedBivariateDerivation,
    swappedBivariateDerivation, filteredDarbouxDerivation]
  apply map_polynomialTotalDerivation
    (polynomialTotalDerivation d p) dL phi
      (C (C logarithmicWeight) * X) (C weightL * X)
      hcoeff
  ext n
  simp [hweight]

/-- Darboux divisibility in the stored presentation transports to Darboux
divisibility over the coefficient field. -/
theorem map_swap_darboux_dvd
    (d : Derivation ℤ K K) (p : K[X]) (logarithmicWeight : K)
    (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L)
    (hcoeff : ∀ a : K[X],
      phi (polynomialTotalDerivation d p a) = dL (phi a))
    (hweight : phi (C logarithmicWeight) = weightL)
    (polynomial : K[X][X])
    (hdvd : polynomial ∣
      storedBivariateDerivation d p logarithmicWeight polynomial) :
    (Bivariate.swap polynomial).map phi ∣
      filteredDarbouxDerivation dL weightL
        ((Bivariate.swap polynomial).map phi) := by
  obtain ⟨quotient, hquotient⟩ := hdvd
  refine ⟨(Bivariate.swap quotient).map phi, ?_⟩
  rw [← map_swap_storedBivariateDerivation
      d p logarithmicWeight dL phi weightL hcoeff hweight polynomial,
    hquotient, map_mul, Polynomial.map_mul]

/-- Aggregated bivariate Darboux-localization binding certificate. -/
theorem bivariate_darboux_localization_binding_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (p : K[X]) (logarithmicWeight : K)
      (dL : Derivation ℤ L L) (phi : K[X] →+* L) (weightL : L),
      (∀ a : K[X],
        phi (polynomialTotalDerivation d p a) = dL (phi a)) →
      phi (C logarithmicWeight) = weightL →
      ∀ polynomial : K[X][X],
        polynomial ∣ storedBivariateDerivation d p logarithmicWeight polynomial →
        (Bivariate.swap polynomial).map phi ∣
          filteredDarbouxDerivation dL weightL
            ((Bivariate.swap polynomial).map phi) := by
  intro d p logarithmicWeight dL phi weightL hcoeff hweight polynomial hdvd
  exact map_swap_darboux_dvd d p logarithmicWeight dL phi weightL
    hcoeff hweight polynomial hdvd

end FormalBivariateDarbouxLocalizationBinding
