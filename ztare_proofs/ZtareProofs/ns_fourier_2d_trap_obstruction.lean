import Mathlib.Tactic
import ZtareProofs.ns_parity_transversality_target

namespace ZtareProofs

/-!
`ns_fourier_2d_trap_obstruction` records the red-team correction to the proposed
"2D trap" Fourier argument.

The tempting argument was:

  projected Riesz integral = 0
  => `(tau · k)^2 LambdaHat(k) = 0` on the support
  => support lies in `tau · k = 0`
  => the flow is effectively 2D.

That implication is false unless the spectral integrand has a positivity
structure. The pressure source

  `Lambda = |S|^2 - |omega|^2 / 2`

is sign-indefinite, and its Fourier transform is not a nonnegative measure.
Therefore cancellation can make the projected integral vanish while non-null
frequency mass remains.

This file gives the finite-mode algebraic counterexample and names the
additional positivity/cone-mass condition required for a valid Fourier route.
-/

/-- Two-mode surrogate for a projected Riesz integral. -/
def twoModeProjectedIntegral
    (weight source : Fin 2 → Real) : Real :=
  weight 0 * source 0 + weight 1 * source 1

/-- A mode is non-null for the projection if its multiplier weight is positive. -/
def nonNullMode (weight : Fin 2 → Real) (i : Fin 2) : Prop :=
  0 < weight i

/--
Cancellation obstruction:
a projected integral can vanish even when both modes are non-null and the source
is nonzero on both modes.

This is the finite-dimensional version of the Calderon-Zygmund cancellation
obstruction. It blocks the inference "zero projection implies support lies in
the null plane" for sign-indefinite sources.
-/
theorem zero_projection_does_not_force_null_support :
    ∃ weight source : Fin 2 → Real,
      twoModeProjectedIntegral weight source = 0 ∧
      nonNullMode weight 0 ∧
      nonNullMode weight 1 ∧
      source 0 ≠ 0 ∧
      source 1 ≠ 0 := by
  let weight : Fin 2 → Real := fun _ => 1
  let source : Fin 2 → Real := fun i => if i = 0 then 1 else -1
  refine ⟨weight, source, ?_, ?_, ?_, ?_, ?_⟩
  · unfold twoModeProjectedIntegral weight source
    norm_num
  · unfold nonNullMode weight
    norm_num
  · unfold nonNullMode weight
    norm_num
  · unfold source
    norm_num
  · unfold source
    norm_num

/--
Positive spectral cone-mass condition.

This is the missing hypothesis required to make a Fourier lower-bound argument
valid: enough same-sign source mass must live in modes where the projection
multiplier is bounded below.
-/
def positiveConeMassLowerBound
    (projectedIntegral coneMass multiplierFloor : Real) : Prop :=
  multiplierFloor * coneMass ≤ |projectedIntegral|

/--
If the projected spectral cone has positive mass and the multiplier is bounded
below on that cone, then the projected integral is nonzero.

This is the valid replacement for the false support-plane inference.
-/
theorem nonzero_projection_of_positive_cone_mass
    {projectedIntegral coneMass multiplierFloor : Real}
    (hmult : 0 < multiplierFloor)
    (hmass : 0 < coneMass)
    (hcone : positiveConeMassLowerBound projectedIntegral coneMass multiplierFloor) :
    0 < |projectedIntegral| := by
  unfold positiveConeMassLowerBound at hcone
  have hprod : 0 < multiplierFloor * coneMass := mul_pos hmult hmass
  exact lt_of_lt_of_le hprod hcone

end ZtareProofs
