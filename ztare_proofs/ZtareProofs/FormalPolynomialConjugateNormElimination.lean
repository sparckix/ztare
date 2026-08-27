import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Tactic

/-!
# Conjugate-norm elimination for polynomial root relations

A coefficient-field involution removes one quadratic extension from a
polynomial root relation.  For `P` over the extension field, the eliminant
`P * sigma(P)` is nonzero, retains every root of `P` in every commutative
extension algebra, and has coefficients fixed by `sigma`.

Descent from the fixed coefficient field to a chosen base field is a separate
interface.
-/

namespace FormalPolynomialConjugateNormElimination

open Polynomial

/-- Apply the coefficient-field equivalence to a polynomial. -/
noncomputable def conjugatePolynomial
    {K : Type*} [Field K] (sigma : K ≃+* K) (p : K[X]) : K[X] :=
  p.map sigma.toRingHom

/-- The coefficient-conjugate norm eliminant. -/
noncomputable def conjugateNormPolynomial
    {K : Type*} [Field K] (sigma : K ≃+* K) (p : K[X]) : K[X] :=
  p * conjugatePolynomial sigma p

/-- Coefficient conjugation cannot annihilate a nonzero polynomial. -/
theorem conjugatePolynomial_ne_zero
    {K : Type*} [Field K] (sigma : K ≃+* K) {p : K[X]}
    (hp : p ≠ 0) :
    conjugatePolynomial sigma p ≠ 0 := by
  exact (Polynomial.map_ne_zero_iff sigma.injective).2 hp

/-- The conjugate norm of a nonzero polynomial is nonzero. -/
theorem conjugateNormPolynomial_ne_zero
    {K : Type*} [Field K] (sigma : K ≃+* K) {p : K[X]}
    (hp : p ≠ 0) :
    conjugateNormPolynomial sigma p ≠ 0 := by
  exact mul_ne_zero hp (conjugatePolynomial_ne_zero sigma hp)

/-- Every root of the original relation remains a root of the norm
eliminant, even when the root lies in a larger commutative algebra. -/
theorem conjugateNormPolynomial_eval₂_eq_zero
    {K E : Type*} [Field K] [CommRing E] [Algebra K E]
    (sigma : K ≃+* K) (p : K[X]) (x : E)
    (hroot : p.eval₂ (algebraMap K E) x = 0) :
    (conjugateNormPolynomial sigma p).eval₂ (algebraMap K E) x = 0 := by
  rw [conjugateNormPolynomial, Polynomial.eval₂_mul, hroot, zero_mul]

/-- An involutive coefficient equivalence fixes the conjugate norm
polynomial. -/
theorem conjugateNormPolynomial_map_eq_self
    {K : Type*} [Field K] (sigma : K ≃+* K) (p : K[X])
    (hinvolution : ∀ a : K, sigma (sigma a) = a) :
    (conjugateNormPolynomial sigma p).map sigma.toRingHom =
      conjugateNormPolynomial sigma p := by
  have hcompose :
      sigma.toRingHom.comp sigma.toRingHom = RingHom.id K := by
    ext a
    exact hinvolution a
  rw [conjugateNormPolynomial, Polynomial.map_mul,
    conjugatePolynomial, Polynomial.map_map, hcompose,
    Polynomial.map_id]
  exact mul_comm _ _

/-- Every coefficient of the norm eliminant lies in the fixed field of the
involution. -/
theorem conjugateNormPolynomial_coefficient_fixed
    {K : Type*} [Field K] (sigma : K ≃+* K) (p : K[X])
    (hinvolution : ∀ a : K, sigma (sigma a) = a) (n : ℕ) :
    sigma ((conjugateNormPolynomial sigma p).coeff n) =
      (conjugateNormPolynomial sigma p).coeff n := by
  have hinvariant := congrArg (fun q : K[X] ↦ q.coeff n)
    (conjugateNormPolynomial_map_eq_self sigma p hinvolution)
  simpa using hinvariant

/-- Aggregated elimination surface: a nonzero relation yields a nonzero
fixed-coefficient relation with the same selected root. -/
theorem polynomial_conjugate_norm_elimination_terminal_certificate :
    ∀ {K E : Type*} [Field K] [CommRing E] [Algebra K E]
      (sigma : K ≃+* K) (p : K[X]) (x : E),
      (∀ a : K, sigma (sigma a) = a) →
      p ≠ 0 →
      p.eval₂ (algebraMap K E) x = 0 →
      conjugateNormPolynomial sigma p ≠ 0 ∧
        (conjugateNormPolynomial sigma p).eval₂
          (algebraMap K E) x = 0 ∧
        ∀ n : ℕ,
          sigma ((conjugateNormPolynomial sigma p).coeff n) =
            (conjugateNormPolynomial sigma p).coeff n := by
  intro K E _ _ _ sigma p x hinvolution hp hroot
  exact ⟨conjugateNormPolynomial_ne_zero sigma hp,
    conjugateNormPolynomial_eval₂_eq_zero sigma p x hroot,
    conjugateNormPolynomial_coefficient_fixed sigma p hinvolution⟩

end FormalPolynomialConjugateNormElimination
