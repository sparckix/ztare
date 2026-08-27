import Mathlib.RingTheory.Localization.Integral
import Mathlib.Tactic
import ZtareProofs.FormalFiniteDerivativeDarbouxAlternative
import ZtareProofs.FormalFiniteLocalizationEliminant
import ZtareProofs.FormalPrimitiveDarbouxFractionDescent

/-!
# Localized derivative-prefix dichotomy

The coefficient extension `A → Frac(A)` converts `A[Y]` into the PID
`Frac(A)[Y]`.  This file first proves that a pair of intertwined derivations
carry the entire finite derivative-prefix ideal across that extension.  The
unit-ideal branch then contracts to a nonzero coefficient in `A`.

The complementary branch is completed below by primitive Gauss descent: its
fraction-field Darboux prime is replaced by a primitive irreducible
representative in `A[Y]`.
-/

namespace FormalLocalizedDerivativeDarbouxDichotomy

open Ideal Polynomial
open FormalFiniteDerivativeDarbouxAlternative
open FormalFiniteLocalizationEliminant
open ZtareProofs.FormalPrimitiveDarbouxFractionDescent

noncomputable section

/-- Intertwining one derivation step intertwines every natural iterate. -/
theorem map_iterate_of_intertwines
    {R S : Type*} [CommRing R] [CommRing S]
    (D_R : Derivation ℤ R R) (D_S : Derivation ℤ S S)
    (phi : R →+* S)
    (hintertwines : ∀ value : R, phi (D_R value) = D_S (phi value)) :
    ∀ order value,
      phi (((D_R : R → R)^[order]) value) =
        ((D_S : S → S)^[order]) (phi value) := by
  intro order
  induction order with
  | zero =>
      intro value
      rfl
  | succ order inductionHypothesis =>
      intro value
      rw [Function.iterate_succ_apply', Function.iterate_succ_apply',
        hintertwines, inductionHypothesis]

/-- A commuting coefficient extension maps the complete derivative-prefix
ideal to the derivative-prefix ideal of the mapped initial polynomial. -/
theorem map_derivativePrefixIdeal
    {R S : Type*} [CommRing R] [CommRing S]
    (D_R : Derivation ℤ R R) (D_S : Derivation ℤ S S)
    (phi : R →+* S)
    (hintertwines : ∀ value : R, phi (D_R value) = D_S (phi value))
    (initial : R) (bound : ℕ) :
    (derivativePrefixIdeal D_R initial bound).map phi =
      derivativePrefixIdeal D_S (phi initial) bound := by
  rw [derivativePrefixIdeal, derivativePrefixIdeal, Ideal.map_span]
  congr 1
  ext value
  constructor
  · rintro ⟨source, ⟨index, rfl⟩, rfl⟩
    exact ⟨index,
      (map_iterate_of_intertwines
        D_R D_S phi hintertwines index.1 initial).symm⟩
  · rintro ⟨index, rfl⟩
    refine ⟨((D_R : R → R)^[index.1]) initial, ⟨index, rfl⟩, ?_⟩
    exact map_iterate_of_intertwines
      D_R D_S phi hintertwines index.1 initial

/-- If the localized derivative prefix is the unit ideal, clearing its
finitely many coefficient denominators produces a nonzero base eliminant. -/
theorem exists_base_eliminant_of_localized_derivativePrefixIdeal_eq_top
    {A L : Type*}
    [CommRing A] [IsDomain A]
    [Field L] [Algebra A L] [IsFractionRing A L]
    (D_A : Derivation ℤ A[X] A[X])
    (D_L : Derivation ℤ L[X] L[X])
    (hintertwines : ∀ polynomial : A[X],
      (D_A polynomial).map (algebraMap A L) =
        D_L (polynomial.map (algebraMap A L)))
    (initial : A[X]) (bound : ℕ)
    (htop : derivativePrefixIdeal D_L
      (initial.map (algebraMap A L)) bound = ⊤) :
    ∃ d : A, d ≠ 0 ∧
      C d ∈ derivativePrefixIdeal D_A initial bound := by
  apply exists_nonzero_base_eliminant_of_polynomial_mapped_span_eq_top
    (A := A) (K := L)
    (fun index : Fin (bound + 1) ↦
      ((D_A : A[X] → A[X])^[index.1]) initial)
  change Ideal.span
      (Set.range
        ((Polynomial.mapRingHom (algebraMap A L)) ∘
          fun index : Fin (bound + 1) ↦
            ((D_A : A[X] → A[X])^[index.1]) initial)) = ⊤
  rw [Set.range_comp, ← Ideal.map_span]
  change (derivativePrefixIdeal D_A initial bound).map
    (Polynomial.mapRingHom (algebraMap A L)) = ⊤
  rw [map_derivativePrefixIdeal D_A D_L
    (Polynomial.mapRingHom (algebraMap A L)) hintertwines initial bound]
  exact htop

/-- The unconditional localized finite-prefix alternative.  Either clearing
the localized unit-ideal certificate produces a nonzero base eliminant, or
the fraction-field Darboux prime contracts to a primitive irreducible Darboux
factor over the original coefficient domain. -/
theorem exists_base_eliminant_or_primitive_darboux_factor
    {A L : Type*}
    [CommRing A] [IsDomain A] [NormalizedGCDMonoid A]
    [Field L] [CharZero L] [Algebra A L] [IsFractionRing A L]
    (D_A : Derivation ℤ A[X] A[X])
    (D_L : Derivation ℤ L[X] L[X])
    (hintertwines : ∀ polynomial : A[X],
      (D_A polynomial).map (algebraMap A L) =
        D_L (polynomial.map (algebraMap A L)))
    (initial : A[X]) (hinitial : initial ≠ 0) :
    (∃ d : A, d ≠ 0 ∧
      C d ∈ derivativePrefixIdeal D_A initial initial.natDegree) ∨
    (∃ hA : A[X],
      Irreducible hA ∧ hA ∣ initial ∧ hA ∣ D_A hA) := by
  have hinitialMapped : initial.map (algebraMap A L) ≠ 0 :=
    (Polynomial.map_ne_zero_iff (IsFractionRing.injective A L)).2 hinitial
  obtain htop | ⟨hL, hprime, hdivInitial, hdarboux⟩ :=
    polynomial_derivativePrefixIdeal_top_or_exists_darboux_prime
      D_L (initial.map (algebraMap A L)) hinitialMapped
  · left
    rw [Polynomial.natDegree_map_eq_of_injective
      (IsFractionRing.injective A L)] at htop
    exact exists_base_eliminant_of_localized_derivativePrefixIdeal_eq_top
      D_A D_L hintertwines initial initial.natDegree htop
  · right
    have hirreducibleL : Irreducible hL := irreducible_iff_prime.mpr hprime
    have hdescent :=
      primitive_darboux_fraction_descent_terminal_certificate
        (A := A) (L := L) hirreducibleL
        D_A D_L hintertwines hdarboux
    exact ⟨primitiveFractionRepresentative hL,
      hdescent.2.1,
      hdescent.2.2.2.1 initial hdivInitial,
      hdescent.2.2.2.2⟩

/-- Aggregated localized derivative-prefix certificate. -/
theorem localized_derivative_darboux_dichotomy_terminal_certificate :
    ∀ {A L : Type*}
      [CommRing A] [IsDomain A] [NormalizedGCDMonoid A]
      [Field L] [CharZero L] [Algebra A L] [IsFractionRing A L]
      (D_A : Derivation ℤ A[X] A[X])
      (D_L : Derivation ℤ L[X] L[X]),
      (∀ polynomial : A[X],
        (D_A polynomial).map (algebraMap A L) =
          D_L (polynomial.map (algebraMap A L))) →
      ∀ initial : A[X], initial ≠ 0 →
        (∃ d : A, d ≠ 0 ∧
          C d ∈ derivativePrefixIdeal D_A initial initial.natDegree) ∨
        (∃ hA : A[X],
          Irreducible hA ∧ hA ∣ initial ∧ hA ∣ D_A hA) := by
  intro A L _ _ _ _ _ _ _ D_A D_L hintertwines initial hinitial
  exact exists_base_eliminant_or_primitive_darboux_factor
    D_A D_L hintertwines initial hinitial

end

end FormalLocalizedDerivativeDarbouxDichotomy
