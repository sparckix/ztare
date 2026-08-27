import Mathlib.FieldTheory.Minpoly.Field
import Mathlib.Tactic
import ZtareProofs.FormalCriticalRationalEigenrowExclusion
import ZtareProofs.FormalDifferentialGermEvaluation
import ZtareProofs.FormalFilteredDarbouxPolynomialBinding

/-!
# Algebraic eigenvectors force forbidden Darboux minimal polynomials

Let a differential field embed compatibly into another differential field.
If an algebraic element satisfies the scalar equation `D x = L x`, then its
minimal polynomial is preserved by the Euler-filtered derivation
`d + L X d/dX`.  Cross-weight nonresonance collapses that minimal polynomial
to one monomial.  Irreducibility then makes it associated to `X`, forcing the
element to vanish.

The critical specialization consumes the existing irrational-residue
cross-weight theorem over `RatFunc Real`; it adds no analytic continuation or
new residue assumption.
-/

namespace FormalAlgebraicEigenvectorDarbouxExclusion

open Polynomial
open FormalCriticalConnectionRationalization
open FormalCriticalRationalEigenrowExclusion
open FormalDifferentialGermEvaluation
open FormalFilteredDarbouxPolynomialBinding

noncomputable section

variable {K E : Type*} [Field K] [Field E] [Algebra K E]

abbrev CriticalRF := RatFunc ℝ

/-- Differentiating the minimal-polynomial root equation makes the minimal
polynomial a Darboux divisor for the Euler-filtered connection. -/
theorem minpoly_dvd_filteredDarbouxDerivation_of_eigenvector
    (dK : Derivation ℤ K K) (dE : Derivation ℤ E E)
    (logarithmicWeight : K) (element : E)
    (hcoefficients : ∀ coefficient : K,
      algebraMap K E (dK coefficient) =
        dE (algebraMap K E coefficient))
    (heigenvector :
      dE element = algebraMap K E logarithmicWeight * element) :
    minpoly K element ∣
      filteredDarbouxDerivation dK logarithmicWeight
        (minpoly K element) := by
  have hpoint :
      dE element =
        (C logarithmicWeight * X).eval₂ (algebraMap K E) element := by
    simpa using heigenvector
  have hintertwines :=
    eval₂_polynomialTotalDerivation dK dE (algebraMap K E)
      (C logarithmicWeight * X) element hcoefficients hpoint
      (minpoly K element)
  have hroot :
      (minpoly K element).eval₂ (algebraMap K E) element = 0 := by
    simpa [Polynomial.aeval_def] using minpoly.aeval K element
  have hderivativeRoot :
      (filteredDarbouxDerivation dK logarithmicWeight
          (minpoly K element)).eval₂ (algebraMap K E) element = 0 := by
    rw [filteredDarbouxDerivation]
    rw [hintertwines, hroot, map_zero]
  exact minpoly.dvd K element (by
    simpa [Polynomial.aeval_def] using hderivativeRoot)

/-- A nonzero algebraic scalar eigenvector cannot exist when every pair of
distinct occupied weights is nonresonant over the coefficient field. -/
theorem no_nonzero_algebraic_eigenvector_of_no_weight_resonance
    (dK : Derivation ℤ K K) (dE : Derivation ℤ E E)
    (logarithmicWeight : K) (element : E)
    (hcoefficients : ∀ coefficient : K,
      algebraMap K E (dK coefficient) =
        dE (algebraMap K E coefficient))
    (heigenvector :
      dE element = algebraMap K E logarithmicWeight * element)
    (halgebraic : IsAlgebraic K element)
    (helement : element ≠ 0)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      (minpoly K element).coeff firstWeight ≠ 0 →
      (minpoly K element).coeff secondWeight ≠ 0 →
      (minpoly K element).coeff secondWeight *
            dK ((minpoly K element).coeff firstWeight) -
          (minpoly K element).coeff firstWeight *
            dK ((minpoly K element).coeff secondWeight) ≠
        ((secondWeight : K) - (firstWeight : K)) *
          logarithmicWeight *
          (minpoly K element).coeff firstWeight *
          (minpoly K element).coeff secondWeight) :
    False := by
  have hintegral : IsIntegral K element := halgebraic.isIntegral
  have hminpolyNonzero : minpoly K element ≠ 0 :=
    minpoly.ne_zero hintegral
  have hdivisor :
      minpoly K element ∣
        filteredDarbouxDerivation dK logarithmicWeight
          (minpoly K element) :=
    minpoly_dvd_filteredDarbouxDerivation_of_eigenvector
      dK dE logarithmicWeight element hcoefficients heigenvector
  have hmonomial :
      minpoly K element =
        monomial (minpoly K element).natDegree
          (minpoly K element).leadingCoeff :=
    eq_monomial_of_darboux_dvd_and_no_weight_resonance
      dK logarithmicWeight (minpoly K element) hminpolyNonzero
      hdivisor hnoResonance
  have hirreducible : Irreducible (minpoly K element) :=
    minpoly.irreducible hintegral
  rcases
      natDegree_eq_zero_or_associated_X_of_irreducible_eq_monomial
        (minpoly K element) hirreducible hmonomial with
    hdegreeZero | hassociated
  · exact (Nat.ne_of_gt hirreducible.natDegree_pos) hdegreeZero
  · obtain ⟨quotient, hquotient⟩ := hassociated.dvd
    have hzero : element = 0 := by
      have hevaluated := congrArg (Polynomial.aeval element) hquotient
      simpa using hevaluated
    exact helement hzero

/-- The July critical rational connection has no nonzero algebraic
eigenvector in any compatible differential field extension. -/
theorem no_nonzero_algebraic_critical_eigenvector
    {E : Type*} [Field E] [Algebra CriticalRF E]
    (dE : Derivation ℤ E E) (element : E)
    (hcoefficients : ∀ coefficient : CriticalRF,
      algebraMap CriticalRF E
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ) coefficient) =
        dE (algebraMap CriticalRF E coefficient))
    (heigenvector :
      dE element =
        algebraMap CriticalRF E explicitRationalDifferential * element)
    (halgebraic : IsAlgebraic CriticalRF element)
    (helement : element ≠ 0) : False := by
  apply no_nonzero_algebraic_eigenvector_of_no_weight_resonance
    (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
      (K := ℝ)) dE explicitRationalDifferential
    element hcoefficients heigenvector halgebraic helement
  intro firstWeight secondWeight hweights hfirst hsecond
  exact no_distinct_natural_weight_critical_rational_cross
    firstWeight secondWeight hweights
    ((minpoly CriticalRF element).coeff firstWeight)
    ((minpoly CriticalRF element).coeff secondWeight) hfirst hsecond

/-- Aggregated general and critical algebraic-eigenvector certificate. -/
theorem algebraic_eigenvector_darboux_exclusion_terminal_certificate :
    (∀ (dK : Derivation ℤ K K) (dE : Derivation ℤ E E)
      (logarithmicWeight : K) (element : E),
      (∀ coefficient : K,
        algebraMap K E (dK coefficient) =
          dE (algebraMap K E coefficient)) →
      dE element = algebraMap K E logarithmicWeight * element →
      IsAlgebraic K element →
      element ≠ 0 →
      (∀ firstWeight secondWeight,
        firstWeight ≠ secondWeight →
        (minpoly K element).coeff firstWeight ≠ 0 →
        (minpoly K element).coeff secondWeight ≠ 0 →
        (minpoly K element).coeff secondWeight *
              dK ((minpoly K element).coeff firstWeight) -
            (minpoly K element).coeff firstWeight *
              dK ((minpoly K element).coeff secondWeight) ≠
          ((secondWeight : K) - (firstWeight : K)) *
            logarithmicWeight *
            (minpoly K element).coeff firstWeight *
            (minpoly K element).coeff secondWeight) →
      False) ∧
    (∀ {E : Type*} [Field E] [Algebra CriticalRF E]
      (dE : Derivation ℤ E E) (element : E),
      (∀ coefficient : CriticalRF,
        algebraMap CriticalRF E
            (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
              (K := ℝ) coefficient) =
          dE (algebraMap CriticalRF E coefficient)) →
      dE element =
        algebraMap CriticalRF E explicitRationalDifferential * element →
      IsAlgebraic CriticalRF element → element ≠ 0 → False) := by
  constructor
  · intro dK dE logarithmicWeight element hcoefficients heigenvector
      halgebraic helement hnoResonance
    exact no_nonzero_algebraic_eigenvector_of_no_weight_resonance
      dK dE logarithmicWeight element hcoefficients heigenvector
      halgebraic helement hnoResonance
  · intro E _ _ dE element hcoefficients heigenvector halgebraic helement
    exact no_nonzero_algebraic_critical_eigenvector
      dE element hcoefficients heigenvector halgebraic helement

end

end FormalAlgebraicEigenvectorDarbouxExclusion
