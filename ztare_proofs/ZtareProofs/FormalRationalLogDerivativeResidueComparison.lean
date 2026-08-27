import Mathlib.Algebra.Polynomial.Derivative
import Mathlib.NumberTheory.Real.Irrational
import Mathlib.Tactic

/-!
# Local residue comparison for rational logarithmic derivatives

After exact zero/pole powers have been removed from a rational function at
`a`, its remaining numerator and denominator are units there.  Evaluating
the normalized cross-multiplied logarithmic-derivative equation then forces
the residue to equal the integral zero-minus-pole order.

This is a local algebraic kernel.  It does not construct the local normal
form or claim that an analytic coefficient belongs to a rational function
field.
-/

namespace FormalRationalLogDerivativeResidueComparison

open Polynomial

variable {K : Type*} [Field K]

/-- Multiplying by the local parameter removes the apparent negative power
in the logarithmic derivative of an exact zero/pole factor. -/
theorem localParameter_mul_derivative_power_unit
    (a : K) (order : ℕ) (unit : K[X]) :
    (X - C a) * (((X - C a) ^ order * unit).derivative) =
      (X - C a) ^ order *
        (C (order : K) * unit + (X - C a) * unit.derivative) := by
  cases order with
  | zero => simp
  | succ order =>
      rw [derivative_mul, derivative_pow, derivative_X_sub_C]
      simp only [Nat.cast_add, Nat.cast_one, pow_succ,
        Nat.add_one_sub_one, mul_one]
      ring

/-- Cross multiplication for a rational eigenfunction, followed by exact
zero/pole normalization, produces the row consumed by the residue theorem.
-/
theorem normalized_cross_of_local_factorizations
    (a weight : K)
    (zeroOrder poleOrder : ℕ)
    (numeratorUnit denominatorUnit connectionNumerator
      reducedDenominator : K[X])
    (hraw :
      ((X - C a) * reducedDenominator) *
          ((((X - C a) ^ zeroOrder * numeratorUnit).derivative) *
              ((X - C a) ^ poleOrder * denominatorUnit) -
            ((X - C a) ^ zeroOrder * numeratorUnit) *
              (((X - C a) ^ poleOrder * denominatorUnit).derivative)) =
        C weight * connectionNumerator *
          ((X - C a) ^ zeroOrder * numeratorUnit) *
          ((X - C a) ^ poleOrder * denominatorUnit)) :
    reducedDenominator *
          (C ((zeroOrder : K) - (poleOrder : K)) *
                numeratorUnit * denominatorUnit +
            (X - C a) *
              (numeratorUnit.derivative * denominatorUnit -
                numeratorUnit * denominatorUnit.derivative)) =
        C weight * connectionNumerator *
          numeratorUnit * denominatorUnit := by
  let localParameter : K[X] := X - C a
  have hnumeratorDerivative :
      localParameter *
          ((localParameter ^ zeroOrder * numeratorUnit).derivative) =
        localParameter ^ zeroOrder *
          (C (zeroOrder : K) * numeratorUnit +
            localParameter * numeratorUnit.derivative) := by
    exact localParameter_mul_derivative_power_unit
      a zeroOrder numeratorUnit
  have hdenominatorDerivative :
      localParameter *
          ((localParameter ^ poleOrder * denominatorUnit).derivative) =
        localParameter ^ poleOrder *
          (C (poleOrder : K) * denominatorUnit +
            localParameter * denominatorUnit.derivative) := by
    exact localParameter_mul_derivative_power_unit
      a poleOrder denominatorUnit
  have hfactored :
      localParameter ^ (zeroOrder + poleOrder) *
          (reducedDenominator *
            (C ((zeroOrder : K) - (poleOrder : K)) *
                  numeratorUnit * denominatorUnit +
              localParameter *
                (numeratorUnit.derivative * denominatorUnit -
                  numeratorUnit * denominatorUnit.derivative))) =
        localParameter ^ (zeroOrder + poleOrder) *
          (C weight * connectionNumerator *
            numeratorUnit * denominatorUnit) := by
    rw [pow_add]
    calc
      localParameter ^ zeroOrder * localParameter ^ poleOrder *
            (reducedDenominator *
              (C ((zeroOrder : K) - (poleOrder : K)) *
                    numeratorUnit * denominatorUnit +
                localParameter *
                  (numeratorUnit.derivative * denominatorUnit -
                    numeratorUnit * denominatorUnit.derivative))) =
          reducedDenominator *
            ((localParameter *
                (localParameter ^ zeroOrder * numeratorUnit).derivative) *
                (localParameter ^ poleOrder * denominatorUnit) -
              (localParameter ^ zeroOrder * numeratorUnit) *
                (localParameter *
                  (localParameter ^ poleOrder *
                    denominatorUnit).derivative)) := by
          rw [hnumeratorDerivative, hdenominatorDerivative]
          rw [map_sub]
          ring
      _ = (localParameter * reducedDenominator) *
            (((localParameter ^ zeroOrder * numeratorUnit).derivative) *
                (localParameter ^ poleOrder * denominatorUnit) -
              (localParameter ^ zeroOrder * numeratorUnit) *
                ((localParameter ^ poleOrder * denominatorUnit).derivative)) := by
          ring
      _ = C weight * connectionNumerator *
            (localParameter ^ zeroOrder * numeratorUnit) *
            (localParameter ^ poleOrder * denominatorUnit) := by
          simpa [localParameter] using hraw
      _ = localParameter ^ zeroOrder * localParameter ^ poleOrder *
            (C weight * connectionNumerator *
              numeratorUnit * denominatorUnit) := by ring
  have hparameter : localParameter ^ (zeroOrder + poleOrder) ≠ 0 :=
    pow_ne_zero _ (by
      simpa [localParameter] using (X_sub_C_ne_zero a))
  exact mul_left_cancel₀ hparameter hfactored

/-- Evaluation of the normalized logarithmic-derivative row compares the
integral local order with the connection residue. -/
theorem local_order_eq_weight_mul_residue
    (a weight residue : K)
    (zeroOrder poleOrder : ℕ)
    (numeratorUnit denominatorUnit connectionNumerator
      reducedDenominator : K[X])
    (hnumeratorUnit : numeratorUnit.eval a ≠ 0)
    (hdenominatorUnit : denominatorUnit.eval a ≠ 0)
    (hreducedDenominator : reducedDenominator.eval a ≠ 0)
    (hresidue :
      connectionNumerator.eval a =
        residue * reducedDenominator.eval a)
    (hnormalized :
      reducedDenominator *
          (C ((zeroOrder : K) - (poleOrder : K)) *
                numeratorUnit * denominatorUnit +
            (X - C a) *
              (numeratorUnit.derivative * denominatorUnit -
                numeratorUnit * denominatorUnit.derivative)) =
        C weight * connectionNumerator *
          numeratorUnit * denominatorUnit) :
    (zeroOrder : K) - (poleOrder : K) = weight * residue := by
  have hevaluated := congrArg (fun p : K[X] ↦ p.eval a) hnormalized
  simp only [eval_mul, eval_add, eval_sub, eval_C, eval_X] at hevaluated
  rw [hresidue] at hevaluated
  have hunit :
      reducedDenominator.eval a *
          (numeratorUnit.eval a * denominatorUnit.eval a) ≠ 0 :=
    mul_ne_zero hreducedDenominator
      (mul_ne_zero hnumeratorUnit hdenominatorUnit)
  apply mul_left_cancel₀ hunit
  calc
    reducedDenominator.eval a *
          (numeratorUnit.eval a * denominatorUnit.eval a) *
        ((zeroOrder : K) - (poleOrder : K)) =
        reducedDenominator.eval a *
          (((zeroOrder : K) - (poleOrder : K)) *
            numeratorUnit.eval a * denominatorUnit.eval a) := by ring
    _ = weight *
          (residue * reducedDenominator.eval a) *
          numeratorUnit.eval a * denominatorUnit.eval a := by
      simpa using hevaluated
    _ = reducedDenominator.eval a *
          (numeratorUnit.eval a * denominatorUnit.eval a) *
        (weight * residue) := by ring

/-- A nonzero integral weight cannot turn an irrational real residue into an
integral zero-minus-pole order. -/
theorem irrational_residue_excludes_integral_weight
    (residue : ℝ)
    (hirrational : Irrational residue)
    (weight : ℤ)
    (hweight : weight ≠ 0)
    (zeroOrder poleOrder : ℕ) :
    (zeroOrder : ℝ) - (poleOrder : ℝ) ≠
      (weight : ℝ) * residue := by
  intro heigen
  have hweightReal : (weight : ℝ) ≠ 0 := by
    exact_mod_cast hweight
  have horderCast :
      ((((zeroOrder : ℤ) - (poleOrder : ℤ) : ℤ) : ℝ)) =
        (zeroOrder : ℝ) - (poleOrder : ℝ) := by
    norm_num
  have hresidueRational :
      residue =
        (((zeroOrder : ℤ) - (poleOrder : ℤ) : ℤ) : ℝ) /
          (weight : ℝ) := by
    apply (eq_div_iff hweightReal).2
    rw [horderCast]
    simpa [mul_comm] using heigen.symm
  exact hirrational.ne_rational
    ((zeroOrder : ℤ) - (poleOrder : ℤ)) weight hresidueRational

/-- Complex-cast form consumed by rational connections with a real critical
residue. -/
theorem complex_irrational_residue_excludes_integral_weight
    (residue : ℝ)
    (hirrational : Irrational residue)
    (weight : ℤ)
    (hweight : weight ≠ 0)
    (zeroOrder poleOrder : ℕ) :
    (zeroOrder : ℂ) - (poleOrder : ℂ) ≠
      (weight : ℂ) * (residue : ℂ) := by
  intro heigen
  have hreal := congrArg Complex.re heigen
  exact irrational_residue_excludes_integral_weight residue hirrational
    weight hweight zeroOrder poleOrder (by simpa using hreal)

/-- Aggregated local residue-comparison certificate. -/
theorem rational_log_derivative_residue_comparison_terminal_certificate :
    (∀ (a weight residue : K) (zeroOrder poleOrder : ℕ)
      (numeratorUnit denominatorUnit connectionNumerator
        reducedDenominator : K[X]),
      numeratorUnit.eval a ≠ 0 →
      denominatorUnit.eval a ≠ 0 →
      reducedDenominator.eval a ≠ 0 →
      connectionNumerator.eval a =
          residue * reducedDenominator.eval a →
      reducedDenominator *
            (C ((zeroOrder : K) - (poleOrder : K)) *
                  numeratorUnit * denominatorUnit +
              (X - C a) *
                (numeratorUnit.derivative * denominatorUnit -
                  numeratorUnit * denominatorUnit.derivative)) =
          C weight * connectionNumerator *
            numeratorUnit * denominatorUnit →
      (zeroOrder : K) - (poleOrder : K) = weight * residue) ∧
    (∀ (residue : ℝ), Irrational residue →
      ∀ (weight : ℤ), weight ≠ 0 →
      ∀ (zeroOrder poleOrder : ℕ),
        (zeroOrder : ℂ) - (poleOrder : ℂ) ≠
          (weight : ℂ) * (residue : ℂ)) := by
  constructor
  · exact local_order_eq_weight_mul_residue
  · exact complex_irrational_residue_excludes_integral_weight

end FormalRationalLogDerivativeResidueComparison
