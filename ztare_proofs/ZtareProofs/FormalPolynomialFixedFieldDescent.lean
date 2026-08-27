import Mathlib.Algebra.Polynomial.Degree.Support
import Mathlib.Algebra.Polynomial.FieldDivision
import Mathlib.Tactic

/-!
# Polynomial descent to the fixed field of a coefficient automorphism

A polynomial whose coefficients are fixed by a field automorphism is
constructed over the corresponding fixed subfield.  Mapping it back recovers
the original polynomial exactly, preserving both nonzeroness and every root
in an arbitrary commutative extension algebra.
-/

namespace FormalPolynomialFixedFieldDescent

open Polynomial

/-- The subfield fixed pointwise by one field automorphism. -/
def fixedField {K : Type*} [Field K] (sigma : K ≃+* K) : Subfield K where
  carrier := {a | sigma a = a}
  zero_mem' := sigma.map_zero
  one_mem' := sigma.map_one
  add_mem' := by
    intro a b ha hb
    change sigma a = a at ha
    change sigma b = b at hb
    change sigma (a + b) = a + b
    rw [map_add, ha, hb]
  mul_mem' := by
    intro a b ha hb
    change sigma a = a at ha
    change sigma b = b at hb
    change sigma (a * b) = a * b
    rw [map_mul, ha, hb]
  neg_mem' := by
    intro a ha
    change sigma a = a at ha
    change sigma (-a) = -a
    rw [map_neg, ha]
  inv_mem' := by
    intro a ha
    change sigma a = a at ha
    change sigma a⁻¹ = a⁻¹
    rw [map_inv₀, ha]

@[simp]
theorem mem_fixedField_iff
    {K : Type*} [Field K] (sigma : K ≃+* K) (a : K) :
    a ∈ fixedField sigma ↔ sigma a = a :=
  Iff.rfl

/-- Rebuild a coefficientwise-fixed polynomial over the fixed subfield. -/
noncomputable def descendPolynomial
    {K : Type*} [Field K] (sigma : K ≃+* K) (p : K[X])
    (hfixed : ∀ n : ℕ, sigma (p.coeff n) = p.coeff n) :
    (fixedField sigma)[X] :=
  ∑ n ∈ p.support, monomial n
    (⟨p.coeff n, hfixed n⟩ : fixedField sigma)

/-- Mapping the constructed fixed-field polynomial back through the subtype
embedding recovers the original polynomial. -/
theorem descendPolynomial_map_eq
    {K : Type*} [Field K] (sigma : K ≃+* K) (p : K[X])
    (hfixed : ∀ n : ℕ, sigma (p.coeff n) = p.coeff n) :
    (descendPolynomial sigma p hfixed).map (fixedField sigma).subtype = p := by
  rw [descendPolynomial, Polynomial.map_sum]
  simp only [map_monomial]
  change (∑ n ∈ p.support, monomial n (p.coeff n)) = p
  exact p.as_sum_support.symm

/-- Descent preserves nonzeroness. -/
theorem descendPolynomial_ne_zero
    {K : Type*} [Field K] (sigma : K ≃+* K) {p : K[X]}
    (hfixed : ∀ n : ℕ, sigma (p.coeff n) = p.coeff n)
    (hp : p ≠ 0) :
    descendPolynomial sigma p hfixed ≠ 0 := by
  intro hzero
  apply hp
  rw [← descendPolynomial_map_eq sigma p hfixed, hzero, Polynomial.map_zero]

/-- Every root of the original polynomial remains a root of the descended
fixed-field relation through the composed coefficient embedding. -/
theorem descendPolynomial_eval₂_eq_zero
    {K E : Type*} [Field K] [CommRing E] [Algebra K E]
    (sigma : K ≃+* K) (p : K[X])
    (hfixed : ∀ n : ℕ, sigma (p.coeff n) = p.coeff n)
    (x : E) (hroot : p.eval₂ (algebraMap K E) x = 0) :
    (descendPolynomial sigma p hfixed).eval₂
        ((algebraMap K E).comp (fixedField sigma).subtype) x = 0 := by
  rw [← descendPolynomial_map_eq sigma p hfixed] at hroot
  simpa only [Polynomial.eval₂_map] using hroot

/-- Aggregated coefficient descent: construct a nonzero polynomial over the
fixed field that maps to the original relation and retains its selected
root. -/
theorem polynomial_fixed_field_descent_terminal_certificate :
    ∀ {K E : Type*} [Field K] [CommRing E] [Algebra K E]
      (sigma : K ≃+* K) (p : K[X]) (x : E),
      (∀ n : ℕ, sigma (p.coeff n) = p.coeff n) →
      p ≠ 0 →
      p.eval₂ (algebraMap K E) x = 0 →
      ∃ q : (fixedField sigma)[X],
        q.map (fixedField sigma).subtype = p ∧
          q ≠ 0 ∧
          q.eval₂ ((algebraMap K E).comp (fixedField sigma).subtype) x = 0 := by
  intro K E _ _ _ sigma p x hfixed hp hroot
  exact ⟨descendPolynomial sigma p hfixed,
    descendPolynomial_map_eq sigma p hfixed,
    descendPolynomial_ne_zero sigma hfixed hp,
    descendPolynomial_eval₂_eq_zero sigma p hfixed x hroot⟩

end FormalPolynomialFixedFieldDescent
