import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Complex.HasPrimitives
import Mathlib.Analysis.Normed.Field.Basic
import ZtareProofs.FormalPolynomialDiskNonvanishing

/-!
# Rational uniformization and exact continuation disks

The selected quadratic cover is rationally parameterized by `q`.  Three
overlapping complex disks connect the normalization point `q = 1` to the
ramification point `q = 3`.  Exact shifted-coefficient dominance proves that
the degree-seven ODE denominator has no zero in any disk.
-/

namespace AxiomPackJacobianCriticalPuiseuxUniformization

open Metric Set
open FormalPolynomialDiskNonvanishing

/-- The denominator of the rational uniformizing chart. -/
noncomputable def conicDenominator (q : ℂ) : ℂ := q ^ 2 + 3

/-- Original critical coordinate in the rational parameter. -/
noncomputable def uniformizedX (q : ℂ) : ℂ :=
  -12 * (q - 1) / conicDenominator q

/-- Selected discriminant coordinate in the rational parameter. -/
noncomputable def uniformizedY (q : ℂ) : ℂ :=
  -6 * (q - 3) * (q + 1) / conicDenominator q

theorem uniformized_conic_identity (q : ℂ)
    (hdenominator : conicDenominator q ≠ 0) :
    uniformizedY q ^ 2 =
      36 + 12 * uniformizedX q - 3 * uniformizedX q ^ 2 := by
  have hden : q ^ 2 + 3 ≠ 0 := by
    simpa [conicDenominator] using hdenominator
  simp only [uniformizedX, uniformizedY, conicDenominator]
  field_simp [hden]
  ring

theorem uniformized_ramification_identity (q : ℂ)
    (hdenominator : conicDenominator q ≠ 0) :
    uniformizedX q + 2 =
      2 * (q - 3) ^ 2 / conicDenominator q := by
  have hden : q ^ 2 + 3 ≠ 0 := by
    simpa [conicDenominator] using hdenominator
  simp only [uniformizedX, conicDenominator]
  field_simp [hden]
  ring

@[simp]
theorem uniformizedX_one : uniformizedX 1 = 0 := by
  norm_num [uniformizedX, conicDenominator]

@[simp]
theorem uniformizedY_one : uniformizedY 1 = 6 := by
  norm_num [uniformizedY, conicDenominator]

@[simp]
theorem uniformizedX_three : uniformizedX 3 = -2 := by
  norm_num [uniformizedX, conicDenominator]

@[simp]
theorem uniformizedY_three : uniformizedY 3 = 0 := by
  norm_num [uniformizedY, conicDenominator]

/-- Degree-seven denominator of the regularized uniformized ODE. -/
noncomputable def flowDenominator (q : ℂ) : ℂ :=
  39 * q ^ 7 - 273 * q ^ 6 + 1571 * q ^ 5 - 6981 * q ^ 4 +
    5493 * q ^ 3 - 21843 * q ^ 2 - 8703 * q + 2025

/-- Numerator after removing the simple zero at the normalization point from
the inverse holonomy. -/
noncomputable def regularizedFlowNumerator (q : ℂ) : ℂ :=
  -39 * q ^ 6 + 234 * q ^ 5 - 2233 * q ^ 4 + 11916 * q ^ 3 +
    1047 * q ^ 2 + 1386 * q + 2025

/-- Regular logarithmic derivative of `F(q)/(q-1)`. -/
noncomputable def regularizedLogDerivative (q : ℂ) : ℂ :=
  regularizedFlowNumerator q / flowDenominator q

@[simp]
theorem regularizedLogDerivative_one :
    regularizedLogDerivative 1 = -1 / 2 := by
  norm_num [regularizedLogDerivative, regularizedFlowNumerator,
    flowDenominator]

@[simp]
theorem regularizedLogDerivative_three :
    regularizedLogDerivative 3 = -1 / 2 := by
  norm_num [regularizedLogDerivative, regularizedFlowNumerator,
    flowDenominator]

noncomputable def leftShiftedCoefficient : ℕ → ℂ
  | 0 => -743170265 / 16384
  | 1 => -314905583 / 4096
  | 2 => -44549837 / 1024
  | 3 => -3122347 / 256
  | 4 => -57259 / 64
  | 5 => 12851 / 16
  | 6 => 273 / 4
  | 7 => 39
  | _ => 0

noncomputable def middleShiftedCoefficient : ℕ → ℂ
  | 0 => -132713
  | 1 => -162815
  | 2 => -70061
  | 3 => -9355
  | 4 => 3269
  | 5 => 1571
  | 6 => 273
  | 7 => 39
  | _ => 0

noncomputable def rightShiftedCoefficient : ℕ → ℂ
  | 0 => -4861448543 / 16384
  | 1 => -1127440223 / 4096
  | 2 => -73686203 / 1024
  | 3 => 3078197 / 256
  | 4 => 770531 / 64
  | 5 => 52163 / 16
  | 6 => 1911 / 4
  | 7 => 39
  | _ => 0

theorem flowDenominator_left_shift (q : ℂ) :
    flowDenominator q = shiftedPolynomialValue
      leftShiftedCoefficient 7 (q - 5 / 4) := by
  simp [flowDenominator, shiftedPolynomialValue, leftShiftedCoefficient,
    Finset.sum_range_succ]
  ring

theorem flowDenominator_middle_shift (q : ℂ) :
    flowDenominator q = shiftedPolynomialValue
      middleShiftedCoefficient 7 (q - 2) := by
  simp [flowDenominator, shiftedPolynomialValue, middleShiftedCoefficient,
    Finset.sum_range_succ]
  ring

theorem flowDenominator_right_shift (q : ℂ) :
    flowDenominator q = shiftedPolynomialValue
      rightShiftedCoefficient 7 (q - 11 / 4) := by
  simp [flowDenominator, shiftedPolynomialValue, rightShiftedCoefficient,
    Finset.sum_range_succ]
  ring

theorem left_shift_dominance :
    (∑ i ∈ Finset.range 7,
      ‖leftShiftedCoefficient (i + 1)‖ * (1 / 3 : ℝ) ^ (i + 1)) <
        ‖leftShiftedCoefficient 0‖ := by
  norm_num [leftShiftedCoefficient, Finset.sum_range_succ, Complex.norm_real]

theorem middle_shift_dominance :
    (∑ i ∈ Finset.range 7,
      ‖middleShiftedCoefficient (i + 1)‖ * (3 / 5 : ℝ) ^ (i + 1)) <
        ‖middleShiftedCoefficient 0‖ := by
  norm_num [middleShiftedCoefficient, Finset.sum_range_succ,
    Complex.norm_real]

theorem right_shift_dominance :
    (∑ i ∈ Finset.range 7,
      ‖rightShiftedCoefficient (i + 1)‖ * (1 / 3 : ℝ) ^ (i + 1)) <
        ‖rightShiftedCoefficient 0‖ := by
  norm_num [rightShiftedCoefficient, Finset.sum_range_succ,
    Complex.norm_real]

theorem flowDenominator_ne_zero_on_left_disk
    {q : ℂ} (hq : q ∈ ball (5 / 4) (1 / 3)) :
    flowDenominator q ≠ 0 := by
  rw [flowDenominator_left_shift]
  apply shiftedPolynomialValue_ne_zero_of_norm_lt
    leftShiftedCoefficient 7 (1 / 3) (q - 5 / 4)
  · simpa [mem_ball, dist_eq_norm] using hq
  · exact left_shift_dominance

theorem flowDenominator_ne_zero_on_middle_disk
    {q : ℂ} (hq : q ∈ ball 2 (3 / 5)) :
    flowDenominator q ≠ 0 := by
  rw [flowDenominator_middle_shift]
  apply shiftedPolynomialValue_ne_zero_of_norm_lt
    middleShiftedCoefficient 7 (3 / 5) (q - 2)
  · simpa [mem_ball, dist_eq_norm] using hq
  · exact middle_shift_dominance

theorem flowDenominator_ne_zero_on_right_disk
    {q : ℂ} (hq : q ∈ ball (11 / 4) (1 / 3)) :
    flowDenominator q ≠ 0 := by
  rw [flowDenominator_right_shift]
  apply shiftedPolynomialValue_ne_zero_of_norm_lt
    rightShiftedCoefficient 7 (1 / 3) (q - 11 / 4)
  · simpa [mem_ball, dist_eq_norm] using hq
  · exact right_shift_dominance

theorem selected_disk_chain_overlaps :
    (1 : ℂ) ∈ ball (5 / 4) (1 / 3) ∧
    (3 / 2 : ℂ) ∈ ball (5 / 4) (1 / 3) ∩ ball 2 (3 / 5) ∧
    (5 / 2 : ℂ) ∈ ball 2 (3 / 5) ∩ ball (11 / 4) (1 / 3) ∧
    (3 : ℂ) ∈ ball (11 / 4) (1 / 3) := by
  norm_num [mem_ball, dist_eq_norm, Complex.norm_real]

theorem regularizedFlowNumerator_analyticAt (q : ℂ) :
    AnalyticAt ℂ regularizedFlowNumerator q := by
  unfold regularizedFlowNumerator
  fun_prop

theorem flowDenominator_analyticAt (q : ℂ) :
    AnalyticAt ℂ flowDenominator q := by
  unfold flowDenominator
  fun_prop

theorem regularizedLogDerivative_analyticOnNhd_left :
    AnalyticOnNhd ℂ regularizedLogDerivative (ball (5 / 4) (1 / 3)) := by
  intro q hq
  exact (regularizedFlowNumerator_analyticAt q).div
    (flowDenominator_analyticAt q)
    (flowDenominator_ne_zero_on_left_disk hq)

theorem regularizedLogDerivative_analyticOnNhd_middle :
    AnalyticOnNhd ℂ regularizedLogDerivative (ball 2 (3 / 5)) := by
  intro q hq
  exact (regularizedFlowNumerator_analyticAt q).div
    (flowDenominator_analyticAt q)
    (flowDenominator_ne_zero_on_middle_disk hq)

theorem regularizedLogDerivative_analyticOnNhd_right :
    AnalyticOnNhd ℂ regularizedLogDerivative (ball (11 / 4) (1 / 3)) := by
  intro q hq
  exact (regularizedFlowNumerator_analyticAt q).div
    (flowDenominator_analyticAt q)
    (flowDenominator_ne_zero_on_right_disk hq)

theorem exists_regularized_primitive_left :
    ∃ primitive : ℂ → ℂ,
      primitive (5 / 4) = 0 ∧
      ∀ q ∈ ball (5 / 4) (1 / 3),
        HasDerivAt primitive (regularizedLogDerivative q) q := by
  exact regularizedLogDerivative_analyticOnNhd_left.differentiableOn
    |>.isExactOn_ball.with_val_at (5 / 4) 0

theorem exists_regularized_primitive_middle :
    ∃ primitive : ℂ → ℂ,
      primitive 2 = 0 ∧
      ∀ q ∈ ball 2 (3 / 5),
        HasDerivAt primitive (regularizedLogDerivative q) q := by
  exact regularizedLogDerivative_analyticOnNhd_middle.differentiableOn
    |>.isExactOn_ball.with_val_at 2 0

theorem exists_regularized_primitive_right :
    ∃ primitive : ℂ → ℂ,
      primitive (11 / 4) = 0 ∧
      ∀ q ∈ ball (11 / 4) (1 / 3),
        HasDerivAt primitive (regularizedLogDerivative q) q := by
  exact regularizedLogDerivative_analyticOnNhd_right.differentiableOn
    |>.isExactOn_ball.with_val_at (11 / 4) 0

/-- Aggregated rational-chart and disk-chain certificate. -/
theorem selected_uniformization_terminal_certificate :
    uniformizedX 1 = 0 ∧ uniformizedY 1 = 6 ∧
    uniformizedX 3 = -2 ∧ uniformizedY 3 = 0 ∧
    (∀ q ∈ ball (5 / 4) (1 / 3), flowDenominator q ≠ 0) ∧
    (∀ q ∈ ball 2 (3 / 5), flowDenominator q ≠ 0) ∧
    (∀ q ∈ ball (11 / 4) (1 / 3), flowDenominator q ≠ 0) ∧
    AnalyticOnNhd ℂ regularizedLogDerivative (ball (5 / 4) (1 / 3)) ∧
    AnalyticOnNhd ℂ regularizedLogDerivative (ball 2 (3 / 5)) ∧
    AnalyticOnNhd ℂ regularizedLogDerivative (ball (11 / 4) (1 / 3)) ∧
    (1 : ℂ) ∈ ball (5 / 4) (1 / 3) ∧
    (3 / 2 : ℂ) ∈ ball (5 / 4) (1 / 3) ∩ ball 2 (3 / 5) ∧
    (5 / 2 : ℂ) ∈ ball 2 (3 / 5) ∩ ball (11 / 4) (1 / 3) ∧
    (3 : ℂ) ∈ ball (11 / 4) (1 / 3) := by
  refine ⟨uniformizedX_one, uniformizedY_one,
    uniformizedX_three, uniformizedY_three, ?_, ?_, ?_,
    regularizedLogDerivative_analyticOnNhd_left,
    regularizedLogDerivative_analyticOnNhd_middle,
    regularizedLogDerivative_analyticOnNhd_right,
    selected_disk_chain_overlaps⟩
  · intro q hq
    exact flowDenominator_ne_zero_on_left_disk hq
  · intro q hq
    exact flowDenominator_ne_zero_on_middle_disk hq
  · intro q hq
    exact flowDenominator_ne_zero_on_right_disk hq

end AxiomPackJacobianCriticalPuiseuxUniformization
