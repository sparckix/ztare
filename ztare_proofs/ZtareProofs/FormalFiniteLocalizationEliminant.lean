import Mathlib.RingTheory.Localization.Ideal
import Mathlib.RingTheory.Localization.Integral
import Mathlib.RingTheory.MvPolynomial.Localization

/-!
# Clearing a finite localization certificate to a base eliminant

If an ideal becomes the unit ideal after localization, one element of the
localizing submonoid already belongs to the original ideal.  Applied to a
polynomial ring localized only in its coefficient ring, this produces a
nonzero constant polynomial in the hidden variables.  In an elimination
problem that coefficient is the endpoint eliminant.

This file does not prove coprimality of a polynomial prefix, factor any
polynomial, or compute Bezout coefficients.
-/

namespace FormalFiniteLocalizationEliminant

open Ideal IsLocalization
open Polynomial

noncomputable section

/-- Unit-ideal generation after localization clears to one localizing
element in the original ideal. -/
theorem exists_localizing_element_mem_ideal_of_map_eq_top
    {R S : Type*} [CommSemiring R] [CommSemiring S]
    (M : Submonoid R) [Algebra R S] [IsLocalization M S]
    (I : Ideal R)
    (hlocalized : I.map (algebraMap R S) = ⊤) :
    ∃ m : M, (m : R) ∈ I := by
  have hone : algebraMap R S (1 : R) ∈ I.map (algebraMap R S) := by
    rw [hlocalized]
    simp
  obtain ⟨m, hmM, hmI⟩ :=
    (IsLocalization.algebraMap_mem_map_algebraMap_iff M S I (1 : R)).mp
      hone
  exact ⟨⟨m, hmM⟩, by simpa using hmI⟩

/-- If polynomials become unit-ideal generators after passing from a domain
to its fraction field, their original ideal contains a nonzero coefficient
polynomial, constant in every displayed polynomial variable. -/
theorem exists_nonzero_base_eliminant_of_mapped_span_eq_top
    {A K σ ι : Type*}
    [CommRing A] [IsDomain A]
    [Field K] [Algebra A K] [IsFractionRing A K]
    (generators : ι → MvPolynomial σ A)
    (hlocalized :
      Ideal.span
          (Set.range fun i ↦
            MvPolynomial.map (algebraMap A K) (generators i)) = ⊤) :
    ∃ d : A,
      d ≠ 0 ∧
      MvPolynomial.C d ∈ Ideal.span (Set.range generators) := by
  letI : Algebra (MvPolynomial σ A) (MvPolynomial σ K) :=
    MvPolynomial.algebraMvPolynomial
  haveI : IsLocalization
      ((nonZeroDivisors A).map
        (MvPolynomial.C : A →+* MvPolynomial σ A))
      (MvPolynomial σ K) :=
    MvPolynomial.isLocalization (nonZeroDivisors A) K
  have halgebraMap :
      algebraMap (MvPolynomial σ A) (MvPolynomial σ K) =
        MvPolynomial.map (algebraMap A K) := rfl
  let I : Ideal (MvPolynomial σ A) :=
    Ideal.span (Set.range generators)
  have hmap :
      I.map
          (algebraMap (MvPolynomial σ A) (MvPolynomial σ K)) = ⊤ := by
    dsimp only [I]
    rw [Ideal.map_span]
    rw [halgebraMap]
    rw [← Set.range_comp]
    simpa only [Function.comp_apply] using hlocalized
  obtain ⟨m, hmI⟩ :=
    exists_localizing_element_mem_ideal_of_map_eq_top
      ((nonZeroDivisors A).map
        (MvPolynomial.C : A →+* MvPolynomial σ A))
      I hmap
  obtain ⟨d, hd, hdm⟩ := Submonoid.mem_map.mp m.property
  refine ⟨d, (mem_nonZeroDivisors_iff_ne_zero.mp hd), ?_⟩
  rw [hdm]
  exact hmI

/-- The univariate form of coefficient-localization elimination.  Keeping
the coefficient ring explicit is important in bivariate applications: if
`A = K[F]` and the displayed polynomial variable is `Y`, the resulting
element `d : A` is an eliminant in the visible variable `F`. -/
theorem exists_nonzero_base_eliminant_of_polynomial_mapped_span_eq_top
    {A K ι : Type*}
    [CommRing A] [IsDomain A]
    [Field K] [Algebra A K] [IsFractionRing A K]
    (generators : ι → A[X])
    (hlocalized :
      Ideal.span
          (Set.range fun i ↦
            (generators i).map (algebraMap A K)) = ⊤) :
    ∃ d : A,
      d ≠ 0 ∧
      Polynomial.C d ∈ Ideal.span (Set.range generators) := by
  letI : Algebra A[X] K[X] := Polynomial.algebra A K
  haveI : IsLocalization
      ((nonZeroDivisors A).map
        (Polynomial.C : A →+* A[X]))
      K[X] :=
    Polynomial.isLocalization (nonZeroDivisors A) K
  have halgebraMap :
      algebraMap A[X] K[X] = Polynomial.mapRingHom (algebraMap A K) := rfl
  let I : Ideal A[X] := Ideal.span (Set.range generators)
  have hmap : I.map (algebraMap A[X] K[X]) = ⊤ := by
    dsimp only [I]
    rw [Ideal.map_span]
    rw [halgebraMap]
    rw [← Set.range_comp]
    simpa only [Function.comp_apply] using hlocalized
  obtain ⟨m, hmI⟩ :=
    exists_localizing_element_mem_ideal_of_map_eq_top
      ((nonZeroDivisors A).map
        (Polynomial.C : A →+* A[X]))
      I hmap
  obtain ⟨d, hd, hdm⟩ := Submonoid.mem_map.mp m.property
  refine ⟨d, (mem_nonZeroDivisors_iff_ne_zero.mp hd), ?_⟩
  rw [hdm]
  exact hmI

/-- Aggregated denominator-clearing surface for finite-prefix consumers. -/
theorem finite_localization_eliminant_terminal_certificate :
    ∀ {A K σ ι : Type*}
      [CommRing A] [IsDomain A]
      [Field K] [Algebra A K] [IsFractionRing A K]
      (generators : ι → MvPolynomial σ A),
      Ideal.span
          (Set.range fun i ↦
            MvPolynomial.map (algebraMap A K) (generators i)) = ⊤ →
      ∃ d : A,
        d ≠ 0 ∧
        MvPolynomial.C d ∈ Ideal.span (Set.range generators) := by
  intro A K σ ι _ _ _ _ _ generators hlocalized
  exact exists_nonzero_base_eliminant_of_mapped_span_eq_top
    generators hlocalized

/-- Aggregated univariate denominator-clearing surface. -/
theorem polynomial_finite_localization_eliminant_terminal_certificate :
    ∀ {A K ι : Type*}
      [CommRing A] [IsDomain A]
      [Field K] [Algebra A K] [IsFractionRing A K]
      (generators : ι → A[X]),
      Ideal.span
          (Set.range fun i ↦
            (generators i).map (algebraMap A K)) = ⊤ →
      ∃ d : A,
        d ≠ 0 ∧
        Polynomial.C d ∈ Ideal.span (Set.range generators) := by
  intro A K ι _ _ _ _ _ generators hlocalized
  exact exists_nonzero_base_eliminant_of_polynomial_mapped_span_eq_top
    generators hlocalized

end

end FormalFiniteLocalizationEliminant
