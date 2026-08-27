import Mathlib.RingTheory.LaurentSeries
import Mathlib.Tactic

/-!
# Polynomial nonvanishing at a Laurent pole

The inverse of a nonzero power series with zero constant coefficient is
transcendental over the coefficient field in the finite sense needed here:
no nonzero polynomial can vanish at that Laurent element.  Reversal clears
the pole and exposes the original leading coefficient as the constant term.
-/

namespace FormalLaurentInversePolynomialNonvanishing

open Polynomial PowerSeries
open scoped LaurentSeries

noncomputable section

abbrev PS := PowerSeries ℂ
abbrev LS := LaurentSeries ℂ

/-- A nonzero zero-constant power-series germ cannot have its Laurent inverse
annihilated by a nonzero complex polynomial. -/
theorem polynomial_aeval_inverse_ne_zero
    (reciprocal : PS)
    (hreciprocal : reciprocal ≠ 0)
    (hconstant : reciprocal.constantCoeff = 0)
    (polynomial : ℂ[X]) (hpolynomial : polynomial ≠ 0) :
    Polynomial.aeval
        ((algebraMap PS LS reciprocal)⁻¹) polynomial ≠ 0 := by
  let reciprocalLaurent : LS := algebraMap PS LS reciprocal
  have hreciprocalLaurent : reciprocalLaurent ≠ 0 := by
    simpa only [reciprocalLaurent, map_zero] using
      (FaithfulSMul.algebraMap_injective PS LS).ne hreciprocal
  let hidden : LS := reciprocalLaurent⁻¹
  have hhidden : hidden ≠ 0 := by
    exact inv_ne_zero hreciprocalLaurent
  letI : Invertible hidden := invertibleOfNonzero hhidden
  intro hevaluation
  have hreversalProduct :=
    Polynomial.eval₂_reverse_mul_pow
      (algebraMap ℂ LS) hidden polynomial
  have hinverseHidden : ⅟hidden = reciprocalLaurent := by
    rw [invOf_eq_inv]
    simp [hidden, reciprocalLaurent, hreciprocalLaurent]
  rw [hinverseHidden] at hreversalProduct
  have hreversalLaurent :
      Polynomial.eval₂ (algebraMap ℂ LS) reciprocalLaurent
          polynomial.reverse = 0 := by
    apply (mul_eq_zero.mp ?_).resolve_right (pow_ne_zero _ hhidden)
    rw [hreversalProduct]
    simpa only [hidden, reciprocalLaurent, Polynomial.aeval_def] using
      hevaluation
  have hreversalPower :
      Polynomial.aeval reciprocal polynomial.reverse = 0 := by
    apply FaithfulSMul.algebraMap_injective PS LS
    rw [map_zero]
    simpa only [reciprocalLaurent, Polynomial.aeval_def] using
      hreversalLaurent
  have hconstantCoefficient :=
    congrArg PowerSeries.constantCoeff hreversalPower
  have hleading : polynomial.leadingCoeff ≠ 0 :=
    Polynomial.leadingCoeff_ne_zero.mpr hpolynomial
  apply hleading
  simpa [Polynomial.aeval_def, hconstant,
    Polynomial.coeff_zero_reverse] using hconstantCoefficient

/-- Aggregated reusable pole certificate. -/
theorem laurent_inverse_polynomial_nonvanishing_terminal_certificate :
    ∀ (reciprocal : PS), reciprocal ≠ 0 →
      reciprocal.constantCoeff = 0 →
      ∀ polynomial : ℂ[X], polynomial ≠ 0 →
        Polynomial.aeval
          ((algebraMap PS LS reciprocal)⁻¹) polynomial ≠ 0 := by
  intro reciprocal hreciprocal hconstant polynomial hpolynomial
  exact polynomial_aeval_inverse_ne_zero reciprocal hreciprocal hconstant
    polynomial hpolynomial

end

end FormalLaurentInversePolynomialNonvanishing
