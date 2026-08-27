import Mathlib.Algebra.Polynomial.Degree.Operations
import ZtareProofs.FormalOneWeightIrreducibleContraction

/-!
# Reflecting one-weight support through an injective coefficient map

Coefficient-field localization is useful for differential equations, but the
irreducible factor belongs to the pre-localized polynomial ring.  An
injective coefficient map preserves degree and leading coefficient, so a
one-weight identity in the target reflects directly to the source.  No
irreducibility transport is required.
-/

namespace FormalOneWeightMapDescent

open Polynomial
open ZtareProofs.FormalOneWeightIrreducibleContraction

/-- A one-weight equation reflects through every injective coefficient map. -/
theorem eq_monomial_of_map_eq_monomial
    {A K : Type*} [Semiring A] [Semiring K]
    (f : A →+* K) (hf : Function.Injective f) (polynomial : A[X])
    (hmapped :
      polynomial.map f =
        monomial (polynomial.map f).natDegree
          (polynomial.map f).leadingCoeff) :
    polynomial = monomial polynomial.natDegree polynomial.leadingCoeff := by
  apply Polynomial.map_injective f hf
  rw [map_monomial]
  simpa only [natDegree_map_eq_of_injective hf,
    leadingCoeff_map_of_injective hf] using hmapped

/-- If an irreducible polynomial becomes one-weight after an injective
coefficient extension, it was already either constant or associated to the
displayed variable over the original domain. -/
theorem natDegree_eq_zero_or_associated_X_of_map_eq_monomial
    {A K : Type*} [CommRing A] [IsDomain A] [CommRing K]
    (f : A →+* K) (hf : Function.Injective f) (polynomial : A[X])
    (hirreducible : Irreducible polynomial)
    (hmapped :
      polynomial.map f =
        monomial (polynomial.map f).natDegree
          (polynomial.map f).leadingCoeff) :
    polynomial.natDegree = 0 ∨ Associated polynomial X := by
  exact natDegree_eq_zero_or_associated_X polynomial hirreducible
    (eq_monomial_of_map_eq_monomial f hf polynomial hmapped)

/-- Aggregated one-weight localization-descent certificate. -/
theorem one_weight_map_descent_terminal_certificate :
    ∀ {A K : Type*} [CommRing A] [IsDomain A] [CommRing K]
      (f : A →+* K), Function.Injective f →
      ∀ (polynomial : A[X]), Irreducible polynomial →
      polynomial.map f =
          monomial (polynomial.map f).natDegree
            (polynomial.map f).leadingCoeff →
      polynomial.natDegree = 0 ∨ Associated polynomial X := by
  intro A K _ _ _ f hf polynomial hirreducible hmapped
  exact natDegree_eq_zero_or_associated_X_of_map_eq_monomial
    f hf polynomial hirreducible hmapped

end FormalOneWeightMapDescent
