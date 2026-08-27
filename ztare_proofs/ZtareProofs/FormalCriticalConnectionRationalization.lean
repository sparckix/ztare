import Mathlib.FieldTheory.RatFunc.AsPolynomial
import Mathlib.Tactic
import ZtareProofs.FormalCriticalMonodromyResidueBinding

/-!
# Rational-function identity for the critical logarithmic connection

The source rows below are the original algebraic critical connection.  This
file substitutes the exact conic parameterization and checks the resulting
logarithmic differential as an equality in `RatFunc ℝ`.  Equality in the
rational-function field records every cancellation without choosing a
pointwise domain or accepting denominator side conditions as premises.
-/

namespace FormalCriticalConnectionRationalization

open Polynomial RatFunc

abbrev RF := RatFunc ℝ

noncomputable def parameter : RF := RatFunc.X

noncomputable def connectionDenominator (x : RF) : RF :=
  896 * x ^ 3 * (x - 4) * (x ^ 2 - 4 * x - 8)

noncomputable def rationalVelocity (x : RF) : RF :=
  (21 * x ^ 6 - 124 * x ^ 5 + 456 * x ^ 4 - 2048 * x ^ 3
      - 6768 * x ^ 2 + 22464 * x + 44928) /
    connectionDenominator x

noncomputable def radicalVelocity (x : RF) : RF :=
  ((x - 6) * (x + 2) * (7 * x ^ 3 - 42 * x ^ 2 + 624)) /
    connectionDenominator x

noncomputable def xOfParameter : RF :=
  6 * (parameter ^ 2 - 1) / (parameter ^ 2 + 3)

noncomputable def radicalOfParameter : RF :=
  24 * parameter / (parameter ^ 2 + 3)

/-- The formal derivative of the displayed rational parameterization. -/
noncomputable def xDerivativeOfParameter : RF :=
  48 * parameter / (parameter ^ 2 + 3) ^ 2

noncomputable def velocityOfParameter : RF :=
  rationalVelocity xOfParameter
    + radicalVelocity xOfParameter * radicalOfParameter

noncomputable def connectionLogarithmicDifferential : RF :=
  xDerivativeOfParameter /
    (xOfParameter * (1 + 2 * xOfParameter * velocityOfParameter))

noncomputable def poleRationalFunction : RF :=
  algebraMap ℝ[X] RF
    FormalCriticalMonodromyResidueBinding.polePolynomial

noncomputable def numeratorRationalFunction : RF :=
  algebraMap ℝ[X] RF
    FormalCriticalMonodromyResidueBinding.numeratorPolynomial

noncomputable def explicitRationalDifferential : RF :=
  numeratorRationalFunction /
    ((parameter - 1) * poleRationalFunction)

theorem parameter_sq_add_three_ne_zero :
    parameter ^ 2 + 3 ≠ 0 := by
  have hpoly :
      (Polynomial.X ^ 2 + 3 : ℝ[X]) ≠ 0 := by
    intro hzero
    have hcoeff := congrArg (fun p : ℝ[X] => p.coeff 0) hzero
    norm_num at hcoeff
  simpa only [parameter, map_add, map_pow, RatFunc.algebraMap_X,
    map_ofNat] using
    (RatFunc.algebraMap_ne_zero hpoly :
      algebraMap ℝ[X] RF
        (Polynomial.X ^ 2 + 3) ≠ 0)

theorem parameter_sub_constant_ne_zero (c : ℝ) :
    parameter - RatFunc.C c ≠ 0 := by
  have hpoly :
      (Polynomial.X - Polynomial.C c : ℝ[X]) ≠ 0 := by
    intro hzero
    have hcoeff := congrArg (fun p : ℝ[X] => p.coeff 1) hzero
    simp at hcoeff
  simpa only [parameter, map_sub, RatFunc.algebraMap_X,
    RatFunc.algebraMap_C] using
    (RatFunc.algebraMap_ne_zero hpoly :
      algebraMap ℝ[X] RF
        (Polynomial.X - Polynomial.C c) ≠ 0)

theorem parameter_quadratic_ne_zero (b c : ℝ) :
    parameter ^ 2 + RatFunc.C b * parameter + RatFunc.C c ≠ 0 := by
  have hpoly :
      (Polynomial.X ^ 2 + Polynomial.C b * Polynomial.X
          + Polynomial.C c : ℝ[X]) ≠ 0 := by
    intro hzero
    have hcoeff := congrArg (fun p : ℝ[X] => p.coeff 2) hzero
    simp at hcoeff
  simpa only [parameter, map_add, map_mul, map_pow,
    RatFunc.algebraMap_X, RatFunc.algebraMap_C] using
    (RatFunc.algebraMap_ne_zero hpoly :
      algebraMap ℝ[X] RF
        (Polynomial.X ^ 2 + Polynomial.C b * Polynomial.X
          + Polynomial.C c) ≠ 0)

@[simp] theorem ratFunc_C_natCast (n : ℕ) :
    RatFunc.C (n : ℝ) = (n : RF) := by
  exact map_natCast (RatFunc.C (K := ℝ)) n

@[simp] theorem ratFunc_C_neg_natCast (n : ℕ) :
    RatFunc.C (-(n : ℝ)) = -(n : RF) := by
  rw [map_neg, ratFunc_C_natCast]

theorem ratFunc_C_one : RatFunc.C (1 : ℝ) = (1 : RF) :=
  map_one (RatFunc.C (K := ℝ))

theorem ratFunc_C_three : RatFunc.C (3 : ℝ) = (3 : RF) :=
  ratFunc_C_natCast 3

theorem ratFunc_C_six : RatFunc.C (6 : ℝ) = (6 : RF) :=
  ratFunc_C_natCast 6

theorem ratFunc_C_neg_one : RatFunc.C (-1 : ℝ) = (-1 : RF) :=
  by rw [map_neg, ratFunc_C_one]

theorem ratFunc_C_neg_three : RatFunc.C (-3 : ℝ) = (-3 : RF) :=
  ratFunc_C_neg_natCast 3

theorem ratFunc_C_neg_six : RatFunc.C (-6 : ℝ) = (-6 : RF) :=
  ratFunc_C_neg_natCast 6

theorem ratFunc_C_67 : RatFunc.C (67 : ℝ) = (67 : RF) :=
  ratFunc_C_natCast 67

theorem ratFunc_C_199 : RatFunc.C (199 : ℝ) = (199 : RF) :=
  ratFunc_C_natCast 199

theorem ratFunc_C_219 : RatFunc.C (219 : ℝ) = (219 : RF) :=
  ratFunc_C_natCast 219

theorem ratFunc_C_896 : RatFunc.C (896 : ℝ) = (896 : RF) :=
  ratFunc_C_natCast 896

theorem ratFunc_C_1393 : RatFunc.C (1393 : ℝ) = (1393 : RF) :=
  ratFunc_C_natCast 1393

theorem ratFunc_C_2889 : RatFunc.C (2889 : ℝ) = (2889 : RF) :=
  ratFunc_C_natCast 2889

theorem ratFunc_C_5973 : RatFunc.C (5973 : ℝ) = (5973 : RF) :=
  ratFunc_C_natCast 5973

theorem ratFunc_C_10125 : RatFunc.C (10125 : ℝ) = (10125 : RF) :=
  ratFunc_C_natCast 10125

theorem ratFunc_C_10593 : RatFunc.C (10593 : ℝ) = (10593 : RF) :=
  ratFunc_C_natCast 10593

theorem parameter_sub_three_ne_zero : parameter - 3 ≠ 0 := by
  have h := parameter_sub_constant_ne_zero 3
  rw [ratFunc_C_three] at h
  exact h

theorem parameter_sub_one_ne_zero : parameter - 1 ≠ 0 := by
  have h := parameter_sub_constant_ne_zero 1
  rw [ratFunc_C_one] at h
  exact h

theorem parameter_add_one_ne_zero : parameter + 1 ≠ 0 := by
  have heq : parameter + 1 = parameter - RatFunc.C (-1 : ℝ) := by
    rw [ratFunc_C_neg_one]
    ring
  rw [heq]
  exact parameter_sub_constant_ne_zero (-1)

theorem parameter_add_three_ne_zero : parameter + 3 ≠ 0 := by
  have heq : parameter + 3 = parameter - RatFunc.C (-3 : ℝ) := by
    rw [ratFunc_C_neg_three]
    ring
  rw [heq]
  exact parameter_sub_constant_ne_zero (-3)

theorem parameter_quadratic_minus_ne_zero :
    parameter ^ 2 - 6 * parameter - 3 ≠ 0 := by
  have heq : parameter ^ 2 - 6 * parameter - 3 =
      parameter ^ 2 + RatFunc.C (-6 : ℝ) * parameter
        + RatFunc.C (-3 : ℝ) := by
    rw [ratFunc_C_neg_six, ratFunc_C_neg_three]
    ring
  rw [heq]
  exact parameter_quadratic_ne_zero (-6) (-3)

theorem parameter_quadratic_plus_ne_zero :
    parameter ^ 2 + 6 * parameter - 3 ≠ 0 := by
  have heq : parameter ^ 2 + 6 * parameter - 3 =
      parameter ^ 2 + RatFunc.C (6 : ℝ) * parameter
        + RatFunc.C (-3 : ℝ) := by
    rw [ratFunc_C_six, ratFunc_C_neg_three]
    ring
  rw [heq]
  exact parameter_quadratic_ne_zero 6 (-3)

noncomputable def simplifiedConnectionDenominator : RF :=
  1548288 * (parameter - 3) * (parameter - 1) ^ 3
    * (parameter + 1) ^ 3 * (parameter + 3)
    * (parameter ^ 2 - 6 * parameter - 3)
    * (parameter ^ 2 + 6 * parameter - 3)
    / (parameter ^ 2 + 3) ^ 6

theorem simplifiedConnectionDenominator_ne_zero :
    simplifiedConnectionDenominator ≠ 0 := by
  apply div_ne_zero
  · exact mul_ne_zero
      (mul_ne_zero
        (mul_ne_zero
          (mul_ne_zero
            (mul_ne_zero
              (mul_ne_zero (by norm_num) parameter_sub_three_ne_zero)
                (pow_ne_zero 3 parameter_sub_one_ne_zero))
              (pow_ne_zero 3 parameter_add_one_ne_zero))
            parameter_add_three_ne_zero)
          parameter_quadratic_minus_ne_zero)
      parameter_quadratic_plus_ne_zero
  · exact pow_ne_zero 6 parameter_sq_add_three_ne_zero

theorem connection_denominator_parameter_identity :
    connectionDenominator xOfParameter =
      simplifiedConnectionDenominator := by
  rw [connectionDenominator, xOfParameter,
    simplifiedConnectionDenominator]
  field_simp [parameter_sq_add_three_ne_zero]
  ring

theorem connectionDenominator_xOfParameter_ne_zero :
    connectionDenominator xOfParameter ≠ 0 := by
  rw [connection_denominator_parameter_identity]
  exact simplifiedConnectionDenominator_ne_zero

noncomputable def simplifiedVelocityNumerator : RF :=
  (parameter - 1) *
      (29 * parameter ^ 5 - 145 * parameter ^ 4
        - 334 * parameter ^ 3 - 786 * parameter ^ 2
        - 255 * parameter - 45)

noncomputable def simplifiedVelocityDenominator : RF :=
  448 * (parameter - 3) * (parameter + 1) ^ 3
    * (parameter ^ 2 - 6 * parameter - 3)

noncomputable def simplifiedVelocity : RF :=
  simplifiedVelocityNumerator / simplifiedVelocityDenominator

theorem simplifiedVelocityDenominator_ne_zero :
    simplifiedVelocityDenominator ≠ 0 := by
  rw [simplifiedVelocityDenominator]
  apply mul_ne_zero
  · apply mul_ne_zero
    · apply mul_ne_zero
      · norm_num
      · exact parameter_sub_three_ne_zero
    · exact pow_ne_zero 3 parameter_add_one_ne_zero
  · exact parameter_quadratic_minus_ne_zero

theorem velocity_parameter_identity :
    velocityOfParameter = simplifiedVelocity := by
  rw [velocityOfParameter, rationalVelocity, radicalVelocity,
    radicalOfParameter, simplifiedVelocity]
  rw [eq_div_iff simplifiedVelocityDenominator_ne_zero]
  rw [connection_denominator_parameter_identity]
  field_simp [simplifiedConnectionDenominator_ne_zero,
    parameter_sq_add_three_ne_zero]
  rw [simplifiedConnectionDenominator, xOfParameter]
  field_simp [parameter_sq_add_three_ne_zero]
  rw [simplifiedVelocityNumerator, simplifiedVelocityDenominator]
  ring

theorem poleRationalFunction_ne_zero : poleRationalFunction ≠ 0 := by
  have hpoly :
      FormalCriticalMonodromyResidueBinding.polePolynomial ≠ 0 := by
    intro hzero
    have hcoeff := congrArg (fun p : ℝ[X] => p.coeff 7) hzero
    norm_num [FormalCriticalMonodromyResidueBinding.polePolynomial] at hcoeff
  exact RatFunc.algebraMap_ne_zero hpoly

theorem poleRationalFunction_expansion :
    poleRationalFunction =
      199 * parameter ^ 7 - 1393 * parameter ^ 6
        + 67 * parameter ^ 5 + 219 * parameter ^ 4
        + 5973 * parameter ^ 3 + 10125 * parameter ^ 2
        + 10593 * parameter + 2889 := by
  rw [poleRationalFunction,
    FormalCriticalMonodromyResidueBinding.polePolynomial]
  simp only [map_add, map_mul, map_pow, map_neg,
    RatFunc.algebraMap_X, RatFunc.algebraMap_C]
  rw [parameter, ratFunc_C_199, ratFunc_C_1393, ratFunc_C_67,
    ratFunc_C_219, ratFunc_C_5973, ratFunc_C_10125,
    ratFunc_C_10593, ratFunc_C_2889]
  ring

theorem numeratorRationalFunction_expansion :
    numeratorRationalFunction =
      896 * parameter * (parameter - 3) * (parameter + 1)
        * (parameter ^ 2 - 6 * parameter - 3) := by
  rw [numeratorRationalFunction,
    FormalCriticalMonodromyResidueBinding.numeratorPolynomial]
  simp only [map_mul, map_pow, map_sub, map_add,
    RatFunc.algebraMap_X, RatFunc.algebraMap_C]
  rw [parameter, ratFunc_C_896, ratFunc_C_three,
    ratFunc_C_one, ratFunc_C_six]

noncomputable def simplifiedRadialNumerator : RF :=
  3 * (parameter - 1) * poleRationalFunction

noncomputable def simplifiedRadialFractionDenominator : RF :=
  56 * (parameter - 3) * (parameter + 1)
    * (parameter ^ 2 + 3) ^ 2
    * (parameter ^ 2 - 6 * parameter - 3)

noncomputable def simplifiedRadialDenominator : RF :=
  simplifiedRadialNumerator / simplifiedRadialFractionDenominator

theorem simplifiedRadialDenominatorDenominator_ne_zero :
    simplifiedRadialFractionDenominator ≠ 0 := by
  rw [simplifiedRadialFractionDenominator]
  exact mul_ne_zero
    (mul_ne_zero
      (mul_ne_zero
        (mul_ne_zero (by norm_num) parameter_sub_three_ne_zero)
          parameter_add_one_ne_zero)
        (pow_ne_zero 2 parameter_sq_add_three_ne_zero))
    parameter_quadratic_minus_ne_zero

theorem simplifiedRadialDenominator_ne_zero :
    simplifiedRadialDenominator ≠ 0 := by
  rw [simplifiedRadialDenominator, simplifiedRadialNumerator]
  exact div_ne_zero
    (mul_ne_zero
      (mul_ne_zero (by norm_num) parameter_sub_one_ne_zero)
      poleRationalFunction_ne_zero)
    simplifiedRadialDenominatorDenominator_ne_zero

theorem radial_denominator_parameter_identity :
    xOfParameter *
        (1 + 2 * xOfParameter * velocityOfParameter) =
      simplifiedRadialDenominator := by
  rw [velocity_parameter_identity, simplifiedVelocity]
  calc
    xOfParameter *
          (1 + 2 * xOfParameter *
            (simplifiedVelocityNumerator /
              simplifiedVelocityDenominator)) =
        xOfParameter *
          (simplifiedVelocityDenominator
              + 2 * xOfParameter * simplifiedVelocityNumerator) /
            simplifiedVelocityDenominator := by
      field_simp [simplifiedVelocityDenominator_ne_zero]
    _ = simplifiedRadialDenominator := by
      rw [simplifiedRadialDenominator]
      rw [div_eq_div_iff simplifiedVelocityDenominator_ne_zero
        simplifiedRadialDenominatorDenominator_ne_zero]
      rw [xOfParameter, simplifiedVelocityNumerator,
        simplifiedVelocityDenominator, simplifiedRadialNumerator,
        simplifiedRadialFractionDenominator,
        poleRationalFunction_expansion]
      field_simp [parameter_sq_add_three_ne_zero]
      ring

/-- Exact substitution of the original critical connection into the conic
parameter gives the rational differential consumed by the pole theorem. -/
theorem critical_connection_rational_differential_identity :
    connectionLogarithmicDifferential =
      explicitRationalDifferential := by
  rw [connectionLogarithmicDifferential,
    radial_denominator_parameter_identity,
    explicitRationalDifferential]
  rw [div_eq_div_iff simplifiedRadialDenominator_ne_zero
    (mul_ne_zero parameter_sub_one_ne_zero poleRationalFunction_ne_zero)]
  rw [simplifiedRadialDenominator, ← mul_div_assoc]
  rw [eq_div_iff simplifiedRadialDenominatorDenominator_ne_zero]
  rw [xDerivativeOfParameter, numeratorRationalFunction_expansion,
    simplifiedRadialNumerator, simplifiedRadialFractionDenominator]
  field_simp [parameter_sq_add_three_ne_zero]
  ring

/-- The conic parameterization selects the displayed radical sheet. -/
theorem conic_parameterization_identity :
    radicalOfParameter ^ 2 =
      36 + 12 * xOfParameter - 3 * xOfParameter ^ 2 := by
  rw [radicalOfParameter, xOfParameter]
  field_simp [parameter_sq_add_three_ne_zero]
  ring

/-- Pointwise analytic check that the rational expression called
`xDerivativeOfParameter` is the derivative of the real parameterization. -/
theorem x_parameterization_hasDerivAt (t : ℝ) :
    HasDerivAt
      (fun u : ℝ => 6 * (u ^ 2 - 1) / (u ^ 2 + 3))
      (48 * t / (t ^ 2 + 3) ^ 2) t := by
  have hden : t ^ 2 + 3 ≠ 0 := by nlinarith [sq_nonneg t]
  have hnum : HasDerivAt (fun u : ℝ => 6 * (u ^ 2 - 1)) (12 * t) t := by
    convert (hasDerivAt_const t (6 : ℝ)).mul
      (((hasDerivAt_id t).pow 2).sub_const 1) using 1 <;>
      simp only [id_eq] <;> ring
  have hdenDeriv : HasDerivAt (fun u : ℝ => u ^ 2 + 3) (2 * t) t := by
    convert ((hasDerivAt_id t).pow 2).add_const 3 using 1 <;>
      simp only [id_eq] <;> ring
  convert hnum.div hdenDeriv hden using 1 <;>
    field_simp [hden] <;> ring

/-- The theorem-scoped surface used by governed coverage receipts. -/
theorem critical_connection_rationalization_terminal_certificate :
    radicalOfParameter ^ 2 =
        36 + 12 * xOfParameter - 3 * xOfParameter ^ 2
      ∧ connectionLogarithmicDifferential =
        numeratorRationalFunction /
          ((parameter - 1) * poleRationalFunction) := by
  exact ⟨conic_parameterization_identity,
    critical_connection_rational_differential_identity⟩

end FormalCriticalConnectionRationalization
