import Mathlib.RingTheory.PowerSeries.Substitution
import Mathlib.RingTheory.PowerSeries.NoZeroDivisors
import Mathlib.Tactic

/-!
# Injectivity of substitution by an invertible tangent power series

A zero-constant power series with invertible linear coefficient has a formal
substitution inverse.  Substitution by it is therefore injective.  In
particular, no nonzero polynomial can vanish identically after evaluation on
such a tangent germ.

This is the cancellation kernel needed when a selected nonconstant flow
branch satisfies a polynomial relation carrying a common equilibrium factor.
-/

namespace FormalTangentSubstitutionInjectivity

open Polynomial PowerSeries

variable {K : Type*} [Field K]

/-- Substitution by a zero-constant series with invertible linear coefficient
is injective on all formal power series. -/
theorem subst_injective_of_invertible_linear
    (endpoint : K⟦X⟧)
    (hconstant : endpoint.constantCoeff = 0)
    [Invertible (endpoint.coeff 1)] :
    Function.Injective (fun series : K⟦X⟧ ↦ series.subst endpoint) := by
  intro first second hequal
  have hsubst := congrArg
    (fun series : K⟦X⟧ ↦ series.subst endpoint.substInv) hequal
  have hendpoint : HasSubst endpoint :=
    HasSubst.of_constantCoeff_zero' hconstant
  have hinverse : HasSubst endpoint.substInv := hasSubst_substInv endpoint
  have hleft (series : K⟦X⟧) :
      PowerSeries.subst endpoint.substInv
          (PowerSeries.subst endpoint series) = series := by
    rw [PowerSeries.subst_comp_subst_apply hendpoint hinverse,
      PowerSeries.subst_substInv_right endpoint hconstant,
      PowerSeries.X_subst]
  exact (hleft first).symm.trans (hsubst.trans (hleft second))

/-- Evaluating a nonzero polynomial on an invertible tangent formal germ is
nonzero. -/
theorem polynomial_aeval_ne_zero_of_invertible_linear
    (endpoint : K⟦X⟧)
    (hconstant : endpoint.constantCoeff = 0)
    [Invertible (endpoint.coeff 1)]
    (polynomial : K[X])
    (hpolynomial : polynomial ≠ 0) :
    Polynomial.aeval endpoint polynomial ≠ 0 := by
  intro heval
  have hendpoint : HasSubst endpoint :=
    HasSubst.of_constantCoeff_zero' hconstant
  have hsubst : (polynomial : K⟦X⟧).subst endpoint = 0 := by
    exact (subst_coe hendpoint polynomial).trans heval
  have hzero : PowerSeries.subst endpoint (0 : K⟦X⟧) = 0 := by
    rw [← PowerSeries.coe_substAlgHom hendpoint]
    exact map_zero (PowerSeries.substAlgHom hendpoint)
  have hcoerced : (polynomial : K⟦X⟧) = 0 :=
    (subst_injective_of_invertible_linear endpoint hconstant)
      (hsubst.trans hzero.symm)
  exact hpolynomial ((Polynomial.coe_injective K) (by simpa using hcoerced))

/-- A common polynomial factor may be canceled from a selected tangent-germ
identity. -/
theorem cancel_polynomial_factor_on_tangent_germ
    (endpoint : K⟦X⟧)
    (hconstant : endpoint.constantCoeff = 0)
    [Invertible (endpoint.coeff 1)]
    (factor left right : K[X])
    (hfactor : factor ≠ 0)
    (hidentity :
      Polynomial.aeval endpoint (factor * left) =
        Polynomial.aeval endpoint (factor * right)) :
    Polynomial.aeval endpoint left = Polynomial.aeval endpoint right := by
  simp only [map_mul] at hidentity
  exact mul_left_cancel₀
    (polynomial_aeval_ne_zero_of_invertible_linear endpoint hconstant
      factor hfactor)
    hidentity

/-- Aggregated tangent-substitution cancellation certificate. -/
theorem tangent_substitution_injectivity_terminal_certificate :
    ∀ (endpoint : K⟦X⟧) (hconstant : endpoint.constantCoeff = 0)
      [Invertible (endpoint.coeff 1)],
      Function.Injective (fun series : K⟦X⟧ ↦ series.subst endpoint) ∧
      (∀ polynomial : K[X], polynomial ≠ 0 →
        Polynomial.aeval endpoint polynomial ≠ 0) ∧
      (∀ (factor left right : K[X]),
        factor ≠ 0 →
        Polynomial.aeval endpoint (factor * left) =
          Polynomial.aeval endpoint (factor * right) →
        Polynomial.aeval endpoint left =
          Polynomial.aeval endpoint right) := by
  intro endpoint hconstant _
  exact ⟨subst_injective_of_invertible_linear endpoint hconstant,
    polynomial_aeval_ne_zero_of_invertible_linear endpoint hconstant,
    cancel_polynomial_factor_on_tangent_germ endpoint hconstant⟩

end FormalTangentSubstitutionInjectivity
