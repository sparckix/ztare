import Mathlib.RingTheory.UniqueFactorizationDomain.GCDMonoid
import ZtareProofs.FormalLocalizedDerivativeDarbouxDichotomy
import ZtareProofs.FormalPolynomialDerivationRatFuncExtension

/-!
# Polynomial total-derivative dichotomy with canonical localization

This module hides the normalization and integer-algebra choices used to pass
from `K[F][Y]` to `RatFunc(K)[Y]`.  Its exported theorem mentions only the
original polynomial domain: either the finite derivative prefix contains a
nonzero coefficient polynomial, or the initial relation has an irreducible
Darboux factor in that original domain.
-/

namespace FormalPolynomialTotalDerivativeDichotomy

open Polynomial
open FormalDifferentialPolynomialInvariantSpecialization
open FormalFiniteDerivativeDarbouxAlternative
open FormalLocalizedDerivativeDarbouxDichotomy
open FormalPolynomialDerivationRatFuncExtension

variable {K : Type*} [Field K] [CharZero K]

noncomputable local instance ratFuncCanonicalIntAlgebra :
    Algebra ℤ (RatFunc K) :=
  Ring.toIntAlgebra (RatFunc K)

noncomputable local instance fieldNormalizationMonoid :
    NormalizationMonoid K :=
  UniqueFactorizationMonoid.normalizationMonoid

noncomputable local instance fieldNormalizedGCDMonoid :
    NormalizedGCDMonoid K :=
  UniqueFactorizationMonoid.toNormalizedGCDMonoid K

noncomputable local instance polynomialNormalizedGCDMonoid :
    NormalizedGCDMonoid K[X] :=
  Polynomial.normalizedGcdMonoid

/-- Canonically localize a polynomial total derivation and hide the
localization choices from the resulting polynomial-domain alternative. -/
theorem exists_base_eliminant_or_primitive_darboux_factor_for_total_derivation
    (coefficientDerivation : Derivation ℤ K[X] K[X])
    (velocity initial : K[X][X]) (hinitial : initial ≠ 0) :
    (∃ eliminant : K[X], eliminant ≠ 0 ∧
      C eliminant ∈ derivativePrefixIdeal
        (polynomialTotalDerivation coefficientDerivation velocity)
        initial initial.natDegree) ∨
    (∃ h : K[X][X],
      Irreducible h ∧ h ∣ initial ∧
        h ∣ polynomialTotalDerivation coefficientDerivation velocity h) := by
  exact exists_base_eliminant_or_primitive_darboux_factor
    (A := K[X]) (L := RatFunc K)
    (polynomialTotalDerivation coefficientDerivation velocity)
    (localizedPolynomialTotalDerivation coefficientDerivation velocity)
    (map_localizedPolynomialTotalDerivation coefficientDerivation velocity)
    initial hinitial

/-- Aggregated total-derivation localization certificate. -/
theorem polynomial_total_derivative_dichotomy_terminal_certificate :
    ∀ (coefficientDerivation : Derivation ℤ K[X] K[X])
      (velocity initial : K[X][X]), initial ≠ 0 →
      (∃ eliminant : K[X], eliminant ≠ 0 ∧
        C eliminant ∈ derivativePrefixIdeal
          (polynomialTotalDerivation coefficientDerivation velocity)
          initial initial.natDegree) ∨
      (∃ h : K[X][X],
        Irreducible h ∧ h ∣ initial ∧
          h ∣ polynomialTotalDerivation coefficientDerivation velocity h) := by
  intro coefficientDerivation velocity initial hinitial
  exact exists_base_eliminant_or_primitive_darboux_factor_for_total_derivation
    coefficientDerivation velocity initial hinitial

end FormalPolynomialTotalDerivativeDichotomy
