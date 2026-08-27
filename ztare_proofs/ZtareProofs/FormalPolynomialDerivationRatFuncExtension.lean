import Mathlib.FieldTheory.RatFunc.AsPolynomial
import Mathlib.RingTheory.Derivation.Basic
import Mathlib.Tactic
import ZtareProofs.FormalDifferentialPolynomialInvariantSpecialization

/-!
# Extending a polynomial derivation to the rational-function field

Every derivation on `K[X]` extends by the quotient rule to `RatFunc K`.
Unlike ordinary rational differentiation, the input derivation may also act
on coefficients.  This is the localization adapter needed when a bivariate
total derivation is viewed as a univariate derivation over `Frac(K[X])`.
-/

namespace FormalPolynomialDerivationRatFuncExtension

open Polynomial
open FormalDifferentialPolynomialInvariantSpecialization

variable {K : Type*} [Field K]

/-- Quotient-rule extension of an arbitrary polynomial derivation on one
chosen numerator/denominator presentation. -/
noncomputable def quotientDerivation
    (D : Derivation ℤ K[X] K[X])
    (numerator denominator : K[X]) : RatFunc K :=
  (algebraMap K[X] (RatFunc K) (D numerator) *
        algebraMap K[X] (RatFunc K) denominator -
      algebraMap K[X] (RatFunc K) numerator *
        algebraMap K[X] (RatFunc K) (D denominator)) /
    algebraMap K[X] (RatFunc K) denominator ^ 2

/-- Multiplying numerator and denominator by the same nonzero polynomial
does not change the quotient-rule value. -/
theorem quotientDerivation_mul_common
    (D : Derivation ℤ K[X] K[X])
    (numerator denominator common : K[X])
    (hdenominator : denominator ≠ 0) (hcommon : common ≠ 0) :
    quotientDerivation D (common * numerator) (common * denominator) =
      quotientDerivation D numerator denominator := by
  rw [quotientDerivation, quotientDerivation]
  simp only [Derivation.leibniz, smul_eq_mul, map_add, map_mul]
  field_simp [RatFunc.algebraMap_ne_zero hdenominator,
    RatFunc.algebraMap_ne_zero hcommon]
  ring

/-- The extension of `D` to the rational-function field. -/
noncomputable def rationalExtension
    (D : Derivation ℤ K[X] K[X])
    (value : RatFunc K) : RatFunc K :=
  value.liftOn' (quotientDerivation D) (by
    intro numerator denominator common hdenominator hcommon
    exact quotientDerivation_mul_common D numerator denominator common
      hdenominator hcommon)

/-- Exact quotient rule for arbitrary polynomial representatives. -/
theorem rationalExtension_div
    (D : Derivation ℤ K[X] K[X])
    (numerator denominator : K[X]) :
    rationalExtension D
        (algebraMap K[X] (RatFunc K) numerator /
          algebraMap K[X] (RatFunc K) denominator) =
      quotientDerivation D numerator denominator := by
  rw [rationalExtension]
  apply RatFunc.liftOn'_div
  intro polynomial
  simp [quotientDerivation]

/-- The rational extension is additive. -/
theorem rationalExtension_add
    (D : Derivation ℤ K[X] K[X])
    (first second : RatFunc K) :
    rationalExtension D (first + second) =
      rationalExtension D first + rationalExtension D second := by
  induction first using RatFunc.induction_on with
  | f firstNumerator firstDenominator hfirstDenominator =>
      induction second using RatFunc.induction_on with
      | f secondNumerator secondDenominator hsecondDenominator =>
          have hproduct :
              firstDenominator * secondDenominator ≠ 0 :=
            mul_ne_zero hfirstDenominator hsecondDenominator
          rw [show
              algebraMap K[X] (RatFunc K) firstNumerator /
                    algebraMap K[X] (RatFunc K) firstDenominator +
                  algebraMap K[X] (RatFunc K) secondNumerator /
                    algebraMap K[X] (RatFunc K) secondDenominator =
                algebraMap K[X] (RatFunc K)
                      (firstNumerator * secondDenominator +
                        firstDenominator * secondNumerator) /
                    algebraMap K[X] (RatFunc K)
                      (firstDenominator * secondDenominator) by
                simp only [map_add, map_mul]
                field_simp [RatFunc.algebraMap_ne_zero hfirstDenominator,
                  RatFunc.algebraMap_ne_zero hsecondDenominator]]
          rw [rationalExtension_div, rationalExtension_div,
            rationalExtension_div]
          rw [quotientDerivation, quotientDerivation, quotientDerivation]
          simp only [Derivation.leibniz, smul_eq_mul,
            map_add, map_mul]
          field_simp [RatFunc.algebraMap_ne_zero hfirstDenominator,
            RatFunc.algebraMap_ne_zero hsecondDenominator,
            RatFunc.algebraMap_ne_zero hproduct]
          ring

/-- The rational extension obeys Leibniz. -/
theorem rationalExtension_mul
    (D : Derivation ℤ K[X] K[X])
    (first second : RatFunc K) :
    rationalExtension D (first * second) =
      first * rationalExtension D second +
        second * rationalExtension D first := by
  induction first using RatFunc.induction_on with
  | f firstNumerator firstDenominator hfirstDenominator =>
      induction second using RatFunc.induction_on with
      | f secondNumerator secondDenominator hsecondDenominator =>
          have hproduct :
              firstDenominator * secondDenominator ≠ 0 :=
            mul_ne_zero hfirstDenominator hsecondDenominator
          rw [show
              (algebraMap K[X] (RatFunc K) firstNumerator /
                    algebraMap K[X] (RatFunc K) firstDenominator) *
                  (algebraMap K[X] (RatFunc K) secondNumerator /
                    algebraMap K[X] (RatFunc K) secondDenominator) =
                algebraMap K[X] (RatFunc K)
                      (firstNumerator * secondNumerator) /
                    algebraMap K[X] (RatFunc K)
                      (firstDenominator * secondDenominator) by
                simp only [map_mul]
                exact div_mul_div_comm _ _ _ _]
          rw [rationalExtension_div, rationalExtension_div,
            rationalExtension_div]
          rw [quotientDerivation, quotientDerivation, quotientDerivation]
          simp only [Derivation.leibniz, smul_eq_mul,
            map_add, map_mul]
          field_simp [RatFunc.algebraMap_ne_zero hfirstDenominator,
            RatFunc.algebraMap_ne_zero hsecondDenominator,
            RatFunc.algebraMap_ne_zero hproduct]
          ring

/-- The additive-hom surface of the rational extension. -/
noncomputable def rationalExtensionAddHom
    (D : Derivation ℤ K[X] K[X]) : RatFunc K →+ RatFunc K where
  toFun := rationalExtension D
  map_zero' := by
    simpa [quotientDerivation] using
      (rationalExtension_div D (0 : K[X]) 1)
  map_add' := rationalExtension_add D

/-- Use the canonical integer algebra expected by integer-linear derivation
kernels, avoiding the non-definitional tower-induced instance. -/
noncomputable local instance ratFuncCanonicalIntAlgebra :
    Algebra ℤ (RatFunc K) :=
  Ring.toIntAlgebra (RatFunc K)

/-- The quotient-rule extension packaged as an integer derivation. -/
noncomputable def ratFuncExtensionDerivation
    (D : Derivation ℤ K[X] K[X]) :
    Derivation ℤ (RatFunc K) (RatFunc K) :=
  Derivation.mk'
    (rationalExtensionAddHom D).toIntLinearMap
    (by
      intro first second
      simpa only [smul_eq_mul] using rationalExtension_mul D first second)

@[simp]
theorem ratFuncExtensionDerivation_apply
    (D : Derivation ℤ K[X] K[X]) (value : RatFunc K) :
    ratFuncExtensionDerivation D value = rationalExtension D value :=
  rfl

/-- The extension intertwines the canonical polynomial algebra map. -/
theorem ratFuncExtensionDerivation_algebraMap
    (D : Derivation ℤ K[X] K[X]) (polynomial : K[X]) :
    ratFuncExtensionDerivation D
        (algebraMap K[X] (RatFunc K) polynomial) =
      algebraMap K[X] (RatFunc K) (D polynomial) := by
  have hquotient := rationalExtension_div D polynomial 1
  simpa [quotientDerivation] using hquotient

/-- Extend a polynomial total derivation one variable further after
localizing its coefficient ring. -/
noncomputable def localizedPolynomialTotalDerivation
    (D : Derivation ℤ K[X] K[X]) (velocity : K[X][X]) :
    Derivation ℤ (RatFunc K)[X] (RatFunc K)[X] :=
  polynomialTotalDerivation
    (ratFuncExtensionDerivation D)
    (velocity.map (algebraMap K[X] (RatFunc K)))

/-- Coefficient localization intertwines the complete polynomial total
derivations. -/
theorem map_localizedPolynomialTotalDerivation
    (D : Derivation ℤ K[X] K[X]) (velocity polynomial : K[X][X]) :
    (polynomialTotalDerivation D velocity polynomial).map
          (algebraMap K[X] (RatFunc K)) =
      localizedPolynomialTotalDerivation D velocity
        (polynomial.map (algebraMap K[X] (RatFunc K))) := by
  exact map_polynomialTotalDerivation
    D (ratFuncExtensionDerivation D)
    (algebraMap K[X] (RatFunc K))
    velocity (velocity.map (algebraMap K[X] (RatFunc K)))
    (fun value ↦ (ratFuncExtensionDerivation_algebraMap D value).symm)
    rfl polynomial

/-- Aggregated arbitrary-polynomial-derivation localization certificate. -/
theorem polynomial_derivation_ratfunc_extension_terminal_certificate :
    ∀ (D : Derivation ℤ K[X] K[X]),
      (∀ polynomial : K[X],
        ratFuncExtensionDerivation D
            (algebraMap K[X] (RatFunc K) polynomial) =
          algebraMap K[X] (RatFunc K) (D polynomial)) ∧
      ∀ (velocity polynomial : K[X][X]),
        (polynomialTotalDerivation D velocity polynomial).map
              (algebraMap K[X] (RatFunc K)) =
          localizedPolynomialTotalDerivation D velocity
            (polynomial.map (algebraMap K[X] (RatFunc K))) := by
  intro D
  exact ⟨ratFuncExtensionDerivation_algebraMap D,
    map_localizedPolynomialTotalDerivation D⟩

end FormalPolynomialDerivationRatFuncExtension
