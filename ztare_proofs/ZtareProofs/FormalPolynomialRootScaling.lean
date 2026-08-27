import Mathlib.Algebra.Polynomial.Degree.Operations
import Mathlib.Algebra.Polynomial.Monic
import Mathlib.Tactic

/-!
# Finite-power normalization of a polynomial root

If the top coefficient of a degree-bounded polynomial has the form `z^s*u`,
then scaling a root by `z^s` produces a root of an explicit monic polynomial.
All transformed coefficients use nonnegative powers of `z`; this is the
algebraic core of local analytic-root normalization.
-/

namespace FormalPolynomialRootScaling

open Finset Polynomial

/-- The monic polynomial annihilating the scaled root. -/
noncomputable def scaledMonicPolynomial
    (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit : ℂ) : ℂ[X] :=
  X ^ degree +
    ∑ i ∈ range degree,
      C (z ^ (scaleOrder * (degree - i - 1)) * p.coeff i / unit) * X ^ i

theorem scaledMonicPolynomial_monic
    (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit : ℂ) :
    (scaledMonicPolynomial p degree scaleOrder z unit).Monic := by
  rw [scaledMonicPolynomial]
  apply monic_X_pow_add
  simp_rw [← Fin.sum_univ_eq_sum_range, degree_sum_fin_lt]

theorem scaledMonicPolynomial_natDegree
    (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit : ℂ) :
    (scaledMonicPolynomial p degree scaleOrder z unit).natDegree = degree := by
  rw [scaledMonicPolynomial]
  calc
    (X ^ degree +
        ∑ i ∈ range degree,
          C (z ^ (scaleOrder * (degree - i - 1)) * p.coeff i / unit) *
            X ^ i).natDegree =
        (X ^ degree : ℂ[X]).natDegree := by
          apply natDegree_add_eq_left_of_degree_lt
          rw [degree_X_pow]
          simp_rw [← Fin.sum_univ_eq_sum_range, degree_sum_fin_lt]
    _ = degree := natDegree_X_pow degree

theorem coeff_scaledMonicPolynomial_of_lt
    (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit : ℂ)
    {i : ℕ} (hi : i < degree) :
    (scaledMonicPolynomial p degree scaleOrder z unit).coeff i =
      z ^ (scaleOrder * (degree - i - 1)) * p.coeff i / unit := by
  simp [scaledMonicPolynomial, coeff_X_pow, hi.ne, hi]

private theorem scale_exponent_lower
    {degree scaleOrder i : ℕ} (hi : i < degree) :
    scaleOrder * (degree - i - 1) + scaleOrder * i =
      scaleOrder * (degree - 1) := by
  have hsplit : degree - i - 1 + i = degree - 1 := by omega
  have h := congrArg (fun n : ℕ ↦ scaleOrder * n) hsplit
  simpa [Nat.mul_add] using h

private theorem scale_exponent_top
    {degree scaleOrder : ℕ} (hdegree : 0 < degree) :
    scaleOrder * degree = scaleOrder * (degree - 1) + scaleOrder := by
  have hsplit : degree = degree - 1 + 1 := by omega
  have h := congrArg (fun n : ℕ ↦ scaleOrder * n) hsplit
  simpa [Nat.mul_add] using h

/-- The scaled root satisfies the explicit monic relation. -/
theorem scaledMonicPolynomial_isRoot
    (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit root : ℂ)
    (hdegreePositive : 0 < degree)
    (hdegree : p.natDegree ≤ degree)
    (hunit : unit ≠ 0)
    (hleading : p.coeff degree = z ^ scaleOrder * unit)
    (hroot : p.IsRoot root) :
    (scaledMonicPolynomial p degree scaleOrder z unit).IsRoot
      (z ^ scaleOrder * root) := by
  have hpExpansion := p.as_sum_range' (degree + 1) (by omega)
  have hpRoot :
      (∑ i ∈ range degree, p.coeff i * root ^ i) +
          p.coeff degree * root ^ degree = 0 := by
    have hevalExpansion := congrArg (Polynomial.eval root) hpExpansion
    have hevalZero :
        Polynomial.eval root
            (∑ i ∈ range (degree + 1), monomial i (p.coeff i)) = 0 := by
      rw [← hevalExpansion]
      exact hroot
    simpa [sum_range_succ, Polynomial.eval_finset_sum,
      Polynomial.eval_monomial] using hevalZero
  rw [Polynomial.IsRoot.def]
  simp only [scaledMonicPolynomial, Polynomial.eval_add,
    Polynomial.eval_pow, Polynomial.eval_X, Polynomial.eval_finset_sum,
    Polynomial.eval_mul, Polynomial.eval_C]
  have hlower :
      unit *
          (∑ i ∈ range degree,
            (z ^ (scaleOrder * (degree - i - 1)) * p.coeff i / unit) *
              (z ^ scaleOrder * root) ^ i) =
        z ^ (scaleOrder * (degree - 1)) *
          (∑ i ∈ range degree, p.coeff i * root ^ i) := by
    rw [Finset.mul_sum, Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro i hi
    have hiDegree : i < degree := mem_range.mp hi
    have hexponent := scale_exponent_lower
      (scaleOrder := scaleOrder) hiDegree
    rw [mul_pow, ← pow_mul]
    calc
      unit *
          (z ^ (scaleOrder * (degree - i - 1)) * p.coeff i / unit *
            (z ^ (scaleOrder * i) * root ^ i)) =
          (z ^ (scaleOrder * (degree - i - 1)) *
            z ^ (scaleOrder * i)) * (p.coeff i * root ^ i) := by
              field_simp [hunit]
      _ = z ^
            (scaleOrder * (degree - i - 1) + scaleOrder * i) *
              (p.coeff i * root ^ i) := by rw [pow_add]
      _ = z ^ (scaleOrder * (degree - 1)) *
              (p.coeff i * root ^ i) := by rw [hexponent]
  have htop :
      unit * (z ^ scaleOrder * root) ^ degree =
        z ^ (scaleOrder * (degree - 1)) *
          ((z ^ scaleOrder * unit) * root ^ degree) := by
    rw [mul_pow]
    have hexponent := scale_exponent_top
      (scaleOrder := scaleOrder) hdegreePositive
    rw [← pow_mul, hexponent, pow_add]
    ring
  apply (mul_eq_zero.mp ?_).resolve_left hunit
  rw [mul_add, htop, hlower, ← mul_add, ← hleading]
  rw [add_comm, hpRoot, mul_zero]

/-- Aggregated root-scaling surface. -/
theorem polynomial_root_scaling_terminal_certificate :
    (∀ (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit : ℂ),
      (scaledMonicPolynomial p degree scaleOrder z unit).Monic ∧
      (scaledMonicPolynomial p degree scaleOrder z unit).natDegree = degree) ∧
    (∀ (p : ℂ[X]) (degree scaleOrder : ℕ) (z unit root : ℂ),
      0 < degree → p.natDegree ≤ degree → unit ≠ 0 →
      p.coeff degree = z ^ scaleOrder * unit → p.IsRoot root →
      (scaledMonicPolynomial p degree scaleOrder z unit).IsRoot
        (z ^ scaleOrder * root)) := by
  constructor
  · intro p degree scaleOrder z unit
    exact ⟨scaledMonicPolynomial_monic p degree scaleOrder z unit,
      scaledMonicPolynomial_natDegree p degree scaleOrder z unit⟩
  · intro p degree scaleOrder z unit root hpositive hdegree hunit
      hleading hroot
    exact scaledMonicPolynomial_isRoot p degree scaleOrder z unit root
      hpositive hdegree hunit hleading hroot

end FormalPolynomialRootScaling
