import Mathlib.Algebra.Polynomial.Reverse
import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.Tactic
import ZtareProofs.FormalPolynomialInfinityTimeCoordinate

/-!
# Reciprocal-time separation for polynomial trajectories

The infinity-time integrand of a polynomial vector field is the reciprocal
of the induced vector field in the coordinate `z = x⁻¹`.  This file proves
that identity from polynomial reversal, transports an original polynomial
trajectory to the reciprocal ODE, and then separates the continued time by
the zero-derivative theorem on a preconnected domain.
-/

namespace FormalPolynomialTimeSeparation

open Filter Polynomial Set
open scoped Topology

open FormalPolynomialInfinityTimeCoordinate

/-- The vector field induced by `x' = p(x)` in the reciprocal coordinate
`z = x⁻¹`. -/
noncomputable def reciprocalVectorField
    (p : ℂ[X]) (degree : ℕ) : ℂ → ℂ :=
  fun z ↦ -(p.reverse.eval z) / z ^ (degree - 2)

/-- Away from the reciprocal origin and the reversed-polynomial divisor, the
infinity-time differential and reciprocal vector field cancel exactly. -/
theorem reciprocalTimeIntegrand_mul_reciprocalVectorField
    (p : ℂ[X]) (degree : ℕ) {z : ℂ}
    (hz : z ≠ 0) (hreverse : p.reverse.eval z ≠ 0) :
    reciprocalTimeIntegrand p degree z *
        reciprocalVectorField p degree z = 1 := by
  have hzpow : z ^ (degree - 2) ≠ 0 := pow_ne_zero _ hz
  simp only [reciprocalTimeIntegrand, reciprocalVectorField]
  field_simp

/-- Polynomial reversal converts evaluation at a nonzero point into
evaluation at its reciprocal with the exact natural-degree power. -/
theorem reverse_eval_inv_mul_pow
    (p : ℂ[X]) {x : ℂ} (hx : x ≠ 0) :
    p.reverse.eval x⁻¹ * x ^ p.natDegree = p.eval x := by
  letI : Invertible x := invertibleOfNonzero hx
  simpa only [Polynomial.eval₂_id, invOf_eq_inv] using
    (Polynomial.eval₂_reverse_mul_pow (RingHom.id ℂ) x p)

/-- An original polynomial trajectory induces the exact reciprocal ODE. -/
theorem hasDerivAt_reciprocal_of_polynomial_trajectory
    (p : ℂ[X]) (degree : ℕ)
    (hdegree : p.natDegree = degree) (htwo : 2 ≤ degree)
    {trajectory : ℂ → ℂ} {t : ℂ}
    (htrajectory :
      HasDerivAt trajectory (p.eval (trajectory t)) t)
    (hnonzero : trajectory t ≠ 0) :
    HasDerivAt (fun s ↦ (trajectory s)⁻¹)
      (reciprocalVectorField p degree (trajectory t)⁻¹) t := by
  have hreverse := reverse_eval_inv_mul_pow p hnonzero
  have hdegreePower : trajectory t ^ p.natDegree =
      trajectory t ^ degree := by rw [hdegree]
  have hcoeff :
      -p.eval (trajectory t) / trajectory t ^ 2 =
        reciprocalVectorField p degree (trajectory t)⁻¹ := by
    rw [← hreverse]
    simp only [reciprocalVectorField, hdegreePower]
    rw [inv_pow_sub₀ hnonzero htwo]
    field_simp
  convert htrajectory.inv hnonzero using 1
  exact hcoeff.symm

/-- Along a reciprocal trajectory, every local primitive of the infinity-time
integrand advances at unit speed. -/
theorem hasDerivAt_timeCoordinate_comp_reciprocal
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate reciprocalTrajectory : ℂ → ℂ} {t : ℂ}
    (htime : HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (reciprocalTrajectory t))
      (reciprocalTrajectory t))
    (htrajectory : HasDerivAt reciprocalTrajectory
      (reciprocalVectorField p degree (reciprocalTrajectory t)) t)
    (hnonzero : reciprocalTrajectory t ≠ 0)
    (hreverse : p.reverse.eval (reciprocalTrajectory t) ≠ 0) :
    HasDerivAt (timeCoordinate ∘ reciprocalTrajectory) 1 t := by
  have hproduct := reciprocalTimeIntegrand_mul_reciprocalVectorField
    p degree hnonzero hreverse
  convert htime.comp t htrajectory using 1
  exact hproduct.symm

/-- The separated time `T(z(t)) - t` has zero derivative wherever the
trajectory avoids the reciprocal divisor. -/
theorem hasDerivAt_separatedTime_zero
    (p : ℂ[X]) (degree : ℕ)
    {timeCoordinate reciprocalTrajectory : ℂ → ℂ} {t : ℂ}
    (htime : HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (reciprocalTrajectory t))
      (reciprocalTrajectory t))
    (htrajectory : HasDerivAt reciprocalTrajectory
      (reciprocalVectorField p degree (reciprocalTrajectory t)) t)
    (hnonzero : reciprocalTrajectory t ≠ 0)
    (hreverse : p.reverse.eval (reciprocalTrajectory t) ≠ 0) :
    HasDerivAt
      (fun s ↦ timeCoordinate (reciprocalTrajectory s) - s) 0 t := by
  simpa only [Function.comp_apply, sub_self] using
    (hasDerivAt_timeCoordinate_comp_reciprocal p degree htime
      htrajectory hnonzero hreverse).sub (hasDerivAt_id t)

/-- Connected-domain integration of the unit-speed identity. -/
theorem separatedTime_eqOn
    (p : ℂ[X]) (degree : ℕ)
    {domain : Set ℂ} {timeCoordinate reciprocalTrajectory : ℂ → ℂ}
    {t₀ : ℂ}
    (hopen : IsOpen domain)
    (hpreconnected : IsPreconnected domain)
    (ht₀ : t₀ ∈ domain)
    (htime : ∀ t ∈ domain, HasDerivAt timeCoordinate
      (reciprocalTimeIntegrand p degree (reciprocalTrajectory t))
      (reciprocalTrajectory t))
    (htrajectory : ∀ t ∈ domain, HasDerivAt reciprocalTrajectory
      (reciprocalVectorField p degree (reciprocalTrajectory t)) t)
    (hnonzero : ∀ t ∈ domain, reciprocalTrajectory t ≠ 0)
    (hreverse : ∀ t ∈ domain,
      p.reverse.eval (reciprocalTrajectory t) ≠ 0) :
    ∀ t ∈ domain,
      timeCoordinate (reciprocalTrajectory t) - t =
        timeCoordinate (reciprocalTrajectory t₀) - t₀ := by
  let separated : ℂ → ℂ :=
    fun t ↦ timeCoordinate (reciprocalTrajectory t) - t
  have hderivative : ∀ t ∈ domain, HasDerivAt separated 0 t := by
    intro t ht
    exact hasDerivAt_separatedTime_zero p degree
      (htime t ht) (htrajectory t ht) (hnonzero t ht) (hreverse t ht)
  have hdifferentiable : DifferentiableOn ℂ separated domain := by
    intro t ht
    exact (hderivative t ht).differentiableAt.differentiableWithinAt
  have hderivZero : domain.EqOn (deriv separated) 0 := by
    intro t ht
    exact (hderivative t ht).deriv
  intro t ht
  exact hopen.is_const_of_deriv_eq_zero hpreconnected
    hdifferentiable hderivZero ht ht₀

/-- Aggregated reusable certificate for polynomial reciprocal-time
separation. -/
theorem polynomial_time_separation_terminal_certificate :
    (∀ (p : ℂ[X]) (degree : ℕ) (z : ℂ),
      z ≠ 0 → p.reverse.eval z ≠ 0 →
      reciprocalTimeIntegrand p degree z *
        reciprocalVectorField p degree z = 1) ∧
    (∀ (p : ℂ[X]) (degree : ℕ)
      (_hdegree : p.natDegree = degree)
      (_htwo : 2 ≤ degree)
      (trajectory : ℂ → ℂ) (t : ℂ),
      HasDerivAt trajectory (p.eval (trajectory t)) t →
      trajectory t ≠ 0 →
      HasDerivAt (fun s ↦ (trajectory s)⁻¹)
        (reciprocalVectorField p degree (trajectory t)⁻¹) t) ∧
    (∀ (p : ℂ[X]) (degree : ℕ)
      (domain : Set ℂ) (timeCoordinate reciprocalTrajectory : ℂ → ℂ)
      (t₀ : ℂ),
      IsOpen domain → IsPreconnected domain → t₀ ∈ domain →
      (∀ t ∈ domain, HasDerivAt timeCoordinate
        (reciprocalTimeIntegrand p degree (reciprocalTrajectory t))
        (reciprocalTrajectory t)) →
      (∀ t ∈ domain, HasDerivAt reciprocalTrajectory
        (reciprocalVectorField p degree (reciprocalTrajectory t)) t) →
      (∀ t ∈ domain, reciprocalTrajectory t ≠ 0) →
      (∀ t ∈ domain,
        p.reverse.eval (reciprocalTrajectory t) ≠ 0) →
      ∀ t ∈ domain,
        timeCoordinate (reciprocalTrajectory t) - t =
          timeCoordinate (reciprocalTrajectory t₀) - t₀) := by
  refine ⟨?_, ?_, ?_⟩
  · intro p degree z hz hreverse
    exact reciprocalTimeIntegrand_mul_reciprocalVectorField
      p degree hz hreverse
  · intro p degree hdegree htwo trajectory t htrajectory hnonzero
    exact hasDerivAt_reciprocal_of_polynomial_trajectory
      p degree hdegree htwo htrajectory hnonzero
  · intro p degree domain timeCoordinate reciprocalTrajectory t₀
      hopen hpreconnected ht₀ htime htrajectory hnonzero hreverse
    exact separatedTime_eqOn p degree hopen hpreconnected ht₀
      htime htrajectory hnonzero hreverse

end FormalPolynomialTimeSeparation
