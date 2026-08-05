import Mathlib.Tactic
import ZtareProofs.AxiomPackJacobianCriticalPuiseuxArithmetic

/-!
Universal arithmetic mechanisms inside the critical Puiseux terminal.

This file formalizes two implications used after the adapter supplies the
selected germ and the structural flow alternatives:

* equality of the first nonzero fractional coefficient in Julia's root
  branch forces the integral root multiplicity to equal `5/2`; and
* the nonproportional two-flow exponent lies strictly between one and two.

It does not encode the algebraic-germ expansion, Julia's formal-flow identity,
or the exhaustive finite/infinity/proportional factorization alternative.
-/

namespace AxiomPackJacobianCriticalPuiseuxMechanism

open AxiomPackJacobianCriticalPuiseuxArithmetic

/-- Cancellation of the nonzero branch coefficient exposes the forbidden
integral multiplicity. -/
theorem fractional_coefficient_forces_nonintegral_multiplicity
    (m : ℤ) (c a : ℚ) (hc : c ≠ 0) (ha : a ≠ 0)
    (hcoeff : (m : ℚ) * (c / a) = (5 / 2) * (c / a)) : False := by
  have hzero : ((m : ℚ) - 5 / 2) * (c / a) = 0 := by
    calc
      ((m : ℚ) - 5 / 2) * (c / a) =
          (m : ℚ) * (c / a) - (5 / 2) * (c / a) := by ring
      _ = 0 := sub_eq_zero.mpr hcoeff
  rcases mul_eq_zero.mp hzero with hm | hca
  · apply no_integral_multiplicity_five_halves m
    linarith
  · exact (div_ne_zero hc ha hca).elim

def twoFlowTransitionExponent (d e : ℚ) : ℚ :=
  1 + (d - e) / (d - 1)

/-- The first nonproportional two-flow exponent is trapped in `(1,2)` for
every degree pair in the structural alternative. -/
theorem two_flow_transition_exponent_interval
    (d e : ℚ) (hd : 1 < d) (he : 1 < e) (hed : e < d) :
    1 < twoFlowTransitionExponent d e ∧
      twoFlowTransitionExponent d e < 2 := by
  have hdenominator : 0 < d - 1 := sub_pos.mpr hd
  have hnumerator : 0 < d - e := sub_pos.mpr hed
  have hratioPositive : 0 < (d - e) / (d - 1) :=
    div_pos hnumerator hdenominator
  have hnumeratorSmall : d - e < d - 1 := by
    linarith
  have hratioSmall : (d - e) / (d - 1) < 1 :=
    (div_lt_one hdenominator).2 hnumeratorSmall
  constructor <;> simp only [twoFlowTransitionExponent] <;> linarith

theorem two_flow_transition_exponent_ne_five_halves
    (d e : ℚ) (hd : 1 < d) (he : 1 < e) (hed : e < d) :
    twoFlowTransitionExponent d e ≠ 5 / 2 := by
  have hinterval := two_flow_transition_exponent_interval d e hd he hed
  intro hequal
  rw [hequal] at hinterval
  norm_num at hinterval

/-- Aggregated universal arithmetic endpoint.  Structural adapter premises
remain outside this certificate. -/
theorem critical_puiseux_mechanism_terminal_certificate :
    (∀ (m : ℤ) (c a : ℚ), c ≠ 0 → a ≠ 0 →
      (m : ℚ) * (c / a) = (5 / 2) * (c / a) → False) ∧
    (∀ d e : ℚ, 1 < d → 1 < e → e < d →
      (1 < twoFlowTransitionExponent d e ∧
        twoFlowTransitionExponent d e < 2) ∧
      twoFlowTransitionExponent d e ≠ 5 / 2) := by
  constructor
  · intro m c a hc ha hcoeff
    exact fractional_coefficient_forces_nonintegral_multiplicity
      m c a hc ha hcoeff
  · intro d e hd he hed
    exact ⟨two_flow_transition_exponent_interval d e hd he hed,
      two_flow_transition_exponent_ne_five_halves d e hd he hed⟩

end AxiomPackJacobianCriticalPuiseuxMechanism
