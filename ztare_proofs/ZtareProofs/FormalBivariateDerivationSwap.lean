import Mathlib.Algebra.Polynomial.Bivariate
import Mathlib.Tactic
import ZtareProofs.FormalDifferentialPolynomialInvariantSpecialization

/-!
# Bivariate swap for nested polynomial total derivations

The coupled-Julia relation is stored as `K[F][Y]`, while visible-weight
rigidity reads it as `K[Y][F]`.  The bivariate swap intertwines the exact
nested total derivation: the hidden velocity becomes part of the coefficient
derivation and the logarithmic visible velocity becomes the outer Euler term.
-/

namespace FormalBivariateDerivationSwap

open Polynomial
open FormalDifferentialPolynomialInvariantSpecialization

variable {K : Type*} [CommRing K]

noncomputable def storedBivariateDerivation
    (d : Derivation ℤ K K) (p : K[X]) (logarithmicWeight : K) :
    Derivation ℤ K[X][X] K[X][X] :=
  polynomialTotalDerivation
    (polynomialTotalDerivation d (C logarithmicWeight * X))
    (p.map C)

noncomputable def swappedBivariateDerivation
    (d : Derivation ℤ K K) (p : K[X]) (logarithmicWeight : K) :
    Derivation ℤ K[X][X] K[X][X] :=
  polynomialTotalDerivation
    (polynomialTotalDerivation d p)
    (C (C logarithmicWeight) * X)

/-- The swap intertwining on a stored coefficient polynomial. -/
theorem swap_storedBivariateDerivation_C
    (d : Derivation ℤ K K) (p coefficient : K[X])
    (logarithmicWeight : K) :
    Bivariate.swap
        (storedBivariateDerivation d p logarithmicWeight (C coefficient)) =
      swappedBivariateDerivation d p logarithmicWeight
        (Bivariate.swap (C coefficient)) := by
  have hstored :
      storedBivariateDerivation d p logarithmicWeight (C coefficient) =
        C (polynomialTotalDerivation d (C logarithmicWeight * X)
          coefficient) := by
    exact polynomialTotalDerivation_C
      (polynomialTotalDerivation d (C logarithmicWeight * X))
      (p.map C) coefficient
  have hintertwine :
      (polynomialTotalDerivation d (C logarithmicWeight * X)
          coefficient).map C =
        polynomialTotalDerivation (polynomialTotalDerivation d p)
          (C (C logarithmicWeight) * X) (coefficient.map C) := by
    apply map_polynomialTotalDerivation
      d (polynomialTotalDerivation d p) C
        (C logarithmicWeight * X) (C (C logarithmicWeight) * X)
    · intro a
      exact (polynomialTotalDerivation_C d p a).symm
    · ext n
      simp
  calc
    Bivariate.swap
          (storedBivariateDerivation d p logarithmicWeight (C coefficient)) =
        Bivariate.swap
          (C (polynomialTotalDerivation d (C logarithmicWeight * X)
            coefficient)) := congrArg Bivariate.swap hstored
    _ = (polynomialTotalDerivation d (C logarithmicWeight * X)
          coefficient).map C := Bivariate.swap_C _
    _ = polynomialTotalDerivation (polynomialTotalDerivation d p)
          (C (C logarithmicWeight) * X) (coefficient.map C) := hintertwine
    _ = swappedBivariateDerivation d p logarithmicWeight
          (Bivariate.swap (C coefficient)) := by
      rw [swappedBivariateDerivation, Bivariate.swap_C]
      rfl

/-- The swap intertwining on the stored outer variable. -/
theorem swap_storedBivariateDerivation_X
    (d : Derivation ℤ K K) (p : K[X])
    (logarithmicWeight : K) :
    Bivariate.swap
        (storedBivariateDerivation d p logarithmicWeight X) =
      swappedBivariateDerivation d p logarithmicWeight
        (Bivariate.swap X) := by
  have hstored :
      storedBivariateDerivation d p logarithmicWeight X = p.map C := by
    exact polynomialTotalDerivation_X
      (polynomialTotalDerivation d (C logarithmicWeight * X)) (p.map C)
  have hswapped :
      swappedBivariateDerivation d p logarithmicWeight (C X) = C p := by
    calc
      swappedBivariateDerivation d p logarithmicWeight (C X) =
          C (polynomialTotalDerivation d p X) :=
        polynomialTotalDerivation_C (polynomialTotalDerivation d p)
          (C (C logarithmicWeight) * X) X
      _ = C p := by rw [polynomialTotalDerivation_X]
  calc
    Bivariate.swap (storedBivariateDerivation d p logarithmicWeight X) =
        Bivariate.swap (p.map C) := congrArg Bivariate.swap hstored
    _ = C p := Bivariate.swap_map_C p
    _ = swappedBivariateDerivation d p logarithmicWeight (C X) := hswapped.symm
    _ = swappedBivariateDerivation d p logarithmicWeight
          (Bivariate.swap X) := by rw [Bivariate.swap_Y]

/-- The exact nested total derivations are conjugate under bivariate swap. -/
theorem swap_storedBivariateDerivation
    (d : Derivation ℤ K K) (p : K[X])
    (logarithmicWeight : K) :
    ∀ polynomial : K[X][X],
      Bivariate.swap
          (storedBivariateDerivation d p logarithmicWeight polynomial) =
        swappedBivariateDerivation d p logarithmicWeight
          (Bivariate.swap polynomial) := by
  intro polynomial
  induction polynomial using Polynomial.induction_on' with
  | add left right hleft hright =>
      simp only [map_add]
      rw [hleft, hright]
  | monomial degree coefficient =>
      have hpower :
          Bivariate.swap
              (storedBivariateDerivation d p logarithmicWeight (X ^ degree)) =
            swappedBivariateDerivation d p logarithmicWeight
              (Bivariate.swap (X ^ degree)) := by
        induction degree with
        | zero => simp
        | succ degree inductionHypothesis =>
            rw [pow_succ,
              (storedBivariateDerivation d p logarithmicWeight).leibniz,
              map_add, map_mul,
              (swappedBivariateDerivation d p logarithmicWeight).leibniz]
            simp only [smul_eq_mul]
            simp only [map_mul]
            rw [inductionHypothesis, swap_storedBivariateDerivation_X]
      rw [← C_mul_X_pow_eq_monomial]
      rw [(storedBivariateDerivation d p logarithmicWeight).leibniz,
        map_add, map_mul,
        (swappedBivariateDerivation d p logarithmicWeight).leibniz]
      simp only [smul_eq_mul]
      simp only [map_mul]
      rw [swap_storedBivariateDerivation_C, hpower]

/-- Aggregated bivariate derivation-swap certificate. -/
theorem bivariate_derivation_swap_terminal_certificate :
    ∀ (d : Derivation ℤ K K) (p : K[X])
      (logarithmicWeight : K) (polynomial : K[X][X]),
      Bivariate.swap
          (storedBivariateDerivation d p logarithmicWeight polynomial) =
        swappedBivariateDerivation d p logarithmicWeight
          (Bivariate.swap polynomial) := by
  exact swap_storedBivariateDerivation

end FormalBivariateDerivationSwap
