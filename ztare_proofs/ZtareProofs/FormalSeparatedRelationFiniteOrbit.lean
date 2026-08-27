import Mathlib.Algebra.Polynomial.Roots
import Mathlib.Tactic

/-!
# Finite orbit of a nonproportional separated polynomial relation

At a fixed return value, the relation

`visible * p(Y) = scalar * q(Y)`

places every finite return value in one polynomial root set.  Unless `p` and
`q` are proportional, that polynomial is nonzero whenever `(visible, scalar)`
is not `(0, 0)`.  Consequently it cannot contain an injective infinite orbit.

This is the algebraic return-orbit kernel only.  It does not construct an
analytic continuation or choose a sheet of the associated projective cover.
-/

namespace FormalSeparatedRelationFiniteOrbit

open Polynomial Set

/-- The polynomial whose roots are the finite values in a separated fiber. -/
noncomputable def separatedRelationPolynomial
    (p q : ℂ[X]) (visible scalar : ℂ) : ℂ[X] :=
  C visible * p - C scalar * q

/-- Nonproportionality prevents a nontrivial separated fiber polynomial from
vanishing identically.  The zero-scalar case is included. -/
theorem separatedRelationPolynomial_ne_zero
    (p q : ℂ[X]) (visible scalar : ℂ)
    (q_nonzero : q ≠ 0)
    (nonproportional : ∀ coefficient : ℂ, p ≠ C coefficient * q)
    (pair_nonzero : visible ≠ 0 ∨ scalar ≠ 0) :
    separatedRelationPolynomial p q visible scalar ≠ 0 := by
  by_cases hvisible : visible = 0
  · rcases pair_nonzero with hvisible_nonzero | hscalar
    · exact (hvisible_nonzero hvisible).elim
    simp only [separatedRelationPolynomial, hvisible, C_0, zero_mul,
      zero_sub, neg_ne_zero]
    exact mul_ne_zero (C_ne_zero.mpr hscalar) q_nonzero
  · intro hzero
    have heq : C visible * p = C scalar * q := sub_eq_zero.mp hzero
    apply nonproportional (visible⁻¹ * scalar)
    apply mul_left_cancel₀ (C_ne_zero.mpr hvisible)
    calc
      C visible * p = C scalar * q := heq
      _ = C visible * (C (visible⁻¹ * scalar) * q) := by
        rw [← mul_assoc, ← C_mul]
        field_simp

/-- An injective infinite return orbit cannot remain in one nonproportional
separated fiber.  Collisions and deck permutations are allowed; the theorem
only excludes an orbit whose returned finite values are all distinct. -/
theorem no_injective_infinite_separated_return_orbit
    (p q : ℂ[X]) (visible scalar : ℂ)
    (q_nonzero : q ≠ 0)
    (nonproportional : ∀ coefficient : ℂ, p ≠ C coefficient * q)
    (pair_nonzero : visible ≠ 0 ∨ scalar ≠ 0)
    (orbit : ℕ → ℂ)
    (orbit_injective : Function.Injective orbit)
    (relation : ∀ order : ℕ,
      visible * p.eval (orbit order) =
        scalar * q.eval (orbit order)) :
    False := by
  let relationPolynomial :=
    separatedRelationPolynomial p q visible scalar
  have hpolynomial : relationPolynomial ≠ 0 :=
    separatedRelationPolynomial_ne_zero p q visible scalar q_nonzero
      nonproportional pair_nonzero
  have horbitInfinite : (Set.range orbit).Infinite :=
    Set.infinite_range_of_injective orbit_injective
  have horbitRoots : Set.range orbit ⊆ { value | relationPolynomial.IsRoot value } := by
    rintro value ⟨order, rfl⟩
    change relationPolynomial.IsRoot (orbit order)
    rw [Polynomial.IsRoot.def]
    simpa [relationPolynomial, separatedRelationPolynomial] using
      sub_eq_zero.mpr (relation order)
  exact horbitInfinite
    ((Polynomial.finite_setOf_isRoot hpolynomial).subset horbitRoots)

/-- Aggregated finite-return-orbit surface. -/
theorem separated_relation_finite_orbit_terminal_certificate :
    ∀ (p q : ℂ[X]) (visible scalar : ℂ),
      q ≠ 0 →
      (∀ coefficient : ℂ, p ≠ C coefficient * q) →
      (visible ≠ 0 ∨ scalar ≠ 0) →
      ∀ (orbit : ℕ → ℂ),
        Function.Injective orbit →
        (∀ order : ℕ,
          visible * p.eval (orbit order) =
            scalar * q.eval (orbit order)) →
        False := by
  intro p q visible scalar hq hnonproportional hpair orbit hinjective
    hrelation
  exact no_injective_infinite_separated_return_orbit
    p q visible scalar hq hnonproportional hpair orbit hinjective hrelation

end FormalSeparatedRelationFiniteOrbit
